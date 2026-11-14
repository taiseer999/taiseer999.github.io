# -*- coding: utf-8 -*-
"""
tmdbh_sync.py - TMDb Helper sync provider: Trakt, set up without questions (4.7.4).

TMDb Helper 6.20 moved Trakt / MDbList into separate sync modules. The first
AF3 widget that needs one (trakt_inprogress, trakt_nextepisodes...) makes
TMDb Helper ask on screen (resources/tmdbhelper/lib/script/sync/provider_setup.py):

    "<list> needs a sync provider - set one up?"   Yes / Never / Later
    -> select: None / Trakt / MDbList / Install Trakt / Install MDbList
    -> InstallAddon(script.module.tmdbhelper.sync.xxx) -> Kodi's install yes/no

During setup that lands on top of the wizard (kodi.log 2026-11-01 17:09:58 -
17:10:19). Here instead:

  * hold_prompts(): Home property TMDbHelper.SyncProviderSetup.Later - TMDb
    Helper's own "Later" for widget prompts, so nothing pops up meanwhile;
  * ensure(): install script.module.tmdbhelper.sync.trakt and .sync.mdblist
    when missing (Kodi's install yes/no answered Yes, Add-on Portal
    installer), then save Trakt as the provider for watched, watchlist,
    collection, scrobbling and stats. A capability that already has a value
    (a restored choice, MDbList, or "never") is left as it is.

Runs as a setup step after the add-ons and once per boot in the background.
"""

import json

import xbmc
import xbmcaddon
import xbmcgui

TMDBH = 'plugin.video.themoviedb.helper'
MODULES = ('script.module.tmdbhelper.sync.trakt', 'script.module.tmdbhelper.sync.mdblist')
PROVIDER = 'trakt'
CAPABILITIES = ('watched', 'watchlist', 'collection', 'scrobbling', 'stats')
LATER_PROP = 'TMDbHelper.SyncProviderSetup.Later'


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools TMDbHSync] %s' % msg, level)


def hold_prompts():
    xbmcgui.Window(10000).setProperty(LATER_PROP, 'True')


def release_prompts():
    xbmcgui.Window(10000).clearProperty(LATER_PROP)


def _tmdbh():
    try:
        return xbmcaddon.Addon(TMDBH)
    except Exception:
        return None


def unconfigured():
    """Capabilities with no provider at all (what makes TMDb Helper ask)."""
    a = _tmdbh()
    if a is None:
        return []
    return [c for c in CAPABILITIES if not a.getSetting('sync_provider_%s' % c)]


def _install_modules():
    from resources.lib import addon_portal as ap
    missing = [m for m in MODULES if not ap._has_addon(m)]
    for m in missing:
        ok = ap._kodi_install(m)            # Kodi's yes/no answered by _YesWatchdog
        if ok:
            ap._enable(m)
        _log('%s %s' % (m, 'installed' if ok else 'NOT installed'),
             xbmc.LOGINFO if ok else xbmc.LOGWARNING)
    return [m for m in MODULES if not ap._has_addon(m)]


def ensure(install=True):
    """Returns (status, detail). status: ok | skipped | failed."""
    a = _tmdbh()
    if a is None:
        return 'skipped', 'TMDb Helper not installed'
    still_missing = _install_modules() if install else []
    if MODULES[0] in still_missing:
        return 'failed', 'could not install %s' % MODULES[0]
    todo = unconfigured()
    for cap in todo:
        value = json.dumps([PROVIDER]) if cap == 'scrobbling' else PROVIDER
        a.setSetting('sync_provider_%s' % cap, value)
    if todo:
        _log('sync provider set to %s for: %s' % (PROVIDER, ', '.join(todo)))
    detail = ('Trakt for %s' % ', '.join(todo)) if todo else 'already configured'
    if still_missing:
        detail += '; not installed: %s' % ', '.join(still_missing)
    return 'ok', detail


def boot(monitor):
    """Background boot check: nothing to do on a configured box."""
    try:
        if _tmdbh() is None or not unconfigured():
            return
        hold_prompts()                      # no widget prompt while we fix it
        if monitor.waitForAbort(20):        # let Kodi and the repos settle
            return
        status, detail = ensure()
        _log('boot: %s (%s)' % (status, detail))
        if status != 'ok':
            release_prompts()               # let TMDb Helper ask the normal way
    except Exception as e:
        _log('boot check failed: %s' % e, xbmc.LOGWARNING)
        release_prompts()
