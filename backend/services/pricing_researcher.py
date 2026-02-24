import os
import json
import logging
import statistics
import time
from typing import List, Dict, Any
from anthropic import Anthropic
from langsmith import traceable
from models import PricingResponse, PricingStatistics, CompetitorListing
from utils.performance_logger import PerformanceTracker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PricingResearcher:
    """Service for researching product pricing using Claude AI."""

    def __init__(self, api_key: str):
        """Initialize the Claude API client.

        Args:
            api_key: Anthropic API key
        """
        self.client = Anthropic(
            api_key=api_key,
            timeout=300.0  # 5 minutes to allow for web search operations
        )
        self.model = "claude-sonnet-4-5-20250929"

    def _build_pricing_prompt(
        self,
        product_name: str,
        category: str,
        condition: str,
        platform: str
    ) -> str:
        """Build the pricing research prompt for Claude.

        Args:
            product_name: Product name to research
            category: Product category
            condition: Product condition
            platform: Target platform

        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a marketplace pricing analyst with real-time web access. Research CURRENT pricing for:

Product: {product_name}
Category: {category or 'General'}
Condition: {condition}
Platform: {platform.upper()}

**REQUIRED: Use web search to find REAL, CURRENT listings**

## Step 1: Search for Active Listings
Search: "{product_name} {condition} for sale {platform}"
- Find 3-5 currently active listings
- Note exact prices, titles, and URLs
- Look for listings with similar condition

## Step 2: Search for Sold/Completed Listings
Search: "{product_name} {condition} sold {platform}"
- Find 2-4 recently sold listings (if available)
- Note sold prices and dates
- Compare sold vs active prices for trend analysis

## Step 3: Search Competitor Platforms (if needed)
If {platform} data is sparse, search similar marketplaces:
- For eBay: Try "site:ebay.com {product_name} sold"
- For general: Try StockX, Mercari, or Poshmark
- Use these for market context, but prioritize {platform} prices

## Analysis Requirements:

1. **Competitor Prices**: List 5-7 REAL listings you found via web search
   - **MUST include actual URLs** (not null) from your searches
   - Include actual titles from the listings you found
   - Note if listing is "Active" or "Sold on [date]"
   - Ensure prices match the condition ({condition})

2. **Statistical Analysis**: Calculate from the REAL prices you found:
   - min_price: Lowest price found
   - max_price: Highest price found
   - average: Mean of all prices
   - median: Middle value of sorted prices
   - suggested_price: Strategic recommendation (see below)

3. **Suggested Price**: Based on REAL market data
   - If you found sold listings: Price between median sold and median active
   - If only active listings: Price at or slightly below median
   - Account for condition relative to listings found
   - Balance quick sale vs maximum profit

4. **Confidence Score** (0-100):
   - **90-100**: Found 6+ listings from {platform}, clear price consensus, recent sold data
   - **75-89**: Found 4-5 listings from {platform}, good price range
   - **60-74**: Found 2-3 listings, some uncertainty in pricing
   - **40-59**: Found 1-2 listings or used competitor platform data
   - **0-39**: No direct listings found, using category/brand averages

5. **Market Insights**: Based on your web search findings (2-3 sentences):
   - Current supply: "Found [X] active listings" (many=high supply, few=low supply)
   - Demand signals: Sold listings count, listing ages, price trends
   - Price trends: Compare sold prices vs active prices (increasing/decreasing/stable)
   - Platform-specific factors: Shipping costs, buyer protection, seasonality

**CRITICAL**: All competitor_prices MUST come from REAL web search results with actual URLs. Do not fabricate data or use null URLs.

Return ONLY valid JSON in this exact format:
{{
  "competitor_prices": [
    {{
      "price": 149.99,
      "title": "Actual listing title from web search",
      "url": "https://www.ebay.com/itm/actual-listing-id",
      "date_sold": "2025-01-08" or "Active"
    }},
    {{
      "price": 165.00,
      "title": "Another actual listing title",
      "url": "https://www.ebay.com/itm/another-listing-id",
      "date_sold": "Active"
    }}
  ],
  "statistics": {{
    "min_price": 99.99,
    "max_price": 249.99,
    "average": 175.50,
    "median": 169.99,
    "suggested_price": 179.99
  }},
  "confidence_score": 85,
  "market_insights": "Found 6 active listings on {platform} ranging $120-$240. Three recently sold at $165-$180 within past week. Strong demand with most listings under 7 days old. Suggested price is competitive for quick sale while maximizing value."
}}

Remember:
- Every URL must be real (from your web searches)
- Every title must be actual listing text
- Confidence score must reflect actual data availability
- Market insights must reference your search findings"""

        return prompt

    @traceable(name="research_pricing")
    async def research_pricing(
        self,
        product_name: str,
        category: str = None,
        condition: str = "Used",
        platform: str = "ebay"
    ) -> PricingResponse:
        """Research pricing for a product using Claude AI.

        Args:
            product_name: Product name to research
            category: Product category
            condition: Product condition
            platform: Target platform

        Returns:
            PricingResponse with pricing data and insights

        Raises:
            Exception: If API call fails or response is invalid
        """
        # Initialize performance tracker
        tracker = PerformanceTracker()
        tracker.log_event("pricing_research_start",
                         product_name=product_name,
                         platform=platform)

        try:
            logger.info(f"Researching pricing for: {product_name} on {platform}")

            # Build the pricing prompt
            prompt = self._build_pricing_prompt(product_name, category, condition, platform)

            # Track Claude API request for pricing
            api_start = time.time()
            tracker.log_api_request("pricing_api_start",
                                   model=self.model,
                                   platform=platform)

            # Call Claude API with web search
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                tools=[
                    {
                        "type": "web_search_20250305",
                        "name": "web_search",
                        "max_uses": 5,
                        "allowed_domains": [
                            # Primary marketplaces
                            "ebay.com",
                            "stockx.com",
                            "poshmark.com",
                            "mercari.com",
                            "depop.com",
                            "grailed.com",
                            "offerup.com",
                            "amazon.com",
                            # Price tracking / comparison
                            "camelcamelcamel.com",
                            "pricecharting.com",
                        ]
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
            )

            # Log API completion time
            api_duration_ms = (time.time() - api_start) * 1000
            tracker.log_api_request("pricing_api_complete",
                                   duration_ms=api_duration_ms,
                                   input_tokens=message.usage.input_tokens,
                                   output_tokens=message.usage.output_tokens)

            # ========================================
            # EXTRACT SYNTHESIZED PRICING & CITATIONS
            # ========================================

            # Log all web searches performed with timing
            parsing_start = time.time()
            search_count = 0
            search_queries = []
            for content_block in message.content:
                if hasattr(content_block, 'type') and content_block.type == 'server_tool_use':
                    if hasattr(content_block, 'name') and content_block.name == 'web_search':
                        search_count += 1
                        query = content_block.input.get('query', 'N/A') if hasattr(content_block, 'input') else 'N/A'
                        search_queries.append(query)
                        logger.info(f"🔍 Pricing Search {search_count}: {query}")
                        # Log each pricing web search
                        tracker.log_web_search(
                            search_num=search_count,
                            query=query,
                            duration_ms=0  # Duration not available per search
                        )

            if search_count > 0:
                logger.info(f"📊 Total web searches performed for pricing: {search_count}")
                tracker.log_event("pricing_web_searches_detected", count=search_count, queries=search_queries)
            else:
                logger.warning("⚠️  No web searches performed - pricing may be based on cached knowledge")

            # Check for web search errors
            for content_block in message.content:
                if hasattr(content_block, 'type') and content_block.type == 'web_search_tool_result':
                    if hasattr(content_block, 'content') and isinstance(content_block.content, dict):
                        if content_block.content.get('type') == 'web_search_tool_result_error':
                            error_code = content_block.content.get('error_code')
                            logger.error(f"❌ Pricing web search error: {error_code}")

                            if error_code == 'max_uses_exceeded':
                                raise Exception("Too many pricing search attempts. Please try again.")
                            elif error_code == 'too_many_requests':
                                raise Exception("Rate limit exceeded. Please wait a moment and try again.")
                            elif error_code == 'unavailable':
                                logger.warning("Web search unavailable - using cached pricing knowledge")

            # Extract the synthesized final answer (last text block)
            response_text = None
            citations = []

            for content_block in message.content:
                if hasattr(content_block, 'type') and content_block.type == "text":
                    response_text = content_block.text

                    # Extract citations if available
                    if hasattr(content_block, 'citations') and content_block.citations:
                        for citation in content_block.citations:
                            citations.append({
                                "url": citation.url if hasattr(citation, 'url') else None,
                                "title": citation.title if hasattr(citation, 'title') else None,
                                "cited_text": citation.cited_text if hasattr(citation, 'cited_text') else None
                            })

            if not response_text:
                raise Exception("No pricing response received from Claude")

            if citations:
                logger.info(f"📚 Pricing based on {len(citations)} web sources:")
                for i, citation in enumerate(citations[:5], 1):  # Log first 5 sources
                    logger.info(f"  {i}. {citation['title']} - {citation['url']}")
                if len(citations) > 5:
                    logger.info(f"  ... and {len(citations) - 5} more sources")

            logger.info(f"Received pricing response: {response_text[:200]}...")

            # Parse JSON response
            try:
                # Try to extract JSON from the response
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()

                pricing_data = json.loads(response_text)

                # Sanitize: filter out competitor prices with null/missing price
                if "competitor_prices" in pricing_data:
                    pricing_data["competitor_prices"] = [
                        cp for cp in pricing_data["competitor_prices"]
                        if cp.get("price") is not None
                    ]

                # Sanitize: recalculate statistics from valid prices if any are null
                stats = pricing_data.get("statistics", {})
                valid_prices = [cp["price"] for cp in pricing_data.get("competitor_prices", []) if cp.get("price") is not None]

                if valid_prices and any(stats.get(k) is None for k in ("min_price", "max_price", "average", "median", "suggested_price")):
                    sorted_prices = sorted(valid_prices)
                    mid = len(sorted_prices) // 2
                    median_val = (sorted_prices[mid] + sorted_prices[~mid]) / 2
                    avg_val = sum(sorted_prices) / len(sorted_prices)
                    stats["min_price"] = stats.get("min_price") if stats.get("min_price") is not None else sorted_prices[0]
                    stats["max_price"] = stats.get("max_price") if stats.get("max_price") is not None else sorted_prices[-1]
                    stats["average"] = stats.get("average") if stats.get("average") is not None else round(avg_val, 2)
                    stats["median"] = stats.get("median") if stats.get("median") is not None else round(median_val, 2)
                    stats["suggested_price"] = stats.get("suggested_price") if stats.get("suggested_price") is not None else round(median_val, 2)
                    pricing_data["statistics"] = stats
                elif not valid_prices:
                    # No valid prices at all — set defaults to 0
                    pricing_data["statistics"] = {
                        "min_price": 0.0, "max_price": 0.0,
                        "average": 0.0, "median": 0.0, "suggested_price": 0.0
                    }
                    pricing_data["competitor_prices"] = []

                # Log complete pricing result for dashboard
                tracker.log_pricing_result(result=pricing_data)

                # Validate and create response model
                return PricingResponse(**pricing_data)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Response text: {response_text}")
                raise Exception(f"Failed to parse pricing data: {str(e)}")

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            raise Exception("AI returned invalid pricing data format. Please try again.")
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            raise Exception(f"Invalid pricing data: {str(e)}")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error researching pricing: {error_msg}")

            # Provide more specific error messages
            if "rate_limit" in error_msg.lower():
                raise Exception("API rate limit exceeded. Please wait a moment and try again.")
            elif "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
                raise Exception("Authentication error. Please check your API key configuration.")
            elif "timeout" in error_msg.lower():
                raise Exception("Request timed out. Please try again.")
            else:
                raise Exception(f"Failed to research pricing: {error_msg}")


def get_pricing_researcher() -> PricingResearcher:
    """Get a configured PricingResearcher instance.

    Returns:
        PricingResearcher instance

    Raises:
        ValueError: If ANTHROPIC_API_KEY is not set
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    return PricingResearcher(api_key)
