#!/usr/bin/env python3
"""Extract JSON from the raw Claude response in the latest log entry."""
import json
import re

# Read the latest log entry
with open('/Users/tuhin/listing-agent-mvp/backend/logs/analysis_results.jsonl', 'r') as f:
    lines = f.readlines()
    latest = json.loads(lines[-1])

raw_response = latest.get('raw_response', '')

# Find the JSON code block
json_match = re.search(r'```json\s*(\{.*?\})\s*```', raw_response, re.DOTALL)

if json_match:
    json_str = json_match.group(1)
    # Pretty print it
    parsed = json.loads(json_str)
    print(json.dumps(parsed, indent=2))
else:
    print("No JSON block found")
    print("\nRaw response preview (first 2000 chars):")
    print(raw_response[:2000])
