"""
eBay Sell Metadata API — item condition policies.

Valid conditions are category-specific and are NOT exposed by the Taxonomy
aspects endpoint. They come from get_item_condition_policies.
"""

import os
import time
import logging
from typing import Optional, List, Dict, Any

import requests

logger = logging.getLogger(__name__)

MARKETPLACE_ID = "EBAY_US"
CACHE_TTL_SECONDS = 24 * 60 * 60

# eBay numeric conditionId -> Inventory API condition enum
CONDITION_ID_TO_ENUM = {
    "1000": "NEW",
    "1500": "NEW_OTHER",
    "1750": "NEW_WITH_DEFECTS",
    "2000": "CERTIFIED_REFURBISHED",
    "2010": "EXCELLENT_REFURBISHED",
    "2020": "VERY_GOOD_REFURBISHED",
    "2030": "GOOD_REFURBISHED",
    "2500": "SELLER_REFURBISHED",
    "2750": "LIKE_NEW",
    "3000": "USED_EXCELLENT",
    "4000": "USED_VERY_GOOD",
    "5000": "USED_GOOD",
    "6000": "USED_ACCEPTABLE",
    "7000": "FOR_PARTS_OR_NOT_WORKING",
}

# Best -> worst. Used to snap a condition to the nearest allowed one.
CONDITION_SEVERITY = [
    "NEW",
    "NEW_OTHER",
    "NEW_WITH_DEFECTS",
    "CERTIFIED_REFURBISHED",
    "EXCELLENT_REFURBISHED",
    "VERY_GOOD_REFURBISHED",
    "GOOD_REFURBISHED",
    "SELLER_REFURBISHED",
    "LIKE_NEW",
    "USED_EXCELLENT",
    "USED_VERY_GOOD",
    "USED_GOOD",
    "USED_ACCEPTABLE",
    "FOR_PARTS_OR_NOT_WORKING",
]

# Free text (UI labels, Claude output) -> enum. Keys are upper-case.
CONDITION_TEXT_TO_ENUM = {
    **{e: e for e in CONDITION_SEVERITY},
    "NEW": "NEW",
    "BRAND NEW": "NEW",
    "NEW - OTHER": "NEW_OTHER",
    "OPEN BOX": "NEW_OTHER",
    "NEW WITH DEFECTS": "NEW_WITH_DEFECTS",
    "LIKE NEW": "LIKE_NEW",
    "USED - LIKE NEW": "LIKE_NEW",
    "USED - EXCELLENT": "USED_EXCELLENT",
    "EXCELLENT": "USED_EXCELLENT",
    "USED - VERY GOOD": "USED_VERY_GOOD",
    "VERY GOOD": "USED_VERY_GOOD",
    "USED - GOOD": "USED_GOOD",
    "GOOD": "USED_GOOD",
    "PRE-OWNED": "USED_GOOD",
    "USED": "USED_GOOD",
    "USED - FAIR": "USED_ACCEPTABLE",
    "USED - ACCEPTABLE": "USED_ACCEPTABLE",
    "FAIR": "USED_ACCEPTABLE",
    "ACCEPTABLE": "USED_ACCEPTABLE",
    "FOR PARTS": "FOR_PARTS_OR_NOT_WORKING",
    "FOR PARTS OR NOT WORKING": "FOR_PARTS_OR_NOT_WORKING",
    "REFURBISHED": "SELLER_REFURBISHED",
    "SELLER REFURBISHED": "SELLER_REFURBISHED",
    "CERTIFIED REFURBISHED": "CERTIFIED_REFURBISHED",
}

# category_id -> (fetched_at, result)
_cache: Dict[str, tuple] = {}


def normalize_condition(raw: Optional[str]) -> Optional[str]:
    """Map free text or an enum to an Inventory API condition enum, or None if unrecognised."""
    if not raw:
        return None
    key = raw.strip().upper()
    return CONDITION_TEXT_TO_ENUM.get(key) or CONDITION_TEXT_TO_ENUM.get(key.replace("_", " "))


def snap_condition(enum: str, allowed: List[str]) -> Optional[str]:
    """
    Return `enum` if allowed, else the nearest allowed condition, preferring
    equal-or-worse so a listing is never silently upgraded. Falls back to the
    nearest better one only if nothing worse exists.
    """
    if enum in allowed:
        return enum
    if enum not in CONDITION_SEVERITY:
        return None
    idx = CONDITION_SEVERITY.index(enum)
    for cand in CONDITION_SEVERITY[idx + 1:]:
        if cand in allowed:
            return cand
    for cand in reversed(CONDITION_SEVERITY[:idx]):
        if cand in allowed:
            return cand
    return None


def parse_condition_policies(data: Dict[str, Any], category_id: str) -> Dict[str, Any]:
    """Parse a get_item_condition_policies response for one category."""
    policy = None
    for p in data.get("itemConditionPolicies", []):
        if str(p.get("categoryId")) == str(category_id):
            policy = p
            break
    if policy is None and data.get("itemConditionPolicies"):
        policy = data["itemConditionPolicies"][0]
    if policy is None:
        return {"required": False, "conditions": []}

    conditions = []
    for c in policy.get("itemConditions", []):
        enum = CONDITION_ID_TO_ENUM.get(str(c.get("conditionId")))
        if not enum:
            logger.warning(f"Unknown eBay conditionId {c.get('conditionId')} in category {category_id}")
            continue
        conditions.append({
            "id": str(c["conditionId"]),
            "enum": enum,
            "label": c.get("conditionDescription") or enum.replace("_", " ").title(),
        })
    return {"required": bool(policy.get("itemConditionRequired", False)), "conditions": conditions}


def get_item_conditions(category_id: str, app_token: str) -> Optional[Dict[str, Any]]:
    """
    Fetch valid conditions for a category.

    Returns {"required": bool, "conditions": [{"id", "enum", "label"}]}, or
    None if eBay could not be reached (caller must treat the list as unknown).
    """
    cached = _cache.get(str(category_id))
    if cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    base = "https://api.ebay.com" if os.getenv("EBAY_ENV", "SANDBOX") == "PRODUCTION" else "https://api.sandbox.ebay.com"
    url = f"{base}/sell/metadata/v1/marketplace/{MARKETPLACE_ID}/get_item_condition_policies"
    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {app_token}", "Accept": "application/json"},
            params={"filter": f"categoryIds:{{{category_id}}}"},
            timeout=30,
        )
        response.raise_for_status()
        result = parse_condition_policies(response.json(), category_id)
    except Exception as e:
        logger.warning(f"Could not fetch item condition policy for category {category_id}: {e}")
        return None

    # Only cache non-empty results; an empty list is likely a transient/sandbox gap.
    if result["conditions"]:
        _cache[str(category_id)] = (time.time(), result)
    return result
