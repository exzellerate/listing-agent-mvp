#!/usr/bin/env python3
"""
Quick test script for aspect loader functionality.
"""

from services.ebay.aspect_loader import (
    get_aspect_loader,
    get_formatted_aspects_for_category
)


def test_aspect_loader():
    """Test aspect loader basic functionality."""
    print("=" * 80)
    print("TESTING ASPECT LOADER")
    print("=" * 80)

    # Test 1: Load aspect loader
    print("\n1. Loading aspect loader...")
    loader = get_aspect_loader()
    stats = loader.get_statistics()

    print(f"✅ Loaded successfully!")
    print(f"   Total categories: {stats['total_categories']:,}")
    print(f"   Total aspects: {stats['total_aspects']:,}")
    print(f"   Categories with required aspects: {stats['categories_with_required_aspects']:,}")
    print(f"   Average aspects per category: {stats['average_aspects_per_category']:.1f}")
    print(f"   Tree version: {stats['tree_version']}")

    # Test 2: Get aspects for a specific category
    # Using category 20081 (Antiques > Decorative Arts > Ceramics & Pottery)
    print("\n2. Testing aspect lookup for category 20081...")
    aspects = get_formatted_aspects_for_category("20081")

    if aspects:
        print(f"✅ Found aspects for category {aspects['category_id']}: {aspects['category_name']}")
        print(f"   Required: {aspects['counts']['required']}")
        print(f"   Recommended: {aspects['counts']['recommended']}")
        print(f"   Optional: {aspects['counts']['optional']}")
        print(f"   Total: {aspects['counts']['total']}")

        # Show a few examples
        if aspects['aspects']['required']:
            print(f"\n   Sample required aspects:")
            for aspect in aspects['aspects']['required'][:3]:
                print(f"     - {aspect['name']} ({aspect['input_type']})")

        if aspects['aspects']['recommended']:
            print(f"\n   Sample recommended aspects:")
            for aspect in aspects['aspects']['recommended'][:3]:
                print(f"     - {aspect['name']} ({aspect['input_type']})")
    else:
        print("❌ No aspects found for category 20081")

    # Test 3: Test invalid category
    print("\n3. Testing invalid category...")
    invalid_aspects = get_formatted_aspects_for_category("999999999")
    if invalid_aspects is None:
        print("✅ Correctly returned None for invalid category")
    else:
        print("❌ Should have returned None for invalid category")

    # Test 4: Test another category with different characteristics
    # Category 11450 (Clothing, Shoes & Accessories > Women > Shoes)
    print("\n4. Testing category 11450 (Women's Shoes)...")
    shoes_aspects = get_formatted_aspects_for_category("11450")

    if shoes_aspects:
        print(f"✅ Found aspects for {shoes_aspects['category_name']}")
        print(f"   Required: {shoes_aspects['counts']['required']}")
        print(f"   Total: {shoes_aspects['counts']['total']}")
    else:
        print("❌ No aspects found for category 11450")

    print("\n" + "=" * 80)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    test_aspect_loader()
