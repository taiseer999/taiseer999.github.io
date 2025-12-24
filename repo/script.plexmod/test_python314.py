#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Test script for Python 3.14 compatibility with ibis safe_math_eval

import sys
import os

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add lib directory to path so we can import ibis and six
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib', '_included_packages'))

print(f"Python version: {sys.version}")
print(f"Python version info: {sys.version_info}")
print()

# Import the ibis nodes module which contains safe_math_eval
try:
    from ibis import nodes
    print("[OK] Successfully imported ibis.nodes")
except Exception as e:
    print(f"[FAIL] Failed to import ibis.nodes: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test cases - expressions that should work
test_expressions = [
    "wbg_w / 2 - 8",      # The problematic expression from the error
    "10 + 20",            # Simple constant math
    "x + 5",              # Variable with constant
    "a * b / 2",          # Multiple variables
    "width / 2 - offset", # More realistic template expression
    "3.14 * radius",      # Float constant with variable
    "-5 + x",             # Negative constant
]

print("Testing safe_math_eval with various expressions:")
print("=" * 60)

for expr in test_expressions:
    try:
        result = nodes.safe_math_eval(expr)
        if isinstance(result, list):
            print(f"[OK] '{expr}'")
            print(f"     -> Variables detected: {result}")
        else:
            print(f"[OK] '{expr}'")
            print(f"     -> Evaluated to constant: {result}")
    except Exception as e:
        print(f"[FAIL] '{expr}'")
        print(f"       -> Error: {e}")
        import traceback
        traceback.print_exc()
    print()

print("=" * 60)
print("Test complete!")
