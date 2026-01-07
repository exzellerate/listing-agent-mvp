"""
eBay Media API Service for image uploads.

This service handles uploading images to eBay's Media API using the createImageFromUrl endpoint.
Images must be served via HTTPS (using ngrok/localtunnel) and then uploaded to eBay's servers.
"""

import os
import logging
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class EbayMediaService:
    """Service for eBay Media API operations."""

    def __init__(self, access_token: str, environment: str = "SANDBOX"):
        """
        Initialize eBay Media API service.

        Args:
            access_token: OAuth access token for eBay API
            environment: "SANDBOX" or "PRODUCTION"
        """
        self.access_token = access_token
        self.environment = environment

        # Set base URL based on environment
        if environment == "PRODUCTION":
            self.base_url = "https://apim.ebay.com/commerce/media/v1_beta"
        else:
            self.base_url = "https://apim.ebay.com/commerce/media/v1_beta"  # Same for sandbox

        logger.info(f"EbayMediaService initialized for {environment}")

    async def upload_image_from_url(self, image_url: str) -> Optional[str]:
        """
        Upload an image to eBay from a URL using the createImageFromUrl endpoint.

        Args:
            image_url: HTTPS URL where the image is accessible

        Returns:
            eBay-hosted image URL if successful, None otherwise

        Reference:
            https://developer.ebay.com/api-docs/commerce/media/resources/image/methods/createImageFromUrl
        """
        endpoint = f"{self.base_url}/image"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "imageUrl": image_url
        }

        logger.info(f"Uploading image to eBay from URL: {image_url}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    endpoint,
                    headers=headers,
                    json=payload
                )

                if response.status_code == 201:
                    # Success - extract image URL from response
                    response_data = response.json()
                    ebay_image_url = response_data.get("imageUrl")

                    if ebay_image_url:
                        logger.info(f"Successfully uploaded image to eBay: {ebay_image_url}")
                        return ebay_image_url
                    else:
                        logger.error("eBay response missing imageUrl field")
                        logger.error(f"Response data: {response_data}")
                        return None

                elif response.status_code == 400:
                    error_data = response.json()
                    logger.error(f"Bad request uploading image to eBay: {error_data}")
                    return None

                elif response.status_code == 401:
                    logger.error("Unauthorized - access token may be invalid or expired")
                    return None

                elif response.status_code == 403:
                    logger.error("Forbidden - insufficient permissions for Media API")
                    return None

                elif response.status_code == 500:
                    logger.error("eBay server error when uploading image")
                    return None

                else:
                    logger.error(f"Unexpected status code {response.status_code} from eBay Media API")
                    logger.error(f"Response: {response.text}")
                    return None

        except httpx.TimeoutException:
            logger.error("Timeout uploading image to eBay Media API")
            return None
        except Exception as e:
            logger.error(f"Error uploading image to eBay: {str(e)}")
            return None

    async def upload_multiple_images(self, image_urls: list[str]) -> list[str]:
        """
        Upload multiple images to eBay from URLs.

        Args:
            image_urls: List of HTTPS URLs where images are accessible

        Returns:
            List of eBay-hosted image URLs (only successful uploads)
        """
        ebay_urls = []

        for idx, image_url in enumerate(image_urls):
            logger.info(f"Uploading image {idx + 1}/{len(image_urls)}")
            ebay_url = await self.upload_image_from_url(image_url)

            if ebay_url:
                ebay_urls.append(ebay_url)
            else:
                logger.warning(f"Failed to upload image {idx + 1}: {image_url}")

        logger.info(f"Successfully uploaded {len(ebay_urls)}/{len(image_urls)} images to eBay")
        return ebay_urls
