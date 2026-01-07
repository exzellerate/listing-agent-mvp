#!/usr/bin/env python3
"""
Fix remaining unescaped curly braces in claude_analyzer.py prompt.
This complements the previous fix which only covered lines 662-800.
"""
import re

def escape_braces_in_range(lines, start_line, end_line):
    """Escape curly braces in specified line range (1-indexed)."""
    for i in range(start_line - 1, min(end_line, len(lines))):
        line = lines[i]

        # Skip lines that are already escaped (contain {{ or }})
        if '{{' in line or '}}' in line:
            continue

        # Preserve already-doubled braces
        line = line.replace('{{', '\x00DOUBLE_OPEN\x00')
        line = line.replace('}}', '\x00DOUBLE_CLOSE\x00')

        # Escape single braces
        line = line.replace('{', '{{')
        line = line.replace('}', '}}')

        # Restore doubled braces as quadrupled
        line = line.replace('\x00DOUBLE_OPEN\x00', '{{{{')
        line = line.replace('\x00DOUBLE_CLOSE\x00', '}}}}')

        lines[i] = line

    return lines

# Read file
with open('services/claude_analyzer.py', 'r') as f:
    lines = f.readlines()

print(f"Original file has {len(lines)} lines")

# Fix lines 508-661 (the section before the previously fixed 662-800)
# This includes the JSON examples at lines 568-574 and 578-582
print("Escaping curly braces in lines 508-661...")
lines = escape_braces_in_range(lines, 508, 661)

# Fix lines 801-932 (the section after the previously fixed 662-800)
print("Escaping curly braces in lines 801-932...")
lines = escape_braces_in_range(lines, 801, 932)

# Write back
with open('services/claude_analyzer.py', 'w') as f:
    f.writelines(lines)

print("✓ Fixed remaining curly braces")
print("✓ Lines 508-661: Escaped")
print("✓ Lines 801-932: Escaped")
print("✓ Lines 662-800: Already fixed (preserved)")
