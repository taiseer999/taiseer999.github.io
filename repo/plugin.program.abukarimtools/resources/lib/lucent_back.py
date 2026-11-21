# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""
lucent_back.py - AB Tools (rewritten for AB Tools in 4.12.0)

The Back key in the fullscreen player while "AF3: Lucent Player" is on:

  while fast-forwarding or rewinding    -> normal speed again, video stays
  while the seek bar is up / just after
  a skip                                -> the seek bar closes, video stays
  any other time                        -> Kodi's own Back

A keymap in the profile (FullscreenVideo only) sends Back here; the OSD, the
pause card and every menu keep Kodi's Back. sync_keymap() writes the keymap
while Lucent Player is on and removes it otherwise; the toggle, the skin
switcher and the service call it.

    RunScript(special://home/addons/plugin.program.abukarimtools/resources/lib/lucent_back.py)
"""
import xbmc
import xbmcvfs

AF3 = 'skin.arctic.fuse.3'
SKIN_BOOL = 'abk.lucentplayer'
KEYMAP_DIR = 'special://profile/keymaps/'
KEYMAP_PATH = KEYMAP_DIR + 'abk-lucentplayer-back.xml'
_SCRIPT = 'RunScript(special://home/addons/plugin.program.abukarimtools/resources/lib/lucent_back.py)'


def _keymap():
    keys = ''.join('            <%s>%s</%s>\n' % (k, _SCRIPT, k) for k in ('backspace', 'browser_back'))
    return ('<keymap>\n'
            '    <!-- AB Tools - AF3: Lucent Player. Back ends fast-forward, rewind and the\n'
            '         seek bar; any other time it is Kodi\'s Back. Removed with Lucent Player. -->\n'
            '    <FullscreenVideo>\n'
            '        <keyboard>\n%s'
            '        </keyboard>\n'
            '        <remote>\n'
            '            <back>%s</back>\n'
            '        </remote>\n'
            '    </FullscreenVideo>\n'
            '</keymap>\n') % (keys, _SCRIPT)


KEYMAP = _keymap()


def _log(msg):
    xbmc.log('[AbukarimTools LucentBack] %s' % msg, xbmc.LOGINFO)


def _is(condition):
    return bool(xbmc.getCondVisibility(condition))


def lucent_player_on():
    return xbmc.getSkinDir() == AF3 and _is('Skin.HasSetting(%s)' % SKIN_BOOL)


def handle():
    """What Back does now (called by the keymap)."""
    if lucent_player_on():
        if _is('Player.Forwarding') or _is('Player.Rewinding'):
            xbmc.executebuiltin('PlayerControl(Play)')
            return
        if _is('Player.Seeking') or _is('Player.HasPerformedSeek(3)'):
            xbmc.executebuiltin('Dialog.Close(seekbar)')
            return
    xbmc.executebuiltin('Action(Back)')


def _text(path):
    try:
        fh = xbmcvfs.File(path)
    except Exception:
        return None
    try:
        return fh.read()
    finally:
        fh.close()


def clear_lucent_keymaps():
    """The Lucent skin leaves keymaps in the profile (lucent-*.xml) that run
    special://skin/scripts/...; under any other skin those scripts are missing,
    so the keys they take (Back, OK) do nothing. Delete them while Lucent is not
    the skin (Lucent writes them again when it runs). True when one went."""
    if xbmc.getSkinDir() == 'skin.lucent':
        return False
    try:
        names = xbmcvfs.listdir(KEYMAP_DIR)[1]
    except Exception:
        return False
    removed = []
    for name in names:
        if not (name.startswith('lucent-') and name.endswith('.xml')):
            continue
        body = _text(KEYMAP_DIR + name)
        if body and 'special://skin/scripts/' in body and xbmcvfs.delete(KEYMAP_DIR + name):
            removed.append(name)
    if removed:
        _log('removed Lucent skin keymaps (Lucent is not the skin): %s' % ', '.join(removed))
    return bool(removed)


def sync_keymap(wanted=None):
    """Write the keymap while Lucent Player is on, remove it otherwise.
    True when a keymap file changed (Kodi then reloads its keymaps)."""
    if wanted is None:
        wanted = lucent_player_on()
    current = _text(KEYMAP_PATH) if xbmcvfs.exists(KEYMAP_PATH) else None
    changed = clear_lucent_keymaps()
    if wanted and current != KEYMAP:
        xbmcvfs.mkdirs(KEYMAP_DIR)
        fh = xbmcvfs.File(KEYMAP_PATH, 'w')
        try:
            fh.write(KEYMAP)
        finally:
            fh.close()
        changed = True
    elif not wanted and current is not None:
        xbmcvfs.delete(KEYMAP_PATH)
        changed = True
    if changed:
        xbmc.executebuiltin('Action(reloadkeymaps)')
        _log('keymaps updated (Lucent Player Back: %s)' % ('on' if wanted else 'off'))
    return changed


if __name__ == '__main__':
    handle()
