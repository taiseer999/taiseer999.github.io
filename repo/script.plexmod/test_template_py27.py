# coding: utf-8
# Template rendering test for Python 2.7

import sys
import os

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib', '_included_packages'))

print("Python version: {}.{}.{}".format(sys.version_info.major, sys.version_info.minor, sys.version_info.micro))
print("")

from ibis import Template

# Test template rendering with math expressions
test_cases = [
    {
        'name': 'Simple math with variables (line 28 from error)',
        'template': '{{ wbg_w / 2 - 8 }}',
        'context': {'wbg_w': 100},
        'expected': '42.0'
    },
    {
        'name': 'Multiple operations',
        'template': '{{ width / 2 - offset }}',
        'context': {'width': 200, 'offset': 10},
        'expected': '90.0'
    },
    {
        'name': 'Constant expression',
        'template': '{{ 100 / 2 - 8 }}',
        'context': {},
        'expected': '42.0'
    },
]

print("Testing template rendering:")
print("=" * 60)

passed = 0
failed = 0

for test in test_cases:
    try:
        template = Template(test['template'])
        result = template.render(test['context']).strip()
        expected = test['expected']

        if result == expected:
            print("[OK] " + test['name'])
            print("     Template: " + test['template'])
            print("     Result: " + result)
            passed += 1
        else:
            print("[FAIL] " + test['name'])
            print("       Expected: " + expected)
            print("       Got: " + result)
            failed += 1
    except Exception as e:
        print("[FAIL] " + test['name'])
        print("       Error: " + str(e))
        import traceback
        traceback.print_exc()
        failed += 1
    print("")

print("=" * 60)
print("Results: {} passed, {} failed".format(passed, failed))

if failed == 0:
    print("\n[SUCCESS] All tests passed!")
else:
    print("\n[FAILURE] {} test(s) failed".format(failed))
