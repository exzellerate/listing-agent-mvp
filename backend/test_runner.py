#!/usr/bin/env python3
"""
CLI Test Runner for Listing Agent

Run batch tests from command line with progress reporting.

Usage:
    python test_runner.py --csv test_data.csv --images ./test_images
    python test_runner.py --csv test_data.csv --images ./test_images --output results.json
    python test_runner.py --csv test_data.csv --images ./test_images --verbose
    python test_runner.py --csv test_data.csv --images ./test_images --platform ebay
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from services.batch_tester import get_batch_tester


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


def print_progress(current: int, total: int, test_name: str):
    """Print progress bar."""
    percent = (current / total) * 100
    bar_length = 50
    filled = int(bar_length * current / total)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"\r[{bar}] {percent:.1f}% ({current}/{total}) - {test_name[:40]}", end="", flush=True)


def print_summary(summary: dict):
    """Print test summary."""
    print_section("Test Summary")

    # Overall stats
    print(f"  Total Tests:     {summary['total_tests']}")
    print(f"  ✅ Passed:        {summary['passed']} ({summary['pass_rate']:.1f}%)")
    print(f"  ❌ Failed:        {summary['failed']}")
    print(f"  ⏱️  Duration:      {summary['total_duration_seconds']:.2f}s")
    print(f"  📊 Avg Score:     {summary['avg_score']:.1f}%")

    # Field accuracy
    print_section("Field Accuracy")
    for field, accuracy in summary['field_accuracy'].items():
        emoji = "✅" if accuracy >= 80 else "⚠️" if accuracy >= 60 else "❌"
        print(f"  {emoji} {field:20s}: {accuracy:.1f}%")

    # Failed tests
    if summary['failed_tests']:
        print_section("Failed Tests")
        for failed in summary['failed_tests']:
            print(f"  ❌ Test {failed['test_id']}: {failed['image_path']}")
            print(f"     Score: {failed['overall_score']:.1f}%")
            if failed.get('failed_fields'):
                print(f"     Failed fields: {', '.join(failed['failed_fields'])}")


def print_detailed_result(result: dict, verbose: bool = False):
    """Print detailed result for a single test."""
    print(f"\n  {'='*76}")
    print(f"  Test {result['test_id']}: {result['image_path']}")
    print(f"  Status: {result['status'].upper()} | Score: {result['overall_score']:.1f}% | Duration: {result['duration_seconds']:.2f}s")
    print(f"  {'='*76}")

    if verbose:
        analysis = result.get('analysis', {})
        for field, data in analysis.items():
            emoji = "✅" if data['passed'] else "❌"
            print(f"\n  {emoji} {field.upper()}:")
            print(f"     Expected: {data['expected']}")
            print(f"     Actual:   {data['actual']}")
            print(f"     Score:    {data['score']:.1f}%")
            if data.get('details'):
                print(f"     Details:  {data['details']}")


async def run_tests(args):
    """Run tests with CLI interface."""
    print_header("Listing Agent - Batch Test Runner")

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
    if args.platform:
        print(f"🎯 Platform:     {args.platform}")
    if args.output:
        print(f"💾 Output File:  {args.output}")

    # Get tester instance
    tester = get_batch_tester()

    # Load test cases to show progress
    import pandas as pd
    df = pd.read_csv(csv_path)

    # Filter by platform if specified
    if args.platform:
        df = df[df['platform'] == args.platform]
        if len(df) == 0:
            print(f"❌ Error: No test cases found for platform: {args.platform}")
            return 1

    total_tests = len(df)
    print(f"\n🚀 Starting {total_tests} tests...\n")

    # Run tests
    try:
        results = await tester.run_batch_tests(
            csv_path=str(csv_path),
            images_dir=str(images_dir)
        )
    except Exception as e:
        print(f"\n\n❌ Error running tests: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

    print("\n")  # New line after progress bar

    # Print summary
    print_summary(results['summary'])

    # Print detailed results if verbose
    if args.verbose:
        print_section("Detailed Results")
        for result in results['results']:
            print_detailed_result(result, verbose=True)

    # Save results if output file specified
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to: {output_path}")

    # Exit code based on pass rate
    pass_rate = results['summary']['pass_rate']
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
        description="Run batch tests for Listing Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python test_runner.py --csv test_data.csv --images ./test_images

  # Save results to file
  python test_runner.py --csv test_data.csv --images ./test_images --output results.json

  # Verbose output with detailed results
  python test_runner.py --csv test_data.csv --images ./test_images --verbose

  # Test only eBay platform
  python test_runner.py --csv test_data.csv --images ./test_images --platform ebay
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
        '--output',
        help='Output file for results (JSON format)'
    )

    parser.add_argument(
        '--platform',
        choices=['ebay', 'amazon', 'walmart'],
        help='Filter tests by platform'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed results for each test'
    )

    args = parser.parse_args()

    # Run tests
    exit_code = asyncio.run(run_tests(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
