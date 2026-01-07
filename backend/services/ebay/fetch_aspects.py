#!/usr/bin/env python3
"""
eBay Item Aspects Fetcher

Fetches item-specific aspects (item specifics) for eBay categories using
the Taxonomy API. Aspects are cached locally for offline use during listing
creation.

Usage:
    python fetch_aspects.py --category-id 15708
    python fetch_aspects.py --category-ids 15708,15709,15710
    python fetch_aspects.py --prewarm-top 100
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()


class EbayAspectFetcher:
    """Fetches and caches eBay item aspects for categories."""

    # eBay API endpoints
    SANDBOX_BASE = "https://api.sandbox.ebay.com"
    PRODUCTION_BASE = "https://api.ebay.com"

    # OAuth endpoint
    OAUTH_BASE = "https://api.ebay.com/identity/v1/oauth2/token"
    OAUTH_SANDBOX_BASE = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"

    # Batch size limit from eBay API
    MAX_CATEGORIES_PER_REQUEST = 20

    def __init__(self,
                 marketplace_id: str = "0",
                 sandbox: bool = False,
                 cache_dir: str = "data/aspects"):
        """
        Initialize aspect fetcher.

        Args:
            marketplace_id: eBay marketplace ID (0 = US)
            sandbox: Use sandbox environment
            cache_dir: Directory for caching aspect data
        """
        self.marketplace_id = marketplace_id
        self.sandbox = sandbox
        self.base_url = self.SANDBOX_BASE if sandbox else self.PRODUCTION_BASE
        self.oauth_url = self.OAUTH_SANDBOX_BASE if sandbox else self.OAUTH_BASE
        self.cache_dir = Path(cache_dir)

        # Get credentials from environment
        self.app_id = os.getenv("EBAY_APP_ID") or os.getenv("EBAY_CLIENT_ID")
        self.cert_id = os.getenv("EBAY_CERT_ID") or os.getenv("EBAY_CLIENT_SECRET")

        if not self.app_id or not self.cert_id:
            raise ValueError(
                "EBAY_APP_ID (or EBAY_CLIENT_ID) and EBAY_CERT_ID "
                "(or EBAY_CLIENT_SECRET) must be set in .env file"
            )

        self.access_token = None

        # Create cache directories
        self._setup_cache_dirs()

    def _setup_cache_dirs(self):
        """Create cache directory structure."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "by_category").mkdir(exist_ok=True)

        # Initialize metadata file if it doesn't exist
        metadata_file = self.cache_dir / "aspects_metadata.json"
        if not metadata_file.exists():
            with open(metadata_file, 'w') as f:
                json.dump({
                    "created_at": datetime.now().isoformat(),
                    "marketplace_id": self.marketplace_id,
                    "cached_categories": {}
                }, f, indent=2)

    def get_oauth_token(self) -> str:
        """Get OAuth 2.0 access token using Client Credentials flow."""
        print("🔑 Obtaining OAuth access token...")

        auth = (self.app_id, self.cert_id)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope"
        }

        try:
            response = requests.post(
                self.oauth_url,
                auth=auth,
                headers=headers,
                data=data,
                timeout=30
            )
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 7200)

            print(f"✅ Access token obtained (expires in {expires_in}s)")
            return self.access_token

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to obtain access token: {e}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            raise

    def fetch_all_aspects_bulk(self) -> Dict:
        """
        Fetch ALL item aspects for the marketplace using bulk endpoint.

        This returns a comprehensive file of all metadata for every leaf category.
        The response is GZIP-compressed and can be hundreds of megabytes.

        Returns:
            Dictionary with all aspect data for all categories
        """
        if not self.access_token:
            self.get_oauth_token()

        print(f"📥 Fetching ALL aspects for marketplace {self.marketplace_id} (bulk fetch)...")
        print("⚠️  This may take a while - downloading comprehensive aspect data...")

        url = (
            f"{self.base_url}/commerce/taxonomy/v1/"
            f"category_tree/{self.marketplace_id}/fetch_item_aspects"
        )

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip"  # Required for bulk aspects
        }

        try:
            response = requests.get(url, headers=headers, timeout=300, stream=True)
            response.raise_for_status()

            # Debug: Print response info
            print(f"📋 Response status: {response.status_code}")
            print(f"📋 Response headers: {dict(response.headers)}")
            print(f"📋 Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            print(f"📋 Content-Length: {response.headers.get('Content-Length', 'N/A')}")

            # Parse the JSON response
            print("📦 Downloading and parsing aspect data...")

            # Read response text first to see what we got
            response_text = response.text
            if not response_text:
                raise ValueError("Empty response from API")

            print(f"📋 Response preview (first 500 chars): {response_text[:500]}")

            data = response.json()

            # Count aspects
            aspects_by_category = data.get("categoryTreeNodeAspects", [])
            print(f"✅ Fetched aspects for {len(aspects_by_category)} categories")

            return data

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to fetch aspects: {e}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                print(f"Response status: {e.response.status_code}")
                print(f"Response text: {e.response.text}")
            raise

    def cache_aspects_bulk(self, aspects_data: Dict) -> int:
        """
        Cache bulk aspect data locally.

        Args:
            aspects_data: Raw aspect data from bulk API

        Returns:
            Number of categories cached
        """
        print("💾 Caching bulk aspect data...")

        cached_count = 0
        aspects_by_category = aspects_data.get("categoryTreeNodeAspects", [])

        category_ids = []

        for cat_aspects in aspects_by_category:
            category_id = cat_aspects.get("categoryTreeNode", {}).get("categoryId")

            if not category_id:
                continue

            category_ids.append(category_id)

            # Save individual category file
            category_file = self.cache_dir / "by_category" / f"{category_id}.json"

            cache_entry = {
                "fetched_at": datetime.now().isoformat(),
                "category_id": category_id,
                "marketplace_id": self.marketplace_id,
                "data": cat_aspects
            }

            with open(category_file, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, indent=2, ensure_ascii=False)

            cached_count += 1

            # Progress indicator for large datasets
            if cached_count % 1000 == 0:
                print(f"   ... cached {cached_count} categories")

        # Save bulk file as well for reference
        bulk_file = self.cache_dir / f"aspects_bulk_{self.marketplace_id}.json"
        with open(bulk_file, 'w', encoding='utf-8') as f:
            json.dump({
                "fetched_at": datetime.now().isoformat(),
                "marketplace_id": self.marketplace_id,
                "total_categories": cached_count,
                "data": aspects_data
            }, f, indent=2, ensure_ascii=False)

        # Update metadata
        self._update_metadata(category_ids, cached_count)

        print(f"✅ Cached {cached_count} categories")
        return cached_count

    def _update_metadata(self, category_ids: List[str], cached_count: int):
        """Update cache metadata."""
        metadata_file = self.cache_dir / "aspects_metadata.json"

        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        # Update cached categories
        for cat_id in category_ids:
            metadata["cached_categories"][cat_id] = {
                "fetched_at": datetime.now().isoformat(),
                "cache_file": f"by_category/{cat_id}.json"
            }

        metadata["last_updated"] = datetime.now().isoformat()
        metadata["total_cached"] = len(metadata["cached_categories"])

        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def is_cached(self, category_id: str, max_age_days: int = 30) -> bool:
        """
        Check if category aspects are cached and fresh.

        Args:
            category_id: Category ID to check
            max_age_days: Maximum acceptable age in days

        Returns:
            True if cached and fresh
        """
        category_file = self.cache_dir / "by_category" / f"{category_id}.json"

        if not category_file.exists():
            return False

        try:
            with open(category_file, 'r') as f:
                data = json.load(f)

            fetched_at_str = data.get("fetched_at")
            if not fetched_at_str:
                return False

            fetched_at = datetime.fromisoformat(fetched_at_str)
            age = datetime.now() - fetched_at

            return age.days <= max_age_days

        except Exception:
            return False

    def get_uncached_categories(self, category_ids: List[str],
                               max_age_days: int = 30) -> List[str]:
        """
        Get list of categories that need fetching.

        Args:
            category_ids: List of category IDs to check
            max_age_days: Maximum acceptable cache age

        Returns:
            List of category IDs that need fetching
        """
        return [
            cat_id for cat_id in category_ids
            if not self.is_cached(cat_id, max_age_days)
        ]

    def fetch_and_cache_batch(self, category_ids: List[str],
                             max_age_days: int = 30) -> Dict:
        """
        Fetch and cache aspects for a batch of categories.

        Args:
            category_ids: List of category IDs
            max_age_days: Skip fetching if cached within this age

        Returns:
            Summary of fetch operation
        """
        # Filter out already cached categories
        uncached = self.get_uncached_categories(category_ids, max_age_days)

        if not uncached:
            print(f"✅ All {len(category_ids)} categories already cached")
            return {
                "total_requested": len(category_ids),
                "already_cached": len(category_ids),
                "newly_fetched": 0,
                "category_ids": category_ids
            }

        print(f"📊 {len(uncached)}/{len(category_ids)} categories need fetching")

        # Fetch aspects
        aspects_data = self.fetch_aspects_for_categories(uncached)

        # Cache the results
        cached_count = self.cache_aspects(aspects_data, uncached)

        return {
            "total_requested": len(category_ids),
            "already_cached": len(category_ids) - len(uncached),
            "newly_fetched": cached_count,
            "category_ids": uncached
        }

    def prewarm_top_categories(self, top_n: int = 100) -> Dict:
        """
        Pre-fetch aspects for the most commonly used categories.

        Args:
            top_n: Number of top categories to prewarm

        Returns:
            Summary of prewarm operation
        """
        print(f"\n🔥 Prewarming top {top_n} categories...")

        # Load flat categories to find leaf categories
        categories_file = Path("data/categories") / f"ebay_categories_{self.marketplace_id}_flat.json"

        if not categories_file.exists():
            raise FileNotFoundError(
                f"Categories file not found: {categories_file}\n"
                f"Run fetch_ebay_categories.py first."
            )

        with open(categories_file, 'r') as f:
            data = json.load(f)

        # Get leaf categories only
        leaf_categories = [
            cat for cat in data.get("categories", [])
            if cat.get("is_leaf", False)
        ]

        # Take top N by category ID (lower IDs tend to be more popular)
        # In production, you might want to use actual usage statistics
        top_categories = leaf_categories[:top_n]
        category_ids = [cat["category_id"] for cat in top_categories]

        print(f"📋 Selected {len(category_ids)} leaf categories for prewarming")

        # Process in batches
        total_fetched = 0
        total_cached = 0

        for i in range(0, len(category_ids), self.MAX_CATEGORIES_PER_REQUEST):
            batch = category_ids[i:i + self.MAX_CATEGORIES_PER_REQUEST]
            batch_num = i // self.MAX_CATEGORIES_PER_REQUEST + 1
            total_batches = (len(category_ids) + self.MAX_CATEGORIES_PER_REQUEST - 1) // self.MAX_CATEGORIES_PER_REQUEST

            print(f"\n📦 Batch {batch_num}/{total_batches} ({len(batch)} categories)")

            result = self.fetch_and_cache_batch(batch)
            total_fetched += result["newly_fetched"]
            total_cached += result["already_cached"]

        return {
            "top_n": top_n,
            "total_categories": len(category_ids),
            "newly_fetched": total_fetched,
            "already_cached": total_cached,
            "batches_processed": total_batches
        }

    def get_cache_statistics(self) -> Dict:
        """Get statistics about cached aspects."""
        metadata_file = self.cache_dir / "aspects_metadata.json"

        if not metadata_file.exists():
            return {
                "total_cached": 0,
                "cache_dir": str(self.cache_dir),
                "status": "empty"
            }

        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        cached_categories = metadata.get("cached_categories", {})

        # Count stale vs fresh
        fresh_count = 0
        stale_count = 0

        for cat_id, info in cached_categories.items():
            if self.is_cached(cat_id, max_age_days=30):
                fresh_count += 1
            else:
                stale_count += 1

        return {
            "total_cached": len(cached_categories),
            "fresh_cached": fresh_count,
            "stale_cached": stale_count,
            "cache_dir": str(self.cache_dir),
            "last_updated": metadata.get("last_updated"),
            "created_at": metadata.get("created_at"),
            "status": "active" if cached_categories else "empty"
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fetch eBay item aspects and cache locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # RECOMMENDED: Bulk fetch ALL aspects for marketplace (most efficient)
  python fetch_aspects.py --bulk-fetch

  # Fetch aspects for a single category
  python fetch_aspects.py --category-id 15708

  # Fetch aspects for multiple categories
  python fetch_aspects.py --category-ids 15708,15709,15710,11450

  # Prewarm top 100 categories
  python fetch_aspects.py --prewarm-top 100

  # Check cache statistics
  python fetch_aspects.py --stats

  # Force refresh even if cached
  python fetch_aspects.py --category-id 15708 --max-age-days 0

  # Bulk fetch for different marketplace
  python fetch_aspects.py --bulk-fetch --marketplace 3  # UK marketplace
        """
    )

    parser.add_argument(
        '--category-id',
        help='Single category ID to fetch'
    )

    parser.add_argument(
        '--category-ids',
        help='Comma-separated list of category IDs to fetch'
    )

    parser.add_argument(
        '--prewarm-top',
        type=int,
        help='Prewarm top N categories (default: 100)'
    )

    parser.add_argument(
        '--marketplace',
        default='0',
        help='eBay marketplace ID (default: 0 = US)'
    )

    parser.add_argument(
        '--sandbox',
        action='store_true',
        help='Use sandbox environment'
    )

    parser.add_argument(
        '--cache-dir',
        default='data/aspects',
        help='Cache directory (default: data/aspects)'
    )

    parser.add_argument(
        '--max-age-days',
        type=int,
        default=30,
        help='Maximum cache age in days (default: 30)'
    )

    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show cache statistics'
    )

    parser.add_argument(
        '--bulk-fetch',
        action='store_true',
        help='Fetch ALL aspects for marketplace using bulk endpoint (recommended)'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("  eBay Item Aspects Fetcher")
    print("=" * 80)
    print(f"\n📍 Marketplace: {args.marketplace}")
    print(f"🌍 Environment: {'Sandbox' if args.sandbox else 'Production'}")
    print(f"📁 Cache Dir: {args.cache_dir}")

    try:
        fetcher = EbayAspectFetcher(
            marketplace_id=args.marketplace,
            sandbox=args.sandbox,
            cache_dir=args.cache_dir
        )

        # Show stats if requested
        if args.stats:
            stats = fetcher.get_cache_statistics()
            print("\n📊 Cache Statistics:")
            print("=" * 80)
            print(f"Total Cached: {stats['total_cached']}")
            print(f"Fresh (≤30 days): {stats['fresh_cached']}")
            print(f"Stale (>30 days): {stats['stale_cached']}")
            print(f"Cache Dir: {stats['cache_dir']}")
            print(f"Last Updated: {stats.get('last_updated', 'Never')}")
            print(f"Status: {stats['status']}")
            return 0

        # Bulk fetch if requested (RECOMMENDED METHOD)
        if args.bulk_fetch:
            print("\n🚀 Starting bulk fetch of ALL item aspects...")
            print("⚠️  This will download comprehensive aspect data for all categories")
            print("    Response may be hundreds of megabytes (GZIP compressed)")

            # Fetch all aspects using bulk endpoint
            aspects_data = fetcher.fetch_all_aspects_bulk()

            # Cache the results
            cached_count = fetcher.cache_aspects_bulk(aspects_data)

            print("\n" + "=" * 80)
            print("✅ BULK FETCH COMPLETE!")
            print("=" * 80)
            print(f"\n📊 Results:")
            print(f"   Total categories cached: {cached_count:,}")
            print(f"   Cache location: {args.cache_dir}/")
            print(f"   Individual files: {args.cache_dir}/by_category/")
            print(f"   Bulk file: {args.cache_dir}/aspects_bulk_{args.marketplace}.json")

            # Show updated cache stats
            stats = fetcher.get_cache_statistics()
            print(f"\n📈 Cache now contains {stats['total_cached']:,} categories")
            print(f"   Last updated: {stats.get('last_updated', 'Unknown')}")

            return 0

        # Prewarm if requested
        if args.prewarm_top:
            result = fetcher.prewarm_top_categories(args.prewarm_top)
            print("\n" + "=" * 80)
            print("✅ PREWARM COMPLETE!")
            print("=" * 80)
            print(f"\n📊 Results:")
            print(f"   Top N requested: {result['top_n']}")
            print(f"   Total categories: {result['total_categories']}")
            print(f"   Newly fetched: {result['newly_fetched']}")
            print(f"   Already cached: {result['already_cached']}")
            print(f"   Batches processed: {result['batches_processed']}")
            return 0

        # Parse category IDs
        category_ids = []
        if args.category_id:
            category_ids = [args.category_id]
        elif args.category_ids:
            category_ids = [cid.strip() for cid in args.category_ids.split(',')]
        else:
            print("\n❌ Error: Must specify --bulk-fetch, --category-id, --category-ids, --prewarm-top, or --stats")
            print("\n💡 Tip: Use --bulk-fetch to download ALL aspects (recommended)")
            parser.print_help()
            return 1

        # Fetch and cache
        result = fetcher.fetch_and_cache_batch(category_ids, args.max_age_days)

        print("\n" + "=" * 80)
        print("✅ SUCCESS!")
        print("=" * 80)
        print(f"\n📊 Results:")
        print(f"   Total requested: {result['total_requested']}")
        print(f"   Already cached: {result['already_cached']}")
        print(f"   Newly fetched: {result['newly_fetched']}")

        if result['newly_fetched'] > 0:
            print(f"\n💾 Cache location: {args.cache_dir}/by_category/")

        # Show cache stats
        stats = fetcher.get_cache_statistics()
        print(f"\n📈 Total cached categories: {stats['total_cached']}")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
