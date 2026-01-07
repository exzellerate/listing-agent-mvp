"""
eBay Listing Service

Orchestrates the complete process of creating and publishing eBay listings.
Handles inventory creation, offer creation, image upload, and failure tracking.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
import requests

from database_models import (
    EbayListing, EbayListingFailure, ListingStatus, FailureStage
)
from .oauth import EbayOAuthService

logger = logging.getLogger(__name__)


class EbayListingService:
    """
    Manages eBay listing creation and publication.

    Workflow:
    1. Validate listing data
    2. Generate unique SKU
    3. Upload images to eBay
    4. Create inventory item
    5. Create offer with pricing
    6. Publish listing
    7. Track status and handle failures
    """

    def __init__(self, db: Session, oauth_service: EbayOAuthService):
        """
        Initialize listing service.

        Args:
            db: Database session
            oauth_service: OAuth service for authentication
        """
        self.db = db
        self.oauth_service = oauth_service

        # API configuration
        self.environment = os.getenv("EBAY_ENV", "SANDBOX")
        self.api_url = self._get_api_url()

        # Business policies (can be set via env or created in eBay seller hub)
        self.default_shipping_policy_id = os.getenv("EBAY_DEFAULT_SHIPPING_POLICY_ID")
        self.default_return_policy_id = os.getenv("EBAY_DEFAULT_RETURN_POLICY_ID")
        self.default_payment_policy_id = os.getenv("EBAY_DEFAULT_PAYMENT_POLICY_ID")

    def _get_api_url(self) -> str:
        """Get API base URL based on environment."""
        if self.environment == "PRODUCTION":
            return "https://api.ebay.com"
        return "https://api.sandbox.ebay.com"

    def create_listing(
        self,
        analysis_id: Optional[int],
        title: str,
        description: str,
        price: float,
        quantity: int = 1,
        condition: str = "USED_EXCELLENT",
        category_id: Optional[str] = None,
        images: Optional[List[bytes]] = None,
        user_id: str = "default_user",
        shipping_weight_lbs: Optional[float] = None,
        shipping_weight_oz: Optional[float] = None,
        shipping_length: Optional[float] = None,
        shipping_width: Optional[float] = None,
        shipping_height: Optional[float] = None,
        image_urls: Optional[List[str]] = None,
        item_specifics: Optional[Dict[str, Any]] = None
    ) -> EbayListing:
        """
        Create a new eBay listing (orchestrator method).

        Args:
            analysis_id: Link to product analysis
            title: Listing title
            description: Listing description
            price: Price in USD
            quantity: Available quantity
            condition: Item condition
            category_id: eBay category ID
            images: List of image bytes
            user_id: User identifier
            shipping_weight_lbs: Package weight in pounds (for calculated shipping)
            shipping_weight_oz: Package weight in ounces (for calculated shipping)
            shipping_length: Package length in inches (for calculated shipping)
            shipping_width: Package width in inches (for calculated shipping)
            shipping_height: Package height in inches (for calculated shipping)
            image_urls: List of image URLs (HTTPS URLs from analysis)

        Returns:
            Created EbayListing object

        Raises:
            Exception: If listing creation fails
        """
        logger.info(f"Creating eBay listing: {title[:50]}...")

        # Generate unique SKU
        sku = self._generate_sku()

        # Create listing record in database
        listing = EbayListing(
            analysis_id=analysis_id,
            sku=sku,
            title=title,
            description=description,
            price=price,
            quantity=quantity,
            condition=condition,
            category_id=category_id,
            status=ListingStatus.DRAFT,
            shipping_weight_major=shipping_weight_lbs,
            shipping_weight_minor=shipping_weight_oz,
            shipping_length=shipping_length,
            shipping_width=shipping_width,
            shipping_height=shipping_height,
            image_urls=image_urls,  # Store image URLs from analysis
            item_specifics=item_specifics  # Store user-provided item specifics
        )
        self.db.add(listing)
        self.db.commit()
        self.db.refresh(listing)

        logger.info(f"Listing created with SKU: {sku}, ID: {listing.id}")
        if image_urls:
            logger.info(f"Stored {len(image_urls)} image URL(s) in listing: {image_urls}")

        # Start the listing creation workflow
        try:
            self._execute_listing_workflow(listing, images, user_id)
        except Exception as e:
            logger.error(f"Listing workflow failed: {e}")
            self._update_listing_status(
                listing.id,
                ListingStatus.FAILED,
                error=str(e)
            )
            raise

        return listing

    def _execute_listing_workflow(
        self,
        listing: EbayListing,
        images: Optional[List[bytes]],
        user_id: str
    ):
        """
        Execute the complete listing creation workflow.

        Args:
            listing: Listing database record
            images: List of image bytes
            user_id: User identifier
        """
        try:
            # Step 1: Validate data
            self._update_listing_status(listing.id, ListingStatus.VALIDATING)
            self._validate_listing_data(listing)

            # Step 1.5: Ensure inventory location exists
            self._ensure_inventory_location(user_id)

            # Step 2: Upload images
            if images:
                self._update_listing_status(listing.id, ListingStatus.UPLOADING_IMAGES)
                image_urls = self._upload_images(listing.sku, images, user_id)
                listing.image_urls = image_urls
                self.db.commit()

            # Step 3: Create inventory item
            self._update_listing_status(listing.id, ListingStatus.CREATING_INVENTORY)
            self._create_inventory_item(listing, user_id)

            # Step 4: Create offer
            self._update_listing_status(listing.id, ListingStatus.CREATING_OFFER)
            offer_id = self._create_offer(listing, user_id)
            listing.offer_id = offer_id
            self.db.commit()

            # Step 5: Publish listing
            self._update_listing_status(listing.id, ListingStatus.PUBLISHING)
            ebay_listing_id = self._publish_listing(offer_id, user_id)
            listing.listing_id = ebay_listing_id
            listing.published_at = datetime.utcnow()
            self.db.commit()

            # Success!
            self._update_listing_status(listing.id, ListingStatus.PUBLISHED)
            logger.info(f"Listing {listing.sku} published successfully! eBay ID: {ebay_listing_id}")

        except Exception as e:
            # Log failure and re-raise
            stage = self._get_failure_stage_from_status(listing.status)
            self._log_failure(listing.id, stage, str(e))
            raise

    def _generate_sku(self) -> str:
        """
        Generate unique SKU for listing.

        Returns:
            Unique SKU string

        Example:
            LA-2025-001234
        """
        from datetime import datetime
        import random

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = random.randint(1000, 9999)
        sku = f"LA-{timestamp}-{random_suffix}"

        # Ensure uniqueness
        existing = self.db.query(EbayListing).filter(EbayListing.sku == sku).first()
        if existing:
            # Recursive call if collision (rare)
            return self._generate_sku()

        return sku

    def _create_default_fulfillment_policy(self, user_id: str) -> Optional[str]:
        """
        Create a default fulfillment (shipping) policy in eBay.

        Args:
            user_id: User identifier

        Returns:
            Policy ID if successful, None otherwise
        """
        token = self.oauth_service.get_valid_token(user_id)
        if not token:
            return None

        url = f"{self.api_url}/sell/account/v1/fulfillment_policy"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "name": "Default Shipping Policy",
            "marketplaceId": "EBAY_US",
            "categoryTypes": [{"name": "ALL_EXCLUDING_MOTORS_VEHICLES"}],
            "handlingTime": {"value": 1, "unit": "BUSINESS_DAY"},
            "shippingOptions": [
                {
                    "costType": "FLAT_RATE",
                    "shippingServices": [
                        {
                            "shippingCarrierCode": "USPS",
                            "shippingServiceCode": "USPSPriority",
                            "shippingCost": {"value": "10.00", "currency": "USD"},
                            "sortOrder": 1
                        }
                    ],
                    "optionType": "DOMESTIC"
                }
            ],
            "shipToLocations": {
                "regionIncluded": [{"regionName": "DOMESTIC", "regionType": "COUNTRY"}]
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            policy_id = data.get("fulfillmentPolicyId")
            if policy_id:
                logger.info(f"Created default fulfillment policy: {policy_id}")
            return policy_id
        except Exception as e:
            logger.warning(f"Could not create fulfillment policy: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.warning(f"eBay error response: {error_data}")
                except:
                    pass
            return None

    def _get_fulfillment_policies(self, user_id: str) -> list:
        """
        Get user's fulfillment (shipping) policies from eBay.

        Args:
            user_id: User identifier

        Returns:
            List of fulfillment policies
        """
        token = self.oauth_service.get_valid_token(user_id)
        if not token:
            raise ValueError("No valid eBay authentication token")

        url = f"{self.api_url}/sell/account/v1/fulfillment_policy"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(
                url,
                headers=headers,
                params={"marketplace_id": "EBAY_US"},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            policies = data.get("fulfillmentPolicies", [])

            # If no policies exist, try to create a default one
            if not policies:
                logger.info("No fulfillment policies found, creating default policy")
                policy_id = self._create_default_fulfillment_policy(user_id)
                if policy_id:
                    return [{"fulfillmentPolicyId": policy_id}]

            return policies
        except Exception as e:
            logger.warning(f"Could not fetch fulfillment policies: {e}")
            # Try to create a default policy
            policy_id = self._create_default_fulfillment_policy(user_id)
            if policy_id:
                return [{"fulfillmentPolicyId": policy_id}]
            return []

    def _create_default_payment_policy(self, user_id: str) -> Optional[str]:
        """
        Create a default payment policy in eBay.

        Args:
            user_id: User identifier

        Returns:
            Policy ID if successful, None otherwise
        """
        token = self.oauth_service.get_valid_token(user_id)
        if not token:
            return None

        url = f"{self.api_url}/sell/account/v1/payment_policy"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "name": "Default Payment Policy",
            "marketplaceId": "EBAY_US",
            "categoryTypes": [{"name": "ALL_EXCLUDING_MOTORS_VEHICLES"}],
            "paymentMethods": [
                {"paymentMethodType": "PAYPAL"},
                {"paymentMethodType": "CREDIT_CARD"}
            ],
            "immediatePay": False
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            policy_id = data.get("paymentPolicyId")
            if policy_id:
                logger.info(f"Created default payment policy: {policy_id}")
            return policy_id
        except Exception as e:
            logger.warning(f"Could not create payment policy: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.warning(f"eBay error response: {error_data}")
                except:
                    pass
            return None

    def _get_payment_policies(self, user_id: str) -> list:
        """
        Get user's payment policies from eBay.

        Args:
            user_id: User identifier

        Returns:
            List of payment policies
        """
        token = self.oauth_service.get_valid_token(user_id)
        if not token:
            raise ValueError("No valid eBay authentication token")

        url = f"{self.api_url}/sell/account/v1/payment_policy"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(
                url,
                headers=headers,
                params={"marketplace_id": "EBAY_US"},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            policies = data.get("paymentPolicies", [])

            # If no policies exist, try to create a default one
            if not policies:
                logger.info("No payment policies found, creating default policy")
                policy_id = self._create_default_payment_policy(user_id)
                if policy_id:
                    return [{"paymentPolicyId": policy_id}]

            return policies
        except Exception as e:
            logger.warning(f"Could not fetch payment policies: {e}")
            # Try to create a default policy
            policy_id = self._create_default_payment_policy(user_id)
            if policy_id:
                return [{"paymentPolicyId": policy_id}]
            return []

    def _create_default_return_policy(self, user_id: str) -> Optional[str]:
        """
        Create a default return policy in eBay.

        Args:
            user_id: User identifier

        Returns:
            Policy ID if successful, None otherwise
        """
        token = self.oauth_service.get_valid_token(user_id)
        if not token:
            return None

        url = f"{self.api_url}/sell/account/v1/return_policy"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "name": "Default Return Policy",
            "marketplaceId": "EBAY_US",
            "categoryTypes": [{"name": "ALL_EXCLUDING_MOTORS_VEHICLES"}],
            "returnsAccepted": True,
            "returnPeriod": {
                "value": 30,
                "unit": "DAY"
            },
            "refundMethod": "MONEY_BACK",
            "returnShippingCostPayer": "BUYER"
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            policy_id = data.get("returnPolicyId")
            if policy_id:
                logger.info(f"Created default return policy: {policy_id}")
            return policy_id
        except Exception as e:
            logger.warning(f"Could not create return policy: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.warning(f"eBay error response: {error_data}")
                except:
                    pass
            return None

    def _get_return_policies(self, user_id: str) -> list:
        """
        Get user's return policies from eBay.

        Args:
            user_id: User identifier

        Returns:
            List of return policies
        """
        token = self.oauth_service.get_valid_token(user_id)
        if not token:
            raise ValueError("No valid eBay authentication token")

        url = f"{self.api_url}/sell/account/v1/return_policy"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(
                url,
                headers=headers,
                params={"marketplace_id": "EBAY_US"},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            policies = data.get("returnPolicies", [])

            # If no policies exist, try to create a default one
            if not policies:
                logger.info("No return policies found, creating default policy")
                policy_id = self._create_default_return_policy(user_id)
                if policy_id:
                    return [{"returnPolicyId": policy_id}]

            return policies
        except Exception as e:
            logger.warning(f"Could not fetch return policies: {e}")
            # Try to create a default policy
            policy_id = self._create_default_return_policy(user_id)
            if policy_id:
                return [{"returnPolicyId": policy_id}]
            return []

    def _ensure_inventory_location(self, user_id: str):
        """
        Ensure inventory location exists for the user.
        Creates a default location if it doesn't exist.

        Args:
            user_id: User identifier
        """
        logger.info("Ensuring inventory location exists")

        # Get valid OAuth token
        token = self.oauth_service.get_valid_token(user_id)
        if not token:
            raise ValueError("No valid eBay authentication token")

        # Check if location already exists
        url = f"{self.api_url}/sell/inventory/v1/location/DEFAULT_LOCATION"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            # Try to get existing location
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                logger.info("Inventory location already exists")
                return
        except:
            pass

        # Location doesn't exist, create it
        location_payload = {
            "location": {
                "address": {
                    "addressLine1": "123 Main St",
                    "city": "San Jose",
                    "stateOrProvince": "CA",
                    "postalCode": "95131",
                    "country": "US"
                }
            },
            "locationInstructions": "Default shipping location",
            "name": "Default Location",
            "merchantLocationStatus": "ENABLED",
            "locationTypes": ["WAREHOUSE"]
        }

        try:
            response = requests.post(
                f"{self.api_url}/sell/inventory/v1/location/DEFAULT_LOCATION",
                headers=headers,
                json=location_payload,
                timeout=30
            )
            # 201 or 204 are success codes
            if response.status_code in [201, 204]:
                logger.info("Inventory location created successfully")
            elif response.status_code == 200:
                logger.info("Inventory location already exists")
            else:
                response.raise_for_status()
        except requests.exceptions.RequestException as e:
            # If it fails, log but don't fail the listing - might already exist
            logger.warning(f"Could not create/verify inventory location: {e}")
            # Continue anyway - the location might exist or eBay will provide better error

    def _validate_listing_data(self, listing: EbayListing):
        """
        Validate listing data before creation.

        Args:
            listing: Listing to validate

        Raises:
            ValueError: If validation fails
        """
        errors = []

        # Title validation
        if len(listing.title) > 80:
            errors.append(f"Title too long ({len(listing.title)}/80 characters)")
        if len(listing.title) < 10:
            errors.append("Title too short (minimum 10 characters)")

        # Price validation
        if listing.price <= 0:
            errors.append("Price must be greater than 0")
        if listing.price > 999999:
            errors.append("Price too high (maximum $999,999)")

        # Quantity validation
        if listing.quantity < 1:
            errors.append("Quantity must be at least 1")

        # Category validation (if provided)
        if listing.category_id and not listing.category_id.isdigit():
            errors.append("Invalid category ID format")

        if errors:
            error_msg = "; ".join(errors)
            logger.error(f"Validation failed: {error_msg}")
            raise ValueError(f"Listing validation failed: {error_msg}")

        logger.info("Listing validation passed")

    def _upload_images(
        self,
        sku: str,
        images: List[bytes],
        user_id: str
    ) -> List[str]:
        """
        Upload images to eBay Picture Services.

        Args:
            sku: Listing SKU
            images: List of image bytes
            user_id: User identifier

        Returns:
            List of eBay-hosted image URLs

        Raises:
            Exception: If image upload fails
        """
        logger.info(f"Uploading {len(images)} images for SKU: {sku}")

        # TODO: Implement eBay image upload
        # Endpoint: POST /sell/inventory/v1/inventory_item/{sku}/image

        raise NotImplementedError(
            "eBay image upload not yet implemented. "
            "This requires eBay Picture Services integration."
        )

    def _get_category_metadata(self, category_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get category metadata including valid conditions and required item specifics.

        Args:
            category_id: eBay category ID
            user_id: User identifier

        Returns:
            Dictionary with:
            {
                "conditions": ["NEW", "USED_EXCELLENT", ...],
                "item_specifics": [
                    {
                        "name": "Type",
                        "required": True,
                        "values": ["Digital", "Manual", ...]
                    },
                    ...
                ]
            }
        """
        default_result = {
            "conditions": ["USED_EXCELLENT", "USED_GOOD", "NEW"],
            "item_specifics": []
        }

        # Get application token (not user token) for metadata API
        try:
            token = self.oauth_service.get_application_token()
            if not token:
                logger.warning("No application token available, using defaults")
                return default_result
        except Exception as e:
            logger.warning(f"Could not get application token: {e}")
            return default_result

        # Use the Taxonomy API to get category-specific metadata
        url = f"{self.api_url}/commerce/taxonomy/v1/category_tree/0/get_item_aspects_for_category"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(
                url,
                headers=headers,
                params={"category_id": category_id},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            result = {
                "conditions": [],
                "item_specifics": []
            }

            # Parse all aspects
            aspects = data.get("aspects", [])
            logger.info(f"Found {len(aspects)} aspects for category {category_id}")

            for aspect in aspects:
                aspect_name = aspect.get("localizedAspectName", "")
                aspect_constraint = aspect.get("aspectConstraint", {})
                is_required = aspect_constraint.get("aspectRequired", False)
                max_values = aspect_constraint.get("itemToAspectCardinality")  # e.g., "MULTI" or "SINGLE"
                aspect_values = aspect.get("aspectValues", [])

                # Extract values
                values = [v.get("value") or v.get("localizedValue") for v in aspect_values if v.get("value") or v.get("localizedValue")]

                # Determine max_values (default to 1 for single, higher for multi)
                # eBay uses "MULTI" for multiple values allowed
                max_vals = None
                if max_values == "MULTI":
                    max_vals = 10  # Default max for multi-value fields
                elif max_values:
                    max_vals = 1

                # Special handling for Condition aspect
                if aspect_name.lower() == "condition":
                    result["conditions"] = values
                    logger.info(f"Found {len(values)} valid conditions")
                else:
                    # Add as item specific
                    specific_dict = {
                        "name": aspect_name,
                        "required": is_required,
                        "values": values
                    }
                    if max_vals is not None:
                        specific_dict["max_values"] = max_vals

                    result["item_specifics"].append(specific_dict)
                    if is_required:
                        logger.info(f"Required item specific: {aspect_name} (with {len(values)} possible values, max_values={max_vals})")

            # Use defaults if no conditions found
            if not result["conditions"]:
                logger.info("No condition aspect found, using defaults")
                result["conditions"] = default_result["conditions"]

            logger.info(f"Category metadata: {len(result['conditions'])} conditions, "
                       f"{len(result['item_specifics'])} item specifics "
                       f"({sum(1 for s in result['item_specifics'] if s['required'])} required)")

            return result

        except Exception as e:
            logger.warning(f"Could not fetch category metadata for {category_id}: {e}")
            return default_result

    def _validate_and_map_aspect_value(
        self,
        aspect_name: str,
        aspect_value: str,
        item_specific_schema: Dict[str, Any],
        listing_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Validate an aspect value against eBay's schema and map to valid value if needed.

        Args:
            aspect_name: Name of the aspect (e.g., "Type", "Brand")
            aspect_value: AI-generated value to validate
            item_specific_schema: eBay schema for this aspect (with allowed values)
            listing_data: Additional listing data for context

        Returns:
            Valid eBay value, or None if value cannot be mapped
        """
        allowed_values = item_specific_schema.get("values", [])

        # If no allowed values specified, accept any value
        if not allowed_values:
            return aspect_value

        # Check for exact match (case-insensitive)
        for allowed in allowed_values:
            if aspect_value.lower() == allowed.lower():
                return allowed

        # Try fuzzy matching for common cases
        aspect_value_lower = aspect_value.lower()

        # Special handling for "Type" in blood pressure monitor category
        if aspect_name == "Type":
            # Map generic AI values to eBay-specific values
            type_mappings = {
                "digital": "Upper Arm Monitor",  # Most digital BP monitors are upper arm
                "manual": "Blood Pressure Testing",
                "automatic": "Upper Arm Monitor",
                "wrist": "Wrist Monitor",
                "upper arm": "Upper Arm Monitor",
                "arm": "Upper Arm Monitor"
            }

            # Check product name for clues
            product_name = listing_data.get("product_name", "").lower()
            title = listing_data.get("title", "").lower()
            combined_text = f"{product_name} {title}"

            # Try direct mapping first
            for pattern, ebay_value in type_mappings.items():
                if pattern in aspect_value_lower:
                    if ebay_value in allowed_values:
                        logger.info(f"Mapped Type value '{aspect_value}' → '{ebay_value}'")
                        return ebay_value

            # Check product context
            if "wrist" in combined_text:
                if "Wrist Monitor" in allowed_values:
                    logger.info(f"Inferred Type='Wrist Monitor' from product context")
                    return "Wrist Monitor"
            elif "upper arm" in combined_text or "arm cuff" in combined_text:
                if "Upper Arm Monitor" in allowed_values:
                    logger.info(f"Inferred Type='Upper Arm Monitor' from product context")
                    return "Upper Arm Monitor"

            # Default to first valid value as fallback
            if allowed_values:
                logger.warning(f"Could not map Type='{aspect_value}', using default: {allowed_values[0]}")
                return allowed_values[0]

        # For other aspects, try partial match
        for allowed in allowed_values:
            if aspect_value_lower in allowed.lower() or allowed.lower() in aspect_value_lower:
                logger.info(f"Fuzzy matched '{aspect_value}' → '{allowed}' for {aspect_name}")
                return allowed

        # No valid mapping found
        logger.warning(f"Could not map {aspect_name}='{aspect_value}' to any allowed value")
        return None

    def _map_attributes_to_item_specifics(
        self,
        ai_attributes: Dict[str, Any],
        required_specifics: List[Dict[str, Any]],
        listing_data: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """
        Map AI-extracted product attributes to eBay item specifics format.
        Validates all values against eBay's category-specific schema.

        Args:
            ai_attributes: Product attributes from AI analysis
            required_specifics: Required item specifics from category metadata
            listing_data: Additional listing data (brand, model, etc.)

        Returns:
            Dictionary of item specifics in eBay format: {"Type": ["Digital"], ...}
        """
        aspects = {}

        if not ai_attributes:
            logger.info("No AI attributes provided")
            return aspects

        # Build schema lookup for validation
        schema_lookup = {spec["name"]: spec for spec in required_specifics}

        # Direct mapping for common attributes
        direct_mappings = {
            "Type": ai_attributes.get("Type"),
            "Size": ai_attributes.get("Size"),
            "Style": ai_attributes.get("Style"),
            "Connectivity": ai_attributes.get("Connectivity"),
            "Power Source": ai_attributes.get("Power Source"),
            "Material": ai_attributes.get("Material")
        }

        # Add direct mappings with validation
        for key, value in direct_mappings.items():
            if value:
                schema = schema_lookup.get(key, {})
                if schema:
                    # Validate against eBay schema
                    validated_value = self._validate_and_map_aspect_value(
                        key, value, schema, listing_data
                    )
                    if validated_value:
                        aspects[key] = [validated_value]
                else:
                    # No schema, accept as-is
                    aspects[key] = [value] if isinstance(value, str) else value

        # Handle Features specially - flatten list into comma-separated or multiple values
        features = ai_attributes.get("Features")
        if features and isinstance(features, list):
            aspects["Features"] = features  # eBay accepts list format

        # Add Brand if available (common required field)
        if listing_data.get("brand"):
            brand_value = listing_data["brand"]
            brand_schema = schema_lookup.get("Brand", {})
            if brand_schema:
                validated_brand = self._validate_and_map_aspect_value(
                    "Brand", brand_value, brand_schema, listing_data
                )
                if validated_brand:
                    aspects["Brand"] = [validated_brand]
            else:
                aspects["Brand"] = [brand_value]

        # Add Model if available
        if listing_data.get("model_number"):
            aspects["Model"] = [listing_data["model_number"]]

        # Handle additional_attributes from AI
        additional_attrs = ai_attributes.get("additional_attributes", {})
        if isinstance(additional_attrs, dict):
            for key, value in additional_attrs.items():
                if value and key not in aspects:
                    schema = schema_lookup.get(key, {})
                    if schema:
                        validated_value = self._validate_and_map_aspect_value(
                            key, value, schema, listing_data
                        )
                        if validated_value:
                            aspects[key] = [validated_value]
                    else:
                        aspects[key] = [value] if isinstance(value, str) else value

        # Validate required specifics are present
        required_names = [s["name"] for s in required_specifics if s.get("usage") == "REQUIRED"]
        missing_required = [name for name in required_names if name not in aspects]

        if missing_required:
            logger.warning(f"Missing required item specifics: {missing_required}")
            logger.warning("Attempting to infer from available data...")

            # Try to infer missing required fields
            for missing in missing_required:
                schema = schema_lookup.get(missing, {})

                if missing == "Type":
                    # Try to infer Type from product name/title
                    product_name = listing_data.get("product_name", "").lower()
                    title = listing_data.get("title", "").lower()
                    combined_text = f"{product_name} {title}"

                    logger.info(f"Attempting to infer missing Type field. Product: '{product_name}', Title: '{title}'")

                    # Use validation method to intelligently map
                    inferred_value = self._validate_and_map_aspect_value(
                        "Type", "digital", schema, listing_data  # Start with "digital" as default
                    )

                    if inferred_value:
                        aspects["Type"] = [inferred_value]
                        logger.info(f"Successfully inferred Type='{inferred_value}'")
                    else:
                        # Last resort: use first allowed value
                        allowed_values = schema.get("values", [])
                        if allowed_values:
                            aspects["Type"] = [allowed_values[0]]
                            logger.warning(f"Type inference failed, using first allowed value: {allowed_values[0]}")
                        else:
                            logger.error("Type inference failed and no allowed values found!")

        # Final validation - log what we're sending
        logger.info(f"Final mapped item specifics ({len(aspects)} total):")
        for key, value in aspects.items():
            logger.info(f"  {key}: {value}")

        # Check for required fields one more time
        final_missing = [name for name in [s["name"] for s in required_specifics if s.get("usage") == "REQUIRED"] if name not in aspects]
        if final_missing:
            logger.error(f"CRITICAL: Still missing required fields after inference: {final_missing}")

        return aspects

    def _create_inventory_item(self, listing: EbayListing, user_id: str):
        """
        Create inventory item on eBay.

        Args:
            listing: Listing database record
            user_id: User identifier

        Raises:
            Exception: If inventory creation fails
        """
        logger.info(f"Creating inventory item for SKU: {listing.sku}")

        # Get valid OAuth token
        token = self.oauth_service.get_valid_token(user_id)
        if not token:
            raise ValueError("No valid eBay authentication token")

        # Get category metadata (conditions and item specifics) if category is specified
        category_metadata = None
        valid_conditions = None
        item_specifics = []

        if listing.category_id:
            category_metadata = self._get_category_metadata(listing.category_id, user_id)
            valid_conditions = category_metadata.get("conditions", [])
            item_specifics = category_metadata.get("item_specifics", [])
            logger.info(f"Category {listing.category_id} - Valid conditions: {valid_conditions}")
            logger.info(f"Category {listing.category_id} - Item specifics: {len(item_specifics)} total, "
                       f"{sum(1 for s in item_specifics if s['required'])} required")

        # Build inventory item payload
        # Map our condition values to eBay's condition enum
        condition_mapping = {
            "NEW": "NEW",
            "LIKE_NEW": "LIKE_NEW",
            "USED_EXCELLENT": "USED_EXCELLENT",
            "USED_GOOD": "USED_GOOD",
            "USED_ACCEPTABLE": "USED_ACCEPTABLE",
            "FOR_PARTS_OR_NOT_WORKING": "FOR_PARTS_OR_NOT_WORKING"
        }

        ebay_condition = condition_mapping.get(listing.condition, "USED_EXCELLENT")

        # If we have valid conditions for this category, verify our condition is valid
        # If not, use the first valid condition
        if valid_conditions and ebay_condition not in valid_conditions:
            logger.warning(f"Condition '{ebay_condition}' not valid for category {listing.category_id}")
            logger.warning(f"Using first valid condition: {valid_conditions[0]}")
            ebay_condition = valid_conditions[0]

        # Build base payload
        payload = {
            "availability": {
                "shipToLocationAvailability": {
                    "quantity": listing.quantity
                }
            },
            "condition": ebay_condition,
            "conditionDescription": f"Condition: {ebay_condition.replace('_', ' ').title()}",
            "product": {
                "title": listing.title,
                "description": listing.description
            }
        }

        # Map and add item specifics if we have them
        if item_specifics:
            # Get AI-extracted attributes and product details from the ProductAnalysis record
            ai_attributes = None
            product_name = ""
            brand = None
            model_number = None

            if listing.analysis_id:
                try:
                    from database_models import ProductAnalysis
                    analysis = self.db.query(ProductAnalysis).filter(
                        ProductAnalysis.id == listing.analysis_id
                    ).first()

                    if analysis:
                        # Get product details from analysis
                        product_name = analysis.ai_product_name or ""
                        brand = analysis.ai_brand
                        model_number = analysis.ai_model_number

                        # Build ai_attributes dict from analysis columns
                        ai_attributes = {}

                        if analysis.ai_color:
                            ai_attributes["Color"] = analysis.ai_color
                        if analysis.ai_material:
                            ai_attributes["Material"] = analysis.ai_material
                        if analysis.ai_category:
                            # Try to infer Type from category
                            ai_attributes["Type"] = analysis.ai_category
                        if analysis.ai_features:
                            # Parse features from JSON if needed
                            features = analysis.ai_features
                            if isinstance(features, str):
                                try:
                                    features = json.loads(features)
                                except:
                                    pass
                            if features:
                                ai_attributes["Features"] = features

                        logger.info(f"Built ai_attributes from analysis {listing.analysis_id}: {list(ai_attributes.keys()) if ai_attributes else 'None'}")
                except Exception as e:
                    logger.warning(f"Could not fetch/parse analysis data: {e}")

            # Prepare listing data for mapping
            listing_data = {
                "product_name": product_name,
                "brand": brand,
                "model_number": model_number
            }

            logger.info(f"Listing data for mapping: product_name='{product_name}', brand='{brand}', model='{model_number}'")

            # Map AI attributes to eBay item specifics
            aspects = self._map_attributes_to_item_specifics(
                ai_attributes or {},
                item_specifics,
                listing_data
            )

            # Merge with user-provided item specifics (user values take precedence)
            if listing.item_specifics:
                logger.info(f"Merging {len(listing.item_specifics)} user-provided item specifics")
                for key, value in listing.item_specifics.items():
                    # Only add non-empty values
                    if value:
                        # eBay aspects format expects arrays
                        if isinstance(value, list):
                            aspects[key] = value
                        else:
                            aspects[key] = [str(value)]
                        logger.info(f"User-provided aspect: {key} = {aspects[key]}")

            logger.info(f"Final aspects: {list(aspects.keys()) if aspects else 'None'}")
            if aspects and 'Brand' in aspects:
                logger.info(f"Brand value in aspects: {aspects['Brand']}")
            else:
                logger.warning("Brand not found in mapped aspects!")

            if aspects:
                payload["product"]["aspects"] = aspects
                logger.info(f"Added {len(aspects)} item specifics to inventory payload")
            else:
                logger.warning("No item specifics could be mapped from AI data or user input")

        # Only include imageUrls if we have them (eBay requires at least 1 if provided)
        if listing.image_urls and len(listing.image_urls) > 0:
            payload["product"]["imageUrls"] = listing.image_urls
            logger.info(f"Added {len(listing.image_urls)} image URL(s) to inventory payload: {listing.image_urls}")
        else:
            logger.warning("No image URLs available for inventory item - eBay requires at least 1 photo")

        # Add packageWeightAndSize if shipping weight/dimensions are provided
        # This is required for calculated shipping policies
        if listing.shipping_weight_major or listing.shipping_weight_minor:
            # Calculate total weight in pounds
            major = int(float(listing.shipping_weight_major)) if listing.shipping_weight_major else 0
            minor = int(float(listing.shipping_weight_minor)) if listing.shipping_weight_minor else 0
            total_weight_lbs = float(major) + (float(minor) / 16.0)

            # eBay minimum weight validation (at least 0.1 lbs)
            if total_weight_lbs < 0.1:
                total_weight_lbs = 0.1

            # Round to 2 decimal places
            total_weight_lbs = round(total_weight_lbs, 2)

            package_weight_and_size = {
                "weight": {
                    "value": total_weight_lbs,
                    "unit": "POUND"
                },
                "packageType": "PACKAGE_THICK_ENVELOPE",
                "shippingIrregular": False
            }

            # Add dimensions if provided
            if listing.shipping_length and listing.shipping_width and listing.shipping_height:
                length = round(float(listing.shipping_length), 2)
                width = round(float(listing.shipping_width), 2)
                height = round(float(listing.shipping_height), 2)

                package_weight_and_size["dimensions"] = {
                    "length": length,
                    "width": width,
                    "height": height,
                    "unit": "INCH"
                }
                logger.info(f"Added packageWeightAndSize to inventory with dimensions: {length}x{width}x{height} inches, {total_weight_lbs} lbs")
            else:
                logger.info(f"Added packageWeightAndSize to inventory with weight only: {total_weight_lbs} lbs")

            payload["packageWeightAndSize"] = package_weight_and_size

        # Make API call
        url = f"{self.api_url}/sell/inventory/v1/inventory_item/{listing.sku}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Content-Language": "en-US"
        }

        # Log the full payload for debugging
        logger.info(f"Inventory item payload: {json.dumps(payload, indent=2)}")

        try:
            response = requests.put(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()

            # Log the response to see if eBay provides any warnings
            response_data = response.json() if response.text else {}
            logger.info(f"Inventory item creation response: {json.dumps(response_data, indent=2)}")
            logger.info(f"Inventory item created successfully for SKU: {listing.sku}")

            # Verify what eBay stored by fetching the inventory item back
            try:
                verify_url = f"{self.api_url}/sell/inventory/v1/inventory_item/{listing.sku}"
                verify_response = requests.get(verify_url, headers=headers, timeout=30)
                if verify_response.ok:
                    stored_data = verify_response.json()
                    logger.info(f"Verified inventory item aspects from eBay: {stored_data.get('product', {}).get('aspects', {})}")
                else:
                    logger.warning(f"Could not verify inventory item: {verify_response.status_code}")
            except Exception as verify_error:
                logger.warning(f"Failed to verify inventory item: {verify_error}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Inventory creation failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"eBay error response: {error_data}")
                    error_msg = error_data.get('errors', [{}])[0].get('message', str(e))
                    raise Exception(f"eBay inventory creation error: {error_msg}")
                except:
                    pass
            raise Exception(f"Failed to create inventory item: {str(e)}")

    def _get_fulfillment_policy_details(self, policy_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific fulfillment policy.

        Args:
            policy_id: The fulfillment policy ID
            user_id: User identifier

        Returns:
            Policy details dict, or None if fetch fails
        """
        token = self.oauth_service.get_valid_token(user_id)
        if not token:
            return None

        url = f"{self.api_url}/sell/account/v1/fulfillment_policy/{policy_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Could not fetch fulfillment policy details: {e}")
            return None

    def _policy_requires_shipping_weight(self, policy_details: Dict[str, Any]) -> bool:
        """
        Check if a fulfillment policy requires shipping weight (calculated shipping).

        Args:
            policy_details: Fulfillment policy details from eBay API

        Returns:
            True if policy uses calculated shipping and needs weight
        """
        if not policy_details:
            return False

        # Check shipping options for calculated shipping
        shipping_options = policy_details.get("shippingOptions", [])
        for option in shipping_options:
            rate_type = option.get("rateType", "")
            if rate_type == "CALCULATED":
                logger.info("Fulfillment policy uses CALCULATED shipping - weight required")
                return True

        logger.info("Fulfillment policy uses FLAT_RATE shipping - weight not required")
        return False

    def get_all_business_policies(self, user_id: str, marketplace_id: str = "EBAY_US") -> Dict[str, Any]:
        """
        Get all business policies (fulfillment, payment, return) for a user.

        Args:
            user_id: User identifier
            marketplace_id: eBay marketplace ID (default: EBAY_US)

        Returns:
            Dict containing fulfillment_policies, payment_policies, and return_policies lists

        Raises:
            Exception: If fetching policies fails
        """
        token = self.oauth_service.get_valid_token(user_id)
        if not token:
            raise Exception("No valid OAuth token available")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        result = {
            "fulfillment_policies": [],
            "payment_policies": [],
            "return_policies": []
        }

        try:
            # Fetch fulfillment policies
            fulfillment_url = f"{self.api_url}/sell/account/v1/fulfillment_policy?marketplace_id={marketplace_id}"
            logger.info(f"Fetching fulfillment policies from: {fulfillment_url}")
            fulfillment_response = requests.get(fulfillment_url, headers=headers, timeout=30)

            if not fulfillment_response.ok:
                error_detail = fulfillment_response.text
                try:
                    error_json = fulfillment_response.json()
                    error_detail = json.dumps(error_json, indent=2)
                except:
                    pass
                logger.error(f"Fulfillment policy fetch failed: {fulfillment_response.status_code} - {error_detail}")

            fulfillment_response.raise_for_status()
            fulfillment_data = fulfillment_response.json()
            result["fulfillment_policies"] = fulfillment_data.get("fulfillmentPolicies", [])
            logger.info(f"Fetched {len(result['fulfillment_policies'])} fulfillment policies")

            # Fetch payment policies
            payment_url = f"{self.api_url}/sell/account/v1/payment_policy?marketplace_id={marketplace_id}"
            logger.info(f"Fetching payment policies from: {payment_url}")
            payment_response = requests.get(payment_url, headers=headers, timeout=30)

            if not payment_response.ok:
                error_detail = payment_response.text
                try:
                    error_json = payment_response.json()
                    error_detail = json.dumps(error_json, indent=2)
                except:
                    pass
                logger.error(f"Payment policy fetch failed: {payment_response.status_code} - {error_detail}")

            payment_response.raise_for_status()
            payment_data = payment_response.json()
            result["payment_policies"] = payment_data.get("paymentPolicies", [])
            logger.info(f"Fetched {len(result['payment_policies'])} payment policies")

            # Fetch return policies
            return_url = f"{self.api_url}/sell/account/v1/return_policy?marketplace_id={marketplace_id}"
            logger.info(f"Fetching return policies from: {return_url}")
            return_response = requests.get(return_url, headers=headers, timeout=30)

            if not return_response.ok:
                error_detail = return_response.text
                try:
                    error_json = return_response.json()
                    error_detail = json.dumps(error_json, indent=2)
                except:
                    pass
                logger.error(f"Return policy fetch failed: {return_response.status_code} - {error_detail}")

            return_response.raise_for_status()
            return_data = return_response.json()
            result["return_policies"] = return_data.get("returnPolicies", [])
            logger.info(f"Fetched {len(result['return_policies'])} return policies")

            logger.info(f"Successfully fetched all business policies - Fulfillment: {len(result['fulfillment_policies'])}, "
                       f"Payment: {len(result['payment_policies'])}, Return: {len(result['return_policies'])}")

            return result

        except requests.exceptions.HTTPError as e:
            error_detail = str(e)
            if e.response is not None:
                try:
                    error_json = e.response.json()
                    error_detail = f"Status {e.response.status_code}: {json.dumps(error_json, indent=2)}"
                except:
                    error_detail = f"Status {e.response.status_code}: {e.response.text}"

            logger.error(f"HTTP error fetching business policies: {error_detail}")
            raise Exception(f"Failed to fetch business policies: {error_detail}")
        except Exception as e:
            logger.error(f"Error fetching business policies: {e}", exc_info=True)
            raise Exception(f"Failed to fetch business policies: {str(e)}")

    def _create_offer(self, listing: EbayListing, user_id: str) -> str:
        """
        Create offer for inventory item.

        Args:
            listing: Listing database record
            user_id: User identifier

        Returns:
            eBay offer ID

        Raises:
            Exception: If offer creation fails
        """
        logger.info(f"Creating offer for SKU: {listing.sku}")

        # Get valid OAuth token
        token = self.oauth_service.get_valid_token(user_id)
        if not token:
            raise ValueError("No valid eBay authentication token")

        # Get business policies
        logger.info("Fetching business policies from eBay")
        fulfillment_policies = self._get_fulfillment_policies(user_id)
        payment_policies = self._get_payment_policies(user_id)
        return_policies = self._get_return_policies(user_id)

        # Use first available policy of each type, or env defaults
        fulfillment_policy_id = (
            self.default_shipping_policy_id or
            (fulfillment_policies[0].get("fulfillmentPolicyId") if fulfillment_policies else None)
        )
        payment_policy_id = (
            self.default_payment_policy_id or
            (payment_policies[0].get("paymentPolicyId") if payment_policies else None)
        )
        return_policy_id = (
            self.default_return_policy_id or
            (return_policies[0].get("returnPolicyId") if return_policies else None)
        )

        # Validate we have all required policies
        if not fulfillment_policy_id:
            raise Exception(
                "No fulfillment (shipping) policy found. "
                "Please create business policies in your eBay Sandbox account:\n"
                "1. Go to https://www.sandbox.ebay.com/\n"
                "2. Sign in with your sandbox account\n"
                "3. Go to Account Settings > Business Policies\n"
                "4. Create a Shipping Policy, Payment Policy, and Return Policy"
            )
        if not payment_policy_id:
            raise Exception(
                "No payment policy found. "
                "Please create business policies in your eBay Sandbox account:\n"
                "1. Go to https://www.sandbox.ebay.com/\n"
                "2. Sign in with your sandbox account\n"
                "3. Go to Account Settings > Business Policies\n"
                "4. Create a Shipping Policy, Payment Policy, and Return Policy"
            )
        if not return_policy_id:
            raise Exception(
                "No return policy found. "
                "Please create business policies in your eBay Sandbox account:\n"
                "1. Go to https://www.sandbox.ebay.com/\n"
                "2. Sign in with your sandbox account\n"
                "3. Go to Account Settings > Business Policies\n"
                "4. Create a Shipping Policy, Payment Policy, and Return Policy"
            )

        logger.info(f"Using policies - Fulfillment: {fulfillment_policy_id}, Payment: {payment_policy_id}, Return: {return_policy_id}")

        # Check if fulfillment policy requires shipping weight (calculated shipping)
        policy_details = self._get_fulfillment_policy_details(fulfillment_policy_id, user_id)
        requires_weight = self._policy_requires_shipping_weight(policy_details)

        # If policy requires weight and we don't have it, raise an error
        if requires_weight and not listing.shipping_weight_major:
            raise Exception(
                "This fulfillment policy uses calculated shipping and requires package weight. "
                "Please provide shipping weight (in pounds and ounces) for this listing."
            )

        # Build offer payload
        payload = {
            "sku": listing.sku,
            "marketplaceId": "EBAY_US",
            "format": "FIXED_PRICE",
            "listingDescription": listing.description,
            "availableQuantity": listing.quantity,
            "categoryId": listing.category_id,
            "listingPolicies": {
                "fulfillmentPolicyId": fulfillment_policy_id,
                "paymentPolicyId": payment_policy_id,
                "returnPolicyId": return_policy_id
            },
            "pricingSummary": {
                "price": {
                    "value": round(float(listing.price), 2),
                    "currency": "USD"
                }
            },
            "quantityLimitPerBuyer": 10
        }

        # Add merchant location key (required for shipping)
        # In sandbox, we need to create a location or use a default one
        payload["merchantLocationKey"] = "DEFAULT_LOCATION"

        # Add shipping package details ONLY if policy requires it (calculated shipping)
        logger.info(f"Shipping weight check - Major: {listing.shipping_weight_major}, Minor: {listing.shipping_weight_minor}")
        logger.info(f"Policy requires weight: {requires_weight}")

        # Only include shippingPackageDetails if the policy uses CALCULATED shipping
        if requires_weight and (listing.shipping_weight_major or listing.shipping_weight_minor):
            # Calculate total weight in pounds
            # NOTE: Frontend may send decimal values, but we need to treat them as integers
            # Example: 1.01 should be treated as 1 pound, 1.1 should be treated as 1 ounce
            major = int(float(listing.shipping_weight_major)) if listing.shipping_weight_major else 0
            minor = int(float(listing.shipping_weight_minor)) if listing.shipping_weight_minor else 0

            # Convert to total pounds: major pounds + (minor ounces / 16)
            total_weight_lbs = float(major) + (float(minor) / 16.0)

            logger.info(f"Weight conversion - Input: {listing.shipping_weight_major} lbs, {listing.shipping_weight_minor} oz")
            logger.info(f"Weight conversion - Converted to: {major} lbs, {minor} oz")
            logger.info(f"Calculated total weight: {total_weight_lbs} lbs")

            # eBay minimum weight validation (at least 0.1 lbs)
            if total_weight_lbs < 0.1:
                logger.warning(f"Weight {total_weight_lbs} lbs is below eBay minimum, using 0.1 lbs")
                total_weight_lbs = 0.1

            # Round to 2 decimal places for eBay API
            total_weight_lbs = round(total_weight_lbs, 2)

            shipping_package = {
                "weight": {
                    "value": total_weight_lbs,
                    "unit": "POUND"
                },
                "packageType": "PACKAGE_THICK_ENVELOPE",
                "shippingIrregular": False
            }

            # Add dimensions if provided (required for calculated shipping)
            if listing.shipping_length and listing.shipping_width and listing.shipping_height:
                # Round dimensions to 2 decimal places
                length = round(float(listing.shipping_length), 2)
                width = round(float(listing.shipping_width), 2)
                height = round(float(listing.shipping_height), 2)

                shipping_package["dimensions"] = {
                    "length": length,
                    "width": width,
                    "height": height,
                    "unit": "INCH"
                }
                logger.info(f"Added dimensions to offer: {length}x{width}x{height} inches")

            payload["packageWeightAndSize"] = shipping_package
            logger.info(f"Package weight and size payload: {json.dumps(shipping_package, indent=2)}")
        else:
            logger.warning("No shipping weight provided - may fail if using calculated shipping policy")

        # Make API call
        url = f"{self.api_url}/sell/inventory/v1/offer"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Content-Language": "en-US"
        }

        # Log environment and API details
        logger.info(f"=== eBay API Call Details ===")
        logger.info(f"Environment: {self.environment}")
        logger.info(f"API Base URL: {self.api_url}")
        logger.info(f"Full Endpoint: {url}")
        logger.info(f"Offer Payload: {json.dumps(payload, indent=2)}")
        logger.info(f"=============================")

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()

            offer_data = response.json()
            offer_id = offer_data.get("offerId")

            if not offer_id:
                raise Exception("eBay did not return offer ID")

            logger.info(f"Offer created successfully: {offer_id}")
            return offer_id

        except requests.exceptions.RequestException as e:
            logger.error(f"Offer creation failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"eBay error response: {error_data}")
                    error_msg = error_data.get('errors', [{}])[0].get('message', str(e))
                    raise Exception(f"eBay offer creation error: {error_msg}")
                except:
                    pass
            raise Exception(f"Failed to create offer: {str(e)}")

    def _publish_listing(self, offer_id: str, user_id: str) -> str:
        """
        Publish offer to create live listing.

        Args:
            offer_id: eBay offer ID
            user_id: User identifier

        Returns:
            eBay listing ID

        Raises:
            Exception: If publishing fails
        """
        logger.info(f"Publishing offer: {offer_id}")

        # Get valid OAuth token
        token = self.oauth_service.get_valid_token(user_id)
        if not token:
            raise ValueError("No valid eBay authentication token")

        # Make API call
        url = f"{self.api_url}/sell/inventory/v1/offer/{offer_id}/publish"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Content-Language": "en-US"
        }

        try:
            response = requests.post(url, headers=headers, json={}, timeout=60)
            response.raise_for_status()

            publish_data = response.json()
            listing_id = publish_data.get("listingId")

            if not listing_id:
                raise Exception("eBay did not return listing ID")

            logger.info(f"Listing published successfully: {listing_id}")
            return listing_id

        except requests.exceptions.RequestException as e:
            logger.error(f"Listing publish failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"eBay error response: {json.dumps(error_data, indent=2)}")

                    # Extract detailed error message
                    errors = error_data.get('errors', [])
                    if errors:
                        error_details = []
                        for error in errors:
                            msg = error.get('message', '')
                            params = error.get('parameters', [])
                            if params:
                                param_info = ', '.join([f"{p.get('name')}: {p.get('value')}" for p in params])
                                error_details.append(f"{msg} ({param_info})")
                            else:
                                error_details.append(msg)
                        error_msg = '; '.join(error_details)
                    else:
                        error_msg = str(error_data)

                    raise Exception(f"eBay listing publish error: {error_msg}")
                except json.JSONDecodeError:
                    logger.error(f"Could not parse eBay error response: {e.response.text}")
                    raise Exception(f"Failed to publish listing: {str(e)}")
            raise Exception(f"Failed to publish listing: {str(e)}")

    def _update_listing_status(
        self,
        listing_id: int,
        status: ListingStatus,
        error: Optional[str] = None
    ):
        """Update listing status in database."""
        listing = self.db.query(EbayListing).filter(EbayListing.id == listing_id).first()
        if listing:
            listing.status = status
            listing.updated_at = datetime.utcnow()

            if error:
                listing.last_error = error

            self.db.commit()
            logger.info(f"Listing {listing_id} status updated to: {status}")

    def _log_failure(
        self,
        listing_id: int,
        stage: FailureStage,
        error_message: str,
        error_code: Optional[str] = None,
        error_details: Optional[Dict] = None,
        is_recoverable: bool = True
    ):
        """
        Log listing failure to database.

        Args:
            listing_id: Listing ID
            stage: Stage where failure occurred
            error_message: Error message
            error_code: Error code from eBay
            error_details: Full error response
            is_recoverable: Whether error can be recovered
        """
        logger.error(f"Logging failure for listing {listing_id}: {error_message}")

        failure = EbayListingFailure(
            listing_id=listing_id,
            failure_stage=stage,
            error_code=error_code,
            error_message=error_message,
            error_details=error_details,
            is_recoverable=1 if is_recoverable else 0
        )
        self.db.add(failure)
        self.db.commit()

    def _get_failure_stage_from_status(self, status: ListingStatus) -> FailureStage:
        """Map listing status to failure stage."""
        mapping = {
            ListingStatus.VALIDATING: FailureStage.VALIDATION,
            ListingStatus.UPLOADING_IMAGES: FailureStage.IMAGE_UPLOAD,
            ListingStatus.CREATING_INVENTORY: FailureStage.INVENTORY_CREATION,
            ListingStatus.CREATING_OFFER: FailureStage.OFFER_CREATION,
            ListingStatus.PUBLISHING: FailureStage.PUBLISH,
        }
        return mapping.get(status, FailureStage.UNKNOWN)

    def get_listing(self, listing_id: int) -> Optional[EbayListing]:
        """Get listing by ID."""
        return self.db.query(EbayListing).filter(EbayListing.id == listing_id).first()

    def get_listing_by_sku(self, sku: str) -> Optional[EbayListing]:
        """Get listing by SKU."""
        return self.db.query(EbayListing).filter(EbayListing.sku == sku).first()

    def retry_listing(self, listing_id: int, user_id: str = "default_user") -> EbayListing:
        """
        Retry a failed listing.

        Args:
            listing_id: Listing ID to retry
            user_id: User identifier

        Returns:
            Updated listing

        Raises:
            ValueError: If listing cannot be retried
        """
        listing = self.get_listing(listing_id)
        if not listing:
            raise ValueError(f"Listing {listing_id} not found")

        if listing.status != ListingStatus.FAILED:
            raise ValueError(f"Listing is not in failed status: {listing.status}")

        if listing.retry_count >= listing.max_retries:
            raise ValueError(f"Maximum retries ({listing.max_retries}) exceeded")

        # Increment retry count
        listing.retry_count += 1
        listing.last_retry_at = datetime.utcnow()
        listing.status = ListingStatus.DRAFT
        self.db.commit()

        logger.info(f"Retrying listing {listing_id} (attempt {listing.retry_count}/{listing.max_retries})")

        # Re-execute workflow
        try:
            self._execute_listing_workflow(listing, None, user_id)  # Images already uploaded
        except Exception as e:
            logger.error(f"Retry failed: {e}")
            raise

        return listing

    def get_all_active_offers(self, user_id: str = "default_user", limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Fetch all active offers from eBay Inventory API.

        Args:
            user_id: User identifier
            limit: Number of offers to fetch per page
            offset: Offset for pagination

        Returns:
            List of offer dictionaries from eBay API

        Raises:
            Exception: If API call fails
        """
        logger.info(f"Fetching active offers from eBay (limit={limit}, offset={offset})")

        # Get valid OAuth token
        token = self.oauth_service.get_valid_token(user_id)
        if not token:
            raise ValueError("No valid eBay authentication token")

        url = f"{self.api_url}/sell/inventory/v1/offer"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        params = {
            "limit": min(limit, 100),  # eBay max is 100
            "offset": offset
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            offers = data.get("offers", [])

            logger.info(f"Fetched {len(offers)} active offers from eBay")
            return offers

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch active offers: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"eBay error response: {json.dumps(error_data, indent=2)}")
                except:
                    pass
            raise Exception(f"Failed to fetch active offers from eBay: {str(e)}")

    def get_offer_details(self, offer_id: str, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Get detailed information about a specific offer including metrics.

        Args:
            offer_id: eBay offer ID
            user_id: User identifier

        Returns:
            Offer details dictionary

        Raises:
            Exception: If API call fails
        """
        logger.info(f"Fetching offer details for offer ID: {offer_id}")

        # Get valid OAuth token
        token = self.oauth_service.get_valid_token(user_id)
        if not token:
            raise ValueError("No valid eBay authentication token")

        url = f"{self.api_url}/sell/inventory/v1/offer/{offer_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            offer_data = response.json()
            logger.info(f"Fetched offer details for {offer_id}")
            return offer_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch offer details: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"eBay error response: {json.dumps(error_data, indent=2)}")
                except:
                    pass
            raise Exception(f"Failed to fetch offer details from eBay: {str(e)}")

    def get_listing_metrics(self, listing_id: str, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Get metrics (views, watchers) for a specific listing from eBay Analytics API.

        Note: eBay's Analytics API may not be available in all environments (sandbox/production).
        This method attempts to fetch metrics but will gracefully handle unavailability.

        Args:
            listing_id: eBay listing ID
            user_id: User identifier

        Returns:
            Dictionary with views and watchers count (defaults to 0 if unavailable)
        """
        logger.info(f"Fetching metrics for listing ID: {listing_id}")

        # Get valid OAuth token
        token = self.oauth_service.get_valid_token(user_id)
        if not token:
            logger.warning("No valid token for fetching metrics")
            return {"views": 0, "watchers": 0}

        # Try to fetch from eBay Marketing API (item promotion insights)
        # Note: This may require additional OAuth scopes
        url = f"{self.api_url}/sell/marketing/v1/item/{listing_id}/promotion_summary"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)

            if response.ok:
                data = response.json()
                views = data.get("impressionCount", 0)
                watchers = data.get("watcherCount", 0)

                logger.info(f"Fetched metrics for {listing_id}: views={views}, watchers={watchers}")
                return {"views": views, "watchers": watchers}
            else:
                logger.warning(f"Metrics API unavailable (status {response.status_code}), returning defaults")
                return {"views": 0, "watchers": 0}

        except Exception as e:
            logger.warning(f"Could not fetch metrics for {listing_id}: {e}")
            return {"views": 0, "watchers": 0}

    def sync_listings_from_ebay(self, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Sync active listings from eBay to local database.
        Updates metrics (views, watchers) and status for all published listings.

        Args:
            user_id: User identifier

        Returns:
            Dictionary with sync summary (listings_synced, errors, etc.)
        """
        logger.info("Starting eBay listings sync")

        summary = {
            "listings_synced": 0,
            "metrics_updated": 0,
            "errors": []
        }

        try:
            # Fetch all active offers from eBay
            offers = self.get_all_active_offers(user_id, limit=100, offset=0)

            for offer in offers:
                try:
                    offer_id = offer.get("offerId")
                    sku = offer.get("sku")
                    listing_id = offer.get("listingId")

                    if not sku:
                        logger.warning(f"Offer {offer_id} has no SKU, skipping")
                        continue

                    # Find corresponding listing in database
                    listing = self.get_listing_by_sku(sku)

                    if not listing:
                        logger.info(f"Listing with SKU {sku} not found in database, skipping")
                        continue

                    # Update listing data from eBay
                    if listing_id and not listing.listing_id:
                        listing.listing_id = listing_id

                    if offer_id and not listing.offer_id:
                        listing.offer_id = offer_id

                    # Update status
                    ebay_status = offer.get("status")
                    if ebay_status:
                        listing.ebay_status = ebay_status

                    # Update eBay listing URL
                    if listing_id and self.environment == "PRODUCTION":
                        listing.ebay_listing_url = f"https://www.ebay.com/itm/{listing_id}"
                    elif listing_id:
                        listing.ebay_listing_url = f"https://www.sandbox.ebay.com/itm/{listing_id}"

                    # Fetch and update metrics (if listing is published)
                    if listing_id:
                        metrics = self.get_listing_metrics(listing_id, user_id)
                        listing.views = metrics.get("views", 0)
                        listing.watchers = metrics.get("watchers", 0)
                        summary["metrics_updated"] += 1

                    listing.updated_at = datetime.utcnow()
                    self.db.commit()

                    summary["listings_synced"] += 1
                    logger.info(f"Synced listing {listing.sku} (ID: {listing.id})")

                except Exception as e:
                    error_msg = f"Error syncing offer {offer.get('offerId', 'unknown')}: {str(e)}"
                    logger.error(error_msg)
                    summary["errors"].append(error_msg)

            logger.info(f"Sync completed: {summary['listings_synced']} listings synced, "
                       f"{summary['metrics_updated']} metrics updated, {len(summary['errors'])} errors")

            return summary

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            raise Exception(f"Failed to sync listings from eBay: {str(e)}")

    def get_sold_orders(self, user_id: str = "default_user", limit: int = 50, created_from: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch sold orders from eBay Orders API.

        Args:
            user_id: User identifier
            limit: Number of orders to fetch
            created_from: ISO 8601 datetime string for filtering orders (e.g., "2025-01-01T00:00:00Z")

        Returns:
            List of order dictionaries from eBay API

        Raises:
            Exception: If API call fails
        """
        logger.info(f"Fetching sold orders from eBay (limit={limit})")

        # Get valid OAuth token
        token = self.oauth_service.get_valid_token(user_id)
        if not token:
            raise ValueError("No valid eBay authentication token")

        url = f"{self.api_url}/sell/fulfillment/v1/order"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        params = {
            "limit": min(limit, 200),  # eBay max is 200
            "filter": "orderfulfillmentstatus:{NOT_STARTED|IN_PROGRESS}"
        }

        # Add date filter if provided
        if created_from:
            params["filter"] = f"{params['filter']},creationdate:[{created_from}..]"

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            orders = data.get("orders", [])

            logger.info(f"Fetched {len(orders)} sold orders from eBay")
            return orders

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch sold orders: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"eBay error response: {json.dumps(error_data, indent=2)}")
                except:
                    pass
            raise Exception(f"Failed to fetch sold orders from eBay: {str(e)}")

    def update_sold_listings(self, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Update sold listings in database from eBay Orders API.
        Marks listings as sold and updates sold_quantity and sold_at timestamp.

        Args:
            user_id: User identifier

        Returns:
            Dictionary with update summary
        """
        logger.info("Updating sold listings from eBay")

        summary = {
            "orders_processed": 0,
            "listings_updated": 0,
            "errors": []
        }

        try:
            # Fetch recent sold orders (last 90 days)
            from datetime import timedelta
            ninety_days_ago = (datetime.utcnow() - timedelta(days=90)).isoformat() + "Z"
            orders = self.get_sold_orders(user_id, limit=200, created_from=ninety_days_ago)

            for order in orders:
                try:
                    order_id = order.get("orderId")
                    line_items = order.get("lineItems", [])

                    for item in line_items:
                        sku = item.get("sku")
                        quantity = item.get("quantity", 1)
                        listing_id = item.get("legacyItemId")  # eBay listing ID

                        if not sku:
                            continue

                        # Find listing in database
                        listing = self.get_listing_by_sku(sku)

                        if not listing:
                            logger.info(f"Listing with SKU {sku} not found in database")
                            continue

                        # Update sold information
                        if not listing.sold_quantity:
                            listing.sold_quantity = 0

                        listing.sold_quantity += quantity

                        # Set sold timestamp if this is the first sale
                        if not listing.sold_at:
                            order_date_str = order.get("creationDate")
                            if order_date_str:
                                # Parse ISO 8601 datetime
                                from datetime import datetime as dt
                                listing.sold_at = dt.fromisoformat(order_date_str.replace("Z", "+00:00"))

                        listing.updated_at = datetime.utcnow()
                        self.db.commit()

                        summary["listings_updated"] += 1
                        logger.info(f"Updated sold listing {listing.sku} (sold {quantity} units)")

                    summary["orders_processed"] += 1

                except Exception as e:
                    error_msg = f"Error processing order {order.get('orderId', 'unknown')}: {str(e)}"
                    logger.error(error_msg)
                    summary["errors"].append(error_msg)

            logger.info(f"Sold listings update completed: {summary['orders_processed']} orders processed, "
                       f"{summary['listings_updated']} listings updated, {len(summary['errors'])} errors")

            return summary

        except Exception as e:
            logger.error(f"Failed to update sold listings: {e}")
            raise Exception(f"Failed to update sold listings from eBay: {str(e)}")


# Helper function to get listing service instance
def get_ebay_listing_service(db: Session, oauth_service: EbayOAuthService) -> EbayListingService:
    """
    Factory function to create EbayListingService instance.

    Args:
        db: Database session
        oauth_service: OAuth service instance

    Returns:
        Configured EbayListingService instance
    """
    return EbayListingService(db, oauth_service)
