"""
Batch Testing Service for Listing Agent

Processes CSV test files and runs comprehensive testing.
"""

import time
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

from models import TestCaseExpected
from services.claude_analyzer import get_analyzer
from services.pricing_researcher import get_pricing_researcher
from services.test_scorer import TestScorer, TestResult

logger = logging.getLogger(__name__)


class BatchTester:
    """Service for running batch tests from CSV files."""

    def __init__(self):
        self.analyzer = get_analyzer()
        self.pricing_researcher = get_pricing_researcher()
        self.scorer = TestScorer()

    async def run_batch_tests(self, csv_path: str, images_dir: str = ".") -> Dict[str, Any]:
        """
        Run batch tests from a CSV file.

        Args:
            csv_path: Path to CSV file with test cases
            images_dir: Directory containing test images

        Returns:
            Dictionary with test results and summary
        """
        logger.info(f"Starting batch tests from: {csv_path}")
        start_time = time.time()

        # Load test cases from CSV
        test_cases = self._load_test_cases(csv_path)
        logger.info(f"Loaded {len(test_cases)} test cases")

        # Run tests
        results: List[TestResult] = []
        for idx, test_case in enumerate(test_cases, 1):
            logger.info(f"Running test {idx}/{len(test_cases)}: {test_case['image_path']}")

            result = await self._run_single_test(
                test_id=idx,
                test_case=test_case,
                images_dir=images_dir
            )
            results.append(result)

        # Generate summary
        summary = self.scorer.generate_summary(results)

        total_time = time.time() - start_time
        logger.info(f"Batch tests complete in {total_time:.2f}s. Pass rate: {summary['pass_rate']:.1f}%")

        return {
            "summary": summary,
            "results": [r.to_dict() for r in results]
        }

    def _load_test_cases(self, csv_path: str) -> List[Dict[str, Any]]:
        """
        Load test cases from CSV file.

        Args:
            csv_path: Path to CSV file

        Returns:
            List of test case dictionaries
        """
        try:
            df = pd.read_csv(csv_path)

            # Validate required columns
            required_columns = [
                "image_path", "expected_name", "expected_category",
                "expected_condition", "expected_title", "expected_description_keywords",
                "expected_price_min", "expected_price_max", "platform"
            ]

            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

            # Convert to list of dicts
            test_cases = df.to_dict('records')

            return test_cases

        except Exception as e:
            logger.error(f"Failed to load test cases: {e}")
            raise

    async def _run_single_test(
        self,
        test_id: int,
        test_case: Dict[str, Any],
        images_dir: str
    ) -> TestResult:
        """
        Run a single test case.

        Args:
            test_id: Test identifier
            test_case: Test case data
            images_dir: Directory containing images

        Returns:
            TestResult object
        """
        start_time = time.time()

        try:
            # Build full image path
            image_path = Path(images_dir) / test_case["image_path"]

            if not image_path.exists():
                error_msg = f"Image file not found at path: {image_path}"
                logger.error(f"Test {test_id}: {error_msg}")
                return self._create_error_result(
                    test_id=test_id,
                    image_path=test_case["image_path"],
                    error_type="file_not_found",
                    error_message=error_msg,
                    error_traceback=None,
                    duration=time.time() - start_time
                )

            # Read image file
            try:
                with open(image_path, 'rb') as f:
                    image_data = f.read()
            except Exception as e:
                error_msg = f"Failed to read image file: {str(e)}"
                logger.error(f"Test {test_id}: {error_msg}", exc_info=True)
                return self._create_error_result(
                    test_id=test_id,
                    image_path=test_case["image_path"],
                    error_type="file_read_error",
                    error_message=error_msg,
                    error_traceback=traceback.format_exc(),
                    duration=time.time() - start_time
                )

            # Determine image type
            suffix = image_path.suffix.lower()
            content_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.webp': 'image/webp',
                '.gif': 'image/gif'
            }
            image_type = content_type_map.get(suffix, 'image/jpeg')

            # Step 1: Analyze image
            logger.info(f"Test {test_id}: Analyzing image: {test_case['image_path']}")
            try:
                analysis_result = await self.analyzer.analyze_image(
                    image_data=image_data,
                    image_type=image_type,
                    platform=test_case["platform"]
                )
            except Exception as e:
                error_msg = f"Image analysis failed: {str(e)}"
                logger.error(f"Test {test_id}: {error_msg}", exc_info=True)
                return self._create_error_result(
                    test_id=test_id,
                    image_path=test_case["image_path"],
                    error_type="analysis_error",
                    error_message=error_msg,
                    error_traceback=traceback.format_exc(),
                    duration=time.time() - start_time
                )

            # Step 2: Research pricing
            logger.info(f"Test {test_id}: Researching pricing for: {analysis_result.product_name}")
            try:
                pricing_result = await self.pricing_researcher.research_pricing(
                    product_name=analysis_result.product_name,
                    category=analysis_result.category,
                    condition=analysis_result.condition,
                    platform=test_case["platform"]
                )
            except Exception as e:
                error_msg = f"Pricing research failed: {str(e)}"
                logger.error(f"Test {test_id}: {error_msg}", exc_info=True)
                return self._create_error_result(
                    test_id=test_id,
                    image_path=test_case["image_path"],
                    error_type="pricing_error",
                    error_message=error_msg,
                    error_traceback=traceback.format_exc(),
                    duration=time.time() - start_time
                )

            # Step 3: Score results
            try:
                scores = self.scorer.compare_results(
                    expected=test_case,
                    analysis_result=analysis_result.model_dump(),
                    pricing_result=pricing_result.model_dump()
                )
            except Exception as e:
                error_msg = f"Scoring failed: {str(e)}"
                logger.error(f"Test {test_id}: {error_msg}", exc_info=True)
                return self._create_error_result(
                    test_id=test_id,
                    image_path=test_case["image_path"],
                    error_type="scoring_error",
                    error_message=error_msg,
                    error_traceback=traceback.format_exc(),
                    duration=time.time() - start_time
                )

            # Calculate overall score
            overall_score = self.scorer.calculate_overall_score(scores)

            # Determine pass/fail (70% threshold)
            status = "passed" if overall_score >= 70.0 else "failed"

            duration = time.time() - start_time

            logger.info(
                f"Test {test_id} {status}: {overall_score:.1f}% in {duration:.2f}s"
            )

            return TestResult(
                test_id=test_id,
                image_path=test_case["image_path"],
                status=status,
                overall_score=overall_score,
                duration_seconds=duration,
                scores=scores,
                timestamp=datetime.utcnow().isoformat() + 'Z'
            )

        except Exception as e:
            # Catch-all for any unexpected errors
            error_msg = f"Unexpected error during test execution: {str(e)}"
            logger.error(f"Test {test_id}: {error_msg}", exc_info=True)
            return self._create_error_result(
                test_id=test_id,
                image_path=test_case["image_path"],
                error_type="unknown_error",
                error_message=error_msg,
                error_traceback=traceback.format_exc(),
                duration=time.time() - start_time
            )

    def _create_error_result(
        self,
        test_id: int,
        image_path: str,
        error_type: str,
        error_message: str,
        error_traceback: str,
        duration: float
    ) -> TestResult:
        """
        Create an error result for a failed test.

        Args:
            test_id: Test identifier
            image_path: Path to image
            error_type: Type of error (file_not_found, analysis_error, etc.)
            error_message: Human-readable error message
            error_traceback: Full traceback for debugging
            duration: Test duration

        Returns:
            TestResult with error status
        """
        from services.test_scorer import FieldScore

        return TestResult(
            test_id=test_id,
            image_path=image_path,
            status="error",
            overall_score=0.0,
            duration_seconds=duration,
            scores={
                "error": FieldScore(
                    expected="Success",
                    actual="Error",
                    score=0.0,
                    passed=False,
                    details=error_message
                )
            },
            timestamp=datetime.utcnow().isoformat() + 'Z',
            error_type=error_type,
            error_details=error_message,
            error_traceback=error_traceback
        )


def get_batch_tester() -> BatchTester:
    """Get BatchTester instance."""
    return BatchTester()
