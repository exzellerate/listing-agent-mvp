#!/usr/bin/env python3
"""
Quick test for category matching with tumbler/bottle keywords using eBay Taxonomy API.
"""

from services.ebay.taxonomy import EbayTaxonomyService
from services.ebay.category_recommender import CategoryRecommender
from services.ebay.oauth import EbayOAuthService
from database import get_db


def extract_category_keywords(product_analysis: dict) -> list[str]:
    """
    Extract category search keywords from product analysis.
    (Copied from main.py for testing)
    """
    keywords = []

    # 1. Product name (most important - split into words)
    if product_analysis.get('product_name'):
        words = product_analysis['product_name'].split()
        # Filter out short words and take first 5 significant ones
        keywords.extend([w for w in words if len(w) > 2][:5])

    # 2. Brand (high signal for category matching)
    if product_analysis.get('brand'):
        keywords.append(product_analysis['brand'])

    # 3. Category (helps narrow down)
    if product_analysis.get('category'):
        keywords.append(product_analysis['category'])

    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = [
        k for k in keywords
        if not (k.lower() in seen or seen.add(k.lower()))
    ]

    return unique_keywords[:5]  # Return max 5 keywords


def test_tumbler_matching():
    """Test category matching for tumbler/bottle products using eBay Taxonomy API."""
    print("=" * 80)
    print("TESTING CATEGORY MATCHING - TUMBLER/BOTTLE (eBay Taxonomy API)")
    print("=" * 80)

    # Test product analysis (simulating Claude's output)
    product_analysis = {
        'product_name': 'Insulated Tumbler Owala Tumbler Stainless Steel Water Bottle Travel Tumbler',
        'brand': 'Owala',
        'category': 'Water Bottles'
    }

    # Extract keywords
    print("\n1. Extracting category keywords from product analysis:")
    print(f"   Product Name: {product_analysis['product_name']}")
    print(f"   Brand: {product_analysis['brand']}")
    print(f"   Category: {product_analysis['category']}")

    keywords = extract_category_keywords(product_analysis)
    print(f"\n   ✅ Extracted keywords: {keywords}")

    # Initialize eBay services
    print("\n2. Initializing eBay Taxonomy API services...")
    try:
        # Get database session
        db = next(get_db())

        # Get OAuth service and application token
        oauth_service = EbayOAuthService(db)
        app_token = oauth_service.get_application_token()
        print(f"   ✅ Got application token")

        # Initialize taxonomy service
        taxonomy_service = EbayTaxonomyService(app_token)
        recommender = CategoryRecommender(taxonomy_service)
        print(f"   ✅ Initialized CategoryRecommender")

    except Exception as e:
        print(f"   ❌ Error initializing services: {e}")
        return

    # Get category recommendations
    print("\n3. Getting category recommendations from eBay Taxonomy API...")
    try:
        category_matches = recommender.recommend_categories(
            product_name=product_analysis.get('product_name', ''),
            brand=product_analysis.get('brand'),
            category_keywords=keywords,
            product_category=product_analysis.get('category')
        )

        if category_matches and len(category_matches) > 0:
            print(f"\n   ✅ Found {len(category_matches)} category matches:\n")
            for i, match in enumerate(category_matches, 1):
                print(f"   {i}. {match.get('category_name')}")
                print(f"      Path: {match.get('path', 'N/A')}")
                print(f"      ID: {match.get('category_id')}")
                print(f"      Leaf: {match.get('is_leaf', 'N/A')}")
                if match.get('matched_keywords'):
                    print(f"      Matched Keywords: {', '.join(match['matched_keywords'])}")
                print()
        else:
            print("\n   ❌ No category matches found")

    except Exception as e:
        print(f"\n   ❌ Error getting category recommendations: {e}")
        import traceback
        traceback.print_exc()

    # Test with simpler keywords
    print("\n4. Testing with simpler keywords ('water bottle' + 'tumbler')...")
    try:
        simple_keywords = ['water', 'bottle', 'tumbler', 'Owala']

        simple_matches = recommender.recommend_categories(
            product_name='water bottle tumbler',
            brand='Owala',
            category_keywords=simple_keywords,
            product_category='Drinkware'
        )

        if simple_matches:
            print(f"\n   ✅ Found {len(simple_matches)} matches:")
            for i, match in enumerate(simple_matches[:3], 1):  # Show top 3
                print(f"   {i}. {match.get('category_name')} (ID: {match.get('category_id')})")
        else:
            print("\n   ❌ No matches found")

    except Exception as e:
        print(f"\n   ❌ Error: {e}")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_tumbler_matching()
