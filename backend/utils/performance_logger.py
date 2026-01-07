"""
Performance Logger for tracking API call timings and bottlenecks.

Writes structured JSON Lines logs for easy analysis.
"""

import os
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager

# Log directory
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Log files
PERFORMANCE_LOG = LOG_DIR / "performance.jsonl"
API_REQUESTS_LOG = LOG_DIR / "api_requests.jsonl"
WEB_SEARCH_LOG = LOG_DIR / "web_search.jsonl"
ANALYSIS_REQUESTS_LOG = LOG_DIR / "analysis_requests.jsonl"
ANALYSIS_RESULTS_LOG = LOG_DIR / "analysis_results.jsonl"
PRICING_RESULTS_LOG = LOG_DIR / "pricing_results.jsonl"
REQUEST_STATUS_LOG = LOG_DIR / "request_status.jsonl"


def write_log(log_file: Path, data: Dict[str, Any]) -> None:
    """Write a log entry as JSON Lines format."""
    data["timestamp"] = datetime.utcnow().isoformat() + "Z"
    with open(log_file, "a") as f:
        f.write(json.dumps(data) + "\n")


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return f"req_{uuid.uuid4().hex[:12]}"


class PerformanceTracker:
    """Track performance metrics for a single request."""

    def __init__(self, request_id: Optional[str] = None):
        self.request_id = request_id or generate_request_id()
        self.start_time = time.time()
        self.metrics = {}

    def log_event(self, event_type: str, **kwargs) -> None:
        """Log an event with timing."""
        data = {
            "type": event_type,
            "request_id": self.request_id,
            **kwargs
        }
        write_log(PERFORMANCE_LOG, data)

    def log_api_request(self, event_type: str, **kwargs) -> None:
        """Log API request events."""
        data = {
            "type": event_type,
            "request_id": self.request_id,
            **kwargs
        }
        write_log(API_REQUESTS_LOG, data)

    def log_web_search(self, search_num: int, query: str, duration_ms: float, **kwargs) -> None:
        """Log web search operation."""
        data = {
            "type": "web_search",
            "request_id": self.request_id,
            "search_num": search_num,
            "query": query,
            "duration_ms": duration_ms,
            **kwargs
        }
        write_log(WEB_SEARCH_LOG, data)

    def log_analysis_request(self, **kwargs) -> None:
        """Log analysis request input data."""
        data = {
            "type": "analysis_request",
            "request_id": self.request_id,
            **kwargs
        }
        write_log(ANALYSIS_REQUESTS_LOG, data)

    def log_analysis_result(self, image_index: int, result: Dict[str, Any], raw_response: Optional[str] = None, extraction_strategy: Optional[str] = None) -> None:
        """Log complete analysis result for a single image.

        Args:
            image_index: Image number (1-indexed)
            result: Parsed analysis result dictionary
            raw_response: Raw Claude API response text (before JSON extraction)
            extraction_strategy: Strategy used to extract JSON (e.g., 'json_code_block', 'brace_counting', 'no_extraction_needed')
        """
        data = {
            "type": "analysis_result",
            "request_id": self.request_id,
            "image_index": image_index,
            "result": result
        }

        # Add optional debugging information
        if raw_response is not None:
            data["raw_response"] = raw_response
            data["raw_response_length"] = len(raw_response)

        if extraction_strategy is not None:
            data["extraction_strategy"] = extraction_strategy

        write_log(ANALYSIS_RESULTS_LOG, data)

    def log_pricing_result(self, result: Dict[str, Any]) -> None:
        """Log complete pricing research result."""
        data = {
            "type": "pricing_result",
            "request_id": self.request_id,
            "result": result
        }
        write_log(PRICING_RESULTS_LOG, data)

    def log_request_status(self, status: str, error: Optional[Dict[str, Any]] = None) -> None:
        """Log final request status and outcome.

        Args:
            status: 'success' or 'error'
            error: Error details dict with keys: type, message, details, traceback (only for error status)
        """
        data = {
            "request_id": self.request_id,
            "status": status
        }

        if error:
            data["error"] = error

        write_log(REQUEST_STATUS_LOG, data)

    @contextmanager
    def track_operation(self, operation_name: str, **metadata):
        """Context manager to track operation timing."""
        start = time.time()
        self.log_event(f"{operation_name}_start", **metadata)

        try:
            yield
        finally:
            duration_ms = (time.time() - start) * 1000
            self.log_event(
                f"{operation_name}_complete",
                duration_ms=duration_ms,
                **metadata
            )

    def get_elapsed_ms(self) -> float:
        """Get elapsed time since tracker creation."""
        return (time.time() - self.start_time) * 1000


# Simple timer context manager
@contextmanager
def timer(label: str):
    """Simple timer that returns duration."""
    start = time.time()
    duration = {"ms": 0}

    try:
        yield duration
    finally:
        duration["ms"] = (time.time() - start) * 1000
        print(f"⏱️  {label}: {duration['ms']:.2f}ms")
