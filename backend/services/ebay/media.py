"""
eBay Media API Service for image uploads.

Supports two upload methods:
1. createImageFromFile — binary upload (preferred, no URL accessibility needed)
2. createImageFromUrl — URL-based upload (eBay fetches from provided HTTPS URL)
"""

import os
import logging
import httpx
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class EbayMediaService:
    """Service for eBay Media API operations."""

    def __init__(self, access_token: str, environment: str = "SANDBOX"):
        self.access_token = access_token
        self.environment = environment

        if environment == "PRODUCTION":
            self.base_url = "https://apim.ebay.com/commerce/media/v1_beta"
        else:
            self.base_url = "https://apim.sandbox.ebay.com/commerce/media/v1_beta"

        logger.info(f"EbayMediaService initialized for {environment}")

    async def upload_image_from_file(self, image_data: bytes, filename: str) -> Optional[str]:
        """
        Upload an image to eBay as binary data using createImageFromFile.

        Args:
            image_data: Raw image bytes
            filename: Original filename (used for content-type detection)

        Returns:
            eBay-hosted image URL if successful, None otherwise
        """
        endpoint = f"{self.base_url}/image/create_image_from_file"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }

        # Detect content type from extension
        ext = os.path.splitext(filename)[1].lower()
        content_type_map = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".gif": "image/gif",
            ".webp": "image/webp", ".bmp": "image/bmp",
            ".tiff": "image/tiff", ".tif": "image/tiff",
            ".avif": "image/avif", ".heic": "image/heic",
        }
        content_type = content_type_map.get(ext, "image/jpeg")

        logger.info(f"Uploading image to eBay (binary): {filename} ({len(image_data)} bytes, {content_type})")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    endpoint,
                    headers=headers,
                    files={"image": (filename, image_data, content_type)},
                )

                if response.status_code in (200, 201):
                    response_data = response.json()
                    ebay_image_url = response_data.get("imageUrl")

                    if ebay_image_url:
                        logger.info(f"Successfully uploaded image to eBay: {ebay_image_url}")
                        return ebay_image_url
                    else:
                        logger.error(f"eBay response missing imageUrl field: {response_data}")
                        return None
                else:
                    logger.error(f"eBay Media API createImageFromFile failed: status={response.status_code}")
                    logger.error(f"Response: {response.text}")
                    return None

        except httpx.TimeoutException:
            logger.error(f"Timeout uploading image (binary) to eBay: {filename}")
            return None
        except Exception as e:
            logger.error(f"Error uploading image (binary) to eBay: {str(e)}")
            return None

    async def upload_image_from_url(self, image_url: str) -> Optional[str]:
        """
        Upload an image to eBay from a URL using createImageFromUrl.

        Args:
            image_url: HTTPS URL where the image is accessible

        Returns:
            eBay-hosted image URL if successful, None otherwise
        """
        endpoint = f"{self.base_url}/image/create_image_from_url"

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

                if response.status_code in (200, 201):
                    response_data = response.json()
                    ebay_image_url = response_data.get("imageUrl")

                    if ebay_image_url:
                        logger.info(f"Successfully uploaded image to eBay: {ebay_image_url}")
                        return ebay_image_url
                    else:
                        logger.error(f"eBay response missing imageUrl field: {response_data}")
                        return None
                else:
                    logger.error(f"eBay Media API createImageFromUrl failed: status={response.status_code}")
                    logger.error(f"Response: {response.text}")
                    return None

        except httpx.TimeoutException:
            logger.error("Timeout uploading image (URL) to eBay Media API")
            return None
        except Exception as e:
            logger.error(f"Error uploading image (URL) to eBay: {str(e)}")
            return None

    async def upload_multiple_images_from_files(
        self, images: List[Tuple[bytes, str]]
    ) -> List[str]:
        """
        Upload multiple images as binary data.

        Args:
            images: List of (image_bytes, filename) tuples

        Returns:
            List of eBay-hosted image URLs (only successful uploads)
        """
        ebay_urls = []

        for idx, (image_data, filename) in enumerate(images):
            logger.info(f"Uploading image {idx + 1}/{len(images)}: {filename}")
            ebay_url = await self.upload_image_from_file(image_data, filename)

            if ebay_url:
                ebay_urls.append(ebay_url)
            else:
                logger.warning(f"Failed to upload image {idx + 1}: {filename}")

        logger.info(f"Successfully uploaded {len(ebay_urls)}/{len(images)} images to eBay")
        return ebay_urls

    async def upload_multiple_images(self, image_urls: list[str]) -> list[str]:
        """
        Upload multiple images from URLs (fallback method).

        Args:
            image_urls: List of HTTPS URLs where images are accessible

        Returns:
            List of eBay-hosted image URLs (only successful uploads)
        """
        ebay_urls = []

        for idx, image_url in enumerate(image_urls):
            logger.info(f"Uploading image {idx + 1}/{len(image_urls)} from URL")
            ebay_url = await self.upload_image_from_url(image_url)

            if ebay_url:
                ebay_urls.append(ebay_url)
            else:
                logger.warning(f"Failed to upload image {idx + 1}: {image_url}")

        logger.info(f"Successfully uploaded {len(ebay_urls)}/{len(image_urls)} images to eBay")
        return ebay_urls
