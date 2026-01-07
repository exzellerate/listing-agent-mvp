"""
eBay Category Matcher Service

Matches product information to the most appropriate eBay category using
local category data and intelligent matching algorithms.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from rapidfuzz import fuzz, process


class CategoryMatch:
    """Represents a category match with confidence score."""

    def __init__(self, category_id: str, category_name: str, path: str,
                 score: float, level: int, is_leaf: bool):
        self.category_id = category_id
        self.category_name = category_name
        self.path = path
        self.score = score
        self.level = level
        self.is_leaf = is_leaf

    def to_dict(self) -> Dict:
        return {
            "category_id": self.category_id,
            "category_name": self.category_name,
            "path": self.path,
            "score": self.score,
            "level": self.level,
            "is_leaf": self.is_leaf
        }

    def __repr__(self):
        return f"CategoryMatch(id={self.category_id}, name={self.category_name}, score={self.score:.1f})"


class EbayCategoryMatcher:
    """Matches products to eBay categories using local taxonomy data."""

    def __init__(self, categories_file: str = "data/categories/ebay_categories_0_flat.json"):
        """
        Initialize matcher with category data.

        Args:
            categories_file: Path to flat categories JSON file
        """
        self.categories_file = Path(categories_file)
        self.categories: List[Dict] = []
        self.category_by_id: Dict[str, Dict] = {}

        self._load_categories()

    def _load_categories(self):
        """Load categories from JSON file."""
        if not self.categories_file.exists():
            raise FileNotFoundError(
                f"Categories file not found: {self.categories_file}\n"
                f"Run fetch_ebay_categories.py first to download category data."
            )

        with open(self.categories_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.categories = data.get("categories", [])

        # Build lookup dictionary
        self.category_by_id = {
            cat["category_id"]: cat for cat in self.categories
        }

        print(f"✅ Loaded {len(self.categories)} categories from {self.categories_file.name}")

    def find_by_keywords(self,
                        product_name: str,
                        brand: Optional[str] = None,
                        product_type: Optional[str] = None,
                        top_n: int = 10,
                        min_score: float = 60.0,
                        prefer_leaf: bool = True) -> List[CategoryMatch]:
        """
        Find matching categories by keywords using fuzzy matching.

        Args:
            product_name: Name of the product
            brand: Brand name (optional)
            product_type: Product type/category hint (optional)
            top_n: Number of top matches to return
            min_score: Minimum fuzzy match score (0-100)
            prefer_leaf: Prefer leaf categories (most specific)

        Returns:
            List of CategoryMatch objects sorted by score
        """
        # Build search query
        search_parts = [product_name]
        if brand:
            search_parts.append(brand)
        if product_type:
            search_parts.append(product_type)

        search_query = " ".join(search_parts).lower()

        # Prepare category strings for matching
        category_strings = []
        for cat in self.categories:
            # Weight leaf categories higher if preferred
            if prefer_leaf and not cat.get("is_leaf", False):
                continue

            # Create searchable string from category path
            searchable = cat["path"].lower()
            category_strings.append((searchable, cat))

        # Use fuzzy matching to find best matches
        matches = process.extract(
            search_query,
            [cs[0] for cs in category_strings],
            scorer=fuzz.token_sort_ratio,
            limit=top_n * 2  # Get more candidates to filter
        )

        # Convert to CategoryMatch objects
        results = []
        for match_text, score, idx in matches:
            if score < min_score:
                continue

            cat = category_strings[idx][1]

            results.append(CategoryMatch(
                category_id=cat["category_id"],
                category_name=cat["category_name"],
                path=cat["path"],
                score=score,
                level=cat["level"],
                is_leaf=cat.get("is_leaf", False)
            ))

        # Sort by score (descending) and level (descending for specificity)
        results.sort(key=lambda x: (x.score, x.level), reverse=True)

        return results[:top_n]

    def find_by_product_info(self,
                            product_info: Dict,
                            top_n: int = 5) -> List[CategoryMatch]:
        """
        Find matching categories from product analysis results.

        Args:
            product_info: Dictionary with product_name, brand, etc.
            top_n: Number of top matches to return

        Returns:
            List of CategoryMatch objects
        """
        product_name = product_info.get("product_name", "")
        brand = product_info.get("brand", "")

        # Try to infer product type from title or description
        product_type = None
        title = product_info.get("title", "")
        description = product_info.get("description", "")

        # Extract potential category hints from title/description
        category_hints = []
        common_types = [
            "vacuum", "shoes", "helmet", "golf", "balls", "headphones",
            "airpods", "cooker", "reader", "kindle", "lego", "controller",
            "gaming", "electronics", "clothing", "toys", "sports"
        ]

        for hint in common_types:
            if hint in title.lower() or hint in description.lower() or hint in product_name.lower():
                category_hints.append(hint)

        if category_hints:
            product_type = " ".join(category_hints)

        return self.find_by_keywords(
            product_name=product_name,
            brand=brand,
            product_type=product_type,
            top_n=top_n,
            min_score=50.0,  # Lower threshold for automated matching
            prefer_leaf=True
        )

    def get_category_by_id(self, category_id: str) -> Optional[Dict]:
        """Get category details by ID."""
        return self.category_by_id.get(category_id)

    def get_category_path(self, category_id: str) -> Optional[str]:
        """Get full category path for a category ID."""
        cat = self.get_category_by_id(category_id)
        return cat.get("path") if cat else None

    def suggest_similar_categories(self, category_id: str, top_n: int = 5) -> List[CategoryMatch]:
        """
        Suggest similar categories based on a given category ID.

        Args:
            category_id: The reference category ID
            top_n: Number of suggestions to return

        Returns:
            List of similar CategoryMatch objects
        """
        ref_cat = self.get_category_by_id(category_id)
        if not ref_cat:
            return []

        ref_path = ref_cat["path"]
        ref_level = ref_cat["level"]

        # Find categories with similar paths or same parent
        candidates = []
        for cat in self.categories:
            if cat["category_id"] == category_id:
                continue

            # Calculate similarity based on path overlap
            score = fuzz.token_sort_ratio(ref_path, cat["path"])

            # Boost score for categories at similar levels
            if abs(cat["level"] - ref_level) <= 1:
                score += 10

            if score > 50:
                candidates.append(CategoryMatch(
                    category_id=cat["category_id"],
                    category_name=cat["category_name"],
                    path=cat["path"],
                    score=score,
                    level=cat["level"],
                    is_leaf=cat.get("is_leaf", False)
                ))

        # Sort by score and return top N
        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates[:top_n]

    def validate_category(self, category_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if a category ID exists and is suitable for listing.

        Args:
            category_id: Category ID to validate

        Returns:
            Tuple of (is_valid, message)
        """
        cat = self.get_category_by_id(category_id)

        if not cat:
            return False, f"Category ID {category_id} not found"

        if not cat.get("is_leaf", False):
            return False, f"Category '{cat['category_name']}' is not a leaf category. You must select a more specific subcategory."

        return True, None

    def get_statistics(self) -> Dict:
        """Get statistics about loaded categories."""
        leaf_count = sum(1 for cat in self.categories if cat.get("is_leaf", False))
        max_level = max(cat["level"] for cat in self.categories) if self.categories else 0

        return {
            "total_categories": len(self.categories),
            "leaf_categories": leaf_count,
            "parent_categories": len(self.categories) - leaf_count,
            "max_depth": max_level,
            "data_file": str(self.categories_file)
        }
