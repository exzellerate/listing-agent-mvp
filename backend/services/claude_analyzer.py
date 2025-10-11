import os
import json
import base64
import logging
from typing import Dict, Any, Optional
from anthropic import Anthropic
from models import AnalysisResponse, Platform

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClaudeAnalyzer:
    """Service for analyzing product images using Claude API with vision."""

    def __init__(self, api_key: str):
        """Initialize the Claude API client.

        Args:
            api_key: Anthropic API key
        """
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"

    def _get_platform_constraints(self, platform: Platform) -> Dict[str, Any]:
        """Get platform-specific constraints for titles and descriptions.

        Args:
            platform: Target marketplace platform

        Returns:
            Dictionary with title_max_chars and platform-specific guidelines
        """
        constraints = {
            "ebay": {
                "title_max_chars": 80,
                "guidelines": "eBay titles should be keyword-rich, include brand, model, key features, and condition. Avoid promotional language."
            },
            "amazon": {
                "title_max_chars": 200,
                "guidelines": "Amazon titles should follow: Brand + Model + Key Features + Size/Color. Use proper capitalization."
            },
            "walmart": {
                "title_max_chars": 75,
                "guidelines": "Walmart titles should be concise, include brand, product type, and 1-2 key features."
            }
        }
        return constraints.get(platform, constraints["ebay"])

    def _build_analysis_prompt(self, platform: Platform) -> str:
        """Build the analysis prompt for Claude.

        Args:
            platform: Target marketplace platform

        Returns:
            Formatted prompt string
        """
        constraints = self._get_platform_constraints(platform)

        prompt = f"""Analyze this product image and extract detailed information to create a marketplace listing for {platform.upper()}.

Please analyze the image and provide the following information in JSON format:

1. Product identification:
   - product_name: The specific product name/type
   - brand: Brand name (if visible or identifiable)
   - category: Product category (e.g., "Electronics", "Clothing", "Home & Garden")
   - model_number: Model number if visible on the product or packaging

2. Product details:
   - condition: Assess condition as "New", "Used - Like New", "Used - Good", "Used - Fair", or "Refurbished"
   - color: Primary color(s)
   - material: Material composition if identifiable
   - key_features: Array of 5-8 notable features, specifications, or selling points

3. Generate optimized listing content for {platform.upper()}:
   - suggested_title: Create a title optimized for {platform.upper()} (max {constraints['title_max_chars']} characters)
     Guidelines: {constraints['guidelines']}

   - suggested_description: Create a compelling product description with:
     * Opening paragraph: Engaging introduction (2-3 sentences)
     * Key Features: Bullet points highlighting main features
     * Condition Details: Specific condition information
     * Professional tone suitable for marketplace listing

Return ONLY valid JSON in this exact format:
{{
  "product_name": "string",
  "brand": "string or null",
  "category": "string or null",
  "condition": "string",
  "color": "string or null",
  "material": "string or null",
  "model_number": "string or null",
  "key_features": ["feature1", "feature2", ...],
  "suggested_title": "string",
  "suggested_description": "string"
}}

Be specific and accurate. If information is not visible or cannot be determined, use null for optional fields."""

        return prompt

    async def analyze_image(
        self,
        image_data: bytes,
        image_type: str,
        platform: Platform = "ebay"
    ) -> AnalysisResponse:
        """Analyze a product image using Claude API.

        Args:
            image_data: Raw image bytes
            image_type: MIME type (e.g., 'image/jpeg', 'image/png')
            platform: Target platform for optimization

        Returns:
            AnalysisResponse with product details and listing content

        Raises:
            Exception: If API call fails or response is invalid
        """
        try:
            # Encode image to base64
            base64_image = base64.standard_b64encode(image_data).decode("utf-8")

            # Determine media type
            media_type = image_type if image_type.startswith("image/") else f"image/{image_type}"

            logger.info(f"Analyzing image for platform: {platform}")

            # Build the analysis prompt
            prompt = self._build_analysis_prompt(platform)

            # Call Claude API with vision
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64_image,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ],
                    }
                ],
            )

            # Extract the response text
            response_text = message.content[0].text
            logger.info(f"Received response from Claude: {response_text[:200]}...")

            # Parse JSON response
            try:
                # Try to extract JSON from the response
                # Claude might wrap it in markdown code blocks
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()

                analysis_data = json.loads(response_text)

                # Validate and create response model
                return AnalysisResponse(**analysis_data)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Response text: {response_text}")
                raise Exception(f"Failed to parse API response as JSON: {str(e)}")

        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            raise Exception(f"Failed to analyze image: {str(e)}")


def get_analyzer() -> ClaudeAnalyzer:
    """Get a configured ClaudeAnalyzer instance.

    Returns:
        ClaudeAnalyzer instance

    Raises:
        ValueError: If ANTHROPIC_API_KEY is not set
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    return ClaudeAnalyzer(api_key)
