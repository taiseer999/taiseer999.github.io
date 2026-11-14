# -*- coding: utf-8 -*-
"""glass_look.py - AB Wizard 4.2.2 (test)

The glass look of ABUKARIM TOOLS 4.8.57 for the wizard: white glass icons
with no background (resources/media/icons_glass, made by
tools/gen_glass_icons.py from resources/media/icons) and the see-through
settings page. There is ONE switch for both add-ons - AB Tools' Toggles >
AB Tools: Glass Look; this reads the same flag file.
"""
import os

import xbmcvfs

_FLAG = 'special://profile/addon_data/plugin.program.abukarimtools/glass_look.txt'
_SRC = '/media/icons/'
_DST = '/media/icons_glass/'


def is_on():
    try:
        return os.path.isfile(xbmcvfs.translatePath(_FLAG))
    except Exception:
        return False


def icon(path):
    """The glass copy of a wizard icon path when the look is on and the copy
    exists; the path itself otherwise."""
    if not path or not is_on():
        return path
    p = path.replace('\\', '/')
    i = p.rfind(_SRC)
    if i < 0:
        return path
    glass = p[:i] + _DST + p[i + len(_SRC):]
    return glass if os.path.isfile(glass) else path
