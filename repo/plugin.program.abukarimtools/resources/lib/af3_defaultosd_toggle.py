# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""
af3_defaultosd_toggle.py - ABUKARIM TOOLS (4.10.9, 4.10.10)

Toggles entry "AF3: Default OSD". Taiseer's AF3 (50.11.87+) keeps its own info
line - plain labels and its own pillbox style - and leaves out what upstream
Arctic Fuse 3 (3.5.6) made the default there: the item details drawn as
outlined tags, the star rating on a solid pill, and the "Plain text / Pill"
choice in Skin settings > Information. This switch brings those back.

The skin does the drawing; this flips the AF3 skin bool abk.defaultosd. The
info line picks the tags at skin load (include conditions), so the skin is
reloaded after the switch. Turning it on also clears InfoTags.DisableTags so
the Pill style shows straight away; the skin setting can still pick Plain text.

4.10.10: upstream draws the details on ONE row (the "i" pill, the stars, the
date and the duration side by side). AF3's "Two-line information bar"
(InfoBar.TwoRow - also switched on by AF3: Plot on the Right) splits them and
keeps the plain labels on the second row, so turning Default OSD on also turns
TwoRow off; turning it off again restores TwoRow only when this switch cleared it.
"""
import json
import os

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

SKIN_ID = 'skin.arctic.fuse.3'
SETTING = 'abk.defaultosd'
PLAIN = 'InfoTags.DisableTags'
TITLE = 'ABUKARIM TOOLS'
MARK = 'name="Exp_ABK_DefaultOSD_Tags"'
TWOROW = 'InfoBar.TwoRow'
_STATE = os.path.join(xbmcvfs.translatePath('special://profile/addon_data/'),
                      'plugin.program.abukarimtools', 'af3_defaultosd.json')


def _load():
    try:
        with open(_STATE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(data):
    try:
        os.makedirs(os.path.dirname(_STATE), exist_ok=True)
        with open(_STATE, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except Exception as e:
        _log('state not saved: %s' % e, xbmc.LOGWARNING)


def _tworow_on():
    return bool(xbmc.getCondVisibility('Skin.HasSetting(%s)' % TWOROW))


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools DefaultOSD] %s' % msg, level)


def default_osd_on():
    return bool(xbmc.getCondVisibility('Skin.HasSetting(%s)' % SETTING))


def skin_supports():
    """True when the installed AF3 has the Default OSD support (50.11.87+)."""
    try:
        path = os.path.join(xbmcvfs.translatePath('special://home/addons/%s/' % SKIN_ID),
                            '1080i', 'Includes_Expressions.xml')
        with open(path, 'r', encoding='utf-8') as f:
            return MARK in f.read()
    except Exception:
        return False


def set_on(on):
    state = _load()
    if on:
        xbmc.executebuiltin('Skin.SetBool(%s)' % SETTING)
        xbmc.executebuiltin('Skin.Reset(%s)' % PLAIN)
        if _tworow_on():                       # one row, like upstream
            xbmc.executebuiltin('Skin.Reset(%s)' % TWOROW)
            state['tworow_cleared'] = True
            _log('two-line information bar turned off (one row, like upstream)')
    else:
        xbmc.executebuiltin('Skin.Reset(%s)' % SETTING)
        if state.pop('tworow_cleared', False) and not _tworow_on():
            xbmc.executebuiltin('Skin.SetBool(%s)' % TWOROW)
            _log('two-line information bar restored')
    _save(state)
    _log('default OSD: %s' % ('ON' if on else 'OFF'))
    return 'default OSD %s' % ('on' if on else 'off')


def run():
    if not xbmc.getCondVisibility('System.HasAddon(%s)' % SKIN_ID):
        xbmcgui.Dialog().ok(TITLE, T(30440))          # AF3 is not installed
        return
    if xbmc.getSkinDir() != SKIN_ID:
        xbmcgui.Dialog().ok(TITLE, T(30602))          # switch to AF3 first
        return
    if default_osd_on():
        set_on(False)
        msg = T(32312)
    else:
        if not skin_supports():
            xbmcgui.Dialog().ok(TITLE, T(32313))      # needs AF3 50.11.87 or newer
            return
        set_on(True)
        msg = T(32311)
    xbmcgui.Dialog().notification(TITLE, msg, xbmcgui.NOTIFICATION_INFO, 3000)
    xbmc.sleep(300)
    from resources.lib.settings_engine import safe_reload_skin   # the tags are chosen at skin load
    safe_reload_skin()
