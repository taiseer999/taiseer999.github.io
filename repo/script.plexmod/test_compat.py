# coding: utf-8
# Compatibility test for Python 2.7 and 3.x

import sys
import os

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib', '_included_packages'))

print("Python {}.{}.{}".format(sys.version_info[0], sys.version_info[1], sys.version_info[2]))

from ibis import Template, nodes

# Test cases covering edge cases with math expressions
tests = [
    ("wbg_w / 2 - 8", {'wbg_w': 100}, "Expression from error"),
    ("0 + x", {'x': 5}, "Constant 0"),
    ("x + 1", {'x': 0}, "Variable with value 0"),
    ("y * 0", {'y': 100}, "Multiply by 0"),
    ("-5 + z", {'z': 10}, "Negative constant"),
]

print("\nTesting safe_math_eval:")
print("-" * 40)
for expr, ctx, desc in tests:
    try:
        result = nodes.safe_math_eval(expr)
        print("[OK] {}: {}".format(desc, expr))
    except Exception as e:
        print("[FAIL] {}: {} - {}".format(desc, expr, str(e)))

print("\nTesting template rendering:")
print("-" * 40)
for expr, ctx, desc in tests:
    try:
        template_str = "{{ " + expr + " }}"
        t = Template(template_str)
        result = t.render(ctx)
        print("[OK] {}: result='{}'".format(desc, result.strip()))
    except Exception as e:
        print("[FAIL] {}: {}".format(desc, str(e)))

print("\nAll tests completed!")
