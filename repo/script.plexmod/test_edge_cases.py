#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Edge case tests for Python 3.14 compatibility

import sys
import os

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib', '_included_packages'))

print(f"Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
print()

from ibis import Template

# Edge case tests
test_cases = [
    {
        'name': 'Negative numbers',
        'template': '{{ -5 + x }}',
        'context': {'x': 10},
        'expected': '5'
    },
    {
        'name': 'Float division',
        'template': '{{ val / 3 }}',
        'context': {'val': 10},
        'expected_contains': '3.3'  # Should be 3.333...
    },
    {
        'name': 'Power operator',
        'template': '{{ base ** exp }}',
        'context': {'base': 2, 'exp': 3},
        'expected': '8'
    },
    {
        'name': 'Modulo operator',
        'template': '{{ num % mod }}',
        'context': {'num': 10, 'mod': 3},
        'expected': '1'
    },
    {
        'name': 'Complex expression',
        'template': '{{ (width - padding * 2) / columns }}',
        'context': {'width': 1000, 'padding': 10, 'columns': 4},
        'expected': '245.0'  # (1000 - 10*2) / 4 = 980 / 4 = 245
    },
    {
        'name': 'Floating point constant',
        'template': '{{ radius * 3.14159 }}',
        'context': {'radius': 10},
        'expected_contains': '31.4159'
    },
]

print("Testing edge cases:")
print("=" * 60)

passed = 0
failed = 0

for test in test_cases:
    try:
        template = Template(test['template'])
        result = template.render(test['context']).strip()

        if 'expected' in test:
            if result == test['expected']:
                print(f"[OK] {test['name']}")
                print(f"     Result: {result}")
                passed += 1
            else:
                print(f"[FAIL] {test['name']}")
                print(f"       Expected: {test['expected']}")
                print(f"       Got: {result}")
                failed += 1
        elif 'expected_contains' in test:
            if test['expected_contains'] in result:
                print(f"[OK] {test['name']}")
                print(f"     Result: {result}")
                passed += 1
            else:
                print(f"[FAIL] {test['name']}")
                print(f"       Expected to contain: {test['expected_contains']}")
                print(f"       Got: {result}")
                failed += 1
    except Exception as e:
        print(f"[FAIL] {test['name']}")
        print(f"       Error: {e}")
        import traceback
        traceback.print_exc()
        failed += 1
    print()

print("=" * 60)
print(f"Results: {passed} passed, {failed} failed")

if failed == 0:
    print("\n[SUCCESS] All edge case tests passed!")
else:
    print(f"\n[FAILURE] {failed} test(s) failed")
