"""
eBay Taxonomy API Service

Handles category browsing, searching, and retrieving item specifics
for the eBay marketplace.
"""

import os
import logging
from typing import Optional, List, Dict, Any
import requests

logger = logging.getLogger(__name__)


class EbayTaxonomyService:
    """
    Service for interacting with eBay's Taxonomy API.

    Provides category search, hierarchy browsing, and item specifics retrieval.
    """

    def __init__(self, access_token: str):
        """
        Initialize taxonomy service.

        Args:
            access_token: Valid eBay OAuth access token
        """
        self.access_token = access_token
        self.environment = os.getenv("EBAY_ENV", "SANDBOX")
        self.base_url = self._get_base_url()
        self.marketplace_id = "EBAY_US"  # Default to US marketplace

    def _get_base_url(self) -> str:
        """Get API base URL based on environment."""
        if self.environment == "PRODUCTION":
            return "https://api.ebay.com/commerce/taxonomy/v1"
        return "https://api.sandbox.ebay.com/commerce/taxonomy/v1"

    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated API request.

        Args:
            endpoint: API endpoint path
            method: HTTP method
            params: Query parameters
            data: Request body data

        Returns:
            Response data

        Raises:
            Exception: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Taxonomy API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"eBay error response: {error_data}")
                    raise Exception(f"eBay API error: {error_data.get('errors', [{}])[0].get('message', str(e))}")
                except:
                    pass
            raise Exception(f"Failed to make taxonomy API request: {str(e)}")

    def get_default_category_tree_id(self) -> str:
        """
        Get the default category tree ID for the marketplace.

        Returns:
            Category tree ID (e.g., "0" for US marketplace)
        """
        try:
            response = self._make_request("/get_default_category_tree_id", params={
                "marketplace_id": self.marketplace_id
            })
            return response.get("categoryTreeId", "0")
        except Exception as e:
            logger.warning(f"Failed to get default category tree ID: {e}")
            return "0"  # Default to US tree

    def search_categories(
        self,
        query: str,
        category_tree_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for categories by keyword.

        Args:
            query: Search query (e.g., "laptops", "shoes")
            category_tree_id: Optional category tree ID

        Returns:
            List of matching categories with hierarchy information

        Example:
            >>> service.search_categories("laptop")
            [
                {
                    'category_id': '177',
                    'category_name': 'Laptops & Netbooks',
                    'category_path': 'Computers/Tablets & Networking > Laptops & Netbooks',
                    'leaf_category': True
                }
            ]
        """
        if not category_tree_id:
            category_tree_id = self.get_default_category_tree_id()

        logger.info(f"Searching categories for query: {query}")

        try:
            # eBay doesn't have a direct search endpoint, so we'll use get_category_suggestions
            response = self._make_request(
                f"/category_tree/{category_tree_id}/get_category_suggestions",
                params={"q": query}
            )

            categories = []
            for suggestion in response.get("categorySuggestions", []):
                category = suggestion.get("category", {})
                categories.append({
                    "category_id": category.get("categoryId"),
                    "category_name": category.get("categoryName"),
                    "category_path": self._build_category_path(category),
                    "leaf_category": not category.get("categoryTreeNodeLevel")  # Simplified check
                })

            logger.info(f"Found {len(categories)} category suggestions")
            return categories

        except Exception as e:
            logger.error(f"Category search failed: {e}")
            return []

    def _build_category_path(self, category: Dict[str, Any]) -> str:
        """
        Build human-readable category path.

        Args:
            category: Category data from API

        Returns:
            Formatted path string
        """
        # Build path from category tree node ancestry
        path_parts = []

        # Add parent categories if available
        if "categoryTreeNodeAncestors" in category:
            for ancestor in category["categoryTreeNodeAncestors"]:
                path_parts.append(ancestor.get("categoryName", ""))

        # Add current category
        path_parts.append(category.get("categoryName", ""))

        return " > ".join(path_parts)

    def get_category_tree(
        self,
        category_id: str,
        category_tree_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get full category tree information for a category.

        Args:
            category_id: Category ID to retrieve
            category_tree_id: Optional category tree ID

        Returns:
            Category tree data including hierarchy
        """
        if not category_tree_id:
            category_tree_id = self.get_default_category_tree_id()

        logger.info(f"Getting category tree for category: {category_id}")

        try:
            response = self._make_request(
                f"/category_tree/{category_tree_id}/get_category_subtree",
                params={"category_id": category_id}
            )
            return response

        except Exception as e:
            logger.error(f"Failed to get category tree: {e}")
            raise

    def get_category_tree_node(
        self,
        category_id: str,
        category_tree_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get category node information including name and hierarchy.

        Args:
            category_id: Category ID to retrieve
            category_tree_id: Optional category tree ID

        Returns:
            Category node data with name and path, or None if not found
        """
        if not category_tree_id:
            category_tree_id = self.get_default_category_tree_id()

        logger.info(f"Getting category tree node for category: {category_id}")

        try:
            response = self._make_request(
                f"/category_tree/{category_tree_id}/get_category_subtree",
                params={"category_id": category_id}
            )

            # Extract category info from response
            if response and "categorySubtreeNode" in response:
                node = response["categorySubtreeNode"]
                category = node.get("category", {})

                return {
                    "category_id": category.get("categoryId", category_id),
                    "category_name": category.get("categoryName", f"Category {category_id}"),
                    "category_tree_id": category_tree_id,
                    "leaf_category": node.get("leafCategoryTreeNode", False)
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get category tree node: {e}")
            return None

    def get_item_aspects(
        self,
        category_id: str,
        category_tree_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get item aspects (specifics) for a category.

        Args:
            category_id: Leaf category ID
            category_tree_id: Optional category tree ID

        Returns:
            Dict with aspects information including required and recommended fields

        Example:
            >>> service.get_item_aspects("177")
            {
                'aspects': [
                    {
                        'localizedAspectName': 'Brand',
                        'aspectRequired': True,
                        'aspectValues': [
                            {'localizedValue': 'Apple'},
                            {'localizedValue': 'Dell'}
                        ]
                    }
                ]
            }
        """
        if not category_tree_id:
            category_tree_id = self.get_default_category_tree_id()

        logger.info(f"Getting item aspects for category: {category_id}")

        try:
            response = self._make_request(
                f"/category_tree/{category_tree_id}/get_item_aspects_for_category",
                params={"category_id": category_id}
            )

            # Process and structure the aspects
            aspects = []
            for aspect in response.get("aspects", []):
                aspect_data = {
                    "name": aspect.get("localizedAspectName"),
                    "required": aspect.get("aspectConstraint", {}).get("aspectRequired", False),
                    "mode": aspect.get("aspectConstraint", {}).get("aspectMode", "FREE_TEXT"),
                    "usage": aspect.get("aspectConstraint", {}).get("aspectUsage"),
                    "values": []
                }

                # Get possible values if available
                if "aspectValues" in aspect:
                    aspect_data["values"] = [
                        v.get("localizedValue") for v in aspect["aspectValues"]
                    ]

                aspects.append(aspect_data)

            logger.info(f"Found {len(aspects)} aspects for category {category_id}")

            return {
                "category_id": category_id,
                "aspects": aspects
            }

        except Exception as e:
            logger.error(f"Failed to get item aspects: {e}")
            raise


def get_taxonomy_service(access_token: str) -> EbayTaxonomyService:
    """
    Factory function to create EbayTaxonomyService instance.

    Args:
        access_token: Valid eBay OAuth access token

    Returns:
        Configured EbayTaxonomyService instance
    """
    return EbayTaxonomyService(access_token)
