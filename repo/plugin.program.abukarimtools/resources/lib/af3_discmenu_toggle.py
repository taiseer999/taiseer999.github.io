# -*- coding: utf-8 -*-
"""
af3_discmenu_toggle.py - ABUKARIM TOOLS (4.7.36)

Toggles entry "AF3: Disc Menu for ISO Streams". Flips the AF3 skin bool
abk.discmenu; the always-on patcher entries ("AF3 Disc Menu", VideoOSD.xml)
read it, so the two OSD buttons appear / go at once - no skin reload unless
the XML was only just patched. The buttons show only while a Blu-ray ISO
plays from a stream; disc_menu.py does the switching.
"""
import os

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

SKIN_ID = 'skin.arctic.fuse.3'
SETTING = 'abk.discmenu'
TITLE = 'ABUKARIM TOOLS'
MARK = '<!-- ABUKARIM: AF3 disc menu buttons -->'


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools DiscMenu] %s' % msg, level)


def disc_menu_on():
    return bool(xbmc.getCondVisibility('Skin.HasSetting(%s)' % SETTING))


def _ensure_patch():
    """(patched_ok, xml_changed)."""
    try:
        from resources.lib import patcher
        _ok, _failed, changed, _r = patcher.apply_set(addon_ids=[SKIN_ID])
    except Exception as exc:
        _log('skin patch failed: %s' % exc, xbmc.LOGWARNING)
        return False, False
    try:
        path = os.path.join(xbmcvfs.translatePath('special://home/addons/%s/' % SKIN_ID),
                            '1080i', 'VideoOSD.xml')
        with open(path, 'r', encoding='utf-8') as f:
            ok = MARK in f.read()
    except Exception:
        ok = False
    return ok, changed > 0


def run():
    if not xbmc.getCondVisibility('System.HasAddon(%s)' % SKIN_ID):
        xbmcgui.Dialog().ok(TITLE, T(30440))          # AF3 is not installed
        return
    if xbmc.getSkinDir() != SKIN_ID:
        xbmcgui.Dialog().ok(TITLE, T(30602))          # switch to AF3 first
        return
    ok, reload_needed = _ensure_patch()
    if disc_menu_on():
        xbmc.executebuiltin('Skin.Reset(%s)' % SETTING)
        msg = T(32104)
        _log('disc menu buttons: OFF')
    else:
        if not ok:
            xbmcgui.Dialog().ok(TITLE, T(32105))
            return
        xbmc.executebuiltin('Skin.SetBool(%s)' % SETTING)
        msg = T(32103)
        _log('disc menu buttons: ON')
    xbmcgui.Dialog().notification(TITLE, msg, xbmcgui.NOTIFICATION_INFO, 3000)
    if reload_needed:
        xbmc.sleep(300)
        xbmc.executebuiltin('ReloadSkin()')
    else:
        xbmc.executebuiltin('Container.Refresh')
