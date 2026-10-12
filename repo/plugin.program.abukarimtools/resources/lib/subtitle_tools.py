# -*- coding: utf-8 -*-
"""
AF3 Subtitle Buttons (3.2.67) - the runtime half of the 'af3_subtools' toggle.

The patcher adds two buttons to the Arctic Fuse 3 player OSD, right after the
Subtitles button:
  * DexSubtitles AutoSync - runs abk_osd_sync.py inside
    service.subtitles.dexworld (the add-on's own sync flow -> autosync.py).
  * Subtitle Cycler - RunScript(script.subtitle.cycler) when it is installed
    and enabled; otherwise RunPlugin(...?mode=subtitle_cycler), which lands
    in osd_cycler() below: install it from repository.taiseer (Program
    add-ons), enable it, then run it - no prompts.

ensure_cycler() is also started once per boot from the service (thread, after
a delay) so the add-on is normally there before the button is ever pressed.
"""

import os
import threading

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

CYCLER_ID = 'script.subtitle.cycler'
REPO_ID = 'repository.taiseer'
TOGGLE_ID = 'af3_subtools'

_ADDONS = xbmcvfs.translatePath('special://home/addons/')
_LOCK = threading.Lock()


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools SubtitleTools] %s' % msg, level)


def _notify(msg, ms=3000, warn=False):
    try:
        xbmcgui.Dialog().notification(
            'Subtitle Cycler', msg,
            xbmcgui.NOTIFICATION_WARNING if warn else xbmcgui.NOTIFICATION_INFO, ms)
    except Exception:
        pass


def _is_local(addon_id):
    return os.path.isfile(os.path.join(_ADDONS, addon_id, 'addon.xml'))


def cycler_ready():
    return bool(xbmc.getCondVisibility('System.AddonIsEnabled(%s)' % CYCLER_ID))


def toggle_on():
    """The OSD buttons belong to the 'af3_subtools' patch toggle; when the
    user switched it off, the boot install must not run either."""
    try:
        from resources.lib import patcher
        return TOGGLE_ID not in patcher._load_disabled()
    except Exception:
        return True


def ensure_cycler():
    """Installed + enabled -> True. Otherwise install it from the ABUKARIM
    repository (repo itself installed first if missing), enable it and pin
    its update origin. Silent: no dialogs. Never raises."""
    if cycler_ready():
        return True
    if not _LOCK.acquire(False):
        _log('install already running')
        return False
    try:
        from resources.lib import addon_portal as ap
        if _is_local(CYCLER_ID):
            _log('%s present but disabled - enabling' % CYCLER_ID)
            return ap._enable(CYCLER_ID)

        # 1) repository.taiseer (carries the add-on in Program add-ons)
        if not _is_local(REPO_ID):
            url = ap._resolve_repo_zip(REPO_ID)
            if url and ap._install_zip(url):
                xbmc.executebuiltin('UpdateLocalAddons')
                xbmc.sleep(2500)
                ap._enable(REPO_ID)
                ap._force_origin(REPO_ID, REPO_ID)
                _log('repo installed: %s' % REPO_ID)
            else:
                _log('repo install failed: %s' % REPO_ID, xbmc.LOGWARNING)

        # 2) the add-on zip, pinned to that repository
        ok = False
        if _is_local(REPO_ID):
            zip_url, ver = ap._resolve_zip_in_repo(REPO_ID, CYCLER_ID)
            if zip_url:
                _log('%s %s <- %s' % (CYCLER_ID, ver, zip_url))
                ok = ap._install_zip(zip_url)
        if ok:
            xbmc.executebuiltin('UpdateLocalAddons')
            xbmc.sleep(2500)
        else:
            # repo unreachable / not resolvable: let Kodi resolve it itself
            # (its "Install?" prompt is auto-answered).
            _log('%s: falling back to InstallAddon' % CYCLER_ID, xbmc.LOGWARNING)
            ok = ap._kodi_install(CYCLER_ID)
        if not ok:
            _log('%s could not be installed' % CYCLER_ID, xbmc.LOGWARNING)
            return False

        enabled = ap._enable(CYCLER_ID)
        ap._force_origin(CYCLER_ID, REPO_ID)
        _log('%s installed (enabled=%s)' % (CYCLER_ID, enabled))
        return enabled
    except Exception as e:
        _log('install failed: %s' % e, xbmc.LOGWARNING)
        return False
    finally:
        _LOCK.release()


def osd_cycler():
    """OSD button when the cycler is missing/disabled: install, then run."""
    if not cycler_ready():
        _notify(T(30701), 6000)                     # installing...
        if not ensure_cycler():
            _notify(T(30702), 5000, warn=True)      # install failed
            return
        _notify(T(30703), 2500)                     # installed
        xbmc.sleep(500)
    xbmc.executebuiltin('RunScript(%s)' % CYCLER_ID)


def start_boot_ensure(monitor, delay=90):
    """Install the cycler once per boot in the background if it is missing.
    Waits out first-run setup and playback; quiet on success."""
    if cycler_ready():
        return

    def _run():
        if monitor.waitForAbort(delay):
            return
        try:
            from resources.lib import patcher
            lock = patcher._FIRST_RUN_LOCK_FILE
        except Exception:
            lock = ''
        for _ in range(60):                         # up to ~30 min
            busy = (lock and os.path.exists(lock)) or \
                xbmc.getCondVisibility('Player.HasMedia')
            if not busy:
                break
            if monitor.waitForAbort(30):
                return
        if cycler_ready() or not toggle_on():
            return
        _log('boot: %s missing - installing from %s' % (CYCLER_ID, REPO_ID))
        ensure_cycler()

    t = threading.Thread(target=_run, name='abk-subcycler-ensure')
    t.daemon = True
    t.start()
