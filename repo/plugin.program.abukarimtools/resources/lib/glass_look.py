# -*- coding: utf-8 -*-
"""glass_look.py - ABUKARIM TOOLS (4.8.57, test)

AB Tools' own glass look: white glass icons with no background
(resources/icons_glass, made by tools/gen_glass_icons.py from
resources/icons) and a see-through settings window. Off by default; the
flag is a file in addon_data so every caller reads it without an Addon
object.
"""
import os

import xbmcvfs

ADDON_ID = 'plugin.program.abukarimtools'
_FLAG = 'special://profile/addon_data/%s/glass_look.txt' % ADDON_ID
_SRC = 'resources/icons/'
_DST = 'resources/icons_glass/'


def _flag():
    return xbmcvfs.translatePath(_FLAG)


def is_on():
    try:
        return os.path.isfile(_flag())
    except Exception:
        return False


def set_on(on):
    f = _flag()
    try:
        if on:
            os.makedirs(os.path.dirname(f), exist_ok=True)
            with open(f, 'w') as fh:
                fh.write('1')
        elif os.path.isfile(f):
            os.remove(f)
    except Exception:
        pass
    return is_on()


def toggle():
    return set_on(not is_on())


def icon(path, on=None):
    """The glass copy of an AB Tools icon path (relative or absolute) when the
    look is on and the copy exists; the path itself otherwise."""
    if not path or not (is_on() if on is None else on):
        return path
    p = path.replace('\\', '/')
    i = p.rfind(_SRC)
    if i < 0:
        return path
    glass = p[:i] + _DST + p[i + len(_SRC):]
    if os.path.isabs(glass) and not os.path.isfile(glass):
        return path
    return glass
