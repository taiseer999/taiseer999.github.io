# -*- coding: utf-8 -*-
"""
af3_lucentplayer_toggle.py - ABUKARIM TOOLS (4.7.25)

Toggles entry "AF3: Lucent Player". djdirty60's Lucent player
(github.com/djdirty60/Lucent, GPL-2.0-or-later) ported to Arctic Fuse 3: the
OSD, the seek bar with the "YOU'RE WATCHING" pause card, the buffering spinner
and the Statistics window that replaces the PPI. The always-on AF3 patches in
patcher.py install the files and gate everything on the skin bool
abk.lucentplayer; this flips the bool and reloads the skin (the OSD includes
are conditional includes, evaluated when the skin loads). Live TV keeps the
Arctic Fuse 3 OSD.
"""
import os

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

SKIN_ID = 'skin.arctic.fuse.3'
SETTING = 'abk.lucentplayer'
TITLE = 'ABUKARIM TOOLS'
_FILES = ('Includes_ABK_LucentPlayer.xml', 'ABK_LucentPlayerInfo.xml')


def _log(msg):
    xbmc.log('[AbukarimTools LucentPlayer] %s' % msg, xbmc.LOGINFO)


def player_on():
    return bool(xbmc.getCondVisibility('Skin.HasSetting(%s)' % SETTING))


def _skin_dir():
    try:
        from resources.lib import patcher
        d = patcher._resolve_addon_dir(SKIN_ID)
        if d:
            return d
    except Exception:
        pass
    return xbmcvfs.translatePath('special://home/addons/%s' % SKIN_ID)


def _files_present():
    d = os.path.join(_skin_dir(), '1080i')
    return all(os.path.isfile(os.path.join(d, f)) for f in _FILES)


def _ensure_patch():
    """Apply the AF3 patches now; True when a skin file changed."""
    try:
        from resources.lib import patcher
        _ok, _failed, changed, _r = patcher.apply_set(addon_ids=[SKIN_ID])
        return changed > 0
    except Exception as exc:
        _log('skin patch failed: %s' % exc)
        return False


def set_on(on):
    """Silent switch (setup wizard / Toggles page). The caller reloads."""
    if on and not _files_present():
        raise RuntimeError('Lucent Player files are not in the skin')
    xbmc.executebuiltin(('Skin.SetBool(%s)' if on else 'Skin.Reset(%s)') % SETTING)
    _log('Lucent Player: %s' % ('ON' if on else 'OFF'))
    return 'Lucent Player %s' % ('on' if on else 'off')


def run():
    if not xbmc.getCondVisibility('System.HasAddon(%s)' % SKIN_ID):
        xbmcgui.Dialog().ok(TITLE, T(30440))          # AF3 is not installed
        return
    if xbmc.getSkinDir() != SKIN_ID:
        xbmcgui.Dialog().ok(TITLE, T(30602))          # switch to AF3 first
        return
    _ensure_patch()
    turn_on = not player_on()
    if turn_on and not _files_present():
        xbmcgui.Dialog().ok(TITLE, T(32083))
        return
    set_on(turn_on)
    xbmcgui.Dialog().notification(TITLE, T(32081) if turn_on else T(32082),
                                  xbmcgui.NOTIFICATION_INFO, 3000)
    # the OSD hooks are conditional includes: always reload
    xbmc.sleep(300)
    xbmc.executebuiltin('ReloadSkin()')
