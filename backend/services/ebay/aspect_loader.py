"""
eBay Item Aspects Loader and Lookup Service

Loads the GZIP-compressed aspects metadata and provides fast lookups
for category-specific aspects/item specifics.
"""

import json
import gzip
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class AspectData:
    """Represents aspect data for a category."""

    def __init__(self, category_id: str, category_name: str, aspects: List[Dict]):
        self.category_id = category_id
        self.category_name = category_name
        self.aspects = aspects

    def get_required_aspects(self) -> List[Dict]:
        """Get only required aspects."""
        return [
            aspect for aspect in self.aspects
            if aspect.get("aspectConstraint", {}).get("aspectRequired", False)
        ]

    def get_recommended_aspects(self) -> List[Dict]:
        """Get recommended (but not required) aspects."""
        return [
            aspect for aspect in self.aspects
            if aspect.get("aspectConstraint", {}).get("aspectUsage") == "RECOMMENDED"
            and not aspect.get("aspectConstraint", {}).get("aspectRequired", False)
        ]

    def get_all_aspects(self) -> List[Dict]:
        """Get all aspects."""
        return self.aspects

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "category_id": self.category_id,
            "category_name": self.category_name,
            "aspects": self.aspects,
            "total_aspects": len(self.aspects),
            "required_count": len(self.get_required_aspects()),
            "recommended_count": len(self.get_recommended_aspects())
        }


class EbayAspectLoader:
    """Loads and provides lookups for eBay item aspects metadata."""

    def __init__(self, aspects_file: str = "services/ebay/data/aspects/aspects_metadata.json"):
        """
        Initialize the aspect loader.

        Args:
            aspects_file: Path to the GZIP-compressed aspects metadata file
        """
        self.aspects_file = Path(aspects_file)
        self.category_aspects: Dict[str, AspectData] = {}
        self.metadata: Dict = {}
        self._loaded = False

    def load(self) -> bool:
        """
        Load aspects metadata from the GZIP-compressed JSON file.

        Returns:
            True if loaded successfully, False otherwise
        """
        if self._loaded:
            logger.info("Aspects already loaded, skipping reload")
            return True

        if not self.aspects_file.exists():
            logger.error(f"Aspects file not found: {self.aspects_file}")
            logger.error("Run fetch_aspects.py --bulk-fetch to download aspects data")
            return False

        try:
            logger.info(f"Loading aspects metadata from {self.aspects_file}")

            # Decompress and load JSON
            with gzip.open(self.aspects_file, 'rt', encoding='utf-8') as f:
                data = json.load(f)

            # Extract metadata
            self.metadata = {
                "categoryTreeId": data.get("categoryTreeId"),
                "categoryTreeVersion": data.get("categoryTreeVersion"),
                "total_categories": len(data.get("categoryAspects", []))
            }

            # Build category index
            category_aspects = data.get("categoryAspects", [])
            for cat_data in category_aspects:
                category = cat_data.get("category", {})
                category_id = category.get("categoryId")
                category_name = category.get("categoryName", "Unknown")
                aspects = cat_data.get("aspects", [])

                if category_id:
                    self.category_aspects[category_id] = AspectData(
                        category_id=category_id,
                        category_name=category_name,
                        aspects=aspects
                    )

            self._loaded = True
            logger.info(f"✅ Loaded aspects for {len(self.category_aspects)} categories")
            logger.info(f"   Tree Version: {self.metadata['categoryTreeVersion']}")

            return True

        except gzip.BadGzipFile:
            logger.error(f"File is not a valid GZIP file: {self.aspects_file}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return False
        except Exception as e:
            logger.error(f"Error loading aspects: {e}")
            return False

    def get_aspects_for_category(self, category_id: str) -> Optional[AspectData]:
        """
        Get aspects for a specific category ID.

        Args:
            category_id: eBay category ID

        Returns:
            AspectData object or None if not found
        """
        if not self._loaded:
            logger.warning("Aspects not loaded, attempting to load now")
            if not self.load():
                return None

        return self.category_aspects.get(category_id)

    def has_aspects(self, category_id: str) -> bool:
        """Check if a category has aspects defined."""
        if not self._loaded:
            self.load()
        return category_id in self.category_aspects

    def get_metadata(self) -> Dict:
        """Get metadata about the loaded aspects."""
        if not self._loaded:
            self.load()
        return self.metadata

    def get_statistics(self) -> Dict:
        """Get statistics about loaded aspects."""
        if not self._loaded:
            self.load()

        total_aspects = sum(
            len(aspect_data.aspects)
            for aspect_data in self.category_aspects.values()
        )

        categories_with_required = sum(
            1 for aspect_data in self.category_aspects.values()
            if len(aspect_data.get_required_aspects()) > 0
        )

        return {
            "total_categories": len(self.category_aspects),
            "total_aspects": total_aspects,
            "categories_with_required_aspects": categories_with_required,
            "average_aspects_per_category": total_aspects / len(self.category_aspects) if self.category_aspects else 0,
            "tree_version": self.metadata.get("categoryTreeVersion", "unknown")
        }


# Singleton instance
_aspect_loader: Optional[EbayAspectLoader] = None


def get_aspect_loader() -> EbayAspectLoader:
    """
    Get the singleton aspect loader instance.

    Returns:
        EbayAspectLoader instance
    """
    global _aspect_loader
    if _aspect_loader is None:
        _aspect_loader = EbayAspectLoader()
        _aspect_loader.load()
    return _aspect_loader


def format_aspect_for_ui(aspect: Dict) -> Dict:
    """
    Format an aspect for frontend consumption.

    Args:
        aspect: Raw aspect dictionary from eBay API

    Returns:
        Formatted aspect dictionary optimized for UI rendering
    """
    constraint = aspect.get("aspectConstraint", {})

    return {
        "name": aspect.get("localizedAspectName", ""),
        "required": constraint.get("aspectRequired", False),
        "input_type": "dropdown" if constraint.get("aspectMode") == "SELECTION_ONLY" else "text",
        "multi_select": constraint.get("itemToAspectCardinality") == "MULTI",
        "data_type": constraint.get("aspectDataType", "STRING"),
        "usage": constraint.get("aspectUsage", "OPTIONAL"),
        "enabled_for_variations": constraint.get("aspectEnabledForVariations", False),
        "values": [
            {
                "value": val.get("localizedValue", ""),
                "value_id": val.get("valueId")
            }
            for val in aspect.get("aspectValues", [])
        ] if constraint.get("aspectMode") == "SELECTION_ONLY" else [],
        "max_length": constraint.get("aspectMaxLength"),
        "applicable_to": constraint.get("aspectApplicableTo", [])
    }


def get_formatted_aspects_for_category(category_id: str) -> Optional[Dict]:
    """
    Get formatted aspects for a category, ready for UI consumption.

    Args:
        category_id: eBay category ID

    Returns:
        Dictionary with formatted aspects or None if not found
    """
    loader = get_aspect_loader()
    aspect_data = loader.get_aspects_for_category(category_id)

    if not aspect_data:
        return None

    # Format all aspects for UI
    formatted_aspects = [
        format_aspect_for_ui(aspect)
        for aspect in aspect_data.aspects
    ]

    # Separate required and optional
    required = [a for a in formatted_aspects if a["required"]]
    recommended = [a for a in formatted_aspects if not a["required"] and a["usage"] == "RECOMMENDED"]
    optional = [a for a in formatted_aspects if not a["required"] and a["usage"] != "RECOMMENDED"]

    return {
        "category_id": aspect_data.category_id,
        "category_name": aspect_data.category_name,
        "aspects": {
            "required": required,
            "recommended": recommended,
            "optional": optional
        },
        "counts": {
            "total": len(formatted_aspects),
            "required": len(required),
            "recommended": len(recommended),
            "optional": len(optional)
        }
    }
