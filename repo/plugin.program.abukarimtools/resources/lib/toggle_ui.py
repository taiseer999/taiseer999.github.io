# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools, see LICENSE.txt
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


# ---------------------------------------------------------------- 4.9.3
# The switch lists in a window of their own (abk_switches.xml): "Done" is a
# button at the top instead of the first row, and a pick flips the switch in
# place (no reopening). The old Kodi list below stays as the fallback.
XML = 'abk_switches.xml'


def _rtl():
    try:
        return (xbmc.getLanguage(xbmc.ISO_639_1) or '').lower() in ('ar', 'he', 'fa', 'ur')
    except Exception:
        return False


def _short_done(label):
    import re
    return re.sub(r'\[/?B\]', '', label or '').split(' - ')[0].strip() or T(32286)


class _Switches(xbmcgui.WindowXMLDialog):
    """rows: [[key, label, value, choices]] (choices None = on/off)."""
    def __init__(self, *args, **kwargs):
        self.rows = kwargs.pop('rows')
        self.title = kwargs.pop('title', '')
        self.done_text = kwargs.pop('done', '')
        self.result = None              # 'done' or None (Back)
        self.lis = []
        super().__init__(*args, **kwargs)

    def _li(self, row):
        # not offscreen: the item is changed while the window shows it
        li = xbmcgui.ListItem(row[1])
        self._paint(li, row)
        return li

    def _paint(self, li, row):
        _k, _l, v, c = row
        if c is None:
            on, text = bool(v), state_text(bool(v))
        else:
            on, text = v != c[0][0], dict(c).get(v, str(v))
        ic = icon(on)
        li.setArt({'icon': ic, 'thumb': ic})
        li.setLabel2(text)

    def onInit(self):
        self.setProperty('dir', 'rtl' if _rtl() else 'ltr')
        self.setProperty('title', self.title)
        self.setProperty('done', self.done_text)
        lst = self.getControl(100)
        lst.reset()
        self.lis = [self._li(r) for r in self.rows]
        lst.addItems(self.lis)
        self.setFocusId(100)

    def onClick(self, control_id):
        if control_id in (200, 201):
            self.result = 'done'
            self.close()
            return
        if control_id == 100:
            pos = self.getControl(100).getSelectedPosition()
            if not 0 <= pos < len(self.rows):
                return
            row = self.rows[pos]
            if row[3] is None:
                row[2] = not row[2]
            else:
                vals = [v for v, _l in row[3]]
                i = vals.index(row[2]) if row[2] in vals else -1
                row[2] = vals[(i + 1) % len(vals)]
            self._paint(self.lis[pos], row)

    def onAction(self, action):
        if action.getId() in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK):
            self.close()


def _window(title, rows, done_label):
    """('done' | None, rows) - None when the window could not be shown."""
    try:
        w = _Switches(XML, paths.ADDON_PATH, 'Default', '1080i',
                      rows=rows, title=title, done=_short_done(done_label))
        w.doModal()
        res = w.result
        del w
        return res, rows
    except Exception as e:
        xbmc.log('[AbukarimTools Switches] window failed, using the list: %s' % e, xbmc.LOGWARNING)
        return False, rows


def switch_list(title, rows, done_label=None, confirm_back=None):
    rs = [[k, l, bool(o), None] for k, l, o in rows]
    initial = {k: bool(o) for k, _l, o in rows}
    res, rs = _window(title, rs, done_label)
    if res is not False:
        current = {k: v for k, _l, v, _c in rs}
        if res == 'done':
            return current
        if confirm_back and current != initial:
            msg, yes, no = confirm_back
            if xbmcgui.Dialog().yesno(title, msg, yeslabel=yes, nolabel=no):
                return current
        return None
    return _switch_list_dialog(title, rows, done_label, confirm_back)


def option_list(title, rows, done_label=None):
    rs = [[k, l, v, c] for k, l, v, c in rows]
    res, rs = _window(title, rs, done_label)
    if res is not False:
        return {k: v for k, _l, v, _c in rs}      # Back moves on too (see below)
    return _option_list_dialog(title, rows, done_label)


def _switch_list_dialog(title, rows, done_label=None, confirm_back=None):
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


def _option_list_dialog(title, rows, done_label=None):
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
