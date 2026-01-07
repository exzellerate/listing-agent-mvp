#!/usr/bin/env python3
"""
eBay Category Taxonomy Fetcher

Fetches the complete eBay category tree using the eBay Taxonomy API
and stores it locally for fast category matching.

Usage:
    python fetch_ebay_categories.py --marketplace EBAY_US
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()


class EbayCategoryFetcher:
    """Fetches and stores eBay category taxonomy."""

    # eBay API endpoints
    SANDBOX_BASE = "https://api.sandbox.ebay.com"
    PRODUCTION_BASE = "https://api.ebay.com"

    # OAuth endpoint
    OAUTH_BASE = "https://api.ebay.com/identity/v1/oauth2/token"
    OAUTH_SANDBOX_BASE = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"

    def __init__(self, sandbox: bool = False):
        """Initialize fetcher with credentials."""
        self.sandbox = sandbox
        self.base_url = self.SANDBOX_BASE if sandbox else self.PRODUCTION_BASE
        self.oauth_url = self.OAUTH_SANDBOX_BASE if sandbox else self.OAUTH_BASE

        # Get credentials from environment
        # Note: APP_ID = CLIENT_ID and CERT_ID = CLIENT_SECRET
        self.app_id = os.getenv("EBAY_APP_ID") or os.getenv("EBAY_CLIENT_ID")
        self.cert_id = os.getenv("EBAY_CERT_ID") or os.getenv("EBAY_CLIENT_SECRET")

        if not self.app_id or not self.cert_id:
            raise ValueError("EBAY_APP_ID (or EBAY_CLIENT_ID) and EBAY_CERT_ID (or EBAY_CLIENT_SECRET) must be set in .env file")

        self.access_token = None

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
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            raise

    def fetch_category_tree(self, marketplace_id: str = "EBAY_US") -> Dict:
        """
        Fetch the complete category tree for a marketplace.

        Args:
            marketplace_id: eBay marketplace ID (e.g., EBAY_US, EBAY_GB)

        Returns:
            Complete category tree as dictionary
        """
        if not self.access_token:
            self.get_oauth_token()

        print(f"\n📥 Fetching category tree for {marketplace_id}...")

        url = f"{self.base_url}/commerce/taxonomy/v1/category_tree/{marketplace_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Get metadata
            category_tree_id = data.get("categoryTreeId")
            category_tree_version = data.get("categoryTreeVersion")

            print(f"✅ Category tree fetched successfully")
            print(f"   Tree ID: {category_tree_id}")
            print(f"   Version: {category_tree_version}")

            return data

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to fetch category tree: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            raise

    def fetch_category_subtree(self, category_id: str, marketplace_id: str = "EBAY_US") -> Dict:
        """
        Fetch a specific category subtree.

        Args:
            category_id: Root category ID for the subtree
            marketplace_id: eBay marketplace ID

        Returns:
            Category subtree as dictionary
        """
        if not self.access_token:
            self.get_oauth_token()

        print(f"📥 Fetching category subtree for category {category_id}...")

        url = f"{self.base_url}/commerce/taxonomy/v1/category_tree/{marketplace_id}/get_category_subtree"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        params = {
            "category_id": category_id
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            print(f"✅ Subtree fetched for category {category_id}")

            return data

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to fetch category subtree: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            raise

    def save_category_tree(self, tree_data: Dict, output_dir: str = "data/categories") -> str:
        """
        Save category tree to JSON file.

        Args:
            tree_data: Category tree data
            output_dir: Directory to save the file

        Returns:
            Path to saved file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        marketplace_id = tree_data.get("categoryTreeId", "EBAY_US")
        version = tree_data.get("categoryTreeVersion", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = f"ebay_categories_{marketplace_id}_{version}_{timestamp}.json"
        filepath = output_path / filename

        # Add metadata
        output_data = {
            "fetched_at": datetime.now().isoformat(),
            "marketplace_id": marketplace_id,
            "version": version,
            "data": tree_data
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Category tree saved to: {filepath}")

        # Also save as "latest" for easy access
        latest_filepath = output_path / f"ebay_categories_{marketplace_id}_latest.json"
        with open(latest_filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"💾 Also saved as: {latest_filepath}")

        return str(filepath)

    def flatten_category_tree(self, tree_data: Dict) -> List[Dict]:
        """
        Flatten the hierarchical category tree into a flat list for easier searching.

        Args:
            tree_data: Category tree data

        Returns:
            Flat list of categories with full paths
        """
        print("\n🔄 Flattening category tree...")

        flat_categories = []

        def traverse(category: Dict, path: List[str] = None):
            """Recursively traverse and flatten the tree."""
            if path is None:
                path = []

            category_id = category.get("category", {}).get("categoryId")
            category_name = category.get("category", {}).get("categoryName")

            if category_id and category_name:
                current_path = path + [category_name]

                flat_categories.append({
                    "category_id": category_id,
                    "category_name": category_name,
                    "path": " > ".join(current_path),
                    "level": len(current_path),
                    "parent_path": " > ".join(path) if path else None,
                    "is_leaf": "childCategoryTreeNodes" not in category or not category["childCategoryTreeNodes"]
                })

                # Process children
                children = category.get("childCategoryTreeNodes", [])
                for child in children:
                    traverse(child, current_path)

        # Start traversal from root node
        root_node = tree_data.get("rootCategoryNode", {})
        if root_node:
            traverse(root_node)

        print(f"✅ Flattened {len(flat_categories)} categories")

        return flat_categories

    def save_flat_categories(self, flat_categories: List[Dict], marketplace_id: str, output_dir: str = "data/categories") -> str:
        """Save flattened categories for fast lookup."""
        output_path = Path(output_dir)
        filepath = output_path / f"ebay_categories_{marketplace_id}_flat.json"

        output_data = {
            "fetched_at": datetime.now().isoformat(),
            "marketplace_id": marketplace_id,
            "total_categories": len(flat_categories),
            "categories": flat_categories
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"💾 Flat categories saved to: {filepath}")

        return str(filepath)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fetch eBay category taxonomy and store locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch US marketplace categories (production)
  python fetch_ebay_categories.py --marketplace EBAY_US

  # Fetch UK marketplace categories
  python fetch_ebay_categories.py --marketplace EBAY_GB

  # Use sandbox environment
  python fetch_ebay_categories.py --marketplace EBAY_US --sandbox

  # Fetch specific category subtree
  python fetch_ebay_categories.py --marketplace EBAY_US --category-id 11450
        """
    )

    parser.add_argument(
        '--marketplace',
        default='EBAY_US',
        help='eBay marketplace ID (default: EBAY_US)'
    )

    parser.add_argument(
        '--sandbox',
        action='store_true',
        help='Use sandbox environment'
    )

    parser.add_argument(
        '--category-id',
        help='Fetch specific category subtree'
    )

    parser.add_argument(
        '--output-dir',
        default='data/categories',
        help='Output directory for category files (default: data/categories)'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("  eBay Category Taxonomy Fetcher")
    print("=" * 80)
    print(f"\n📍 Marketplace: {args.marketplace}")
    print(f"🌍 Environment: {'Sandbox' if args.sandbox else 'Production'}")
    print(f"📁 Output Dir: {args.output_dir}")

    try:
        fetcher = EbayCategoryFetcher(sandbox=args.sandbox)

        if args.category_id:
            # Fetch specific subtree
            tree_data = fetcher.fetch_category_subtree(args.category_id, args.marketplace)
        else:
            # Fetch full tree
            tree_data = fetcher.fetch_category_tree(args.marketplace)

        # Save full tree
        filepath = fetcher.save_category_tree(tree_data, args.output_dir)

        # Flatten and save
        flat_categories = fetcher.flatten_category_tree(tree_data)
        flat_filepath = fetcher.save_flat_categories(flat_categories, args.marketplace, args.output_dir)

        print("\n" + "=" * 80)
        print("✅ SUCCESS!")
        print("=" * 80)
        print(f"\n📊 Total categories: {len(flat_categories)}")
        print(f"📄 Full tree: {filepath}")
        print(f"📄 Flat list: {flat_filepath}")

        # Show some sample categories
        if flat_categories:
            print("\n📋 Sample categories:")
            for cat in flat_categories[:10]:
                print(f"   [{cat['category_id']}] {cat['path']}")
            if len(flat_categories) > 10:
                print(f"   ... and {len(flat_categories) - 10} more")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.sandbox:
            print("\n💡 Tip: Make sure your eBay Developer credentials are configured in .env")
            print("   EBAY_APP_ID and EBAY_CERT_ID must be set")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
