#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Comprehensive test for ibis template rendering in Python 3.14

import sys
import os

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib', '_included_packages'))

print(f"Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
print()

# Import ibis
try:
    import ibis
    from ibis import Template
    print("[OK] Successfully imported ibis")
except Exception as e:
    print(f"[FAIL] Failed to import ibis: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test template rendering with math expressions
test_cases = [
    {
        'name': 'Simple math with variables',
        'template': '{{ wbg_w / 2 - 8 }}',
        'context': {'wbg_w': 100},
        'expected': '42.0'  # 100 / 2 - 8 = 50 - 8 = 42
    },
    {
        'name': 'Multiple operations',
        'template': '{{ width / 2 - offset }}',
        'context': {'width': 200, 'offset': 10},
        'expected': '90.0'  # 200 / 2 - 10 = 100 - 10 = 90
    },
    {
        'name': 'Multiplication and division',
        'template': '{{ value * 2 / 4 }}',
        'context': {'value': 8},
        'expected': '4.0'  # 8 * 2 / 4 = 16 / 4 = 4
    },
    {
        'name': 'Constant expression',
        'template': '{{ 100 / 2 - 8 }}',
        'context': {},
        'expected': '42.0'
    },
    {
        'name': 'Addition and subtraction',
        'template': '{{ x + y - z }}',
        'context': {'x': 10, 'y': 5, 'z': 3},
        'expected': '12'
    },
]

print("Testing template rendering with math expressions:")
print("=" * 60)

passed = 0
failed = 0

for test in test_cases:
    try:
        template = Template(test['template'])
        result = template.render(test['context'])

        # Normalize result (strip whitespace)
        result = result.strip()
        expected = test['expected']

        if result == expected:
            print(f"[OK] {test['name']}")
            print(f"     Template: {test['template']}")
            print(f"     Result: {result}")
            passed += 1
        else:
            print(f"[FAIL] {test['name']}")
            print(f"       Template: {test['template']}")
            print(f"       Expected: {expected}")
            print(f"       Got: {result}")
            failed += 1
    except Exception as e:
        print(f"[FAIL] {test['name']}")
        print(f"       Template: {test['template']}")
        print(f"       Error: {e}")
        import traceback
        traceback.print_exc()
        failed += 1
    print()

print("=" * 60)
print(f"Test Results: {passed} passed, {failed} failed")

if failed == 0:
    print("\n[SUCCESS] All tests passed!")
    sys.exit(0)
else:
    print(f"\n[FAILURE] {failed} test(s) failed")
    sys.exit(1)
