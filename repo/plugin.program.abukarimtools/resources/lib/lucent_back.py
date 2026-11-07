# -*- coding: utf-8 -*-
"""
lucent_back.py - ABUKARIM TOOLS (4.7.32)

Back in the fullscreen player while "AF3: Lucent Player" is on. Idea from
Lucent 1.34.3 (scripts/fsback.py by djdirty60, github.com/djdirty60/Lucent,
GPL-2.0-or-later), changed for Piers: Lucent maps Back to Stop, AF3 / Kodi
leave fullscreen with the video playing on. Only the skipping part is taken:

  fast forward / rewind          -> back to normal speed, stay in the video
  seek bar up / a seek just done -> close the seek bar, stay in the video
  anything else                  -> Kodi's own Back (unchanged)

Called from the keymap special://profile/keymaps/abk-lucentplayer-back.xml
(FullscreenVideo only; the OSD, pause card dialogs and menus are untouched).
sync_keymap() writes or removes that file and is called by the toggle and at
service start.

    RunScript(special://home/addons/plugin.program.abukarimtools/resources/lib/lucent_back.py)
"""
import xbmc
import xbmcvfs

SKIN_ID = 'skin.arctic.fuse.3'
SETTING = 'abk.lucentplayer'
KEYMAP_DIR = 'special://profile/keymaps/'
KEYMAP_PATH = KEYMAP_DIR + 'abk-lucentplayer-back.xml'
_RUN = ('RunScript(special://home/addons/plugin.program.abukarimtools/'
        'resources/lib/lucent_back.py)')
KEYMAP = """<keymap>
    <!-- ABUKARIM TOOLS - AF3: Lucent Player. Back while skipping ends the skipping;
         otherwise Kodi's normal Back. Removed when Lucent Player is turned off. -->
    <FullscreenVideo>
        <keyboard>
            <backspace>%(r)s</backspace>
            <browser_back>%(r)s</browser_back>
        </keyboard>
        <remote>
            <back>%(r)s</back>
        </remote>
    </FullscreenVideo>
</keymap>
""" % {'r': _RUN}


def _log(msg):
    xbmc.log('[AbukarimTools LucentBack] %s' % msg, xbmc.LOGINFO)


def _cond(c):
    return bool(xbmc.getCondVisibility(c))


def _active():
    return xbmc.getSkinDir() == SKIN_ID and _cond('Skin.HasSetting(%s)' % SETTING)


def handle():
    if _active():
        if _cond('Player.Forwarding | Player.Rewinding'):
            xbmc.executebuiltin('PlayerControl(Play)')       # back to normal speed
            return
        if _cond('Player.Seeking | Player.HasPerformedSeek(3)'):
            xbmc.executebuiltin('Dialog.Close(seekbar)')
            return
    xbmc.executebuiltin('Action(Back)')                     # Kodi's own Back


def _read():
    if not xbmcvfs.exists(KEYMAP_PATH):
        return None
    f = xbmcvfs.File(KEYMAP_PATH)
    try:
        return f.read()
    finally:
        f.close()


def clear_lucent_keymaps():
    """4.7.33: the Lucent skin writes keymaps into the profile (lucent-back-stop.xml:
    Back in fullscreen video, lucent-ok-page.xml: OK in the video lists) that run
    special://skin/scripts/... - with another skin active those scripts do not
    exist, so Back / OK did nothing (they also load after ours and override it).
    Remove them while Lucent is not the skin; Lucent writes them again itself
    (scripts/keymap.py) when its Home opens. Returns True when a file went."""
    if xbmc.getSkinDir() == 'skin.lucent':
        return False
    gone = []
    try:
        _dirs, files = xbmcvfs.listdir(KEYMAP_DIR)
    except Exception:
        return False
    for name in files:
        if not (name.startswith('lucent-') and name.endswith('.xml')):
            continue
        path = KEYMAP_DIR + name
        try:
            f = xbmcvfs.File(path)
            try:
                body = f.read()
            finally:
                f.close()
        except Exception:
            continue
        if 'special://skin/scripts/' in body and xbmcvfs.delete(path):
            gone.append(name)
    if gone:
        _log('removed Lucent skin keymaps (not the active skin): %s' % ', '.join(gone))
    return bool(gone)


def sync_keymap(wanted=None):
    """Keymap present while Lucent Player is on (AF3 active), gone otherwise.
    Returns True when the file changed (keymaps are then reloaded)."""
    if wanted is None:
        wanted = _active()
    have = _read()
    changed = clear_lucent_keymaps()
    if wanted and have != KEYMAP:
        xbmcvfs.mkdirs(KEYMAP_DIR)
        f = xbmcvfs.File(KEYMAP_PATH, 'w')
        try:
            f.write(KEYMAP)
        finally:
            f.close()
        changed = True
    elif not wanted and have is not None:
        xbmcvfs.delete(KEYMAP_PATH)
        changed = True
    if changed:
        xbmc.executebuiltin('Action(reloadkeymaps)')
        _log('keymaps updated (Lucent Player Back: %s)' % ('on' if wanted else 'off'))
    return changed


if __name__ == '__main__':
    handle()
