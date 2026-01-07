#!/usr/bin/env python3
"""
eBay Category Freshness Checker

Checks if the local eBay category data is up-to-date and provides warnings
if it needs to be refreshed.

Usage:
    python check_category_freshness.py
    python check_category_freshness.py --max-age-days 30
    python check_category_freshness.py --auto-refresh
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Tuple, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class CategoryFreshnessChecker:
    """Checks freshness of local eBay category data."""

    def __init__(self, categories_file: str = "data/categories/ebay_categories_0_flat.json"):
        """Initialize with path to category file."""
        self.categories_file = Path(categories_file)

    def check_freshness(self, max_age_days: int = 30) -> Tuple[bool, dict]:
        """
        Check if category data is fresh.

        Args:
            max_age_days: Maximum acceptable age in days

        Returns:
            Tuple of (is_fresh: bool, info: dict)
        """
        if not self.categories_file.exists():
            return False, {
                "status": "missing",
                "message": "Category data file not found",
                "age_days": None,
                "fetched_at": None,
                "action": "Run fetch_ebay_categories.py to download category data"
            }

        try:
            with open(self.categories_file, 'r') as f:
                data = json.load(f)

            fetched_at_str = data.get("fetched_at")
            if not fetched_at_str:
                return False, {
                    "status": "invalid",
                    "message": "Category file missing fetch timestamp",
                    "age_days": None,
                    "fetched_at": None,
                    "action": "Re-run fetch_ebay_categories.py"
                }

            # Parse timestamp
            fetched_at = datetime.fromisoformat(fetched_at_str)
            age = datetime.now() - fetched_at
            age_days = age.days

            total_categories = data.get("total_categories", 0)
            marketplace_id = data.get("marketplace_id", "unknown")

            is_fresh = age_days <= max_age_days

            info = {
                "status": "fresh" if is_fresh else "stale",
                "message": f"Category data is {age_days} days old" +
                          (f" (max: {max_age_days} days)" if not is_fresh else ""),
                "age_days": age_days,
                "fetched_at": fetched_at_str,
                "total_categories": total_categories,
                "marketplace_id": marketplace_id,
                "max_age_days": max_age_days,
                "action": "Run fetch_ebay_categories.py to refresh" if not is_fresh else None
            }

            return is_fresh, info

        except json.JSONDecodeError:
            return False, {
                "status": "corrupted",
                "message": "Category file is corrupted (invalid JSON)",
                "age_days": None,
                "fetched_at": None,
                "action": "Delete file and run fetch_ebay_categories.py"
            }
        except Exception as e:
            return False, {
                "status": "error",
                "message": f"Error checking freshness: {e}",
                "age_days": None,
                "fetched_at": None,
                "action": "Check file permissions and format"
            }

    def get_next_refresh_date(self, max_age_days: int = 30) -> Optional[datetime]:
        """
        Get the date when categories should be refreshed next.

        Args:
            max_age_days: Maximum acceptable age in days

        Returns:
            Datetime when refresh is needed, or None if file doesn't exist
        """
        if not self.categories_file.exists():
            return None

        try:
            with open(self.categories_file, 'r') as f:
                data = json.load(f)

            fetched_at_str = data.get("fetched_at")
            if not fetched_at_str:
                return None

            fetched_at = datetime.fromisoformat(fetched_at_str)
            next_refresh = fetched_at + timedelta(days=max_age_days)

            return next_refresh

        except Exception:
            return None


def print_status(info: dict):
    """Print formatted status information."""
    status = info["status"]

    # Status emoji
    status_emoji = {
        "fresh": "✅",
        "stale": "⚠️",
        "missing": "❌",
        "invalid": "❌",
        "corrupted": "❌",
        "error": "❌"
    }
    emoji = status_emoji.get(status, "ℹ️")

    print(f"\n{emoji} Category Data Status: {status.upper()}")
    print("=" * 60)

    # Basic info
    print(f"Message: {info['message']}")

    if info.get("fetched_at"):
        print(f"Last Updated: {info['fetched_at']}")
        print(f"Age: {info['age_days']} days")
        print(f"Max Age: {info.get('max_age_days', 'N/A')} days")

    if info.get("total_categories"):
        print(f"Total Categories: {info['total_categories']:,}")

    if info.get("marketplace_id"):
        print(f"Marketplace: {info['marketplace_id']}")

    # Action required
    if info.get("action"):
        print(f"\n⚡ Action Required:")
        print(f"   {info['action']}")

    print("=" * 60 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check freshness of eBay category data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check with default settings (30 days max age)
  python check_category_freshness.py

  # Check with custom max age
  python check_category_freshness.py --max-age-days 60

  # Get next refresh date
  python check_category_freshness.py --show-next-refresh

  # Auto-refresh if stale
  python check_category_freshness.py --auto-refresh
        """
    )

    parser.add_argument(
        '--max-age-days',
        type=int,
        default=30,
        help='Maximum acceptable age in days (default: 30)'
    )

    parser.add_argument(
        '--show-next-refresh',
        action='store_true',
        help='Show when next refresh is needed'
    )

    parser.add_argument(
        '--auto-refresh',
        action='store_true',
        help='Automatically refresh if stale'
    )

    parser.add_argument(
        '--categories-file',
        default='data/categories/ebay_categories_0_flat.json',
        help='Path to categories file (default: data/categories/ebay_categories_0_flat.json)'
    )

    args = parser.parse_args()

    # Create checker
    checker = CategoryFreshnessChecker(args.categories_file)

    # Show next refresh date if requested
    if args.show_next_refresh:
        next_refresh = checker.get_next_refresh_date(args.max_age_days)
        if next_refresh:
            days_until = (next_refresh - datetime.now()).days
            print(f"\n📅 Next refresh recommended: {next_refresh.strftime('%Y-%m-%d')}")
            print(f"   ({days_until} days from now)\n")
        else:
            print("\n⚠️  Cannot determine next refresh date (file missing or invalid)\n")
        return 0

    # Check freshness
    is_fresh, info = checker.check_freshness(args.max_age_days)

    # Print status
    print_status(info)

    # Auto-refresh if stale
    if args.auto_refresh and not is_fresh:
        print("🔄 Auto-refresh is enabled. Starting category refresh...\n")

        try:
            import subprocess
            result = subprocess.run(
                ["python", "services/ebay/fetch_ebay_categories.py", "--marketplace", "0"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                print("✅ Category data refreshed successfully!")
                # Re-check freshness
                is_fresh, info = checker.check_freshness(args.max_age_days)
                print_status(info)
                return 0
            else:
                print(f"❌ Refresh failed with code {result.returncode}")
                print(f"Error: {result.stderr}")
                return 1

        except subprocess.TimeoutExpired:
            print("❌ Refresh timed out after 5 minutes")
            return 1
        except Exception as e:
            print(f"❌ Error during auto-refresh: {e}")
            return 1

    # Exit with appropriate code
    return 0 if is_fresh else 1


if __name__ == "__main__":
    sys.exit(main())
