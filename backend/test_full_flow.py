#!/usr/bin/env python3
"""
Test script for the complete Listing Agent flow.

This script tests:
1. Image upload and analysis
2. Pricing research
3. Complete end-to-end workflow

Usage:
    python test_full_flow.py <path_to_image> [platform]
"""

import sys
import json
import asyncio
import httpx
from pathlib import Path
from typing import Optional


API_BASE_URL = "http://localhost:8000"


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def print_section(text: str):
    """Print a formatted section header."""
    print("\n" + "-" * 80)
    print(f"  {text}")
    print("-" * 80)


async def test_health_check():
    """Test that the API is running."""
    print_header("Step 1: Health Check")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/health", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                print("✅ API is healthy")
                print(f"   Status: {data['status']}")
                print(f"   API Key Configured: {data['api_key_configured']}")
                return True
            else:
                print(f"❌ Health check failed with status: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            print(f"   Make sure the backend is running on {API_BASE_URL}")
            return False


async def test_image_analysis(image_path: str, platform: str = "ebay"):
    """Test image analysis endpoint."""
    print_header("Step 2: Image Analysis")

    # Check if image exists
    if not Path(image_path).exists():
        print(f"❌ Image file not found: {image_path}")
        return None

    print(f"📁 Image: {image_path}")
    print(f"🎯 Platform: {platform.upper()}")
    print("\n⏳ Analyzing image with Claude AI...")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            with open(image_path, 'rb') as f:
                files = {'file': (Path(image_path).name, f, 'image/jpeg')}
                data = {'platform': platform}

                response = await client.post(
                    f"{API_BASE_URL}/api/analyze",
                    files=files,
                    data=data
                )

            if response.status_code == 200:
                analysis = response.json()
                print("\n✅ Analysis Complete!")

                print_section("Product Information")
                print(f"   Product: {analysis['product_name']}")
                if analysis.get('brand'):
                    print(f"   Brand: {analysis['brand']}")
                if analysis.get('category'):
                    print(f"   Category: {analysis['category']}")
                print(f"   Condition: {analysis['condition']}")
                if analysis.get('color'):
                    print(f"   Color: {analysis['color']}")
                if analysis.get('model_number'):
                    print(f"   Model: {analysis['model_number']}")

                print_section("Generated Title")
                print(f"   {analysis['suggested_title']}")
                print(f"   ({len(analysis['suggested_title'])} characters)")

                print_section("Key Features")
                for i, feature in enumerate(analysis['key_features'], 1):
                    print(f"   {i}. {feature}")

                print_section("Description Preview")
                desc_lines = analysis['suggested_description'].split('\n')
                for line in desc_lines[:5]:  # First 5 lines
                    print(f"   {line}")
                if len(desc_lines) > 5:
                    print(f"   ... ({len(desc_lines) - 5} more lines)")

                return analysis
            else:
                error = response.json()
                print(f"❌ Analysis failed: {error.get('detail', 'Unknown error')}")
                return None

        except httpx.TimeoutException:
            print("❌ Request timed out. The analysis is taking too long.")
            return None
        except Exception as e:
            print(f"❌ Error during analysis: {e}")
            return None


async def test_pricing_research(analysis: dict, platform: str = "ebay"):
    """Test pricing research endpoint."""
    print_header("Step 3: Pricing Research")

    product_name = analysis['product_name']
    category = analysis.get('category')
    condition = analysis['condition']

    print(f"🔍 Researching prices for: {product_name}")
    print(f"   Category: {category or 'General'}")
    print(f"   Condition: {condition}")
    print(f"   Platform: {platform.upper()}")
    print("\n⏳ Researching market prices...")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            request_data = {
                "product_name": product_name,
                "category": category,
                "condition": condition,
                "platform": platform
            }

            response = await client.post(
                f"{API_BASE_URL}/api/research-pricing",
                json=request_data
            )

            if response.status_code == 200:
                pricing = response.json()
                print("\n✅ Pricing Research Complete!")

                stats = pricing['statistics']

                print_section("Price Statistics")
                print(f"   Min Price:        ${stats['min_price']:.2f}")
                print(f"   Max Price:        ${stats['max_price']:.2f}")
                print(f"   Average:          ${stats['average']:.2f}")
                print(f"   Median:           ${stats['median']:.2f}")
                print(f"   💰 Suggested:      ${stats['suggested_price']:.2f}")

                print_section(f"Confidence & Insights")
                confidence = pricing['confidence_score']
                confidence_emoji = "🟢" if confidence >= 80 else "🟡" if confidence >= 50 else "🔴"
                print(f"   {confidence_emoji} Confidence Score: {confidence}%")
                print(f"\n   📊 Market Insights:")
                print(f"   {pricing['market_insights']}")

                print_section("Competitor Prices")
                competitors = pricing['competitor_prices']
                if competitors:
                    for i, comp in enumerate(competitors, 1):
                        print(f"   {i}. ${comp['price']:.2f} - {comp['title']}")
                        if comp.get('date_sold'):
                            print(f"      Date: {comp['date_sold']}")
                else:
                    print("   No competitor data available")

                print_section("Timestamp")
                print(f"   Data fetched: {pricing['timestamp']}")

                return pricing
            else:
                error = response.json()
                print(f"❌ Pricing research failed: {error.get('detail', 'Unknown error')}")
                return None

        except httpx.TimeoutException:
            print("❌ Request timed out. The pricing research is taking too long.")
            return None
        except Exception as e:
            print(f"❌ Error during pricing research: {e}")
            return None


async def run_complete_test(image_path: str, platform: str = "ebay"):
    """Run the complete end-to-end test."""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "LISTING AGENT - COMPLETE FLOW TEST" + " " * 24 + "║")
    print("╚" + "═" * 78 + "╝")

    # Step 1: Health check
    healthy = await test_health_check()
    if not healthy:
        print("\n❌ Cannot proceed. Please start the backend server.")
        return

    # Step 2: Image analysis
    analysis = await test_image_analysis(image_path, platform)
    if not analysis:
        print("\n❌ Image analysis failed. Cannot proceed to pricing research.")
        return

    # Step 3: Pricing research
    pricing = await test_pricing_research(analysis, platform)
    if not pricing:
        print("\n⚠️  Pricing research failed, but analysis succeeded.")
        return

    # Summary
    print_header("🎉 Complete Test Summary")
    print("✅ Health Check: Passed")
    print("✅ Image Analysis: Passed")
    print("✅ Pricing Research: Passed")
    print("\n📦 Product: " + analysis['product_name'])
    print(f"💰 Suggested Price: ${pricing['statistics']['suggested_price']:.2f}")
    print(f"📈 Confidence: {pricing['confidence_score']}%")

    print("\n" + "=" * 80)
    print("  All tests completed successfully! ✨")
    print("=" * 80 + "\n")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python test_full_flow.py <path_to_image> [platform]")
        print("\nExample:")
        print("  python test_full_flow.py ~/Downloads/DysonVaccum.jpg ebay")
        print("\nPlatforms: ebay (default), amazon, walmart")
        sys.exit(1)

    image_path = sys.argv[1]
    platform = sys.argv[2] if len(sys.argv) > 2 else "ebay"

    # Validate platform
    if platform not in ["ebay", "amazon", "walmart"]:
        print(f"❌ Invalid platform: {platform}")
        print("   Valid platforms: ebay, amazon, walmart")
        sys.exit(1)

    # Run the test
    asyncio.run(run_complete_test(image_path, platform))


if __name__ == "__main__":
    main()
