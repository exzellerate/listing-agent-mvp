"""
eBay Category Recommendation Service

Uses AI to intelligently recommend the best eBay categories for a product
based on product attributes and search results from eBay's Taxonomy API.
"""

import logging
from typing import List, Dict, Any, Optional
from services.ebay.taxonomy import EbayTaxonomyService

logger = logging.getLogger(__name__)


class CategoryRecommender:
    """
    Recommends the best eBay category for a product using AI analysis.

    Features:
    - Searches all AI-suggested keywords in parallel
    - Scores categories based on relevance and specificity
    - Returns ranked recommendations with confidence scores
    """

    def __init__(self, taxonomy_service: EbayTaxonomyService):
        """
        Initialize recommender with taxonomy service.

        Args:
            taxonomy_service: eBay taxonomy service instance
        """
        self.taxonomy_service = taxonomy_service

    def recommend_categories(
        self,
        product_name: str,
        brand: Optional[str],
        category_keywords: List[str],
        product_category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Recommend best eBay categories for a product.

        Args:
            product_name: Product name from AI analysis
            brand: Product brand (if available)
            category_keywords: AI-suggested keywords for category search
            product_category: General category from AI (optional)

        Returns:
            List of category recommendations with confidence scores, sorted by relevance

        Example:
            >>> recommender.recommend_categories(
            ...     product_name="Apple AirPods Pro",
            ...     brand="Apple",
            ...     category_keywords=["wireless earbuds", "apple airpods", "bluetooth headphones"]
            ... )
            [
                {
                    'category_id': '112529',
                    'category_name': 'Headphones',
                    'category_path': 'Consumer Electronics > Portable Audio > Headphones',
                    'leaf_category': True,
                    'confidence': 0.95,
                    'match_reason': 'Exact product match',
                    'recommended': True
                },
                ...
            ]
        """
        logger.info(f"Recommending categories for: {product_name}")

        # Collect all unique categories from searches
        all_categories = {}

        # Search using each keyword
        for keyword in category_keywords:
            logger.info(f"Searching with keyword: {keyword}")
            try:
                categories = self.taxonomy_service.search_categories(keyword)

                # Store categories with their search context
                for cat in categories:
                    cat_id = cat['category_id']
                    if cat_id not in all_categories:
                        all_categories[cat_id] = {
                            **cat,
                            'matched_keywords': [keyword],
                            'search_rank': len(all_categories)  # Track discovery order
                        }
                    else:
                        # Category found with multiple keywords - increase relevance
                        all_categories[cat_id]['matched_keywords'].append(keyword)

            except Exception as e:
                logger.warning(f"Search failed for keyword '{keyword}': {e}")
                continue

        if not all_categories:
            logger.warning("No categories found for any keywords")
            return []

        # Score and rank categories
        scored_categories = []
        for cat_id, cat in all_categories.items():
            score = self._score_category(
                category=cat,
                product_name=product_name,
                brand=brand,
                product_category=product_category,
                all_keywords=category_keywords
            )

            scored_categories.append({
                'category_id': cat['category_id'],
                'category_name': cat['category_name'],
                'category_path': cat['category_path'],
                'leaf_category': cat['leaf_category'],
                'confidence': score['confidence'],
                'match_reason': score['reason'],
                'recommended': False  # Will mark top choice as recommended
            })

        # Sort by confidence (descending)
        scored_categories.sort(key=lambda x: x['confidence'], reverse=True)

        # Mark the top choice as recommended (if it's a leaf category)
        for cat in scored_categories:
            if cat['leaf_category'] and cat['confidence'] >= 0.5:
                cat['recommended'] = True
                break

        # Filter out non-leaf categories with low confidence
        filtered_categories = [
            cat for cat in scored_categories
            if cat['leaf_category'] or cat['confidence'] >= 0.7
        ]

        logger.info(f"Recommended {len(filtered_categories)} categories (top confidence: {filtered_categories[0]['confidence']:.2f})" if filtered_categories else "No suitable categories found")

        return filtered_categories[:10]  # Return top 10

    def _score_category(
        self,
        category: Dict[str, Any],
        product_name: str,
        brand: Optional[str],
        product_category: Optional[str],
        all_keywords: List[str]
    ) -> Dict[str, Any]:
        """
        Score a category's relevance to the product.

        Returns:
            Dict with 'confidence' (0-1) and 'reason' explaining the score
        """
        score = 0.0
        reasons = []

        cat_name = category['category_name'].lower()
        cat_path = category['category_path'].lower()
        matched_keywords = category.get('matched_keywords', [])

        # Base scoring factors

        # 1. Leaf category bonus (required for listing)
        if category['leaf_category']:
            score += 0.3
            reasons.append("Leaf category")

        # 2. Multiple keyword matches (strong signal)
        keyword_match_ratio = len(matched_keywords) / max(len(all_keywords), 1)
        if keyword_match_ratio >= 0.5:
            score += 0.3
            reasons.append(f"Matched {len(matched_keywords)}/{len(all_keywords)} keywords")
        elif keyword_match_ratio > 0:
            score += 0.15

        # 3. Brand presence in category path
        if brand and brand.lower() in cat_path:
            score += 0.2
            reasons.append(f"Brand-specific category")

        # 4. Product name terms in category
        product_terms = set(product_name.lower().split())
        cat_terms = set(cat_path.split(' > ')[-1].lower().split())  # Last part of path

        common_terms = product_terms & cat_terms
        if common_terms:
            score += 0.2
            reasons.append(f"Product match: {', '.join(common_terms)}")

        # 5. Specificity bonus (deeper in hierarchy = more specific)
        path_depth = len(category['category_path'].split(' > '))
        if path_depth >= 3:
            score += 0.1
            reasons.append("Specific category")

        # 6. First search result bonus (eBay's ranking)
        if category.get('search_rank', 999) == 0:
            score += 0.1
            reasons.append("Top eBay result")

        # Normalize score to 0-1 range
        confidence = min(score, 1.0)

        # Determine primary reason
        if not reasons:
            primary_reason = "General match"
        elif confidence >= 0.8:
            primary_reason = "Excellent match"
        elif confidence >= 0.6:
            primary_reason = "Good match"
        else:
            primary_reason = "Possible match"

        return {
            'confidence': round(confidence, 2),
            'reason': primary_reason
        }


def get_category_recommender(taxonomy_service: EbayTaxonomyService) -> CategoryRecommender:
    """
    Factory function to create CategoryRecommender instance.

    Args:
        taxonomy_service: Configured taxonomy service

    Returns:
        CategoryRecommender instance
    """
    return CategoryRecommender(taxonomy_service)
