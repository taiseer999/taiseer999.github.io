# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools, see LICENSE.txt
"""
af3_defaultosd_toggle.py - ABUKARIM TOOLS (4.10.9)

Toggles entry "AF3: Default OSD". Taiseer's AF3 (50.11.87+) keeps its own info
line - plain labels and its own pillbox style - and leaves out what upstream
Arctic Fuse 3 (3.5.6) made the default there: the item details drawn as
outlined tags, the star rating on a solid pill, and the "Plain text / Pill"
choice in Skin settings > Information. This switch brings those back.

The skin does the drawing; this flips the AF3 skin bool abk.defaultosd. The
info line picks the tags at skin load (include conditions), so the skin is
reloaded after the switch. Turning it on also clears InfoTags.DisableTags so
the Pill style shows straight away; the skin setting can still pick Plain text.
"""
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
    if on:
        xbmc.executebuiltin('Skin.SetBool(%s)' % SETTING)
        xbmc.executebuiltin('Skin.Reset(%s)' % PLAIN)
    else:
        xbmc.executebuiltin('Skin.Reset(%s)' % SETTING)
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
