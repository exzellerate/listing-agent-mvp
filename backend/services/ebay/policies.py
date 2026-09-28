"""
eBay Business Policies Service

Lets a user create eBay business policies (fulfillment/shipping, payment,
return) directly from this app instead of eBay's own Seller Hub. Kept
separate from EbayListingService because that service's existing
_get_*_policies methods have a side effect (auto-creating a hardcoded
default policy when none exist) that must NOT be triggered just to check
for a name collision before a user-driven create.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
import requests

from .oauth import EbayOAuthService

logger = logging.getLogger(__name__)


class EbayPolicyError(Exception):
    """User-facing error from an eBay business-policy API call."""

    def __init__(self, message: str, status_code: int = 400, ebay_error_id: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.ebay_error_id = ebay_error_id


class EbayPoliciesService:
    """Create and list eBay business policies for a user's connected account."""

    def __init__(self, db: Session, oauth_service: EbayOAuthService):
        self.db = db
        self.oauth_service = oauth_service
        self.environment = os.getenv("EBAY_ENV", "SANDBOX")
        self.api_url = self._get_api_url()

    def _get_api_url(self) -> str:
        if self.environment == "PRODUCTION":
            return "https://api.ebay.com"
        return "https://api.sandbox.ebay.com"

    def _auth_headers(self, user_id: str) -> Dict[str, str]:
        token = self.oauth_service.get_valid_token(user_id)
        if not token:
            raise EbayPolicyError(
                "Your eBay connection has expired. Please reconnect your eBay account.",
                status_code=401
            )
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def _raise_friendly_error(self, response: requests.Response):
        """Translate an eBay error response into a friendly EbayPolicyError."""
        message = response.text
        ebay_error_id = None
        try:
            error_json = response.json()
            errors = error_json.get("errors") or []
            if errors:
                first = errors[0]
                ebay_error_id = first.get("errorId")
                message = first.get("longMessage") or first.get("message") or message
        except Exception:
            pass

        lowered = (message or "").lower()
        if "already exists" in lowered or "duplicate" in lowered:
            friendly = f"A policy with this name already exists. Choose a different name."
        elif (
            "not eligible for business policy" in lowered
            or ebay_error_id == 20403
            or ("opt" in lowered and ("program" in lowered or "business polic" in lowered))
        ):
            friendly = (
                "Your eBay account isn't opted in to eBay Business Policies yet. "
                'Click "Enable Business Policies" below, then try again.'
            )
        elif response.status_code == 401:
            friendly = "Your eBay connection has expired. Please reconnect your eBay account."
        else:
            friendly = message or "eBay rejected this policy. Please check the details and try again."

        logger.warning(f"eBay policy API error ({response.status_code}, errorId={ebay_error_id}): {message}")
        raise EbayPolicyError(friendly, status_code=400 if response.status_code < 500 else 502, ebay_error_id=ebay_error_id)

    def _post(self, path: str, payload: dict, user_id: str) -> dict:
        headers = self._auth_headers(user_id)
        url = f"{self.api_url}{path}"
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error calling eBay policy API ({url}): {e}")
            raise EbayPolicyError("Could not reach eBay. Please try again.", status_code=502)

        if not response.ok:
            self._raise_friendly_error(response)

        # eBay's opt-in endpoint (and some others) return 200/204 with an
        # empty body on success - don't choke trying to parse that as JSON.
        if not response.text:
            return {}
        return response.json()

    def _get(self, path: str, params: dict, user_id: str) -> dict:
        headers = self._auth_headers(user_id)
        url = f"{self.api_url}{path}"
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error calling eBay policy API ({url}): {e}")
            raise EbayPolicyError("Could not reach eBay. Please try again.", status_code=502)

        if not response.ok:
            self._raise_friendly_error(response)

        return response.json()

    # ------------------------------------------------------------------
    # Side-effect-free list methods (no auto-create-default fallback)
    # ------------------------------------------------------------------

    def list_fulfillment_policies(self, user_id: str, marketplace_id: str = "EBAY_US") -> List[dict]:
        data = self._get("/sell/account/v1/fulfillment_policy", {"marketplace_id": marketplace_id}, user_id)
        return data.get("fulfillmentPolicies", [])

    def list_payment_policies(self, user_id: str, marketplace_id: str = "EBAY_US") -> List[dict]:
        data = self._get("/sell/account/v1/payment_policy", {"marketplace_id": marketplace_id}, user_id)
        return data.get("paymentPolicies", [])

    def list_return_policies(self, user_id: str, marketplace_id: str = "EBAY_US") -> List[dict]:
        data = self._get("/sell/account/v1/return_policy", {"marketplace_id": marketplace_id}, user_id)
        return data.get("returnPolicies", [])

    # ------------------------------------------------------------------
    # Create methods
    # ------------------------------------------------------------------

    def create_fulfillment_policy(
        self,
        user_id: str,
        name: str,
        handling_time_days: int = 1,
        free_shipping: bool = False,
        shipping_cost: Optional[float] = None,
        marketplace_id: str = "EBAY_US"
    ) -> dict:
        shipping_service: Dict[str, Any] = {
            "shippingCarrierCode": "USPS",
            "shippingServiceCode": "USPSPriority",
            "sortOrder": 1,
            "freeShipping": free_shipping
        }
        if not free_shipping:
            cost = shipping_cost if shipping_cost is not None else 10.00
            shipping_service["shippingCost"] = {"value": f"{cost:.2f}", "currency": "USD"}

        payload = {
            "name": name,
            "marketplaceId": marketplace_id,
            "categoryTypes": [{"name": "ALL_EXCLUDING_MOTORS_VEHICLES"}],
            "handlingTime": {"value": handling_time_days, "unit": "BUSINESS_DAY"},
            "shippingOptions": [
                {
                    "costType": "FLAT_RATE",
                    "shippingServices": [shipping_service],
                    "optionType": "DOMESTIC"
                }
            ],
            "shipToLocations": {
                "regionIncluded": [{"regionName": "DOMESTIC", "regionType": "COUNTRY"}]
            }
        }
        return self._post("/sell/account/v1/fulfillment_policy", payload, user_id)

    def create_payment_policy(
        self,
        user_id: str,
        name: str,
        immediate_pay_required: bool = False,
        marketplace_id: str = "EBAY_US"
    ) -> dict:
        payload = {
            "name": name,
            "marketplaceId": marketplace_id,
            "categoryTypes": [{"name": "ALL_EXCLUDING_MOTORS_VEHICLES"}],
            "immediatePay": immediate_pay_required
        }
        return self._post("/sell/account/v1/payment_policy", payload, user_id)

    def create_return_policy(
        self,
        user_id: str,
        name: str,
        returns_accepted: bool = True,
        return_period_days: int = 30,
        refund_method: str = "MONEY_BACK",
        return_shipping_payer: str = "BUYER",
        marketplace_id: str = "EBAY_US"
    ) -> dict:
        payload: Dict[str, Any] = {
            "name": name,
            "marketplaceId": marketplace_id,
            "categoryTypes": [{"name": "ALL_EXCLUDING_MOTORS_VEHICLES"}],
            "returnsAccepted": returns_accepted
        }
        if returns_accepted:
            payload["returnPeriod"] = {"value": return_period_days, "unit": "DAY"}
            payload["refundMethod"] = refund_method
            payload["returnShippingCostPayer"] = return_shipping_payer
        return self._post("/sell/account/v1/return_policy", payload, user_id)

    # ------------------------------------------------------------------
    # Program opt-in (some eBay accounts must opt in before ANY business
    # policy call - read or write - will succeed; eBay returns errorId
    # 20403 "User is not eligible for Business Policy" until they do)
    # ------------------------------------------------------------------

    def opt_in_to_business_policies(self, user_id: str) -> dict:
        payload = {"programType": "SELLING_POLICY_MANAGEMENT"}
        return self._post("/sell/account/v1/program/opt_in", payload, user_id)


def get_ebay_policies_service(db: Session, oauth_service: EbayOAuthService) -> EbayPoliciesService:
    """Factory function to create EbayPoliciesService instance."""
    return EbayPoliciesService(db, oauth_service)
