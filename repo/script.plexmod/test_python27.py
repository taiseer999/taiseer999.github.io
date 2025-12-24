# coding: utf-8
# Test script for Python 2.7 compatibility with ibis safe_math_eval

import sys
import os

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib', '_included_packages'))

print("Python version: " + str(sys.version))
print("Python version info: " + str(sys.version_info))
print("")

# Import the ibis nodes module
try:
    from ibis import nodes
    print("[OK] Successfully imported ibis.nodes")
except Exception as e:
    print("[FAIL] Failed to import ibis.nodes: " + str(e))
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test cases - expressions that should work
test_expressions = [
    ("wbg_w / 2 - 8", "The problematic expression from the error"),
    ("10 + 20", "Simple constant math"),
    ("x + 5", "Variable with constant"),
    ("a * b / 2", "Multiple variables"),
    ("width / 2 - offset", "More realistic template expression"),
    ("3.14 * radius", "Float constant with variable"),
    ("-5 + x", "Negative constant"),
]

print("Testing safe_math_eval with various expressions:")
print("=" * 60)

for expr, description in test_expressions:
    try:
        result = nodes.safe_math_eval(expr)
        if isinstance(result, list):
            print("[OK] '" + expr + "'")
            print("     -> Variables detected: " + str(result))
        else:
            print("[OK] '" + expr + "'")
            print("     -> Evaluated to constant: " + str(result))
    except Exception as e:
        print("[FAIL] '" + expr + "'")
        print("       -> Error: " + str(e))
        import traceback
        traceback.print_exc()
    print("")

print("=" * 60)
print("Test complete!")
