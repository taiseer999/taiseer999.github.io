# -*- coding: utf-8 -*-
import os
import sys
import xbmc

addon_path = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.join(addon_path, 'resources', 'lib')
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

from resources.lib.companion import CompanionPlayer, ProgressLoop
from resources.lib import trakt
from resources.lib import tmdbh_player
from resources.lib import favorites_store
import xbmcgui


def _purge_http_cache():
    """Delete cached HTTP responses older than twice their max TTL. Keeps the
    cache dir bounded on long-running installs."""
    import os as _os, time as _t
    try:
        from resources.lib.dexhub.client import HTTP_CACHE_DIR, catalog_ttl, meta_ttl
        max_ttl = max(catalog_ttl(), meta_ttl(), 3600) * 2
        if not _os.path.isdir(HTTP_CACHE_DIR):
            return
        now = _t.time()
        removed = 0
        for name in _os.listdir(HTTP_CACHE_DIR):
            path = _os.path.join(HTTP_CACHE_DIR, name)
            try:
                if _os.path.isfile(path) and (now - _os.path.getmtime(path)) > max_ttl:
                    _os.remove(path)
                    removed += 1
            except Exception:
                continue
        if removed:
            xbmc.log('[DexHub] purged %d stale http-cache files' % removed, xbmc.LOGINFO)
    except Exception as exc:
        xbmc.log('[DexHub] http-cache purge failed: %s' % exc, xbmc.LOGWARNING)


def _win():
    try:
        return xbmcgui.Window(10000)
    except Exception:
        return None



def _setting(key, default=''):
    try:
        import xbmcaddon
        return xbmcaddon.Addon().getSetting(key) or default
    except Exception:
        return default



def _primary_player_mode():
    raw = str(_setting('catalog_click_mode', 'TMDb Helper') or 'TMDb Helper').strip().lower()
    compact = raw.replace(' ', '').replace('_', '').replace('-', '')
    if compact in ('tmdbhelper', 'helper', '1') or 'tmdb' in compact:
        return 'tmdbhelper'
    if compact in ('ask', 'askeverytime', '2') or raw == 'اسأل كل مرة':
        return 'ask'
    return 'dexhub'



def _publish_core_props(last_sync=''):
    win = _win()
    if not win:
        return
    tmdbh_available = '1' if tmdbh_player.has_tmdbhelper() else '0'
    tmdbh_installed = '1' if tmdbh_player.player_installed() else '0'
    tmdbh_primary = '1' if _primary_player_mode() == 'tmdbhelper' else '0'
    trakt_enabled = '1' if trakt.enabled() else '0'
    trakt_connected = '1' if trakt.authorized() else '0'
    payload = {
        'dexhub.core.ready': '1',
        'dexhub.core.tmdbh.available': tmdbh_available,
        'dexhub.core.tmdbh.player_installed': tmdbh_installed,
        'dexhub.core.tmdbh.primary': tmdbh_primary,
        'dexhub.core.trakt.enabled': trakt_enabled,
        'dexhub.core.trakt.connected': trakt_connected,
        'dexhub.core.trakt.last_sync': str(last_sync or ''),
        'dexhub.core.formatter.enabled': '1' if ((_setting('enable_source_formatter', 'true') or 'true').lower() == 'true') else '0',
    }
    for k, v in payload.items():
        try:
            win.setProperty(k, v)
        except Exception:
            pass



def _invalidate_ui_caches():
    win = _win()
    if not win:
        return
    for key in ('dexhub.nextup_cache', 'dexhub.nextup_cache_ts', 'dexhub.fav_mirror_done'):
        try:
            win.clearProperty(key)
        except Exception:
            pass



def _sync_trakt_state(reason='manual'):
    if not trakt.enabled():
        _publish_core_props('')
        return False
    try:
        if not trakt.authorized():
            _publish_core_props('')
            return False
    except Exception:
        _publish_core_props('')
        return False

    did_work = False
    try:
        if trakt.sync_enabled():
            trakt.import_progress(limit=100)
            did_work = True
    except Exception as exc:
        xbmc.log('[DexHub] trakt progress sync failed (%s): %s' % (reason, exc), xbmc.LOGWARNING)

    try:
        if ((_setting('trakt_sync_watchlist', 'true') or 'true').lower() == 'true'):
            rows = trakt.fetch_watchlist(limit=300) or []
            favorites_store.replace_trakt_mirror(rows)
            did_work = True
    except Exception as exc:
        xbmc.log('[DexHub] trakt watchlist sync failed (%s): %s' % (reason, exc), xbmc.LOGWARNING)

    if did_work:
        try:
            trakt.invalidate_cache('next_up_v1')
            trakt.invalidate_cache('/sync/playback/')
        except Exception:
            pass
        _invalidate_ui_caches()
        _publish_core_props(str(int(__import__('time').time())))
    else:
        _publish_core_props('')
    return did_work



def _sync_interval_ms():
    try:
        minutes = int(_setting('trakt_service_sync_interval', '10') or '10')
    except Exception:
        minutes = 10
    minutes = max(2, min(60, minutes))
    return minutes * 60 * 1000



def _background_sync_loop(monitor):
    xbmc.sleep(4000)
    while not monitor.abortRequested():
        try:
            tmdbh_player.ensure_installed_once()
        except Exception as exc:
            xbmc.log('[DexHub] tmdbh keepalive failed: %s' % exc, xbmc.LOGWARNING)
        try:
            _sync_trakt_state(reason='service')
        except Exception as exc:
            xbmc.log('[DexHub] trakt background sync failed: %s' % exc, xbmc.LOGWARNING)
        _publish_core_props(_win().getProperty('dexhub.core.trakt.last_sync') if _win() else '')
        if monitor.waitForAbort(_sync_interval_ms() / 1000.0):
            break


if __name__ == '__main__':
    xbmc.log('[DexHub] companion service started', xbmc.LOGINFO)

    _purge_http_cache()

    try:
        tmdbh_player.ensure_installed_once()
    except Exception as exc:
        xbmc.log('[DexHub] tmdbh player auto-install failed: %s' % exc, xbmc.LOGWARNING)

    _publish_core_props('')

    player = CompanionPlayer()
    monitor = xbmc.Monitor()

    def _startup_sync():
        try:
            xbmc.sleep(5000)
            _sync_trakt_state(reason='startup')
        except Exception as exc:
            xbmc.log('[DexHub] trakt startup sync failed: %s' % exc, xbmc.LOGWARNING)

    try:
        import threading as _thr
        _thr.Thread(target=_startup_sync, name='DexHubCoreBoot', daemon=True).start()
        _thr.Thread(target=_background_sync_loop, args=(monitor,), name='DexHubCoreLoop', daemon=True).start()
    except Exception as exc:
        xbmc.log('[DexHub] could not spawn core sync thread: %s' % exc, xbmc.LOGWARNING)
    ProgressLoop(player).run()
