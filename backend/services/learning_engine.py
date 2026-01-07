"""
Learning Engine Service

Core intelligence of the learning system:
- Aggregates product_analyses into learned_products
- Calculates confidence scores
- Matches new images to learned products
- Manages API call optimization
"""

import logging
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from database_models import (
    ProductAnalysis, LearnedProduct, LearningStats,
    UserAction, AnalysisSource
)
from utils.image_hash import compare_hashes, THRESHOLD_VERY_SIMILAR

logger = logging.getLogger(__name__)


class LearningEngine:
    """Learning engine for the listing agent."""

    # Configuration
    MIN_ANALYSES_FOR_LEARNING = 3  # Minimum analyses before creating learned product
    CONFIDENCE_THRESHOLD_HIGH = 0.7  # Skip API, use learned data
    CONFIDENCE_THRESHOLD_MED = 0.3   # Hybrid mode, verify with API
    AGGREGATION_TRIGGER = 10         # Auto-aggregate every N confirmations
    IMAGE_SIMILARITY_THRESHOLD = 5   # Hamming distance for image matching

    def __init__(self, db: Session):
        """Initialize learning engine with database session."""
        self.db = db

    def find_similar_learned_product(
        self,
        image_hash: str,
        platform: Optional[str] = None
    ) -> Optional[Tuple[LearnedProduct, float, int]]:
        """
        Find a learned product that matches the given image hash.

        Args:
            image_hash: Perceptual hash of the image
            platform: Optional platform filter

        Returns:
            Tuple of (LearnedProduct, confidence_score, hamming_distance) or None
        """
        # Get all learned products
        query = self.db.query(LearnedProduct)

        # Filter by platform if specified
        if platform:
            query = query.filter(LearnedProduct.platform == platform)

        learned_products = query.all()

        best_match = None
        best_distance = float('inf')
        best_product = None

        for product in learned_products:
            # Get reference hashes (stored as JSON list)
            reference_hashes = product.reference_image_hashes or []

            # Compare with all reference hashes
            for ref_hash in reference_hashes:
                try:
                    distance = compare_hashes(image_hash, ref_hash)

                    if distance <= self.IMAGE_SIMILARITY_THRESHOLD and distance < best_distance:
                        best_distance = distance
                        best_product = product
                        best_match = (product, product.confidence_score, distance)

                except Exception as e:
                    logger.warning(f"Hash comparison failed: {e}")
                    continue

        if best_match:
            logger.info(
                f"Found similar product: {best_product.product_name} "
                f"(confidence: {best_product.confidence_score:.2f}, distance: {best_distance})"
            )

        return best_match

    def calculate_confidence_score(
        self,
        times_analyzed: int,
        times_accepted: int,
        times_edited: int,
        times_corrected: int,
        times_rejected: int,
        last_seen: datetime
    ) -> float:
        """
        Calculate confidence score for a learned product.

        Factors:
        1. Acceptance rate (most important)
        2. Volume (more samples = higher confidence)
        3. Recency (decay for old data)

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if times_analyzed == 0:
            return 0.0

        # 1. Calculate acceptance rate with weighted actions
        # accepted = 1.0, edited = 0.8, corrected = -2.0, rejected = -1.0
        weighted_score = (
            (times_accepted * 1.0) +
            (times_edited * 0.8) +
            (times_corrected * -2.0) +
            (times_rejected * -1.0)
        )

        acceptance_rate = weighted_score / times_analyzed

        # Normalize to 0-1 range (clamp negative values)
        acceptance_rate = max(0.0, min(1.0, acceptance_rate))

        # 2. Volume factor (more samples = higher confidence)
        # Use logarithmic scale to prevent runaway confidence
        volume_factor = min(1.0, times_analyzed / 10.0)

        # 3. Recency factor (decay over time)
        days_since_last_seen = (datetime.utcnow() - last_seen).days
        recency_factor = 1.0

        if days_since_last_seen > 30:
            # Decay 10% per month after 30 days
            months_old = (days_since_last_seen - 30) / 30.0
            recency_factor = max(0.5, 1.0 - (months_old * 0.1))

        # Combine factors
        # Acceptance rate: 70%, Volume: 20%, Recency: 10%
        confidence = (
            acceptance_rate * 0.7 +
            volume_factor * 0.2 +
            recency_factor * 0.1
        )

        return min(1.0, max(0.0, confidence))

    def aggregate_product_analyses(
        self,
        product_identifier: Optional[str] = None,
        force: bool = False
    ) -> List[LearnedProduct]:
        """
        Aggregate product_analyses into learned_products.

        Args:
            product_identifier: Optional specific product to aggregate
            force: Force aggregation even if below threshold

        Returns:
            List of created/updated LearnedProduct objects
        """
        logger.info("Starting aggregation of product analyses...")

        updated_products = []

        # Group analyses by product (name + brand + model)
        # Only consider accepted, edited, or corrected analyses
        query = self.db.query(ProductAnalysis).filter(
            ProductAnalysis.user_action.in_([
                UserAction.ACCEPTED,
                UserAction.EDITED,
                UserAction.CORRECTED
            ])
        )

        if product_identifier:
            query = query.filter(ProductAnalysis.product_identifier == product_identifier)

        analyses = query.all()

        # Group by product identifier
        products_map: Dict[str, List[ProductAnalysis]] = {}

        for analysis in analyses:
            # Generate product identifier if not set
            if not analysis.product_identifier:
                identifier = self._generate_product_identifier(
                    analysis.ai_product_name,
                    analysis.ai_brand,
                    analysis.ai_model_number
                )
                analysis.product_identifier = identifier
                self.db.commit()
            else:
                identifier = analysis.product_identifier

            if identifier not in products_map:
                products_map[identifier] = []

            products_map[identifier].append(analysis)

        # Process each product group
        for identifier, product_analyses in products_map.items():
            # Skip if below minimum threshold (unless forced)
            if not force and len(product_analyses) < self.MIN_ANALYSES_FOR_LEARNING:
                logger.debug(
                    f"Skipping {identifier}: only {len(product_analyses)} analyses "
                    f"(minimum: {self.MIN_ANALYSES_FOR_LEARNING})"
                )
                continue

            # Find or create learned product
            learned_product = self.db.query(LearnedProduct).filter(
                LearnedProduct.product_identifier == identifier
            ).first()

            if not learned_product:
                learned_product = LearnedProduct(
                    product_identifier=identifier,
                    created_at=datetime.utcnow()
                )
                self.db.add(learned_product)
                logger.info(f"Creating new learned product: {identifier}")

            # Aggregate data from analyses
            self._aggregate_product_data(learned_product, product_analyses)

            updated_products.append(learned_product)

        # Commit all changes
        self.db.commit()

        logger.info(f"Aggregation complete: {len(updated_products)} products updated")
        return updated_products

    def _generate_product_identifier(
        self,
        product_name: Optional[str],
        brand: Optional[str],
        model_number: Optional[str]
    ) -> str:
        """Generate normalized product identifier."""
        parts = []

        if brand:
            parts.append(brand.lower().strip())
        if product_name:
            parts.append(product_name.lower().strip())
        if model_number:
            parts.append(model_number.lower().strip())

        return "_".join(parts) if parts else "unknown_product"

    def _aggregate_product_data(
        self,
        learned_product: LearnedProduct,
        analyses: List[ProductAnalysis]
    ) -> None:
        """
        Aggregate data from multiple analyses into a learned product.

        Updates:
        - Basic product info (name, brand, category, etc.)
        - Best title and description
        - Typical price range
        - Common features
        - Confidence metrics
        - Reference image hashes
        """
        # Count user actions
        times_accepted = sum(1 for a in analyses if a.user_action == UserAction.ACCEPTED)
        times_edited = sum(1 for a in analyses if a.user_action == UserAction.EDITED)
        times_corrected = sum(1 for a in analyses if a.user_action == UserAction.CORRECTED)
        times_rejected = sum(1 for a in analyses if a.user_action == UserAction.REJECTED)

        # Update counts
        learned_product.times_analyzed = len(analyses)
        learned_product.times_accepted = times_accepted
        learned_product.times_edited = times_edited
        learned_product.times_corrected = times_corrected
        learned_product.times_rejected = times_rejected

        # Calculate acceptance rate
        total_feedback = times_accepted + times_edited + times_corrected + times_rejected
        if total_feedback > 0:
            learned_product.acceptance_rate = (times_accepted + times_edited) / total_feedback
        else:
            learned_product.acceptance_rate = 0.0

        # Get most recent analysis
        latest_analysis = max(analyses, key=lambda a: a.created_at)
        learned_product.last_seen = latest_analysis.created_at

        # Update basic product info (use user-corrected data if available, else AI data)
        learned_product.product_name = self._get_most_common_value(
            analyses,
            lambda a: a.user_product_name or a.ai_product_name
        )

        learned_product.brand = self._get_most_common_value(
            analyses,
            lambda a: a.user_brand or a.ai_brand
        )

        learned_product.category = self._get_most_common_value(
            analyses,
            lambda a: a.user_category or a.ai_category
        )

        learned_product.model_number = self._get_most_common_value(
            analyses,
            lambda a: a.ai_model_number
        )

        # Platform (use most common or from latest)
        learned_product.platform = self._get_most_common_value(
            analyses,
            lambda a: a.platform
        )

        # Best title (prefer user-edited, then most common AI title)
        learned_product.best_title = self._get_best_title(analyses)

        # Best description (prefer user-edited, then most common AI description)
        learned_product.best_description = self._get_best_description(analyses)

        # Typical price range
        learned_product.typical_price_range = self._calculate_price_range(analyses)

        # Common features
        learned_product.common_features = self._extract_common_features(analyses)

        # Typical attributes
        learned_product.typical_condition = self._get_most_common_value(
            analyses,
            lambda a: a.ai_condition
        )

        learned_product.typical_color = self._get_most_common_value(
            analyses,
            lambda a: a.ai_color
        )

        learned_product.typical_material = self._get_most_common_value(
            analyses,
            lambda a: a.ai_material
        )

        # Collect reference image hashes (unique hashes only)
        image_hashes = list(set(a.image_hash for a in analyses if a.image_hash))
        learned_product.reference_image_hashes = image_hashes

        # Calculate confidence score
        learned_product.confidence_score = self.calculate_confidence_score(
            times_analyzed=learned_product.times_analyzed,
            times_accepted=times_accepted,
            times_edited=times_edited,
            times_corrected=times_corrected,
            times_rejected=times_rejected,
            last_seen=learned_product.last_seen
        )

        learned_product.last_updated = datetime.utcnow()

        logger.info(
            f"Updated {learned_product.product_name}: "
            f"{learned_product.times_analyzed} analyses, "
            f"confidence: {learned_product.confidence_score:.2f}"
        )

    def _get_most_common_value(
        self,
        analyses: List[ProductAnalysis],
        getter: callable
    ) -> Optional[str]:
        """Get most common value from analyses."""
        values = [getter(a) for a in analyses if getter(a)]

        if not values:
            return None

        # Count occurrences
        value_counts = {}
        for value in values:
            value_counts[value] = value_counts.get(value, 0) + 1

        # Return most common
        return max(value_counts, key=value_counts.get)

    def _get_best_title(self, analyses: List[ProductAnalysis]) -> Optional[str]:
        """Get best title from analyses (prefer user-edited)."""
        # Prefer user-edited titles
        user_titles = [a.user_title for a in analyses if a.user_title]
        if user_titles:
            return self._get_most_common_value(analyses, lambda a: a.user_title)

        # Fall back to AI titles
        return self._get_most_common_value(analyses, lambda a: a.ai_title)

    def _get_best_description(self, analyses: List[ProductAnalysis]) -> Optional[str]:
        """Get best description from analyses (prefer user-edited)."""
        # Prefer user-edited descriptions
        user_descriptions = [a.user_description for a in analyses if a.user_description]
        if user_descriptions:
            return self._get_most_common_value(analyses, lambda a: a.user_description)

        # Fall back to AI descriptions
        return self._get_most_common_value(analyses, lambda a: a.ai_description)

    def _calculate_price_range(self, analyses: List[ProductAnalysis]) -> Optional[Dict[str, Any]]:
        """Calculate typical price range from analyses."""
        prices = []

        # Collect user prices
        for analysis in analyses:
            if analysis.user_price:
                prices.append(analysis.user_price)
            elif analysis.ai_price_range:
                # If AI price range exists, use suggested price
                if isinstance(analysis.ai_price_range, dict):
                    if 'suggested' in analysis.ai_price_range:
                        prices.append(analysis.ai_price_range['suggested'])

        if not prices:
            return None

        prices.sort()

        return {
            "min": min(prices),
            "max": max(prices),
            "median": prices[len(prices) // 2],
            "samples": len(prices)
        }

    def _extract_common_features(self, analyses: List[ProductAnalysis]) -> List[str]:
        """Extract common features across analyses."""
        feature_counts = {}

        for analysis in analyses:
            features = analysis.ai_features or []
            for feature in features:
                feature_counts[feature] = feature_counts.get(feature, 0) + 1

        # Return features that appear in at least 50% of analyses
        threshold = len(analyses) * 0.5
        common_features = [
            feature for feature, count in feature_counts.items()
            if count >= threshold
        ]

        return common_features

    def should_use_learned_data(self, confidence_score: float) -> bool:
        """Check if confidence is high enough to skip AI API."""
        return confidence_score >= self.CONFIDENCE_THRESHOLD_HIGH

    def should_use_hybrid_mode(self, confidence_score: float) -> bool:
        """Check if should use hybrid mode (learned + AI verification)."""
        return (
            confidence_score >= self.CONFIDENCE_THRESHOLD_MED and
            confidence_score < self.CONFIDENCE_THRESHOLD_HIGH
        )

    def update_learning_stats(self, date: Optional[datetime] = None) -> LearningStats:
        """
        Update learning statistics for a given date.

        Args:
            date: Date to update stats for (defaults to today)

        Returns:
            Updated LearningStats object
        """
        if date is None:
            date = datetime.utcnow().date()

        # Find or create stats record
        stats = self.db.query(LearningStats).filter(
            func.date(LearningStats.date) == date
        ).first()

        if not stats:
            stats = LearningStats(date=date, created_at=datetime.utcnow())
            self.db.add(stats)

        # Count analyses for today
        start_of_day = datetime.combine(date, datetime.min.time())
        end_of_day = datetime.combine(date, datetime.max.time())

        stats.analyses_today = self.db.query(ProductAnalysis).filter(
            and_(
                ProductAnalysis.created_at >= start_of_day,
                ProductAnalysis.created_at <= end_of_day
            )
        ).count()

        # Count API calls (source = AI_API)
        stats.api_calls_today = self.db.query(ProductAnalysis).filter(
            and_(
                ProductAnalysis.created_at >= start_of_day,
                ProductAnalysis.created_at <= end_of_day,
                ProductAnalysis.source == AnalysisSource.AI_API
            )
        ).count()

        # Count API calls saved (source = LEARNED_DATA)
        stats.api_calls_saved_today = self.db.query(ProductAnalysis).filter(
            and_(
                ProductAnalysis.created_at >= start_of_day,
                ProductAnalysis.created_at <= end_of_day,
                ProductAnalysis.source == AnalysisSource.LEARNED_DATA
            )
        ).count()

        # Calculate cumulative totals
        stats.total_analyses = self.db.query(ProductAnalysis).count()

        stats.total_api_calls = self.db.query(ProductAnalysis).filter(
            ProductAnalysis.source == AnalysisSource.AI_API
        ).count()

        stats.total_api_calls_saved = self.db.query(ProductAnalysis).filter(
            ProductAnalysis.source == AnalysisSource.LEARNED_DATA
        ).count()

        # Calculate acceptance rate (across all confirmed analyses)
        confirmed_analyses = self.db.query(ProductAnalysis).filter(
            ProductAnalysis.user_action.in_([
                UserAction.ACCEPTED,
                UserAction.EDITED,
                UserAction.CORRECTED,
                UserAction.REJECTED
            ])
        ).all()

        if confirmed_analyses:
            accepted = sum(
                1 for a in confirmed_analyses
                if a.user_action in [UserAction.ACCEPTED, UserAction.EDITED]
            )
            stats.acceptance_rate = accepted / len(confirmed_analyses)
        else:
            stats.acceptance_rate = 0.0

        # Calculate average confidence across learned products
        learned_products = self.db.query(LearnedProduct).all()
        if learned_products:
            stats.average_confidence = sum(
                p.confidence_score for p in learned_products
            ) / len(learned_products)
        else:
            stats.average_confidence = 0.0

        # Calculate cost savings
        cost_per_call = 0.01  # $0.01 per API call (adjust as needed)
        stats.estimated_cost_per_api_call = cost_per_call
        stats.estimated_savings_today = stats.api_calls_saved_today * cost_per_call
        stats.estimated_total_savings = stats.total_api_calls_saved * cost_per_call

        stats.updated_at = datetime.utcnow()

        self.db.commit()

        logger.info(
            f"Stats updated for {date}: "
            f"{stats.analyses_today} analyses, "
            f"{stats.api_calls_saved_today} API calls saved, "
            f"${stats.estimated_savings_today:.2f} saved today"
        )

        return stats


def get_learning_engine(db: Session) -> LearningEngine:
    """Get learning engine instance."""
    return LearningEngine(db)
