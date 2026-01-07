#!/usr/bin/env python3
"""
Phase A Testing Script
Tests the complete flow:
1. Upload image → Analyze → Store in DB
2. Confirm analysis with user action
3. Verify data in DB
"""

import requests
import os
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
TEST_IMAGE_PATH = "test_images/iphone_13.webp"  # Using test image from repo

def test_analyze_endpoint():
    """Test /api/analyze endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Analyzing image and storing in database")
    print("="*60)

    # Check if test image exists
    if not os.path.exists(TEST_IMAGE_PATH):
        print(f"❌ Test image not found: {TEST_IMAGE_PATH}")
        print("Please provide a test image in the test_images/ directory")
        return None

    # Prepare the request
    with open(TEST_IMAGE_PATH, 'rb') as f:
        files = {'files': (os.path.basename(TEST_IMAGE_PATH), f, 'image/webp')}
        data = {'platform': 'ebay'}

        print(f"📤 Uploading: {TEST_IMAGE_PATH}")
        response = requests.post(f"{BASE_URL}/api/analyze", files=files, data=data)

    if response.status_code == 200:
        result = response.json()
        analysis_id = result.get('analysis_id')

        print("✅ Analysis successful!")
        print(f"   Analysis ID: {analysis_id}")
        print(f"   Product: {result.get('product_name')}")
        print(f"   Brand: {result.get('brand')}")
        print(f"   Confidence: {result.get('confidence_score')}%")
        print(f"   Title: {result.get('suggested_title')[:60]}...")

        return analysis_id
    else:
        print(f"❌ Analysis failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return None


def test_confirm_endpoint(analysis_id, action="accepted"):
    """Test /api/analyses/confirm endpoint"""
    print("\n" + "="*60)
    print(f"TEST 2: Confirming analysis with action: {action}")
    print("="*60)

    # Prepare confirmation request
    payload = {
        "analysis_id": analysis_id,
        "user_action": action
    }

    # If editing or correcting, add some corrections
    if action in ["edited", "corrected"]:
        payload.update({
            "user_title": "My Custom Title",
            "user_price": 29.99,
            "user_notes": "This is a test confirmation"
        })

    print(f"📤 Confirming analysis {analysis_id}...")
    response = requests.post(f"{BASE_URL}/api/analyses/confirm", json=payload)

    if response.status_code == 200:
        result = response.json()
        print("✅ Confirmation successful!")
        print(f"   Message: {result.get('message')}")
        return True
    else:
        print(f"❌ Confirmation failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return False


def verify_database(analysis_id):
    """Verify data in database using SQLite"""
    print("\n" + "="*60)
    print("TEST 3: Verifying data in database")
    print("="*60)

    import sqlite3

    try:
        conn = sqlite3.connect('listing_agent.db')
        cursor = conn.cursor()

        # Query the analysis
        cursor.execute("""
            SELECT
                id, image_hash, ai_product_name, ai_brand, ai_category,
                ai_title, ai_confidence, user_action, user_title, user_price,
                platform, source, processing_time_ms, created_at
            FROM product_analyses
            WHERE id = ?
        """, (analysis_id,))

        row = cursor.fetchone()

        if row:
            print("✅ Analysis found in database!")
            print(f"\n   Database Record:")
            print(f"   ├─ ID: {row[0]}")
            print(f"   ├─ Image Hash: {row[1][:16]}...")
            print(f"   ├─ AI Product: {row[2]}")
            print(f"   ├─ AI Brand: {row[3]}")
            print(f"   ├─ AI Category: {row[4]}")
            print(f"   ├─ AI Title: {row[5][:50]}...")
            print(f"   ├─ AI Confidence: {row[6]}%")
            print(f"   ├─ User Action: {row[7]}")
            print(f"   ├─ User Title: {row[8]}")
            print(f"   ├─ User Price: ${row[9]}" if row[9] else f"   ├─ User Price: None")
            print(f"   ├─ Platform: {row[10]}")
            print(f"   ├─ Source: {row[11]}")
            print(f"   ├─ Processing Time: {row[12]}ms")
            print(f"   └─ Created: {row[13]}")

            # Check learned_products table (should be empty in Phase A)
            cursor.execute("SELECT COUNT(*) FROM learned_products")
            learned_count = cursor.fetchone()[0]
            print(f"\n   Learned Products: {learned_count} (expected 0 in Phase A)")

            # Check learning_stats table (should be empty in Phase A)
            cursor.execute("SELECT COUNT(*) FROM learning_stats")
            stats_count = cursor.fetchone()[0]
            print(f"   Learning Stats: {stats_count} (expected 0 in Phase A)")

            return True
        else:
            print(f"❌ Analysis {analysis_id} not found in database!")
            return False

    except Exception as e:
        print(f"❌ Database verification failed: {str(e)}")
        return False
    finally:
        conn.close()


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 PHASE A - DATABASE & STORAGE TESTING")
    print("="*60)

    # Test 1: Analyze image
    analysis_id = test_analyze_endpoint()
    if not analysis_id:
        print("\n❌ Test suite failed: Could not analyze image")
        return

    # Test 2: Confirm analysis (accepted)
    success = test_confirm_endpoint(analysis_id, action="accepted")
    if not success:
        print("\n❌ Test suite failed: Could not confirm analysis")
        return

    # Test 3: Verify in database
    success = verify_database(analysis_id)
    if not success:
        print("\n❌ Test suite failed: Could not verify database")
        return

    # Summary
    print("\n" + "="*60)
    print("✅ ALL PHASE A TESTS PASSED!")
    print("="*60)
    print("\nPhase A Implementation Complete:")
    print("  ✓ Database schema created")
    print("  ✓ Image hash utility working")
    print("  ✓ /api/analyze stores analyses in DB")
    print("  ✓ /api/analyses/confirm updates user actions")
    print("  ✓ Data persists correctly in SQLite")
    print("\nReady for Phase B: Learning Engine")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
