#!/usr/bin/env python3
"""
Test script to verify enhanced logging is working.
Uploads a test image and checks if new logging fields appear.
"""
import requests
import json
import time
from pathlib import Path

# Test image
TEST_IMAGE = Path("/Users/tuhin/listing-agent-mvp/backend/test_images/airpods_pro.webp")

print("🧪 Testing enhanced logging...")
print(f"📸 Using test image: {TEST_IMAGE.name}")

# Prepare the request
url = "http://localhost:8000/api/analyze"
files = {
    'images': (TEST_IMAGE.name, open(TEST_IMAGE, 'rb'), 'image/webp')
}
data = {
    'platform': 'ebay'
}

print("\n📤 Sending analysis request...")
start_time = time.time()

try:
    response = requests.post(url, files=files, data=data, timeout=180)
    elapsed = time.time() - start_time

    print(f"⏱️  Response time: {elapsed:.2f}s")
    print(f"📊 Status code: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Analysis successful!")
        print(f"   Product: {result.get('results', [{}])[0].get('product_name', 'Unknown')}")
        print(f"   Request ID: {result.get('request_id', 'N/A')}")

        # Now check the logs
        print("\n🔍 Checking logs for new fields...")
        log_file = Path("/Users/tuhin/listing-agent-mvp/backend/logs/analysis_results.jsonl")

        # Read the last log entry
        with open(log_file, 'r') as f:
            lines = f.readlines()
            if lines:
                last_entry = json.loads(lines[-1])
                print(f"\n📋 Latest log entry:")
                print(f"   Request ID: {last_entry.get('request_id', 'N/A')}")
                print(f"   Has raw_response: {'raw_response' in last_entry}")
                print(f"   Has extraction_strategy: {'extraction_strategy' in last_entry}")

                if 'raw_response' in last_entry:
                    print(f"   ✅ raw_response length: {last_entry.get('raw_response_length', 0)} chars")
                    print(f"   ✅ extraction_strategy: {last_entry.get('extraction_strategy', 'N/A')}")
                    print("\n🎉 Enhanced logging is WORKING!")
                else:
                    print("\n⚠️  New fields NOT found in latest log entry")
                    print("   This might be an old log. Try refreshing the performance dashboard.")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   Response: {response.text[:200]}")

except Exception as e:
    print(f"❌ Request failed: {e}")

print("\n✅ Test complete!")
