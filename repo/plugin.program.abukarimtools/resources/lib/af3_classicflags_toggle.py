# -*- coding: utf-8 -*-
"""
af3_classicflags_toggle.py - ABUKARIM TOOLS (4.8.17)

Toggles entry "AF3: Classic OSD Flags". The classic colour media-flag badges
(codec / HDR / audio / channels / source / language) that the Piers AF3 build
draws in the player OSD extras row and the footer codec row used to ship
inside the skin (media/flags/colorful, ~7 MB loose + the same set again in
Textures.xbt). They now live in their own add-on, resource.images.af3.classicflags,
published next to AF3 in the same repository (repository.taiseerKODI22 on
Kodi 22+, repository.taiseer below - origin_fix.AF3_REPO), so the skin zip
stays under GitHub's 100 MB limit.

The skin (50.11.68+) reads the add-on through
  resource://resource.images.af3.classicflags/colorful[_mono]/...
and gates the OSD extras row, the footer codec row and the four matching
Skin Settings entries on System.AddonIsEnabled(resource.images.af3.classicflags).
Without the add-on AF3 simply shows its stock footer (studio logo) and OSD.

  On  (default)  install the add-on from AF3's repository if missing, enable it
  Off            disable the add-on (kept installed, so On is instant again)

State is the patch-toggle id 'af3_classicflags' in the shared disabled set
(patcher._load_disabled), so it rides along with presets and phone setup.
start_boot_ensure() puts the add-on back once per boot when it is missing.
"""
import os
import threading

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

SKIN_ID = 'skin.arctic.fuse.3'
RES_ID = 'resource.images.af3.classicflags'
TOGGLE_ID = 'af3_classicflags'
TITLE = 'ABUKARIM TOOLS'

_ADDONS = xbmcvfs.translatePath('special://home/addons/')
_LOCK = threading.Lock()


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools ClassicFlags] %s' % msg, level)


def _repo_id():
    try:
        from resources.lib import origin_fix
        return origin_fix.AF3_REPO
    except Exception:
        return 'repository.taiseer'


def _is_local(addon_id):
    return os.path.isfile(os.path.join(_ADDONS, addon_id, 'addon.xml'))


def res_ready():
    return bool(xbmc.getCondVisibility('System.AddonIsEnabled(%s)' % RES_ID))


def toggle_on():
    """4.8.77: always on - the add-on is required by AB Tools and the on/off
    moved to "AF3: OSD Flags Style" > Off (which hides AF3's badge rows via
    Skin.String(abk.flagstyle) instead of disabling this add-on). An old Off
    in the shared disabled set is migrated by af3_flagstyle._migrate()."""
    return True


def _save_toggle(on):
    from resources.lib import patcher
    disabled = set(patcher._load_disabled())
    if on:
        disabled.discard(TOGGLE_ID)
    else:
        disabled.add(TOGGLE_ID)
    patcher._save_disabled(disabled)


def _set_enabled(enabled):
    try:
        import json
        out = xbmc.executeJSONRPC(json.dumps({
            'jsonrpc': '2.0', 'id': 1, 'method': 'Addons.SetAddonEnabled',
            'params': {'addonid': RES_ID, 'enabled': bool(enabled)}}))
        return '"error"' not in out
    except Exception as e:
        _log('SetAddonEnabled(%s) failed: %s' % (enabled, e), xbmc.LOGWARNING)
        return False


def ensure():
    """Installed + enabled -> True. Otherwise install it from AF3's own
    repository (the repo add-on itself first if missing), enable it and pin
    its update origin there. Silent: no dialogs. Never raises."""
    if res_ready():
        return True
    if not _LOCK.acquire(False):
        _log('install already running')
        return False
    repo = _repo_id()
    try:
        from resources.lib import addon_portal as ap
        if _is_local(RES_ID):
            _log('%s present but disabled - enabling' % RES_ID)
            return ap._enable(RES_ID)

        try:
            from resources.lib import origin_fix
            origin_fix.ensure_repo_installed(repo)
        except Exception as e:
            _log('repo check failed: %s' % e, xbmc.LOGWARNING)

        ok = False
        if _is_local(repo):
            zip_url, ver = ap._resolve_zip_in_repo(repo, RES_ID)
            if zip_url:
                _log('%s %s <- %s' % (RES_ID, ver, zip_url))
                ok = ap._install_zip(zip_url, RES_ID)
        if not ok:
            # not resolvable from the repo listing: let Kodi resolve it itself
            # (its "Install?" prompt is auto-answered by the portal watchdog).
            _log('%s: falling back to InstallAddon' % RES_ID, xbmc.LOGWARNING)
            ok = ap._kodi_install(RES_ID)
        if not ok:
            _log('%s could not be installed' % RES_ID, xbmc.LOGWARNING)
            return False
        enabled = ap._enable(RES_ID)
        ap._force_origin(RES_ID, repo)
        _log('%s installed from %s (enabled=%s)' % (RES_ID, repo, enabled))
        return enabled
    except Exception as e:
        _log('install failed: %s' % e, xbmc.LOGWARNING)
        return False
    finally:
        _LOCK.release()


def _reload_af3():
    """The skin's include conditions read the add-on state at load time."""
    if xbmc.getSkinDir() != SKIN_ID:
        return
    xbmc.sleep(300)
    from resources.lib.settings_engine import safe_reload_skin   # 4.8.72: never under the page
    safe_reload_skin()


def run():
    if not xbmc.getCondVisibility('System.HasAddon(%s)' % SKIN_ID):
        xbmcgui.Dialog().ok(TITLE, T(30440))          # AF3 is not installed
        return
    if toggle_on() and res_ready():
        _save_toggle(False)
        _set_enabled(False)
        _log('classic OSD flags: OFF')
        xbmcgui.Dialog().notification(TITLE, T(32129), xbmcgui.NOTIFICATION_INFO, 3500)
        _reload_af3()
        xbmc.executebuiltin('Container.Refresh')
        return
    _save_toggle(True)
    xbmcgui.Dialog().notification(TITLE, T(32130), xbmcgui.NOTIFICATION_INFO, 6000)
    if not ensure():
        _log('classic OSD flags: install failed', xbmc.LOGWARNING)
        xbmcgui.Dialog().ok(TITLE, T(32131))
        xbmc.executebuiltin('Container.Refresh')
        return
    _log('classic OSD flags: ON')
    xbmcgui.Dialog().notification(TITLE, T(32128), xbmcgui.NOTIFICATION_INFO, 3000)
    _reload_af3()
    xbmc.executebuiltin('Container.Refresh')


def start_boot_ensure(monitor, delay=100):
    """Once per boot, in the background: put the add-on back when the toggle
    is on and it is missing (fresh box, AF3 reinstalled, add-on removed), or
    disable it when the toggle is off. Waits out first-run setup and playback.
    Reloads AF3 afterwards only when it is the active skin and safe to do so."""
    if not xbmc.getCondVisibility('System.HasAddon(%s)' % SKIN_ID):
        return
    if toggle_on() == res_ready():
        return

    def _run():
        if monitor.waitForAbort(delay):
            return
        try:
            from resources.lib import patcher
            lock = patcher._FIRST_RUN_LOCK_FILE
        except Exception:
            patcher, lock = None, ''
        for _ in range(60):                         # up to ~30 min
            busy = (lock and os.path.exists(lock)) or \
                xbmc.getCondVisibility('Player.HasMedia')
            if not busy:
                break
            if monitor.waitForAbort(30):
                return
        if toggle_on():
            if res_ready():
                return
            _log('boot: %s missing - installing from %s' % (RES_ID, _repo_id()))
            changed = ensure()
        else:
            if not res_ready():
                return
            _log('boot: toggle is off - disabling %s' % RES_ID)
            changed = _set_enabled(False)
        if changed and patcher and xbmc.getSkinDir() == SKIN_ID:
            patcher._mark_skin_reload()
            patcher.reload_skin_if_pending()

    t = threading.Thread(target=_run, name='abk-classicflags-ensure')
    t.daemon = True
    t.start()
