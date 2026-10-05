# -*- coding: utf-8 -*-
"""On/off switch art used everywhere ABUKARIM TOOLS shows a state (3.2.23).

    icon(on)                 -> path of toggle_on.png / toggle_off.png
    item(label, on, ...)     -> ListItem with the switch as icon + On/Off label2
    switch_list(title, rows) -> a list of switches; picking a row flips it,
                                the first row ("Done") returns the new states.
"""
import os
import time

import xbmc
import xbmcgui

from resources.lib import paths
from resources.lib.i18n import T

ICON_ON = os.path.join(paths.ADDON_PATH, 'resources', 'icons', 'toggle_on.png')
ICON_OFF = os.path.join(paths.ADDON_PATH, 'resources', 'icons', 'toggle_off.png')
ICON_DONE = os.path.join(paths.ADDON_PATH, 'resources', 'icons', 'patcher.png')


def icon(on):
    return ICON_ON if on else ICON_OFF


def state_text(on):
    return T(30436) if on else T(30437)          # On / Off


def item(label, on, label2=None):
    li = xbmcgui.ListItem(label, label2 if label2 is not None else state_text(on),
                          offscreen=True)
    ic = icon(on)
    li.setArt({'icon': ic, 'thumb': ic})
    return li


def switch_list(title, rows, done_label=None):
    """rows: [(key, label, on), ...]. Returns {key: on} after "Done", or None
    on Back. Each pick flips that switch and reopens the list on the same row.
    A list that answers faster than a person can (Kodi swallowed it while
    busy) is reopened instead of being treated as Back."""
    states = [(k, l, bool(o)) for k, l, o in rows]
    done = done_label or T(30604)
    pos, quick = 0, 0
    while True:
        lis = [xbmcgui.ListItem(done, offscreen=True)]
        lis[0].setArt({'icon': ICON_DONE, 'thumb': ICON_DONE})
        lis += [item(l, o) for _k, l, o in states]
        started = time.monotonic()
        choice = xbmcgui.Dialog().select(title, lis, preselect=pos, useDetails=True)
        if choice < 0:
            if time.monotonic() - started < 1.0 and quick < 3:
                quick += 1
                xbmc.sleep(800)
                continue
            return None
        quick = 0
        if choice == 0:
            return {k: o for k, _l, o in states}
        k, l, o = states[choice - 1]
        states[choice - 1] = (k, l, not o)
        pos = choice
