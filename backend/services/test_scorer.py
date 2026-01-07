"""
Test Scoring Module for Listing Agent

This module provides comprehensive scoring and comparison functions
for validating the accuracy of image analysis and pricing research.
"""

import re
from typing import Dict, List, Any, Tuple
from rapidfuzz import fuzz
from dataclasses import dataclass


@dataclass
class FieldScore:
    """Score for a single field comparison."""
    expected: Any
    actual: Any
    score: float
    passed: bool
    details: str = ""


@dataclass
class TestResult:
    """Complete test result for a single item."""
    test_id: int
    image_path: str
    status: str  # "passed", "failed", or "error"
    overall_score: float
    duration_seconds: float
    scores: Dict[str, FieldScore]
    timestamp: str = None  # ISO 8601 timestamp when test was run
    error_type: str = None  # Type of error if status is "error"
    error_details: str = None  # Detailed error message
    error_traceback: str = None  # Full traceback for debugging

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "test_id": self.test_id,
            "image_path": self.image_path,
            "status": self.status,
            "overall_score": round(self.overall_score, 2),
            "duration_seconds": round(self.duration_seconds, 2),
            "analysis": {
                field: {
                    "expected": score.expected,
                    "actual": score.actual,
                    "score": round(score.score, 2) if isinstance(score.score, float) else score.score,
                    "passed": score.passed,
                    "details": score.details
                }
                for field, score in self.scores.items()
            }
        }

        # Include timestamp if available
        if self.timestamp:
            result["timestamp"] = self.timestamp

        # Include error details if this is an error result
        if self.error_type:
            result["error_type"] = self.error_type
        if self.error_details:
            result["error_details"] = self.error_details
        if self.error_traceback:
            result["error_traceback"] = self.error_traceback

        return result


class TestScorer:
    """Scoring engine for comparing expected vs actual results."""

    # Score thresholds
    TITLE_THRESHOLD = 70.0
    DESCRIPTION_THRESHOLD = 60.0
    PRODUCT_NAME_THRESHOLD = 80.0

    # Weights for overall score calculation
    WEIGHTS = {
        "product_name": 0.20,
        "title": 0.20,
        "description": 0.15,
        "category": 0.15,
        "condition": 0.15,
        "price": 0.15
    }

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for comparison (lowercase, remove extra spaces)."""
        return re.sub(r'\s+', ' ', text.lower().strip())

    @staticmethod
    def score_product_name(expected: str, actual: str) -> FieldScore:
        """
        Score product name similarity using fuzzy matching.

        Args:
            expected: Expected product name
            actual: Actual detected product name

        Returns:
            FieldScore with similarity percentage
        """
        expected_norm = TestScorer.normalize_text(expected)
        actual_norm = TestScorer.normalize_text(actual)

        # Use token sort ratio for word-order flexibility
        score = fuzz.token_sort_ratio(expected_norm, actual_norm)
        passed = score >= TestScorer.PRODUCT_NAME_THRESHOLD

        details = f"Fuzzy match score: {score}%"
        if not passed:
            details += f" (threshold: {TestScorer.PRODUCT_NAME_THRESHOLD}%)"

        return FieldScore(
            expected=expected,
            actual=actual,
            score=score,
            passed=passed,
            details=details
        )

    @staticmethod
    def score_title(expected: str, actual: str) -> FieldScore:
        """
        Score listing title similarity.

        Uses partial ratio to allow for variations in title format
        while maintaining key information.

        Args:
            expected: Expected title
            actual: Generated title

        Returns:
            FieldScore with similarity percentage
        """
        expected_norm = TestScorer.normalize_text(expected)
        actual_norm = TestScorer.normalize_text(actual)

        # Use partial ratio for substring matching
        partial_score = fuzz.partial_ratio(expected_norm, actual_norm)
        # Use token sort for word-order flexibility
        token_score = fuzz.token_sort_ratio(expected_norm, actual_norm)

        # Average the two scores
        score = (partial_score + token_score) / 2
        passed = score >= TestScorer.TITLE_THRESHOLD

        details = f"Partial: {partial_score}%, Token: {token_score}%, Avg: {score:.1f}%"
        if not passed:
            details += f" (threshold: {TestScorer.TITLE_THRESHOLD}%)"

        return FieldScore(
            expected=expected,
            actual=actual,
            score=score,
            passed=passed,
            details=details
        )

    @staticmethod
    def score_description(expected_keywords: List[str], actual_description: str) -> FieldScore:
        """
        Score description quality by keyword matching.

        Args:
            expected_keywords: List of keywords that should appear
            actual_description: Generated description text

        Returns:
            FieldScore with keyword match percentage
        """
        actual_norm = TestScorer.normalize_text(actual_description)

        found_keywords = []
        missing_keywords = []

        for keyword in expected_keywords:
            keyword_norm = TestScorer.normalize_text(keyword)

            # Check for exact match or close fuzzy match
            if keyword_norm in actual_norm:
                found_keywords.append(keyword)
            else:
                # Try fuzzy matching for each word in description
                words = actual_norm.split()
                best_match = max([fuzz.ratio(keyword_norm, word) for word in words] + [0])

                if best_match >= 85:  # Close enough match
                    found_keywords.append(keyword)
                else:
                    missing_keywords.append(keyword)

        score = (len(found_keywords) / len(expected_keywords) * 100) if expected_keywords else 100
        passed = score >= TestScorer.DESCRIPTION_THRESHOLD

        details = f"Found {len(found_keywords)}/{len(expected_keywords)} keywords"
        if missing_keywords:
            details += f". Missing: {', '.join(missing_keywords[:3])}"
            if len(missing_keywords) > 3:
                details += f" +{len(missing_keywords) - 3} more"

        return FieldScore(
            expected=expected_keywords,
            actual=found_keywords,
            score=score,
            passed=passed,
            details=details
        )

    @staticmethod
    def score_category(expected: str, actual: str) -> FieldScore:
        """
        Score category match (exact match required).

        Args:
            expected: Expected category
            actual: Detected category

        Returns:
            FieldScore with pass/fail
        """
        expected_norm = TestScorer.normalize_text(expected) if expected else ""
        actual_norm = TestScorer.normalize_text(actual) if actual else ""

        # Exact match required
        exact_match = expected_norm == actual_norm

        # But also check fuzzy match for partial credit
        fuzzy_score = fuzz.ratio(expected_norm, actual_norm)

        passed = exact_match
        score = 100.0 if exact_match else fuzzy_score

        details = "Exact match" if exact_match else f"Fuzzy match: {fuzzy_score}%"

        return FieldScore(
            expected=expected,
            actual=actual,
            score=score,
            passed=passed,
            details=details
        )

    @staticmethod
    def score_condition(expected: str, actual: str) -> FieldScore:
        """
        Score condition match (exact match required).

        Args:
            expected: Expected condition
            actual: Detected condition

        Returns:
            FieldScore with pass/fail
        """
        expected_norm = TestScorer.normalize_text(expected)
        actual_norm = TestScorer.normalize_text(actual)

        # Exact match required
        exact_match = expected_norm == actual_norm
        passed = exact_match
        score = 100.0 if exact_match else 0.0

        details = "Exact match" if exact_match else "Mismatch"

        return FieldScore(
            expected=expected,
            actual=actual,
            score=score,
            passed=passed,
            details=details
        )

    @staticmethod
    def score_price(expected_min: float, expected_max: float, actual: float,
                   confidence_score: int) -> FieldScore:
        """
        Score price accuracy.

        Args:
            expected_min: Minimum acceptable price
            expected_max: Maximum acceptable price
            actual: Suggested price
            confidence_score: AI confidence score (0-100)

        Returns:
            FieldScore with pass/fail and details
        """
        in_range = expected_min <= actual <= expected_max

        if in_range:
            # Price is within range - perfect score
            score = 100.0
            details = f"Within range ${expected_min:.2f} - ${expected_max:.2f}"
        else:
            # Calculate how far off the price is
            if actual < expected_min:
                diff_pct = ((expected_min - actual) / expected_min) * 100
                details = f"Too low by ${expected_min - actual:.2f} ({diff_pct:.1f}%)"
            else:
                diff_pct = ((actual - expected_max) / expected_max) * 100
                details = f"Too high by ${actual - expected_max:.2f} ({diff_pct:.1f}%)"

            # Partial credit based on how close it is
            if diff_pct < 10:
                score = 80.0
            elif diff_pct < 20:
                score = 60.0
            elif diff_pct < 30:
                score = 40.0
            else:
                score = 0.0

        details += f". Confidence: {confidence_score}%"

        return FieldScore(
            expected=(expected_min, expected_max),
            actual=actual,
            score=score,
            passed=in_range,
            details=details
        )

    @staticmethod
    def calculate_overall_score(scores: Dict[str, FieldScore]) -> float:
        """
        Calculate weighted overall score.

        Args:
            scores: Dictionary of field scores

        Returns:
            Overall score (0-100)
        """
        total_score = 0.0
        total_weight = 0.0

        for field, weight in TestScorer.WEIGHTS.items():
            if field in scores:
                total_score += scores[field].score * weight
                total_weight += weight

        return (total_score / total_weight) if total_weight > 0 else 0.0

    @staticmethod
    def compare_results(expected: Dict[str, Any],
                       analysis_result: Dict[str, Any],
                       pricing_result: Dict[str, Any]) -> Dict[str, FieldScore]:
        """
        Compare expected values with actual results.

        Args:
            expected: Expected values from test case
            analysis_result: Result from /api/analyze
            pricing_result: Result from /api/research-pricing

        Returns:
            Dictionary of field scores
        """
        scores = {}

        # Score product name
        scores["product_name"] = TestScorer.score_product_name(
            expected["expected_name"],
            analysis_result.get("product_name", "")
        )

        # Score title
        scores["title"] = TestScorer.score_title(
            expected["expected_title"],
            analysis_result.get("suggested_title", "")
        )

        # Score description (keyword matching)
        keywords = [k.strip() for k in expected["expected_description_keywords"].split(",")]
        scores["description"] = TestScorer.score_description(
            keywords,
            analysis_result.get("suggested_description", "")
        )

        # Score category
        scores["category"] = TestScorer.score_category(
            expected["expected_category"],
            analysis_result.get("category", "")
        )

        # Score condition
        scores["condition"] = TestScorer.score_condition(
            expected["expected_condition"],
            analysis_result.get("condition", "")
        )

        # Score price
        scores["price"] = TestScorer.score_price(
            float(expected["expected_price_min"]),
            float(expected["expected_price_max"]),
            pricing_result.get("statistics", {}).get("suggested_price", 0.0),
            pricing_result.get("confidence_score", 0)
        )

        return scores

    @staticmethod
    def generate_summary(results: List[TestResult]) -> Dict[str, Any]:
        """
        Generate summary statistics from test results.

        Args:
            results: List of TestResult objects

        Returns:
            Summary dictionary with overall statistics
        """
        if not results:
            return {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "avg_score": 0.0,
                "total_duration_seconds": 0.0
            }

        total = len(results)
        passed = sum(1 for r in results if r.status == "passed")
        failed = total - passed

        avg_score = sum(r.overall_score for r in results) / total
        total_duration = sum(r.duration_seconds for r in results)

        # Calculate per-field accuracy
        field_scores = {field: [] for field in TestScorer.WEIGHTS.keys()}
        for result in results:
            for field, score in result.scores.items():
                if field in field_scores:
                    field_scores[field].append(score.score)

        field_accuracy = {
            field: round(sum(scores) / len(scores), 2) if scores else 0.0
            for field, scores in field_scores.items()
        }

        # Find failed tests
        failed_tests = [
            {
                "test_id": r.test_id,
                "image_path": r.image_path,
                "overall_score": round(r.overall_score, 2),
                "failed_fields": [
                    field for field, score in r.scores.items() if not score.passed
                ]
            }
            for r in results if r.status == "failed"
        ]

        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round((passed / total) * 100, 2),
            "avg_score": round(avg_score, 2),
            "total_duration_seconds": round(total_duration, 2),
            "field_accuracy": field_accuracy,
            "failed_tests": failed_tests
        }
