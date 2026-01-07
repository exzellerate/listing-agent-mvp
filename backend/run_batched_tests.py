#!/usr/bin/env python3
"""
Batched Test Runner for Listing Agent

Runs tests in batches to avoid API rate limits while maximizing throughput.

Usage:
    python run_batched_tests.py --csv test_data_current.csv --images ./test_images
    python run_batched_tests.py --csv test_data_current.csv --images ./test_images --batch-size 2 --delay 90
"""

import asyncio
import argparse
import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from services.batch_tester import BatchTester
from services.test_scorer import TestResult, FieldScore


def print_header(text: str):
    """Print formatted header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def print_section(text: str):
    """Print formatted section."""
    print("\n" + "-" * 80)
    print(f"  {text}")
    print("-" * 80)


def dict_to_test_result(result_dict: Dict[str, Any]) -> TestResult:
    """Convert a result dictionary back to TestResult object."""
    # Convert analysis dict back to scores dict with FieldScore objects
    scores = {}
    for field, field_data in result_dict.get("analysis", {}).items():
        scores[field] = FieldScore(
            expected=field_data["expected"],
            actual=field_data["actual"],
            score=field_data["score"],
            passed=field_data["passed"],
            details=field_data.get("details", "")
        )

    return TestResult(
        test_id=result_dict["test_id"],
        image_path=result_dict["image_path"],
        status=result_dict["status"],
        overall_score=result_dict["overall_score"],
        duration_seconds=result_dict["duration_seconds"],
        scores=scores
    )


def print_batch_progress(batch_num: int, total_batches: int, batch_size: int):
    """Print batch progress."""
    print(f"\n{'='*80}")
    print(f"  📦 BATCH {batch_num}/{total_batches} ({batch_size} tests)")
    print(f"{'='*80}\n")


def print_summary(all_results: List[TestResult], total_duration: float):
    """Print comprehensive test summary."""
    print_section("Final Test Summary")

    total = len(all_results)
    passed = sum(1 for r in all_results if r.status == "passed")
    failed = sum(1 for r in all_results if r.status == "failed")
    errors = sum(1 for r in all_results if r.status == "error")

    avg_score = sum(r.overall_score for r in all_results) / total if total > 0 else 0
    pass_rate = (passed / total * 100) if total > 0 else 0

    print(f"  Total Tests:     {total}")
    print(f"  ✅ Passed:        {passed} ({pass_rate:.1f}%)")
    print(f"  ❌ Failed:        {failed}")
    print(f"  ⚠️  Errors:        {errors}")
    print(f"  ⏱️  Duration:      {total_duration:.2f}s ({total_duration/60:.1f}m)")
    print(f"  📊 Avg Score:     {avg_score:.1f}%")

    # Calculate field accuracy from all results
    from services.test_scorer import TestScorer
    field_scores = {field: [] for field in TestScorer.WEIGHTS.keys()}
    for result in all_results:
        for field, score in result.scores.items():
            if field in field_scores:
                field_scores[field].append(score.score)

    field_accuracy = {
        field: round(sum(scores) / len(scores), 2) if scores else 0.0
        for field, scores in field_scores.items()
    }

    print_section("Field Accuracy")
    for field, accuracy in field_accuracy.items():
        emoji = "✅" if accuracy >= 80 else "⚠️" if accuracy >= 60 else "❌"
        print(f"  {emoji} {field:20s}: {accuracy:.1f}%")

    # Show failed tests
    failed_results = [r for r in all_results if r.status == "failed"]
    if failed_results:
        print_section(f"Failed Tests ({len(failed_results)})")
        for result in failed_results[:5]:  # Show first 5
            failed_fields = [field for field, score in result.scores.items() if not score.passed]
            print(f"  ❌ Test {result.test_id}: {result.image_path}")
            print(f"     Score: {result.overall_score:.1f}%")
            print(f"     Failed: {', '.join(failed_fields)}")
        if len(failed_results) > 5:
            print(f"  ... and {len(failed_results) - 5} more")

    # Show errors
    error_results = [r for r in all_results if r.status == "error"]
    if error_results:
        print_section(f"Errors ({len(error_results)})")
        for result in error_results[:3]:  # Show first 3
            error_msg = result.scores.get("error", None)
            print(f"  ⚠️  Test {result.test_id}: {result.image_path}")
            if error_msg:
                print(f"     {error_msg.details[:100]}")
        if len(error_results) > 3:
            print(f"  ... and {len(error_results) - 3} more")


async def run_batched_tests(args):
    """Run tests in batches with delays."""
    print_header("Listing Agent - Batched Test Runner")

    # Validate inputs
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"❌ Error: CSV file not found: {csv_path}")
        return 1

    images_dir = Path(args.images)
    if not images_dir.exists():
        print(f"❌ Error: Images directory not found: {images_dir}")
        return 1

    print(f"📄 Test Data:    {csv_path}")
    print(f"📁 Images Dir:   {images_dir}")
    print(f"📦 Batch Size:   {args.batch_size} tests per batch")
    print(f"⏱️  Delay:        {args.delay}s between batches")
    if args.output:
        print(f"💾 Output File:  {args.output}")

    # Load test cases
    df = pd.read_csv(csv_path)
    total_tests = len(df)
    num_batches = (total_tests + args.batch_size - 1) // args.batch_size  # Ceiling division

    print(f"\n🚀 Running {total_tests} tests in {num_batches} batches...\n")

    # Get tester instance
    tester = BatchTester()

    # Store all results
    all_results: List[TestResult] = []
    overall_start = time.time()

    # Process batches
    for batch_num in range(num_batches):
        start_idx = batch_num * args.batch_size
        end_idx = min(start_idx + args.batch_size, total_tests)
        batch_df = df.iloc[start_idx:end_idx]

        batch_size = len(batch_df)
        print_batch_progress(batch_num + 1, num_batches, batch_size)

        # Create temporary CSV for this batch
        temp_csv = f"temp_batch_{batch_num}.csv"
        batch_df.to_csv(temp_csv, index=False)

        try:
            # Run this batch
            batch_start = time.time()
            results = await tester.run_batch_tests(
                csv_path=temp_csv,
                images_dir=str(images_dir)
            )
            batch_duration = time.time() - batch_start

            # Convert dicts back to TestResult objects
            batch_results = [dict_to_test_result(r) for r in results['results']]
            all_results.extend(batch_results)

            # Show batch summary
            batch_summary = results['summary']
            print(f"\n  Batch Complete:")
            print(f"    Passed: {batch_summary['passed']}/{batch_summary['total_tests']}")
            print(f"    Avg Score: {batch_summary['avg_score']:.1f}%")
            print(f"    Duration: {batch_duration:.1f}s")

            # Save incremental results
            if args.output:
                incremental_output = {
                    "batches_completed": batch_num + 1,
                    "total_batches": num_batches,
                    "tests_completed": len(all_results),
                    "total_tests": total_tests,
                    "results": [r.to_dict() for r in all_results]
                }
                with open(args.output, 'w') as f:
                    json.dump(incremental_output, f, indent=2)
                print(f"  💾 Progress saved to {args.output}")

        except Exception as e:
            print(f"\n❌ Batch {batch_num + 1} failed: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
        finally:
            # Clean up temp CSV
            Path(temp_csv).unlink(missing_ok=True)

        # Wait between batches (except after last batch)
        if batch_num < num_batches - 1:
            print(f"\n⏸️  Waiting {args.delay}s before next batch...")
            for remaining in range(args.delay, 0, -1):
                print(f"  ⏱️  {remaining}s remaining...", end='\r', flush=True)
                await asyncio.sleep(1)
            print()  # New line after countdown

    # Calculate total duration
    total_duration = time.time() - overall_start

    # Print final summary
    print_summary(all_results, total_duration)

    # Save final results
    if args.output:
        final_output = {
            "total_tests": total_tests,
            "batches": num_batches,
            "total_duration_seconds": total_duration,
            "results": [r.to_dict() for r in all_results]
        }
        with open(args.output, 'w') as f:
            json.dump(final_output, f, indent=2)
        print(f"\n💾 Final results saved to: {args.output}")

    # Exit code based on pass rate
    passed = sum(1 for r in all_results if r.status == "passed")
    pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0

    if pass_rate >= 90:
        print("\n🎉 Excellent! All tests passed with high accuracy.")
        return 0
    elif pass_rate >= 70:
        print("\n✅ Good! Most tests passed.")
        return 0
    elif pass_rate >= 50:
        print("\n⚠️  Warning: Many tests failed. Review failed cases.")
        return 1
    else:
        print("\n❌ Critical: Most tests failed. Immediate attention required.")
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run batch tests with rate limit handling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings (2 tests per batch, 60s delay)
  python run_batched_tests.py --csv test_data_current.csv --images ./test_images

  # Custom batch size and delay
  python run_batched_tests.py --csv test_data_current.csv --images ./test_images --batch-size 3 --delay 90

  # Save results
  python run_batched_tests.py --csv test_data_current.csv --images ./test_images --output results.json

  # Verbose mode
  python run_batched_tests.py --csv test_data_current.csv --images ./test_images --verbose
        """
    )

    parser.add_argument(
        '--csv',
        required=True,
        help='Path to CSV file with test cases'
    )

    parser.add_argument(
        '--images',
        required=True,
        help='Directory containing test images'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=2,
        help='Number of tests per batch (default: 2)'
    )

    parser.add_argument(
        '--delay',
        type=int,
        default=60,
        help='Delay in seconds between batches (default: 60)'
    )

    parser.add_argument(
        '--output',
        help='Output file for results (JSON format)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed error messages'
    )

    args = parser.parse_args()

    # Run tests
    exit_code = asyncio.run(run_batched_tests(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
