#!/usr/bin/env python3
"""
Category Matching Example

Demonstrates how to use the eBay category matcher with real product data.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.ebay.category_matcher import EbayCategoryMatcher


def print_header(text: str):
    """Print formatted header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def print_matches(matches, title):
    """Print category matches in a formatted way."""
    print(f"\n{title}:")
    print("-" * 80)

    if not matches:
        print("  No matches found")
        return

    for i, match in enumerate(matches, 1):
        leaf_indicator = "🍃 LEAF" if match.is_leaf else "📁 PARENT"
        print(f"\n  {i}. {leaf_indicator} [{match.category_id}] {match.category_name}")
        print(f"     Path: {match.path}")
        print(f"     Score: {match.score:.1f}%  |  Level: {match.level}")


def example_1_simple_keywords():
    """Example 1: Find categories using simple keywords."""
    print_header("Example 1: Simple Keyword Matching")

    matcher = EbayCategoryMatcher()

    # Example products from test data
    products = [
        {"name": "Dyson Ball Multi Floor Vacuum", "brand": "Dyson"},
        {"name": "Nike A'ja Wilson Basketball Shoes", "brand": "Nike"},
        {"name": "Apple AirPods Pro", "brand": "Apple"},
        {"name": "Instant Pot Duo Pressure Cooker", "brand": "Instant Pot"},
        {"name": "LEGO Star Wars Millennium Falcon", "brand": "LEGO"},
    ]

    for product in products:
        print(f"\n🔍 Searching for: {product['name']}")
        print(f"   Brand: {product['brand']}")

        matches = matcher.find_by_keywords(
            product_name=product["name"],
            brand=product["brand"],
            top_n=3,
            min_score=60.0
        )

        if matches:
            print(f"\n   ✅ Found {len(matches)} categories:")
            for i, match in enumerate(matches, 1):
                leaf = "🍃" if match.is_leaf else "📁"
                print(f"   {i}. {leaf} {match.category_name} (Score: {match.score:.1f}%)")
                print(f"      → {match.path}")
        else:
            print("   ❌ No suitable categories found")


def example_2_product_info():
    """Example 2: Match using complete product information."""
    print_header("Example 2: Matching with Complete Product Info")

    matcher = EbayCategoryMatcher()

    # Complete product information (as would come from Claude analysis)
    product_info = {
        "product_name": "Dyson Ball Multi Floor Vacuum Cleaner",
        "brand": "Dyson",
        "title": "Dyson Ball Multi Floor Vacuum Cleaner DC25 Upright",
        "description": "Powerful upright vacuum cleaner with cyclone technology, "
                      "HEPA filtration, and bagless design for multi-floor cleaning",
        "condition": "Used - Good"
    }

    print("Product Information:")
    for key, value in product_info.items():
        print(f"  {key}: {value}")

    matches = matcher.find_by_product_info(product_info, top_n=5)
    print_matches(matches, "Top 5 Category Matches")


def example_3_validation():
    """Example 3: Validate category selections."""
    print_header("Example 3: Category Validation")

    matcher = EbayCategoryMatcher()

    # Test category IDs (these would be real IDs from eBay)
    test_categories = [
        "20614",  # Example: Vacuum cleaners
        "15709",  # Example: Men's Athletic Shoes
        "11450"   # Example: Headphones
    ]

    for category_id in test_categories:
        is_valid, message = matcher.validate_category(category_id)

        if is_valid:
            cat = matcher.get_category_by_id(category_id)
            print(f"✅ Category {category_id}: VALID")
            if cat:
                print(f"   Name: {cat['category_name']}")
                print(f"   Path: {cat['path']}")
        else:
            print(f"❌ Category {category_id}: INVALID")
            print(f"   Reason: {message}")


def example_4_similar_categories():
    """Example 4: Find similar categories."""
    print_header("Example 4: Finding Similar Categories")

    matcher = EbayCategoryMatcher()

    # Start with a specific category
    reference_category_id = "15709"  # Example: Athletic Shoes

    cat = matcher.get_category_by_id(reference_category_id)
    if cat:
        print(f"Reference Category:")
        print(f"  ID: {reference_category_id}")
        print(f"  Name: {cat['category_name']}")
        print(f"  Path: {cat['path']}")

        similar = matcher.suggest_similar_categories(reference_category_id, top_n=5)
        print_matches(similar, "Similar Categories")
    else:
        print(f"❌ Category {reference_category_id} not found")


def example_5_statistics():
    """Example 5: Get category statistics."""
    print_header("Example 5: Category Statistics")

    matcher = EbayCategoryMatcher()
    stats = matcher.get_statistics()

    print("eBay Category Data:")
    print(f"  Total Categories: {stats['total_categories']:,}")
    print(f"  Leaf Categories: {stats['leaf_categories']:,}")
    print(f"  Parent Categories: {stats['parent_categories']:,}")
    print(f"  Maximum Depth: {stats['max_depth']}")
    print(f"  Data File: {stats['data_file']}")


def demo_integration():
    """Demonstrate how this integrates with the main listing flow."""
    print_header("Integration Demo: Complete Listing Flow")

    matcher = EbayCategoryMatcher()

    # Simulated product analysis result from Claude
    analysis_result = {
        "product_name": "Nike A'ja Wilson Basketball Shoes",
        "brand": "Nike",
        "title": "Nike A'ja Wilson Basketball Shoes Size 10",
        "description": "Women's basketball shoes featuring A'ja Wilson signature design. "
                      "High-performance athletic footwear for basketball.",
        "condition": "Used - Good",
        "price_estimate": {
            "min": 80.00,
            "max": 120.00
        }
    }

    print("Step 1: Product Analysis Complete")
    print(f"  Product: {analysis_result['product_name']}")
    print(f"  Brand: {analysis_result['brand']}")

    print("\nStep 2: Finding Best eBay Category...")
    matches = matcher.find_by_product_info(analysis_result, top_n=3)

    if matches:
        best_match = matches[0]
        print(f"\n  ✅ Best Match Found:")
        print(f"     Category: {best_match.category_name}")
        print(f"     Category ID: {best_match.category_id}")
        print(f"     Full Path: {best_match.path}")
        print(f"     Confidence: {best_match.score:.1f}%")

        # Validate the category
        is_valid, message = matcher.validate_category(best_match.category_id)
        if is_valid:
            print(f"\n  ✅ Category Validation: PASSED")
        else:
            print(f"\n  ⚠️  Category Validation: {message}")
            print(f"      Suggesting alternatives...")
            alternatives = matcher.suggest_similar_categories(best_match.category_id, top_n=3)
            for alt in alternatives:
                if alt.is_leaf:
                    print(f"      → {alt.category_name} (ID: {alt.category_id})")

        print("\nStep 3: Ready for eBay Listing Creation")
        print(f"  Title: {analysis_result['title']}")
        print(f"  Category ID: {best_match.category_id}")
        print(f"  Condition: {analysis_result['condition']}")
        print(f"  Starting Price: ${analysis_result['price_estimate']['min']:.2f}")
    else:
        print("  ❌ No suitable categories found")
        print("  → Manual category selection required")


def main():
    """Run all examples."""
    print_header("eBay Category Matching Examples")
    print("These examples demonstrate how to use the category matcher")
    print("to find the best eBay categories for your products.\n")

    print("NOTE: These examples require category data to be downloaded first.")
    print("Run: python services/ebay/fetch_ebay_categories.py --marketplace EBAY_US")

    try:
        # Run examples
        example_5_statistics()
        example_1_simple_keywords()
        example_2_product_info()
        example_3_validation()
        example_4_similar_categories()
        demo_integration()

        print_header("Examples Complete!")
        print("The category matcher is ready to integrate with your listing agent.\n")

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 To fix this:")
        print("   1. Make sure your eBay API credentials are in .env")
        print("   2. Run: python services/ebay/fetch_ebay_categories.py --marketplace EBAY_US")
        print("   3. Then run this example script again\n")
        return 1

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
