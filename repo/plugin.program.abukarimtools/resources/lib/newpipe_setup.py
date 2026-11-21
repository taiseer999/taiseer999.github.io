# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""4.8.78: NewPipe (AF3 Auto Trailers) - repository.twilight0 FIRST, then NewPipe.

plugin.video.newpipe and the libraries it needs (tulip, scrapetube, unicache,
urldispatcher, resolveurl.pluginsgr) are published on Twilight0's repository,
not on repository.taiseer. Kodi resolves every <import> of addon.xml before it
installs AB Tools, so NewPipe can no longer be a hard dependency: a box without
repository.twilight0 would refuse to install AB Tools at all. Order here:

  1. repository.twilight0  - origin_fix.ensure_repo_installed (its own zip
                             from .../repository.twilight0/master/repo_dir/),
                             enabled, then UpdateAddonRepos
  2. wait for its listing   - until Kodi knows plugin.video.newpipe
  3. plugin.video.newpipe   - Kodi's own InstallAddon (resolves the libraries
                             from twilight0's dirs; the "Install?" prompt is
                             answered by the portal watchdog), enabled, origin
                             pinned to repository.twilight0

Silent, never raises. Boot: background thread, delayed, waits out first-run
setup and playback (same pattern as af3_classicflags_toggle).
"""
import os
import threading

import xbmc

NEWPIPE_ID = 'plugin.video.newpipe'
REPO_ID = 'repository.twilight0'

_LOCK = threading.Lock()
_TRIED = []                     # one full attempt per Kodi session


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools NewPipe] %s' % msg, level)


def _has(addon_id):
    return bool(xbmc.getCondVisibility('System.HasAddon(%s)' % addon_id))


def ready():
    return bool(xbmc.getCondVisibility(
        'System.HasAddon(%s) + System.AddonIsEnabled(%s)' % (NEWPIPE_ID, NEWPIPE_ID)))


def _known_to_kodi(addon_id):
    """True once repository.twilight0's cached listing (Addons DB repo tables)
    carries addon_id - i.e. InstallAddon can find it. Read-only, never raises."""
    from resources.lib import origin_fix
    conn = None
    try:
        db = origin_fix._find_addons_db()
        if not db:
            return False
        conn = origin_fix._connect(db)
        return any(rid == REPO_ID for rid, _v in
                   origin_fix._repo_candidates(conn.cursor(), addon_id))
    except Exception:
        return False
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def _repo_ready(monitor):
    """Step 1: repository.twilight0 present + enabled, listing refreshed."""
    from resources.lib import addon_portal as ap
    from resources.lib import origin_fix
    fresh = not origin_fix._local_dir_for(REPO_ID)
    if fresh:
        _log('%s missing - installing it first' % REPO_ID)
        if not origin_fix.ensure_repo_installed(REPO_ID):
            _log('%s could not be installed' % REPO_ID, xbmc.LOGWARNING)
            return False
    if not ap._enable(REPO_ID):
        _log('%s could not be enabled' % REPO_ID, xbmc.LOGWARNING)
        return False
    if fresh or not _known_to_kodi(NEWPIPE_ID):
        xbmc.executebuiltin('UpdateAddonRepos')
    # Step 2: Kodi must have read the new listing before InstallAddon can
    # find NewPipe (up to 90 s, one more refresh half way)
    for i in range(90):
        if _known_to_kodi(NEWPIPE_ID):
            _log('%s ready, %s listed' % (REPO_ID, NEWPIPE_ID))
            return True
        if i == 45:
            xbmc.executebuiltin('UpdateAddonRepos')
        if monitor.waitForAbort(1):
            return False
    # the DB check can lag (or the schema differ): let InstallAddon decide
    _log('%s listing not confirmed for %s - trying InstallAddon anyway'
         % (REPO_ID, NEWPIPE_ID), xbmc.LOGWARNING)
    return True


def ensure(monitor=None):
    """NewPipe installed + enabled -> True. Otherwise repository.twilight0
    first, then NewPipe from it. Silent, never raises."""
    if ready():
        return True
    if not _LOCK.acquire(False):
        _log('install already running')
        return False
    monitor = monitor or xbmc.Monitor()
    try:
        from resources.lib import addon_portal as ap
        if _has(NEWPIPE_ID):
            _log('%s present but disabled - enabling' % NEWPIPE_ID)
            return ap._enable(NEWPIPE_ID)
        if not _repo_ready(monitor):
            return False
        ok = ap._kodi_install(NEWPIPE_ID, timeout_ms=180000)
        if not ok:
            _log('%s could not be installed' % NEWPIPE_ID, xbmc.LOGWARNING)
            return False
        enabled = ap._enable(NEWPIPE_ID)
        ap._force_origin(NEWPIPE_ID, REPO_ID)
        _log('%s installed from %s (enabled=%s)' % (NEWPIPE_ID, REPO_ID, enabled))
        return enabled
    except Exception as e:
        _log('install failed: %s' % e, xbmc.LOGWARNING)
        return False
    finally:
        _LOCK.release()


def start_boot_ensure(monitor, delay=120):
    """Once per boot, in the background, only when NewPipe is missing or off."""
    if ready() or _TRIED:
        return
    _TRIED.append(1)

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
        if not ready():
            _log('boot: %s missing - %s first, then NewPipe' % (NEWPIPE_ID, REPO_ID))
            ensure(monitor)

    t = threading.Thread(target=_run, name='abk-newpipe-ensure')
    t.daemon = True
    t.start()
