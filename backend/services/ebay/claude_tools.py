"""
eBay Taxonomy Tools for Claude

Provides tool definitions and execution handlers for Claude to use
the eBay Taxonomy API during image analysis.
"""

import logging
from typing import Dict, Any, List
from services.ebay.taxonomy import EbayTaxonomyService
from services.ebay.aspect_loader import get_aspect_loader

logger = logging.getLogger(__name__)


def get_ebay_tools() -> List[Dict[str, Any]]:
    """
    Get tool definitions for eBay Taxonomy API.

    Returns:
        List of tool definitions in Anthropic tool format
    """
    return [
        {
            "name": "search_ebay_categories",
            "description": """Search for eBay categories that match a product. Use this to find the best category for listing an item on eBay.

Call this tool EARLY in your analysis, right after identifying the product type. The category information will help you determine the appropriate eBay category for the product.

Returns top category matches with:
- category_id: The eBay category ID
- category_name: Human-readable category name
- category_path: Full category hierarchy path
- is_leaf: Whether this is a leaf (listable) category
- aspects: Required and recommended item specifics for this category (if available)
  - required: List of required aspects (name, input_type, values)
  - recommended: List of recommended aspects (name, input_type, values)

The aspects are automatically included for each category, so you can immediately see what item specifics are needed.

Best practices:
- Use specific product type keywords (e.g., "water bottle", "tumbler")
- Include brand if relevant (e.g., "Owala tumbler")
- Review the aspects to understand what details eBay expects for this category""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'stainless steel water bottle', 'wireless earbuds', 'vintage watch')"
                    }
                },
                "required": ["query"]
            }
        }
    ]


def execute_ebay_tool(
    tool_name: str,
    tool_input: Dict[str, Any],
    taxonomy_service: EbayTaxonomyService
) -> Dict[str, Any]:
    """
    Execute an eBay tool.

    Args:
        tool_name: Name of the tool to execute
        tool_input: Tool input parameters
        taxonomy_service: Initialized eBay taxonomy service

    Returns:
        Tool execution result
    """
    try:
        if tool_name == "search_ebay_categories":
            return _search_ebay_categories(tool_input["query"], taxonomy_service)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        return {"error": str(e)}


def _search_ebay_categories(query: str, taxonomy_service: EbayTaxonomyService) -> Dict[str, Any]:
    """
    Search for eBay categories with aspects included.

    Args:
        query: Search query
        taxonomy_service: eBay taxonomy service

    Returns:
        Search results with aspect data
    """
    logger.info(f"Searching eBay categories for: {query}")

    try:
        categories = taxonomy_service.search_categories(query)

        # Get aspect loader instance
        aspect_loader = get_aspect_loader()

        # Format results for Claude WITH aspects
        results = []
        for cat in categories[:5]:  # Return top 5 matches
            category_id = cat.get("category_id")
            category_data = {
                "category_id": category_id,
                "category_name": cat.get("category_name"),
                "category_path": cat.get("path", "N/A"),
                "is_leaf": cat.get("leaf_category", False)
            }

            # Get aspect data for this category
            aspect_data = aspect_loader.get_aspects_for_category(category_id)
            if aspect_data:
                # Get required and recommended aspects
                required_aspects = aspect_data.get_required_aspects()
                recommended_aspects = aspect_data.get_recommended_aspects()

                # Format aspects for tool response (simplified version)
                category_data["aspects"] = {
                    "required": [
                        {
                            "name": asp.get("localizedAspectName"),
                            "input_type": "dropdown" if asp.get("aspectConstraint", {}).get("aspectMode") == "SELECTION_ONLY" else "text",
                            "values": [v.get("localizedValue") for v in asp.get("aspectValues", [])][:10]  # Limit to 10 values for brevity
                        }
                        for asp in required_aspects[:10]  # Limit to 10 aspects for brevity
                    ],
                    "recommended": [
                        {
                            "name": asp.get("localizedAspectName"),
                            "input_type": "dropdown" if asp.get("aspectConstraint", {}).get("aspectMode") == "SELECTION_ONLY" else "text",
                            "values": [v.get("localizedValue") for v in asp.get("aspectValues", [])][:10]
                        }
                        for asp in recommended_aspects[:10]  # Limit to 10 aspects
                    ]
                }
                logger.info(f"   Found {len(required_aspects)} required, {len(recommended_aspects)} recommended aspects for category {category_id}")
            else:
                category_data["aspects"] = None
                logger.info(f"   No aspects found for category {category_id}")

            results.append(category_data)

        return {
            "success": True,
            "query": query,
            "matches_found": len(results),
            "categories": results
        }

    except Exception as e:
        logger.error(f"Category search failed for '{query}': {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query
        }


