# -*- coding: utf-8 -*-
import json
import urllib.error
import urllib.parse
import urllib.request
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui

from .session_store import clear_session, load_session, save_session
from . import trakt, playback_store

ADDON = xbmcaddon.Addon()


def _monitor_path():
    try:
        import xbmcvfs
        return xbmcvfs.translatePath('special://profile/addon_data/plugin.video.dexhub/playback_monitor.log')
    except Exception:
        try:
            return xbmc.translatePath('special://profile/addon_data/plugin.video.dexhub/playback_monitor.log')
        except Exception:
            return ''


def _monitor(event, level=xbmc.LOGINFO, **payload):
    record = {'event': str(event or ''), 'ts': int(time.time())}
    for key, value in dict(payload or {}).items():
        if value in (None, '', [], {}, ()): 
            continue
        try:
            record[key] = value if isinstance(value, (dict, list)) else str(value)
        except Exception:
            continue
    try:
        xbmc.log('[DexHubMonitor] %s' % json.dumps(record, ensure_ascii=False, sort_keys=True), level)
    except Exception:
        pass
    try:
        path = _monitor_path()
        if path:
            import os
            folder = os.path.dirname(path)
            if folder and not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)
            if os.path.exists(path) and os.path.getsize(path) > 262144:
                with open(path, 'rb') as fh:
                    data = fh.read()[-131072:]
                with open(path, 'wb') as fh:
                    fh.write(data)
            with open(path, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
    except Exception:
        pass


def _timeout():
    try:
        return max(3, int(ADDON.getSetting('timeout') or '20'))
    except Exception:
        return 20


def _interval_seconds():
    try:
        return max(2, int(ADDON.getSetting('companion_interval') or '5'))
    except Exception:
        return 5


def companion_enabled():
    try:
        return (ADDON.getSetting('enable_companion_sync') or 'true').lower() == 'true'
    except Exception:
        return True


def _json_post(url, payload, headers=None):
    data = json.dumps(payload or {}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=dict(headers or {}, **{'Content-Type': 'application/json', 'Accept': 'application/json'}), method='POST')
    with urllib.request.urlopen(req, timeout=_timeout()) as resp:
        return resp.read().decode('utf-8', 'ignore')


def _json_get(url, headers=None):
    req = urllib.request.Request(url, headers=dict(headers or {}, **{'Accept': 'application/json'}), method='GET')
    with urllib.request.urlopen(req, timeout=_timeout()) as resp:
        return json.loads(resp.read().decode('utf-8', 'ignore'))


def _absolute_url(base, maybe_url):
    value = str(maybe_url or '').strip()
    if not value:
        return ''
    if value.startswith('http://') or value.startswith('https://'):
        return value
    if value.startswith('/') and base:
        parsed = urllib.parse.urlparse(base)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}{value}"
    return value


class BaseReporter(object):
    def started(self, ctx, position_ms=0):
        raise NotImplementedError
    def progress(self, ctx, position_ms):
        raise NotImplementedError
    def paused(self, ctx, position_ms):
        raise NotImplementedError
    def stopped(self, ctx, position_ms):
        raise NotImplementedError
    def ended(self, ctx, position_ms=0):
        raise NotImplementedError


class UrlCompanionReporter(BaseReporter):
    def _headers(self, ctx):
        headers = {}
        client_id = ctx.get('clientIdentifier') or ctx.get('client_id')
        if client_id:
            headers['X-Plex-Client-Identifier'] = client_id
        product = ctx.get('product') or 'Dex Hub'
        headers['X-Plex-Product'] = product
        headers['X-Plex-Platform'] = 'Kodi'
        headers['X-Plex-Device'] = 'Kodi'
        headers['X-Plex-Device-Name'] = ctx.get('deviceName') or 'Kodi'
        if ctx.get('token'):
            headers['X-Plex-Token'] = ctx.get('token')
        return headers

    def _bootstrap(self, ctx):
        if ctx.get('_bootstrapped'):
            return
        url = ctx.get('bootstrapUrl')
        if not url and ctx.get('companionUrl'):
            url = str(ctx['companionUrl']).replace('/companion/timeline/', '/companion/bootstrap/')
        if not url:
            ctx['_bootstrapped'] = True
            return
        try:
            data = _json_get(url, headers=self._headers(ctx))
            if isinstance(data, dict):
                for src, dst in [('timelineUrl','companionUrl'),('scrobbleUrl','companionScrobbleUrl'),('unscrobbleUrl','companionUnscrobbleUrl'),('sessionIdentifier','sessionIdentifier'),('playbackSessionId','playbackSessionId'),('clientIdentifier','clientIdentifier')]:
                    val = data.get(src)
                    val = _absolute_url(url, val)
                    if val:
                        ctx[dst] = val
                interval = data.get('intervalMs')
                if interval and not ctx.get('intervalSeconds'):
                    try:
                        ctx['intervalSeconds'] = max(2, int(float(interval) / 1000.0))
                    except Exception:
                        pass
                if data.get('duration') and not ctx.get('duration_ms'):
                    try:
                        ctx['duration_ms'] = int(data.get('duration'))
                    except Exception:
                        pass
        except Exception as exc:
            xbmc.log('[DexHub] companion bootstrap error: %s' % exc, xbmc.LOGWARNING)
        ctx['_bootstrapped'] = True

    def _payload(self, ctx, position_ms, state, mark_watched=None):
        payload = {
            'state': state,
            'time': int(position_ms or 0),
            'duration': int(ctx.get('duration_ms') or 0),
            'playbackTime': int(position_ms or 0),
            'sessionIdentifier': ctx.get('sessionIdentifier') or '',
            'playbackSessionId': ctx.get('playbackSessionId') or ctx.get('sessionIdentifier') or '',
            'deviceName': ctx.get('deviceName') or 'Kodi',
            'device': 'Kodi',
            'platform': 'Kodi',
            'product': ctx.get('product') or 'Dex Hub',
        }
        if mark_watched is not None:
            payload['markWatched'] = bool(mark_watched)
        return payload

    def _post(self, ctx, key, position_ms, state, mark_watched=None):
        self._bootstrap(ctx)
        url = ctx.get(key)
        if not url:
            return None
        return _json_post(url, self._payload(ctx, position_ms, state, mark_watched), headers=self._headers(ctx))

    def started(self, ctx, position_ms=0):
        return self._post(ctx, 'companionUrl', position_ms, 'playing')

    def progress(self, ctx, position_ms):
        return self._post(ctx, 'companionUrl', position_ms, 'playing')

    def paused(self, ctx, position_ms):
        return self._post(ctx, 'companionUrl', position_ms, 'paused')

    def stopped(self, ctx, position_ms):
        return self._post(ctx, 'companionUrl', position_ms, 'stopped')

    def ended(self, ctx, position_ms=0):
        if ctx.get('companionScrobbleUrl'):
            return self._post(ctx, 'companionScrobbleUrl', position_ms or int(ctx.get('duration_ms') or 0), 'stopped', mark_watched=True)
        return self._post(ctx, 'companionUrl', position_ms or int(ctx.get('duration_ms') or 0), 'stopped', mark_watched=True)


class PlexReporter(BaseReporter):
    def _headers(self, ctx):
        return {
            'X-Plex-Product': ctx.get('product', 'Dex Hub'),
            'X-Plex-Version': ctx.get('product_version', '2.6.0'),
            'X-Plex-Client-Identifier': ctx['client_id'],
            'X-Plex-Provides': 'player',
            'X-Plex-Device-Name': ctx.get('device_name', 'Kodi'),
            'X-Plex-Platform': 'Kodi',
            'X-Plex-Model': 'Kodi',
            'X-Plex-Device': ctx.get('device_name', 'Kodi'),
        }

    def _get(self, ctx, path, params):
        params = dict(params)
        params['X-Plex-Token'] = ctx['token']
        url = ctx['server_url'].rstrip('/') + path + '?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=self._headers(ctx), method='GET')
        with urllib.request.urlopen(req, timeout=_timeout()) as resp:
            return resp.read()

    def _timeline(self, ctx, position_ms, state):
        rating_key = ctx['rating_key']
        duration_ms = int(ctx.get('duration_ms', 0))
        params = {
            'duration': duration_ms,
            'guid': 'com.plexapp.plugins.library',
            'key': f'/library/metadata/{rating_key}',
            'containerKey': f'/library/metadata/{rating_key}',
            'ratingKey': str(rating_key),
            'state': state,
            'time': int(position_ms),
        }
        return self._get(ctx, '/:/timeline', params)

    def _scrobble(self, ctx):
        return self._get(ctx, '/:/scrobble', {'key': str(ctx['rating_key']), 'identifier': 'com.plexapp.plugins.library'})

    def started(self, ctx, position_ms=0):
        return self._timeline(ctx, position_ms, 'playing')
    def progress(self, ctx, position_ms):
        return self._timeline(ctx, position_ms, 'playing')
    def paused(self, ctx, position_ms):
        return self._timeline(ctx, position_ms, 'paused')
    def stopped(self, ctx, position_ms):
        return self._timeline(ctx, position_ms, 'stopped')
    def ended(self, ctx, position_ms=0):
        self._timeline(ctx, position_ms or int(ctx.get('duration_ms', 0)), 'stopped')
        return self._scrobble(ctx)


class EmbyReporter(BaseReporter):
    def _headers(self, ctx):
        return {
            'Content-Type': 'application/json',
            'X-Emby-Token': ctx['token'],
            'X-Emby-Authorization': (
                'MediaBrowser Client="Kodi", Device="Kodi", DeviceId="%s", Version="1.0.0"' % ctx['device_id']
            ),
        }

    def _post(self, ctx, path, payload):
        url = ctx['server_url'].rstrip('/') + path
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=self._headers(ctx), method='POST')
        with urllib.request.urlopen(req, timeout=_timeout()) as resp:
            return resp.read()

    def _payload(self, ctx, position_ms, paused=False):
        return {
            'ItemId': ctx['item_id'],
            'PositionTicks': int(position_ms) * 10000,
            'IsPaused': paused,
            'PlayMethod': 'DirectStream',
            'CanSeek': True,
            'SessionId': ctx.get('session_id', ctx['device_id']),
        }

    def started(self, ctx, position_ms=0):
        return self._post(ctx, '/Sessions/Playing', self._payload(ctx, position_ms, paused=False))
    def progress(self, ctx, position_ms):
        payload = self._payload(ctx, position_ms, paused=False); payload['EventName']='TimeUpdate'; return self._post(ctx, '/Sessions/Playing/Progress', payload)
    def paused(self, ctx, position_ms):
        payload = self._payload(ctx, position_ms, paused=True); payload['EventName']='Pause'; return self._post(ctx, '/Sessions/Playing/Progress', payload)
    def stopped(self, ctx, position_ms):
        payload = self._payload(ctx, position_ms, paused=False); payload['EventName']='Stop'; return self._post(ctx, '/Sessions/Playing/Stopped', payload)
    def ended(self, ctx, position_ms=0):
        payload = self._payload(ctx, position_ms or int(ctx.get('duration_ms', 0)), paused=False); payload['EventName']='Stop'; return self._post(ctx, '/Sessions/Playing/Stopped', payload)




class TraktReporter(BaseReporter):
    def started(self, ctx, position_ms=0):
        return trakt.scrobble('start', ctx, position_ms)

    def progress(self, ctx, position_ms):
        return None

    def paused(self, ctx, position_ms):
        return trakt.scrobble('pause', ctx, position_ms)

    def stopped(self, ctx, position_ms):
        return trakt.scrobble('pause', ctx, position_ms)

    def ended(self, ctx, position_ms=0):
        return trakt.scrobble('stop', ctx, position_ms)


class MultiReporter(BaseReporter):
    def __init__(self, reporters):
        self.reporters = [r for r in (reporters or []) if r]

    def _call(self, method_name, ctx, position_ms=0):
        results = []
        for reporter in self.reporters:
            try:
                results.append(getattr(reporter, method_name)(ctx, position_ms))
            except TypeError:
                results.append(getattr(reporter, method_name)(ctx))
            except Exception as exc:
                xbmc.log('[DexHub] reporter %s error: %s' % (method_name, exc), xbmc.LOGWARNING)
        return results

    def started(self, ctx, position_ms=0):
        return self._call('started', ctx, position_ms)

    def progress(self, ctx, position_ms):
        return self._call('progress', ctx, position_ms)

    def paused(self, ctx, position_ms):
        return self._call('paused', ctx, position_ms)

    def stopped(self, ctx, position_ms):
        return self._call('stopped', ctx, position_ms)

    def ended(self, ctx, position_ms=0):
        return self._call('ended', ctx, position_ms)


def get_reporter(ctx):
    if not ctx:
        return None
    reporters = []
    server_reporter = None
    if ctx.get('companionUrl') or ctx.get('companionScrobbleUrl'):
        server_reporter = UrlCompanionReporter()
    elif ctx.get('server_type') == 'plex' and ctx.get('server_url') and ctx.get('token') and ctx.get('rating_key'):
        server_reporter = PlexReporter()
    elif ctx.get('server_type') == 'emby' and ctx.get('server_url') and ctx.get('token') and ctx.get('item_id'):
        server_reporter = EmbyReporter()
    if server_reporter:
        reporters.append(server_reporter)
    if trakt.enabled() and trakt.scrobble_enabled():
        ids_present = any(ctx.get(k) for k in ('imdb_id', 'tmdb_id', 'tvdb_id'))
        if ids_present:
            reporters.append(TraktReporter())
    if not reporters:
        return None
    if len(reporters) == 1:
        return reporters[0]
    return MultiReporter(reporters)


def should_mark_watched(position_ms, duration_ms, threshold=0.9):
    try:
        return duration_ms > 0 and (float(position_ms) / float(duration_ms)) >= threshold
    except Exception:
        return False


def _safe_int(value, default=0):
    try:
        return int(value or 0)
    except Exception:
        return default


def _safe_float(value, default=0.0):
    try:
        return float(value or 0.0)
    except Exception:
        return default


def _local_percent(position_ms, duration_ms):
    try:
        if duration_ms and duration_ms > 0:
            return max(0.0, min(100.0, (float(position_ms) / float(duration_ms)) * 100.0))
    except Exception:
        pass
    return 0.0


def _save_local_progress(ctx, position_ms=0, duration_ms=0, finished=False):
    if not isinstance(ctx, dict) or not ctx:
        return
    media_type = (ctx.get('media_type') or '').lower()
    canonical_id = ctx.get('canonical_id') or ''
    if not canonical_id:
        return
    is_episode = media_type in ('series', 'anime', 'show', 'tv') or (ctx.get('season') not in (None, '', 0, '0') and ctx.get('episode') not in (None, '', 0, '0'))
    if not media_type:
        media_type = 'series' if is_episode else 'movie'
    video_id = ctx.get('video_id') or canonical_id
    season = _safe_int(ctx.get('season'), 0) if is_episode else None
    episode = _safe_int(ctx.get('episode'), 0) if is_episode else None
    title = ctx.get('show_title') or ctx.get('title') or canonical_id
    provider_name = ctx.get('provider_name') or 'Dex Hub'
    poster = ctx.get('poster') or ''
    background = ctx.get('background') or ''
    clearlogo = ctx.get('clearlogo') or ''
    duration_sec = _safe_float(duration_ms, 0.0) / 1000.0
    position_sec = _safe_float(position_ms, 0.0) / 1000.0
    percent = 100.0 if finished else _local_percent(position_ms, duration_ms)
    event_type = 'watched' if finished else 'progress'
    try:
        playback_store.upsert_entry(
            media_type,
            canonical_id,
            video_id,
            title,
            provider_name,
            poster,
            background,
            clearlogo,
            season,
            episode,
            position_sec,
            duration_sec,
            percent,
            ctx.get('stream_url') or '',
            event_type,
        )
    except Exception as exc:
        xbmc.log('[DexHub] local progress save failed: %s' % exc, xbmc.LOGWARNING)
    else:
        _invalidate_nextup_cache()
        # Wake up the home / CW UI so the row reflects this save without
        # the user having to navigate away and back. Skipped when we're
        # mid-stream and only saving an interim progress tick — those
        # don't change the visible row order or membership.
        if finished or position_ms >= 30000:
            _refresh_cw_containers()


def _invalidate_nextup_cache():
    try:
        win = xbmcgui.Window(10000)
        for key in ('dexhub.nextup_cache', 'dexhub.nextup_cache_ts'):
            try:
                win.clearProperty(key)
            except Exception:
                pass
    except Exception:
        pass


# Paths whose visible content is driven by playback_store / favorites and
# therefore needs a Container.Refresh after each progress save. Matched as
# substrings against Container.FolderPath.
_CW_REFRESH_PATHS = (
    'plugin.video.dexhub/?',     # root home page (CW row + nextup row)
    'plugin.video.dexhub/',      # any DexHub container
    'action=continue',           # full Continue Watching list
    'action=favorites',          # favorites screen
    'action=nextup',             # next-up list
    'action=home',               # explicit home action
)


def _refresh_cw_containers():
    """Trigger Container.Refresh on the current container if it's CW-related,
    AND set a stale-flag on Window(10000) so that the next time the user
    opens a CW-displaying screen it rebuilds from fresh data even if Kodi
    served its directory cache.

    Why both:
      - Container.Refresh handles the "user is staring at CW right now"
        case (e.g. episode ended → Kodi auto-returned to the previous
        container which was the CW list).
      - The stale-flag handles "user finished playback then navigated
        elsewhere then came back to CW", where Container.Refresh isn't
        applicable because no DexHub container was visible.
    """
    # Always set the stale flag so the next CW-screen open rebuilds.
    try:
        win = xbmcgui.Window(10000)
        win.setProperty('dexhub.cw_dirty', '1')
        win.setProperty('dexhub.cw_dirty_ts', str(int(time.time())))
    except Exception:
        pass

    # If a CW-affected DexHub container is the current container, refresh it.
    try:
        current = xbmc.getInfoLabel('Container.FolderPath') or ''
    except Exception:
        return
    if not current or 'plugin.video.dexhub' not in current:
        return
    if not any(token in current for token in _CW_REFRESH_PATHS):
        return
    try:
        xbmc.executebuiltin('Container.Refresh')
    except Exception:
        pass


def _clear_tmdbh_handoff_flag():
    try:
        for win_id in (12005, 10000):
            try:
                win = xbmcgui.Window(win_id)
            except Exception:
                continue
            for key in ('dexhub.invoked_by_tmdbh', 'dexhub.tmdbh_seed_ids', 'dexhub.tmdbh_seed_for', 'dexhub.tmdbh_handoff_until'):
                try:
                    win.clearProperty(key)
                except Exception:
                    pass
    except Exception:
        pass


def _reopen_source_picker_url(sess, position_seconds=0.0):
    picker = (sess or {}).get('source_picker_url') or ''
    if not picker:
        return False
    try:
        parts = urllib.parse.urlsplit(picker)
        query = dict(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))
        if float(position_seconds or 0.0) > 1.0:
            query['resume_seconds'] = '%.1f' % float(position_seconds or 0.0)
        query['fresh_search'] = '1'
        picker = urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(query), parts.fragment))
    except Exception:
        pass
    try:
        _monitor('stop-reopen-sources', title=(sess or {}).get('title') or '', position_seconds='%.1f' % float(position_seconds or 0.0))
    except Exception:
        pass
    try:
        xbmc.executebuiltin('Container.Update(%s,replace)' % picker)
        return True
    except Exception as exc:
        xbmc.log('[DexHub] reopen source picker failed: %s' % exc, xbmc.LOGWARNING)
        return False


def _publish_playback_artwork(ctx):
    if not isinstance(ctx, dict) or not ctx:
        return
    try:
        logo = ctx.get('clearlogo') or ''
        poster = ctx.get('poster') or ''
        fanart = ctx.get('background') or poster or ''
        title = ctx.get('title') or ''
        plot = ctx.get('plot') or ''
        year = str(ctx.get('year') or '')
        for win_id in (10000,):
            try:
                win = xbmcgui.Window(win_id)
            except Exception:
                continue
            for key, value in (
                ('dexhub.source.clearlogo', logo),
                ('dexhub.source.poster', poster),
                ('dexhub.source.thumb', poster),
                ('dexhub.source.fanart', fanart),
                ('dexhub.source.title', title),
                ('dexhub.source.plot', plot),
                ('dexhub.source.year', year),
                ('clearlogo', logo),
                ('logo', logo),
                ('tvshow.clearlogo', logo),
                ('poster', poster),
                ('thumb', poster),
                ('fanart', fanart),
                ('fanart_image', fanart),
            ):
                try:
                    win.setProperty(key, value)
                except Exception:
                    pass
    except Exception:
        pass


def _is_internal_navigation_path(path):
    value = str(path or '').strip()
    if not value.startswith('plugin://plugin.video.dexhub/'):
        return False
    markers = (
        'action=streams', 'action=episode_streams', 'action=item_open',
        'action=series_meta', 'action=play_item', 'action=cw_resume',
        'action=cw_play_from_start', 'action=play'
    )
    return any(marker in value for marker in markers)


class CompanionPlayer(xbmc.Player):
    def __init__(self):
        super().__init__()
        self.ctx = {}
        self.reporter = None
        # Playback health tracking for fallback.
        self._play_start_time = 0.0
        self._had_error = False
        self._progress_seen_ms = 0
        self._fallback_chain = []
        self._next_episode = None
        self._started_reported = False
        self._started_probe_pending = False
        self._resume_applied = False
        # Flag we set when we're the ones triggering the next play (avoid loops).
        self._own_trigger = False
        # Delayed fallback timer for false-positive start/stop handoffs.
        self._fallback_pending = False
        self._started_reported = False
        self._started_probe_pending = False

    def _refresh_context(self):
        self.ctx = load_session() or {}
        base = self.ctx.get('provider_base_url') or self.ctx.get('server_url') or ''
        for key in ('bootstrapUrl', 'companionUrl', 'companionScrobbleUrl', 'companionUnscrobbleUrl'):
            if self.ctx.get(key):
                self.ctx[key] = _absolute_url(base, self.ctx.get(key))
        self.reporter = get_reporter(self.ctx)
        self._fallback_chain = list(self.ctx.get('fallback_stream_keys') or [])
        self._next_episode = self.ctx.get('next_episode') or None
        self._had_error = False
        self._progress_seen_ms = 0
        self._own_trigger = False
        self._fallback_pending = False
        self._started_reported = False
        self._started_probe_pending = False
        self._resume_applied = False
        import time as _t
        self._play_start_time = _t.time()

    def _position_ms(self):
        try:
            return int(self.getTime() * 1000)
        except Exception:
            return 0

    def _duration_ms(self):
        try:
            total = int(self.getTotalTime() * 1000)
            if total > 0:
                return total
        except Exception:
            pass
        return int(self.ctx.get('duration_ms', 0))

    def _current_playing_file(self):
        try:
            return self.getPlayingFile() or ''
        except Exception:
            return ''

    def _player_looks_active(self, require_real_media=False):
        playing_file = self._current_playing_file()
        if playing_file and _is_internal_navigation_path(playing_file):
            return False
        try:
            if self.isPlayingVideo():
                return True
        except Exception:
            pass
        if playing_file:
            return True
        try:
            if xbmc.getCondVisibility('Player.HasVideo'):
                if not require_real_media:
                    return True
                return self._position_ms() > 0
        except Exception:
            pass
        return False

    def _confirm_started_async(self):
        if self._started_probe_pending or self._started_reported:
            return
        self._started_probe_pending = True

        def _runner():
            try:
                for _ in range(32):
                    if self._player_looks_active(require_real_media=True):
                        if not self._started_reported:
                            self._started_reported = True
                            _monitor('playback-started', title=self.ctx.get('title') or '', canonical_id=self.ctx.get('canonical_id') or '', provider=self.ctx.get('provider_name') or self.ctx.get('provider_id') or '', playing_file=self._current_playing_file())
                            self._report('started')
                        return
                    xbmc.sleep(250)
                _monitor('playback-start-timeout', level=xbmc.LOGWARNING, title=self.ctx.get('title') or '', canonical_id=self.ctx.get('canonical_id') or '', provider=self.ctx.get('provider_name') or self.ctx.get('provider_id') or '', playing_file=self._current_playing_file())
            finally:
                self._started_probe_pending = False

        try:
            threading.Thread(target=_runner, name='DexHubStartedProbe', daemon=True).start()
        except Exception as exc:
            self._started_probe_pending = False
            xbmc.log('[DexHub] start probe thread failed: %s' % exc, xbmc.LOGWARNING)

    def _schedule_fallback(self, reason='', delay_ms=3200):
        if not self._fallback_chain:
            return False
        if self._fallback_pending:
            return True
        self._fallback_pending = True

        def _runner():
            try:
                remaining = max(250, int(delay_ms or 0))
                while remaining > 0:
                    xbmc.sleep(min(250, remaining))
                    remaining -= 250
                    if self._player_looks_active():
                        xbmc.log('[DexHub] fallback cancelled — playback recovered (%s)' % (reason or 'unknown'), xbmc.LOGINFO)
                        return
                if self._player_looks_active():
                    xbmc.log('[DexHub] fallback cancelled late — playback active (%s)' % (reason or 'unknown'), xbmc.LOGINFO)
                    return
                self._try_fallback()
            finally:
                self._fallback_pending = False

        try:
            threading.Thread(target=_runner, name='DexHubFallbackGrace', daemon=True).start()
            return True
        except Exception as exc:
            self._fallback_pending = False
            xbmc.log('[DexHub] fallback grace thread failed: %s' % exc, xbmc.LOGWARNING)
            return self._try_fallback()

    def _report(self, method_name, position_ms=None):
        if not companion_enabled():
            return
        if not self.reporter:
            return
        try:
            getattr(self.reporter, method_name)(self.ctx, self._position_ms() if position_ms is None else position_ms)
        except TypeError:
            getattr(self.reporter, method_name)(self.ctx)
        except urllib.error.HTTPError as exc:
            xbmc.log('[DexHub] companion %s HTTP %s' % (method_name, exc.code), xbmc.LOGWARNING)
        except Exception as exc:
            xbmc.log('[DexHub] companion %s error: %s' % (method_name, exc), xbmc.LOGWARNING)

    def _apply_resume_async(self):
        if self._resume_applied:
            return
        try:
            target = float(self.ctx.get('resume_seconds') or 0.0)
        except Exception:
            target = 0.0
        try:
            resume_pct = float(self.ctx.get('resume_percent') or 0.0)
        except Exception:
            resume_pct = 0.0
        if target <= 1.0 and not (1.0 < resume_pct < 95.0):
            return
        self._resume_applied = True

        def _runner():
            try:
                for attempt in range(14):
                    xbmc.sleep(450 + min(1400, attempt * 150))
                    if not self._player_looks_active():
                        continue
                    seek_to = target
                    try:
                        total = float(self.getTotalTime() or 0.0)
                    except Exception:
                        total = 0.0
                    # Trakt rows sometimes have percent but no exact seconds.
                    # Compute resume from the actual player duration after the
                    # stream starts so Continue Watching does not restart at 0.
                    if seek_to <= 1.0 and 1.0 < resume_pct < 95.0 and total > 60.0:
                        seek_to = max(0.0, total * resume_pct / 100.0)
                    try:
                        if total > 0 and seek_to > max(0.0, total - 90.0):
                            seek_to = max(0.0, total - 90.0)
                    except Exception:
                        pass
                    if seek_to <= 1.0:
                        continue
                    try:
                        self.seekTime(seek_to)
                    except Exception:
                        continue
                    xbmc.sleep(700)
                    try:
                        current = float(self.getTime() or 0.0)
                    except Exception:
                        current = 0.0
                    if current >= max(1.0, seek_to - 6.0):
                        _monitor('resume-applied', title=self.ctx.get('title') or '', target_seconds='%.1f' % seek_to, current_seconds='%.1f' % current)
                        return
                _monitor('resume-failed', level=xbmc.LOGWARNING, title=self.ctx.get('title') or '', target_seconds='%.1f' % target, resume_percent='%.2f' % resume_pct)
            except Exception as exc:
                _monitor('resume-error', level=xbmc.LOGWARNING, error=exc, title=self.ctx.get('title') or '')

        try:
            threading.Thread(target=_runner, name='DexHubResumeSeek', daemon=True).start()
        except Exception:
            pass

    def onPlayBackStarted(self):
        self._refresh_context()
        _clear_tmdbh_handoff_flag()
        _publish_playback_artwork(self.ctx)
        self._apply_resume_async()
        self._confirm_started_async()

    def onPlayBackPaused(self):
        _publish_playback_artwork(self.ctx)
        _monitor('playback-paused', title=self.ctx.get('title') or '', position_ms=self._position_ms())
        pos = self._position_ms()
        self._progress_seen_ms = max(self._progress_seen_ms, int(pos or 0))
        dur = self._duration_ms()
        _save_local_progress(self.ctx, pos, dur, finished=False)
        self._report('paused', position_ms=pos)

    def onPlayBackResumed(self):
        _publish_playback_artwork(self.ctx)
        _monitor('playback-resumed', title=self.ctx.get('title') or '', position_ms=self._position_ms())
        pos = self._position_ms()
        self._progress_seen_ms = max(self._progress_seen_ms, int(pos or 0))
        _save_local_progress(self.ctx, pos, self._duration_ms(), finished=False)
        self._report('progress', position_ms=pos)

    def onPlayBackError(self):
        """Kodi 20+ fires this on format/codec/network failures."""
        _clear_tmdbh_handoff_flag()
        self._had_error = True
        _monitor('playback-error', level=xbmc.LOGWARNING, title=self.ctx.get('title') or '', canonical_id=self.ctx.get('canonical_id') or '', provider=self.ctx.get('provider_name') or self.ctx.get('provider_id') or '')
        xbmc.log('[DexHub] onPlayBackError — scheduling fallback grace', xbmc.LOGWARNING)
        self._schedule_fallback('playback-error', delay_ms=3200)

    def _try_fallback(self):
        """Try the next stream key in the fallback chain, if any."""
        if not self._fallback_chain:
            return False
        next_key = self._fallback_chain.pop(0)
        # One-shot fallback only: once we move to the next stream, stop there
        # instead of walking the entire source list on repeated failures.
        self._fallback_chain = []
        try:
            sess = load_session() or {}
            sess['fallback_stream_keys'] = []
            save_session(sess)
        except Exception:
            pass
        _monitor('fallback-trigger', next_key=next_key, title=self.ctx.get('title') or '', provider=self.ctx.get('provider_name') or self.ctx.get('provider_id') or '')
        xbmc.log('[DexHub] triggering fallback stream: %s' % next_key, xbmc.LOGINFO)
        try:
            xbmcgui.Dialog().notification('Dex Hub', tr('فشل الرابط — تجربة التالي...'), xbmcgui.NOTIFICATION_WARNING, 2500)
        except Exception:
            pass
        self._own_trigger = True
        xbmc.executebuiltin('RunPlugin(plugin://plugin.video.dexhub/?action=play&stream_key=%s)' % next_key)
        return True

    def onPlayBackStopped(self):
        _clear_tmdbh_handoff_flag()
        sess_for_reopen = load_session() or {}
        pos = self._position_ms()
        dur = self._duration_ms()
        self._progress_seen_ms = max(self._progress_seen_ms, int(pos or 0))
        watched = should_mark_watched(pos, dur)
        # False-positive fallback fix: some hosts briefly stop/reopen the
        # player while the real stream continues. Only auto-fallback when
        # playback died almost immediately AND we never reached meaningful
        # progress, or Kodi explicitly reported a playback error.
        import time as _t
        elapsed = _t.time() - (self._play_start_time or 0)
        played_little = (pos < 3000)
        no_real_progress = (self._progress_seen_ms < 3000)
        # Do not auto-play another source when the user backs out or stops
        # early. Kodi reports those cases the same way as an early stop, so the
        # old no-progress fallback could re-enter the source search and start
        # the movie again. Only fallback after an explicit Kodi playback error.
        probably_failed = bool(self._had_error)
        if probably_failed and self._fallback_chain:
            _monitor('stopped-probably-failed', level=xbmc.LOGWARNING, title=self.ctx.get('title') or '', elapsed='%.2f' % elapsed, position_ms=pos, duration_ms=dur, progress_seen_ms=self._progress_seen_ms, had_error=self._had_error, fallback_count=len(self._fallback_chain or []))
            self._schedule_fallback('stopped-early', delay_ms=3200)
            # Don't clear session yet — the fallback or recovered playback will reload it.
            return
        if watched:
            _monitor('playback-ended', title=self.ctx.get('title') or '', position_ms=dur or pos, duration_ms=dur, watched=True)
            _save_local_progress(self.ctx, dur or pos, dur or pos, finished=True)
        elif pos >= 15000 or _local_percent(pos, dur) >= 1.0:
            _monitor('playback-stopped', title=self.ctx.get('title') or '', position_ms=pos, duration_ms=dur, watched=False)
            _save_local_progress(self.ctx, pos, dur, finished=False)
        if self.reporter:
            if watched:
                self._report('ended', position_ms=dur or pos)
            else:
                self._report('stopped', position_ms=pos)
                if self.ctx.get('companionUnscrobbleUrl'):
                    try:
                        self.reporter._post(self.ctx, 'companionUnscrobbleUrl', pos, 'stopped', mark_watched=False)
                    except Exception as exc:
                        xbmc.log('[DexHub] companion unscrobble error: %s' % exc, xbmc.LOGWARNING)
        # User request: after Back/Stop, stay where Kodi returns naturally.
        # Do not reopen the source picker or trigger a fresh source search.
        try:
            _monitor('stop-reopen-sources-suppressed', title=self.ctx.get('title') or '', position_seconds='%.1f' % (float(pos or 0) / 1000.0))
        except Exception:
            pass
        clear_session()
        self.ctx = {}
        self.reporter = None
        self._fallback_chain = []
        self._next_episode = None

    def onPlayBackEnded(self):
        _clear_tmdbh_handoff_flag()
        dur = self._duration_ms()
        _save_local_progress(self.ctx, dur or self._position_ms(), dur, finished=True)
        self._report('ended', position_ms=dur)
        next_ep = self._next_episode
        clear_session()
        self.ctx = {}
        self.reporter = None
        self._fallback_chain = []
        self._next_episode = None
        self._started_reported = False
        self._started_probe_pending = False
        # Auto-next episode prompt (if enabled and available).
        if next_ep:
            self._maybe_play_next(next_ep)

    def _maybe_play_next(self, next_ep):
        try:
            auto = (ADDON.getSetting('auto_next_episode') or 'true').lower() == 'true'
        except Exception:
            auto = True
        if not auto:
            return
        try:
            countdown = max(3, int(ADDON.getSetting('auto_next_prompt_seconds') or '20'))
        except Exception:
            countdown = 20
        title = next_ep.get('title') or ''
        s = int(next_ep.get('season') or 0)
        e = int(next_ep.get('episode') or 0)
        dlg = xbmcgui.DialogProgress()
        try:
            dlg.create('Dex Hub', tr('الحلقة التالية: %s — S%02dE%02d') % (title, s, e))
            import time as _t
            start = _t.time()
            while not dlg.iscanceled() and (_t.time() - start) < countdown:
                remaining = int(countdown - (_t.time() - start))
                pct = int(max(0, min(100, ((_t.time() - start) / float(countdown)) * 100)))
                dlg.update(pct, tr('الحلقة التالية: %s — S%02dE%02d\nالبدء خلال: %ss') % (title, s, e, remaining))
                xbmc.sleep(250)
        finally:
            try:
                dlg.close()
            except Exception:
                pass
        if dlg.iscanceled():
            return
        # Trigger the next episode via the plugin router — this re-enters the
        # whole streams/auto-pick pipeline with correct IDs and artwork.
        params = {
            'action': 'play_item',
            'media_type': 'series',
            'canonical_id': next_ep.get('canonical_id') or '',
            'video_id': next_ep.get('video_id') or '',
            'season': str(s),
            'episode': str(e),
            'title': next_ep.get('title') or '',
        }
        url = 'plugin://plugin.video.dexhub/?' + urllib.parse.urlencode(params)
        xbmc.executebuiltin('RunPlugin(%s)' % url)


class ProgressLoop(object):
    def __init__(self, player):
        self.player = player
        self._back_reopen_until = 0.0
        self._back_seen_for = 0.0

    def _fullscreen_active(self):
        try:
            return bool(xbmc.getCondVisibility('Window.IsActive(fullscreenvideo)'))
        except Exception:
            return True

    def _maybe_stop_and_reopen_sources(self):
        # Keep playback alive when the user backs out of fullscreen. Kodi can
        # continue the video in the background / mini-player; the source picker
        # should only reopen after the user actually stops/closes playback.
        self._back_seen_for = 0.0
        return

    def _reopen_sources_after_stop(self, sess, position_seconds=0.0):
        # Disabled: stopping/backing out must not reopen source search or play again.
        return False


    def run(self):
        monitor = xbmc.Monitor()
        while not monitor.abortRequested():
            interval = _interval_seconds()
            if companion_enabled() and self.player.isPlayingVideo() and self.player.reporter:
                self.player._report('progress')
            self._maybe_stop_and_reopen_sources()
            if monitor.waitForAbort(interval):
                break
