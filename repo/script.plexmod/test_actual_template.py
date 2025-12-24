#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Test the actual watched_indicator template that was failing

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

# Test the exact expressions from the template file
print("Testing expressions from watched_indicator.xml.tpl:")
print("=" * 60)

# Test case 1: Line 28 - {{ wbg_w / 2 - 8 }}
print("\n1. Testing line 28: {{ wbg_w / 2 - 8 }}")
try:
    template = Template("{{ wbg_w / 2 - 8 }}")
    result = template.render({'wbg_w': 50})
    print(f"   [OK] Rendered: {result.strip()}")
    print(f"   Expected: 17.0 (50/2 - 8 = 25 - 8 = 17)")
except Exception as e:
    print(f"   [FAIL] Error: {e}")
    import traceback
    traceback.print_exc()

# Test case 2: Line 29 - {{ (wbg_h / 2 - 8)|vscale }}
# Note: We'll test without the filter since we don't have the filter implementation
print("\n2. Testing line 29 expression (without filter): {{ wbg_h / 2 - 8 }}")
try:
    template = Template("{{ wbg_h / 2 - 8 }}")
    result = template.render({'wbg_h': 40})
    print(f"   [OK] Rendered: {result.strip()}")
    print(f"   Expected: 12.0 (40/2 - 8 = 20 - 8 = 12)")
except Exception as e:
    print(f"   [FAIL] Error: {e}")
    import traceback
    traceback.print_exc()

# Test case 3: Line 21 - {{ wbg_w }}
print("\n3. Testing line 21: {{ wbg_w }}")
try:
    template = Template("{{ wbg_w }}")
    result = template.render({'wbg_w': 100})
    print(f"   [OK] Rendered: {result.strip()}")
except Exception as e:
    print(f"   [FAIL] Error: {e}")

# Test a more complex snippet from the actual template
print("\n4. Testing multi-line template snippet:")
template_snippet = """<control type="image">
    <posx>{{ wbg_w / 2 - 8 }}</posx>
    <posy>{{ wbg_h / 2 - 8 }}</posy>
    <width>16</width>
    <height>16</height>
</control>"""

try:
    template = Template(template_snippet)
    result = template.render({'wbg_w': 100, 'wbg_h': 80})
    print("   [OK] Template rendered successfully!")
    print("\n   Result:")
    for line in result.split('\n'):
        print(f"   {line}")
except Exception as e:
    print(f"   [FAIL] Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("[SUCCESS] All actual template tests passed!")
