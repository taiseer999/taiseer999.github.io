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


def _g(path):
    try:
        from resources.lib import glass_look
        return glass_look.icon(path)
    except Exception:
        return path


def icon(on):
    return _g(ICON_ON if on else ICON_OFF)


def state_text(on):
    return T(30436) if on else T(30437)          # On / Off


def item(label, on, label2=None):
    li = xbmcgui.ListItem(label, label2 if label2 is not None else state_text(on),
                          offscreen=True)
    ic = icon(on)
    li.setArt({'icon': ic, 'thumb': ic})
    return li


def switch_list(title, rows, done_label=None, confirm_back=None):
    """rows: [(key, label, on), ...]. Returns {key: on} after "Done", or None
    on Back. Each pick flips that switch and reopens the list on the same row.
    A list that answers faster than a person can (Kodi swallowed it while
    busy) is reopened instead of being treated as Back.

    3.4.13: confirm_back=(message, yeslabel, nolabel). When given and Back is
    pressed after at least one switch was flipped, ask first: yes returns the
    new states exactly like "Done", no discards them (None). Before this,
    Back silently threw the flips away and nothing was saved (2026-10-19:
    a switch turned off, never saved, stayed on)."""
    states = [(k, l, bool(o)) for k, l, o in rows]
    initial = {k: o for k, _l, o in states}
    done = done_label or T(30604)
    pos, quick = 0, 0
    while True:
        lis = [xbmcgui.ListItem(done, offscreen=True)]
        lis[0].setArt({'icon': _g(ICON_DONE), 'thumb': _g(ICON_DONE)})
        lis += [item(l, o) for _k, l, o in states]
        started = time.monotonic()
        choice = xbmcgui.Dialog().select(title, lis, preselect=pos, useDetails=True)
        if choice < 0:
            if time.monotonic() - started < 1.0 and quick < 3:
                quick += 1
                xbmc.sleep(800)
                continue
            current = {k: o for k, _l, o in states}
            if confirm_back and current != initial:
                msg, yes, no = confirm_back
                if xbmcgui.Dialog().yesno(title, msg, yeslabel=yes, nolabel=no):
                    return current
            return None
        quick = 0
        if choice == 0:
            return {k: o for k, _l, o in states}
        k, l, o = states[choice - 1]
        states[choice - 1] = (k, l, not o)
        pos = choice


def option_list(title, rows, done_label=None):
    """4.7.9 (setup wizard, all toggles on one page).

    rows: [(key, label, value, choices), ...]
      choices None      -> on/off switch, value is a bool; a pick flips it
      choices [(v, l)]  -> several states; a pick moves to the next one,
                           label2 shows the state, the switch shows "on" for
                           anything but the first state (Off / Original)
    Returns {key: value} after "Done" and also on Back (Back moves on, it is
    never a cancel of the wizard - the summary page can change it again). A list that answers
    faster than a person can is shown again, as in switch_list."""
    states = [[k, l, v, c] for k, l, v, c in rows]
    pos, quick = 0, 0
    done = done_label or T(30604)
    while True:
        lis = [xbmcgui.ListItem(done, offscreen=True)]
        lis[0].setArt({'icon': _g(ICON_DONE), 'thumb': _g(ICON_DONE)})
        for _k, l, v, c in states:
            if c is None:
                lis.append(item(l, bool(v)))
            else:
                names = dict(c)
                lis.append(item(l, v != c[0][0], names.get(v, str(v))))
        started = time.monotonic()
        choice = xbmcgui.Dialog().select(title, lis, preselect=pos, useDetails=True)
        if choice < 0:
            if time.monotonic() - started < 1.0 and quick < 3:
                quick += 1
                xbmc.sleep(800)
                continue
            return {k: v for k, _l, v, _c in states}
        quick = 0
        if choice == 0:
            return {k: v for k, _l, v, _c in states}
        row = states[choice - 1]
        if row[3] is None:
            row[2] = not row[2]
        else:
            vals = [v for v, _l in row[3]]
            i = vals.index(row[2]) if row[2] in vals else -1
            row[2] = vals[(i + 1) % len(vals)]
        pos = choice
