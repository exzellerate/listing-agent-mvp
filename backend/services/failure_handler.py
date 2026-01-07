"""
Failure Handler Service

Manages retry logic, failure categorization, and recovery suggestions
for eBay listing failures.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session

from database_models import EbayListing, EbayListingFailure, ListingStatus, FailureStage

logger = logging.getLogger(__name__)


# Error categories
TRANSIENT_ERRORS = [
    'RATE_LIMIT_EXCEEDED',
    'SERVICE_UNAVAILABLE',
    'TIMEOUT',
    'NETWORK_ERROR',
    'INTERNAL_ERROR',
    'GATEWAY_TIMEOUT',
]

PERMANENT_ERRORS = [
    'INVALID_TOKEN',
    'INVALID_CREDENTIALS',
    'INVALID_DATA',
    'DUPLICATE_SKU',
    'INVALID_CATEGORY',
    'POLICY_VIOLATION',
    'PROHIBITED_ITEM',
    'ACCOUNT_SUSPENDED',
]

RECOVERABLE_ERRORS = [
    'IMAGE_TOO_LARGE',
    'INVALID_IMAGE_FORMAT',
    'MISSING_REQUIRED_FIELD',
    'INVALID_PRICE',
    'INVALID_QUANTITY',
    'MISSING_CATEGORY',
    'MISSING_POLICY',
    'TITLE_TOO_LONG',
]


class FailureHandlerService:
    """
    Handles failure tracking, retry logic, and recovery suggestions.

    Features:
    - Classify errors (transient, permanent, recoverable)
    - Determine retry eligibility
    - Generate recovery suggestions
    - Track failure patterns
    """

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAYS = [60, 300, 900, 3600]  # 1min, 5min, 15min, 1hour (in seconds)

    def __init__(self, db: Session):
        """
        Initialize failure handler.

        Args:
            db: Database session
        """
        self.db = db

    def should_retry(self, listing_id: int) -> Tuple[bool, str]:
        """
        Check if a listing should be retried.

        Args:
            listing_id: Listing ID

        Returns:
            Tuple of (should_retry, reason)

        Example:
            >>> should, reason = handler.should_retry(123)
            >>> if should:
            ...     handler.schedule_retry(123)
        """
        listing = self.db.query(EbayListing).filter(EbayListing.id == listing_id).first()

        if not listing:
            return False, "Listing not found"

        if listing.status != ListingStatus.FAILED:
            return False, f"Listing is not in failed status (current: {listing.status})"

        if listing.retry_count >= listing.max_retries:
            return False, f"Maximum retries exceeded ({listing.retry_count}/{listing.max_retries})"

        # Check if error is retryable
        if listing.last_error_code:
            if self._is_permanent_error(listing.last_error_code):
                return False, "Error is permanent and cannot be retried"

        # Check if enough time has passed since last retry
        if listing.last_retry_at:
            retry_delay = self._get_retry_delay(listing.retry_count)
            next_retry_time = listing.last_retry_at + timedelta(seconds=retry_delay)
            now = datetime.utcnow()

            if now < next_retry_time:
                wait_seconds = int((next_retry_time - now).total_seconds())
                return False, f"Must wait {wait_seconds} seconds before retrying"

        return True, "Listing is eligible for retry"

    def classify_error(self, error_code: str) -> str:
        """
        Classify error type.

        Args:
            error_code: Error code from eBay

        Returns:
            Error category: 'transient', 'permanent', 'recoverable', or 'unknown'
        """
        error_code_upper = error_code.upper() if error_code else ""

        if any(err in error_code_upper for err in TRANSIENT_ERRORS):
            return "transient"
        elif any(err in error_code_upper for err in PERMANENT_ERRORS):
            return "permanent"
        elif any(err in error_code_upper for err in RECOVERABLE_ERRORS):
            return "recoverable"
        else:
            return "unknown"

    def _is_permanent_error(self, error_code: str) -> bool:
        """Check if error is permanent (not retryable)."""
        return self.classify_error(error_code) == "permanent"

    def _is_transient_error(self, error_code: str) -> bool:
        """Check if error is transient (should retry automatically)."""
        return self.classify_error(error_code) == "transient"

    def _is_recoverable_error(self, error_code: str) -> bool:
        """Check if error is recoverable (user can fix data and retry)."""
        return self.classify_error(error_code) == "recoverable"

    def _get_retry_delay(self, retry_count: int) -> int:
        """
        Get retry delay in seconds based on retry count.

        Implements exponential backoff.

        Args:
            retry_count: Current retry count

        Returns:
            Delay in seconds
        """
        if retry_count < len(self.RETRY_DELAYS):
            return self.RETRY_DELAYS[retry_count]
        return self.RETRY_DELAYS[-1]  # Use max delay

    def get_recovery_suggestion(self, error_code: Optional[str], error_message: Optional[str]) -> str:
        """
        Generate user-friendly recovery suggestion based on error.

        Args:
            error_code: Error code from eBay
            error_message: Error message

        Returns:
            Recovery suggestion text
        """
        if not error_code:
            return "An unknown error occurred. Please try again or contact support."

        error_code_upper = error_code.upper()

        # Specific suggestions based on error type
        suggestions = {
            'RATE_LIMIT_EXCEEDED': "You've made too many requests. Please wait a few minutes and try again.",
            'SERVICE_UNAVAILABLE': "eBay's servers are temporarily unavailable. Please try again in a few minutes.",
            'TIMEOUT': "The request timed out. Please check your internet connection and try again.",
            'INVALID_TOKEN': "Your eBay authentication has expired. Please reconnect your eBay account.",
            'INVALID_CREDENTIALS': "Your eBay credentials are invalid. Please reconnect your eBay account.",
            'INVALID_DATA': "Some listing data is invalid. Please review and correct the listing details.",
            'DUPLICATE_SKU': "This SKU already exists. The listing will be automatically retried with a new SKU.",
            'INVALID_CATEGORY': "The selected category is not valid for this product. Please choose a different category.",
            'POLICY_VIOLATION': "This listing violates eBay policies. Please review eBay's listing policies and modify the listing.",
            'PROHIBITED_ITEM': "This item cannot be listed on eBay. It may be prohibited or restricted.",
            'IMAGE_TOO_LARGE': "One or more images are too large. Please reduce image file sizes to under 12MB.",
            'INVALID_IMAGE_FORMAT': "Image format not supported. Please use JPEG, PNG, or GIF format.",
            'MISSING_REQUIRED_FIELD': "Required listing information is missing. Please complete all required fields.",
            'INVALID_PRICE': "The price is invalid. Please check that the price is reasonable and properly formatted.",
            'INVALID_QUANTITY': "The quantity is invalid. Please set a valid quantity (1 or more).",
            'MISSING_CATEGORY': "A category must be selected. Please choose an appropriate eBay category.",
            'MISSING_POLICY': "Business policies are required. Please set up shipping, return, and payment policies in your eBay account.",
            'TITLE_TOO_LONG': "The title is too long. eBay titles must be 80 characters or less.",
            'ACCOUNT_SUSPENDED': "Your eBay seller account is suspended. Please contact eBay to resolve this issue.",
        }

        # Find matching suggestion
        for key, suggestion in suggestions.items():
            if key in error_code_upper:
                return suggestion

        # Classify and provide generic suggestion
        error_type = self.classify_error(error_code)

        if error_type == "transient":
            return "This is a temporary error. The listing will be automatically retried."
        elif error_type == "permanent":
            return "This error cannot be automatically resolved. Please review the error details and contact support if needed."
        elif error_type == "recoverable":
            return "Please review and correct the listing data, then try again."
        else:
            return f"An error occurred: {error_message or error_code}. Please try again or contact support."

    def get_failure_summary(self, listing_id: int) -> Dict:
        """
        Get summary of all failures for a listing.

        Args:
            listing_id: Listing ID

        Returns:
            Dict with failure summary

        Example:
            >>> summary = handler.get_failure_summary(123)
            >>> print(f"Failed {summary['total_failures']} times")
        """
        failures = self.db.query(EbayListingFailure).filter(
            EbayListingFailure.listing_id == listing_id
        ).order_by(EbayListingFailure.occurred_at.desc()).all()

        if not failures:
            return {
                "total_failures": 0,
                "failures": []
            }

        return {
            "total_failures": len(failures),
            "most_recent_failure": {
                "stage": failures[0].failure_stage.value,
                "error_code": failures[0].error_code,
                "error_message": failures[0].error_message,
                "occurred_at": failures[0].occurred_at.isoformat(),
                "is_recoverable": bool(failures[0].is_recoverable),
                "suggestion": failures[0].recovery_suggestion or self.get_recovery_suggestion(
                    failures[0].error_code,
                    failures[0].error_message
                )
            },
            "failures": [
                {
                    "stage": f.failure_stage.value,
                    "error_code": f.error_code,
                    "occurred_at": f.occurred_at.isoformat()
                }
                for f in failures
            ]
        }

    def get_failure_statistics(self) -> Dict:
        """
        Get overall failure statistics.

        Returns:
            Dict with failure statistics

        Example:
            >>> stats = handler.get_failure_statistics()
            >>> print(f"Success rate: {stats['success_rate']}%")
        """
        # Total listings
        total_listings = self.db.query(EbayListing).count()

        # Published listings
        published = self.db.query(EbayListing).filter(
            EbayListing.status == ListingStatus.PUBLISHED
        ).count()

        # Failed listings
        failed = self.db.query(EbayListing).filter(
            EbayListing.status == ListingStatus.FAILED
        ).count()

        # In progress
        in_progress = self.db.query(EbayListing).filter(
            EbayListing.status.in_([
                ListingStatus.VALIDATING,
                ListingStatus.UPLOADING_IMAGES,
                ListingStatus.CREATING_INVENTORY,
                ListingStatus.CREATING_OFFER,
                ListingStatus.PUBLISHING
            ])
        ).count()

        # Calculate success rate
        success_rate = (published / total_listings * 100) if total_listings > 0 else 0

        # Get common failure stages
        failure_stages = self.db.query(
            EbayListingFailure.failure_stage,
            self.db.func.count(EbayListingFailure.id)
        ).group_by(EbayListingFailure.failure_stage).all()

        return {
            "total_listings": total_listings,
            "published": published,
            "failed": failed,
            "in_progress": in_progress,
            "success_rate": round(success_rate, 2),
            "common_failure_stages": [
                {"stage": stage.value, "count": count}
                for stage, count in failure_stages
            ]
        }

    def schedule_retry(self, listing_id: int) -> Dict:
        """
        Schedule a listing for retry.

        Args:
            listing_id: Listing ID

        Returns:
            Dict with retry information

        Example:
            >>> result = handler.schedule_retry(123)
            >>> print(f"Next retry at: {result['next_retry_at']}")
        """
        should_retry, reason = self.should_retry(listing_id)

        if not should_retry:
            return {
                "scheduled": False,
                "reason": reason
            }

        listing = self.db.query(EbayListing).filter(EbayListing.id == listing_id).first()

        # Calculate next retry time
        retry_delay = self._get_retry_delay(listing.retry_count)
        next_retry_at = datetime.utcnow() + timedelta(seconds=retry_delay)

        logger.info(
            f"Scheduling retry for listing {listing_id} "
            f"(attempt {listing.retry_count + 1}/{listing.max_retries}) "
            f"at {next_retry_at}"
        )

        return {
            "scheduled": True,
            "retry_count": listing.retry_count,
            "max_retries": listing.max_retries,
            "next_retry_at": next_retry_at.isoformat(),
            "retry_delay_seconds": retry_delay,
            "reason": "Listing scheduled for automatic retry"
        }


# Helper function to get failure handler instance
def get_failure_handler(db: Session) -> FailureHandlerService:
    """
    Factory function to create FailureHandlerService instance.

    Args:
        db: Database session

    Returns:
        Configured FailureHandlerService instance
    """
    return FailureHandlerService(db)
