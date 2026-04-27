# -*- coding: utf-8 -*-
import base64
import html
import json
import os
import re
import sys
import threading
import time
import unicodedata
from urllib.parse import parse_qsl, parse_qs, urlencode, urlparse, urljoin, quote_plus
from urllib.request import Request, urlopen

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

from . import cache_store, playback_store, store
from .art import addon_fanart, catalog_art, enrich_meta_art, hybrid_meta_art, posters_prefer_local, poster_source_mode, native_meta_art, extract_ids, media_path, provider_art, root_art, stream_art, neutral_fanart, _wrap_tokenized_url
from .i18n import tr
from .client import fetch_catalog, fetch_meta, fetch_streams, run_parallel, iter_parallel, supports_resource, validate_manifest, fast_timeout, meta_ttl, parallel_workers
from .source_browser import open_sources_window
from .sources_loading import SourcesLoadingDialog
from .playback_wait import PlaybackWaiter
from .session_store import save_session, clear_session, load_session
from .subtitle_broker import search_subtitles as broker_search_subtitles
from .stream_ranking import finalize_stream_entries as _rank_finalize_stream_entries
from .nextup_logic import invalidate_nextup_cache as _nextup_invalidate_cache, series_videos_cached as _nextup_series_videos_cached, nextup_items_cached as _nextup_items_cached_logic
from . import trakt
from . import mdblist
from . import tmdbh_player
from . import formatter as _source_formatter
from . import tmdbhelper as _tmdb_art_db
from . import tmdb_direct as _tmdb_direct
from . import collection_sets as _collections_mod
from . import favorites_store
from . import meta_source as _meta_source

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]
WINDOW_ID = 10000
PROP = 'dexhub.play_context'
SERIES_PROP_PREFIX = 'dexhub.series.'
SUBS_DIR = xbmcvfs.translatePath('special://temp/dexhub_subs/')

LANG_MAP = {
    'ar': ('🇸🇦', 'Arabic'), 'ara': ('🇸🇦', 'Arabic'), 'arabic': ('🇸🇦', 'Arabic'),
    'en': ('🇺🇸', 'English'), 'eng': ('🇺🇸', 'English'), 'english': ('🇺🇸', 'English'),
    'fr': ('🇫🇷', 'French'), 'fre': ('🇫🇷', 'French'), 'fra': ('🇫🇷', 'French'), 'french': ('🇫🇷', 'French'),
    'es': ('🇪🇸', 'Spanish'), 'spa': ('🇪🇸', 'Spanish'), 'spanish': ('🇪🇸', 'Spanish'),
    'de': ('🇩🇪', 'German'), 'deu': ('🇩🇪', 'German'), 'ger': ('🇩🇪', 'German'), 'german': ('🇩🇪', 'German'),
    'it': ('🇮🇹', 'Italian'), 'ita': ('🇮🇹', 'Italian'), 'italian': ('🇮🇹', 'Italian'),
    'pt': ('🇵🇹', 'Portuguese'), 'por': ('🇵🇹', 'Portuguese'), 'portuguese': ('🇵🇹', 'Portuguese'),
    'pt-br': ('🇧🇷', 'Portuguese BR'), 'pob': ('🇧🇷', 'Portuguese BR'), 'pb': ('🇧🇷', 'Portuguese BR'), 'brazilian': ('🇧🇷', 'Portuguese BR'),
    'tr': ('🇹🇷', 'Turkish'), 'tur': ('🇹🇷', 'Turkish'), 'turkish': ('🇹🇷', 'Turkish'),
    'ru': ('🇷🇺', 'Russian'), 'rus': ('🇷🇺', 'Russian'), 'russian': ('🇷🇺', 'Russian'),
    'ja': ('🇯🇵', 'Japanese'), 'jpn': ('🇯🇵', 'Japanese'), 'japanese': ('🇯🇵', 'Japanese'),
    'ko': ('🇰🇷', 'Korean'), 'kor': ('🇰🇷', 'Korean'), 'korean': ('🇰🇷', 'Korean'),
    'zh': ('🇨🇳', 'Chinese'), 'chi': ('🇨🇳', 'Chinese'), 'zho': ('🇨🇳', 'Chinese'), 'chinese': ('🇨🇳', 'Chinese'),
    'hi': ('🇮🇳', 'Hindi'), 'hin': ('🇮🇳', 'Hindi'), 'hindi': ('🇮🇳', 'Hindi'),
    'fa': ('🇮🇷', 'Persian'), 'fas': ('🇮🇷', 'Persian'), 'per': ('🇮🇷', 'Persian'), 'persian': ('🇮🇷', 'Persian'),
    'und': ('🏳️', 'Unknown'),
}

FILTER_NAMES = {
    'search': 'Search', 'sort': 'Sort', 'genre': 'Genre', 'availability': 'Availability', 'year': 'Year',
    'contentRating': 'Rating', 'studio': 'Studio', 'collection': 'Collection', 'unwatched': 'Unwatched',
}

HEX_ENTITIES = [
    ('&#x26;', '&'), ('&#x27;', "'"), ('&#xC6;', 'AE'), ('&#xC7;', 'C'), ('&#xF4;', 'o'),
    ('&#xE9;', 'e'), ('&#xEB;', 'e'), ('&#xED;', 'i'), ('&#xEE;', 'i'), ('&#xA2;', 'c'),
    ('&#xE2;', 'a'), ('&#xEF;', 'i'), ('&#xE1;', 'a'), ('&#xE8;', 'e'), ('%2E', '.'),
    ('&frac12;', '%BD'), ('&#xBD;', '%BD'), ('&#xB3;', '%B3'), ('&#xB0;', '%B0'),
    ('&amp;', '&'), ('&#xB7;', '.'), ('&#xE4;', 'A'), ('\xe2\x80\x99', '')
]
SPECIAL_BLANKS = [
    ('"', ' '), ('/', ' '), (':', ' '), ('<', ' '), ('>', ' '), ('?', ' '), ('\\', ' '), ('|', ' '),
    ('%BD;', ' '), ('%B3;', ' '), ('%B0;', ' '), ("'", ''), (' - ', ' '), ('.', ' '), ('!', ''), (';', ''), (',', ' ')
]
COLOR_TAG_RE = re.compile(r'\[/?(?:COLOR|B|I|UPPERCASE|LOWERCASE|LIGHT)\b[^\]]*\]', re.I)
STREAM_ICON_RE = re.compile(r'[\u2500-\u257F\u2580-\u259F\u25A0-\u25FF\u2600-\u27BF\uE000-\uF8FF\U0001F300-\U0001FAFF]')
REGIONAL_FLAG_RE = re.compile(r'[\U0001F1E6-\U0001F1FF]{2}')
BRACKET_RE = re.compile(r'\[[^\]]*\]')
MULTI_WS_RE = re.compile(r'\s+')
QUALITY_RE = re.compile(r'\b(?:2160p|4k|1080p|720p|480p|sd|hdr10\+|hdr10|hdr|dv|dovi|dolby\s*vision|remux|bluray|blu\s*ray|web[- ]?dl|webrip|x265|x264|hevc|av1|aac|dts(?:-?hd)?|truehd|atmos|ddp(?:5\.1)?|5\.1|7\.1)\b', re.I)
SIZE_RE = re.compile(r'(\d+(?:\.\d+)?\s*(?:GB|MB|GiB|MiB))', re.I)
YEAR_RE = re.compile(r'^(\d{4})')


def build_url(**query):
    return BASE_URL + '?' + urlencode(query)


def notify(msg):
    xbmcgui.Dialog().notification('Dex Hub', tr(msg), xbmcgui.NOTIFICATION_INFO, 2500)


def error(msg):
    xbmcgui.Dialog().notification('Dex Hub', tr(msg), xbmcgui.NOTIFICATION_ERROR, 3500)


def _get_int_setting(key, default, minimum=None, maximum=None):
    try:
        value = int(ADDON.getSetting(key) or default)
    except Exception:
        value = int(default)
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _get_bool_setting(key, default=False):
    try:
        raw = (ADDON.getSetting(key) or ('true' if default else 'false')).strip().lower()
    except Exception:
        raw = 'true' if default else 'false'
    return raw in ('true', '1', 'yes', 'on')


def _profile_path():
    try:
        path = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
    except Exception:
        path = ''
    if path:
        try:
            os.makedirs(path, exist_ok=True)
        except Exception:
            pass
    return path or xbmcvfs.translatePath('special://profile/addon_data/plugin.video.dexhub/')


def _source_pref_path():
    return os.path.join(_profile_path(), 'last_source_map.json')


def _load_source_pref_map():
    path = _source_pref_path()
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_source_pref_map(data):
    path = _source_pref_path()
    try:
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(data or {}, fh, ensure_ascii=False)
    except Exception:
        pass


def _source_scope_key(media_type='', canonical_id='', video_id=''):
    mt = (media_type or '').lower() or 'movie'
    cid = str(canonical_id or '').strip()
    vid = str(video_id or '').strip()
    if mt in ('series', 'anime', 'show', 'tv') and vid:
        return '%s|%s|%s' % (mt, cid, vid)
    return '%s|%s' % (mt, cid)


def _playback_monitor_path():
    try:
        path = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.dexhub/playback_monitor.log')
    except Exception:
        path = os.path.join(_profile_path(), 'playback_monitor.log')
    return path


def _monitor_playback(event, level=xbmc.LOGINFO, **payload):
    record = {'event': str(event or ''), 'ts': int(time.time())}
    for key, value in dict(payload or {}).items():
        if value in (None, '', [], {}, ()): 
            continue
        try:
            if isinstance(value, (dict, list, tuple)):
                record[key] = value
            else:
                record[key] = str(value)
        except Exception:
            continue
    try:
        xbmc.log('[DexHubMonitor] %s' % json.dumps(record, ensure_ascii=False, sort_keys=True), level)
    except Exception:
        pass
    try:
        path = _playback_monitor_path()
        folder = os.path.dirname(path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        try:
            if path and os.path.exists(path) and os.path.getsize(path) > 262144:
                with open(path, 'rb') as fh:
                    data = fh.read()[-131072:]
                with open(path, 'wb') as fh:
                    fh.write(data)
        except Exception:
            pass
        with open(path, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
    except Exception:
        pass



def _is_internal_navigation_path(path):
    value = str(path or '').strip()
    if not value.startswith('plugin://plugin.video.dexhub/'):
        return False
    markers = (
        'action=streams', 'action=episode_streams', 'action=item_open',
        'action=series_meta', 'action=play_item', 'action=cw_resume',
        'action=cw_play_from_start', 'action=play', 'action=tmdb_player',
        'action=kodi_route_browse',
    )
    return any(marker in value for marker in markers)


def _player_has_real_media(player=None):
    player = player or xbmc.Player()
    playing_file = ''
    try:
        playing_file = player.getPlayingFile() or ''
    except Exception:
        playing_file = ''
    if playing_file and not _is_internal_navigation_path(playing_file):
        return True
    try:
        if player.isPlayingVideo() and not _is_internal_navigation_path(playing_file):
            return True
    except Exception:
        pass
    try:
        if xbmc.getCondVisibility('Player.HasVideo') and not _is_internal_navigation_path(playing_file):
            return True
    except Exception:
        pass
    return False


def _is_series_media(media_type=''):
    return str(media_type or '').strip().lower() in ('series', 'anime', 'show', 'tv')


def _source_picker_url(media_type='movie', canonical_id='', title='', season='', episode='', video_id='', resume_seconds='', preferred_provider_name='', source_provider_id=''):
    media_type = str(media_type or 'movie').strip().lower()
    if season not in (None, '', 0, '0') and episode not in (None, '', 0, '0'):
        args = {
            'action': 'episode_streams',
            'canonical_id': canonical_id,
            'video_id': video_id or canonical_id,
            'season': str(season),
            'episode': str(episode),
            'title': title or canonical_id,
            'media_type': 'series' if _is_series_media(media_type) else media_type,
        }
        if resume_seconds not in (None, '', 0, '0'):
            args['resume_seconds'] = str(resume_seconds)
        if preferred_provider_name:
            args['preferred_provider_name'] = preferred_provider_name
        if source_provider_id:
            args['source_provider_id'] = source_provider_id
        return build_url(**args)
    if _is_series_media(media_type):
        return build_url(action='series_meta', media_type='series', canonical_id=canonical_id, title=title or canonical_id, source_provider_id=source_provider_id or '')
    args = {'action': 'streams', 'media_type': media_type or 'movie', 'canonical_id': canonical_id, 'title': title or canonical_id}
    if resume_seconds not in (None, '', 0, '0'):
        args['resume_seconds'] = str(resume_seconds)
    if preferred_provider_name:
        args['preferred_provider_name'] = preferred_provider_name
    if source_provider_id:
        args['source_provider_id'] = source_provider_id
    return build_url(**args)


def _source_picker_url_from_ctx(ctx, resume_seconds=''):
    ctx = ctx or {}
    try:
        rs = resume_seconds if resume_seconds not in (None, '') else ctx.get('resume_seconds', '')
        return _source_picker_url(
            media_type=ctx.get('media_type') or 'movie',
            canonical_id=ctx.get('canonical_id') or '',
            title=ctx.get('title') or ctx.get('show_title') or ctx.get('canonical_id') or '',
            season=ctx.get('season') or '',
            episode=ctx.get('episode') or '',
            video_id=ctx.get('video_id') or ctx.get('canonical_id') or '',
            resume_seconds=rs,
            preferred_provider_name=ctx.get('provider_name') or '',
            source_provider_id=ctx.get('source_provider_id') or ctx.get('meta_target_key') or '',
        )
    except Exception:
        return ''


def _build_source_picker_menu(media_type='movie', canonical_id='', title='', season='', episode='', video_id='', resume_seconds='', preferred_provider_name='', source_provider_id=''):
    url = _source_picker_url(media_type=media_type, canonical_id=canonical_id, title=title, season=season, episode=episode, video_id=video_id, resume_seconds=resume_seconds, preferred_provider_name=preferred_provider_name, source_provider_id=source_provider_id)
    if not url:
        return []
    label = tr('فتح المواسم') if _is_series_media(media_type) and season in (None, '', 0, '0') and episode in (None, '', 0, '0') else tr('اختيار المصدر')
    return [(label, 'Container.Update(%s)' % url)]


# ─── Cross-invocation dispatch de-dup ──────────────────────────────────
# Kodi spawns a fresh plugin process for every click. A fast double-click
# therefore launches two processes that both try to open the source picker
# / TMDb Helper / start playback — the user sees stacked modals or
# TMDb Helper opens twice in a row. SourcesWindow has its own action guard
# for clicks within the same process; this is the cross-process backstop.
# Stored on Window(WINDOW_ID) as 'key|timestamp'.
_DISPATCH_PROP = 'dexhub.dispatch.in_flight'


def _dispatch_in_flight(key, window_seconds=6):
    """Return True if another plugin invocation just claimed `key`.

    Stamps `key` with the current timestamp on a miss, so a second
    invocation within `window_seconds` is suppressed.
    """
    if not key:
        return False
    now = time.time()
    try:
        win = xbmcgui.Window(WINDOW_ID)
        raw = win.getProperty(_DISPATCH_PROP) or ''
        if raw and '|' in raw:
            prev_key, prev_ts = raw.split('|', 1)
            try:
                prev_ts_f = float(prev_ts)
            except Exception:
                prev_ts_f = 0.0
            if prev_key == key and (now - prev_ts_f) < window_seconds:
                return True
        win.setProperty(_DISPATCH_PROP, '%s|%.3f' % (key, now))
    except Exception:
        return False
    return False


def _dispatch_clear():
    try:
        xbmcgui.Window(WINDOW_ID).clearProperty(_DISPATCH_PROP)
    except Exception:
        pass

_TMDBH_HANDOFF_UNTIL_PROP = 'dexhub.tmdbh_handoff_until'
_TMDBH_TRANSIENT_PROPS = ('dexhub.invoked_by_tmdbh', 'dexhub.tmdbh_seed_ids', 'dexhub.tmdbh_seed_for', _TMDBH_HANDOFF_UNTIL_PROP)
_SOURCE_TRANSIENT_PROPS = (
    'dexhub.source.clearlogo', 'dexhub.source.logo', 'dexhub.source.poster', 'dexhub.source.thumb',
    'dexhub.source.fanart', 'dexhub.source.title', 'dexhub.source.plot', 'dexhub.source.year',
    'dexhub.source.rating', 'dexhub.source.genre'
)
_GLOBAL_ART_TRANSIENT_PROPS = (
    'clearlogo', 'logo', 'tvshow.clearlogo', 'poster', 'thumb', 'fanart', 'fanart_image',
    'dexhub.clearlogo', 'dexhub.poster', 'dexhub.fanart',
    'ArcticFuse.NowPlaying.Logo', 'ArcticFuse.NowPlaying.Thumb', 'ArcticFuse.NowPlaying.Fanart',
    'ArcticFuse.NowPlaying.Title', 'ArcticFuse.NowPlaying.Plot', 'ArcticFuse.NowPlaying.Year',
    'ArcticFuse.NowPlaying.Episode', 'ArcticFuse.NowPlaying.ShowTitle',
    'ArcticFuse.Player.Logo', 'ArcticFuse.Player.Thumb', 'ArcticFuse.Player.Fanart',
    'ArcticFuse.Player.Episode', 'ArcticFuse.Player.ShowTitle', 'ArcticFuse.CurrentlyPlaying',
)


def _mark_tmdbh_handoff(seconds=45):
    """Mark a TMDb Helper -> Dex Hub handoff across plugin invocations.

    TMDb Helper can immediately re-open its player route if Kodi receives a
    second click/resolve event while our source dialog is still active. A short
    scoped cooldown keeps every internal Dex Hub click on the Dex path until
    playback starts, cancel/no-source occurs, or the cooldown expires.
    """
    try:
        until = time.time() + max(8, int(seconds or 45))
        for win_id in (WINDOW_ID, 10000, 12005):
            try:
                xbmcgui.Window(win_id).setProperty(_TMDBH_HANDOFF_UNTIL_PROP, '%.3f' % until)
            except Exception:
                pass
    except Exception:
        pass


def _tmdbh_handoff_active():
    try:
        now = time.time()
        for win_id in (WINDOW_ID, 10000, 12005):
            try:
                win = xbmcgui.Window(win_id)
                if (win.getProperty('dexhub.invoked_by_tmdbh') or '').strip() == '1':
                    return True
                raw_until = win.getProperty(_TMDBH_HANDOFF_UNTIL_PROP) or ''
                if raw_until:
                    try:
                        if float(raw_until) > now:
                            return True
                    except Exception:
                        pass
            except Exception:
                continue
    except Exception:
        pass
    return False


def _clear_tmdbh_transient():
    """Clear TMDb Helper handoff flags/seeds after cancel/error/no-source paths."""
    for win_id in (WINDOW_ID, 10000, 12005):
        try:
            win = xbmcgui.Window(win_id)
        except Exception:
            continue
        for key in _TMDBH_TRANSIENT_PROPS:
            try:
                win.clearProperty(key)
            except Exception:
                pass


def _clear_source_transient_props(clear_global=False):
    """Clear source/window artwork that can leak from the previous item."""
    if clear_global:
        try:
            if _player_has_real_media():
                clear_global = False
        except Exception:
            clear_global = False
    for win_id in (WINDOW_ID, 10000):
        try:
            win = xbmcgui.Window(win_id)
        except Exception:
            continue
        for key in _SOURCE_TRANSIENT_PROPS:
            try:
                win.clearProperty(key)
            except Exception:
                pass
        if clear_global:
            for key in _GLOBAL_ART_TRANSIENT_PROPS:
                try:
                    win.clearProperty(key)
                except Exception:
                    pass


def play_item(media_type='', canonical_id='', title='', video_id='', season='', episode='', resume_seconds='0', preferred_provider_name='', tmdb_id='', imdb_id='', tvdb_id='', source_provider_id=''):
    media_type = str(media_type or 'movie').strip().lower()
    _dispatch_key = 'play_item|%s|%s|%s|%s|%s' % (
        media_type, canonical_id or '', video_id or '',
        str(season or ''), str(episode or ''),
    )
    if _dispatch_in_flight(_dispatch_key):
        xbmc.log('[DexHub] play_item: duplicate dispatch suppressed (%s)' % _dispatch_key, xbmc.LOGINFO)
        return
    if _maybe_redirect_default_player(media_type=media_type, canonical_id=canonical_id, title=title or canonical_id, season=season, episode=episode, tmdb_id=tmdb_id, imdb_id=imdb_id, tvdb_id=tvdb_id):
        return
    return _dispatch_dexhub_play(
        media_type=media_type,
        canonical_id=canonical_id,
        title=title or canonical_id,
        video_id=video_id,
        season=season,
        episode=episode,
        resume_seconds=resume_seconds,
        preferred_provider_name=preferred_provider_name,
        source_provider_id=source_provider_id,
    )


def _remember_source_choice(ctx):
    if not _get_bool_setting('remember_last_source', False):
        return
    if not isinstance(ctx, dict):
        return
    scope = _source_scope_key(ctx.get('media_type'), ctx.get('canonical_id'), ctx.get('video_id'))
    if not scope.strip('|'):
        return
    payload = {
        'provider_name': str(ctx.get('provider_name') or '').strip(),
        'provider_id': str(ctx.get('provider_id') or '').strip(),
        'stream_url_host': (urlparse(str(ctx.get('stream_url') or '')).netloc or '').lower(),
        'saved_at': int(time.time()),
    }
    data = _load_source_pref_map()
    data[scope] = payload
    items = sorted(data.items(), key=lambda kv: int(((kv[1] or {}).get('saved_at') or 0)), reverse=True)[:600]
    _save_source_pref_map(dict(items))


def _last_source_choice(media_type='', canonical_id='', video_id=''):
    if not _get_bool_setting('remember_last_source', False):
        return {}
    return _load_source_pref_map().get(_source_scope_key(media_type, canonical_id, video_id), {}) or {}


def _invalidate_nextup_cache():
    try:
        _nextup_invalidate_cache(xbmcgui.Window(WINDOW_ID))
    except Exception:
        pass


def _listing_page_size():
    return _get_int_setting('large_section_limit', 30, minimum=12, maximum=60)


_SEARCH_RESULT_CACHE = {}
_SEARCH_RESULT_CACHE_ORDER = []
_SEARCH_RESULT_CACHE_MAX = 32
_SEARCH_RESULT_TTL = 180


def _search_cache_get(key):
    entry = _SEARCH_RESULT_CACHE.get(key)
    if not entry:
        return None
    expires_at, value = entry
    if expires_at < time.time():
        _SEARCH_RESULT_CACHE.pop(key, None)
        return None
    return value


def _search_cache_put(key, value):
    _SEARCH_RESULT_CACHE[key] = (time.time() + _SEARCH_RESULT_TTL, value)
    if key not in _SEARCH_RESULT_CACHE_ORDER:
        _SEARCH_RESULT_CACHE_ORDER.append(key)
    while len(_SEARCH_RESULT_CACHE_ORDER) > _SEARCH_RESULT_CACHE_MAX:
        old = _SEARCH_RESULT_CACHE_ORDER.pop(0)
        _SEARCH_RESULT_CACHE.pop(old, None)


def _subtitle_pick_mode_setting():
    try:
        raw = str(ADDON.getSetting('subtitle_search_mode') or '').strip().lower()
    except Exception:
        raw = ''
    if 'تشغيل مع ترجمة' in raw or 'with subtitle' in raw or 'with subtitles' in raw or 'play_with_subtitles' in raw:
        return 'play_with_subtitles'
    if 'مع التشغيل' in raw or 'auto' in raw or 'playback' in raw:
        return 'play_with_subtitles'
    # No more runtime prompt. Any legacy/empty/"ask" value falls back to
    # normal playback and is controlled from settings only.
    return 'play'


def _subtitle_search_on_demand_only():
    return _subtitle_pick_mode_setting() != 'play_with_subtitles'


def _preferred_subtitle_lang_keys():
    try:
        raw = str(ADDON.getSetting('preferred_subtitle_langs') or 'ar,en').strip()
    except Exception:
        raw = 'ar,en'
    out = []
    for part in raw.split(','):
        key = _normalize_lang(part)
        if key and key not in out:
            out.append(key)
    return out or ['ar', 'en']


def _playback_provider_signature(ctx=None):
    ctx = ctx or {}
    bits = []
    for key in ('server_type', 'provider_id', 'provider_name', 'provider_base_url', 'stream_url'):
        value = str((ctx or {}).get(key) or '').strip().lower()
        if value:
            bits.append(value)
    return ' '.join(bits)


def _is_plex_like_playback(ctx=None):
    sig = _playback_provider_signature(ctx)
    if not sig:
        return False
    return any(marker in sig for marker in ('plex', 'plexio', 'emby', 'jellyfin', 'streambridge', 'dexbridge'))


def _pick_default_subtitle_index(subtitles, ctx=None):
    rows = list(subtitles or [])
    if not rows:
        return -1
    prefs = _preferred_subtitle_lang_keys()

    def _lang_rank(sub):
        key = _normalize_lang(sub.get('lang') or sub.get('languageCode') or sub.get('language') or 'und')
        base = (key.split('-')[0] if key else '').lower()
        for idx, pref in enumerate(prefs):
            pref_key = _normalize_lang(pref)
            pref_base = (pref_key.split('-')[0] if pref_key else '').lower()
            if key == pref_key or (base and base == pref_base):
                return idx
        return len(prefs) + 10

    best_idx = 0
    best_key = None
    for idx, sub in enumerate(rows):
        sort_key = (
            0 if (sub.get('selected') or sub.get('default')) else 1,
            _lang_rank(sub),
            1 if sub.get('forced') else 0,
            idx,
        )
        if best_key is None or sort_key < best_key:
            best_idx = idx
            best_key = sort_key
    return best_idx


def _resume_success_threshold(target_seconds):
    try:
        target = max(0.0, float(target_seconds or 0.0))
    except Exception:
        target = 0.0
    if target <= 10.0:
        return max(1.0, target - 1.5)
    if target <= 60.0:
        return max(3.0, target - 5.0)
    return max(10.0, target * 0.5)


def _force_remote_posters_enabled(value=''):
    return str(value or '').strip().lower() in ('1', 'true', 'yes', 'remote', 'tmdb', 'trakt')


def _force_remote_query(force_remote=False):
    return {'force_remote': '1'} if force_remote else {}


def _page_slice(rows, page='0'):
    try:
        page_num = max(0, int(page or 0))
    except Exception:
        page_num = 0
    size = _listing_page_size()
    start = page_num * size
    end = start + size
    total = len(rows or [])
    return page_num, size, (rows or [])[start:end], end < total


def _apply_unique_ids(item, ids, info=None):
    ids = ids or {}
    imdb_id = ids.get('imdb_id') or ''
    tmdb_id = ids.get('tmdb_id') or ''
    tvdb_id = ids.get('tvdb_id') or ''
    if info is not None and imdb_id and not info.get('imdbnumber'):
        info['imdbnumber'] = imdb_id
    try:
        if imdb_id:
            item.setProperty('imdb_id', imdb_id)
            item.setProperty('IMDBNumber', imdb_id)
        if tmdb_id:
            item.setProperty('tmdb_id', tmdb_id)
        if tvdb_id:
            item.setProperty('tvdb_id', tvdb_id)
        unique_ids = {}
        if imdb_id:
            unique_ids['imdb'] = imdb_id
        if tmdb_id:
            unique_ids['tmdb'] = tmdb_id
        if tvdb_id:
            unique_ids['tvdb'] = tvdb_id
        if unique_ids and hasattr(item, 'setUniqueIDs'):
            item.setUniqueIDs(unique_ids, 'imdb' if imdb_id else ('tmdb' if tmdb_id else 'tvdb'))
    except Exception:
        pass


# Module-level buffer for the current plugin invocation. Each entry is
# (url, ListItem, isFolder). We flush via addDirectoryItems() in end_dir()
# to make ONE IPC call to Kodi instead of N separate addDirectoryItem calls
# — significantly faster for catalog pages with 30+ items.
_PENDING_ITEMS = []
_META_MEM = {}


def _meta_mem_key(media_type, canonical_id, source_provider_id=''):
    return '%s:%s:%s' % (media_type or '', canonical_id or '', _meta_cache_discriminator(source_provider_id))


def _meta_mem_get(media_type, canonical_id, source_provider_id=''):
    key = _meta_mem_key(media_type, canonical_id, source_provider_id)
    row = _META_MEM.get(key)
    if not row:
        return None
    saved_at, payload = row
    if (time.time() - saved_at) > max(60, int(meta_ttl() or 3600)):
        _META_MEM.pop(key, None)
        return None
    return dict(payload or {})


def _meta_mem_put(media_type, canonical_id, payload, source_provider_id=''):
    if not payload:
        return
    _META_MEM[_meta_mem_key(media_type, canonical_id, source_provider_id)] = (time.time(), dict(payload))


def _favorite_properties(is_favorite=None):
    # Skin quirk fix: some skins draw a heart overlay if the standard
    # IsFavorite/IsFavourite property EXISTS at all, even when its value is
    # 'false'. Only publish the standard properties for real favorites.
    if not bool(is_favorite):
        return {}
    return {
        'IsFavorite': 'true',
        'IsFavourite': 'true',
        'DexHub.IsFavorite': 'true',
        'DexHub.IsFavourite': 'true',
    }





def _art_value_looks_rating_proxy(value):
    text = str(value or '').lower()
    return any(token in text for token in (
        'easyratingsdb.com', 'easyratingsdb', 'erdb',
        'ratingposterdb.com', 'rating-poster', 'ratingposter', 'rpdb',
        'poster-ratings', 'ratings-poster'
    ))


def _art_value_looks_overlay_proxy(value):
    text = str(value or '').lower()
    return _art_value_looks_rating_proxy(text) or any(token in text for token in (
        'plexio', 'plexbridge', 'plex.dexworld', 'plexio.dexworld',
        'sb.dexworld', 'dexbridge',
        '/:/transcode', 'composite', 'overlay', 'photo/:/transcode',
        '/photo/', '/composite/',
        '/items/', '/emby/', '/jellyfin/',
    ))


def _normalize_kodi_item_art(art):
    """Mirror fragile overlay posters to the art keys Kodi skins commonly read.

    Important: do not mirror poster into fanart. ERDB/Plexio may provide a
    separate backdrop, and copying the vertical poster there changes the
    background. Only fill poster-like slots.
    """
    if not art:
        return art
    out = dict(art)
    poster = out.get('poster') or out.get('tvshow.poster') or out.get('season.poster') or out.get('thumb') or out.get('icon')
    if poster:
        out.setdefault('poster', poster)
        out.setdefault('tvshow.poster', poster)
        out.setdefault('season.poster', poster)
        out.setdefault('thumbnail', poster)
        out.setdefault('cover', poster)
        out.setdefault('image', poster)
        out.setdefault('tvshow.thumb', poster)
        if _art_value_looks_overlay_proxy(poster):
            out['thumb'] = poster
            out['icon'] = poster
            out['thumbnail'] = poster
            out['cover'] = poster
            out['image'] = poster
            out['tvshow.thumb'] = poster
        else:
            out.setdefault('thumb', poster)
            out.setdefault('icon', poster)
    return out

def add_item(label, path, is_folder=True, info=None, art=None, properties=None, label2=None, ids=None, context_menu=None, is_favorite=None):
    label = tr(label)
    label2 = tr(label2 or '') if label2 else ''
    item = xbmcgui.ListItem(label=label, label2=label2)
    art = _normalize_kodi_item_art(art)
    info = dict(info or {})
    for _k in ('title', 'plot', 'genre', 'tagline', 'status'):
        if isinstance(info.get(_k), str):
            info[_k] = tr(info.get(_k))
    _apply_unique_ids(item, ids, info)
    if info:
        try:
            item.setInfo('video', info)
        except Exception:
            pass
    if art:
        try:
            item.setArt(art)
        except Exception:
            pass
    fanart_image = (art or {}).get('fanart') or (art or {}).get('landscape') or (art or {}).get('poster') or addon_fanart()
    props = {'fanart_image': fanart_image}
    try:
        if (not is_folder) and 'action=play_item' in str(path or ''):
            props.setdefault('IsPlayable', 'true')
    except Exception:
        pass
    if art:
        for art_key in ('clearlogo', 'logo', 'tvshow.clearlogo', 'clearart', 'landscape', 'banner', 'poster', 'tvshow.poster', 'season.poster', 'thumb', 'icon', 'thumbnail', 'cover', 'image', 'tvshow.thumb', 'fanart'):
            if art.get(art_key):
                props[art_key] = art.get(art_key)
    props.update(_favorite_properties(is_favorite))
    if properties:
        props.update(properties)
    try:
        item.setProperties(props)
    except Exception:
        pass
    if context_menu:
        try:
            # replaceItems=True so we OWN the menu. Previously False appended
            # to Kodi's defaults, which on some skins (Aura, Arctic Fuse,
            # Estuary MOD) injects a built-in 'Add to favourites' that the
            # skin then renders as a persistent heart overlay on EVERY
            # poster — making the heart meaningless as a "this is favourited"
            # marker. Replacing the menu also gives us full control over
            # the available actions.
            item.addContextMenuItems([(tr(lbl), act) for (lbl, act) in list(context_menu)], replaceItems=True)
        except Exception:
            pass
    _PENDING_ITEMS.append((path, item, is_folder))


def _apply_sort_methods(content=None):
    # Issue #8 fix: Kodi remembers the user's last sort choice for a path. If
    # they accidentally tap "Sort by name" once, every catalog page in the
    # addon opens alphabetical from then on. Solution: don't register the
    # alphabetical sort at all on listing pages — Kodi can only fall back to
    # one of OUR registered methods. UNSORTED is first → it becomes the
    # default and the addon's natural order (newest-first for almost every
    # Stremio catalog) is preserved as "last release" feel.
    methods = [xbmcplugin.SORT_METHOD_UNSORTED]
    if content in ('movies', 'tvshows', 'episodes', 'seasons'):
        methods.extend([
            xbmcplugin.SORT_METHOD_VIDEO_YEAR,
            xbmcplugin.SORT_METHOD_VIDEO_RATING,
            xbmcplugin.SORT_METHOD_DATE,
            xbmcplugin.SORT_METHOD_DURATION,
        ])
    # Allow alphabetical only on non-media listings (provider/category menus).
    if content in (None, 'files', 'addons'):
        methods.append(xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    seen = set()
    for method in methods:
        if method in seen:
            continue
        seen.add(method)
        try:
            xbmcplugin.addSortMethod(HANDLE, method)
        except Exception:
            pass


def _flush_pending_items():
    """Push all buffered items to Kodi in ONE IPC call."""
    global _PENDING_ITEMS
    if not _PENDING_ITEMS:
        return
    try:
        xbmcplugin.addDirectoryItems(HANDLE, _PENDING_ITEMS, len(_PENDING_ITEMS))
    except Exception:
        # Fall back to per-item add if the batch path fails (very rare).
        for path, item, is_folder in _PENDING_ITEMS:
            try:
                xbmcplugin.addDirectoryItem(HANDLE, path, item, isFolder=is_folder)
            except Exception:
                pass
    _PENDING_ITEMS = []


def _meta_mem_clear():
    """Drop ALL cached metas from the in-memory layer.

    Called after the user changes a meta-source mapping so subsequent
    catalog/details renders rebuild the cache with the new source. The disk
    HTTP cache is also flushed by meta_source.set_meta_source_for via
    purge_meta_cache(); this complements that for the post-override layer.
    """
    try:
        _META_MEM.clear()
    except Exception:
        pass


def end_dir(content=None, cache=True):
    if content:
        xbmcplugin.setContent(HANDLE, content)
    _apply_sort_methods(content)
    _flush_pending_items()
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=cache)


def _provider_catalogs(provider, media_type=None):
    catalogs = []
    for catalog in provider.get('manifest', {}).get('catalogs', []):
        if not isinstance(catalog, dict):
            continue
        if media_type and catalog.get('type') != media_type:
            continue
        catalogs.append(catalog)
    return catalogs


def _available_types(provider):
    types = []
    for media_type in provider.get('manifest', {}).get('types') or []:
        if _provider_catalogs(provider, media_type):
            types.append(media_type)
    if types:
        return types
    seen = []
    for catalog in _provider_catalogs(provider):
        media_type = catalog.get('type')
        if media_type and media_type not in seen:
            seen.append(media_type)
    return seen


def _provider_supports_search(provider, media_type=None):
    for catalog in _provider_catalogs(provider, media_type):
        for extra in catalog.get('extra') or []:
            if isinstance(extra, dict) and extra.get('name') == 'search':
                return True
    return False




def _provider_is_rating_proxy(provider):
    provider = provider or {}
    manifest = provider.get('manifest') or {}
    haystack = ' '.join([
        str(provider.get('name') or ''),
        str(provider.get('id') or ''),
        str(provider.get('base_url') or ''),
        str(provider.get('manifest_url') or ''),
        str(manifest.get('name') or ''),
        str(manifest.get('id') or ''),
        str(manifest.get('description') or ''),
    ]).lower()
    return any(h in haystack for h in (
        'easyratingsdb.com', 'easyratingsdb', 'erdb proxy', 'erdb',
        'ratingposterdb.com', 'rating poster', 'ratingposter', 'rpdb'
    ))

def _provider_is_plexio(provider):
    provider = provider or {}
    manifest = provider.get('manifest') or {}
    haystack = ' '.join([
        str(provider.get('name') or ''),
        str(provider.get('id') or ''),
        str(provider.get('base_url') or ''),
        str(provider.get('manifest_url') or ''),
        str(manifest.get('name') or ''),
        str(manifest.get('id') or ''),
        str(manifest.get('description') or ''),
    ]).lower()
    return any(h in haystack for h in ('plexio', 'plexbridge', 'com.stremio.plexio', 'com.stremio.plexbridge', 'sb.dexworld', 'dexbridge'))


def _provider_prefers_native_art(provider):
    provider = provider or {}
    manifest = provider.get('manifest') or {}
    haystack = ' '.join([
        str(provider.get('name') or ''),
        str(provider.get('id') or ''),
        str(provider.get('base_url') or ''),
        str(provider.get('manifest_url') or ''),
        str(manifest.get('name') or ''),
        str(manifest.get('id') or ''),
        str(manifest.get('description') or ''),
    ]).lower()
    # Plex / Emby / Plexio / DexBridge all build poster URLs that include
    # auth tokens or session-bound paths. Kodi's image loader strips query
    # strings, expires the cache aggressively, and chokes on long URLs —
    # so for ANY of these providers we prefer remote (TMDb-based) art.
    return any(h in haystack for h in ('plex', 'plexio', 'emby', 'jellyfin', 'dexbridge'))


_ART_URL_KEYS = (
    'poster', 'thumbnail', 'thumb', 'image', 'posterUrl', 'posterURL',
    'imageUrl', 'imageURL', 'thumbUrl', 'thumbURL', 'background', 'fanart',
    'landscape', 'banner', 'backdrop', 'clearlogo', 'logo', 'clearart',
    'parentThumb', 'grandparentThumb', 'art', 'key'
)


def _provider_origin(provider):
    provider = provider or {}
    for raw in (provider.get('base_url'), provider.get('manifest_url')):
        try:
            parsed = urlparse(str(raw or ''))
            if parsed.scheme and parsed.netloc:
                return '%s://%s' % (parsed.scheme, parsed.netloc)
        except Exception:
            continue
    return ''


def _resolve_provider_art_value(provider, value):
    text = str(value or '').strip()
    if not text:
        return text
    lower = text.lower()
    if lower.startswith(('image://', 'special://', 'file://', 'plugin://', 'smb://', 'nfs://')):
        return text
    if lower.startswith(('http://', 'https://')):
        return text
    origin = _provider_origin(provider)
    if text.startswith('/') and origin:
        try:
            return urljoin(origin + '/', text.lstrip('/'))
        except Exception:
            return origin + text
    return text


def _plex_image_token_from_url(value):
    try:
        qs = parse_qs(urlparse(str(value or '')).query or '')
        return (qs.get('X-Plex-Token') or qs.get('x-plex-token') or qs.get('token') or [''])[0]
    except Exception:
        return ''


def _append_plex_token(url, token):
    text = str(url or '').strip()
    token = str(token or '').strip()
    if not text or not token or 'x-plex-token=' in text.lower():
        return text
    return '%s%sX-Plex-Token=%s' % (text, '&' if '?' in text else '?', token)


def _plex_transcode_original_art(provider, value):
    """Extract the original poster path from Plex /photo/:/transcode URLs.

    PlexMod avoids blank composite posters by decoding Plex's /photo/:/transcode
    wrapper and keeping the original image path as a fallback. Dex Hub does the
    same here, preserving auth tokens when present.
    """
    text = str(value or '').strip()
    if not text:
        return ''
    lower = text.lower()
    if '/:/transcode' not in lower and 'transcode' not in lower and 'composite' not in lower and 'overlay' not in lower:
        return ''
    try:
        parsed = urlparse(text)
        qs = parse_qs(parsed.query or '')
        src = (qs.get('url') or qs.get('thumb') or qs.get('path') or [''])[0]
        if not src:
            return ''
        src = _resolve_provider_art_value(provider, src)
        return _append_plex_token(src, _plex_image_token_from_url(text))
    except Exception:
        return ''


def _plexmod_transcode_url(provider, value, width=500, height=750):
    """Build a PlexMod-style photo transcode URL for a poster candidate.

    PlexMod asks Plex for bounded artwork through /photo/:/transcode using
    width/height/minSize/upscale. That is more reliable for Kodi texture caching
    than raw overlay/composite poster URLs.
    """
    text = _resolve_provider_art_value(provider, value)
    if not text:
        return ''
    lower = text.lower()
    if lower.startswith(('image://', 'special://', 'file://', 'plugin://', 'smb://', 'nfs://')):
        return text
    origin = _provider_origin(provider)
    if not origin:
        return ''
    # Bug fix (3.7.89): only wrap URLs that already point to this provider's
    # host. Wrapping a TMDb/Cinemeta URL inside Plex /photo/:/transcode produces
    # a URL Plex can't resolve, leading to broken posters when the user picked
    # an external metadata source. This is defense-in-depth for the same fix
    # applied at the entry of _normalize_meta_art_urls.
    try:
        url_host = urlparse(text).netloc.lower()
        prov_host = urlparse(origin).netloc.lower()
        if url_host and prov_host and url_host != prov_host:
            return ''
    except Exception:
        return ''
    token = _plex_image_token_from_url(text)
    original = _plex_transcode_original_art(provider, text) or text
    original = _resolve_provider_art_value(provider, original)
    if token:
        original = _append_plex_token(original, token)
    path = '/photo/:/transcode?url=%s&width=%s&height=%s&minSize=1&upscale=1' % (
        quote_plus(original), int(width), int(height)
    )
    if token and 'x-plex-token=' not in path.lower():
        path += '&X-Plex-Token=%s' % token
    return urljoin(origin + '/', path.lstrip('/'))


def _normalize_meta_art_urls(provider, meta):
    """Resolve relative Plex/Emby/Plexio artwork paths and add fallback art.

    Some Stremio-compatible Plex/Plexio catalogs expose images as relative
    paths like /photo/:/transcode?... or as long overlay/composite URLs. Kodi can
    fail those when the origin/query/token is not preserved. This normalizes the
    common fields before they reach the art resolver.
    """
    if not isinstance(meta, dict):
        return meta
    # Bug fix (3.7.89): if the meta has been replaced by an explicit user-picked
    # source (Cinemeta, TMDb Helper, Trakt, etc.), do NOT rewrite its URLs through
    # the provider's host. Otherwise we'd wrap a TMDb/Cinemeta poster inside
    # /photo/:/transcode?url=... which Plex/Plexio cannot resolve, producing
    # broken posters every time the user changes the metadata source.
    sid = str(meta.get('_dexhub_meta_source_id') or '').strip().lower()
    strict = str(meta.get('_dexhub_art_strict') or '').strip().lower() in ('1', 'true', 'yes', 'on')
    if strict or (sid and sid not in ('auto', 'native')):
        return meta
    out = dict(meta)
    for key in _ART_URL_KEYS:
        if key in out and out.get(key):
            out[key] = _resolve_provider_art_value(provider, out.get(key))

    for container_key in ('images', 'behaviorHints'):
        node = out.get(container_key)
        if isinstance(node, dict):
            new_node = dict(node)
            for key, value in list(new_node.items()):
                if isinstance(value, dict):
                    child = dict(value)
                    for ckey, cval in list(child.items()):
                        if isinstance(cval, str) and cval.strip():
                            child[ckey] = _resolve_provider_art_value(provider, cval)
                    new_node[key] = child
                elif isinstance(value, str) and value.strip():
                    new_node[key] = _resolve_provider_art_value(provider, value)
            out[container_key] = new_node

    primary = out.get('poster') or out.get('thumbnail') or out.get('thumb') or out.get('image') or ''

    # Rating/overlay add-ons (ERDB/RPDB/Plexio) already return a composed
    # Stremio-ready poster. Re-wrapping it through Plex /photo/:/transcode can
    # make Kodi show a blank poster or the add-on logo. Keep the supplied
    # vertical poster as the primary image and mirror only to poster-like keys.
    if _provider_is_rating_proxy(provider) or _provider_is_plexio(provider) or _art_value_looks_overlay_proxy(primary):
        if primary:
            out['poster'] = primary
            out['thumb'] = primary
            out['thumbnail'] = primary
            out['icon'] = primary
            out['image'] = primary
            out.setdefault('tvshow.poster', primary)
            out.setdefault('season.poster', primary)
            out.setdefault('tvshow.thumb', primary)
        fallback = _plex_transcode_original_art(provider, primary)
        if fallback:
            out.setdefault('plex_original_poster', fallback)
            out.setdefault('thumb_fallback', fallback)
            out.setdefault('thumbnail_fallback', fallback)
        return out

    fallback = _plex_transcode_original_art(provider, primary)
    transcode = _plexmod_transcode_url(provider, primary)
    if fallback:
        out.setdefault('thumb', fallback)
        out.setdefault('thumbnail', fallback)
        out.setdefault('icon', fallback)
        out.setdefault('plex_original_poster', fallback)
    if transcode:
        if primary:
            out.setdefault('plex_overlay_poster', primary)
        out['poster'] = transcode
        out.setdefault('thumbnail', fallback or transcode)
        out.setdefault('thumb', fallback or transcode)
    return out


def _provider_meta_source_id(provider):
    try:
        provider_id = (provider or {}).get('id') or ''
        source_id = (_meta_source.get_meta_source_for(provider_id) if provider_id else 'auto') or 'auto'
        # Plexio auto must mean Plexio/native artwork, not a hidden TMDb/Cinemeta
        # swap. Explicit picks (TMDb Helper / another metadata addon / native)
        # are still honored below by meta_source.override_* and _resolve_meta_art.
        if source_id == 'auto' and _provider_is_plexio(provider):
            return 'native'
        return source_id
    except Exception:
        return 'auto'


def _provider_uses_explicit_meta_art(provider):
    source_id = _provider_meta_source_id(provider)
    return source_id not in ('', 'auto')


def _meta_art_is_strict(meta):
    return str((meta or {}).get('_dexhub_art_strict') or '').strip().lower() in ('1', 'true', 'yes', 'on')


def _meta_source_id_from_meta(meta):
    return str((meta or {}).get('_dexhub_meta_source_id') or '').strip()


def _target_meta_source_id(target_key):
    try:
        return (_meta_source.get_meta_source_for(target_key) if target_key else 'auto') or 'auto'
    except Exception:
        return 'auto'


def _target_meta_source_is_explicit(target_key):
    return _target_meta_source_id(target_key) not in ('', 'auto')


def _is_virtual_meta_target(target_key):
    return str(target_key or '').strip().startswith('virtual.')


def _source_context_requires_exact_meta(source_provider_id):
    sid = str(source_provider_id or '').strip()
    if not sid:
        return False
    if _is_virtual_meta_target(sid):
        return _target_meta_source_is_explicit(sid)
    try:
        provider = store.get_provider(sid)
    except Exception:
        provider = None
    return _provider_uses_explicit_meta_art(provider or {'id': sid})



def _meta_cache_discriminator(source_provider_id=''):
    try:
        source_map = ADDON.getSetting('provider_meta_map') or '{}'
    except Exception:
        source_map = '{}'
    return '|'.join([
        str(source_provider_id or ''),
        str(source_map or '{}'),
        str(poster_source_mode() or ''),
    ])


def _meta_provider_first(providers, source_provider_id=''):
    providers = [p for p in (providers or []) if p]
    sid = str(source_provider_id or '').strip()
    if not sid:
        return providers
    head = []
    tail = []
    seen = set()
    for p in providers:
        pid = str((p or {}).get('id') or '')
        if not pid or pid in seen:
            continue
        seen.add(pid)
        if pid == sid:
            head.append(p)
        else:
            tail.append(p)
    if not head:
        try:
            p = store.get_provider(sid)
        except Exception:
            p = None
        if p:
            head.append(p)
    return head + tail


def _provider_order_for_id_with_context(media_type, canonical_id, source_provider_id=''):
    return _meta_provider_first(_provider_order_for_id(media_type, canonical_id), source_provider_id=source_provider_id)


def _resolve_meta_art(provider, media_type, meta, fallback_art=None, force_remote=False):
    # If the user explicitly selected a metadata source, the artwork resolver
    # must NOT re-enrich from TMDb/direct afterwards. The meta object reaching
    # this function has already been replaced by meta_source.override_*; render
    # its own artwork exactly as-is. This is what makes "Plexio → Cinemeta",
    # "Plexio → Trakt", or "Plexio → TMDb Helper" affect posters 100%.
    meta_source_id = _meta_source_id_from_meta(meta)
    if _meta_art_is_strict(meta) or (meta_source_id and meta_source_id not in ('auto', 'native')):
        # Strict explicit source: do not even use provider/category fallback art,
        # otherwise Plex/Emby logos/posters leak back when the selected source
        # has no poster. native_meta_art still supplies DexHub's neutral default.
        return native_meta_art(meta, media_type, fallback_art={})
    source_id = _provider_meta_source_id(provider)
    if source_id == 'native':
        return native_meta_art(meta, media_type, fallback_art=fallback_art)
    if source_id not in ('', 'auto'):
        return native_meta_art(meta, media_type, fallback_art={})

    if _provider_is_rating_proxy(provider):
        native = native_meta_art(meta, media_type, fallback_art=fallback_art)
        enriched = enrich_meta_art(meta, media_type, fallback_art=fallback_art)
        # ERDB/RPDB must own the vertical poster, while the backdrop should not
        # be replaced by the vertical overlay poster when a better fanart exists.
        for key in ('poster', 'thumb', 'icon', 'thumbnail', 'cover', 'image', 'tvshow.poster', 'season.poster', 'tvshow.thumb'):
            if native.get(key):
                enriched[key] = native.get(key)
        if native.get('clearlogo'):
            for key in ('clearlogo', 'logo', 'tvshow.clearlogo', 'clearart'):
                if native.get(key):
                    enriched[key] = native.get(key)
        has_native_backdrop = any((meta or {}).get(k) for k in ('background', 'fanart', 'backdrop', 'landscape'))
        if has_native_backdrop:
            for key in ('fanart', 'landscape', 'banner'):
                if native.get(key):
                    enriched[key] = native.get(key)
        return enriched

    if force_remote:
        return enrich_meta_art(meta, media_type, fallback_art=fallback_art)
    # Plexio already returns Stremio-ready poster/background URLs from the
    # configured manifest/catalog/meta route. Treat it like Stremio does and
    # render the addon's native artwork in auto mode; otherwise Kodi may swap
    # to TMDb/Helper or leave the tokenized Plex image unwrapped.
    # However, when the poster is NOT an overlay/composite URL (e.g. plain
    # TMDb poster from catalog), use hybrid art so fanart/clearlogo can still
    # be enriched from remote sources.
    if _provider_is_plexio(provider):
        primary = ''
        for _pk in ('poster', 'posterUrl', 'posterURL', 'thumbnail', 'thumb', 'image'):
            _pv = str(meta.get(_pk) or '').strip()
            if _pv and _pv.lower() not in ('none', 'null', 'n/a', '0'):
                primary = _pv
                break
        if primary and _art_value_looks_overlay_proxy(primary):
            return native_meta_art(meta, media_type, fallback_art=fallback_art)
        return hybrid_meta_art(meta, media_type, fallback_art=fallback_art)
    # Preserve native Plex/Plexio/Emby posters when the user selected
    # "محلي فقط". Their local posters often carry collection/status overlays
    # that disappear when we swap to TMDb art. Tokenized URLs are already
    # wrapped with image:// in native_meta_art(), so they can load reliably.
    if _provider_prefers_native_art(provider):
        if posters_prefer_local():
            return native_meta_art(meta, media_type, fallback_art=fallback_art)
        return enrich_meta_art(meta, media_type, fallback_art=fallback_art)
    if posters_prefer_local():
        return hybrid_meta_art(meta, media_type, fallback_art=fallback_art)
    return enrich_meta_art(meta, media_type, fallback_art=fallback_art)


def _prefer_item_art(art, meta, media_type='movie', fallback_art=None):
    """Merge item-native artwork without breaking the selected art source.

    Remote/TMDb/Trakt art wins when local posters are not preferred; native
    provider art then only fills missing fields. When local posters are enabled,
    native Plex/Emby/Plexio art may override.
    """
    if _meta_art_is_strict(meta):
        merged = dict(art or {})
        if merged.get('clearlogo'):
            merged['logo'] = merged.get('clearlogo')
            merged['tvshow.clearlogo'] = merged.get('clearlogo')
            merged['clearart'] = merged.get('clearlogo')
        return merged
    merged = dict(art or {})
    try:
        native = native_meta_art(meta or {}, media_type, fallback_art=fallback_art or {}) or {}
    except Exception:
        native = {}
    prefer_native = posters_prefer_local()
    for key in ('poster', 'thumb', 'icon', 'fanart', 'landscape', 'banner', 'clearlogo', 'logo', 'tvshow.clearlogo', 'clearart'):
        value = native.get(key)
        if not value:
            continue
        if prefer_native or not merged.get(key):
            merged[key] = value
    if merged.get('clearlogo'):
        merged['logo'] = merged.get('clearlogo')
        merged['tvshow.clearlogo'] = merged.get('clearlogo')
        merged['clearart'] = merged.get('clearlogo')
    if merged.get('poster') and not merged.get('fanart'):
        merged['fanart'] = merged.get('poster')
    if merged.get('fanart') and not merged.get('landscape'):
        merged['landscape'] = merged.get('fanart')
    return merged


def _provider_summary(provider):
    manifest = provider.get('manifest') or {}
    catalogs = _provider_catalogs(provider)
    movie_count = len(_provider_catalogs(provider, 'movie'))
    series_count = len(_provider_catalogs(provider, 'series'))
    parts = []
    if movie_count:
        parts.append('%d Movies catalogs' % movie_count)
    if series_count:
        parts.append('%d Series catalogs' % series_count)
    if _provider_supports_search(provider, 'movie'):
        parts.append('Movie Search')
    if _provider_supports_search(provider, 'series'):
        parts.append('Series Search')
    if not parts and catalogs:
        parts.append('%d catalogs' % len(catalogs))
    return ' • '.join(parts) or (manifest.get('description') or provider.get('manifest_url') or '')


def _group_title(media_type):
    return 'أفلام' if media_type == 'movie' else 'مسلسلات' if media_type == 'series' else media_type


def _item_fallback_art(provider=None, media_type='movie', catalog=None, name=''):
    provider = provider or {}
    manifest = provider.get('manifest') or {}
    pname = provider.get('name') or manifest.get('name') or 'Provider'
    base_art = provider_art(pname, manifest, base_url=provider.get('base_url') or '')
    # Use the addon/provider poster for catalog items when item art is missing.
    # Category icons like 4K/search are fine for catalog folders, but not for movie/series posters.
    if catalog:
        cat_art = catalog_art(name or catalog.get('name') or catalog.get('id') or media_type, media_type, manifest, catalog)
        merged = dict(base_art)
        # Keep fanart/background hints from the catalog when available, but poster/icon from provider.
        for key in ('fanart', 'landscape', 'banner'):
            if cat_art.get(key):
                merged[key] = cat_art.get(key)
        return merged
    return base_art


def _content_background(art=None, fallback=None):
    art = art or {}
    fallback = fallback or {}
    return (
        art.get('fanart') or art.get('landscape') or art.get('banner') or art.get('poster') or art.get('thumb') or
        fallback.get('fanart') or fallback.get('landscape') or fallback.get('poster') or fallback.get('thumb') or
        addon_fanart()
    )


def home():
    win = xbmcgui.Window(WINDOW_ID)
    # Clear stale one-shot handoff/source properties. Keep OSD artwork while video is active.
    _clear_tmdbh_transient()
    _clear_source_transient_props(clear_global=True)
    for key in ('dexhub.catalog_extra_name', 'dexhub.catalog_extra_value', 'dexhub.catalog_skip_gate'):
        try:
            win.clearProperty(key)
        except Exception:
            pass

    # Read + consume the CW stale flag set by companion._refresh_cw_containers
    # after each playback save. When set, we tell Kodi NOT to cache this
    # directory listing so the user sees the updated CW row immediately
    # — critical fix for "finished an episode but Continue Watching still
    # shows old progress" in 3.7.66.
    cw_dirty = False
    try:
        if win.getProperty('dexhub.cw_dirty') == '1':
            cw_dirty = True
            win.clearProperty('dexhub.cw_dirty')
            win.clearProperty('dexhub.cw_dirty_ts')
    except Exception:
        pass

    rows = store.list_providers()
    sets = _collections_mod.list_sets()

    # Single call to playback_store: one sqlite open/close instead of two.
    # Drives both the fanart slideshow AND the "متابعة المشاهدة (N)" count.
    try:
        cw_items = playback_store.list_continue_items(limit=24) or []
    except Exception:
        cw_items = []
    cw_count = len(cw_items)

    # Fanart slideshow: pick a random background from the recent items.
    if cw_items:
        try:
            import random as _rnd
            picked = _rnd.choice(cw_items[:10])  # from the most recent 10
            bg = picked.get('background') or picked.get('poster') or ''
            if bg:
                win.setProperty('fanart', bg)
        except Exception:
            pass

    # First-run wizard: if user has no providers, suggest some popular ones
    # via a single "Quick start" entry instead of just the Add button.
    if not rows:
        add_item(
            '[COLOR yellow]%s[/COLOR]' % tr('🚀 ابدأ بسرعة — أضف مصادر شائعة'),
            build_url(action='first_run_wizard'),
            art=root_art('add'),
            info={'title': tr('ابدأ بسرعة'), 'plot': tr('أضف Cinemeta + مصادر DexWorld المقترحة بضغطة واحدة')},
        )

    # 1) Add manifest (always first — users need quick access)
    add_item(tr('إضافة رابط Manifest'), build_url(action='add_provider'), art=root_art('add'),
             info={'title': tr('إضافة رابط Manifest'), 'plot': 'أضف رابط manifest.json لأي مصدر متوافق مع Stremio'})

    # 2) Continue watching — uses Trakt logo (it's mostly Trakt progress anyway).
    cw_label = tr('متابعة المشاهدة') if not cw_count else '%s (%d)' % (tr('متابعة المشاهدة'), cw_count)
    add_item(cw_label, build_url(action='continue'), art=root_art('continue'),
             info={'title': cw_label, 'plot': tr('عناصر في منتصف المشاهدة — محلي ومستورد من Trakt')})

    # 2.5) Next Up — for shows you've started, surface the next unwatched
    # episode. Uses Trakt's `/sync/watched/shows` + per-show progress when
    # Trakt is connected; falls back to playback_store-derived next episode
    # otherwise. Hidden from home if the user disabled it.
    if (ADDON.getSetting('show_nextup_home') or 'true').lower() != 'false':
        # Avoid building Next Up on home open — it can be the slowest cold-start
        # path because it may consult Trakt and series episode caches.
        nu_label = 'التالي'
        add_item(nu_label, build_url(action='nextup'), art=root_art('nextup'),
                 info={'title': nu_label, 'plot': tr('الحلقة القادمة من المسلسلات التي بدأتها (Trakt + محلي)')})

    # 2.6) Favorites — Trakt watchlist + local favorites combined.
    if (ADDON.getSetting('show_favorites_home') or 'true').lower() != 'false':
        # Keep home open light: skip counting favorites on every visit.
        fav_label = 'المفضلة'
        add_item(fav_label, build_url(action='favorites'), art=root_art('favorites'),
                 info={'title': fav_label, 'plot': tr('قائمة المراقبة من Trakt + مفضلتك المحلية')})

    # 3) Sources — Stremio-style providers list icon.
    providers_label = tr('المصادر') if not rows else '%s (%d)' % (tr('المصادر'), len(rows))
    add_item(providers_label, build_url(action='providers'), art=root_art('providers'),
             info={'title': providers_label, 'plot': tr('تصفح كل كتالوجات مصادرك')})


    # 4) Collections — dedicated collection icon.
    collections_label = tr('الكوليكشن') if not sets else '%s (%d)' % (tr('الكوليكشن'), len(sets))
    collections_art = root_art('catalogs')
    add_item(collections_label, build_url(action='collection_sets'), art=collections_art,
             info={'title': collections_label, 'plot': tr('مجموعات اختصارات لكتالوجات وقوائم Trakt')})

    # 5) Integrations submenu (Trakt + TMDb Helper + settings link).
    trakt_state = trakt.authorization_status()
    trakt_tag = tr('متصل') if trakt_state == 'connected' else tr('غير متصل')
    if tmdbh_player.has_tmdbhelper():
        tmdbh_tag = 'مسجّل' if tmdbh_player.player_installed() else 'غير مسجّل'
        integ_subtitle = 'Trakt: %s • TMDb Helper: %s' % (trakt_tag, tmdbh_tag)
    else:
        integ_subtitle = 'Trakt: %s' % trakt_tag
    add_item(tr('الحساب والتكامل'), build_url(action='integrations_menu'),
             art=root_art('accounts'),
             info={'title': tr('الحساب والتكامل'), 'plot': integ_subtitle})

    # 6) Settings shortcut on home — direct entry with the gear icon so the
    # user doesn't need to dig into integrations to tweak anything.
    add_item(tr('الإعدادات'), build_url(action='open_settings'),
             is_folder=False, art=root_art('settings'),
             info={'title': tr('الإعدادات'), 'plot': tr('فتح إعدادات Dex Hub')})

    # cache=False when CW was just updated so Kodi serves the fresh listing
    # instead of yesterday's cached directory. See cw_dirty handling at top.
    end_dir(cache=not cw_dirty)


# ─── First-run wizard ─────────────────────────────────────────────────

# Curated list of widely-used Stremio addons. Users can multi-select; the
# wizard walks each selected manifest through validate_manifest + save.
_RECOMMENDED_SOURCES = [
    {
        'name': 'Cinemeta (الميتاداتا الأساسية)',
        'manifest': 'https://v3-cinemeta.strem.io/manifest.json',
        'why': 'يلزم لكل تنزيل آخر — يوفّر بيانات الأفلام والمسلسلات (poster, plot, IMDb)',
        'configure_url': '',
    },
    {
        'name': 'AIOMetadata (ميتاداتا متقدمة)',
        'manifest': '',  # per-user manifest — must be configured first
        'why': 'ميتاداتا غنية من TMDB/TVDB/MAL/Fanart مع كتالوجات قابلة للتخصيص',
        'configure_url': 'https://aiometadata.elfhosted.com/configure',
    },
    {
        'name': 'AIOStreams (روابط متعددة المصادر)',
        'manifest': '',
        'why': 'يجمع روابط من Torrentio + Comet + MediaFusion + غيرها مع فلترة وفرز موحّد',
        'configure_url': 'https://aiostreams.elfhosted.com/configure',
    },
    {
        'name': 'OpenSubtitles v3',
        'manifest': 'https://opensubtitles-v3.strem.io/manifest.json',
        'why': 'إضافة ترجمات مفتوحة بآلاف اللغات',
        'configure_url': '',
    },
    {
        'name': 'DexWorld Plexio',
        'manifest': '',
        'why': 'Plex server catalogs, Continue Watching, Next Up, streams and external subtitles — السيرفر الخاص بك عبر Plexio',
        'configure_url': 'https://plexio.dexworld.cc/',
    },
    {
        'name': 'DexWorld StreamBridge / Emby',
        'manifest': '',
        'why': 'Emby server catalogs, Continue Watching, Next Up, streams and external subtitles — السيرفر الخاص بك عبر StreamBridge',
        'configure_url': 'https://sb.dexworld.cc/',
    },
    {
        'name': 'DexWorld IPTV',
        'manifest': '',
        'why': 'IPTV for Stremio and Kodi — قوائم بث مباشر عبر DexWorld',
        'configure_url': 'https://dexworld.cc/',
    },
    {
        'name': 'DexWorld Subtitles',
        'manifest': '',
        'why': 'External subtitles for Kodi and Stremio — ترجمات خارجية عبر DexWorld',
        'configure_url': 'https://dexworld.cc/subtitles/stremio/configure',
    },
    {
        'name': 'WatchHub (روابط مجانية ومدفوعة)',
        'manifest': 'https://watchhub.strem.io/manifest.json',
        'why': 'يجمع روابط من Netflix/Hulu/Prime وغيرها',
        'configure_url': '',
    },
]


def first_run_wizard():
    """Walk a new user through adding a recommended set of Stremio addons."""
    if store.list_providers():
        if not xbmcgui.Dialog().yesno(
            'Dex Hub',
            tr('لديك مصادر مضافة بالفعل. هل تريد إضافة المصادر المقترحة فوقها؟'),
        ):
            return home()

    # Build labels — mark per-user-configured addons distinctly so the user
    # knows they'll need an extra step (open browser, configure, paste URL).
    labels = []
    for src in _RECOMMENDED_SOURCES:
        prefix = '[COLOR yellow]⚙ يحتاج إعداد[/COLOR] ' if src.get('configure_url') else ''
        labels.append('%s%s — %s' % (tr(prefix), tr(src['name']), tr(src['why'])))

    selected = xbmcgui.Dialog().multiselect(tr('اختر المصادر المراد إضافتها'), labels)
    if not selected:
        return home()

    added = 0
    failed = []
    needs_manual = []
    for idx in selected:
        item = _RECOMMENDED_SOURCES[idx]
        # Per-user addons: prompt the user to open the configure URL in a
        # browser, configure, then paste the resulting manifest URL.
        if item.get('configure_url') and not item.get('manifest'):
            needs_manual.append(item)
            continue
        try:
            manifest = validate_manifest(item['manifest'])
            name = manifest.get('name') or item['name']
            store.add_provider(name=name, manifest_url=item['manifest'], manifest=manifest)
            added += 1
        except Exception as exc:
            xbmc.log('[DexHub] wizard add failed for %s: %s' % (item['manifest'], exc), xbmc.LOGWARNING)
            failed.append(item['name'])

    # Walk per-user addons one at a time.
    for item in needs_manual:
        choice = xbmcgui.Dialog().yesno(
            tr('Dex Hub — %s') % tr(item['name']),
            tr(
                '[B]%s[/B] يحتاج إعداد شخصي:\n\n'
                '1. افتح في متصفح الجهاز:\n'
                '[COLOR yellow]%s[/COLOR]\n\n'
                '2. اضبط مفاتيح API والإعدادات\n'
                '3. انسخ رابط manifest.json الناتج\n'
                '4. اضغط "أضف رابط" وألصق الرابط\n\n'
                'هل لديك الرابط جاهز؟'
            ) % (tr(item['name']), item['configure_url']),
            nolabel=tr('تخطّي'), yeslabel=tr('أضف رابط'),
        )
        if not choice:
            continue
        kb = xbmc.Keyboard('', tr('ألصق رابط manifest.json الخاص بـ %s') % tr(item['name']))
        kb.doModal()
        if not kb.isConfirmed():
            continue
        url = kb.getText().strip()
        if not url:
            continue
        try:
            manifest = validate_manifest(url)
            name = manifest.get('name') or item['name']
            store.add_provider(name=name, manifest_url=url, manifest=manifest)
            added += 1
        except Exception as exc:
            xbmc.log('[DexHub] wizard manual-add failed for %s: %s' % (url, exc), xbmc.LOGWARNING)
            failed.append(item['name'])

    if added:
        notify('تمت إضافة %d مصدر' % added)
    if failed:
        error('فشل إضافة: %s' % ', '.join(failed))
    return home()


def dexworld_info():
    """Show public DexWorld service links without embedding private manifests."""
    msg = tr(
        '[B]DexWorld Services[/B]\n\n'
        'Plexio / Plex: https://plexio.dexworld.cc/\n'
        'StreamBridge / Emby: https://sb.dexworld.cc/\n'
        'IPTV: https://dexworld.cc/\n'
        'Subtitles: https://dexworld.cc/subtitles/stremio/configure\n\n'
        'الميزات: كتالوجات، متابعة المشاهدة، Next Up، روابط تشغيل، IPTV، وترجمات خارجية لكودي وستريميو.\n\n'
        'للحصول على تجربة مجانية للاشتراك أو الدعم تواصل عبر تيليجرام: [COLOR yellow]@a6ahd[/COLOR]\n\n'
        'بعد إنشاء أي خدمة انسخ رابط manifest.json الخاص بك وأضفه من: إضافة رابط Manifest.'
    )
    xbmcgui.Dialog().ok(tr('DexWorld — تجربة مجانية ودعم'), msg)
    return home()


def integrations_menu():
    """Second-level menu for Trakt + TMDb Helper + addon settings."""
    # Trakt block
    state = trakt.authorization_status()
    status_word = {'connected': 'متصل', 'ready': 'جاهز للربط', 'needs_api': 'يحتاج API'}.get(state, state or '—')
    add_item('Trakt • %s' % status_word, build_url(action='trakt_menu'), art=root_art('trakt'),
             info={'title': 'Trakt', 'plot': 'ربط/فصل، استيراد التقدم، سجل المشاهدة، قوائمك'})

    # TMDb Helper block (only if installed).
    if tmdbh_player.has_tmdbhelper():
        if tmdbh_player.player_installed():
            add_item('TMDb Helper • مسجّل ✓',
                     build_url(action='tmdbh_install'), is_folder=False,
                     art=root_art('tmdb'),
                     info={'title': 'TMDb Helper', 'plot': 'Dex Hub مسجّل كمشغّل — اضغط لإعادة التسجيل/التحديث بدون دخول الإعدادات'},
                     context_menu=[('إلغاء تسجيل Dex Hub من TMDb Helper', 'RunPlugin(%s)' % build_url(action='tmdbh_uninstall'))])
        else:
            add_item('TMDb Helper • غير مسجّل',
                     build_url(action='tmdbh_install'), is_folder=False,
                     art=root_art('tmdb'),
                     info={'title': 'TMDb Helper', 'plot': 'اضغط لتسجيل Dex Hub كمشغّل'})
    else:
        add_item('[COLOR grey]TMDb Helper غير مثبّت[/COLOR]', build_url(action='integrations_menu'), is_folder=False,
                 art=root_art('tmdb'))

    # Metadata sources sub-menu.
    add_item('مصادر الميتاداتا',
             build_url(action='meta_sources_menu'),
             is_folder=True,
             art=root_art('catalogs'),
             info={'title': 'مصادر الميتاداتا', 'plot': 'اختر مصدر البيانات لكل نوع (أفلام/مسلسلات/أنمي)'})

    # Addon settings shortcut.
    add_item('الإعدادات', build_url(action='open_settings'), is_folder=False,
             art=root_art('settings'),
             info={'title': 'الإعدادات', 'plot': 'فتح إعدادات Dex Hub'})
    end_dir()


def meta_sources_menu():
    """Per-provider metadata source picker.

    Shows every registered provider with its currently-configured meta source.
    User picks a provider → gets a select dialog of available meta sources.
    """
    try:
        from . import meta_source as _meta_source
    except Exception as exc:
        error('meta_source module missing: %s' % exc)
        return end_dir()

    providers = store.list_providers() or []
    if not providers:
        add_item('[COLOR grey]لا توجد مصادر — أضف رابط manifest أولًا[/COLOR]',
                 build_url(action='add_provider'),
                 is_folder=True, art=root_art('add'))
        end_dir()
        return

    add_item('[COLOR yellow]ℹ كل إضافة تختار لها مصدر ميتاداتا مستقل[/COLOR]',
             build_url(action='meta_sources_menu'),
             is_folder=False, art=root_art('catalogs'),
             info={'title': 'مصادر الميتاداتا', 'plot': 'تلقائي = ذكي (Plex/Emby يُستبدل، الباقي يبقى أصلي)'})

    for prov in providers:
        pid = prov.get('id') or ''
        name = prov.get('name') or pid or 'Provider'
        current = _meta_source.get_meta_source_for(pid)
        source_label = _meta_source.source_display_name(current)
        # Visual hint: Plex/Emby providers get a ⚠ if still on "native".
        hint = ''
        if _meta_source.provider_is_stream_only(prov) and current == 'native':
            hint = ' [COLOR orange]⚠[/COLOR]'
        label = '%s → %s%s' % (name, source_label, hint)
        add_item(label,
                 build_url(action='meta_pick_for_provider', provider_id=pid),
                 is_folder=True,
                 art=provider_art(name, prov.get('manifest') or {}, base_url=prov.get('base_url') or ''),
                 info={'title': name, 'plot': 'اضغط لتغيير مصدر الميتاداتا لهذه الإضافة'})

    add_item('[COLOR grey]─ إعادة ضبط الكل إلى "تلقائي" ─[/COLOR]',
             'RunPlugin(%s)' % build_url(action='meta_reset_all'),
             is_folder=False,
             art=root_art('providers'))
    end_dir()


def meta_pick_for_provider(provider_id=''):
    """Show a select dialog of available meta sources for one provider."""
    if not provider_id:
        return
    provider = store.get_provider(provider_id)
    if not provider:
        error('الإضافة غير موجودة')
        return
    return _meta_pick_target(provider_id, 'ميتاداتا %s' % (provider.get('name') or provider_id))


def meta_reset_all():
    try:
        from . import meta_source as _meta_source
        _meta_source.clear_meta_map()
        _meta_mem_clear()
        notify('تم إعادة الضبط')
    except Exception as exc:
        error('فشل: %s' % exc)
    xbmc.executebuiltin('Container.Refresh')


def _virtual_meta_targets():
    return [
        ('virtual.continue.movie', 'متابعة المشاهدة • أفلام'),
        ('virtual.continue.series', 'متابعة المشاهدة • مسلسلات/أنمي'),
        ('virtual.collection.trakt', 'الكوليكشن • عناصر Trakt'),
    ]


def _meta_pick_target(target_key='', title=''):
    try:
        from . import meta_source as _meta_source
    except Exception as exc:
        error('meta_source missing: %s' % exc)
        return
    if not target_key:
        return
    sources = _meta_source.list_available_meta_sources()
    provider = store.get_provider(target_key)
    if provider:
        sources = [s for s in sources if s.get('id') != target_key]
        title = title or (provider.get('name') or target_key)
    labels = [s.get('name') or s.get('id') or 'Source' for s in sources]
    current = _meta_source.get_meta_source_for(target_key)
    preselect = 0
    for idx, src in enumerate(sources):
        if src.get('id') == current:
            preselect = idx
            break
    choice = xbmcgui.Dialog().select(tr(title or 'اختر مصدر الميتاداتا'), [tr(x) for x in labels], preselect=preselect)
    if choice < 0:
        return
    picked = sources[choice]
    _meta_source.set_meta_source_for(target_key, picked.get('id') or 'auto')
    # Drop the in-memory meta cache layer so the next catalog/detail render
    # actually re-applies the override path. The HTTP cache is purged by
    # set_meta_source_for; _META_MEM still holds POST-override metas keyed by
    # the previous discriminator — it's already unreachable, but clearing
    # frees the memory immediately and prevents accidental re-use under any
    # future code path that might key by something other than the full map.
    _meta_mem_clear()
    notify('%s → %s' % (title or target_key, picked.get('name') or picked.get('id') or ''))
    try:
        xbmc.executebuiltin('Container.Refresh')
    except Exception:
        pass


def meta_sources_dialog():
    try:
        from . import meta_source as _meta_source
    except Exception as exc:
        error('meta_source missing: %s' % exc)
        return
    rows = []
    for prov in store.list_providers() or []:
        pid = prov.get('id') or ''
        if not pid:
            continue
        current = _meta_source.source_display_name(_meta_source.get_meta_source_for(pid))
        rows.append((pid, '%s → %s' % (prov.get('name') or pid, current), prov.get('name') or pid))
    for key, label in _virtual_meta_targets():
        current = _meta_source.source_display_name(_meta_source.get_meta_source_for(key))
        rows.append((key, '%s → %s' % (label, current), label))
    if not rows:
        error('لا توجد مصادر بعد')
        return
    choice = xbmcgui.Dialog().select(tr('إدارة مصادر الميتاداتا'), [tr(row[1]) for row in rows])
    if choice < 0:
        return
    target_key, _label, title = rows[choice]
    return _meta_pick_target(target_key, title)


def open_settings_action():
    open_addon_settings()


def add_provider():
    keyboard = xbmc.Keyboard('', tr('ألصق رابط manifest.json'))
    keyboard.doModal()
    if not keyboard.isConfirmed():
        return end_dir()
    manifest_url = keyboard.getText().strip()
    if not manifest_url:
        return end_dir()
    try:
        manifest = validate_manifest(manifest_url)
        name = manifest.get('name') or manifest.get('id') or 'Provider'
        store.add_provider(name=name, manifest_url=manifest_url, manifest=manifest)
        notify('تمت إضافة المصدر: %s' % name)
    except Exception as exc:
        error('فشل إضافة المصدر: %s' % exc)
    return providers()


def providers():
    rows = store.list_providers()
    if not rows:
        add_item('لا توجد مصادر. أضف رابط manifest أولًا', build_url(action='add_provider'), art=root_art('add'))
        return end_dir()
    add_item('[COLOR yellow]+ إضافة مصدر جديد[/COLOR]', build_url(action='add_provider'), art=root_art('add'))

    # Identify providers whose stored manifest has no usable logo.
    # Refresh their manifests in the background so the NEXT open
    # shows the correct icon (CDN Plex servers often serve the logo URL
    # from a different base than the manifest URL, and the first save may
    # have caught a 503 / empty response).
    def _bg_refresh_missing_logos(stale_rows):
        for row in stale_rows:
            try:
                murl = row.get('manifest_url') or ''
                if not murl:
                    continue
                fresh = validate_manifest(murl)
                if not fresh:
                    continue
                logo = (fresh.get('logo') or fresh.get('icon') or '').strip()
                if logo:
                    store.refresh_provider_manifest(row.get('id'), fresh)
            except Exception as exc:
                xbmc.log('[DexHub] manifest logo refresh failed for %s: %s' % (
                    row.get('name', ''), exc), xbmc.LOGDEBUG)

    stale = [r for r in rows
             if not (r.get('manifest') or {}).get('logo')
             and not (r.get('manifest') or {}).get('icon')]
    if stale:
        import threading
        threading.Thread(target=_bg_refresh_missing_logos,
                         args=(stale,), name='DexHubLogoRefresh', daemon=True).start()

    for row in rows:
        label = row.get('name') or row.get('id')
        meta = row.get('manifest') or {}
        plot = meta.get('description') or row.get('manifest_url') or ''
        ctx_menu = [
            ('تغيير مصدر الميتاداتا', 'RunPlugin(%s)' % build_url(action='meta_pick_for_provider', provider_id=row.get('id'))),
            ('تحديث هذا المصدر', 'RunPlugin(%s)' % build_url(action='refresh_provider', provider_id=row.get('id'))),
            ('إزالة هذا المصدر', 'RunPlugin(%s)' % build_url(action='remove_provider', provider_id=row.get('id'))),
            ('فتح الفلاتر والأصناف', 'Container.Update(%s)' % build_url(action='provider_menu', provider_id=row.get('id'))),
        ]
        add_item(label, build_url(action='provider_menu', provider_id=row.get('id')),
                 info={'title': label, 'plot': plot},
                 art=provider_art(label, row.get('manifest') or {}, base_url=row.get('base_url') or ''),
                 context_menu=ctx_menu)
    end_dir()


def provider_menu(provider_id):
    provider = store.get_provider(provider_id)
    if not provider:
        return end_dir()
    pname = provider.get('name') or 'Provider'
    summary = _provider_summary(provider)

    for catalog in _provider_catalogs(provider):
        cname = catalog.get('name') or catalog.get('id') or 'Catalog'
        media_type = catalog.get('type')
        plot = catalog.get('description') or ('تصفح قسم %s' % cname)
        extras = [x.get('name') for x in (catalog.get('extra') or []) if isinstance(x, dict) and x.get('name') not in ('skip',)]
        if extras:
            plot += '\nExtras: ' + ', '.join(extras)
        catalog_url = build_url(action='catalog', provider_id=provider_id, media_type=media_type, catalog_id=catalog.get('id'), label=cname)
        all_url = build_url(action='catalog_all', provider_id=provider_id, media_type=media_type, catalog_id=catalog.get('id'), label=cname)
        filters_url = build_url(action='filters_menu', provider_id=provider_id, media_type=media_type, catalog_id=catalog.get('id'))
        ctx_menu = [
            ('عرض كل العناصر (بدون تصفية)', 'Container.Update(%s)' % all_url),
            ('فتح الفلاتر والفرز', 'Container.Update(%s)' % filters_url),
            ('عرض كمجلدات/أصناف', 'Container.Update(%s)' % catalog_url),
            ('تغيير مصدر الميتاداتا', 'RunPlugin(%s)' % build_url(action='meta_pick_for_provider', provider_id=provider_id)),
        ]
        add_item(
            cname,
            catalog_url,
            info={'title': cname, 'plot': plot},
            art=catalog_art(cname, media_type, provider.get('manifest') or {}, catalog),
            context_menu=ctx_menu,
        )

    for media_type in _available_types(provider):
        if _provider_supports_search(provider, media_type):
            s_label = 'بحث %s' % _group_title(media_type)
            add_item(s_label, build_url(action='search', media_type=media_type, provider_id=provider_id), info={'title': s_label, 'plot': 'بحث داخل %s' % pname}, art=root_art('search_movie' if media_type == 'movie' else 'search_series'))

    add_item('تحديث المانيفست', build_url(action='refresh_provider', provider_id=provider_id), art=root_art('providers'), info={'title': 'تحديث المانيفست', 'plot': summary})
    add_item('حذف المصدر', build_url(action='remove_provider', provider_id=provider_id), art=root_art('add'))
    end_dir()


def remove_provider(provider_id):
    provider = store.get_provider(provider_id)
    if provider and xbmcgui.Dialog().yesno('Dex Hub', tr('حذف المصدر: %s ؟') % provider.get('name')):
        store.remove_provider(provider_id)
        notify('تم حذف المصدر')
    return providers()


def _meta_info(meta):
    year = None
    release = meta.get('releaseInfo') or meta.get('year') or ''
    premiered = ''
    if release:
        release_str = str(release)
        m = YEAR_RE.search(release_str)
        if m:
            try:
                year = int(m.group(1))
            except Exception:
                year = None
        m2 = re.search(r'(\d{4}-\d{2}-\d{2})', release_str)
        if m2:
            premiered = m2.group(1)
    title = meta.get('name') or 'Unknown'
    info = {
        'title': title,
        'sorttitle': title,
        'plot': meta.get('description') or meta.get('overview') or '',
        'year': year or 0,
        'genre': ' / '.join(meta.get('genres') or []),
        'rating': float(meta.get('imdbRating') or 0.0),
        'premiered': premiered,
        'date': premiered,
        'mediatype': 'tvshow' if meta.get('type') == 'series' else 'movie',
    }
    ids = extract_ids(meta)
    if ids.get('imdb_id'):
        info['imdbnumber'] = ids['imdb_id']
    return info


def _enrich_listing_meta(provider, media_type, meta):
    if _provider_prefers_native_art(provider):
        return meta
    if ADDON.getSettingBool('deep_meta_enrich'):
        try:
            full = fetch_meta(provider, media_type, meta.get('id'), timeout_override=fast_timeout('meta'))
            deep = full.get('meta') or {}
            if deep:
                merged = dict(meta)
                merged.update({k: v for k, v in deep.items() if v not in (None, '', [], {})})
                return merged
        except Exception:
            pass
    return meta


def _enrich_listing_metas_batch(provider, media_type, metas):
    """Parallel version of _enrich_listing_meta for a whole catalog page.

    Skips items that already have a poster + a plot/description in the
    listing payload — those don't need a /meta/ fetch round-trip.

    For Plex/Emby/Plexio providers, transparently swap metadata for a
    reliable source (Cinemeta/TMDB meta addons or TMDb Helper) based on
    the `meta_source_mode` setting — fixes broken posters and incomplete
    plots.
    """
    # Meta source override: Plex/Emby providers get their metadata
    # upgraded before the normal enrich path runs.
    meta_source_id = 'auto'
    try:
        from . import meta_source as _meta_source
        meta_source_id = _meta_source.get_meta_source_for((provider or {}).get('id') or '') or 'auto'
        metas = _meta_source.override_metas_batch(provider, media_type, metas)
    except Exception as exc:
        xbmc.log('[DexHub] meta override failed: %s' % exc, xbmc.LOGWARNING)

    metas = [_normalize_meta_art_urls(provider, m) for m in (metas or [])]
    # Explicit source must remain explicit. Do not fetch/merge the original
    # provider's /meta after the user picked TMDb Helper/Trakt/Cinemeta/etc.
    if meta_source_id not in ('', 'auto', 'native'):
        return metas
    if _provider_prefers_native_art(provider):
        return metas
    if not ADDON.getSettingBool('deep_meta_enrich') or not metas:
        return metas

    def _fetch_one(meta):
        try:
            full = fetch_meta(provider, media_type, meta.get('id'), timeout_override=fast_timeout('meta'))
            return full.get('meta') or {}
        except Exception:
            return {}

    results = run_parallel(_fetch_one, metas)
    enriched = []
    for meta, (original, deep) in zip(metas, results):
        if isinstance(deep, Exception) or not deep:
            enriched.append(meta)
            continue
        merged = dict(meta)
        merged.update({k: v for k, v in deep.items() if v not in (None, '', [], {})})
        enriched.append(_normalize_meta_art_urls(provider, merged))
    return enriched


def _catalog_definition(provider, catalog_id, media_type):
    for catalog in provider.get('manifest', {}).get('catalogs', []):
        if catalog.get('id') == catalog_id and catalog.get('type') == media_type:
            return catalog
    return {}


def _filter_state(provider_id, catalog_id):
    return dict(store.get_catalog_state(provider_id, catalog_id) or {})


def _available_filter_extras(catalog_def):
    extras = []
    for extra in catalog_def.get('extra') or []:
        if not isinstance(extra, dict):
            continue
        name = extra.get('name')
        if name in ('skip',):
            continue
        extras.append(extra)
    return extras


# Extras that are ordering/sorting/paging — never make sense as folders,
# always show as filters.
_SORT_LIKE_EXTRAS = {'sort', 'sortby', 'orderby', 'order', 'limit', 'search', 'skip'}

# Extras that are natural categories — default to folder view.
_CATEGORY_LIKE_EXTRAS = {'genre', 'year', 'category', 'language', 'country',
                         'network', 'studio', 'contentrating', 'collection', 'type'}


def _extra_mode(name, catalog_def=None):
    """Return 'folder' or 'filter' for a given extra name.

    Rules, in order:
      1. Never-a-folder names (sort/order/limit/...) → filter.
      2. User override via settings (comma lists).
      3. Default classification by name heuristic.
      4. Fallback: filter.
    """
    key = (name or '').strip().lower().replace('_', '').replace('-', '')
    if key in _SORT_LIKE_EXTRAS:
        return 'filter'
    # User overrides
    try:
        force_folder = set(
            s.strip().lower().replace('_', '').replace('-', '')
            for s in ((ADDON.getSetting('extras_as_folder') or '').split(','))
            if s.strip()
        )
        force_filter = set(
            s.strip().lower().replace('_', '').replace('-', '')
            for s in ((ADDON.getSetting('extras_as_filter') or '').split(','))
            if s.strip()
        )
    except Exception:
        force_folder, force_filter = set(), set()
    if key in force_filter:
        return 'filter'
    if key in force_folder:
        return 'folder'
    if key in _CATEGORY_LIKE_EXTRAS:
        return 'folder'
    return 'filter'


def _folder_extras_with_options(catalog_def):
    """Return [(extra_name, [options])] for extras classified as 'folder'
    that actually have an explicit options list in the manifest."""
    out = []
    for extra in (catalog_def.get('extra') or []):
        if not isinstance(extra, dict):
            continue
        name = extra.get('name') or ''
        if _extra_mode(name, catalog_def) != 'folder':
            continue
        opts = [str(o) for o in (extra.get('options') or []) if o not in (None, '')]
        if opts:
            out.append((name, opts))
    return out


def _filter_label(name):
    return FILTER_NAMES.get(name, name)


def _catalog_toolbar(provider, provider_id, media_type, catalog_id, catalog_def, state, force_remote=False):
    extras = _available_filter_extras(catalog_def)
    # Only show toolbar when at least one extra is classified as a filter.
    filter_extras = [e for e in extras if _extra_mode(e.get('name') or '', catalog_def) == 'filter']
    if not filter_extras:
        return
    active = []
    for extra in filter_extras:
        name = extra.get('name')
        if not name:
            continue
        value = (state or {}).get(name)
        if value not in (None, ''):
            active.append('%s: %s' % (_filter_label(name), value))
    # Pretty toolbar entry: uses a leading arrow/badge so it stands out
    # visually from media items.
    if active:
        header = '[COLOR orange]≡ الفرز والتصفية[/COLOR] • [COLOR yellow]%s[/COLOR]' % ' | '.join(active)
        plot = 'الفلاتر الفعّالة:\n— ' + '\n— '.join(active)
    else:
        header = '[COLOR orange]≡ الفرز والتصفية[/COLOR]'
        plot = 'اختر الفرز والتصفية لهذا الكتالوج'
    add_item(
        header,
        build_url(action='filters_menu', provider_id=provider_id, media_type=media_type, catalog_id=catalog_id, **_force_remote_query(force_remote)),
        is_folder=True,
        info={'title': 'الفرز والتصفية', 'plot': plot},
        art=root_art('catalogs'),
        properties={'SpecialSort': 'top'},  # pin to top on skins that honor this
    )


def _apply_catalog_request(provider, media_type, catalog_id, state):
    extra = {}
    for key, value in (state or {}).items():
        if value in (None, ''):
            continue
        extra[key] = value
    if 'limit' not in extra:
        extra['limit'] = str(_listing_page_size())
    return fetch_catalog(provider, media_type, catalog_id, extra=extra)


def _options_for_extra(catalog_def, extra_name):
    """Return the list of explicit options for a named extra, or [] if none."""
    for extra in (catalog_def.get('extra') or []):
        if isinstance(extra, dict) and extra.get('name') == extra_name:
            opts = extra.get('options') or []
            return [str(o) for o in opts if o not in (None, '')]
    return []


def catalog(provider_id, media_type, catalog_id, label='', page='0', genre='', year='', force_remote=''):
    provider = store.get_provider(provider_id)
    if not provider:
        return end_dir()
    force_remote = _force_remote_posters_enabled(force_remote)
    catalog_def = _catalog_definition(provider, catalog_id, media_type)
    state = _filter_state(provider_id, catalog_id)

    # Preset filters from URL (used by "filter folders" below) — non-persistent.
    preset_filters = {}
    if genre:
        preset_filters['genre'] = genre
    if year:
        preset_filters['year'] = year
    # Generic single-extra preset via Window property (set by catalog_extra()).
    try:
        win_now = xbmcgui.Window(WINDOW_ID)
        _xn = win_now.getProperty('dexhub.catalog_extra_name') or ''
        _xv = win_now.getProperty('dexhub.catalog_extra_value') or ''
        if _xn and _xv:
            preset_filters[_xn] = _xv
    except Exception:
        pass

    # Detect filter-as-folder opportunities.
    try:
        show_genre_folders = (ADDON.getSetting('catalog_genre_folders') or 'true').lower() != 'false'
    except Exception:
        show_genre_folders = True
    has_preset = bool(preset_filters)
    # Issue #5: DexWorld Pro internal sub-catalogs should ALWAYS open as
    # folders. Flip the gate on regardless of the global setting and
    # regardless of whether the user already opened the catalog before.
    force_folders = _force_folders_for_provider(provider)
    if force_folders:
        show_genre_folders = True
        try:
            xbmcgui.Window(WINDOW_ID).clearProperty('dexhub.catalog_skip_gate')
        except Exception:
            pass

    if show_genre_folders and not has_preset             and not any(state.get(k) for k in (state or {}))             and xbmcgui.Window(WINDOW_ID).getProperty('dexhub.catalog_skip_gate') != '1':
        folder_extras = _folder_extras_with_options(catalog_def)
        cat_fb = _item_fallback_art(provider, media_type, catalog_def, catalog_def.get('name') or catalog_id)
        folder_art = {
            'thumb': cat_fb.get('poster') or '',
            'poster': cat_fb.get('poster') or '',
            'icon': cat_fb.get('poster') or '',
            'fanart': cat_fb.get('fanart') or addon_fanart(),
        }
        any_folders = False
        for extra_name, opts in folder_extras:
            if extra_name.lower() == 'year' and len(opts) > 40:
                continue
            for opt in opts:
                label_text = opt if extra_name.lower() == 'genre' else '%s: %s' % (_filter_label(extra_name), opt)
                if extra_name.lower() == 'genre':
                    link = build_url(action='catalog', provider_id=provider_id, media_type=media_type,
                                     catalog_id=catalog_id, label=label, genre=opt, **_force_remote_query(force_remote))
                elif extra_name.lower() == 'year':
                    link = build_url(action='catalog', provider_id=provider_id, media_type=media_type,
                                     catalog_id=catalog_id, label=label, year=opt, **_force_remote_query(force_remote))
                else:
                    link = build_url(action='catalog_extra', provider_id=provider_id, media_type=media_type,
                                     catalog_id=catalog_id, label=label, extra_name=extra_name, extra_value=opt,
                                     **_force_remote_query(force_remote))
                add_item(label_text, link, info={'title': label_text}, art=folder_art)
                any_folders = True
        if any_folders:
            _catalog_toolbar(provider, provider_id, media_type, catalog_id, catalog_def, state, force_remote=force_remote)
            # Hide the "show everything unfiltered" escape hatch when folders
            # are mandatory (DexWorld Pro). The user explicitly wants the
            # internal sub-catalogs to always be the entry point.
            if not force_folders:
                add_item(
                    '[COLOR yellow]◉ عرض كل العناصر بدون تصفية[/COLOR]',
                    build_url(action='catalog_all', provider_id=provider_id, media_type=media_type, catalog_id=catalog_id, label=label, **_force_remote_query(force_remote)),
                    art=root_art('catalogs'),
                    info={'title': 'كل العناصر', 'plot': 'تجاوز المجلدات وعرض القائمة الكاملة'},
                )
            end_dir(content='files')
            return

    _catalog_toolbar(provider, provider_id, media_type, catalog_id, catalog_def, state, force_remote=force_remote)
    skip_supported = any(isinstance(x, dict) and x.get('name') == 'skip' for x in (catalog_def.get('extra') or []))
    try:
        page_num = max(0, int(page or 0))
    except Exception:
        page_num = 0
    page_size = _listing_page_size()
    metas = []
    seen_ids = set()
    has_more = False

    request_state = dict(state or {})
    request_state.update(preset_filters)

    if skip_supported:
        request_state['skip'] = str(page_num * page_size)
        try:
            data = _apply_catalog_request(provider, media_type, catalog_id, request_state)
            batch = data.get('metas') or []
        except Exception as exc:
            error('فشل تحميل الكتالوج: %s' % exc)
            return end_dir()
        for meta in batch:
            mid = str((meta or {}).get('id') or '')
            if mid and mid in seen_ids:
                continue
            if mid:
                seen_ids.add(mid)
            metas.append(meta)
        # Client-side cap: many Stremio addons ignore our `limit` param and
        # return fixed-size pages (100 items). Trim to page_size so the
        # user sees the expected 30 — with a "المزيد" button for the rest.
        had_overflow = len(metas) > page_size
        if had_overflow:
            metas = metas[:page_size]
        has_more = len(batch) >= page_size or had_overflow
    else:
        try:
            data = _apply_catalog_request(provider, media_type, catalog_id, request_state)
            batch = data.get('metas') or []
        except Exception as exc:
            error('فشل تحميل الكتالوج: %s' % exc)
            return end_dir()
        all_metas = []
        for meta in batch:
            mid = str((meta or {}).get('id') or '')
            if mid and mid in seen_ids:
                continue
            if mid:
                seen_ids.add(mid)
            all_metas.append(meta)
        page_num, _ps, metas, has_more = _page_slice(all_metas, page_num)

    win = xbmcgui.Window(WINDOW_ID)
    first_fanart = ''
    metas = _enrich_listing_metas_batch(provider, media_type, metas)
    try:
        favorite_keys = favorites_store.favorite_keys()
    except Exception:
        favorite_keys = set()
    for meta in metas:
        meta = _normalize_meta_art_urls(provider, meta)
        meta_id = meta.get('id')
        item_label = meta.get('name') or meta_id or 'Unknown'
        fallback = _item_fallback_art(provider, media_type, catalog_def, meta.get('name') or meta_id or '')
        art = _resolve_meta_art(provider, media_type, meta, fallback_art=fallback, force_remote=force_remote)
        if not first_fanart and art.get('fanart'):
            first_fanart = art.get('fanart')
        try:
            _meta_mem_put(media_type, meta_id, meta, source_provider_id=provider.get('id') or '')
        except Exception:
            pass
        info = _meta_info(meta)
        ids = extract_ids(meta)
        path, path_is_folder = _content_click_path(media_type=media_type, canonical_id=meta_id, title=item_label, tmdb_id=ids.get('tmdb_id') or '', imdb_id=ids.get('imdb_id') or '', tvdb_id=ids.get('tvdb_id') or '', source_provider_id=provider.get('id') or '')
        ctx_menu = _build_source_picker_menu(media_type=media_type, canonical_id=meta_id, title=item_label, source_provider_id=provider.get('id') or '') + _build_player_chooser_menu(
            media_type=media_type,
            canonical_id=meta_id,
            title=item_label,
            tmdb_id=ids.get('tmdb_id') or '',
            imdb_id=ids.get('imdb_id') or '',
            tvdb_id=ids.get('tvdb_id') or '',
            source_provider_id=provider.get('id') or '',
        )
        # NOTE: TMDb Helper is already accessible via "اختيار المشغّل…" above.
        # Adding a separate "فتح في TMDb Helper" entry here caused it to appear
        # twice (once in the chooser dialog, once as a direct item). Removed.
        already_fav = (str(media_type or ''), str(meta_id or '')) in favorite_keys
        if already_fav:
            ctx_menu.append(('إزالة من المفضلة', 'RunPlugin(%s)' % build_url(
                action='fav_remove', media_type=media_type, canonical_id=meta_id,
            )))
        else:
            ctx_menu.append(('إضافة إلى المفضلة', 'RunPlugin(%s)' % build_url(
                action='fav_add', media_type=media_type, canonical_id=meta_id,
                title=item_label, poster=art.get('poster') or '',
                background=art.get('fanart') or '', clearlogo=art.get('clearlogo') or '',
                year=str(info.get('year') or 0),
            )))
        add_item(item_label, path, is_folder=path_is_folder, info=info, art=art, ids=ids, context_menu=ctx_menu, is_favorite=already_fav)
    if first_fanart:
        win.setProperty('fanart', first_fanart)
    if has_more and metas:
        more_args = dict(action='catalog', provider_id=provider_id, media_type=media_type, catalog_id=catalog_id, label=label, page=str(page_num + 1))
        if genre:
            more_args['genre'] = genre
        if year:
            more_args['year'] = year
        if force_remote:
            more_args['force_remote'] = '1'
        more_url = build_url(**more_args)
        add_item('المزيد', more_url, info={'title': 'المزيد', 'plot': 'تحميل المزيد من نتائج هذا الكتالوج'}, art=root_art('catalogs'))
        if skip_supported:
            try:
                import threading as _thr
                def _prefetch():
                    try:
                        next_state = dict(state or {})
                        next_state.update(preset_filters)
                        next_state['skip'] = str((page_num + 1) * page_size)
                        _apply_catalog_request(provider, media_type, catalog_id, next_state)
                    except Exception:
                        pass
                _thr.Thread(target=_prefetch, daemon=True).start()
            except Exception:
                pass
    end_dir(content=_directory_content_for_type(media_type))

def catalog_all(provider_id, media_type, catalog_id, label='', page='0', genre='', year='', force_remote=''):
    """Bypass genre/year folder gate — show the full unfiltered catalog listing."""
    win = xbmcgui.Window(WINDOW_ID)
    win.setProperty('dexhub.catalog_skip_gate', '1')
    try:
        return catalog(provider_id, media_type, catalog_id, label=label, page=page, genre=genre, year=year, force_remote=force_remote)
    finally:
        win.clearProperty('dexhub.catalog_skip_gate')


def catalog_extra(provider_id, media_type, catalog_id, label='', page='0', extra_name='', extra_value='', force_remote=''):
    """Open a catalog with one arbitrary preset extra (used for folder-mode extras
    that aren't specially named genre/year)."""
    # Temporarily store the preset in a Window property, then call catalog with skip-gate.
    win = xbmcgui.Window(WINDOW_ID)
    win.setProperty('dexhub.catalog_extra_name', extra_name or '')
    win.setProperty('dexhub.catalog_extra_value', extra_value or '')
    win.setProperty('dexhub.catalog_skip_gate', '1')
    try:
        return catalog(provider_id, media_type, catalog_id, label=label, page=page, force_remote=force_remote)
    finally:
        win.clearProperty('dexhub.catalog_extra_name')
        win.clearProperty('dexhub.catalog_extra_value')
        win.clearProperty('dexhub.catalog_skip_gate')


def filters_menu(provider_id, media_type, catalog_id, force_remote=''):
    provider = store.get_provider(provider_id)
    if not provider:
        return end_dir()
    catalog_def = _catalog_definition(provider, catalog_id, media_type)
    extras = [e for e in _available_filter_extras(catalog_def)
              if _extra_mode((e.get('name') or ''), catalog_def) == 'filter']
    if not extras:
        return catalog(provider_id, media_type, catalog_id, force_remote=force_remote)
    state = _filter_state(provider_id, catalog_id)
    labels = []
    actions = []
    for extra in extras:
        name = extra.get('name')
        if not name:
            continue
        current = state.get(name)
        labels.append('%s%s' % (_filter_label(name), ('  •  %s' % current) if current not in (None, '') else ''))
        actions.append(('set', name))
    if state:
        labels.append('مسح كل الفلاتر')
        actions.append(('clear', ''))
    idx = xbmcgui.Dialog().select(tr('الفرز والتصفية'), [tr(x) for x in labels])
    if idx < 0:
        return catalog(provider_id, media_type, catalog_id, force_remote=force_remote)
    action, value = actions[idx]
    if action == 'clear':
        store.clear_catalog_filters(provider_id, catalog_id)
        return catalog(provider_id, media_type, catalog_id, force_remote=force_remote)
    return select_filter(provider_id, media_type, catalog_id, value, force_remote=force_remote)


def select_filter(provider_id, media_type, catalog_id, filter_name, force_remote=''):
    provider = store.get_provider(provider_id)
    if not provider:
        return end_dir()
    catalog_def = _catalog_definition(provider, catalog_id, media_type)
    extra_def = None
    for extra in catalog_def.get('extra') or []:
        if isinstance(extra, dict) and extra.get('name') == filter_name:
            extra_def = extra
            break
    if not extra_def:
        return catalog(provider_id, media_type, catalog_id, force_remote=force_remote)

    options = list(extra_def.get('options') or [])
    title = _filter_label(filter_name)
    if options:
        labels = ['إلغاء الفلتر'] + [str(x) for x in options]
        idx = xbmcgui.Dialog().select(tr('اختر %s') % tr(title), [tr(x) for x in labels])
        if idx < 0:
            return catalog(provider_id, media_type, catalog_id, force_remote=force_remote)
        if idx == 0:
            store.set_catalog_filter(provider_id, catalog_id, filter_name, '__clear__')
        else:
            store.set_catalog_filter(provider_id, catalog_id, filter_name, labels[idx])
    else:
        default = _filter_state(provider_id, catalog_id).get(filter_name, '')
        kb = xbmc.Keyboard(default, tr('اكتب %s') % tr(title))
        kb.doModal()
        if not kb.isConfirmed():
            return catalog(provider_id, media_type, catalog_id, force_remote=force_remote)
        value = kb.getText().strip()
        store.set_catalog_filter(provider_id, catalog_id, filter_name, value or '__clear__')
    return catalog(provider_id, media_type, catalog_id, force_remote=force_remote)


def clear_filters(provider_id, media_type, catalog_id, force_remote=''):
    store.clear_catalog_filters(provider_id, catalog_id)
    return catalog(provider_id, media_type, catalog_id, force_remote=force_remote)


def _query_is_id(query):
    q = (query or '').strip().lower()
    return q.startswith('tmdb:') or q.startswith('tt') or q.startswith('imdb:') or q.startswith('tvdb:')


def search(media_type, provider_id=None):
    rows = [store.get_provider(provider_id)] if provider_id else store.list_providers()
    rows = [x for x in rows if x]
    if not rows:
        return providers()
    # Seed keyboard with last search query so users can refine without retyping.
    win = xbmcgui.Window(WINDOW_ID)
    last_key = 'dexhub.last_search.%s' % (media_type or 'any')
    last_query = win.getProperty(last_key) or ''
    keyboard = xbmc.Keyboard(last_query, tr('ابحث أو اكتب tmdb:123 / tt1234567'))
    keyboard.doModal()
    if not keyboard.isConfirmed():
        return end_dir()
    query = keyboard.getText().strip()
    if not query:
        return end_dir()
    win.setProperty(last_key, query)
    seen = {}
    if _query_is_id(query):
        item_label = query
        if media_type == 'series':
            path, path_is_folder = _content_click_path(media_type=media_type, canonical_id=query, title=item_label)
            add_item(item_label, path, is_folder=path_is_folder, info={'title': item_label}, art=catalog_art('search', media_type))
        else:
            path, path_is_folder = _content_click_path(media_type=media_type, canonical_id=query, title=item_label)
            add_item(item_label, path, is_folder=path_is_folder, info={'title': item_label}, art=catalog_art('search', media_type), context_menu=_build_source_picker_menu(media_type=media_type, canonical_id=query, title=item_label))
        return end_dir(content=_directory_content_for_type(media_type), cache=False)

    search_jobs = []
    for provider in rows:
        for cat in _provider_catalogs(provider, media_type):
            searchable = any((x.get('name') == 'search') for x in (cat.get('extra') or []) if isinstance(x, dict))
            if searchable:
                search_jobs.append((provider, cat))

    if not search_jobs:
        return end_dir(content=_directory_content_for_type(media_type), cache=False)

    cache_key = (str(media_type or ''), str(provider_id or ''), query.lower(), _meta_cache_discriminator(provider_id or ''))
    cached_rows = _search_cache_get(cache_key)
    if cached_rows:
        for provider, meta_id, meta in cached_rows:
            item_label = meta.get('name') or meta_id
            try:
                _meta_mem_put(media_type, meta_id, meta, source_provider_id=provider.get('id') or '')
            except Exception:
                pass
            path_action = 'series_meta' if media_type == 'series' else 'play_item'
            fallback = _item_fallback_art(provider, media_type, None, item_label)
            add_item(item_label, build_url(action=path_action, media_type=media_type, canonical_id=meta_id, title=item_label, source_provider_id=provider.get('id') or ''), is_folder=_is_series_media(media_type), info=_meta_info(meta), art=_resolve_meta_art(provider, media_type, meta, fallback_art=fallback), ids=extract_ids(meta), context_menu=_build_source_picker_menu(media_type=media_type, canonical_id=meta_id, title=item_label, source_provider_id=provider.get('id') or ''))
        return end_dir(content=_directory_content_for_type(media_type), cache=False)

    def _run_search(job):
        provider, cat = job
        return fetch_catalog(provider, media_type, cat.get('id'), extra={'search': query, 'limit': str(_listing_page_size())}, timeout_override=fast_timeout('search'))

    # Issue: previously we early-stopped at ~30 results, which in practice
    # meant only the FIRST provider returned anything. Users with multiple
    # sources (Cinemeta + Plexio + Plex + custom catalogs) only saw results
    # from one. Now we query EVERY searchable catalog in parallel batches
    # and merge the results. We still cap the total to avoid runaway lists,
    # but the cap is generous (8x page size, max 240) so realistic searches
    # always reach the cap from at least 2-3 sources.
    ordered_rows = []
    enough = max(60, _listing_page_size() * 8)
    enough = min(enough, 240)
    batch_size = max(2, min(parallel_workers(), 6))
    for start in range(0, len(search_jobs), batch_size):
        batch = search_jobs[start:start + batch_size]
        for job, result in iter_parallel(_run_search, batch, workers=min(batch_size, len(batch))):
            provider, _cat = job
            if isinstance(result, Exception):
                continue
            metas = []
            for meta in (result or {}).get('metas') or []:
                meta_id = meta.get('id')
                if not meta_id or meta_id in seen:
                    continue
                seen[meta_id] = True
                metas.append(meta)
            if not metas:
                continue
            # Search should feel instant — avoid expensive deep enrich here.
            try:
                from . import meta_source as _meta_source
                metas = _meta_source.override_metas_batch(provider, media_type, metas)
            except Exception:
                pass
            for meta in metas:
                ordered_rows.append((provider, meta.get('id'), meta))
        # Hard cap (rare for normal queries): protects against pathological
        # broad searches like "the" returning thousands across providers.
        if len(ordered_rows) >= enough:
            ordered_rows = ordered_rows[:enough]
            break

    if ordered_rows:
        _search_cache_put(cache_key, ordered_rows)

    for provider, meta_id, meta in ordered_rows:
        item_label = meta.get('name') or meta_id
        try:
            _meta_mem_put(media_type, meta_id, meta, source_provider_id=provider.get('id') or '')
        except Exception:
            pass
        path_action = 'series_meta' if media_type == 'series' else 'play_item'
        fallback = _item_fallback_art(provider, media_type, None, item_label)
        add_item(item_label, build_url(action=path_action, media_type=media_type, canonical_id=meta_id, title=item_label, source_provider_id=provider.get('id') or ''), is_folder=_is_series_media(media_type), info=_meta_info(meta), art=_resolve_meta_art(provider, media_type, meta, fallback_art=fallback), ids=extract_ids(meta), context_menu=_build_source_picker_menu(media_type=media_type, canonical_id=meta_id, title=item_label, source_provider_id=provider.get('id') or ''))
    end_dir(content=_directory_content_for_type(media_type), cache=False)


def _provider_order_for_id(media_type, canonical_id):
    rows = []
    for provider in store.list_providers():
        if supports_resource(provider, 'stream', media_type=media_type, item_id=canonical_id) or supports_resource(provider, 'meta', media_type=media_type, item_id=canonical_id):
            rows.append(provider)
    # Bug fix: previously, if the strict idPrefix filter matched 0 providers
    # (e.g. Continue Watching has a `tmdb:` ID but the user's stream addons
    # only declare `tt`), the source list came back empty and Continue
    # Watching items appeared "broken" with no streams. Fall back to ALL
    # stream-capable providers and let each provider decide whether it can
    # actually resolve the ID — this matches Stremio's own behavior.
    if not rows:
        for provider in store.list_providers():
            if supports_resource(provider, 'stream', media_type=media_type) or supports_resource(provider, 'meta', media_type=media_type):
                rows.append(provider)
    return rows


def _unique(values):
    seen = set()
    out = []
    for value in values:
        sval = str(value or '').strip()
        if not sval or sval in seen:
            continue
        seen.add(sval)
        out.append(sval)
    return out



def _enrich_stream_ids(ids, media_type, meta=None, canonical_id='', title=''):
    """Fill IMDb/TMDb/TVDb ids before asking Stremio stream addons.

    Stremio apps normally call stream addons with catalogue ids such as `tt...`.
    When Dex Hub starts from TMDb Helper or TMDb-based catalogues we may only
    have `tmdb:123`; AIOStreams/Torrentio then miss Debrid results.  Resolve
    ids locally first, using TMDb Helper's DB (no API) and then TMDb Direct if
    the user has configured an API key.
    """
    out = dict(ids or {})
    meta = meta or {}
    parsed = extract_ids(meta)
    for key in ('tmdb_id', 'imdb_id', 'tvdb_id'):
        if parsed.get(key) and not out.get(key):
            out[key] = parsed.get(key)
    cid = str(canonical_id or meta.get('id') or '').strip()
    if cid.startswith('tmdb:') and not out.get('tmdb_id'):
        tail = cid.split(':')[-1]
        if tail.isdigit():
            out['tmdb_id'] = tail
    elif cid.startswith('tvdb:') and not out.get('tvdb_id'):
        tail = cid.split(':')[-1]
        if tail.isdigit():
            out['tvdb_id'] = tail
    elif re.match(r'^tt\d{5,10}$', cid, re.I) and not out.get('imdb_id'):
        out['imdb_id'] = cid

    year = (_meta_info(meta).get('year') or meta.get('year') or meta.get('releaseInfo') or '')
    lookup_title = title or meta.get('name') or meta.get('title') or ''
    try:
        db_ids = _tmdb_art_db.get_external_ids_from_db(
            tmdb_id=out.get('tmdb_id') or '', imdb_id=out.get('imdb_id') or '', tvdb_id=out.get('tvdb_id') or '',
            media_type=media_type, title=lookup_title, year=year,
        ) or {}
        for key in ('tmdb_id', 'imdb_id', 'tvdb_id'):
            if db_ids.get(key) and not out.get(key):
                out[key] = db_ids.get(key)
    except Exception:
        pass
    if not out.get('imdb_id') and (out.get('tmdb_id') or lookup_title):
        try:
            bundle = _tmdb_direct.art_for(
                tmdb_id=out.get('tmdb_id') or '', imdb_id='', media_type=media_type,
                title=lookup_title, year=year,
            ) or {}
            if bundle.get('imdb_id'):
                out['imdb_id'] = bundle.get('imdb_id')
            if bundle.get('tmdb_id') and not out.get('tmdb_id'):
                out['tmdb_id'] = str(bundle.get('tmdb_id'))
        except Exception:
            pass
    if out.get('imdb_id') and str(out.get('imdb_id')).isdigit():
        out['imdb_id'] = 'tt%s' % out.get('imdb_id')
    return out

def _candidate_ids_from_meta(canonical_id, meta=None, season=None, episode=None, include_episode_variants=False):
    meta = meta or {}
    ids = extract_ids(meta)
    candidates = [canonical_id]
    if ids.get('imdb_id'):
        imdb = ids['imdb_id']
        candidates.extend([imdb, 'imdb:%s' % imdb])
    if ids.get('tmdb_id'):
        candidates.append('tmdb:%s' % ids['tmdb_id'])
    if ids.get('tvdb_id'):
        candidates.append('tvdb:%s' % ids['tvdb_id'])
    for key in ('kitsu_id', 'anilist_id', 'anidb_id', 'mal_id'):
        val = meta.get(key)
        if val:
            prefix = key.replace('_id', '')
            candidates.append('%s:%s' % (prefix, val))
    external = meta.get('externalIds') or {}
    if isinstance(external, dict):
        for key, value in external.items():
            if not value:
                continue
            skey = str(key).lower()
            sval = str(value)
            if skey.startswith('imdb'):
                candidates.extend([sval if sval.startswith('tt') else 'tt%s' % sval, 'imdb:%s' % (sval if sval.startswith('tt') else 'tt%s' % sval)])
            elif skey.startswith('tmdb'):
                candidates.append('tmdb:%s' % sval)
            elif skey.startswith('tvdb'):
                candidates.append('tvdb:%s' % sval)
            elif skey.startswith('anidb'):
                candidates.append('anidb:%s' % sval)
            elif skey.startswith('kitsu'):
                candidates.append('kitsu:%s' % sval)
            elif skey.startswith('anilist'):
                candidates.append('anilist:%s' % sval)
    if include_episode_variants and season and episode:
        episode_ids = []
        for cid in list(candidates):
            lower = cid.lower()
            if ':' in cid and not lower.startswith('tt'):
                episode_ids.append('%s:%s:%s' % (cid, int(season), int(episode)))
            elif lower.startswith('tt'):
                episode_ids.append('%s:%s:%s' % (cid, int(season), int(episode)))
        candidates = episode_ids + candidates
    return _unique(candidates)


def _stream_resource_id_prefixes(provider, media_type=None):
    """Return idPrefixes advertised by a provider's stream resource.

    Some Stremio aggregators such as AIOStreams/Torrentio advertise only `tt`
    but can still resolve episode ids like `tt123:1:2`. Dex Hub must not hide
    those providers just because the current catalog id is tmdb/tvdb.
    """
    manifest = (provider or {}).get('manifest') or {}
    for resource in manifest.get('resources', []) or []:
        if resource == 'stream':
            return []
        if isinstance(resource, dict) and resource.get('name') == 'stream':
            types = resource.get('types') or []
            if media_type and types and media_type not in types:
                continue
            return [str(x).lower() for x in (resource.get('idPrefixes') or []) if str(x or '').strip()]
    return []


def _candidate_ids_matching_prefixes(candidate_ids, prefixes):
    prefixes = [str(p or '').lower() for p in (prefixes or []) if str(p or '').strip()]
    if not prefixes:
        return list(candidate_ids or [])
    out = []
    for cid in candidate_ids or []:
        lower = str(cid or '').lower()
        if any(lower.startswith(prefix) for prefix in prefixes):
            out.append(cid)
    return out


def _ordered_stream_candidate_ids(provider_ids, season=None, episode=None):
    """Prefer the id shapes stream aggregators resolve best.

    AIOStreams/Torrentio-like addons usually resolve IMDb tt ids first. For
    episodes, the canonical Stremio form is tt1234567:season:episode. Keep
    tmdb/tvdb as fallback candidates, but do not let them run before tt ids.
    """
    ep_suffix = ''
    if season and episode:
        try:
            ep_suffix = ':%s:%s' % (int(season), int(episode))
        except Exception:
            ep_suffix = ''

    def _rank(value):
        lower = str(value or '').lower()
        is_ep = bool(ep_suffix and lower.endswith(ep_suffix))
        if is_ep and lower.startswith('tt'):
            return (0, lower)
        if lower.startswith('tt'):
            return (1, lower)
        if is_ep and lower.startswith('imdb:tt'):
            return (2, lower)
        if lower.startswith('imdb:tt'):
            return (3, lower)
        if is_ep and lower.startswith('tmdb:'):
            return (4, lower)
        if lower.startswith('tmdb:'):
            return (5, lower)
        if is_ep and lower.startswith('tvdb:'):
            return (6, lower)
        if lower.startswith('tvdb:'):
            return (7, lower)
        return (8, lower)

    return sorted(list(provider_ids or []), key=_rank)

def _stream_provider_targets(media_type, canonical_id, meta=None, season=None, episode=None):
    targets = []
    seen = set()
    meta = _meta_with_seed_ids(meta or {}, _enrich_stream_ids(extract_ids(meta or {}), media_type, meta=meta or {}, canonical_id=canonical_id, title=(meta or {}).get('name') or (meta or {}).get('title') or ''))
    candidate_ids = _candidate_ids_from_meta(canonical_id, meta=meta, season=season, episode=episode, include_episode_variants=bool(season and episode))
    for provider in store.list_providers():
        if not supports_resource(provider, 'stream', media_type=media_type):
            continue
        prefixes = _stream_resource_id_prefixes(provider, media_type=media_type)
        provider_ids = _candidate_ids_matching_prefixes(candidate_ids, prefixes)
        if not provider_ids:
            # Stremio itself lets the addon decide if an id is valid. This keeps
            # dynamic aggregators such as AIOStreams visible even when their
            # manifest prefixes do not cover the current catalog id shape.
            provider_ids = list(candidate_ids or [])
        if season and episode:
            ep_suffix = ':%s:%s' % (int(season), int(episode))
            episode_ids = [x for x in provider_ids if str(x).endswith(ep_suffix)]
            plain_ids = [x for x in provider_ids if x not in episode_ids]
            provider_ids = episode_ids + plain_ids
        provider_ids = _ordered_stream_candidate_ids(provider_ids, season=season, episode=episode)
        if _is_aiostreams_provider(provider):
            tt_ids = [x for x in provider_ids if str(x).lower().startswith('tt')]
            if tt_ids:
                provider_ids = tt_ids
        for item_id in provider_ids[:8]:
            key = (provider.get('id') or provider.get('base_url') or provider.get('name') or '', str(item_id))
            if key in seen:
                continue
            seen.add(key)
            targets.append((provider, item_id))
    if not targets:
        for provider in _provider_order_for_id(media_type, canonical_id):
            key = (provider.get('id') or provider.get('base_url') or provider.get('name') or '', str(canonical_id))
            if key in seen:
                continue
            seen.add(key)
            targets.append((provider, canonical_id))
    return targets


def _directory_content_for_type(media_type):
    return 'tvshows' if media_type in ('series', 'anime', 'show', 'tv') else 'movies'


def _default_click_mode():
    raw = str(ADDON.getSetting('catalog_click_mode') or 'Dex Hub').strip().lower()
    compact = raw.replace(' ', '').replace('_', '').replace('-', '')
    if compact in ('tmdbhelper', 'helper', '1') or 'tmdb' in compact:
        return 'tmdbhelper'
    if raw in ('اسأل كل مرة', 'ask') or compact in ('ask', 'askeverytime', '2'):
        return 'ask'
    return 'dexhub'


def _default_playback_mode():
    raw = (ADDON.getSetting('playback_open_mode') or 'Choose from sources').strip().lower()
    if raw in ('1', 'best quality automatically', 'auto', 'autoplay') or ('best' in raw) or ('أفضل' in raw):
        return 'autoplay'
    return 'sources'


def _prefer_source_picker():
    return _default_playback_mode() != 'autoplay'


def _resolve_routing_ids(media_type='movie', canonical_id='', title='', tmdb_id='', imdb_id='', tvdb_id='', season='', episode=''):
    probe_type = 'series' if _is_series_media(media_type) or (season not in (None, '', '0', 0) and episode not in (None, '', '0', 0)) else 'movie'
    ids = {
        'tmdb_id': str(tmdb_id or '').strip(),
        'imdb_id': str(imdb_id or '').strip(),
        'tvdb_id': str(tvdb_id or '').strip(),
    }
    ids = _merge_seed_ids(ids, _get_tmdbh_seed_ids(canonical_id or ''))
    ids = _merge_seed_ids(ids, extract_ids({'id': canonical_id or ''}))
    if ids.get('tmdb_id') or ids.get('imdb_id') or ids.get('tvdb_id'):
        return ids
    try:
        cached = _meta_mem_get(probe_type, canonical_id)
    except Exception:
        cached = None
    if cached:
        ids = _merge_seed_ids(ids, extract_ids(cached))
        if ids.get('tmdb_id') or ids.get('imdb_id') or ids.get('tvdb_id'):
            return ids
    providers = _provider_order_for_id(probe_type, canonical_id)
    if providers:
        try:
            meta = _best_meta_for_item(probe_type, canonical_id, providers)
            ids = _merge_seed_ids(ids, extract_ids(meta))
        except Exception as exc:
            xbmc.log('[DexHub] routing id probe failed for %s: %s' % (canonical_id, exc), xbmc.LOGWARNING)
    return ids


def _maybe_redirect_default_player(media_type='movie', canonical_id='', title='', season='', episode='', tmdb_id='', imdb_id='', tvdb_id=''):
    mode = _default_click_mode()
    # When TMDb Helper already handed the item off to Dex Hub, do NOT bounce
    # back into TMDb Helper again from inside Dex Hub. That re-entry opens the
    # TMDb Helper page a second time and often ends with failed playback.
    if _tmdbh_invocation_active():
        return False
    if mode != 'tmdbhelper' or not _has_tmdbhelper():
        return False
    probe_type = 'series' if _is_series_media(media_type) or (season not in (None, '', '0', 0) and episode not in (None, '', '0', 0)) else 'movie'
    meta = {'id': canonical_id, 'type': probe_type, 'name': title or canonical_id}
    ids = _resolve_routing_ids(
        media_type=probe_type,
        canonical_id=canonical_id,
        title=title or canonical_id,
        tmdb_id=tmdb_id,
        imdb_id=imdb_id,
        tvdb_id=tvdb_id,
        season=season,
        episode=episode,
    )
    if not (ids.get('tmdb_id') or ids.get('imdb_id') or ids.get('tvdb_id')):
        providers = _provider_order_for_id(probe_type, canonical_id)
        try:
            meta = _best_meta_for_item(probe_type, canonical_id, providers)
        except Exception as exc:
            xbmc.log('[DexHub] default-player meta probe failed for %s: %s' % (canonical_id, exc), xbmc.LOGWARNING)
            meta = {'id': canonical_id, 'type': probe_type, 'name': title or canonical_id}
        ids = _merge_seed_ids(ids, extract_ids(meta))
    url = _tmdbh_url_from_ids(
        media_type='series' if probe_type == 'series' else 'movie',
        tmdb_id=ids.get('tmdb_id') or '',
        imdb_id=ids.get('imdb_id') or '',
        tvdb_id=ids.get('tvdb_id') or '',
        title=(meta.get('name') or meta.get('title') or title or canonical_id),
        season=season or '',
        episode=episode or '',
    )
    if not url:
        return False
    return _launch_tmdbhelper_url(url)


def _dispatch_dexhub_play(media_type='', canonical_id='', title='', video_id='', season='', episode='', resume_seconds='0', resume_percent='', preferred_provider_name='', source_provider_id=''):
    media_type = str(media_type or 'movie').strip().lower()
    try:
        resume = float(resume_seconds or 0.0)
    except Exception:
        resume = 0.0
    if season not in (None, '', '0', 0) and episode not in (None, '', '0', 0):
        if _prefer_source_picker():
            return episode_streams(canonical_id, video_id or canonical_id, int(season), int(episode), title=title or canonical_id, media_type='series', resume_seconds=resume, resume_percent=resume_percent or '', preferred_provider_name=preferred_provider_name or '', source_provider_id=source_provider_id or '')
        return _auto_play_first_episode(
            canonical_id,
            video_id or canonical_id,
            int(season),
            int(episode),
            title=title or canonical_id,
            preferred_provider_name=preferred_provider_name or '',
            resume_seconds=resume,
            resume_percent=resume_percent or '',
            source_provider_id=source_provider_id or '',
        )
    if _is_series_media(media_type):
        return series_meta('series', canonical_id, title=title or canonical_id, source_provider_id=source_provider_id or '')
    if _prefer_source_picker():
        return streams(media_type or 'movie', canonical_id, title=title or canonical_id, resume_seconds=resume, resume_percent=resume_percent or '', preferred_provider_name=preferred_provider_name or '', source_provider_id=source_provider_id or '')
    return _auto_play_first_movie(
        canonical_id,
        title=title or canonical_id,
        preferred_provider_name=preferred_provider_name or '',
        resume_seconds=resume,
        resume_percent=resume_percent or '',
        source_provider_id=source_provider_id or '',
    )


def _has_tmdbhelper():
    try:
        return xbmc.getCondVisibility('System.HasAddon(plugin.video.themoviedb.helper)')
    except Exception:
        return False


def _tmdbh_invocation_active():
    return _tmdbh_handoff_active()


def _tmdbh_url_from_ids(media_type='movie', tmdb_id='', imdb_id='', tvdb_id='', title='', season='', episode='', force_dialog=False):
    media_type = str(media_type or 'movie').strip().lower()
    params = {}
    if media_type in ('movie',):
        params = {'info': 'play', 'type': 'movie'}
    elif media_type in ('series', 'anime', 'show', 'tv') and season not in (None, '', 0, '0') and episode not in (None, '', 0, '0'):
        params = {
            'info': 'play',
            'type': 'episode',
            'season': str(season),
            'episode': str(episode),
        }
    elif media_type in ('series', 'anime', 'show', 'tv'):
        params = {'info': 'details', 'type': 'tv'}
    else:
        return ''
    # Do not force TMDb Helper to ignore its default player by default. The
    # addon explicitly tells users to set Dex Hub as the default TMDb Helper
    # player to avoid the chooser on every click; the old hard-coded
    # ignore_default=true made that impossible and caused a double chooser
    # flow (Dex Hub -> TMDb Helper) for many users. Keep an opt-in flag so we
    # can still force TMDb Helper's chooser from a dedicated path in future if
    # needed.
    if force_dialog and params.get('info') == 'play':
        params['ignore_default'] = 'true'
    if tmdb_id:
        params['tmdb_id'] = str(tmdb_id)
    elif imdb_id:
        params['imdb_id'] = str(imdb_id)
    elif tvdb_id:
        params['tvdb_id'] = str(tvdb_id)
    elif title:
        params['query'] = title
    else:
        return ''
    return 'plugin://plugin.video.themoviedb.helper/?' + urlencode(params)


def _tmdbhelper_play_url(meta, media_type, title=''):
    ids = extract_ids(meta)
    return _tmdbh_url_from_ids(
        media_type=media_type,
        tmdb_id=ids.get('tmdb_id') or '',
        imdb_id=ids.get('imdb_id') or '',
        tvdb_id=ids.get('tvdb_id') or '',
        title=title or meta.get('name') or meta.get('title') or '',
    )


def _launch_tmdbhelper_url(url):
    url = str(url or '').strip()
    if not url:
        return False
    try:
        # Match the known-good context-menu path used elsewhere in the addon.
        xbmc.executebuiltin('Container.Update(%s)' % url)
        return True
    except Exception as exc:
        xbmc.log('[DexHub] tmdbhelper container update failed: %s' % exc, xbmc.LOGWARNING)
    try:
        xbmc.executebuiltin('ActivateWindow(Videos,%s,return)' % url)
        return True
    except Exception as exc:
        xbmc.log('[DexHub] tmdbhelper activate window failed: %s' % exc, xbmc.LOGWARNING)
    return False


def _default_click_uses_tmdbhelper():
    return (not _tmdbh_invocation_active()) and _default_click_mode() == 'tmdbhelper' and _has_tmdbhelper()


def _content_click_path(media_type='movie', canonical_id='', title='', tmdb_id='', imdb_id='', tvdb_id='', season='', episode='', video_id='', source_provider_id=''):
    media_type = str(media_type or 'movie').strip().lower()
    if _default_click_uses_tmdbhelper():
        route_ids = _resolve_routing_ids(
            media_type=media_type,
            canonical_id=canonical_id,
            title=title or canonical_id,
            tmdb_id=tmdb_id,
            imdb_id=imdb_id,
            tvdb_id=tvdb_id,
            season=season,
            episode=episode,
        )
        helper_url = _tmdbh_url_from_ids(
            media_type=media_type,
            tmdb_id=route_ids.get('tmdb_id') or '',
            imdb_id=route_ids.get('imdb_id') or '',
            tvdb_id=route_ids.get('tvdb_id') or '',
            title=title or canonical_id,
            season=season or '',
            episode=episode or '',
        )
        if helper_url:
            # Use the exact TMDb Helper URL directly so pressing the item follows
            # the same successful path as the context-menu entry "فتح في TMDb Helper".
            # Mark it as a folder-style navigation target; Kodi then issues a
            # normal plugin container update instead of treating it as a Dex Hub
            # playable item first.
            return helper_url, True
    if media_type in ('series', 'anime', 'show', 'tv') and season not in (None, '', 0, '0') and episode not in (None, '', 0, '0'):
        return build_url(action='play_item', media_type='series', canonical_id=canonical_id, video_id=video_id or canonical_id, season=season, episode=episode, title=title or canonical_id, tmdb_id=tmdb_id or '', imdb_id=imdb_id or '', tvdb_id=tvdb_id or '', source_provider_id=source_provider_id or ''), False
    if _is_series_media(media_type):
        return build_url(action='item_open', media_type=media_type, canonical_id=canonical_id, title=title or canonical_id, tmdb_id=tmdb_id or '', imdb_id=imdb_id or '', tvdb_id=tvdb_id or '', source_provider_id=source_provider_id or ''), True
    return build_url(action='play_item', media_type=media_type or 'movie', canonical_id=canonical_id, title=title or canonical_id, tmdb_id=tmdb_id or '', imdb_id=imdb_id or '', tvdb_id=tvdb_id or '', source_provider_id=source_provider_id or ''), False


def _source_window_meta_fallback(meta):
    meta = dict(meta or {})
    try:
        win = xbmcgui.Window(WINDOW_ID)
    except Exception:
        win = None
    try:
        home = xbmcgui.Window(10000)
    except Exception:
        home = None

    def _first(*values):
        for value in values:
            if value not in (None, ''):
                return value
        return ''

    poster = _first(
        meta.get('poster'), meta.get('thumb'),
        win.getProperty('poster') if win else '',
        win.getProperty('dexhub.poster') if win else '',
        home.getProperty('dexhub.source.poster') if home else '',
        home.getProperty('dexhub.source.thumb') if home else '',
    )
    fanart = _first(
        meta.get('fanart'), meta.get('background'),
        win.getProperty('fanart') if win else '',
        win.getProperty('dexhub.fanart') if win else '',
        home.getProperty('dexhub.source.fanart') if home else '',
        poster,
    )
    clearlogo = _first(
        meta.get('clearlogo'), meta.get('logo'),
        win.getProperty('clearlogo') if win else '',
        win.getProperty('dexhub.clearlogo') if win else '',
        win.getProperty('tvshow.clearlogo') if win else '',
        home.getProperty('dexhub.source.clearlogo') if home else '',
    )
    title = _first(meta.get('title'), meta.get('name'), home.getProperty('dexhub.source.title') if home else '')
    plot = _first(meta.get('plot'), meta.get('description'), home.getProperty('dexhub.source.plot') if home else '')
    genre = _first(meta.get('genre'), home.getProperty('dexhub.source.genre') if home else '')
    year = _first(meta.get('year'), home.getProperty('dexhub.source.year') if home else '')
    rating = _first(meta.get('rating'), home.getProperty('dexhub.source.rating') if home else '')

    if not poster:
        try:
            poster = _first(
                xbmc.getInfoLabel('ListItem.Art(poster)'),
                xbmc.getInfoLabel('ListItem.Art(tvshow.poster)'),
                xbmc.getInfoLabel('ListItem.Art(thumb)'),
            )
        except Exception:
            poster = ''
    if not fanart:
        try:
            fanart = _first(
                xbmc.getInfoLabel('ListItem.Art(fanart)'),
                xbmc.getInfoLabel('ListItem.Property(fanart_image)'),
                poster,
            )
        except Exception:
            fanart = poster or ''
    if not title:
        try:
            title = _first(xbmc.getInfoLabel('ListItem.Title'), xbmc.getInfoLabel('ListItem.Label'))
        except Exception:
            title = ''
    if not plot:
        try:
            plot = xbmc.getInfoLabel('ListItem.Plot') or ''
        except Exception:
            plot = ''
    if not genre:
        try:
            genre = xbmc.getInfoLabel('ListItem.Genre') or ''
        except Exception:
            genre = ''
    if not year:
        try:
            year = xbmc.getInfoLabel('ListItem.Year') or ''
        except Exception:
            year = ''
    if not rating:
        try:
            rating = xbmc.getInfoLabel('ListItem.Rating') or ''
        except Exception:
            rating = ''

    if poster:
        meta['poster'] = poster
    if fanart:
        meta['fanart'] = fanart
    meta['clearlogo'] = clearlogo or ''
    if title:
        meta['title'] = title
    if plot:
        meta['plot'] = plot
    if genre:
        meta['genre'] = genre
    if year:
        meta['year'] = year
    if rating:
        meta['rating'] = rating
    return meta


def _prioritize_provider_targets(targets, preferred_provider_name=''):
    preferred = str(preferred_provider_name or '').strip().lower()
    if not preferred or not targets:
        return list(targets or [])
    head = []
    tail = []
    for provider, request_id in list(targets or []):
        pid = str((provider or {}).get('id') or '').strip().lower()
        pname = str((provider or {}).get('name') or '').strip().lower()
        if preferred in (pid, pname):
            head.append((provider, request_id))
        else:
            tail.append((provider, request_id))
    return head + tail


def _dex_player_url(media_type='movie', canonical_id='', title='', season='', episode='', video_id='', source_provider_id=''):
    media_type = str(media_type or 'movie').strip().lower()
    if media_type in ('series', 'anime', 'show', 'tv') and season not in (None, '', 0, '0') and episode not in (None, '', 0, '0'):
        return build_url(
            action='episode_streams',
            canonical_id=canonical_id,
            video_id=video_id or canonical_id,
            season=str(season),
            episode=str(episode),
            title=title or canonical_id,
            media_type='series',
            source_provider_id=source_provider_id or '',
        )
    return build_url(
        action='series_meta' if media_type in ('series', 'anime', 'show', 'tv') else 'streams',
        media_type='series' if media_type in ('series', 'anime', 'show', 'tv') else 'movie',
        canonical_id=canonical_id,
        title=title or canonical_id,
        source_provider_id=source_provider_id or '',
    )


def _build_player_chooser_menu(media_type='movie', canonical_id='', title='', tmdb_id='', imdb_id='', tvdb_id='', season='', episode='', video_id='', source_provider_id=''):
    chooser_url = build_url(
        action='choose_player',
        media_type=media_type,
        canonical_id=canonical_id,
        title=title or canonical_id,
        tmdb_id=tmdb_id or '',
        imdb_id=imdb_id or '',
        tvdb_id=tvdb_id or '',
        season=season or '',
        episode=episode or '',
        video_id=video_id or '',
        source_provider_id=source_provider_id or '',
    )
    return [('اختيار المشغّل…', 'RunPlugin(%s)' % chooser_url)]


def choose_player(media_type='movie', canonical_id='', title='', tmdb_id='', imdb_id='', tvdb_id='', season='', episode='', video_id='', source_provider_id=''):
    dex_url = _dex_player_url(media_type=media_type, canonical_id=canonical_id, title=title, season=season, episode=episode, video_id=video_id, source_provider_id=source_provider_id or '')
    options = [('Dex Hub', dex_url)]
    if _has_tmdbhelper():
        route_ids = _resolve_routing_ids(media_type=media_type, canonical_id=canonical_id, title=title or canonical_id, tmdb_id=tmdb_id, imdb_id=imdb_id, tvdb_id=tvdb_id, season=season, episode=episode)
        tmdbh_url = _tmdbh_url_from_ids(media_type=media_type, tmdb_id=route_ids.get('tmdb_id') or '', imdb_id=route_ids.get('imdb_id') or '', tvdb_id=route_ids.get('tvdb_id') or '', title=title, season=season, episode=episode)
        if tmdbh_url:
            options.append(('TMDb Helper', tmdbh_url))
    choice = xbmcgui.Dialog().select(tr('اختر المشغّل'), [tr(label) for label, _ in options])
    if choice < 0 or choice >= len(options):
        return
    label, url = options[choice]
    if label == 'TMDb Helper':
        _launch_tmdbhelper_url(url)
    else:
        xbmc.executebuiltin('Container.Update(%s)' % url)


def _maybe_redirect_player(meta, media_type, title=''):
    if _tmdbh_invocation_active():
        return False
    mode = _default_click_mode()
    if mode == 'dexhub':
        return False
    if mode == 'ask':
        options = ['Dex Hub']
        if _has_tmdbhelper():
            options.append('TMDb Helper')
        choice = xbmcgui.Dialog().select(tr('اختر المشغل'), [tr(x) for x in options])
        if choice <= 0:
            return False
        mode = 'tmdbhelper'
    if mode == 'tmdbhelper' and _has_tmdbhelper():
        url = _tmdbhelper_play_url(meta, media_type, title=title)
        if url:
            return _launch_tmdbhelper_url(url)
    return False


def item_open(media_type, canonical_id, title='', tmdb_id='', imdb_id='', tvdb_id='', source_provider_id=''):
    media_type = (media_type or 'movie').strip().lower()
    if _tmdbh_invocation_active() and not _is_series_media(media_type):
        return play_item(media_type=media_type, canonical_id=canonical_id, title=title or canonical_id, tmdb_id=tmdb_id, imdb_id=imdb_id, tvdb_id=tvdb_id, source_provider_id=source_provider_id or '')
    # Direct playback for movie-like rows. Respect TMDb Helper click-mode if
    # the user explicitly chose it, otherwise go straight to playback.
    if not _is_series_media(media_type):
        mode = _default_click_mode()
        if mode != 'dexhub':
            route_ids = _resolve_routing_ids(media_type=media_type, canonical_id=canonical_id, title=title or canonical_id, tmdb_id=tmdb_id, imdb_id=imdb_id, tvdb_id=tvdb_id)
            if mode == 'tmdbhelper' and _has_tmdbhelper() and (route_ids.get('tmdb_id') or route_ids.get('imdb_id') or route_ids.get('tvdb_id')):
                helper_url = _tmdbh_url_from_ids(media_type=media_type, tmdb_id=route_ids.get('tmdb_id') or '', imdb_id=route_ids.get('imdb_id') or '', tvdb_id=route_ids.get('tvdb_id') or '', title=title or canonical_id)
                if helper_url and _launch_tmdbhelper_url(helper_url):
                    return
            providers = _provider_order_for_id_with_context(media_type, canonical_id, source_provider_id=source_provider_id)
            try:
                meta = _best_meta_for_item(media_type, canonical_id, providers, source_provider_id=source_provider_id)
            except Exception as exc:
                xbmc.log('[DexHub] item_open movie meta probe failed for %s: %s' % (canonical_id, exc), xbmc.LOGWARNING)
                meta = {'id': canonical_id, 'type': media_type, 'name': title or canonical_id}
            try:
                if _maybe_redirect_player(meta, media_type, title=title):
                    return
            except Exception as exc:
                xbmc.log('[DexHub] movie player redirect failed for %s: %s' % (canonical_id, exc), xbmc.LOGWARNING)
        _monitor_playback('item-open-movie', media_type=media_type, canonical_id=canonical_id, title=title or canonical_id)
        return play_item(media_type=media_type, canonical_id=canonical_id, title=title or canonical_id, source_provider_id=source_provider_id or '')

    # Series rows still open the seasons screen unless the user explicitly
    # redirects them to TMDb Helper via the click-mode setting.
    if _default_click_mode() == 'dexhub':
        resolved_title = title or canonical_id
        return series_meta(media_type, canonical_id, title=resolved_title, source_provider_id=source_provider_id or '')

    if _default_click_mode() == 'tmdbhelper' and _has_tmdbhelper():
        route_ids = _resolve_routing_ids(media_type=media_type, canonical_id=canonical_id, title=title or canonical_id, tmdb_id=tmdb_id, imdb_id=imdb_id, tvdb_id=tvdb_id)
        if route_ids.get('tmdb_id') or route_ids.get('imdb_id') or route_ids.get('tvdb_id'):
            helper_url = _tmdbh_url_from_ids(media_type=media_type, tmdb_id=route_ids.get('tmdb_id') or '', imdb_id=route_ids.get('imdb_id') or '', tvdb_id=route_ids.get('tvdb_id') or '', title=title or canonical_id)
            if helper_url and _launch_tmdbhelper_url(helper_url):
                return
    providers = _provider_order_for_id_with_context(media_type, canonical_id, source_provider_id=source_provider_id)
    try:
        meta = _best_meta_for_item(media_type, canonical_id, providers, source_provider_id=source_provider_id)
    except Exception as exc:
        xbmc.log('[DexHub] item_open meta probe failed for %s: %s' % (canonical_id, exc), xbmc.LOGWARNING)
        meta = {'id': canonical_id, 'type': media_type, 'name': title or canonical_id}
    try:
        if _maybe_redirect_player(meta, media_type, title=title):
            return
    except Exception as exc:
        xbmc.log('[DexHub] player redirect failed for %s: %s' % (canonical_id, exc), xbmc.LOGWARNING)
    resolved_title = title or (meta or {}).get('name') or canonical_id
    try:
        return series_meta(media_type, canonical_id, title=resolved_title, source_provider_id=source_provider_id or '')
    except Exception as exc:
        xbmc.log('[DexHub] series_meta failed for %s: %s' % (canonical_id, exc), xbmc.LOGWARNING)
        return series_meta('series', canonical_id, title=resolved_title)



def _best_meta_for_item(media_type, canonical_id, providers, source_provider_id=''):
    cached = _meta_mem_get(media_type, canonical_id, source_provider_id=source_provider_id)
    if cached:
        return cached
    providers = _meta_provider_first(providers, source_provider_id=source_provider_id)
    if not providers:
        fallback = {'id': canonical_id, 'type': media_type, 'name': canonical_id}
        _meta_mem_put(media_type, canonical_id, fallback, source_provider_id=source_provider_id)
        return fallback

    def _apply_provider_source(provider, meta):
        try:
            if _is_virtual_meta_target(source_provider_id):
                return _meta_source.override_virtual_meta(source_provider_id, media_type, meta) or meta
            return _meta_source.override_meta(provider, media_type, meta) or meta
        except Exception as exc:
            xbmc.log('[DexHub] meta source override failed for %s: %s' % ((provider or {}).get('name') or (provider or {}).get('id') or source_provider_id or '', exc), xbmc.LOGDEBUG)
            return meta

    def _probe(provider):
        data = fetch_meta(provider, media_type, canonical_id, timeout_override=fast_timeout('meta'))
        meta = data.get('meta') or data.get('metas')
        if isinstance(meta, list):
            meta = meta[0] if meta else None
        if not meta:
            return None
        return _apply_provider_source(provider, meta)

    def _score(meta):
        """Rough richness score — prefers metas with poster/fanart/description/year."""
        if not isinstance(meta, dict):
            return -1
        score = 0
        for key in ('poster', 'background', 'fanart', 'logo', 'clearlogo'):
            if meta.get(key):
                score += 2
        for key in ('description', 'overview', 'plot'):
            val = meta.get(key)
            if val and len(str(val)) > 60:
                score += 2
        if meta.get('releaseInfo') or meta.get('year'):
            score += 1
        if meta.get('videos'):
            score += 3  # series with episode list is most useful
        if meta.get('genres'):
            score += 1
        if meta.get('imdbRating') or meta.get('rating'):
            score += 1
        if _meta_art_is_strict(meta):
            score += 50  # explicit picker must win over any other provider
        return score

    # If the item came from a specific catalog/provider, that provider's
    # configured metadata source is authoritative. Do not let a richer unrelated
    # provider win the score race and undo the user's selected source.
    if source_provider_id and not _is_virtual_meta_target(source_provider_id):
        first = providers[0] if providers else None
        if first and str(first.get('id') or '') == str(source_provider_id):
            try:
                meta = _probe(first)
                if meta:
                    _meta_mem_put(media_type, canonical_id, meta, source_provider_id=source_provider_id)
                    return meta
                if _provider_uses_explicit_meta_art(first):
                    seed = {'id': canonical_id, 'type': media_type, 'name': canonical_id, 'title': canonical_id}
                    meta = _meta_source.override_meta(first, media_type, seed) or seed
                    _meta_mem_put(media_type, canonical_id, meta, source_provider_id=source_provider_id)
                    return meta
            except Exception as exc:
                xbmc.log('[DexHub] source-context meta probe failed for %s: %s' % (canonical_id, exc), xbmc.LOGDEBUG)

    best = None
    best_score = -1
    for _prov, result in run_parallel(_probe, list(providers)):
        if isinstance(result, Exception) or not result:
            continue
        sc = _score(result)
        if sc > best_score:
            best = result
            best_score = sc
    if best is not None:
        _meta_mem_put(media_type, canonical_id, best, source_provider_id=source_provider_id)
        return best
    fallback = {'id': canonical_id, 'type': media_type, 'name': canonical_id}
    _meta_mem_put(media_type, canonical_id, fallback, source_provider_id=source_provider_id)
    return fallback

def _fast_meta_for_sources(media_type, canonical_id, providers, title='', source_provider_id=''):
    cached = _meta_mem_get(media_type, canonical_id, source_provider_id=source_provider_id)
    if cached:
        return cached, True
    if _source_context_requires_exact_meta(source_provider_id):
        try:
            exact = _best_meta_for_item(media_type, canonical_id, providers, source_provider_id=source_provider_id)
            if exact:
                return exact, True
        except Exception as exc:
            xbmc.log('[DexHub] exact meta fetch failed for %s/%s: %s' % (media_type, canonical_id, exc), xbmc.LOGDEBUG)
    label = title or canonical_id
    fallback = {
        'id': canonical_id,
        'type': 'series' if media_type in ('series', 'anime', 'show', 'tv') else 'movie',
        'name': label,
        'title': label,
    }
    return fallback, False


def _prime_best_meta_async(media_type, canonical_id, providers, source_provider_id=''):
    if _meta_mem_get(media_type, canonical_id, source_provider_id=source_provider_id) or not providers:
        return

    def _worker():
        try:
            _best_meta_for_item(media_type, canonical_id, providers, source_provider_id=source_provider_id)
        except Exception:
            pass

    threading.Thread(target=_worker, name='DexHubMetaWarm', daemon=True).start()


def _batch_replace(text, replacements):
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _regional_flag_to_code(match):
    chars = match.group(0)
    try:
        return '[%s%s]' % (chr(ord(chars[0]) - 127397), chr(ord(chars[1]) - 127397))
    except Exception:
        return ' '


def _clean_stream_text(value):
    text = html.unescape(str(value or ''))
    text = _batch_replace(text, HEX_ENTITIES)
    text = COLOR_TAG_RE.sub(' ', text)
    text = REGIONAL_FLAG_RE.sub(_regional_flag_to_code, text)
    text = STREAM_ICON_RE.sub(' ', text)
    text = text.replace('\u200f', ' ').replace('\u200e', ' ').replace('\xa0', ' ')
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = ''.join(ch for ch in text if ch == '\n' or ch == '\t' or ord(ch) >= 32)
    text = _batch_replace(text, SPECIAL_BLANKS)
    text = text.replace('•', ' | ').replace('·', ' | ').replace('—', '-').replace('–', '-')
    text = BRACKET_RE.sub(' ', text)
    text = MULTI_WS_RE.sub(' ', text).strip(' -|_')
    return text.strip()


def _pretty_upper(value):
    text = _clean_stream_text(value)
    return text.upper() if text else ''


def _extract_quality_bits(*values):
    seen = []
    for value in values:
        text = _clean_stream_text(value).lower()
        for match in QUALITY_RE.findall(text):
            item = match.upper().replace('WEB DL', 'WEBDL').replace('WEBRIP', 'WEBRIP').replace('DOLBY VISION', 'DV')
            if item not in seen:
                seen.append(item)
    return seen


def _format_size_value(value):
    try:
        if isinstance(value, (int, float)):
            size = float(value)
            if size <= 0:
                return ''
            if size >= 1024 ** 3:
                return '%.2f GB' % (size / float(1024 ** 3))
            if size >= 1024 ** 2:
                return '%.2f MB' % (size / float(1024 ** 2))
            return '%.0f B' % size
    except Exception:
        pass
    return ''


def _extract_size(*values):
    for value in values:
        if isinstance(value, (int, float)):
            formatted = _format_size_value(value)
            if formatted:
                return formatted
        m = SIZE_RE.search(_clean_stream_text(value))
        if m:
            return m.group(1).upper().replace('GIB', 'GB').replace('MIB', 'MB')
    return ''


def _normalize_ascii(text):
    text = _clean_stream_text(text)
    text = re.sub(r'[^\x00-\x7F]', '', text)
    text = MULTI_WS_RE.sub(' ', text).strip(' -|_')
    return text


def _filename_basename(value):
    text = _normalize_ascii(value)
    if not text:
        return ''
    text = re.sub(r'\.(mkv|mp4|avi|m2ts|ts|mov|wmv|flv|webm|srt|ass|ssa)$', '', text, flags=re.I)
    return text.strip()


def _extract_group(values, patterns):
    seen = []
    for value in values:
        text = _normalize_ascii(value).lower()
        for patt, repl in patterns:
            for _ in re.findall(patt, text, re.I):
                if repl not in seen:
                    seen.append(repl)
    return seen


def _iter_stream_values(value):
    if value is None:
        return
    if isinstance(value, (list, tuple, set)):
        for entry in value:
            for sub in _iter_stream_values(entry):
                yield sub
        return
    if isinstance(value, dict):
        for entry in value.values():
            for sub in _iter_stream_values(entry):
                yield sub
        return
    sval = str(value).strip()
    if sval:
        yield sval


def _collect_stream_texts(row):
    hints = row.get('behaviorHints') or {}
    texts = []
    fields = [
        row.get('name'), row.get('title'), row.get('description'), row.get('filename'), row.get('fileName'), row.get('folderName'),
        row.get('url'), row.get('externalUrl'), row.get('site'), row.get('host'), row.get('tracker'), row.get('sourceSite'),
        row.get('source'), row.get('addon'), row.get('addonName'), row.get('provider'), row.get('streamName'), row.get('releaseTitle'),
        row.get('release'), row.get('bingeGroup'), row.get('resolution'), row.get('quality'), row.get('encode'), row.get('codec'),
        row.get('releaseGroup'), row.get('network'), row.get('service'), row.get('visualTags'), row.get('audioTags'),
        row.get('audioChannels'), row.get('languages'), row.get('subtitles'), row.get('size'), row.get('videoSize'), row.get('sizeLabel'),
    ]
    if isinstance(hints, dict):
        for key in ('filename', 'fileName', 'name', 'title', 'description', 'bingeGroup', 'videoSize', 'quality', 'source', 'provider', 'site', 'resolution', 'codec', 'audioTags', 'audioChannels', 'visualTags', 'languages', 'size'):
            fields.append(hints.get(key))
        try:
            fields.append(json.dumps(hints, ensure_ascii=False))
        except Exception:
            pass
    for value in fields:
        for sval in _iter_stream_values(value):
            if sval not in texts:
                texts.append(sval)
    return texts


def _extract_addon_name(row, provider_name):
    hints = row.get('behaviorHints') or {}
    candidates = [
        row.get('addon'), row.get('addonName'), row.get('sourceAddon'), row.get('source_addon'),
        hints.get('addon') if isinstance(hints, dict) else '', hints.get('addonName') if isinstance(hints, dict) else '',
        row.get('source'), hints.get('source') if isinstance(hints, dict) else '',
        provider_name,
        row.get('provider'), hints.get('provider') if isinstance(hints, dict) else '',
    ]
    for value in candidates:
        text = _normalize_ascii(value)
        if not text:
            continue
        lowered = text.lower()
        if lowered in ('direct play', 'transcode', 'external', 'torrent', 'stream'):
            continue
        if lowered in ('rd', 'rd+', 'realdebrid', 'ad', 'ad+', 'alldebrid', 'pm', 'premiumize', 'tb', 'torbox', 'ed', 'easydebrid'):
            continue
        text = MULTI_WS_RE.sub(' ', text.replace('|', ' ').replace('/', ' ')).strip(' -_.')
        if text:
            return text.upper()
    return (provider_name or 'ADDON').upper()


def _site_from_url(row):
    for key in ('url', 'externalUrl'):
        value = row.get(key)
        if not value:
            continue
        try:
            host = urlparse(str(value)).netloc.lower()
        except Exception:
            host = ''
        if host:
            host = host.split('@')[-1]
            if host.startswith('www.'):
                host = host[4:]
            return host.upper()
    return ''


def _extract_site(row, provider_name):
    addon_name = _extract_addon_name(row, provider_name)
    url_site = _site_from_url(row)
    candidates = [
        row.get('site'), row.get('host'), row.get('tracker'), row.get('sourceSite'),
        (row.get('behaviorHints') or {}).get('site') if isinstance(row.get('behaviorHints'), dict) else '',
        url_site,
        row.get('name'), row.get('title')
    ]
    for value in candidates:
        text = _normalize_ascii(value)
        if not text:
            continue
        lowered = text.lower()
        if 'direct play' in lowered or 'transcode' in lowered:
            continue
        text = text.replace('|', ' ').replace('/', ' ')
        text = MULTI_WS_RE.sub(' ', text).strip(' -_.')
        if text and text.upper() != addon_name:
            return text.upper()
    return addon_name


def _extract_audio_bits(*values):
    patterns = [
        (r'\batmos\b', 'ATMOS'),
        (r'\btruehd\b|\btrue-hd\b', 'TRUEHD'),
        (r'\bdolby\s*digital\s*plus\b|\bddp(?:\+|\b)|\beac-?3\b|\bdd\+\b', 'DD+'),
        (r'\bdolby\s*digital\s*ex\b|\bdd-?ex\b', 'DD-EX'),
        (r'\bdolby\s*digital\b|\bdd\b', 'DD'),
        (r'\bac-?3\b', 'AC3'),
        (r'\bdts\s*x\b|\bdtsx\b', 'DTS-X'),
        (r'\bdts[- ]?hd\s*master\s*audio\b|\bdts[- ]?hd\s*ma\b', 'DTS-HD MA'),
        (r'\bdts[- ]?hd\b', 'DTS-HD'),
        (r'\bdts\b', 'DTS'),
        (r'\bflac\b', 'FLAC'),
        (r'\baac\b', 'AAC'),
        (r'\bopus\b', 'OPUS'),
        (r'\bmp3\b', 'MP3'),
        (r'\bpcm\b', 'PCM'),
        (r'\b8ch(?:\s*audio)?\b', '8CH'),
        (r'\b7\.1\b|\b7ch(?:\s*audio)?\b', '7.1'),
        (r'\b6ch(?:\s*audio)?\b|\b5\.1\b', '5.1'),
        (r'\b2ch(?:\s*audio)?\b|\b2\.0\b', '2.0'),
        (r'\bmulti(?:[- ]?audio|[- ]?lang(?:uages?)?)?\b', 'MULTI'),
        (r'\bdual(?:[- ]?audio)?\b', 'DUAL'),
        (r'\bdubbed?\b|\bdub\b', 'DUBBED'),
        (r'\bsubs?\b|\bsubbed\b|\bsubtitles\b', 'SUBS'),
        (r'\barabic\b', 'ARABIC'),
        (r'\benglish\b', 'ENGLISH'),
        (r'\brussian\b', 'RUSSIAN'),
    ]
    return _extract_group(values, patterns)


def _extract_video_bits(*values):
    patterns = [
        (r'\b2160p\b|\b4k\b|\buhd\b', '2160P'),
        (r'\b1080p\b|\bfhd\b', '1080P'),
        (r'\b720p\b', '720P'),
        (r'\b480p\b|\bsd\b', '480P'),
        (r'\bremux\b', 'REMUX'),
        (r'\bblu[ -]?ray\b', 'BLURAY'),
        (r'\bweb[ -]?dl\b', 'WEB-DL'),
        (r'\bweb[ -]?rip\b', 'WEBRIP'),
        (r'\bhdr10\+\b', 'HDR10+'),
        (r'\bhdr10\b', 'HDR10'),
        (r'\bhigh\s+dynamic\s+range\s*\(hdr\)\b|\bhdr\b', 'HDR'),
        (r'\bdolby\s*vision\b|\bdovi\b|\bdv\b', 'DV'),
        (r'\bhevc\b|\bx265\b|\bh265\b', 'HEVC'),
        (r'\bx264\b|\bh264\b', 'H264'),
        (r'\bav1\b', 'AV1'),
        (r'\b10bit\b|\b10-bit\b', '10BIT'),
        (r'\bhybrid\b', 'HYBRID'),
        (r'\bsdr\b', 'SDR'),
        (r'\b3d\b', '3D'),
        (r'\bnf\b|\bnetflix\b', 'NF'),
        (r'\bamzn\b|\bamazon\b', 'AMZN'),
        (r'\bdsnp\b|\bdisney\+?\b', 'DSNP'),
        (r'\bhulu\b', 'HULU'),
        (r'\batvp\b|\bapple\s?tv\b', 'ATVP'),
        (r'\bdvd\s*source\b|\bdvd\b', 'DVD'),
        (r'\bweb\s*source\b', 'WEB'),
        (r'\bpack\b', 'PACK'),
    ]
    return _extract_group(values, patterns)


def _stream_display_name(row):
    candidates = [
        row.get('folderName'), row.get('filename'), row.get('fileName'),
        (row.get('behaviorHints') or {}).get('filename') if isinstance(row.get('behaviorHints'), dict) else '',
        row.get('releaseTitle'), row.get('release'), row.get('title'), row.get('name'), row.get('description')
    ]
    for value in candidates:
        if value:
            text = _filename_basename(value)
            if text:
                return text.upper()
    return 'STREAM'


def _normalize_lang(value):
    # Stremio subtitle addons are not consistent: lang/language may be a
    # string, list, dict, regional-flag emoji, or a human name. Normalize all
    # of them so the subtitle picker always gets the proper language flag.
    if isinstance(value, (list, tuple, set)):
        for item in value:
            key = _normalize_lang(item)
            if key and key != 'und':
                return key
        return 'und'
    if isinstance(value, dict):
        for k in ('lang', 'language', 'languageCode', 'iso639', 'code', 'name'):
            if value.get(k):
                key = _normalize_lang(value.get(k))
                if key and key != 'und':
                    return key
        return 'und'
    raw_text = str(value or 'und').strip()
    if not raw_text:
        return 'und'
    # Convert regional flag emoji to a country code hint before STREAM_ICON_RE
    # can strip it elsewhere. Arabic subtitles often come as 🇸🇦 / 🇦🇪 only.
    try:
        flag_hint = REGIONAL_FLAG_RE.sub(_regional_flag_to_code, raw_text)
        country = flag_hint.strip('[]').lower() if flag_hint.startswith('[') and flag_hint.endswith(']') else ''
        country_alias = {'sa': 'ar', 'ae': 'ar', 'eg': 'ar', 'us': 'en', 'gb': 'en', 'uk': 'en', 'br': 'pt-br'}
        if country in country_alias:
            return country_alias[country]
    except Exception:
        pass
    raw = raw_text.lower().replace('_', '-').replace(' ', '-')
    aliases = {
        'ara': 'ar', 'arabic': 'ar', 'العربية': 'ar', 'عربي': 'ar', 'عربية': 'ar',
        'eng': 'en', 'english': 'en',
        'spa': 'es', 'spanish': 'es',
        'fre': 'fr', 'fra': 'fr', 'french': 'fr',
        'ger': 'de', 'deu': 'de', 'german': 'de',
        'por': 'pt', 'pob': 'pt-br', 'pb': 'pt-br', 'brazilian': 'pt-br',
        'tur': 'tr', 'turkish': 'tr',
        'rus': 'ru', 'russian': 'ru',
        'jpn': 'ja', 'japanese': 'ja',
        'kor': 'ko', 'korean': 'ko',
        'chi': 'zh', 'zho': 'zh', 'chinese': 'zh',
        'hin': 'hi', 'hindi': 'hi',
        'fas': 'fa', 'per': 'fa', 'persian': 'fa', 'farsi': 'fa',
    }
    raw = aliases.get(raw, raw)
    if raw in LANG_MAP:
        return raw
    raw2 = raw.split('-')[0]
    raw2 = aliases.get(raw2, raw2)
    if raw2 in LANG_MAP:
        return raw2
    return raw or 'und'


# Language hints we look for inside sub filenames / release names. Order
# matters — more specific tokens first so 'arabic' beats 'ara' beats 'ar'.
_FILENAME_LANG_HINTS = [
    ('arabic',     'ar'), ('عربي',     'ar'), ('عربية',    'ar'), ('ara',  'ar'), ('.ar.', 'ar'), ('-ar-', 'ar'), ('_ar_', 'ar'),
    ('english',    'en'), ('eng',      'en'), ('.en.', 'en'), ('-en-', 'en'), ('_en_', 'en'),
    ('french',     'fr'), ('français', 'fr'), ('francais', 'fr'), ('fre',  'fr'), ('fra',  'fr'), ('.fr.', 'fr'),
    ('spanish',    'es'), ('español',  'es'), ('espanol',  'es'), ('spa',  'es'), ('.es.', 'es'),
    ('german',     'de'), ('deutsch',  'de'), ('ger',  'de'), ('deu',  'de'), ('.de.', 'de'),
    ('italian',    'it'), ('italiano', 'it'), ('ita',  'it'), ('.it.', 'it'),
    ('portuguese', 'pt'), ('portugues','pt'), ('por',  'pt'), ('.pt.', 'pt'),
    ('brazilian',  'pt-br'), ('portuguese-br','pt-br'), ('pob','pt-br'), ('pt-br','pt-br'), ('.pb.', 'pt-br'),
    ('turkish',    'tr'), ('turkce',   'tr'), ('türkçe',   'tr'), ('tur',  'tr'), ('.tr.', 'tr'),
    ('russian',    'ru'), ('russky',   'ru'), ('rus',  'ru'), ('.ru.', 'ru'),
    ('japanese',   'ja'), ('jpn',  'ja'), ('.ja.', 'ja'), ('.jp.', 'ja'),
    ('korean',     'ko'), ('kor',  'ko'), ('.ko.', 'ko'), ('.kr.', 'ko'),
    ('chinese',    'zh'), ('chi',  'zh'), ('zho',  'zh'), ('.zh.', 'zh'), ('.cn.', 'zh'),
    ('hindi',      'hi'), ('hin',  'hi'), ('.hi.', 'hi'),
    ('persian',    'fa'), ('farsi','fa'), ('fas',  'fa'), ('per',  'fa'), ('.fa.', 'fa'),
]


def _guess_lang_from_text(text):
    """Best-effort language detection from a filename/release/display string.

    Returns a normalized language code (e.g. 'ar', 'en', 'pt-br') or '' if
    no hint was found. This is the recovery path for issue #12: external
    Stremio subtitles (especially from SubSource/Wyzie) sometimes ship with
    `lang: 'und'` and put the language only in the filename — we used to
    drop them as 'Unknown', now we mine the filename for a hint.
    """
    if not text:
        return ''
    haystack = str(text).strip().lower()
    if not haystack:
        return ''
    # Pad with separators so .ar. style matches at the boundaries too.
    padded = '.' + haystack.replace(' ', '.').replace('_', '.').replace('-', '.') + '.'
    for token, code in _FILENAME_LANG_HINTS:
        if token in padded:
            return code
    return ''


GENERIC_SUBTITLE_NAMES = {
    'external', 'embedded', 'internal', 'subtitle', 'subtitles', 'sub', 'subs',
    'caption', 'captions', 'closed captions', 'cc', 'sdh'
}


def _clean_subtitle_text(value):
    text = _filename_basename(value)
    text = COLOR_TAG_RE.sub('', text)
    text = REGIONAL_FLAG_RE.sub(' ', text)
    text = STREAM_ICON_RE.sub(' ', text)
    text = re.sub(r'^[0-9a-f]{12,}[_\-\s]*', '', text, flags=re.I)
    text = re.sub(r'^\d{1,3}[._\-\s]+', '', text)
    text = text.replace('_', ' ')
    text = MULTI_WS_RE.sub(' ', text).strip(' -|_.')
    return text


def _subtitle_source_name(sub):
    raw = (sub.get('sourceName') or sub.get('providerName') or
           sub.get('addonName') or sub.get('sourceAddon') or sub.get('addonId') or
           sub.get('providerId') or sub.get('provider') or sub.get('addon') or
           sub.get('source') or sub.get('origin') or '')
    text = _clean_subtitle_text(raw)
    # Avoid showing generic type labels as addon names. The display line should
    # feel like Stremio: language + real addon/source name.
    if text.lower() in GENERIC_SUBTITLE_NAMES or text.lower() in ('addon', 'stream', 'manual', 'subtitle addon'):
        return ''
    return text


def _subtitle_language_info(sub):
    lang = sub.get('lang') or sub.get('language') or sub.get('languageCode') or sub.get('iso639') or 'und'
    lang_key = _normalize_lang(lang)
    if lang_key in ('und', '', None):
        for source_field in (sub.get('displayName'), sub.get('label'),
                             sub.get('title'), sub.get('name'),
                             sub.get('release'), sub.get('filename'),
                             sub.get('fileName'), sub.get('url'), sub.get('id')):
            guessed = _guess_lang_from_text(source_field)
            if guessed:
                lang_key = guessed
                break
    if lang_key in ('und', '', None):
        combined_hint = ' '.join(str(sub.get(k) or '') for k in (
            'sourceName', 'providerName', 'addonName', 'sourceAddon', 'addonId',
            'providerId', 'displayName', 'label', 'title', 'name', 'release',
            'filename', 'fileName', 'url', 'id'
        ))
        guessed = _guess_lang_from_text(combined_hint)
        if guessed:
            lang_key = guessed
    lang_key = lang_key or 'und'
    lang_info = LANG_MAP.get(lang_key, ('🏳️', str(lang).title() if lang else 'Unknown'))
    flag = lang_info[0] or ''
    label = lang_info[1] or (str(lang).title() if lang else 'Unknown')
    code = lang_key.split('-')[0].upper() if lang_key else 'UND'
    return lang_key, flag, label, code


def _subtitle_display_name(sub):
    source_name = _subtitle_source_name(sub)
    source_lc = source_name.lower()
    candidates = [
        sub.get('displayName'), sub.get('label'), sub.get('title'), sub.get('name'),
        sub.get('release'), sub.get('filename'), sub.get('fileName')
    ]
    for value in candidates:
        text = _clean_subtitle_text(value)
        if not text:
            continue
        lowered = text.lower()
        if lowered in GENERIC_SUBTITLE_NAMES:
            continue
        if source_lc and lowered == source_lc:
            continue
        if source_lc and lowered.startswith(source_lc + ' '):
            lowered_tail = lowered[len(source_lc):].strip(' -|_.')
            if lowered_tail in GENERIC_SUBTITLE_NAMES or not lowered_tail:
                continue
        return text
    return ''


def _subtitle_title(sub):
    lang_key, flag, label, code = _subtitle_language_info(sub)
    source_name = _subtitle_source_name(sub)
    display_name = _subtitle_display_name(sub)

    # Stremio-style subtitle label:
    #   🇸🇦 Arabic · [OpenSubtitles v3] · Release/File name
    # Source name is wrapped in brackets so the user can clearly see
    # which addon/provider produced each subtitle result. Avoid noisy
    # internal markers such as ADDON/STREAM unless there is no real
    # addon name to show.
    parts = []
    lang_part = ' '.join([part for part in (flag, label if label else code) if part]).strip()
    if lang_part:
        parts.append(lang_part)
    elif code:
        parts.append(code)

    if source_name:
        parts.append('[COLOR cyan]%s[/COLOR]' % source_name)
    else:
        source_type = str(sub.get('sourceType') or '').strip().lower()
        if source_type == 'stream':
            parts.append('[COLOR grey]Stream[/COLOR]')
        elif source_type == 'manual':
            parts.append('[COLOR grey]Manual[/COLOR]')
        elif source_type == 'addon':
            parts.append('[COLOR grey]Addon[/COLOR]')

    if display_name and (not source_name or display_name.lower() != source_name.lower()):
        parts.append(display_name)
    if sub.get('forced'):
        parts.append('Forced')
    if sub.get('hearingImpaired'):
        parts.append('SDH')
    return ' · '.join([part for part in parts if part]).strip()


def _subtitles_summary(subtitles):
    if not subtitles:
        return ''
    parts = []
    seen = set()
    for sub in subtitles[:4]:
        name = _subtitle_title(sub)
        if name not in seen:
            parts.append(name)
            seen.add(name)
    if len(subtitles) > 4:
        parts.append('+%d' % (len(subtitles) - 4))
    return ' | '.join(parts)

def _stream_badges(video_bits, audio_bits, subtitles):
    wanted = ['2160P', '1080P', '720P', 'DV', 'HDR10+', 'HDR10', 'HDR', 'HEVC', 'AV1', 'ATMOS', 'TRUEHD', 'DTS-HD', 'DTS-X', 'DD+', 'DD', '5.1', '7.1', 'MULTI', 'DUBBED', 'SUBS']
    available = [str(x).upper() for x in (video_bits or []) + (audio_bits or [])]
    tags = []
    for key in wanted:
        if key in available and key not in tags:
            tags.append(key)
    if subtitles and 'SUBS' not in tags:
        tags.append('SUBS')
    return ' • '.join(tags[:8])


def _formatter_payload(row, provider_name, facts):
    try:
        return _source_formatter.format_stream(row or {}, provider_name=provider_name or '', facts=facts or {}) or {'tags': [], 'summary': ''}
    except Exception as exc:
        xbmc.log('[DexHub] formatter failed: %s' % exc, xbmc.LOGDEBUG)
        return {'tags': [], 'summary': ''}


def _stream_facts(row, provider_name):
    values = _collect_stream_texts(row)
    display_name = _stream_display_name(row)
    site = _extract_site(row, provider_name)
    hints = row.get('behaviorHints') or {}
    size = _extract_size(row.get('size'), row.get('videoSize'), hints.get('videoSize') if isinstance(hints, dict) else None, hints.get('size') if isinstance(hints, dict) else None, *values)
    video_bits = []
    for value in _iter_stream_values(row.get('resolution')):
        for item in _extract_video_bits(value):
            if item not in video_bits:
                video_bits.append(item)
    for value in _iter_stream_values(row.get('quality')):
        for item in _extract_video_bits(value):
            if item not in video_bits:
                video_bits.append(item)
    for value in _iter_stream_values(row.get('visualTags')):
        for item in _extract_video_bits(value):
            if item not in video_bits:
                video_bits.append(item)
    for item in _extract_video_bits(*values, display_name):
        if item not in video_bits:
            video_bits.append(item)

    audio_bits = []
    for value in _iter_stream_values(row.get('audioTags')):
        for item in _extract_audio_bits(value):
            if item not in audio_bits:
                audio_bits.append(item)
    for value in _iter_stream_values(row.get('audioChannels')):
        for item in _extract_audio_bits(value):
            if item not in audio_bits:
                audio_bits.append(item)
    for item in _extract_audio_bits(*values, display_name):
        if item not in audio_bits:
            audio_bits.append(item)

    # Regex enrichment: providers often hide codec/audio/source details in
    # filenames/descriptions instead of structured fields. Merge a normalized
    # parse here so the UI can show missing video/audio metadata and filters
    # catch HDR/DV/Atmos/REMUX reliably.
    try:
        from .stream_ranking import parse_stream_traits
        trait_parts = list(values) + [display_name, row.get('name'), row.get('title'), row.get('description'), row.get('quality'), row.get('resolution'), row.get('audioChannels'), json.dumps(hints, ensure_ascii=False) if isinstance(hints, dict) else '']
        traits = parse_stream_traits(*trait_parts)
    except Exception:
        traits = {}
    for item in (traits.get('video_bits') or []):
        if item not in video_bits:
            video_bits.append(item)
    for item in (traits.get('audio_bits') or []):
        if item not in audio_bits:
            audio_bits.append(item)
    subtitles = row.get('subtitles') or []
    badges = _stream_badges(video_bits, audio_bits, subtitles)
    return {
        'display_name': display_name,
        'site': site,
        'size': size,
        'video_bits': video_bits,
        'audio_bits': audio_bits,
        'subtitles': subtitles,
        'badges': badges,
    }


def _stream_label(row, provider_name, index=None):
    facts = _stream_facts(row, provider_name)
    display_name = facts['display_name']
    site = facts['site']
    size = facts['size']
    video_bits = facts['video_bits']
    audio_bits = facts['audio_bits']
    subtitles = facts['subtitles']
    subs = _subtitles_summary(subtitles)
    badges = facts['badges']
    description = _normalize_ascii(row.get('description') or '')
    title = _normalize_ascii(row.get('title') or '')

    prefix = ('%02d. ' % int(index)) if index else ''
    label = '[B]%s%s[/B]' % (prefix, display_name)

    line2 = []
    if size:
        line2.append('SIZE: %s' % size)
    line2.append('VIDEO: %s' % (' | '.join(video_bits[:6]) if video_bits else '--'))
    line2.append('AUDIO: %s' % (' | '.join(audio_bits[:6]) if audio_bits else '--'))
    if site:
        line2.append('SITE: %s' % site)
    if badges:
        line2.append('TAGS: %s' % badges)
    label2 = '    '.join(line2)

    plot_lines = []
    if title and title.upper() != display_name:
        plot_lines.append(title)
    if description and description.upper() not in [x.upper() for x in plot_lines]:
        plot_lines.append(description)
    if subs:
        plot_lines.append('Subtitles: %s' % subs)
    plot = '\n'.join(plot_lines) or display_name
    return label, label2, plot


def _quality_badge(video_bits):
    bits = [str(x).upper() for x in (video_bits or [])]
    if '2160P' in bits or '4K' in bits:
        return '4K', 'FF33E6FF'
    if '1080P' in bits:
        return '1080P', 'FF8B5CFF'
    if '720P' in bits:
        return '720P', 'FF6AA8FF'
    if '480P' in bits:
        return '480P', 'FF7A5AA8'
    return '--', 'FF6F6F86'


def _provider_badge(row, provider_name):
    values = [
        row.get('name'), row.get('title'), row.get('description'), row.get('source'), row.get('provider'), provider_name,
        json.dumps(row.get('behaviorHints') or {}) if isinstance(row.get('behaviorHints'), dict) else ''
    ]
    text = ' '.join(_normalize_ascii(v).lower() for v in values if v)
    if 'realdebrid' in text or 'rd+' in text or re.search(r'\brd\+?\b', text):
        return 'RD+'
    if 'alldebrid' in text or re.search(r'\bad\+?\b', text):
        return 'AD+'
    if 'premiumize' in text or re.search(r'\bpm\+?\b', text):
        return 'PM'
    if 'torbox' in text or re.search(r'\btb\+?\b', text):
        return 'TB'
    if 'easydebrid' in text or 'ed+' in text:
        return 'ED+'
    cleaned = _normalize_ascii(provider_name or '')
    return (cleaned.upper()[:8] if cleaned else 'SRC')


def _source_info_text(row, provider_name):
    parts = []
    addon_name = _extract_addon_name(row, provider_name)
    site_name = _extract_site(row, provider_name)
    if addon_name:
        parts.append('addon: %s' % addon_name)
    if site_name and site_name != addon_name:
        parts.append('site: %s' % site_name)
    for key in ('name','title','filename','description'):
        val = row.get(key)
        if val:
            parts.append('%s: %s' % (key, _clean_stream_text(val)))
    if row.get('subtitles'):
        parts.append('subtitles: %s' % _subtitles_summary(row.get('subtitles') or []))
    hints = row.get('behaviorHints') or {}
    if isinstance(hints, dict) and hints:
        try:
            parts.append('behaviorHints: %s' % json.dumps(hints, ensure_ascii=False, indent=2))
        except Exception:
            pass
    return '\n'.join(parts)




def _collect_playback_subtitles(ctx, manual=False, force_search=False):
    initial = []
    # Try to get a meaningful source name from the stream context.
    # The provider_name is the best bet, but fall back to the stream's
    # addon name or source description so the user sees something useful.
    source_name = (
        ctx.get('provider_name') or
        ctx.get('stream_addon_name') or
        ctx.get('source_provider_name') or
        ctx.get('provider_id') or
        ctx.get('addon_name') or
        ''
    )
    # Clean up provider IDs that look like URLs or UUIDs — not user-friendly
    if source_name and ('/' in source_name or len(source_name) > 40):
        # Probably a manifest URL or UUID — extract a readable portion
        short = source_name.rsplit('/', 1)[-1].split('?')[0]
        if short and len(short) < 40:
            source_name = short
        else:
            source_name = ''
    selected = ctx.get('selected_subtitle')
    if selected:
        if isinstance(selected, dict):
            row = dict(selected)
        else:
            row = {'url': selected, 'id': selected, 'lang': 'und'}
        row.setdefault('sourceType', 'manual')
        row.setdefault('sourceName', source_name)
        initial.append(row)
        if row.get('url') or row.get('key'):
            return initial
    for sub in (ctx.get('subtitles') or []):
        if isinstance(sub, dict):
            row = dict(sub)
        else:
            row = {'url': sub, 'id': sub, 'lang': 'und'}
        row.setdefault('sourceType', 'stream')
        row.setdefault('sourceName', source_name)
        initial.append(row)
    if not manual and initial and _is_plex_like_playback(ctx):
        # Plex/Emby/Jellyfin style streams already expose the external subtitle
        # URLs for the exact file we selected. Hitting the subtitle broker
        # before playback only adds delay and can fail even though matching
        # external subtitles are already attached to the stream.
        return initial
    if not manual and not force_search and _subtitle_search_on_demand_only():
        return initial
    try:
        rows = broker_search_subtitles(ctx, initial_subtitles=initial, max_results=12)
    except Exception as exc:
        xbmc.log('[DexHub] subtitle broker failed: %s' % exc, xbmc.LOGWARNING)
        rows = initial
    return rows or []


def _subtitle_picker_title(ctx):
    title = ctx.get('show_title') or ctx.get('title') or tr('الترجمات')
    season = ctx.get('season')
    episode = ctx.get('episode')
    if season not in (None, '') and episode not in (None, ''):
        try:
            return '%s — S%02dE%02d' % (title, int(season), int(episode))
        except Exception:
            return title
    return title


def _subtitle_pick_for_stream_key(stream_key, current=None):
    ctx = cache_store.get('stream', stream_key) or {}
    if not ctx:
        error('انتهت بيانات المصدر. أعد فتحه.')
        return None
    rows = _collect_playback_subtitles(ctx, manual=True)
    labels = ['بدون ترجمة']
    for row in rows:
        labels.append(_subtitle_title(row))
    if len(labels) == 1:
        notify('لا توجد ترجمات متاحة لهذا المصدر')
        return None
    idx = xbmcgui.Dialog().select(tr('الترجمات — %s') % _subtitle_picker_title(ctx), [tr(x) for x in labels])
    if idx < 0:
        return None
    if idx == 0:
        return {'__clear__': True, '_label': 'بدون ترجمة'}
    chosen = dict(rows[idx - 1])
    chosen['_label'] = labels[idx]
    return chosen


def _companion_context_from_playback(ctx):
    hints = ctx.get('behaviorHints') or {}
    if not isinstance(hints, dict):
        hints = {}
    comp = {}
    for src, dst in (
        ('bootstrapUrl', 'bootstrapUrl'),
        ('companionUrl', 'companionUrl'),
        ('companionScrobbleUrl', 'companionScrobbleUrl'),
        ('companionUnscrobbleUrl', 'companionUnscrobbleUrl'),
        ('sessionIdentifier', 'sessionIdentifier'),
        ('playbackSessionId', 'playbackSessionId'),
        ('clientIdentifier', 'clientIdentifier'),
        ('plexDuration', 'duration_ms'),
        ('serverType', 'server_type'),
        ('serverUrl', 'server_url'),
        ('token', 'token'),
        ('itemId', 'item_id'),
        ('deviceId', 'device_id'),
        ('sessionId', 'session_id'),
        ('durationMs', 'duration_ms'),
    ):
        val = hints.get(src)
        if val not in (None, ''):
            comp[dst] = val
    if comp.get('duration_ms'):
        try:
            comp['duration_ms'] = int(float(comp['duration_ms']))
        except Exception:
            comp['duration_ms'] = int(ctx.get('duration_ms') or 0)
    elif ctx.get('duration_ms'):
        comp['duration_ms'] = int(ctx.get('duration_ms') or 0)
    if not comp.get('clientIdentifier'):
        comp['clientIdentifier'] = hints.get('clientIdentifier') or 'DexHub-Kodi'
    if comp.get('server_type') and isinstance(comp.get('server_type'), str):
        comp['server_type'] = comp['server_type'].lower()
    comp['deviceName'] = 'Kodi'
    comp['product'] = 'Dex Hub'
    if any(comp.get(k) for k in ('companionUrl', 'companionScrobbleUrl', 'companionUnscrobbleUrl')):
        return comp
    if all(ctx.get(k) for k in ('server_type', 'server_url', 'token')):
        direct = {
            'server_type': ctx.get('server_type'),
            'server_url': ctx.get('server_url'),
            'token': ctx.get('token'),
            'duration_ms': int(ctx.get('duration_ms') or 0),
        }
        for key in ('rating_key', 'client_id', 'device_name', 'product', 'product_version', 'item_id', 'device_id', 'session_id'):
            if ctx.get(key):
                direct[key] = ctx.get(key)
        return direct
    return {}

def _play_with_context(ctx, stream_key='', fallback_keys=None, entries_meta=None, use_resolved_url=None):
    """Play a stream via xbmc.Player().play() — matches the original behavior
    that reliably starts playback without leaving an empty folder behind.

    `fallback_keys` is an ordered list of alt stream_keys the background
    service can try if this one fails to start.
    """
    xbmcgui.Window(WINDOW_ID).setProperty(PROP, json.dumps(ctx))
    _monitor_playback('play-request', stream_key=stream_key, title=ctx.get('title') or '', media_type=ctx.get('media_type') or '', canonical_id=ctx.get('canonical_id') or '', provider=ctx.get('provider_name') or ctx.get('provider_id') or '', video_id=ctx.get('video_id') or '', fallback_count=len(list(fallback_keys or [])))
    comp_ctx = _companion_context_from_playback(ctx)
    if comp_ctx:
        for key in ('media_type','canonical_id','video_id','title','show_title','year','season','episode','imdb_id','tmdb_id','tvdb_id','provider_id','provider_name','provider_base_url','subtitles','stream_url','poster','background','clearlogo','resume_seconds','resume_percent'):
            if ctx.get(key) not in (None, ''):
                comp_ctx[key] = ctx.get(key)
        if fallback_keys:
            comp_ctx['fallback_stream_keys'] = list(fallback_keys)
        try:
            _picker_url = _source_picker_url_from_ctx(ctx)
            if _picker_url:
                comp_ctx['source_picker_url'] = _picker_url
        except Exception:
            pass
        next_hint = _compute_next_episode_hint(ctx)
        if next_hint:
            comp_ctx['next_episode'] = next_hint
        save_session(comp_ctx)
    else:
        # Still save fallback + next so service can use them even without companion sync.
        minimal = {'stream_url': ctx.get('stream_url') or ''}
        for key in ('media_type','canonical_id','video_id','title','show_title','year','season','episode','imdb_id','tmdb_id','tvdb_id','provider_id','provider_name','provider_base_url','subtitles','poster','background','clearlogo','resume_seconds','resume_percent'):
            if ctx.get(key) not in (None, ''):
                minimal[key] = ctx.get(key)
        if fallback_keys:
            minimal['fallback_stream_keys'] = list(fallback_keys)
        try:
            _picker_url = _source_picker_url_from_ctx(ctx)
            if _picker_url:
                minimal['source_picker_url'] = _picker_url
        except Exception:
            pass
        next_hint = _compute_next_episode_hint(ctx)
        if next_hint:
            minimal['next_episode'] = next_hint
        save_session(minimal)
    _invalidate_nextup_cache()
    # Always write clearlogo — even when empty — so stale art from the
    # previous item doesn't bleed through to the current one.
    _logo = ctx.get('clearlogo') or ''
    xbmcgui.Window(WINDOW_ID).setProperty('dexhub.clearlogo', _logo)
    xbmcgui.Window(WINDOW_ID).setProperty('clearlogo', _logo)
    xbmcgui.Window(WINDOW_ID).setProperty('tvshow.clearlogo', _logo)
    if ctx.get('poster'):
        xbmcgui.Window(WINDOW_ID).setProperty('dexhub.poster', ctx.get('poster'))
    xbmcgui.Window(WINDOW_ID).setProperty('dexhub.fanart', ctx.get('background') or ctx.get('poster') or neutral_fanart())
    # Mirror the active playback artwork onto the always-alive home window as
    # well. Several skins/player overlays read artwork from Window(10000) or
    # global properties during fullscreen playback, not from our transient
    # custom source window. Without this mirror the clearlogo can be visible in
    # Dex Hub's source picker yet disappear once the actual player takes over.
    try:
        home = xbmcgui.Window(10000)
        logo_value = ctx.get('clearlogo') or ''
        poster_value = ctx.get('poster') or ''
        fanart_value = ctx.get('background') or ctx.get('poster') or neutral_fanart()
        title_value = ctx.get('title') or ''
        plot_value = ctx.get('plot') or ''
        year_value = str(ctx.get('year') or '')
        home.setProperty('dexhub.source.clearlogo', logo_value)
        home.setProperty('dexhub.source.poster', poster_value)
        home.setProperty('dexhub.source.thumb', poster_value)
        home.setProperty('dexhub.source.fanart', fanart_value)
        home.setProperty('dexhub.source.title', title_value)
        home.setProperty('dexhub.source.plot', plot_value)
        home.setProperty('dexhub.source.year', year_value)
        # Publish common global artwork keys too; many fullscreen skins read
        # these instead of the addon's namespaced properties during playback.
        home.setProperty('clearlogo', logo_value)
        home.setProperty('logo', logo_value)
        home.setProperty('tvshow.clearlogo', logo_value)
        home.setProperty('poster', poster_value)
        home.setProperty('thumb', poster_value)
        home.setProperty('fanart', fanart_value)
        home.setProperty('fanart_image', fanart_value)

        # ── Arctic Fuse 3 / Arctic Zephyr 2 skin properties ─────────────
        # These skins read from Window(10000) with specific key names during
        # the fullscreen video OSD and the "Now Playing" widgets.
        home.setProperty('ArcticFuse.NowPlaying.Logo',    logo_value)
        home.setProperty('ArcticFuse.NowPlaying.Thumb',   poster_value)
        home.setProperty('ArcticFuse.NowPlaying.Fanart',  fanart_value)
        home.setProperty('ArcticFuse.NowPlaying.Title',   title_value)
        home.setProperty('ArcticFuse.NowPlaying.Plot',    plot_value)
        home.setProperty('ArcticFuse.NowPlaying.Year',    year_value)
        # Arctic Fuse 3 widget format (used by "currently playing" shelf)
        home.setProperty('ArcticFuse.CurrentlyPlaying',   'true')
        home.setProperty('ArcticFuse.Player.Logo',        logo_value)
        home.setProperty('ArcticFuse.Player.Thumb',       poster_value)
        home.setProperty('ArcticFuse.Player.Fanart',      fanart_value)
        # Season/episode for Arctic Fuse OSD overlay
        if ctx.get('season') and ctx.get('episode'):
            _ep_label = 'S%02dE%02d' % (int(ctx.get('season') or 0), int(ctx.get('episode') or 0))
            home.setProperty('ArcticFuse.NowPlaying.Episode', _ep_label)
            home.setProperty('ArcticFuse.Player.Episode',     _ep_label)
            _show = ctx.get('show_title') or title_value
            home.setProperty('ArcticFuse.NowPlaying.ShowTitle', _show)
            home.setProperty('ArcticFuse.Player.ShowTitle',     _show)
        else:
            home.clearProperty('ArcticFuse.NowPlaying.Episode')
            home.clearProperty('ArcticFuse.Player.Episode')
            home.clearProperty('ArcticFuse.NowPlaying.ShowTitle')
            home.clearProperty('ArcticFuse.Player.ShowTitle')
    except Exception:
        pass
    # IMPORTANT: do NOT clear dexhub.invoked_by_tmdbh here.
    # Clearing it before the player actually starts allows internal click/
    # playback paths to think the TMDb Helper handoff is already over, which
    # can bounce back into TMDb Helper one more time just before playback.
    # The flag is now cleared on real playback lifecycle events instead.

    stream_url = ctx.get('stream_url') or ''
    if not stream_url:
        _clear_tmdbh_transient()
        _clear_source_transient_props(clear_global=True)
        _monitor_playback('play-missing-url', level=xbmc.LOGERROR, stream_key=stream_key, title=ctx.get('title') or '', canonical_id=ctx.get('canonical_id') or '')
        # Signal Kodi that resolve failed — without this, the busy spinner
        # hangs indefinitely when a HANDLE-based invocation has no URL.
        if HANDLE >= 0:
            try:
                xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
            except Exception:
                pass
        error('لا يوجد رابط تشغيل')
        return

    item = xbmcgui.ListItem(path=stream_url)
    _is_ep = bool(ctx.get('season') or ctx.get('episode'))
    info = {
        'title':      ctx.get('title') or '',
        'year':       int(ctx.get('year') or 0),
        'mediatype':  'episode' if _is_ep else 'movie',
    }
    # Always include season/episode (even as 0) so Kodi populates
    # VideoPlayer.Season / VideoPlayer.Episode for subtitle addons.
    if _is_ep:
        info['season']  = int(ctx.get('season') or 0)
        info['episode'] = int(ctx.get('episode') or 0)
        if ctx.get('show_title'):
            info['tvshowtitle'] = ctx.get('show_title')
    if ctx.get('imdb_id'):
        info['imdbnumber'] = ctx.get('imdb_id')
    try:
        item.setInfo('video', info)
    except Exception:
        pass
    _apply_unique_ids(item, {'imdb_id': ctx.get('imdb_id') or '', 'tmdb_id': ctx.get('tmdb_id') or '', 'tvdb_id': ctx.get('tvdb_id') or ''}, info)
    # ── DexWorld subtitle service bridge ────────────────────────────────
    # service.subtitles.dexworld reads VideoPlayer.* infolabels. Kodi only
    # populates those AFTER the player starts, and only when setInfo() has
    # been processed. As an extra safety net we also write the IDs as
    # Window(10000) properties; the subtitle service reads these as fallback
    # so it always has the content IDs even before VideoPlayer is ready.
    try:
        _sub_home = xbmcgui.Window(10000)
        _sub_home.setProperty('dexhub.sub.imdb_id',  ctx.get('imdb_id') or '')
        _sub_home.setProperty('dexhub.sub.tmdb_id',  ctx.get('tmdb_id') or '')
        _sub_home.setProperty('dexhub.sub.tvdb_id',  ctx.get('tvdb_id') or '')
        _sub_home.setProperty('dexhub.sub.season',   str(int(ctx.get('season') or 0)) if _is_ep else '')
        _sub_home.setProperty('dexhub.sub.episode',  str(int(ctx.get('episode') or 0)) if _is_ep else '')
        _sub_home.setProperty('dexhub.sub.title',    ctx.get('title') or '')
        _sub_home.setProperty('dexhub.sub.mediatype','episode' if _is_ep else 'movie')
    except Exception:
        pass
    item.setProperty('IsPlayable', 'true')
    art = {
        'thumb': ctx.get('poster') or '', 'poster': ctx.get('poster') or '', 'fanart': ctx.get('background') or ctx.get('poster') or neutral_fanart(),
        'clearlogo': ctx.get('clearlogo') or '', 'logo': ctx.get('clearlogo') or '', 'tvshow.clearlogo': ctx.get('clearlogo') or '',
    }
    try:
        item.setArt(art)
    except Exception:
        pass
    try:
        item.setProperties({
            'clearlogo': ctx.get('clearlogo') or '',
            'logo': ctx.get('clearlogo') or '',
            'tvshow.clearlogo': ctx.get('clearlogo') or '',
            'fanart_image': ctx.get('background') or ctx.get('poster') or neutral_fanart(),
            'poster': ctx.get('poster') or '',
            'thumb': ctx.get('poster') or '',
        })
    except Exception:
        pass
    force_subtitles = bool(ctx.get('play_with_subtitles'))
    subtitle_rows = _collect_playback_subtitles(ctx, force_search=force_subtitles)
    prepared_subs = _prepare_subtitle_files(
        subtitle_rows,
        stream_key or 'play',
        prefer_local_copy=(_is_plex_like_playback(ctx) or any(str((row or {}).get('sourceType') or '').strip().lower() == 'stream' for row in (subtitle_rows or []))),
    )
    subs = [row.get('path') for row in prepared_subs if row.get('path')]
    if force_subtitles and not subs:
        try:
            notify('لم يتم العثور على ترجمة مطابقة لهذا المصدر')
        except Exception:
            pass
    selected_subtitle_index = -1
    selected_subtitle_path = ''
    if subs and (force_subtitles or ctx.get('selected_subtitle')):
        try:
            selected_subtitle_index = _pick_default_subtitle_index(subtitle_rows, ctx)
        except Exception:
            selected_subtitle_index = 0
        if selected_subtitle_index < 0 or selected_subtitle_index >= len(subs):
            selected_subtitle_index = 0
        selected_subtitle_path = subs[selected_subtitle_index] if subs else ''
    if subs:
        try:
            item.setSubtitles(subs)
        except Exception:
            pass
    # Original, proven approach: xbmc.Player().play() starts playback on its
    # own thread. We previously sat here for 6 seconds polling isPlayingVideo
    # to apply the subtitle and resume seek — but that kept the Python
    # invoker alive, which in turn kept Kodi's busy spinner on screen even
    # when playback had already started. Symptom: "loading spinner stays
    # even when the movie plays".
    #
    # The fix: kick off Player.play synchronously (so Kodi knows we have
    # started), then hand off the post-start chores (subtitles, seek) to a
    # background thread, and return immediately. The plugin invoker
    # finishes, the busy dialog clears, and the post-start work runs while
    # playback already shows on screen.
    resume_seconds = 0.0
    try:
        resume_seconds = float(ctx.get('resume_seconds') or 0.0)
    except Exception:
        resume_seconds = 0.0
    resume_percent = 0.0
    try:
        resume_percent = float(ctx.get('resume_percent') or 0.0)
    except Exception:
        resume_percent = 0.0

    # Explicitly close any busy dialog Kodi opened on our behalf BEFORE we
    # start playback, so the user sees the player loading screen instead of
    # a spinner stuck on top of the previous window.
    for dlg in ('busydialog', 'busydialognocancel'):
        try:
            xbmc.executebuiltin('Dialog.Close(%s,true)' % dlg)
        except Exception:
            pass

    # Open the branded wait window BEFORE the handoff so the user
    # sees the correct poster + provider + plot instead of Kodi's
    # generic busy spinner. This now runs for BOTH setResolvedUrl
    # and Player.play paths. `reuselanguageinvoker=true` keeps the
    # Python VM alive after the plugin script returns, so the
    # waiter's background monitor thread survives to close the
    # window when playback actually starts.
    _waiter = PlaybackWaiter(ctx)
    _waiter.open()
    try:
        try:
            current_action = dict(parse_qsl(sys.argv[2].lstrip('?'))).get('action', '')
        except Exception:
            current_action = ''
        if use_resolved_url is None:
            use_resolved_url = (HANDLE >= 0 and current_action in (
                'play_item', 'cw_resume', 'cw_play_from_start', 'play',
                # NOTE: 'tmdb_player' intentionally excluded.
                # dexhub.json uses dialog:false so TMDb Helper fires the URL
                # and exits immediately — there is no open HANDLE to resolve.
                # DexHub uses player.play() directly in that flow.
            ))
            try:
                if float(ctx.get('resume_seconds') or 0.0) > 1.0 or (1.0 < float(ctx.get('resume_percent') or 0.0) < 95.0):
                    use_resolved_url = False
            except Exception:
                pass
        if str(stream_url or '').lower().startswith(('plugin://', 'magnet:')):
            # Torrent handoffs (Elementum/Quasar/Torrest) are plugins, not raw
            # media files. setResolvedUrl can leave Kodi trying to resolve the
            # plugin URL as a file; Player.play dispatches it correctly.
            use_resolved_url = False
        if use_resolved_url:
            _monitor_playback('play-handoff', handoff='setResolvedUrl', handle=HANDLE, stream_key=stream_key, provider=ctx.get('provider_name') or ctx.get('provider_id') or '')
            xbmcplugin.setResolvedUrl(HANDLE, True, item)
        else:
            _monitor_playback('play-handoff', handoff='Player.play', handle=HANDLE, stream_key=stream_key, provider=ctx.get('provider_name') or ctx.get('provider_id') or '')
            xbmc.Player().play(stream_url, item)
        # Auto-close the wait window as soon as AV actually starts.
        _waiter.close_on_av_start()
    except Exception as exc:
        _monitor_playback('play-handoff-failed', level=xbmc.LOGERROR, error=exc, stream_key=stream_key, title=ctx.get('title') or '', provider=ctx.get('provider_name') or ctx.get('provider_id') or '')
        xbmc.log('[DexHub] playback handoff failed: %s' % exc, xbmc.LOGERROR)
        # Tear down the wait window on error so the user isn't stuck
        # staring at a spinner that will never resolve.
        try:
            _waiter.close()
        except Exception:
            pass
        if not use_resolved_url:
            try:
                xbmc.Player().play(stream_url, item)
                _monitor_playback('play-handoff-recovered', stream_key=stream_key, provider=ctx.get('provider_name') or ctx.get('provider_id') or '')
                return
            except Exception as exc2:
                xbmc.log('[DexHub] fallback Player.play failed: %s' % exc2, xbmc.LOGERROR)
        _clear_tmdbh_transient()
        _clear_source_transient_props(clear_global=True)
        return

    # Apply subtitle + resume in a background thread so this function can
    # return and Kodi can clean up the spinner. We wait up to 20s for the
    # player to actually begin (Plex/Plexio over CDN can be slow), check
    # every 250ms.
    def _post_start_chores(_subtitle_path=selected_subtitle_path,
                           _subtitle_index=selected_subtitle_index,
                           _resume=resume_seconds,
                           _resume_pct=resume_percent):
        _started = False
        try:
            # Wait up to 25s (100 × 250ms) for real media to begin.
            for _ in range(100):
                xbmc.sleep(250)
                try:
                    player = xbmc.Player()
                    if not _player_has_real_media(player):
                        continue
                    if not _started:
                        _started = True
                        _monitor_playback('play-started', stream_key=stream_key,
                                          title=ctx.get('title') or '',
                                          provider=ctx.get('provider_name') or ctx.get('provider_id') or '')
                        # Give the player a moment to stabilise before seeking
                        # or applying subtitles — Plex/CDN streams can take
                        # 1-3 seconds to buffer past the first keyframe.
                        xbmc.sleep(800)
                except Exception:
                    continue

                if _subtitle_path:
                    try:
                        try:
                            player.showSubtitles(False)
                        except Exception:
                            pass
                        applied = False
                        if _subtitle_index is not None and int(_subtitle_index) >= 0:
                            try:
                                player.setSubtitleStream(int(_subtitle_index))
                                player.showSubtitles(True)
                                applied = True
                            except Exception:
                                applied = False
                        if not applied:
                            player.setSubtitles(_subtitle_path)
                            player.showSubtitles(True)
                    except Exception:
                        pass
                    _subtitle_path = ''
                    _subtitle_index = -1

                # Bug fix (3.7.91): if we don't have an exact resume_seconds
                # but we DO have a percent (e.g. Trakt-imported row whose
                # runtime wasn't returned by /sync/playback), compute the
                # target from the player's actual reported duration once it
                # starts. This rescues "starts from 0" on legacy Trakt rows.
                if _resume <= 1.0 and _resume_pct > 1.0 and _resume_pct < 95.0:
                    try:
                        total = float(player.getTotalTime() or 0.0)
                    except Exception:
                        total = 0.0
                    if total > 60.0:
                        _resume = max(0.0, total * _resume_pct / 100.0)
                        xbmc.log('[DexHub] resume from percent fallback: %.1f%% × %.1fs = %.1fs' % (_resume_pct, total, _resume), xbmc.LOGINFO)
                    _resume_pct = 0.0

                if _resume > 1.0:
                    target    = max(0.0, float(_resume))
                    threshold = _resume_success_threshold(target)
                    # Try up to 6 times with increasing wait — streams that
                    # buffer slowly need more time between seek attempts.
                    for _seek_try in range(6):
                        try:
                            player.seekTime(target)
                        except Exception:
                            pass
                        wait_ms = 900 + _seek_try * 200
                        xbmc.sleep(wait_ms)
                        try:
                            current = float(player.getTime() or 0.0)
                        except Exception:
                            current = 0.0
                        if current >= threshold:
                            break
                    _resume = 0.0

                # Both chores done — exit the loop.
                if not _subtitle_path and _resume <= 1.0 and _resume_pct <= 1.0:
                    return
        except Exception as exc:
            _monitor_playback('play-post-start-error', level=xbmc.LOGWARNING,
                              error=exc, stream_key=stream_key,
                              title=ctx.get('title') or '')
            xbmc.log('[DexHub] post-start chores failed: %s' % exc, xbmc.LOGDEBUG)
        if not _started:
            _monitor_playback('play-start-timeout', level=xbmc.LOGWARNING,
                              stream_key=stream_key, title=ctx.get('title') or '',
                              provider=ctx.get('provider_name') or ctx.get('provider_id') or '')

    # Always start the post-start thread — it handles resume AND subtitles.
    # Previously it was skipped when both were absent, which meant a resume
    # call with resume_seconds from a CW row silently had no effect if
    # selected_subtitle_path happened to be empty at the same time.
    try:
        threading.Thread(target=_post_start_chores,
                         name='DexHubPlayPost', daemon=True).start()
    except Exception:
        pass

def _compute_next_episode_hint(ctx):
    """Return next-episode playback URL info if current playback is an episode
    and a next episode exists."""
    try:
        season = int(ctx.get('season') or 0)
        episode = int(ctx.get('episode') or 0)
    except Exception:
        return None
    canonical = ctx.get('canonical_id') or ''
    media_type = (ctx.get('media_type') or '').lower()
    if not canonical or season <= 0 or episode <= 0 or media_type not in ('series', 'anime', 'show', 'tv'):
        return None
    # Look up the show's video list from the window prop set by series_meta().
    try:
        raw = xbmcgui.Window(WINDOW_ID).getProperty(SERIES_PROP_PREFIX + canonical) or ''
        videos = json.loads(raw) if raw else []
    except Exception:
        videos = []
    if not videos:
        return None
    # Find next episode — same season & ep+1, else season+1 & ep1.
    candidates = [
        (season, episode + 1),
        (season + 1, 1),
    ]
    for s, e in candidates:
        for v in videos:
            try:
                if int(v.get('season') or 0) == s and int(v.get('episode') or 0) == e:
                    return {
                        'canonical_id': canonical,
                        'video_id': v.get('id') or canonical,
                        'season': s,
                        'episode': e,
                        'title': ctx.get('show_title') or ctx.get('title') or canonical,
                    }
            except Exception:
                continue
    return None


def _source_window_meta_from_entries(entries, meta=None):
    merged = dict(meta or {})
    try:
        home = xbmcgui.Window(10000)
    except Exception:
        home = None
    for entry in list(entries or []):
        try:
            ctx = cache_store.get('stream', entry.get('stream_key') or '') or {}
        except Exception:
            ctx = {}
        if not isinstance(ctx, dict) or not ctx:
            continue
        if not merged.get('poster'):
            merged['poster'] = ctx.get('poster') or ''
        if not merged.get('fanart'):
            merged['fanart'] = ctx.get('background') or ctx.get('poster') or ''
        if not merged.get('clearlogo'):
            merged['clearlogo'] = ctx.get('clearlogo') or ''
        if not merged.get('title'):
            merged['title'] = ctx.get('show_title') or ctx.get('originaltitle') or ctx.get('title') or ''
        if not merged.get('originaltitle'):
            merged['originaltitle'] = ctx.get('originaltitle') or ctx.get('show_title') or ''
        if not merged.get('plot'):
            merged['plot'] = ctx.get('plot') or ctx.get('stream_description') or ''
        if not merged.get('tmdb_id'):
            merged['tmdb_id'] = ctx.get('tmdb_id') or ''
        if not merged.get('imdb_id'):
            merged['imdb_id'] = ctx.get('imdb_id') or ''
        if not merged.get('tvdb_id'):
            merged['tvdb_id'] = ctx.get('tvdb_id') or ''
        if not merged.get('media_type'):
            merged['media_type'] = ctx.get('media_type') or ''
        if not merged.get('year'):
            merged['year'] = ctx.get('year') or ''
        if merged.get('poster') and merged.get('fanart') and merged.get('title'):
            break
    try:
        if home:
            if not merged.get('poster'):
                merged['poster'] = home.getProperty('dexhub.source.poster') or ''
            if not merged.get('fanart'):
                merged['fanart'] = home.getProperty('dexhub.source.fanart') or ''
            if not merged.get('clearlogo'):
                merged['clearlogo'] = home.getProperty('dexhub.source.clearlogo') or ''
            if not merged.get('title'):
                merged['title'] = home.getProperty('dexhub.source.title') or ''
            if not merged.get('plot'):
                merged['plot'] = home.getProperty('dexhub.source.plot') or ''
            if not merged.get('year'):
                merged['year'] = home.getProperty('dexhub.source.year') or ''
    except Exception:
        pass
    if not merged.get('poster'):
        merged['poster'] = merged.get('fanart') or ''
    return merged


def _current_source_ui_meta(meta=None):
    merged = dict(meta or {})
    try:
        win = xbmcgui.Window(WINDOW_ID)
    except Exception:
        win = None
    try:
        home = xbmcgui.Window(10000)
    except Exception:
        home = None

    def _first(*values):
        for value in values:
            if value not in (None, ''):
                return value
        return ''

    poster = _first(
        home.getProperty('dexhub.source.poster') if home else '',
        home.getProperty('dexhub.source.thumb') if home else '',
        win.getProperty('dexhub.poster') if win else '',
        win.getProperty('poster') if win else '',
        xbmc.getInfoLabel('ListItem.Art(poster)'),
        xbmc.getInfoLabel('ListItem.Art(tvshow.poster)'),
        xbmc.getInfoLabel('ListItem.Art(thumb)'),
        merged.get('poster'),
        merged.get('thumb'),
    )
    fanart = _first(
        home.getProperty('dexhub.source.fanart') if home else '',
        win.getProperty('dexhub.fanart') if win else '',
        win.getProperty('fanart') if win else '',
        xbmc.getInfoLabel('ListItem.Art(fanart)'),
        xbmc.getInfoLabel('ListItem.Property(fanart_image)'),
        merged.get('background'),
        merged.get('fanart'),
        poster,
    )
    clearlogo = _first(
        home.getProperty('dexhub.source.clearlogo') if home else '',
        win.getProperty('dexhub.clearlogo') if win else '',
        win.getProperty('clearlogo') if win else '',
        win.getProperty('tvshow.clearlogo') if win else '',
        xbmc.getInfoLabel('ListItem.Art(clearlogo)'),
        xbmc.getInfoLabel('ListItem.Art(tvshow.clearlogo)'),
        xbmc.getInfoLabel('ListItem.Art(logo)'),
        merged.get('clearlogo'),
        merged.get('logo'),
    )
    title = _first(
        home.getProperty('dexhub.source.title') if home else '',
        xbmc.getInfoLabel('ListItem.Title'),
        xbmc.getInfoLabel('ListItem.Label'),
        merged.get('title'),
        merged.get('name'),
    )
    plot = _first(
        home.getProperty('dexhub.source.plot') if home else '',
        xbmc.getInfoLabel('ListItem.Plot'),
        merged.get('plot'),
        merged.get('description'),
    )
    year = _first(
        home.getProperty('dexhub.source.year') if home else '',
        xbmc.getInfoLabel('ListItem.Year'),
        merged.get('year'),
    )
    if poster:
        merged['poster'] = poster
    if fanart:
        merged['fanart'] = fanart
        merged['background'] = fanart
    elif poster:
        merged['fanart'] = poster
        merged['background'] = poster
    if clearlogo:
        merged['clearlogo'] = clearlogo
        merged['logo'] = clearlogo
    if title and not merged.get('title'):
        merged['title'] = title
    if plot and not merged.get('plot'):
        merged['plot'] = plot
    if year and not merged.get('year'):
        merged['year'] = year
    return merged


def _show_stream_window(entries, meta, session_key=''):
    meta = _source_window_meta_from_entries(entries, meta)
    meta = _source_window_meta_fallback(meta)
    chosen_key = None
    play_with_subtitles = False
    play_mode = _subtitle_pick_mode_setting()
    try:
        for _dlg in ('busydialog', 'busydialognocancel'):
            try:
                xbmc.executebuiltin('Dialog.Close(%s,true)' % _dlg)
            except Exception:
                pass
        result = open_sources_window(entries, meta, play_mode=play_mode, session_key=session_key)
        if isinstance(result, dict):
            chosen_key = result.get('stream_key')
            play_with_subtitles = bool(result.get('play_with_subtitles'))
        else:
            chosen_key = result
    except Exception as exc:
        xbmc.log('[DexHub] source window failed, using dialog fallback: %s' % exc, xbmc.LOGWARNING)
        labels = [e.get('name') or e.get('label2') or e.get('stream_key') or 'Stream' for e in entries]
        idx = xbmcgui.Dialog().select(tr(meta.get('title') or 'اختر المصدر'), [tr(x) for x in labels])
        if idx >= 0 and idx < len(entries):
            chosen_key = entries[idx].get('stream_key')
            if play_mode == 'ask':
                play_choice = xbmcgui.Dialog().select(tr('اختر طريقة التشغيل'), [tr('تشغيل'), tr('تشغيل مع ترجمة')])
                if play_choice < 0:
                    chosen_key = None
                else:
                    play_with_subtitles = (play_choice == 1)
            else:
                play_with_subtitles = (play_mode == 'play_with_subtitles')
    if chosen_key:
        ctx = cache_store.get('stream', chosen_key)
        if ctx:
            ctx = dict(ctx or {})
            # Preserve exactly the artwork currently shown in the source UI and
            # forward it to the wait window + player overlay. This prevents TMDb
            # fallback art from replacing the correct XML/source artwork.
            meta = _current_source_ui_meta(meta)
            for _art_key in ('clearlogo', 'poster', 'background'):
                _meta_val = meta.get(_art_key) or meta.get('fanart' if _art_key == 'background' else _art_key)
                if _meta_val:
                    ctx[_art_key] = _meta_val
            # Propagate plot/year/title/media_type so the wait window can
            # render the full right panel without a TMDb DB round-trip.
            for _txt_key in ('plot', 'title', 'year', 'media_type'):
                _txt_val = meta.get(_txt_key)
                if _txt_val and not ctx.get(_txt_key):
                    ctx[_txt_key] = _txt_val
            ctx['play_with_subtitles'] = bool(play_with_subtitles)
            fallback = [e.get('stream_key') for e in entries if e.get('stream_key') and e.get('stream_key') != chosen_key]
            # Pre-emptively close any spinner so it doesn't sit on top of the
            # video player after playback starts. Symptom this fixes:
            # "loading spinner stays even when the movie plays".
            for _dlg in ('busydialog', 'busydialognocancel'):
                try:
                    xbmc.executebuiltin('Dialog.Close(%s,true)' % _dlg)
                except Exception:
                    pass
            _remember_source_choice(ctx)
            try:
                current_action = dict(parse_qsl(sys.argv[2].lstrip('?'))).get('action', '')
            except Exception:
                current_action = ''
            # dialog:false in dexhub.json → no open HANDLE for tmdb_player.
            use_resolved = (HANDLE >= 0 and current_action in (
                'play_item', 'cw_resume', 'cw_play_from_start', 'play',
            ))
            try:
                _needs_resume_seek = float(ctx.get('resume_seconds') or 0.0) > 1.0 or (1.0 < float(ctx.get('resume_percent') or 0.0) < 95.0)
            except Exception:
                _needs_resume_seek = False
            if _needs_resume_seek:
                # Match the known-good resume behavior from the older builds:
                # keep playback in Player.play() so our post-start seek thread
                # stays in control instead of relying on Kodi's setResolvedUrl
                # timing for resumed items.
                use_resolved = False
            _play_with_context(ctx, chosen_key, fallback_keys=fallback[:1], use_resolved_url=use_resolved)
            # When setResolvedUrl was called, the HANDLE is already consumed.
            # Calling endOfDirectory on the same HANDLE would cause a Kodi
            # "Handle not found" error and can trigger a second TMDb Helper
            # invocation. Skip it entirely in that case.
            if use_resolved:
                return
    else:
        _clear_tmdbh_transient()
    try:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=True, updateListing=False, cacheToDisc=False)
    except Exception:
        pass


def _safe_subtitle_filename_part(value, limit=48):
    text = _clean_subtitle_text(value)
    text = re.sub(r'[^\w\- ]+', ' ', text, flags=re.UNICODE)
    text = MULTI_WS_RE.sub(' ', text).strip(' -|_.')
    return text[:limit].strip()



def _subtitle_url_needs_local_copy(url):
    text = str(url or '').strip().lower()
    if not text:
        return False
    if text.startswith(('http://', 'https://', 'plugin://', 'ftp://', 'ftps://', 'smb://', 'nfs://', 'special://')):
        return False
    return True


def _prepare_subtitle_files(subtitles, stream_key, prefer_local_copy=False):
    if not subtitles:
        return []
    try:
        if not xbmcvfs.exists(SUBS_DIR):
            xbmcvfs.mkdirs(SUBS_DIR)
    except Exception:
        pass
    safe_stream_dir = re.sub(r'[^\w\-]+', '_', str(stream_key or 'play')).strip('_') or 'play'
    playback_dir = os.path.join(SUBS_DIR, safe_stream_dir[:80])
    try:
        if not xbmcvfs.exists(playback_dir):
            xbmcvfs.mkdirs(playback_dir)
    except Exception:
        playback_dir = SUBS_DIR
    out = []
    used_filenames = set()
    for idx, sub in enumerate(subtitles, start=1):
        sub_url = sub.get('url') or sub.get('key')
        if not sub_url:
            continue
        lang_key, flag, label, code = _subtitle_language_info(sub)
        fmt = str(sub.get('format') or sub.get('codec') or 'srt').lower().replace('/', '').strip('.') or 'srt'
        source_name = _subtitle_source_name(sub)
        display_name = _subtitle_display_name(sub)
        display_code = code or (lang_key.split('-')[0].upper() if lang_key else 'UND')

        # Kodi displays external subtitles using the local filename.
        # Format: SourceName - Language - DisplayName.srt
        # Source name first so the user immediately sees which addon
        # provided the subtitle. No numeric prefix — uniqueness is
        # handled by appending (2), (3) etc. on collision.
        lang_label = (label if label and label.lower() != 'unknown' else display_code)
        lang_part = ('%s %s' % (flag, lang_label)).strip() if flag else lang_label
        lang_part = re.sub(r'[<>:"/\\|?*]+', ' ', lang_part).strip() or display_code
        safe_source = _safe_subtitle_filename_part(source_name, 36) if source_name else ''
        safe_display = _safe_subtitle_filename_part(display_name, 44) if display_name else ''

        # Build: [Source] - Lang - [Display]
        filename_parts = []
        if safe_source:
            filename_parts.append(safe_source)
        else:
            # Fallback: use sourceType so user sees *something*
            source_type = str(sub.get('sourceType') or '').strip().lower()
            if source_type == 'stream':
                filename_parts.append('Stream')
            elif source_type:
                filename_parts.append(source_type.title())
        filename_parts.append(lang_part)
        if safe_display and safe_display.lower() != safe_source.lower():
            filename_parts.append(safe_display)

        base_name = ' - '.join([part for part in filename_parts if part])
        # Ensure unique filename — append (N) on collision
        candidate = base_name
        collision_counter = 1
        while candidate.lower() in used_filenames:
            collision_counter += 1
            candidate = '%s (%d)' % (base_name, collision_counter)
        used_filenames.add(candidate.lower())
        filename = '%s.%s' % (candidate, fmt)

        local_path = os.path.join(playback_dir, filename)
        final_path = sub_url
        try:
            # Old stable behavior: always try to copy to special://temp so Kodi
            # shows the friendly filename/flag. Fall back to the original URL
            # only if the copy fails.
            should_copy = True
            if should_copy:
                if not xbmcvfs.exists(local_path):
                    xbmcvfs.copy(sub_url, local_path)
                if xbmcvfs.exists(local_path):
                    final_path = local_path
        except Exception:
            final_path = sub_url
        out.append({'path': final_path, 'subtitle': sub, 'lang_key': lang_key})
    return out




def _size_to_bytes(value):
    from .stream_ranking import size_to_bytes
    return size_to_bytes(value)


def _quality_rank(value):
    from .stream_ranking import quality_rank
    return quality_rank(value)


def _entry_text_blob(entry):
    from .stream_ranking import entry_text_blob
    return entry_text_blob(entry)


def _is_cam_entry(entry):
    from .stream_ranking import is_cam_entry
    return is_cam_entry(entry)


def _is_debrid_entry(entry):
    from .stream_ranking import is_debrid_entry
    return is_debrid_entry(entry)


def _entry_matches_last_source(entry, pref):
    from .stream_ranking import entry_matches_last_source
    return entry_matches_last_source(entry, pref)


def _min_quality_required_rank():
    raw = ADDON.getSetting('min_quality') or 'No filter'
    from .stream_ranking import _min_quality_required_rank as _ranker_min_quality_required_rank
    return _ranker_min_quality_required_rank(raw)


def _filter_stream_entries(entries):
    from .stream_ranking import source_settings, filter_stream_entries
    return filter_stream_entries(entries, source_settings(ADDON))


def _stream_sort_key(entry, preferred_source=None):
    from .stream_ranking import source_settings, stream_sort_key
    return stream_sort_key(entry, source_settings(ADDON), preferred_source=preferred_source)


def _renumber_stream_entries(entries):
    from .stream_ranking import renumber_stream_entries
    return renumber_stream_entries(entries)


def _finalize_stream_entries(entries, resort=True, media_type='', canonical_id='', video_id=''):
    preferred_source = _last_source_choice(media_type, canonical_id, video_id)
    from .stream_ranking import source_settings
    return _rank_finalize_stream_entries(entries, source_settings(ADDON), preferred_source=preferred_source, resort=resort)


def _append_stream_entries(entries, provider, request_id, media_type, canonical_id, best_meta, art, bg, ids, title='', video_id=None, season=None, episode=None, show_title=''):
    provider_name = provider.get('name') or 'Provider'
    try:
        data = fetch_streams(provider, media_type, request_id)
    except Exception:
        return
    _append_stream_entries_from_data(entries, data, provider, request_id, media_type, canonical_id, best_meta, art, bg, ids, title=title, video_id=video_id, season=season, episode=episode, show_title=show_title)


def _kodi_header_string(headers):
    """Return Kodi's URL header suffix from a dict/list of HTTP headers."""
    if not headers:
        return ''
    pairs = []
    try:
        if isinstance(headers, dict):
            iterable = headers.items()
        elif isinstance(headers, (list, tuple)):
            iterable = headers
        else:
            iterable = []
        for key, value in iterable:
            key = str(key or '').strip()
            if not key or value in (None, ''):
                continue
            pairs.append((key, str(value)))
    except Exception:
        pairs = []
    if not pairs:
        return ''
    try:
        return urlencode(pairs)
    except Exception:
        return '&'.join('%s=%s' % (quote_plus(k), quote_plus(v)) for k, v in pairs)


def _stream_row_request_headers(row):
    """Extract request headers from Stremio stream rows.

    AIOStreams/Torrentio-style addons can attach headers either at the top
    level (`requestHeaders`) or under `behaviorHints.proxyHeaders.request`.
    Kodi needs those encoded after a `|` suffix on the playable URL.
    """
    if not isinstance(row, dict):
        return {}
    out = {}

    def _merge(value):
        if not value:
            return
        try:
            if isinstance(value, dict):
                iterator = value.items()
            elif isinstance(value, (list, tuple)):
                iterator = value
            else:
                return
            for k, v in iterator:
                k = str(k or '').strip()
                if k and v not in (None, ''):
                    out[k] = str(v)
        except Exception:
            pass

    _merge(row.get('requestHeaders'))
    _merge(row.get('headers'))
    hints = row.get('behaviorHints') or {}
    if isinstance(hints, dict):
        _merge(hints.get('requestHeaders'))
        proxy_headers = hints.get('proxyHeaders') or {}
        if isinstance(proxy_headers, dict):
            _merge(proxy_headers.get('request'))
            # Some implementations put the request headers directly under
            # proxyHeaders instead of nesting them under "request".
            if not any(k in proxy_headers for k in ('request', 'response')):
                _merge(proxy_headers)
    return out


def _apply_kodi_request_headers(url, row):
    url = str(url or '').strip()
    if not url:
        return ''
    # Plugin URLs should receive their own query params, not Kodi pipe headers.
    if url.lower().startswith('plugin://'):
        return url
    headers = _stream_row_request_headers(row)
    suffix = _kodi_header_string(headers)
    if not suffix:
        return url
    if '|' in url:
        base, existing = url.split('|', 1)
        if existing:
            return base + '|' + existing + '&' + suffix
        return base + '|' + suffix
    return url + '|' + suffix


def _torrent_handoff_url(magnet):
    """Return a Kodi plugin handoff URL for a magnet when a torrent player exists."""
    magnet = str(magnet or '').strip()
    if not magnet:
        return ''
    # Elementum is the most common Kodi torrent player and understands the
    # Stremio-style magnet handoff reliably. Quasar uses a compatible route.
    for addon_id, template in (
        ('plugin.video.elementum', 'plugin://plugin.video.elementum/play?uri=%s'),
        ('plugin.video.quasar', 'plugin://plugin.video.quasar/play?uri=%s'),
        # Torrest route support varies by build, but this is harmless when
        # installed and gives users another local torrent player option.
        ('plugin.video.torrest', 'plugin://plugin.video.torrest/play_magnet?magnet=%s'),
    ):
        try:
            xbmcaddon.Addon(addon_id)
            return template % quote_plus(magnet)
        except Exception:
            continue
    # Kodi cannot natively resolve magnets, but returning the magnet keeps the
    # source visible and lets any external/magnet handler attempt playback.
    return magnet


def _magnet_from_stream_row(row):
    if not isinstance(row, dict):
        return ''
    raw_url = str(row.get('url') or '').strip()
    if raw_url.lower().startswith('magnet:'):
        return raw_url
    hints = row.get('behaviorHints') or {}
    if not isinstance(hints, dict):
        hints = {}
    info_hash = (
        row.get('infoHash') or row.get('infohash') or row.get('btih') or
        hints.get('infoHash') or hints.get('infohash') or hints.get('btih') or ''
    )
    info_hash = re.sub(r'[^A-Fa-f0-9]', '', str(info_hash or '')).strip()
    if len(info_hash) not in (32, 40):
        return ''
    name = (
        row.get('title') or row.get('name') or row.get('filename') or
        hints.get('filename') or hints.get('title') or hints.get('name') or
        'DexHub torrent'
    )
    trackers = []
    for value in (row.get('sources') or hints.get('sources') or []):
        text = str(value or '').strip()
        if not text:
            continue
        if text.lower().startswith(('tracker:', 'dht:', 'udp://', 'http://', 'https://')):
            text = re.sub(r'^(tracker:|dht:)', '', text, flags=re.I).strip()
            if text.lower().startswith(('udp://', 'http://', 'https://')):
                trackers.append(text)
    magnet = 'magnet:?xt=urn:btih:%s&dn=%s' % (info_hash, quote_plus(str(name or 'DexHub torrent')))
    for tr_url in trackers[:30]:
        magnet += '&tr=%s' % quote_plus(tr_url)
    try:
        file_idx = row.get('fileIdx') if row.get('fileIdx') not in (None, '') else row.get('fileIndex')
        if file_idx in (None, ''):
            file_idx = hints.get('fileIdx') if hints.get('fileIdx') not in (None, '') else hints.get('fileIndex')
        if file_idx not in (None, ''):
            # Stremio/Torrentio fileIdx is 0-based. Elementum accepts `so` as
            # the selected file index in the magnet query.
            magnet += '&so=%s' % quote_plus(str(file_idx))
    except Exception:
        pass
    return magnet


def _stream_play_url_from_row(row):
    """Normalize a Stremio stream row into something Kodi can play.

    Important: do NOT use `externalUrl` as a fallback playable URL. In the
    Stremio stream schema it is usually an external webpage/intent, while
    `url` is the direct playable stream and `infoHash`/`fileIdx` is the torrent
    stream shape. Treating externalUrl as video is why Torrentio/AIOStreams
    rows could appear in Dex Hub but fail at playback.
    """
    if not isinstance(row, dict):
        return ''
    url = str(row.get('url') or '').strip()
    if url.lower().startswith('magnet:'):
        return _torrent_handoff_url(url)
    if url:
        return _apply_kodi_request_headers(url, row)
    magnet = _magnet_from_stream_row(row)
    if magnet:
        return _torrent_handoff_url(magnet)
    return ''


def _torrent_play_url_from_stream_row(row):
    # Backward-compatible wrapper for older calls in this file.
    magnet = _magnet_from_stream_row(row)
    return _torrent_handoff_url(magnet) if magnet else ''


def _append_stream_entries_from_data(entries, data, provider, request_id, media_type, canonical_id, best_meta, art, bg, ids, title='', video_id=None, season=None, episode=None, show_title='', resume_seconds=0.0, resume_percent=0.0):
    provider_name = provider.get('name') or 'Provider'
    for row in (data or {}).get('streams') or []:
        stream_url = _stream_play_url_from_row(row)
        if not stream_url:
            continue
        label, label2, plot = _stream_label(row, provider_name)
        facts = _stream_facts(row, provider_name)
        display_name = facts['display_name']
        size = facts['size']
        video_bits = facts['video_bits']
        audio_bits = facts['audio_bits']
        quality, highlight = _quality_badge(video_bits)
        formatter = _formatter_payload(row, provider_name, facts)
        payload = {
            'media_type': media_type,
            'canonical_id': canonical_id,
            'video_id': video_id or request_id,
            'provider_name': provider_name,
            'provider_id': provider.get('id') or '',
            'title': title or best_meta.get('name') or canonical_id,
            'show_title': show_title or best_meta.get('name') or canonical_id,
            'year': (_meta_info(best_meta).get('year') or 0),
            'stream_url': stream_url,
            'poster': art.get('poster') or '',
            'background': bg,
            'clearlogo': art.get('clearlogo') or '',
            'tmdb_id': ids.get('tmdb_id') or '',
            'imdb_id': ids.get('imdb_id') or '',
            'tvdb_id': ids.get('tvdb_id') or '',
            'external_ids': ids,
            'subtitles': row.get('subtitles') or [],
            'behaviorHints': row.get('behaviorHints') or {},
            'provider_base_url': provider.get('base_url') or '',
            'duration_ms': int((((row.get('behaviorHints') or {}).get('plexDuration') or (row.get('behaviorHints') or {}).get('durationMs') or 0)) or 0),
            'stream_name': row.get('name') or '',
            'stream_title': row.get('title') or '',
            'stream_description': row.get('description') or '',
            'formatter_tags': formatter.get('tags') or [],
            'formatter_summary': formatter.get('summary') or '',
            'video_bits': facts.get('video_bits') or [],
            'audio_bits': facts.get('audio_bits') or [],
            'request_headers': _stream_row_request_headers(row),
            'external_url': row.get('externalUrl') or '',
            'info_hash': (row.get('infoHash') or row.get('infohash') or ((row.get('behaviorHints') or {}) if isinstance(row.get('behaviorHints') or {}, dict) else {}).get('infoHash') or ''),
        }
        if season is not None:
            payload['season'] = int(season)
        if episode is not None:
            payload['episode'] = int(episode)
        try:
            rs = float(resume_seconds or 0.0)
        except Exception:
            rs = 0.0
        if rs > 1.0:
            payload['resume_seconds'] = rs
        try:
            rp = float(resume_percent or 0.0)
        except Exception:
            rp = 0.0
        if rp > 1.0 and rp < 95.0:
            payload['resume_percent'] = rp
        cache_key = cache_store.put('stream', payload)
        entries.append({
            'stream_key': cache_key,
            'name': display_name,
            'label2': label2,
            'count': '00.',
            'quality': quality,
            'highlight': highlight,
            'provider': _provider_badge(row, provider_name),
            'provider_name_raw': provider_name,
            'addon': _extract_addon_name(row, provider_name),
            'source_site': facts['site'],
            'size_label': size or '--',
            'extraInfo': ' | '.join(video_bits[:8]) if video_bits else '--',
            'extraInfo2': ' | '.join(audio_bits[:8]) if audio_bits else '--',
            'badges': _stream_badges(video_bits, audio_bits, row.get('subtitles') or []),
            'source_info': _source_info_text(row, provider_name) + '\n\n' + plot,
        })

def _stream_initial_target_count():
    """How many providers to wait for before opening the source window.

    Small by design so the window appears quickly, while slower providers
    keep filling in live behind the scenes.
    """
    try:
        workers = max(2, int(float(ADDON.getSetting('parallel_workers') or '8')))
    except Exception:
        workers = 8
    return max(1, min(3, workers // 3 or 1))


def _provider_signature_text(provider):
    manifest = (provider or {}).get('manifest') or {}
    return ' '.join([
        str((provider or {}).get('name') or ''),
        str((provider or {}).get('base_url') or ''),
        str((provider or {}).get('manifest_url') or ''),
        str((provider or {}).get('id') or ''),
        str(manifest.get('name') or ''),
        str(manifest.get('id') or ''),
        str(manifest.get('description') or ''),
    ]).lower()


def _is_aiostreams_provider(provider):
    sig = _provider_signature_text(provider)
    return 'aiostream' in sig or 'aio streams' in sig or 'viren070' in sig


def _stream_timeout_for_provider(provider):
    # AIOStreams is an aggregator: it calls several addons internally, then
    # filters/sorts/deduplicates them. Treating it like a normal single-source
    # addon with the fast 4-8s timeout cuts off many results.
    try:
        base = int(float(ADDON.getSetting('timeout') or '20'))
    except Exception:
        base = 20
    if _is_aiostreams_provider(provider):
        return max(18, min(max(base, 18), 35))
    sig = _provider_signature_text(provider)
    if any(token in sig for token in ('torrentio', 'comet', 'mediafusion', 'stremthru')):
        return max(10, min(max(base, 10), 25))
    return fast_timeout('stream')


def _setting_bool(name, default=False):
    try:
        raw = (ADDON.getSetting(name) or ('true' if default else 'false')).strip().lower()
    except Exception:
        raw = 'true' if default else 'false'
    return raw in ('true', '1', 'yes', 'on')


def _aiostreams_base_url(provider):
    raw = str((provider or {}).get('manifest_url') or (provider or {}).get('base_url') or '').strip()
    if not raw:
        return ''
    raw = raw.split('/manifest.json', 1)[0]
    raw = raw.split('/stremio/', 1)[0]
    raw = re.sub(r'/stremio$', '', raw.rstrip('/'), flags=re.I)
    return raw.rstrip('/')


def _aiostreams_credentials(provider):
    user = ''
    password = ''
    try:
        user = ADDON.getSetting('aiostreams_username') or ''
        password = ADDON.getSetting('aiostreams_password') or ''
    except Exception:
        pass
    if user and password:
        return user, password
    for raw in (str((provider or {}).get('manifest_url') or ''), str((provider or {}).get('base_url') or '')):
        try:
            parsed = urlparse(raw)
            if parsed.username and parsed.password:
                return parsed.username, parsed.password
        except Exception:
            continue
    return user, password


def _aiostreams_direct_enabled(provider):
    """The normal Stremio path is the configured /stream route.

    Stremio does not strip the user's configured AIOStreams URL and then call
    /api/v1/search; it calls the addon instance that was installed from
    /manifest.json.  The direct API is useful only for explicit API/basic-auth
    setups.  Calling it without credentials hits the public/default instance
    and can inject MediaFusion/free results even when the user's configured
    addon has Debrid enabled.
    """
    if not _setting_bool('aiostreams_direct_api', False):
        return False
    user, password = _aiostreams_credentials(provider)
    return bool(user and password)


def _aiostreams_search_id(media_type, request_id):
    rid = str(request_id or '').strip()
    lower = rid.lower()
    if media_type in ('series', 'anime', 'show', 'tv'):
        if re.match(r'^tt\d{5,10}:\d+:\d+$', lower):
            return rid
        m = re.search(r'(tt\d{5,10}:\d+:\d+)', rid, re.I)
        if m:
            return m.group(1)
    if lower.startswith('tt') and re.match(r'^tt\d{5,10}$', lower):
        return rid
    m = re.search(r'\btt\d{5,10}\b', rid, re.I)
    return m.group(0) if m else ''


def _aiostreams_result_to_stream_row(item, provider_name):
    if not isinstance(item, dict):
        return {}
    # Direct API responses may wrap the real Stremio stream object in a
    # `stream` field.  Flatten that first so url/infoHash/behaviorHints and
    # proxy headers survive exactly like the official /stream response.
    stream_obj = item.get('stream')
    if isinstance(stream_obj, dict):
        row = dict(stream_obj)
        for k, v in item.items():
            if k == 'stream':
                continue
            row.setdefault(k, v)
    else:
        row = dict(item)
        if stream_obj and not row.get('url'):
            row['url'] = stream_obj
    parsed = item.get('parsedFile') or item.get('parsed_file') or row.get('parsedFile') or row.get('parsed_file') or {}
    if isinstance(parsed, dict):
        for k, v in parsed.items():
            row.setdefault(k, v)
    for key in ('url', 'link', 'streamUrl', 'stream_url', 'playbackUrl', 'playback_url'):
        if item.get(key) and not row.get('url'):
            row['url'] = item.get(key)
    if item.get('magnet') and not row.get('url'):
        row['url'] = item.get('magnet')
    for key in ('infoHash', 'infohash', 'btih', 'fileIdx', 'fileIndex'):
        if item.get(key) not in (None, ''):
            row[key] = item.get(key)
    addon_name = item.get('addon') or item.get('addonName') or item.get('provider') or item.get('service') or row.get('addon') or row.get('addonName') or provider_name
    title_bits = []
    for value in (
        item.get('title'), item.get('name'), row.get('title'), row.get('name'), item.get('filename'), row.get('filename'),
        parsed.get('title') if isinstance(parsed, dict) else '', parsed.get('quality') if isinstance(parsed, dict) else '',
        item.get('type'), item.get('service'), item.get('cached'), parsed.get('size') if isinstance(parsed, dict) else '',
        item.get('size'), item.get('sizeLabel'), row.get('description')
    ):
        if value not in (None, '', [], {}):
            text = str(value)
            if text not in title_bits:
                title_bits.append(text)
    if addon_name and str(addon_name) not in title_bits:
        title_bits.insert(0, str(addon_name))
    row['name'] = str(addon_name or provider_name or 'AIOStreams')
    row['title'] = row.get('title') or ' | '.join(title_bits)
    row['description'] = row.get('description') or ' | '.join(title_bits)
    return row

def _fetch_aiostreams_direct(provider, media_type, request_id):
    if not _setting_bool('aiostreams_direct_api', False):
        return {}
    aio_id = _aiostreams_search_id(media_type, request_id)
    if not aio_id:
        return {}
    base = _aiostreams_base_url(provider)
    if not base:
        return {}
    url = base + '/api/v1/search?' + urlencode({'type': 'movie' if media_type == 'movie' else 'series', 'id': aio_id})
    headers = {'Accept': 'application/json', 'User-Agent': 'Kodi DexHub/3.7.100'}
    user, password = _aiostreams_credentials(provider)
    if user and password:
        try:
            token = base64.b64encode(('%s:%s' % (user, password)).encode('utf-8')).decode('ascii')
            headers['Authorization'] = 'Basic ' + token
        except Exception:
            pass
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=_stream_timeout_for_provider(provider)) as response:
            text = response.read().decode('utf-8', 'replace')
        payload = json.loads(text.strip().lstrip('\ufeff'))
    except Exception as exc:
        xbmc.log('[DexHub] AIOStreams direct API failed for %s: %s' % (aio_id, exc), xbmc.LOGDEBUG)
        return {}
    data = payload.get('data') if isinstance(payload, dict) else payload
    if isinstance(data, dict):
        rows = data.get('results') or data.get('streams') or []
    else:
        rows = data if isinstance(data, list) else []
    streams = []
    provider_name = (provider or {}).get('name') or 'AIOStreams'
    for item in rows or []:
        row = _aiostreams_result_to_stream_row(item, provider_name)
        if row:
            streams.append(row)
    return {'streams': streams}


def _merge_stream_payloads(primary, extra):
    streams = []
    seen = set()
    for payload in (primary or {}, extra or {}):
        for row in (payload or {}).get('streams') or []:
            sig = '|'.join([str(row.get(k) or '') for k in ('url', 'infoHash', 'infohash', 'title', 'name')])
            if sig in seen:
                continue
            seen.add(sig)
            streams.append(row)
    return {'streams': streams}


def _fetch_stream_payload(target, media_type):
    provider, request_id = target
    try:
        data = fetch_streams(provider, media_type, request_id, timeout_override=_stream_timeout_for_provider(provider))
        if _is_aiostreams_provider(provider) and _aiostreams_direct_enabled(provider):
            direct = _fetch_aiostreams_direct(provider, media_type, request_id)
            if direct.get('streams'):
                data = _merge_stream_payloads(data, direct)
        return data
    except Exception as exc:
        if _is_aiostreams_provider(provider) and _aiostreams_direct_enabled(provider):
            direct = _fetch_aiostreams_direct(provider, media_type, request_id)
            if direct.get('streams'):
                return direct
        return exc

def _collect_stream_entries(targets, media_type, canonical_id, best_meta, art, bg, ids, title='',
                            video_id='', season=None, episode=None, show_title='', resume_seconds=0.0,
                            resume_percent=0.0,
                            stop_after_first=False, show_loader=False, processed_targets=None):
    entries = []
    if not targets:
        return entries

    loader_title = title or show_title or best_meta.get('name') or canonical_id or tr('المصادر')

    def _run(loader=None):
        for idx, (target, data) in enumerate(iter_parallel(lambda t: _fetch_stream_payload(t, media_type), targets), start=1):
            provider, request_id = target
            if processed_targets is not None:
                try:
                    processed_targets.append(target)
                except Exception:
                    pass
            if loader is not None:
                if loader.is_cancelled():
                    break
                loader.update(
                    provider_name=provider.get('name') or (provider.get('manifest') or {}).get('name') or '',
                    index=idx,
                    status=tr('جار البحث عن المصادر...'),
                    sub_status='%d %s' % (len(entries), tr('مصدر')) if entries else '',
                )
            if isinstance(data, Exception) or not data:
                continue
            before = len(entries)
            _append_stream_entries_from_data(
                entries, data, provider, request_id, media_type, canonical_id, best_meta, art, bg, ids,
                title=title, video_id=video_id, season=season, episode=episode, show_title=show_title,
                resume_seconds=resume_seconds, resume_percent=resume_percent,
            )
            if loader is not None and len(entries) > before:
                loader.add_results(len(entries) - before)
            if stop_after_first and entries:
                break
        if loader is not None:
            loader.set_finalizing()

    if show_loader:
        with SourcesLoadingDialog(title=loader_title, fanart=bg or (art or {}).get('fanart') or (art or {}).get('poster') or '', provider_count=len(targets)) as loader:
            _run(loader)
    else:
        _run(None)
    return entries


def _start_stream_session_refresh(session_key, initial_entries, remaining_targets, media_type, canonical_id,
                                  best_meta, art, bg, ids, title='', video_id='', season=None,
                                  episode=None, show_title='', resume_seconds=0.0, resume_percent=0.0):
    if not session_key or not remaining_targets:
        return

    def _worker():
        entries = list(initial_entries or [])
        version = 1
        try:
            for target, data in iter_parallel(lambda t: _fetch_stream_payload(t, media_type), remaining_targets):
                if isinstance(data, Exception) or not data:
                    continue
                provider, request_id = target
                before = len(entries)
                _append_stream_entries_from_data(
                    entries, data, provider, request_id, media_type, canonical_id, best_meta, art, bg, ids,
                    title=title, video_id=video_id, season=season, episode=episode, show_title=show_title,
                    resume_seconds=resume_seconds, resume_percent=resume_percent,
                )
                if len(entries) == before:
                    continue
                fresh = list(entries[before:])
                del entries[before:]
                entries.extend(_finalize_stream_entries(fresh, media_type=media_type, canonical_id=canonical_id, video_id=video_id or request_id))
                version += 1
                cache_store.update('stream_session', session_key, {
                    'entries': _finalize_stream_entries(list(entries), resort=False, media_type=media_type, canonical_id=canonical_id, video_id=video_id or request_id),
                    'done': False,
                    'version': version,
                })
        finally:
            try:
                cache_store.update('stream_session', session_key, {
                    'entries': _finalize_stream_entries(list(entries), resort=False, media_type=media_type, canonical_id=canonical_id, video_id=video_id or request_id),
                    'done': True,
                    'version': version + 1,
                })
            except Exception:
                pass

    threading.Thread(target=_worker, name='DexHubStreamRefresh', daemon=True).start()


def streams(media_type, canonical_id, title='', resume_seconds='0', resume_percent='', preferred_provider_name='', source_provider_id=''):
    _clear_source_transient_props(clear_global=False)
    providers = _provider_order_for_id_with_context(media_type, canonical_id, source_provider_id=source_provider_id)
    best_meta, has_cached_meta = _fast_meta_for_sources(media_type, canonical_id, providers, title=title, source_provider_id=source_provider_id)
    provider_fb = _item_fallback_art(providers[0] if providers else {}, media_type)
    art = _resolve_meta_art(providers[0] if providers else {}, media_type, best_meta, fallback_art=provider_fb) if has_cached_meta else dict(provider_fb)
    art = _prefer_item_art(art, best_meta, media_type, fallback_art=provider_fb)
    ids = _merge_seed_ids(extract_ids(best_meta), _get_tmdbh_seed_ids(canonical_id))
    ids = _enrich_stream_ids(ids, media_type, meta=best_meta, canonical_id=canonical_id, title=title or best_meta.get('name') or best_meta.get('title') or '')
    stream_meta = _meta_with_seed_ids(best_meta, ids)
    _prime_best_meta_async(media_type, canonical_id, providers, source_provider_id=source_provider_id)
    win = xbmcgui.Window(WINDOW_ID)
    logo = art.get('clearlogo') or ''
    win.setProperty('clearlogo', logo)
    win.setProperty('tvshow.clearlogo', logo)
    bg = _content_background(art, provider_fb)
    win.setProperty('fanart', bg)
    win.setProperty('poster', art.get('poster') or '')
    try:
        resume_seconds = float(resume_seconds or 0.0)
    except Exception:
        resume_seconds = 0.0
    try:
        resume_percent_val = float(resume_percent or 0.0)
    except Exception:
        resume_percent_val = 0.0
    targets = _prioritize_provider_targets(list(_stream_provider_targets(media_type, canonical_id, meta=stream_meta)), preferred_provider_name=preferred_provider_name)

    # Race all candidate providers and open the source picker as soon as the
    # first provider returns usable streams. Slow providers continue to fill the
    # window through the live stream_session refresh instead of blocking the UI.
    processed_targets = []
    entries = _collect_stream_entries(
        targets, media_type, canonical_id, best_meta, art, bg, ids,
        title=title, resume_seconds=resume_seconds, resume_percent=resume_percent_val, show_loader=True,
        stop_after_first=False, processed_targets=processed_targets,
    )
    processed_set = set((id(p), rid) for p, rid in processed_targets)
    remaining_targets = [t for t in targets if (id(t[0]), t[1]) not in processed_set]
    if not entries:
        _clear_tmdbh_transient()
        _clear_source_transient_props(clear_global=True)
        error('لم يتم العثور على روابط تشغيل')
        return end_dir()
    entries = _finalize_stream_entries(entries, media_type=media_type, canonical_id=canonical_id)
    # Pull plot/year/genre/rating from best_meta so the source window can
    # render the redesigned hero panel (Plot textbox, year-genre-rating row).
    _genres = best_meta.get('genres') or []
    if isinstance(_genres, list):
        _genre_str = ' / '.join([str(g) for g in _genres[:3] if g])
    else:
        _genre_str = str(_genres or '')
    _year_val = ''
    _release = best_meta.get('releaseInfo') or best_meta.get('year') or ''
    if _release:
        _ymatch = YEAR_RE.search(str(_release))
        if _ymatch:
            _year_val = _ymatch.group(1)
    _rating = best_meta.get('imdbRating') or ''
    try:
        if _rating:
            _rating = '%.1f' % float(_rating)
    except Exception:
        _rating = str(_rating or '')
    meta = {
        'title': title or best_meta.get('name') or canonical_id,
        'poster': art.get('poster') or provider_fb.get('poster') or provider_fb.get('thumb') or '',
        'fanart': _content_background(art, provider_fb),
        'clearlogo': art.get('clearlogo') or '',
        'plot': best_meta.get('description') or best_meta.get('overview') or '',
        'year': _year_val,
        'genre': _genre_str,
        'rating': _rating,
        'imdb_id': ids.get('imdb_id') or '',
        'tmdb_id': ids.get('tmdb_id') or '',
        'tvdb_id': ids.get('tvdb_id') or '',
    }
    session_key = ''
    if remaining_targets:
        session_key = cache_store.put('stream_session', {'entries': entries, 'done': False, 'version': 1}, ttl_hours=6)
        _start_stream_session_refresh(
            session_key, entries, remaining_targets, media_type, canonical_id, best_meta, art, bg, ids,
            title=title, resume_seconds=resume_seconds, resume_percent=resume_percent_val,
        )
    return _show_stream_window(entries, meta, session_key=session_key)


def series_meta(media_type, canonical_id, title='', source_provider_id=''):
    providers = _provider_order_for_id_with_context(media_type, canonical_id, source_provider_id=source_provider_id)
    meta = None
    meta_provider = None
    for provider in providers:
        try:
            data = fetch_meta(provider, media_type, canonical_id, timeout_override=fast_timeout('meta'))
            meta = data.get('meta') or data.get('metas')
            if isinstance(meta, list):
                meta = meta[0] if meta else None
            if meta and meta.get('videos'):
                meta_provider = provider
                break
        except Exception:
            continue
    if not meta:
        error('تعذر جلب بيانات المسلسل')
        return end_dir()
    try:
        from . import meta_source as _meta_source
        if _is_virtual_meta_target(source_provider_id):
            meta = _meta_source.override_virtual_meta(source_provider_id, media_type, meta) or meta
        else:
            meta = _meta_source.override_meta(meta_provider or (providers[0] if providers else {}), media_type, meta) or meta
    except Exception:
        pass
    seasons = {}
    videos = meta.get('videos') or []
    xbmcgui.Window(WINDOW_ID).setProperty(SERIES_PROP_PREFIX + canonical_id, json.dumps(videos))
    art_provider = meta_provider or (providers[0] if providers else {})
    provider_fb = _item_fallback_art(art_provider, media_type)
    series_art = _resolve_meta_art(art_provider, media_type, meta, fallback_art=provider_fb)
    xbmcgui.Window(WINDOW_ID).setProperty(SERIES_PROP_PREFIX + canonical_id + '.art', json.dumps(series_art))
    resolved_series_title = meta.get('name') or title or canonical_id
    xbmcgui.Window(WINDOW_ID).setProperty(SERIES_PROP_PREFIX + canonical_id + '.title', resolved_series_title)
    xbmcgui.Window(WINDOW_ID).setProperty(SERIES_PROP_PREFIX + canonical_id + '.media_type', media_type or 'series')
    xbmcgui.Window(WINDOW_ID).setProperty(SERIES_PROP_PREFIX + canonical_id + '.source_provider_id', source_provider_id if _is_virtual_meta_target(source_provider_id) else ((art_provider or {}).get('id') or source_provider_id or ''))
    xbmcgui.Window(WINDOW_ID).setProperty(SERIES_PROP_PREFIX + canonical_id + '.native_art', '1' if (_provider_prefers_native_art(art_provider) or _provider_uses_explicit_meta_art(art_provider)) else '0')
    ids = _merge_seed_ids(extract_ids(meta), _get_tmdbh_seed_ids(canonical_id))
    for video in videos:
        season_num = int(video.get('season') or 1)
        seasons.setdefault(season_num, []).append(video)
    for season_num in sorted(seasons.keys()):
        add_item(
            'الموسم %s' % season_num,
            build_url(action='season', media_type=media_type, canonical_id=canonical_id, season=season_num, title=resolved_series_title),
            info={'title': 'الموسم %s' % season_num, 'tvshowtitle': resolved_series_title, 'mediatype': 'season'},
            art=dict(series_art, thumb=series_art.get('poster'), icon=series_art.get('poster')),
            ids=ids,
        )
    end_dir(content='seasons')


def season(canonical_id, season, title='', media_type=''):
    raw = xbmcgui.Window(WINDOW_ID).getProperty(SERIES_PROP_PREFIX + canonical_id)
    videos = []
    if raw:
        try:
            videos = json.loads(raw)
        except Exception:
            videos = []
    art_raw = xbmcgui.Window(WINDOW_ID).getProperty(SERIES_PROP_PREFIX + canonical_id + '.art')
    series_art = {}
    if art_raw:
        try:
            series_art = json.loads(art_raw)
        except Exception:
            series_art = {}
    show_title = xbmcgui.Window(WINDOW_ID).getProperty(SERIES_PROP_PREFIX + canonical_id + '.title') or title
    media_type = media_type or xbmcgui.Window(WINDOW_ID).getProperty(SERIES_PROP_PREFIX + canonical_id + '.media_type') or 'series'
    prefer_native_art = xbmcgui.Window(WINDOW_ID).getProperty(SERIES_PROP_PREFIX + canonical_id + '.native_art') == '1'
    season = int(season)
    # Compute once — canonical_id doesn't change across episodes.
    episode_ids = _merge_seed_ids(extract_ids({'id': canonical_id}), _get_tmdbh_seed_ids(canonical_id))
    for video in videos:
        if int(video.get('season') or 1) != season:
            continue
        ep = int(video.get('episode') or 0)
        vtitle = video.get('title') or ('S%02dE%02d' % (season, ep))
        label = 'S%02dE%02d — %s' % (season, ep, vtitle)
        meta = {'id': video.get('id') or canonical_id, 'name': vtitle, 'poster': video.get('thumbnail') or '', 'background': video.get('thumbnail') or '', 'type': 'series'}
        episode_art = native_meta_art(meta, media_type if media_type in ('anime','series') else 'series', fallback_art=series_art) if prefer_native_art else enrich_meta_art(meta, media_type if media_type in ('anime','series') else 'series', fallback_art=series_art)
        episode_path, episode_is_folder = _content_click_path(media_type=media_type or 'series', canonical_id=canonical_id, video_id=video.get('id') or canonical_id, season=season, episode=ep, title=vtitle, tmdb_id=episode_ids.get('tmdb_id') or '', imdb_id=episode_ids.get('imdb_id') or '', tvdb_id=episode_ids.get('tvdb_id') or '', source_provider_id=xbmcgui.Window(WINDOW_ID).getProperty(SERIES_PROP_PREFIX + canonical_id + '.source_provider_id') or '')
        episode_menu = _build_source_picker_menu(media_type=media_type or 'series', canonical_id=canonical_id, title=vtitle, season=season, episode=ep, video_id=video.get('id') or canonical_id, source_provider_id=xbmcgui.Window(WINDOW_ID).getProperty(SERIES_PROP_PREFIX + canonical_id + '.source_provider_id') or '') + _build_player_chooser_menu(media_type=media_type or 'series', canonical_id=canonical_id, title=vtitle, season=season, episode=ep, video_id=video.get('id') or canonical_id)
        add_item(label, episode_path, is_folder=episode_is_folder, info={'title': vtitle, 'episode': ep, 'season': season, 'tvshowtitle': show_title, 'mediatype': 'episode', 'plot': video.get('overview') or ''}, art=episode_art, context_menu=episode_menu)
    end_dir(content='episodes')


def episode_streams(canonical_id, video_id, season, episode, title='', media_type='', resume_seconds='0', resume_percent='', preferred_provider_name='', source_provider_id=''):
    _clear_source_transient_props(clear_global=False)
    media_type = media_type or xbmcgui.Window(WINDOW_ID).getProperty(SERIES_PROP_PREFIX + canonical_id + '.media_type') or 'series'
    source_provider_id = source_provider_id or xbmcgui.Window(WINDOW_ID).getProperty(SERIES_PROP_PREFIX + canonical_id + '.source_provider_id') or ''
    providers = _provider_order_for_id_with_context(media_type, canonical_id, source_provider_id=source_provider_id)
    best_meta, has_cached_meta = _fast_meta_for_sources(media_type, canonical_id, providers, title=title or canonical_id, source_provider_id=source_provider_id)
    provider_fb = _item_fallback_art(providers[0] if providers else {}, media_type)
    art = _resolve_meta_art(providers[0] if providers else {}, media_type, best_meta, fallback_art=provider_fb) if has_cached_meta else dict(provider_fb)
    art = _prefer_item_art(art, best_meta, media_type, fallback_art=provider_fb)
    ids = _merge_seed_ids(extract_ids(best_meta), _get_tmdbh_seed_ids(canonical_id))
    ids = _enrich_stream_ids(ids, media_type, meta=best_meta, canonical_id=canonical_id, title=title or best_meta.get('name') or best_meta.get('title') or '')
    stream_meta = _meta_with_seed_ids(best_meta, ids)
    _prime_best_meta_async(media_type, canonical_id, providers, source_provider_id=source_provider_id)
    win = xbmcgui.Window(WINDOW_ID)
    logo = art.get('clearlogo') or ''
    win.setProperty('clearlogo', logo)
    win.setProperty('tvshow.clearlogo', logo)
    bg = _content_background(art, provider_fb)
    win.setProperty('fanart', bg)
    win.setProperty('poster', art.get('poster') or '')
    direct_targets = []
    for provider in store.list_providers():
        if _is_aiostreams_provider(provider) and not re.match(r'^tt\d{5,10}(?::\d+:\d+)?$', str(video_id or ''), re.I):
            continue
        if supports_resource(provider, 'stream', media_type=media_type, item_id=video_id):
            direct_targets.append((provider, video_id))
    try:
        resume_seconds = float(resume_seconds or 0.0)
    except Exception:
        resume_seconds = 0.0
    try:
        resume_percent_val = float(resume_percent or 0.0)
    except Exception:
        resume_percent_val = 0.0
    targets = direct_targets + [t for t in _stream_provider_targets(media_type, canonical_id, meta=stream_meta, season=season, episode=episode) if t not in direct_targets]
    targets = _prioritize_provider_targets(targets, preferred_provider_name=preferred_provider_name)

    # Same race strategy as movies: do not wait for every provider before the
    # source window opens. This is especially noticeable for NextUp/collections.
    processed_targets = []
    entries = _collect_stream_entries(
        targets, media_type, canonical_id, best_meta, art, bg, ids,
        title=title or video_id, video_id=video_id, season=season, episode=episode,
        show_title=best_meta.get('name') or canonical_id, resume_seconds=resume_seconds, resume_percent=resume_percent_val, show_loader=True,
        stop_after_first=False, processed_targets=processed_targets,
    )
    processed_set = set((id(p), rid) for p, rid in processed_targets)
    remaining_targets = [t for t in targets if (id(t[0]), t[1]) not in processed_set]
    if not entries:
        _clear_tmdbh_transient()
        _clear_source_transient_props(clear_global=True)
        error('لم يتم العثور على روابط تشغيل للحلقة')
        return end_dir()
    entries = _finalize_stream_entries(entries, media_type=media_type, canonical_id=canonical_id, video_id=video_id)
    # Pull plot/year/genre/rating from best_meta so the source window can
    # render the redesigned hero panel for the episode picker too.
    _ep_genres = best_meta.get('genres') or []
    if isinstance(_ep_genres, list):
        _ep_genre_str = ' / '.join([str(g) for g in _ep_genres[:3] if g])
    else:
        _ep_genre_str = str(_ep_genres or '')
    _ep_year_val = ''
    _ep_release = best_meta.get('releaseInfo') or best_meta.get('year') or ''
    if _ep_release:
        _ep_ymatch = YEAR_RE.search(str(_ep_release))
        if _ep_ymatch:
            _ep_year_val = _ep_ymatch.group(1)
    _ep_rating = best_meta.get('imdbRating') or ''
    try:
        if _ep_rating:
            _ep_rating = '%.1f' % float(_ep_rating)
    except Exception:
        _ep_rating = str(_ep_rating or '')
    meta = {
        'title': title or video_id,
        'poster': art.get('poster') or provider_fb.get('poster') or provider_fb.get('thumb') or '',
        'fanart': _content_background(art, provider_fb),
        'clearlogo': art.get('clearlogo') or '',
        'plot': best_meta.get('description') or best_meta.get('overview') or '',
        'year': _ep_year_val,
        'genre': _ep_genre_str,
        'rating': _ep_rating,
        'imdb_id': ids.get('imdb_id') or '',
        'tmdb_id': ids.get('tmdb_id') or '',
        'tvdb_id': ids.get('tvdb_id') or '',
    }
    session_key = ''
    if remaining_targets:
        session_key = cache_store.put('stream_session', {'entries': entries, 'done': False, 'version': 1}, ttl_hours=6)
        _start_stream_session_refresh(
            session_key, entries, remaining_targets, media_type, canonical_id, best_meta, art, bg, ids,
            title=title or video_id, video_id=video_id, season=season, episode=episode,
            show_title=best_meta.get('name') or canonical_id, resume_seconds=resume_seconds, resume_percent=resume_percent_val,
        )
    return _show_stream_window(entries, meta, session_key=session_key)

def _resolve_best_id(video_type, tmdb_id='', imdb_id='', tvdb_id='', title=''):
    if tmdb_id:
        return 'tmdb:%s' % tmdb_id
    if imdb_id:
        return imdb_id if str(imdb_id).startswith('tt') else 'imdb:%s' % imdb_id
    if tvdb_id:
        return 'tvdb:%s' % tvdb_id
    return title or ''


def _find_episode_video_id(canonical_id, season, episode):
    providers = _provider_order_for_id('series', canonical_id)
    for provider in providers:
        try:
            data = fetch_meta(provider, 'series', canonical_id, timeout_override=fast_timeout('meta'))
            meta = data.get('meta') or data.get('metas')
            if isinstance(meta, list):
                meta = meta[0] if meta else None
            videos = (meta or {}).get('videos') or []
            for video in videos:
                if int(video.get('season') or 0) == int(season or 0) and int(video.get('episode') or 0) == int(episode or 0):
                    return video.get('id') or canonical_id, (meta or {}).get('name') or canonical_id
        except Exception:
            continue
    return canonical_id, ''


def tmdb_player(video_type='movie', tmdb_id='', imdb_id='', tvdb_id='', title='', year='', showname='', season='', episode=''):
    vtype = (video_type or 'movie').lower()
    # Suppress duplicate TMDb Helper handoffs. TMDb Helper sometimes
    # fires its play URL twice in quick succession (especially when
    # users tap "Play" before the dialog has fully rendered). The dedup
    # key includes season/episode so different episodes of the same
    # show don't suppress each other.
    _tp_key = 'tmdb_player|%s|%s|%s|%s|%s|%s' % (
        vtype, tmdb_id or '', imdb_id or '', tvdb_id or '',
        str(season or ''), str(episode or ''),
    )
    if _dispatch_in_flight(_tp_key, window_seconds=12):
        xbmc.log('[DexHub] tmdb_player: duplicate dispatch suppressed (%s)' % _tp_key, xbmc.LOGINFO)
        return
    lookup_title = showname or title
    canonical_id = _resolve_best_id(vtype, tmdb_id=tmdb_id, imdb_id=imdb_id, tvdb_id=tvdb_id, title=lookup_title)
    if not canonical_id:
        error('Missing IDs for TMDb Helper player')
        return end_dir()

    # Preserve the IDs TMDb Helper gave us so downstream code (subtitle broker,
    # scrobbler, companion sync) has real identifiers even when our meta
    # provider can't resolve them from the canonical id alone. Scope the stash
    # by canonical_id so a later unrelated stream doesn't wrongly inherit it.
    seed_ids = {
        'tmdb_id': str(tmdb_id or '').strip(),
        'imdb_id': str(imdb_id or '').strip() if str(imdb_id or '').startswith('tt') else ('tt%s' % imdb_id if imdb_id and str(imdb_id).isdigit() else str(imdb_id or '').strip()),
        'tvdb_id': str(tvdb_id or '').strip(),
    }
    try:
        win = xbmcgui.Window(WINDOW_ID)
        win.setProperty('dexhub.tmdbh_seed_ids', json.dumps(seed_ids))
        win.setProperty('dexhub.tmdbh_seed_for', canonical_id or '')
        win.setProperty('dexhub.invoked_by_tmdbh', '1')
        _mark_tmdbh_handoff(60)
    except Exception:
        pass

    auto_first = False
    try:
        auto_first = (ADDON.getSetting('tmdbh_auto_play_first') or 'false').lower() == 'true'
    except Exception:
        auto_first = False

    if vtype in ('episode', 'show', 'series', 'tv'):
        if season and episode:
            video_id, resolved_title = _find_episode_video_id(canonical_id, season, episode)
            if auto_first:
                return _auto_play_first_episode(canonical_id, video_id, season, episode, title=title or resolved_title or showname or canonical_id, seed_ids=seed_ids)
            return episode_streams(canonical_id, video_id, season, episode, title=title or resolved_title or showname or canonical_id, media_type='series')
        return series_meta('series', canonical_id, title=showname or title or canonical_id)

    if auto_first:
        return _auto_play_first_movie(canonical_id, title=title or canonical_id, seed_ids=seed_ids)
    return streams('movie', canonical_id, title=title or canonical_id)


def _merge_seed_ids(base_ids, seed_ids):
    """Non-empty seed IDs win over empty base IDs but never overwrite a resolved value."""
    base_ids = dict(base_ids or {})
    for k, v in (seed_ids or {}).items():
        if v and not base_ids.get(k):
            base_ids[k] = v
    return base_ids


def _meta_with_seed_ids(meta, ids):
    """Expose resolved ids to stream target discovery without changing UI meta."""
    out = dict(meta or {})
    ids = ids or {}
    external = dict(out.get('externalIds') or {}) if isinstance(out.get('externalIds') or {}, dict) else {}
    for src, external_key, camel_key in (
        ('imdb_id', 'imdb', 'imdbId'),
        ('tmdb_id', 'tmdb', 'tmdbId'),
        ('tvdb_id', 'tvdb', 'tvdbId'),
    ):
        val = str(ids.get(src) or '').strip()
        if not val:
            continue
        out.setdefault(src, val)
        out.setdefault(camel_key, val)
        external.setdefault(external_key, val)
    if external:
        out['externalIds'] = external
    return out


def _get_tmdbh_seed_ids(canonical_id=None):
    """Return seed IDs only when the stash's canonical_id matches (or no canonical filter given)."""
    try:
        win = xbmcgui.Window(WINDOW_ID)
        raw = win.getProperty('dexhub.tmdbh_seed_ids') or ''
        scoped_for = win.getProperty('dexhub.tmdbh_seed_for') or ''
        if not raw:
            return {}
        # If caller specified a canonical_id and the stash was set for a different one, don't leak.
        if canonical_id and scoped_for and scoped_for != canonical_id:
            return {}
        return json.loads(raw) or {}
    except Exception:
        return {}


def _auto_play_first_movie(canonical_id, title='', seed_ids=None, preferred_provider_name='', resume_seconds=0.0, resume_percent=0.0, source_provider_id=''):
    providers = _provider_order_for_id_with_context('movie', canonical_id, source_provider_id=source_provider_id)
    best_meta = _best_meta_for_item('movie', canonical_id, providers, source_provider_id=source_provider_id)
    provider_fb = _item_fallback_art(providers[0] if providers else {}, 'movie')
    art = _resolve_meta_art(providers[0] if providers else {}, 'movie', best_meta, fallback_art=provider_fb)
    art = _prefer_item_art(art, best_meta, 'movie', fallback_art=provider_fb)
    bg = _content_background(art, provider_fb)
    ids = _merge_seed_ids(extract_ids(best_meta), seed_ids or _get_tmdbh_seed_ids(canonical_id))
    ids = _enrich_stream_ids(ids, 'movie', meta=best_meta, canonical_id=canonical_id, title=title or best_meta.get('name') or best_meta.get('title') or '')
    stream_meta = _meta_with_seed_ids(best_meta, ids)
    entries = []
    targets = _prioritize_provider_targets(list(_stream_provider_targets('movie', canonical_id, meta=stream_meta)), preferred_provider_name=preferred_provider_name)

    def _fetch(t):
        return _fetch_stream_payload(t, 'movie')

    for target, data in run_parallel(_fetch, targets):
        if isinstance(data, Exception) or not data:
            continue
        p, rid = target
        _append_stream_entries_from_data(entries, data, p, rid, 'movie', canonical_id, best_meta, art, bg, ids, title=title, resume_seconds=resume_seconds, resume_percent=resume_percent)
    if not entries:
        _clear_tmdbh_transient()
        _clear_source_transient_props(clear_global=True)
        error('لم يتم العثور على روابط تشغيل')
        return end_dir()
    entries = _finalize_stream_entries(entries, media_type='movie', canonical_id=canonical_id)
    return play(entries[0]['stream_key'], resume_seconds=resume_seconds, resume_percent=resume_percent)


def _auto_play_first_episode(canonical_id, video_id, season, episode, title='', seed_ids=None, preferred_provider_name='', resume_seconds=0.0, resume_percent=0.0, source_provider_id=''):
    providers = _provider_order_for_id_with_context('series', canonical_id, source_provider_id=source_provider_id)
    best_meta = _best_meta_for_item('series', canonical_id, providers, source_provider_id=source_provider_id)
    provider_fb = _item_fallback_art(providers[0] if providers else {}, 'series')
    art = _resolve_meta_art(providers[0] if providers else {}, 'series', best_meta, fallback_art=provider_fb)
    art = _prefer_item_art(art, best_meta, 'series', fallback_art=provider_fb)
    bg = _content_background(art, provider_fb)
    ids = _merge_seed_ids(extract_ids(best_meta), seed_ids or _get_tmdbh_seed_ids(canonical_id))
    ids = _enrich_stream_ids(ids, 'series', meta=best_meta, canonical_id=canonical_id, title=title or best_meta.get('name') or best_meta.get('title') or '')
    stream_meta = _meta_with_seed_ids(best_meta, ids)
    entries = []
    request_id = video_id or ('%s:%s:%s' % (canonical_id, season, episode))
    targets = _prioritize_provider_targets(list(_stream_provider_targets('series', canonical_id, meta=stream_meta, season=season, episode=episode)), preferred_provider_name=preferred_provider_name)

    def _fetch(t):
        return _fetch_stream_payload(t, 'series')

    for target, data in run_parallel(_fetch, targets):
        if isinstance(data, Exception) or not data:
            continue
        p, rid = target
        _append_stream_entries_from_data(entries, data, p, rid, 'series', canonical_id, best_meta, art, bg, ids, title=title, video_id=video_id, season=season, episode=episode, resume_seconds=resume_seconds, resume_percent=resume_percent)
    if not entries:
        _clear_tmdbh_transient()
        _clear_source_transient_props(clear_global=True)
        error('لم يتم العثور على روابط تشغيل')
        return end_dir()
    entries = _finalize_stream_entries(entries, media_type='series', canonical_id=canonical_id, video_id=video_id)
    return play(entries[0]['stream_key'], resume_seconds=resume_seconds, resume_percent=resume_percent)


def _parse_canonical_ids(canonical_id):
    """Extract tmdb/imdb from a canonical id like 'tmdb:123', 'tt0000123', or plain text."""
    cid = str(canonical_id or '').strip()
    if cid.startswith('tmdb:'):
        return {'tmdb_id': cid.split(':', 1)[1], 'imdb_id': ''}
    if cid.startswith('tt') and cid[2:].isdigit():
        return {'tmdb_id': '', 'imdb_id': cid}
    return {'tmdb_id': '', 'imdb_id': ''}


def _virtual_meta_override(target_key, media_type, seed_meta):
    try:
        from . import meta_source as _meta_source
        return _meta_source.override_virtual_meta(target_key, media_type, seed_meta or {}) or (seed_meta or {})
    except Exception:
        return seed_meta or {}


def _cw_target_key(row):
    mt = (row.get('media_type') or '').lower()
    return 'virtual.continue.series' if mt in ('series', 'anime', 'show', 'tv') or (row.get('season') and row.get('episode') is not None) else 'virtual.continue.movie'


def _lazy_fill_row_art(row):
    """Fill Continue Watching artwork using the configured metadata target."""
    target_key = _cw_target_key(row)
    source_id = 'auto'
    try:
        from . import meta_source as _meta_source
        source_id = (_meta_source.get_meta_source_for(target_key) or 'auto')
    except Exception:
        source_id = 'auto'
    if source_id == 'native':
        return row

    explicit_source = source_id not in ('', 'auto')
    try:
        tokenized_art = _row_poster_looks_provider_tokenized(row.get('poster')) or _row_poster_looks_provider_tokenized(row.get('background'))
    except Exception:
        tokenized_art = False
    needs_fill = tokenized_art or not (row.get('poster') and row.get('background') and row.get('clearlogo'))
    seed_meta = {
        'id': row.get('canonical_id') or '',
        'name': row.get('title') or row.get('canonical_id') or '',
        'title': row.get('title') or row.get('canonical_id') or '',
        'poster': row.get('poster') or '',
        'background': row.get('background') or '',
        'logo': row.get('clearlogo') or '',
        'clearlogo': row.get('clearlogo') or '',
    }
    if not needs_fill and not explicit_source:
        return row

    ids = _parse_canonical_ids(row.get('canonical_id'))
    tmdb_id = ids.get('tmdb_id') or ''
    imdb_id = ids.get('imdb_id') or ''
    media_kind = 'series' if row.get('media_type') in ('series', 'anime', 'tv', 'show') or (row.get('season') and row.get('episode') is not None) else 'movie'
    if (tmdb_id or imdb_id) and not explicit_source:
        media_type = 'tv' if media_kind == 'series' else 'movie'
        try:
            bundle = _tmdb_art_db.get_art_bundle_from_db(
                tmdb_id=tmdb_id, media_type=media_type, imdb_id=imdb_id, title=row.get('title') or ''
            ) or {}
        except Exception:
            bundle = {}
        # Bug fix: previously this skipped TMDb posters when the user had
        # picked "محلي فقط" globally — but Continue Watching rows from Trakt
        # have no local artwork to begin with, so the row stayed blank
        # forever. CW is a virtual surface; in auto mode we allow remote fill.
        if not seed_meta.get('poster'):
            seed_meta['poster'] = bundle.get('poster') or ''
        if not seed_meta.get('background'):
            seed_meta['background'] = bundle.get('fanart') or bundle.get('landscape') or ''
        if not seed_meta.get('clearlogo'):
            seed_meta['clearlogo'] = bundle.get('clearlogo') or ''
            seed_meta['logo'] = seed_meta['clearlogo'] or ''
        # Hard fallback only in auto mode. If the user explicitly chose
        # TMDb Helper/Trakt/Cinemeta, do not bypass that choice with API art.
        if not (seed_meta.get('poster') and seed_meta.get('background')):
            try:
                direct_bundle = _tmdb_direct.art_for(
                    tmdb_id=tmdb_id, imdb_id=imdb_id,
                    media_type=media_type, title=row.get('title') or '',
                ) or {}
                if not seed_meta.get('poster'):
                    seed_meta['poster'] = direct_bundle.get('poster') or ''
                if not seed_meta.get('background'):
                    seed_meta['background'] = direct_bundle.get('fanart') or direct_bundle.get('landscape') or ''
                if not seed_meta.get('clearlogo'):
                    seed_meta['clearlogo'] = direct_bundle.get('clearlogo') or ''
                    seed_meta['logo'] = seed_meta['clearlogo'] or ''
            except Exception:
                pass

    meta = _virtual_meta_override(target_key, media_kind, seed_meta)
    try:
        _meta_mem_put(media_kind, row.get('canonical_id') or '', meta, source_provider_id=target_key)
    except Exception:
        pass
    if explicit_source:
        poster = meta.get('poster') or ''
        background = meta.get('background') or meta.get('fanart') or meta.get('landscape') or ''
        clearlogo = meta.get('clearlogo') or ''
    else:
        poster = meta.get('poster') or seed_meta.get('poster') or ''
        background = meta.get('background') or meta.get('fanart') or meta.get('landscape') or seed_meta.get('background') or ''
        clearlogo = meta.get('clearlogo') or seed_meta.get('clearlogo') or ''
    # Last pass for virtual rows: if the selected meta source still didn't
    # provide a movie/show fanart, use the same resolver shared by Next Up and
    # Favorites. This keeps Continue Watching from falling back to the addon
    # background or poster when a real title fanart exists.
    if not explicit_source and (not background or tokenized_art):
        try:
            resolved_art = _resolve_row_art(dict(row, poster=poster, background=background, clearlogo=clearlogo)) or {}
            poster = poster or resolved_art.get('poster') or resolved_art.get('thumb') or ''
            background = resolved_art.get('fanart') or resolved_art.get('landscape') or background or ''
            clearlogo = clearlogo or resolved_art.get('clearlogo') or ''
        except Exception:
            pass
    if poster or background or clearlogo:
        try:
            playback_store.update_art(
                row.get('media_type'), row.get('canonical_id'), row.get('video_id'),
                poster, background, clearlogo,
            )
        except Exception:
            pass
        row = dict(row)
        row['poster'] = poster
        row['background'] = background
        row['clearlogo'] = clearlogo
    return row


def _continue_item_source_path(row):
    is_episode = _continue_row_is_episode(row)
    # Bug fix (3.7.91): pass resume_percent as a fallback. Trakt-imported rows
    # often have position=0 because Trakt's /sync/playback didn't return
    # runtime (now fetched via ?extended=full, but legacy DB rows may still
    # have position=0 with a valid percent). The seek logic in
    # _post_start_chores will use percent × player.getTotalTime() to
    # compute the resume target if seconds are missing.
    try:
        position_raw = row.get('position')
        position_val = float(position_raw) if position_raw not in (None, '') else 0.0
    except Exception:
        position_val = 0.0
    try:
        percent_raw = row.get('percent')
        percent_val = float(percent_raw) if percent_raw not in (None, '') else 0.0
    except Exception:
        percent_val = 0.0
    common = {
        'title': row.get('title') or row.get('canonical_id') or '',
        'resume_seconds': position_val if position_val > 1.0 else 0,
        'resume_percent': ('%.2f' % percent_val) if (position_val <= 1.0 and percent_val > 1.0 and percent_val < 95.0) else '',
        'preferred_provider_name': row.get('provider_name') or '',
        'source_provider_id': _cw_target_key(row),
    }
    if is_episode:
        return build_url(action='episode_streams', canonical_id=row.get('canonical_id'), video_id=row.get('video_id'), season=row.get('season'), episode=row.get('episode'), media_type=row.get('media_type') or 'series', **common)
    return build_url(action='streams', media_type=row.get('media_type'), canonical_id=row.get('canonical_id'), **common)


def cw_resume(media_type='', canonical_id='', video_id='', season='', episode='', title='', position='0', resume_percent='', provider_name='', direct='0', source_provider_id=''):
    target_media_type = media_type or ('series' if season not in (None, '', '0', 0) and episode not in (None, '', '0', 0) else 'movie')
    is_direct = str(direct or '').strip().lower() in ('1', 'true', 'yes', 'on')
    if is_direct:
        if target_media_type in ('series', 'tv', 'show', 'anime') or (season not in (None, '', '0', 0) and episode not in (None, '', '0', 0)):
            return _auto_play_first_episode(canonical_id, video_id or canonical_id, season, episode, title=title or canonical_id, resume_seconds=position or '0', resume_percent=resume_percent or '', preferred_provider_name=provider_name or '', source_provider_id=source_provider_id or '')
        return _auto_play_first_movie(canonical_id, title=title or canonical_id, resume_seconds=position or '0', resume_percent=resume_percent or '', preferred_provider_name=provider_name or '', source_provider_id=source_provider_id or '')
    # Continue Watching must honor Dex Hub's own resume position. Redirecting
    # here to TMDb Helper discards our stored resume_seconds and the item starts
    # from the beginning. Keep this path inside Dex Hub; users still have an
    # explicit player chooser in the context menu when they want TMDb Helper.
    return _dispatch_dexhub_play(
        media_type=target_media_type,
        canonical_id=canonical_id,
        title=title or canonical_id,
        video_id=video_id,
        season=season,
        episode=episode,
        resume_seconds=position or '0',
        resume_percent=resume_percent or '',
        preferred_provider_name=provider_name or '',
        source_provider_id=source_provider_id or '',
    )


def cw_play_from_start(media_type='', canonical_id='', video_id='', season='', episode='', title='', provider_name=''):
    return cw_resume(
        media_type=media_type,
        canonical_id=canonical_id,
        video_id=video_id,
        season=season,
        episode=episode,
        title=title,
        position='0',
        provider_name=provider_name,
        direct='1',
    )


def _continue_row_is_episode(row):
    try:
        return int(row.get('season') or 0) > 0 and int(row.get('episode') or 0) >= 0
    except Exception:
        return False


def _continue_item_from_start_path(row):
    row = dict(row or {})
    row['position'] = 0
    return _continue_item_source_path(row)


def continue_watching(page='0'):
    # Keep the screen snappy: slice first, then enrich only the visible rows.
    all_rows = playback_store.list_continue_items(limit=500)
    page_num, _page_size, raw_rows, has_more = _page_slice(all_rows, page)
    rows = []
    for _row, _filled in run_parallel(_lazy_fill_row_art, raw_rows):
        rows.append(_filled if not isinstance(_filled, Exception) else _row)
    any_series = any(_continue_row_is_episode(r) for r in rows)
    any_movie = any(not _continue_row_is_episode(r) for r in rows)
    if any_series and not any_movie:
        content_type = 'episodes'
    elif any_movie and not any_series:
        content_type = 'movies'
    else:
        content_type = 'movies'

    for row in rows:
        title = row.get('title') or row.get('canonical_id')
        is_episode = _continue_row_is_episode(row)
        source_path = _continue_item_source_path(row)
        from_start_source_path = _continue_item_from_start_path(row)
        resume_path = build_url(
            action='cw_resume',
            media_type=row.get('media_type') or ('series' if is_episode else 'movie'),
            canonical_id=row.get('canonical_id') or '',
            video_id=row.get('video_id') or '',
            season=row.get('season') or '',
            episode=row.get('episode') or '',
            title=row.get('title') or row.get('canonical_id') or '',
            position=row.get('position') or 0,
            resume_percent=row.get('percent') or '',
            provider_name=row.get('provider_name') or '',
            direct='1',
            source_provider_id=_cw_target_key(row),
        )
        play_from_start_path = build_url(
            action='cw_play_from_start',
            media_type=row.get('media_type') or ('series' if is_episode else 'movie'),
            canonical_id=row.get('canonical_id') or '',
            video_id=row.get('video_id') or '',
            season=row.get('season') or '',
            episode=row.get('episode') or '',
            title=row.get('title') or row.get('canonical_id') or '',
            provider_name=row.get('provider_name') or '',
            direct='1',
        )
        row_ids = _merge_seed_ids(extract_ids({'id': row.get('canonical_id') or ''}), _get_tmdbh_seed_ids(row.get('canonical_id') or ''))
        # Continue Watching always opens Dex Hub's source picker so resume_seconds
        # is preserved and the user can choose the source/provider. TMDb Helper is
        # still available from the explicit player chooser context menu.
        path, path_is_folder = source_path, True
        if is_episode:
            display_title = '%s — S%02dE%02d' % (title, int(row.get('season') or 0), int(row.get('episode') or 0))
            mediatype = 'episode'
        else:
            display_title = title
            mediatype = 'movie'

        percent = float(row.get('percent') or 0.0)
        position = float(row.get('position') or 0.0)
        duration = float(row.get('duration') or 0.0)
        info = {
            'title': display_title,
            'plot': '%.1f%% • %s' % (percent, row.get('provider_name') or ''),
            'mediatype': mediatype,
        }
        if is_episode:
            info['tvshowtitle'] = title
            info['season'] = int(row.get('season') or 0)
            info['episode'] = int(row.get('episode') or 0)
        info['playcount'] = 0
        if duration > 0:
            info['duration'] = int(duration)

        _poster_art = _wrap_tokenized_url(row.get('poster') or '')
        _bg_art = _wrap_tokenized_url(row.get('background') or '') or addon_fanart()
        _logo_art = _wrap_tokenized_url(row.get('clearlogo') or '')
        art = {
            'thumb': _poster_art,
            'poster': _poster_art,
            'fanart': _bg_art,
            'landscape': _bg_art or _poster_art,
            'clearlogo': _logo_art,
        }
        if _logo_art:
            art['logo'] = _logo_art
            art['tvshow.clearlogo'] = _logo_art

        properties = {}
        if not path_is_folder:
            if duration > 0 and position > 0:
                properties['ResumeTime'] = str(int(position))
                properties['TotalTime'] = str(int(duration))
            properties['IsPlayable'] = 'true'
            if percent:
                properties['WatchedProgress'] = str(int(percent))
                properties['PercentPlayed'] = str(int(percent))

        # row_ids already computed above (line ~4711); reuse it here.
        target_key = _cw_target_key(row)
        target_title = 'متابعة المشاهدة • مسلسلات/أنمي' if target_key.endswith('series') else 'متابعة المشاهدة • أفلام'
        resume_menu_action     = 'RunPlugin(%s)' % resume_path
        from_start_menu_action = 'RunPlugin(%s)' % play_from_start_path
        context_menu = [
            ('اختيار المصدر', 'Container.Update(%s)' % source_path),
            ('استكمال مباشر', resume_menu_action),
            ('تشغيل من البداية', from_start_menu_action),
            ('فتح المسلسل' if is_episode else 'فتح التفاصيل', 'Container.Update(%s)' % (build_url(action='series_meta', media_type='series', canonical_id=row.get('canonical_id') or '', title=title) if is_episode else build_url(action='item_open', media_type=row.get('media_type') or 'movie', canonical_id=row.get('canonical_id') or '', title=title, tmdb_id=row_ids.get('tmdb_id') or '', imdb_id=row_ids.get('imdb_id') or '', tvdb_id=row_ids.get('tvdb_id') or ''))),
            ('تغيير مصدر الميتاداتا', 'RunPlugin(%s)' % build_url(action='meta_pick_target', target_key=target_key, title=target_title)),
        ] + _build_player_chooser_menu(
            media_type='series' if is_episode else (row.get('media_type') or 'movie'),
            canonical_id=row.get('canonical_id') or '',
            title=title,
            tmdb_id=row_ids.get('tmdb_id') or '',
            imdb_id=row_ids.get('imdb_id') or '',
            tvdb_id=row_ids.get('tvdb_id') or '',
            season=row.get('season') or '',
            episode=row.get('episode') or '',
            video_id=row.get('video_id') or '',
        ) + [
            ('إزالة من متابعة المشاهدة', 'RunPlugin(%s)' % build_url(action='cw_remove', media_type=row.get('media_type'), canonical_id=row.get('canonical_id'), video_id=row.get('video_id'))),
            ('وسم كمشاهد', 'RunPlugin(%s)' % build_url(action='cw_mark_watched', media_type=row.get('media_type'), canonical_id=row.get('canonical_id'), video_id=row.get('video_id'))),
        ]

        add_item(display_title, path, is_folder=path_is_folder, info=info, art=art, properties=properties if not path_is_folder else {}, context_menu=context_menu)
    if has_more:
        add_item(
            'المزيد',
            build_url(action='continue', page=str(page_num + 1)),
            info={'title': 'المزيد', 'plot': 'تحميل عناصر إضافية من متابعة المشاهدة'},
            art=root_art('continue'),
        )
    end_dir(content=content_type, cache=False)


def cw_remove(media_type='', canonical_id='', video_id=''):
    try:
        playback_store.delete_entry(media_type, canonical_id, video_id)
        _invalidate_nextup_cache()
        notify('تم الإزالة من متابعة المشاهدة')
    except Exception as exc:
        error('تعذّر الإزالة: %s' % exc)
    xbmc.executebuiltin('Container.Refresh')


def cw_mark_watched(media_type='', canonical_id='', video_id=''):
    try:
        playback_store.mark_watched(media_type, canonical_id, video_id)
        _invalidate_nextup_cache()
        notify('تم وسمه كمشاهد')
    except Exception as exc:
        error('تعذّر الوسم: %s' % exc)
    xbmc.executebuiltin('Container.Refresh')


def refresh_provider(provider_id):
    """Re-fetch the manifest for a provider and update its cached snapshot."""
    row = store.get_provider(provider_id)
    if not row:
        error('المصدر غير موجود')
        return
    manifest_url = row.get('manifest_url') or ''
    if not manifest_url:
        error('رابط manifest غير معروف')
        return
    try:
        new_manifest = validate_manifest(manifest_url)
        store.refresh_provider_manifest(provider_id, new_manifest)
        notify('تم تحديث: %s' % (row.get('name') or provider_id))
    except Exception as exc:
        error('فشل التحديث: %s' % exc)
    xbmc.executebuiltin('Container.Refresh')





def formatter_refresh():
    try:
        _source_formatter.clear_cache()
        _source_formatter.format_stream({}, force_refresh=True)
        notify('تم تحديث preset الخاص بالمصادر')
    except Exception as exc:
        error('فشل تحديث preset: %s' % exc)
    try:
        xbmc.executebuiltin('Container.Refresh')
    except Exception:
        pass


def clear_cache():
    removed = 0
    try:
        from .dexhub import client as _client_mod
        removed += int(_client_mod.clear_http_cache() or 0)
    except Exception:
        pass
    try:
        cache_store.clear_all()
    except Exception:
        pass
    try:
        _SEARCH_RESULT_CACHE.clear()
        _SEARCH_RESULT_CACHE_ORDER[:] = []
    except Exception:
        pass
    _invalidate_nextup_cache()
    try:
        path = _source_pref_path()
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
    try:
        mon_path = _playback_monitor_path()
        if mon_path and os.path.exists(mon_path):
            os.remove(mon_path)
    except Exception:
        pass
    try:
        win = xbmcgui.Window(WINDOW_ID)
        for key in ('dexhub.fav_mirror_done', 'dexhub.fav_mirror_syncing', 'dexhub.fav_mirror_syncing_started'):
            try:
                win.clearProperty(key)
            except Exception:
                pass
        try:
            for prop_name in list(getattr(win, 'getPropertyKeys', lambda: [])() or []):
                if prop_name.startswith(SERIES_PROP_PREFIX):
                    try:
                        win.clearProperty(prop_name)
                    except Exception:
                        pass
        except Exception:
            pass
    except Exception:
        pass
    notify('تم مسح الكاش (%s ملف HTTP)' % removed if removed else 'تم مسح الكاش')
    try:
        xbmc.executebuiltin('Container.Refresh')
    except Exception:
        pass
    return end_dir()


def open_addon_settings():
    try:
        ADDON.openSettings()
    except Exception:
        xbmc.executebuiltin('Addon.OpenSettings(%s)' % ADDON.getAddonInfo('id'))


def trakt_menu():
    state = trakt.authorization_status()
    status = 'متصل' if state == 'connected' else 'جاهز للربط عبر PIN'
    plot = 'إدارة ربط ومزامنة Trakt عبر PIN فقط'
    add_item('حالة Trakt: %s' % status, build_url(action='trakt_menu'), is_folder=False, info={'title': 'Trakt', 'plot': plot}, art=root_art('trakt'))
    add_item('ربط Trakt عبر PIN', build_url(action='trakt_auth'), is_folder=False, art=root_art('trakt'),
             info={'title': 'ربط Trakt عبر PIN', 'plot': 'يعرض رابط trakt.tv/activate ورمز الربط ثم ينتظر التفويض'})
    add_item('استيراد التقدم من Trakt', build_url(action='trakt_import'), is_folder=False, art=root_art('continue'))
    add_item('تسجيل خروج Trakt', build_url(action='trakt_logout'), is_folder=False, art=root_art('add'))
    end_dir()


def trakt_auth():
    try:
        if trakt.device_auth():
            notify('تم ربط Trakt')
        else:
            error('تم إلغاء أو انتهت مهلة ربط Trakt')
    except Exception as exc:
        error('فشل ربط Trakt: %s' % exc)
    return trakt_menu()


def trakt_settings():
    open_addon_settings()
    return trakt_menu()


def trakt_logout():
    try:
        trakt.logout()
    except Exception as exc:
        error('فشل تسجيل الخروج: %s' % exc)
    return trakt_menu()


def trakt_import():
    try:
        count = trakt.import_progress(limit=100)
        _invalidate_nextup_cache()
        notify('تم استيراد %s عنصر من Trakt' % count)
    except Exception as exc:
        error('فشل استيراد Trakt: %s' % exc)
    return continue_watching()


def tmdbh_install():
    if not tmdbh_player.has_tmdbhelper():
        error('TMDb Helper غير مثبّت')
        return integrations_menu()
    was_installed = tmdbh_player.player_installed()
    if tmdbh_player.install(silent=False):
        notify('تم تحديث تسجيل Dex Hub في TMDb Helper' if was_installed else 'تم تسجيل Dex Hub في TMDb Helper')
        # Explain the one-time manual step to set Dex Hub as the default player.
        try:
            xbmcgui.Dialog().ok(
                'Dex Hub • TMDb Helper',
                tr(
                    '[B]تم التسجيل/التحديث بنجاح ✓[/B]\n\n'
                    'زر TMDb Helper الآن يعيد تسجيل Dex Hub بدل حذف التسجيل.\n\n'
                    'لتجنّب ظهور نافذة اختيار المشغّل في كل مرّة،\n'
                    'اجعل Dex Hub هو المشغّل الافتراضي:\n\n'
                    '[COLOR orange]TMDb Helper → الإعدادات → المشغّلات\n'
                    '→ Default Player (Movies) = Dex Hub\n'
                    '→ Default Player (TV Shows) = Dex Hub[/COLOR]\n\n'
                    'إلغاء التسجيل موجود في قائمة السياق فقط.'
                ),
            )
        except Exception:
            pass
    return integrations_menu()


def tmdbh_uninstall():
    if tmdbh_player.uninstall(silent=False):
        notify('تم إلغاء تسجيل Dex Hub من TMDb Helper')
    else:
        notify('المشغّل غير مسجّل أصلًا')
    return integrations_menu()


def play(stream_key, resume_seconds='', resume_percent=''):
    if _dispatch_in_flight('play|%s' % (stream_key or ''), window_seconds=4):
        xbmc.log('[DexHub] play: duplicate dispatch suppressed (%s)' % stream_key, xbmc.LOGINFO)
        return
    ctx = cache_store.get('stream', stream_key)
    if not ctx:
        error('انتهت بيانات التشغيل. أعد اختيار المصدر.')
        return end_dir()
    fallback = []
    try:
        sess = load_session() or {}
        fallback = list(sess.get('fallback_stream_keys') or [])[:1]
    except Exception:
        fallback = []
    try:
        rs = float(resume_seconds or 0.0)
    except Exception:
        rs = 0.0
    if rs > 1.0:
        ctx = dict(ctx or {})
        ctx['resume_seconds'] = rs
    try:
        rp = float(resume_percent or 0.0)
    except Exception:
        rp = 0.0
    if rp > 1.0 and rp < 95.0:
        ctx = dict(ctx or {})
        ctx['resume_percent'] = rp
    _play_with_context(ctx, stream_key, fallback_keys=fallback)


# ═════════════ Collection Sets (Fusion-Starter-Kit style) ═════════════

def _make_addon_manifest_resolver(host_hint=''):
    """Return a callback (addon_id, share_url) -> manifest_url for use by
    collection imports. Prompts the user once per unique unresolved addonId."""

    def _resolver(addon_id, share_url):
        try:
            known_manifest = _collections_mod.known_manifest_for_addon_id(addon_id)
            if known_manifest:
                return known_manifest
        except Exception:
            pass
        msg_lines = [
            tr('هذه المجموعة تعتمد على إضافة لم تُثبَّت بعد:'),
            '[COLOR yellow]%s[/COLOR]' % addon_id,
            '',
        ]
        if host_hint:
            msg_lines.extend([
                tr('يبدو أنها مستضافة على:'),
                '[COLOR yellow]%s[/COLOR]' % host_hint,
                '',
            ])
        try:
            if _collections_mod.addon_requires_configuration(addon_id):
                msg_lines.append(tr('هذه الإضافة تحتاج رابط Manifest مُعدّ بحسابك/مكتبتك، وليس manifest العام.'))
                msg_lines.append('')
        except Exception:
            pass
        msg_lines.append(tr('هل لديك رابط manifest.json الخاص بها؟'))
        want = xbmcgui.Dialog().yesno(
            tr('إضافة مفقودة'),
            '\n'.join(msg_lines),
            nolabel=tr('تخطّي'), yeslabel=tr('ألصق رابطًا'),
        )
        if not want:
            return ''
        kb = xbmc.Keyboard('', tr('ألصق رابط manifest.json لـ %s') % addon_id)
        kb.doModal()
        if not kb.isConfirmed():
            return ''
        return kb.getText().strip()

    return _resolver


def collection_set_add():
    """Prompt for a JSON URL (or paste), then a custom display name."""
    keyboard = xbmc.Keyboard('', tr('ألصق رابط JSON أو النص كاملًا'))
    keyboard.doModal()
    if not keyboard.isConfirmed():
        return end_dir()
    raw = keyboard.getText().strip()
    if not raw:
        return end_dir()

    # Fetch + parse first so we can show a meaningful default name and fail
    # with a clear message before the user is asked to name anything.
    is_url = raw.startswith('http://') or raw.startswith('https://')
    try:
        if is_url:
            text = _collections_mod.fetch_raw_text(raw)
        else:
            text = raw
        parsed_entries = _collections_mod.parse_collection_json(text)
    except Exception as exc:
        error('فشل قراءة الملف: %s' % exc)
        return home()

    default_name = _collections_mod._derive_set_name(raw if is_url else '', parsed_entries)
    # Optional: ask user for a name.
    kb2 = xbmc.Keyboard(default_name, tr('اسم المجموعة (اتركه كما هو إذا رضيت)'))
    kb2.doModal()
    custom_name = kb2.getText().strip() if kb2.isConfirmed() else default_name

    # Duplicate detection by URL — offer to refresh instead of re-importing.
    if is_url:
        for existing in _collections_mod.list_sets():
            if existing.get('source_url') == raw:
                if xbmcgui.Dialog().yesno('Dex Hub', tr('هذه المجموعة موجودة بالفعل. هل تريد تحديثها؟')):
                    try:
                        updated = _collections_mod.refresh_set(existing.get('id'), manifest_resolver=_make_addon_manifest_resolver(''))
                        if custom_name and custom_name != updated.get('name'):
                            _collections_mod.rename_set(existing.get('id'), custom_name)
                        notify('تم تحديث المجموعة')
                    except Exception as exc:
                        error('تعذّر التحديث: %s' % exc)
                return collection_sets()

    try:
        # Build a resolver that prompts the user for any missing addonId.
        # The user only sees this for addons that aren't already installed,
        # and we deduplicate so each unique addonId is asked once.
        host_hint = _collections_mod.derive_addon_manifest_url(raw if is_url else '', '') or ''
        resolver = _make_addon_manifest_resolver(host_hint)
        if is_url:
            set_row = _collections_mod.add_set_from_url(raw, name=custom_name, manifest_resolver=resolver)
        else:
            set_row = _collections_mod.add_set_from_text(raw, source_label=custom_name, manifest_resolver=resolver)
    except Exception as exc:
        error('فشل الاستيراد: %s' % exc)
        return home()
    notify('تم استيراد %d اختصار' % len(set_row.get('entries') or []))
    return collection_sets()



def collection_set_export(set_id=''):
    row = _collections_mod.get_set(set_id) if set_id else None
    rows = [row] if row else _collections_mod.list_sets()
    rows = [r for r in rows if isinstance(r, dict)]
    if not rows:
        notify('لا يوجد كوليكشن للتصدير')
        return collection_sets()
    default_name = 'dexhub-collections-backup.json' if not row else 'dexhub-%s.json' % re.sub(r'[^A-Za-z0-9_-]+', '-', row.get('name') or row.get('id') or 'collection').strip('-')
    try:
        folder = xbmcgui.Dialog().browse(0, tr('اختر مجلد حفظ النسخة'), 'files')
    except Exception:
        folder = ''
    if not folder:
        return collection_sets()
    path = os.path.join(xbmcvfs.translatePath(folder), default_name)
    payload = {'format': 'dexhub.collection.backup', 'version': 1, 'exported_at': int(time.time()), 'collections': rows}
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except Exception:
        pass
    try:
        fh = xbmcvfs.File(path, 'w')
        fh.write(json.dumps(payload, ensure_ascii=False, indent=2))
        fh.close()
        notify('تم حفظ نسخة الكوليكشن')
        xbmcgui.Dialog().ok('Dex Hub', 'تم حفظ النسخة:\n%s' % path)
    except Exception as exc:
        error('فشل التصدير: %s' % exc)
    return collection_sets()


def collection_set_import_backup():
    try:
        path = xbmcgui.Dialog().browse(1, tr('اختر ملف نسخة الكوليكشن'), 'files', '.json')
    except Exception:
        path = ''
    if not path:
        return collection_sets()
    try:
        fh = xbmcvfs.File(path)
        raw = fh.read()
        fh.close()
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8', 'ignore')
        data = json.loads(raw or '{}')
        if isinstance(data, dict) and isinstance(data.get('collections'), list):
            imported = _collections_mod.import_sets(data.get('collections') or [])
        elif isinstance(data, list):
            # A Dex Hub backup list has rows with `entries`. Nuvio/Fusion
            # profile backups are also top-level lists, but they use
            # `folders[]`/`catalogSources[]`; importing those as a Dex backup
            # silently produced 0 groups. Detect that shape and parse it as a
            # normal collection JSON instead.
            looks_like_dex_backup = any(isinstance(r, dict) and isinstance(r.get('entries'), list) for r in data)
            if looks_like_dex_backup:
                imported = _collections_mod.import_sets(data)
            else:
                name = os.path.splitext(os.path.basename(path))[0]
                imported_row = _collections_mod.add_set_from_text(raw, source_label=name, manifest_resolver=_make_addon_manifest_resolver(''))
                imported = 1 if imported_row else 0
        else:
            # Also allow importing a plain Nuvio/Fusion JSON as a new set.
            name = os.path.splitext(os.path.basename(path))[0]
            imported_row = _collections_mod.add_set_from_text(raw, source_label=name, manifest_resolver=_make_addon_manifest_resolver(''))
            imported = 1 if imported_row else 0
        notify('تم استيراد %d مجموعة' % int(imported or 0))
    except Exception as exc:
        error('فشل الاستيراد: %s' % exc)
    xbmc.executebuiltin('Container.Refresh')
    return collection_sets()

def collection_set_rename(set_id):
    row = _collections_mod.get_set(set_id)
    if not row:
        error('المجموعة غير موجودة')
        return
    kb = xbmc.Keyboard(row.get('name') or '', tr('اسم المجموعة الجديد'))
    kb.doModal()
    if not kb.isConfirmed():
        return
    new_name = kb.getText().strip()
    if not new_name:
        return
    try:
        _collections_mod.rename_set(set_id, new_name)
        notify('تم إعادة التسمية')
    except Exception as exc:
        error('تعذّر التعديل: %s' % exc)
    xbmc.executebuiltin('Container.Refresh')


def collection_sets():
    """List every saved collection set as a folder."""
    rows = sorted(_collections_mod.list_sets(), key=lambda r: (r.get('name') or '').lower())
    add_item('[COLOR yellow]+ استيراد مجموعة من JSON[/COLOR]', build_url(action='collection_set_add'), is_folder=False, art=root_art('add'))
    add_item('[COLOR yellow]+ استيراد Backup للكوليكشن[/COLOR]', build_url(action='collection_set_import_backup'), is_folder=False, art=root_art('add'))
    add_item('[COLOR yellow]تصدير Backup لكل الكوليكشن[/COLOR]', build_url(action='collection_set_export'), is_folder=False, art=root_art('catalogs'))
    add_item('[COLOR yellow]+ إنشاء مجموعة فارغة (يدويًا)[/COLOR]', build_url(action='collection_set_create_empty'), is_folder=False, art=root_art('add'))
    for row in rows:
        label = row.get('name') or 'Collection Set'
        entries = row.get('entries') or []
        kinds = {}
        for e in entries:
            k = e.get('kind') or 'other'
            kinds[k] = kinds.get(k, 0) + 1
        kind_line = ' / '.join('%s: %d' % (k, v) for k, v in kinds.items())
        plot_lines = ['[B]%s[/B]' % label, '%d اختصار' % len(entries)]
        if kind_line:
            plot_lines.append(kind_line)
        if row.get('source_url'):
            plot_lines.append('المصدر: %s' % row.get('source_url'))
        info = {'title': label, 'plot': '\n'.join(plot_lines)}
        ctx_menu = [
            ('إضافة عنصر يدويًا', 'RunPlugin(%s)' % build_url(action='collection_entry_add', set_id=row.get('id'))),
            ('إعادة تسمية', 'RunPlugin(%s)' % build_url(action='collection_set_rename', set_id=row.get('id'))),
            ('إدارة مصادر الميتاداتا', 'RunPlugin(%s)' % build_url(action='meta_sources_dialog')),
            ('تحديث المجموعة', 'RunPlugin(%s)' % build_url(action='collection_set_refresh', set_id=row.get('id'))),
            ('تصدير Backup', 'RunPlugin(%s)' % build_url(action='collection_set_export', set_id=row.get('id'))),
            ('إزالة المجموعة', 'RunPlugin(%s)' % build_url(action='collection_set_remove', set_id=row.get('id'))),
        ]
        add_item(label, build_url(action='collection_set_browse', set_id=row.get('id')), info=info, art=root_art('catalogs'), context_menu=ctx_menu)
    if not rows:
        add_item('[COLOR grey]لا توجد مجموعات حتى الآن — أضف واحدة بالأعلى[/COLOR]', build_url(action='collection_sets'), is_folder=False, info={'title': 'فارغ'})
    end_dir()


def _trakt_local_poster(meta):
    meta = meta or {}
    poster = str(meta.get('poster') or meta.get('thumbnail') or meta.get('thumb') or '').strip()
    images = meta.get('images') or {}
    if isinstance(images, dict):
        for key in ('poster', 'thumb', 'thumbnail'):
            node = images.get(key) or {}
            if isinstance(node, dict):
                poster = poster or str(node.get('full') or node.get('medium') or node.get('thumb') or '').strip()
            elif node:
                poster = poster or str(node).strip()
    return poster


def _trakt_art_bundle(ids, media_type, title='', year='', meta=None, force_remote=False, allow_direct=True):
    ids = ids or {}
    tmdb_id = str(ids.get('tmdb') or ids.get('tmdb_id') or '').strip()
    imdb_id = str(ids.get('imdb') or ids.get('imdb_id') or '').strip()
    local_mode = posters_prefer_local() and not force_remote
    local_poster = _trakt_local_poster(meta) if local_mode else ''
    db_bundle = {}
    try:
        db_bundle = _tmdb_art_db.get_art_bundle_from_db(
            tmdb_id=tmdb_id,
            imdb_id=imdb_id,
            media_type='tv' if media_type in ('series', 'anime', 'show', 'tv') else 'movie',
            title=title or '',
            year=year or '',
        ) or {}
    except Exception:
        db_bundle = {}
    need_direct = allow_direct and not (db_bundle.get('fanart') and db_bundle.get('clearlogo') and (local_mode or db_bundle.get('poster')))
    if need_direct:
        try:
            direct_bundle = _tmdb_direct.art_for(
                tmdb_id=tmdb_id,
                imdb_id=imdb_id,
                media_type='tv' if media_type in ('series', 'anime', 'show', 'tv') else 'movie',
                title=title or '',
                year=year or '',
            ) or {}
        except Exception:
            direct_bundle = {}
    else:
        direct_bundle = {}
    poster = local_poster if local_mode else (db_bundle.get('poster') or direct_bundle.get('poster') or local_poster or '')
    return {
        'poster': poster,
        'fanart': db_bundle.get('fanart') or db_bundle.get('landscape') or direct_bundle.get('fanart') or direct_bundle.get('landscape') or '',
        'landscape': db_bundle.get('landscape') or db_bundle.get('fanart') or direct_bundle.get('landscape') or direct_bundle.get('fanart') or '',
        'clearlogo': db_bundle.get('clearlogo') or direct_bundle.get('clearlogo') or '',
    }

def _trakt_info(meta, media_type):
    is_series = media_type in ('series', 'anime', 'show', 'tv')
    info = {
        'title': meta.get('title') or '',
        'sorttitle': meta.get('title') or '',
        'plot': meta.get('overview') or meta.get('summary') or '',
        'mediatype': 'tvshow' if is_series else 'movie',
    }
    year = meta.get('year')
    if year:
        try:
            info['year'] = int(year)
        except Exception:
            pass
    if meta.get('rating') not in (None, ''):
        try:
            info['rating'] = float(meta.get('rating') or 0.0)
        except Exception:
            pass
    if meta.get('votes') not in (None, ''):
        try:
            info['votes'] = int(meta.get('votes') or 0)
        except Exception:
            pass
    if meta.get('runtime'):
        try:
            info['duration'] = int(float(meta.get('runtime') or 0) * 60)
        except Exception:
            pass
    genres = meta.get('genres') or []
    if genres:
        info['genre'] = ' / '.join(genres)
    studio = meta.get('network') or meta.get('studio') or ''
    if studio:
        info['studio'] = studio
    if meta.get('certification'):
        info['mpaa'] = meta.get('certification')
    premiered = meta.get('released') or meta.get('first_aired') or ''
    if premiered:
        info['premiered'] = str(premiered)[:10]
        info['date'] = str(premiered)[:10]
    tagline = meta.get('tagline') or ''
    if tagline:
        info['tagline'] = tagline
    status = meta.get('status') or ''
    country = meta.get('country') or ''
    if status and country:
        info['status'] = '%s • %s' % (status, country)
    elif status:
        info['status'] = status
    elif country:
        info['status'] = country
    return info


def _provider_for_manifest_url(manifest_url):
    manifest_url = (manifest_url or '').strip()
    if not manifest_url:
        return None
    for row in store.list_providers():
        if (row.get('manifest_url') or '').strip() == manifest_url:
            return row
    return None


def _provider_for_addon_ref(addon_ref):
    addon_ref = (addon_ref or '').strip()
    if not addon_ref:
        return None
    provider = _provider_for_manifest_url(addon_ref)
    if provider:
        return provider
    try:
        return _collections_mod.find_provider_by_addon_id(addon_ref)
    except Exception:
        return None


def _prompt_text(default_text, heading):
    kb = xbmc.Keyboard(default_text or '', tr(heading))
    kb.doModal()
    if not kb.isConfirmed():
        return None
    return (kb.getText() or '').strip()


def _collection_media_filter_options():
    return [('auto', 'تلقائي / مختلط'), ('movie', 'أفلام'), ('series', 'مسلسلات'), ('anime', 'أنمي')]


def _pick_collection_media_filter(default='auto'):
    opts = _collection_media_filter_options()
    values = [label for _value, label in opts]
    default_value = str(default or 'auto').strip().lower()
    default_index = next((i for i, (value, _label) in enumerate(opts) if value == default_value), 0)
    try:
        choice = xbmcgui.Dialog().select(tr('نوع المحتوى'), [tr(x) for x in values], preselect=default_index)
    except TypeError:
        choice = xbmcgui.Dialog().select(tr('نوع المحتوى'), [tr(x) for x in values])
    if choice < 0:
        return None
    return opts[choice][0]


def _collection_media_filter_label(value):
    value = str(value or 'auto').strip().lower()
    return dict(_collection_media_filter_options()).get(value, 'تلقائي / مختلط')


def _collection_open_mode_options():
    return [('normal', 'عادي'), ('skip', 'تخطي الفلاتر/المجلد الأول')]


def _pick_collection_open_mode(default='normal'):
    opts = _collection_open_mode_options()
    values = [label for _value, label in opts]
    default_value = str(default or 'normal').strip().lower()
    default_index = next((i for i, (value, _label) in enumerate(opts) if value == default_value), 0)
    try:
        choice = xbmcgui.Dialog().select(tr('طريقة فتح العنصر'), [tr(x) for x in values], preselect=default_index)
    except TypeError:
        choice = xbmcgui.Dialog().select(tr('طريقة فتح العنصر'), [tr(x) for x in values])
    if choice < 0:
        return None
    return opts[choice][0]


def _collection_open_mode_label(value):
    value = str(value or 'normal').strip().lower()
    return dict(_collection_open_mode_options()).get(value, 'عادي')


def _derive_name_from_slug(slug):
    slug = str(slug or '').strip().strip('/')
    if not slug:
        return 'Collection'
    name = slug.replace('-', ' ').replace('_', ' ')
    return MULTI_WS_RE.sub(' ', name).strip().title() or 'Collection'


def _parse_trakt_list_url(raw_url):
    raw_url = (raw_url or '').strip()
    if not raw_url:
        return None
    try:
        parsed = urlparse(raw_url)
    except Exception:
        return None
    host = (parsed.netloc or '').lower()
    if 'trakt.tv' not in host:
        return None
    parts = [p for p in (parsed.path or '').split('/') if p]
    if len(parts) < 4 or parts[0] != 'users' or parts[2] != 'lists':
        return None
    username = parts[1].strip()
    slug = parts[3].strip()
    if not username or not slug:
        return None
    return {'username': username, 'slug': slug, 'name': _derive_name_from_slug(slug), 'url': 'https://trakt.tv/users/%s/lists/%s' % (username, slug)}


def _parse_mdblist_list_url(raw_url):
    parsed = mdblist.parse_list_url(raw_url)
    if not parsed:
        return None
    parsed['name'] = _derive_name_from_slug(parsed.get('slug') or '')
    return parsed

def _list_installed_video_addons():
    rows = []
    try:
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Addons.GetAddons',
            'params': {
                'type': 'xbmc.addon.video',
                'properties': ['name', 'summary', 'thumbnail', 'fanart', 'enabled'],
            },
        }
        raw = xbmc.executeJSONRPC(json.dumps(payload))
        data = json.loads(raw or '{}')
        for addon in ((data.get('result') or {}).get('addons') or []):
            addon_id = str(addon.get('addonid') or '').strip()
            if not addon_id or addon_id == ADDON.getAddonInfo('id'):
                continue
            if addon.get('enabled') is False:
                continue
            rows.append({
                'id': addon_id,
                'name': addon.get('name') or addon_id,
                'summary': addon.get('summary') or '',
                'thumbnail': addon.get('thumbnail') or '',
                'fanart': addon.get('fanart') or '',
            })
    except Exception as exc:
        xbmc.log('[DexHub] list installed video addons failed: %s' % exc, xbmc.LOGWARNING)
    rows.sort(key=lambda x: (str(x.get('name') or '')).lower(), reverse=False)
    return rows


def _pick_installed_video_addon():
    rows = _list_installed_video_addons()
    if not rows:
        error('لا توجد إضافات فيديو مثبّتة')
        return None
    labels = [row.get('name') or row.get('id') or 'Addon' for row in rows]
    choice = xbmcgui.Dialog().select(tr('اختر إضافة Kodi'), [tr(x) for x in labels])
    if choice < 0 or choice >= len(rows):
        return None
    return rows[choice]


def _normalize_plugin_route(addon_id, route_text=''):
    addon_id = str(addon_id or '').strip()
    route_text = str(route_text or '').strip()
    if not addon_id and not route_text.startswith('plugin://'):
        return ''
    if route_text.startswith('plugin://'):
        return route_text
    if not route_text:
        return 'plugin://%s/' % addon_id
    if route_text.startswith('?'):
        return 'plugin://%s/%s' % (addon_id, route_text)
    if route_text.startswith('/'):
        return 'plugin://%s%s' % (addon_id, route_text)
    return 'plugin://%s/%s' % (addon_id, route_text)


def _list_plugin_directory_items(directory):
    directory = str(directory or '').strip()
    if not directory:
        return []
    rows = []
    try:
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Files.GetDirectory',
            'params': {
                'directory': directory,
                'media': 'video',
                'properties': ['title', 'thumbnail', 'fanart', 'plot'],
            },
        }
        raw = xbmc.executeJSONRPC(json.dumps(payload))
        data = json.loads(raw or '{}')
        result = data.get('result') or {}
        for item in (result.get('files') or []):
            file_url = str(item.get('file') or '').strip()
            if not file_url.startswith('plugin://'):
                continue
            filetype = str(item.get('filetype') or '').strip().lower()
            label = str(item.get('label') or item.get('title') or item.get('label2') or file_url).strip()
            rows.append({
                'file': file_url,
                'label': label or file_url,
                'is_folder': filetype == 'directory',
                'thumbnail': item.get('thumbnail') or '',
                'fanart': item.get('fanart') or '',
                'plot': item.get('plot') or '',
            })
    except Exception as exc:
        xbmc.log('[DexHub] list plugin directory failed for %s: %s' % (directory, exc), xbmc.LOGWARNING)
    return rows


def _browse_kodi_plugin_route(addon_row, start_route=''):
    addon_id = str((addon_row or {}).get('id') or '').strip()
    addon_name = str((addon_row or {}).get('name') or addon_id or 'Kodi').strip()
    current = _normalize_plugin_route(addon_id, start_route or '')
    if not current:
        return '', ''
    root = _normalize_plugin_route(addon_id, '')
    history = []
    current_label = addon_name
    browse_steps = 0
    while browse_steps < 30:
        browse_steps += 1
        items = _list_plugin_directory_items(current)
        labels = []
        actions = []
        if history:
            labels.append('.. %s' % tr('السابق'))
            actions.append(('back', None))
        labels.append('[COLOR yellow]%s[/COLOR]' % tr('استخدم هذا المسار'))
        actions.append(('choose_current', {'file': current, 'label': current_label or addon_name}))
        labels.append('[COLOR grey]%s[/COLOR]' % tr('إدخال يدوي'))
        actions.append(('manual', {'file': current, 'label': current_label or addon_name}))
        for item in items:
            icon = '📁 ' if item.get('is_folder') else '▶ '
            labels.append('%s%s' % (icon, item.get('label') or item.get('file') or 'Item'))
            actions.append(('entry', item))
        title = '%s — %s' % (tr('اختر مسار من الإضافة'), addon_name)
        choice = xbmcgui.Dialog().select(title, labels)
        if choice < 0:
            return '', ''
        action, payload = actions[choice]
        if action == 'back':
            current, current_label = history.pop()
            continue
        if action == 'choose_current':
            return str((payload or {}).get('file') or current).strip(), str((payload or {}).get('label') or current_label or addon_name).strip()
        if action == 'manual':
            route_text = _prompt_text(str((payload or {}).get('file') or current), 'رابط أو مسار plugin://')
            if route_text is None:
                continue
            route_url = _normalize_plugin_route(addon_id, route_text)
            if route_url:
                return route_url, str((payload or {}).get('label') or addon_name).strip()
            error('رابط plugin غير صالح')
            continue
        item = payload or {}
        item_file = str(item.get('file') or '').strip()
        item_label = str(item.get('label') or item_file or addon_name).strip()
        if not item_file:
            continue
        if item.get('is_folder'):
            history.append((current, current_label or addon_name))
            current = item_file
            current_label = item_label or addon_name
            continue
        return item_file, item_label or addon_name
    return '', ''


def _pick_kodi_plugin_route(addon_row, default_route=''):
    addon_id = str((addon_row or {}).get('id') or '').strip()
    choices = [tr('استعراض الإضافة'), tr('إدخال يدوي')]
    default_idx = 0
    mode_idx = xbmcgui.Dialog().select(tr('طريقة اختيار المسار'), choices, preselect=default_idx)
    if mode_idx < 0:
        return '', ''
    if mode_idx == 0:
        return _browse_kodi_plugin_route(addon_row, start_route=default_route)
    route_text = _prompt_text(str(default_route or 'plugin://%s/' % addon_id), 'رابط أو مسار plugin://')
    if route_text is None:
        return '', ''
    route_url = _normalize_plugin_route(addon_id, route_text)
    if not route_url:
        error('رابط plugin غير صالح')
        return '', ''
    return route_url, str((addon_row or {}).get('name') or addon_id or 'Kodi').strip()


def _prompt_local_json_file():
    try:
        path = xbmcgui.Dialog().browseSingle(1, tr('اختر ملف JSON محلي'), 'files', '.json|.txt', False, False, '')
    except Exception:
        path = ''
    path = str(path or '').strip()
    if path:
        return path
    return _prompt_text('', 'مسار ملف JSON محلي')


def _read_text_from_path(path):
    path = str(path or '').strip()
    if not path:
        raise ValueError('المسار فارغ')
    fh = None
    try:
        fh = xbmcvfs.File(path)
        data = fh.read()
    except Exception:
        translated = xbmcvfs.translatePath(path)
        with open(translated, 'rb') as fh2:
            data = fh2.read()
    finally:
        try:
            if fh:
                fh.close()
        except Exception:
            pass
    if isinstance(data, bytes):
        for enc in ('utf-8-sig', 'utf-8', 'cp1256', 'latin-1'):
            try:
                return data.decode(enc)
            except Exception:
                pass
        return data.decode('utf-8', 'replace')
    return str(data or '')


def _coerce_catalog_media_type(value, default='movie'):
    value = str(value or default).strip().lower()
    mapping = {
        'movie': 'movie', 'movies': 'movie', 'film': 'movie',
        'series': 'series', 'show': 'series', 'tv': 'series', 'tvshow': 'series', 'tvshows': 'series',
        'anime': 'anime',
        'episode': 'series', 'episodes': 'series',
    }
    return mapping.get(value, default or 'movie')


def _canonical_from_ids(media_type, title, year='', tmdb_id='', imdb_id='', tvdb_id=''):
    if tmdb_id:
        return 'tmdb:%s' % tmdb_id
    if imdb_id:
        return imdb_id
    if tvdb_id:
        return 'tvdb:%s' % tvdb_id
    slug = clean_title(title or '')
    if year:
        slug = '%s %s' % (slug, year)
    return slug or (title or 'item')


def _parse_local_json_catalog(text):
    try:
        data = json.loads(text)
    except Exception:
        try:
            data = json.loads((text or '').lstrip('﻿'))
        except Exception:
            raise ValueError('JSON غير صالح')
    meta = {}
    try:
        data = _collections_mod._flatten_fusion_widgets(data)
    except Exception:
        pass
    if isinstance(data, dict):
        for key in ('items', 'results', 'entries', 'videos', 'catalog', 'collections', 'widgets', 'folders'):
            if isinstance(data.get(key), list):
                meta = dict(data.get('meta') or {})
                data = data[key]
                break
        else:
            data = [data]
    try:
        data = _collections_mod._flatten_fusion_widgets(data)
    except Exception:
        pass
    if not isinstance(data, list):
        raise ValueError('الملف لا يحتوي على قائمة عناصر')
    return data, meta


def _render_local_json_catalog(entry, payload):
    file_path = str(payload.get('filePath') or payload.get('path') or '').strip()
    if not file_path:
        error('مسار الملف غير موجود')
        return end_dir()
    try:
        text = _read_text_from_path(file_path)
        rows, meta = _parse_local_json_catalog(text)
    except Exception as exc:
        error('فشل قراءة ملف JSON: %s' % exc)
        return end_dir()
    if not rows:
        error('الملف لا يحتوي على عناصر')
        return end_dir()

    try:
        limit = max(0, int(payload.get('limit') or 0))
    except Exception:
        limit = 0
    if limit > 0:
        rows = rows[:limit]

    win = xbmcgui.Window(WINDOW_ID)
    bg = entry.get('background') or meta.get('fanart') or meta.get('background') or ''
    if bg:
        win.setProperty('fanart', bg)

    content_hint = _coerce_catalog_media_type(payload.get('mediaFilter') or meta.get('media_type') or 'movie')
    has_seriesish = False
    added = 0
    fallback_art = root_art('catalogs')

    for raw in rows:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get('title') or raw.get('name') or '').strip()
        if not title:
            continue
        media_type = _coerce_catalog_media_type(raw.get('media_type') or raw.get('type') or raw.get('mediatype') or content_hint, content_hint)
        ids_raw = raw.get('ids') if isinstance(raw.get('ids'), dict) else {}
        tmdb_id = str(raw.get('tmdb_id') or ids_raw.get('tmdb') or '').strip()
        imdb_id = str(raw.get('imdb_id') or ids_raw.get('imdb') or '').strip()
        tvdb_id = str(raw.get('tvdb_id') or ids_raw.get('tvdb') or '').strip()
        year = str(raw.get('year') or raw.get('release_year') or '').strip()
        season = str(raw.get('season') or '').strip()
        episode = str(raw.get('episode') or '').strip()
        video_id = str(raw.get('video_id') or raw.get('id') or '').strip()
        canonical_id = str(raw.get('canonical_id') or raw.get('id') or '').strip()
        if not canonical_id or canonical_id == video_id:
            canonical_id = _canonical_from_ids(media_type, title, year=year, tmdb_id=tmdb_id, imdb_id=imdb_id, tvdb_id=tvdb_id)

        direct_path = str(raw.get('path') or raw.get('url') or raw.get('plugin_url') or '').strip()
        if direct_path:
            is_folder = bool(raw.get('is_folder')) if 'is_folder' in raw else direct_path.startswith('plugin://')
            path = direct_path
        else:
            path, is_folder = _content_click_path(media_type=media_type, canonical_id=canonical_id, title=title, tmdb_id=tmdb_id, imdb_id=imdb_id, tvdb_id=tvdb_id, season=season, episode=episode, video_id=video_id or canonical_id)

        poster = str(raw.get('poster') or raw.get('thumb') or raw.get('image') or raw.get('poster_url') or '').strip()
        fanart = str(raw.get('fanart') or raw.get('background') or raw.get('backdrop') or raw.get('fanart_url') or '').strip()
        landscape = str(raw.get('landscape') or raw.get('banner') or '').strip()
        clearlogo = str(raw.get('clearlogo') or raw.get('logo') or '').strip()
        plot = str(raw.get('plot') or raw.get('description') or raw.get('overview') or '').strip()
        info = {'title': title, 'plot': plot, 'mediatype': 'tvshow' if media_type in ('series', 'anime') else 'movie'}
        if str(year).isdigit():
            info['year'] = int(year)
        if season.isdigit():
            info['season'] = int(season)
            has_seriesish = True
        if episode.isdigit():
            info['episode'] = int(episode)
            info['mediatype'] = 'episode'
            has_seriesish = True
        if media_type in ('series', 'anime'):
            has_seriesish = True

        art = {'poster': poster or bg or fallback_art.get('poster') or '', 'thumb': poster or bg or fallback_art.get('thumb') or '', 'fanart': fanart or bg or fallback_art.get('fanart') or addon_fanart(), 'landscape': landscape or fanart or poster or bg or '', 'clearlogo': clearlogo or ''}
        ids = {'tmdb': tmdb_id or '', 'imdb': imdb_id or '', 'tvdb': tvdb_id or ''}
        ctx_menu = []
        if not direct_path:
            ctx_menu = _build_source_picker_menu(media_type=media_type, canonical_id=canonical_id, title=title, season=season, episode=episode, video_id=video_id or canonical_id) + _build_player_chooser_menu(media_type=media_type, canonical_id=canonical_id, title=title, tmdb_id=tmdb_id, imdb_id=imdb_id, tvdb_id=tvdb_id, season=season, episode=episode, video_id=video_id or canonical_id)
        add_item(title, path, is_folder=is_folder, info=info, art=art, ids=ids, context_menu=ctx_menu)
        added += 1

    if added == 0:
        error('الملف لا يحتوي على عناصر صالحة')
        return end_dir()
    return end_dir(content='tvshows' if has_seriesish else 'movies')


def _collection_skip_gate_enabled(entry):
    entry = entry or {}
    raw = entry.get('open_mode')
    # Imported Nuvio/Fusion catalogSources behave like skin widgets. Opening
    # them through Dex Hub's filter-gate adds an extra folder and makes the
    # collection feel slow, so default multiCatalog to direct open unless the
    # user explicitly changed it back to normal.
    if raw in (None, '') and str(entry.get('kind') or '').strip() == 'multiCatalog':
        return True
    return str(raw or 'normal').strip().lower() == 'skip'


def _collection_entry_preview(entry):
    payload = entry.get('payload') or {}
    kind = (entry.get('kind') or '').strip()
    label = entry.get('name') or 'Collection'
    background = entry.get('background') or ''
    preview = {'plot': '', 'poster': '', 'fanart': background or '', 'landscape': background or '', 'clearlogo': ''}
    open_mode_label = _collection_open_mode_label(entry.get('open_mode') or 'normal')
    if kind == 'addonCatalog':
        provider = _provider_for_addon_ref(payload.get('addonId') or '')
        catalog_id = (payload.get('catalogId') or '').strip()
        catalog_type = (payload.get('catalogType') or 'movie').strip()
        catalog_def = _catalog_definition(provider, catalog_id, catalog_type) if provider else {}
        art = catalog_art(label, catalog_type, (provider or {}).get('manifest') or {}, catalog_def or {})
        folder_art = root_art('catalogs')
        preview['poster'] = background or art.get('poster') or art.get('thumb') or folder_art.get('poster') or folder_art.get('thumb') or ''
        preview['fanart'] = background or art.get('fanart') or folder_art.get('fanart') or addon_fanart()
        preview['landscape'] = background or art.get('landscape') or art.get('fanart') or folder_art.get('landscape') or preview['poster'] or ''
        preview['clearlogo'] = art.get('clearlogo') or ''
        plot_lines = []
        if catalog_def.get('description'):
            plot_lines.append(str(catalog_def.get('description')))
        plot_lines.extend(['كتالوج: %s' % catalog_id, 'النوع: %s' % catalog_type, 'الفتح: %s' % open_mode_label])
        if provider:
            plot_lines.append('من: %s' % (provider.get('name') or provider.get('id') or payload.get('addonId') or ''))
        elif payload.get('addonId'):
            plot_lines.append('من: %s' % payload.get('addonId'))
        preview['plot'] = '\n'.join([x for x in plot_lines if x])
        return preview
    if kind == 'traktList':
        trakt_art = root_art('trakt')
        folder_art = root_art('catalogs')
        username = (payload.get('username') or '').strip()
        slug = (payload.get('listSlug') or payload.get('slug') or '').strip()
        preview['poster'] = background or trakt_art.get('poster') or trakt_art.get('thumb') or folder_art.get('poster') or folder_art.get('thumb') or ''
        preview['fanart'] = background or trakt_art.get('fanart') or folder_art.get('fanart') or addon_fanart()
        preview['landscape'] = background or trakt_art.get('landscape') or trakt_art.get('fanart') or folder_art.get('landscape') or preview['poster'] or ''
        preview['clearlogo'] = trakt_art.get('clearlogo') or ''
        plot_lines = ['قائمة Trakt: %s' % (payload.get('listName') or slug or label), 'النوع: %s' % _collection_media_filter_label(payload.get('mediaFilter') or 'auto')]
        if username:
            plot_lines.append('المستخدم: %s' % username)
        if slug:
            plot_lines.append('المعرّف: %s' % slug)
        preview['plot'] = '\n'.join([x for x in plot_lines if x])
        return preview
    if kind == 'mdblistList':
        folder_art = root_art('catalogs')
        username = (payload.get('username') or '').strip()
        slug = (payload.get('listSlug') or payload.get('slug') or '').strip()
        preview['poster'] = background or folder_art.get('poster') or folder_art.get('thumb') or ''
        preview['fanart'] = background or folder_art.get('fanart') or addon_fanart()
        preview['landscape'] = background or folder_art.get('landscape') or preview['poster'] or ''
        plot_lines = ['قائمة MDBList: %s' % (payload.get('listName') or slug or label), 'النوع: %s' % _collection_media_filter_label(payload.get('mediaFilter') or 'auto')]
        if username:
            plot_lines.append('المستخدم: %s' % username)
        if slug:
            plot_lines.append('المعرّف: %s' % slug)
        preview['plot'] = '\n'.join([x for x in plot_lines if x])
        return preview
    if kind == 'multiCatalog':
        folder_art = root_art('catalogs')
        sources = payload.get('sources') or []
        preview['poster'] = background or folder_art.get('poster') or folder_art.get('thumb') or ''
        preview['fanart'] = background or folder_art.get('fanart') or addon_fanart()
        preview['landscape'] = background or folder_art.get('landscape') or preview['poster'] or ''
        names = []
        for src in sources[:6]:
            if not isinstance(src, dict):
                continue
            aid = str(src.get('addonId') or '').strip()
            cid = str(src.get('catalogId') or '').strip()
            ctype = str(src.get('catalogType') or src.get('type') or '').strip()
            names.append('%s/%s %s' % (aid, cid, ctype))
        plot_lines = ['مصادر متعددة: %d' % len(sources), 'الفتح: %s' % open_mode_label]
        if names:
            plot_lines.append('\n'.join(names))
        preview['plot'] = '\n'.join([x for x in plot_lines if x])
        return preview
    if kind == 'kodiPluginRoute':
        addon_id = str(payload.get('addonId') or '').strip()
        addon_name = str(payload.get('addonName') or addon_id or 'Kodi')
        preview['poster'] = background or payload.get('thumbnail') or root_art('catalogs').get('poster') or ''
        preview['fanart'] = background or payload.get('fanart') or addon_fanart()
        preview['landscape'] = background or payload.get('fanart') or preview['poster'] or ''
        route_url = str(payload.get('route') or payload.get('url') or '').strip()
        preview['plot'] = '\n'.join([x for x in ['إضافة Kodi: %s' % addon_name, 'المسار: %s' % route_url, 'الفتح: %s' % open_mode_label] if x])
        return preview
    if kind == 'localJsonCatalog':
        path = str(payload.get('filePath') or payload.get('path') or '').strip()
        media_filter = _collection_media_filter_label(payload.get('mediaFilter') or 'auto')
        preview['poster'] = background or root_art('catalogs').get('poster') or ''
        preview['fanart'] = background or addon_fanart()
        preview['landscape'] = background or preview['poster'] or ''
        preview['plot'] = '\n'.join([x for x in ['ملف محلي: %s' % os.path.basename(path or ''), 'النوع: %s' % media_filter, 'المسار: %s' % path] if x])
        return preview
    preview['plot'] = 'نوع غير معروف: %s' % kind
    return preview

def _collection_content_type(entries):
    """Pick Kodi content type to match the layout the user wanted."""
    # If any entry has layout "Wide" or "Banner", use 'tvshows' which renders
    # landscape art nicely in most skins. Otherwise default to 'movies' which
    # renders poster art.
    for e in entries:
        lt = (e.get('layout') or '').lower()
        if lt in ('wide', 'banner', 'landscape'):
            return 'tvshows'
    return 'movies'




def collection_entry_meta_source(set_id, entry_id):
    row = _collections_mod.get_set(set_id)
    if not row:
        error('المجموعة غير موجودة')
        return
    entry = None
    for e in row.get('entries') or []:
        if e.get('id') == entry_id:
            entry = e
            break
    if not entry:
        error('العنصر غير موجود')
        return
    kind = (entry.get('kind') or '').strip()
    payload = entry.get('payload') or {}
    if kind in ('traktList', 'mdblistList'):
        return _meta_pick_target('virtual.collection.trakt', 'الكوليكشن • عناصر Trakt')
    providers = []
    if kind == 'addonCatalog':
        provider = _provider_for_addon_ref(payload.get('addonId') or '')
        if provider:
            providers = [provider]
    elif kind == 'multiCatalog':
        seen = set()
        for src in payload.get('sources') or []:
            provider = _provider_for_addon_ref((src or {}).get('addonId') or '')
            if provider and provider.get('id') not in seen:
                seen.add(provider.get('id'))
                providers.append(provider)
    if not providers:
        error('هذا العنصر لا يملك إضافة مرتبطة لتغيير الميتاداتا')
        return
    if len(providers) == 1:
        return meta_pick_for_provider(providers[0].get('id') or '')
    labels = [p.get('name') or p.get('id') or 'Provider' for p in providers]
    choice = xbmcgui.Dialog().select(tr('اختر الإضافة'), [tr(x) for x in labels])
    if choice < 0:
        return
    return meta_pick_for_provider(providers[choice].get('id') or '')


def collection_set_browse(set_id):
    """List the entries inside one collection set as folders.

    Respects each entry's layout field (Poster | Wide) and enriches collection
    cards with Trakt/addon metadata when available.
    """
    row = _collections_mod.get_set(set_id)
    if not row:
        error('المجموعة غير موجودة')
        return end_dir()
    entries = row.get('entries') or []
    win = xbmcgui.Window(WINDOW_ID)
    first_fanart = ''

    if not entries:
        add_item(
            '[COLOR yellow]+ إضافة عنصر يدويًا[/COLOR]',
            build_url(action='collection_entry_add', set_id=set_id),
            is_folder=False,
            info={'title': 'إضافة عنصر', 'plot': 'أضف اختصارًا (كتالوج أو قائمة Trakt) يدويًا'},
            art=root_art('add'),
        )
        add_item('[COLOR grey]لا توجد عناصر بعد داخل هذه المجموعة[/COLOR]', build_url(action='collection_set_browse', set_id=set_id), is_folder=False, info={'title': 'فارغ'})
        return end_dir(content='movies')

    # Hide entries that have no real poster/background — otherwise Kodi
    # shows empty tiles that can't be rescued (we have no fallback IDs
    # because these are virtual shortcuts, not real meta items).
    hide_empty = True
    try:
        hide_empty = (ADDON.getSetting('hide_empty_collection_entries') or 'true').lower() not in ('false', '0', 'no')
    except Exception:
        pass

    for entry in entries:
        label = entry.get('name') or 'Collection'
        kind = (entry.get('kind') or '').strip()
        layout = (entry.get('layout') or 'Poster').strip()
        is_wide = layout.lower() in ('wide', 'banner', 'landscape')
        hide_title = bool(entry.get('hide_title'))
        preview = _collection_entry_preview(entry)
        bg = entry.get('background') or preview.get('fanart') or preview.get('landscape') or ''
        poster = entry.get('background') or preview.get('poster') or bg or root_art('catalogs').get('poster') or ''

        # Skip visually-empty tiles when the setting is on.
        if hide_empty and not (entry.get('background') or preview.get('poster') or preview.get('fanart') or preview.get('landscape')):
            xbmc.log('[DexHub] skipping empty collection entry: %s' % label, xbmc.LOGDEBUG)
            continue

        if bg and not first_fanart:
            first_fanart = bg

        kind_tag = {'addonCatalog': 'كتالوج', 'multiCatalog': 'مصادر', 'traktList': 'Trakt', 'mdblistList': 'MDBList', 'kodiPluginRoute': 'Kodi', 'localJsonCatalog': 'JSON'}.get(kind, kind or 'أخرى')
        if hide_title:
            display_label = '[COLOR grey][%s][/COLOR]' % kind_tag
        else:
            display_label = '[COLOR grey][%s][/COLOR] %s' % (kind_tag, label)

        if is_wide:
            art = {
                'thumb': bg or poster or '',
                'poster': poster or bg or '',
                'landscape': bg or preview.get('landscape') or poster or '',
                'banner': bg or preview.get('landscape') or poster or '',
                'fanart': bg or addon_fanart(),
                'clearlogo': preview.get('clearlogo') or '',
            }
        else:
            art = {
                'thumb': poster or bg or '',
                'poster': poster or bg or '',
                'fanart': bg or addon_fanart(),
                'landscape': bg or preview.get('landscape') or poster or '',
                'clearlogo': preview.get('clearlogo') or '',
            }
        if art.get('clearlogo'):
            art['logo'] = art.get('clearlogo')
            art['tvshow.clearlogo'] = art.get('clearlogo')

        path = build_url(action='collection_entry_open', set_id=set_id, entry_id=entry.get('id') or '')
        ctx_menu = [
            ('تغيير الصورة', 'RunPlugin(%s)' % build_url(action='collection_entry_edit_bg', set_id=set_id, entry_id=entry.get('id') or '')),
            ('تغيير الاسم', 'RunPlugin(%s)' % build_url(action='collection_entry_edit_name', set_id=set_id, entry_id=entry.get('id') or '')),
            ('تبديل التخطيط (Poster / Wide)', 'RunPlugin(%s)' % build_url(action='collection_entry_toggle_layout', set_id=set_id, entry_id=entry.get('id') or '')),
            ('وضع الفتح: %s' % _collection_open_mode_label(entry.get('open_mode') or 'normal'), 'RunPlugin(%s)' % build_url(action='collection_entry_toggle_open_mode', set_id=set_id, entry_id=entry.get('id') or '')),
            ('تعديل الرابط/المصدر', 'RunPlugin(%s)' % build_url(action='collection_entry_edit_source', set_id=set_id, entry_id=entry.get('id') or '')),
            ('إزالة العنصر', 'RunPlugin(%s)' % build_url(action='collection_entry_remove', set_id=set_id, entry_id=entry.get('id') or '')),
        ]
        if kind in ('addonCatalog', 'multiCatalog', 'traktList', 'mdblistList'):
            ctx_menu.insert(2, ('تغيير مصدر الميتاداتا', 'RunPlugin(%s)' % build_url(action='collection_entry_meta_source', set_id=set_id, entry_id=entry.get('id') or '')))
        info = {
            'title': label,
            'plot': preview.get('plot') or '',
            'mediatype': 'tvshow' if is_wide else 'movie',
        }
        add_item(display_label, path, info=info, art=art, context_menu=ctx_menu)

    if first_fanart:
        win.setProperty('fanart', first_fanart)
    end_dir(content=_collection_content_type(entries))


# ─── collection entry edit handlers ──────────────────────────────────────

def collection_entry_edit_bg(set_id, entry_id):
    row = _collections_mod.get_set(set_id)
    if not row:
        return
    entry = next((e for e in (row.get('entries') or []) if e.get('id') == entry_id), None)
    if not entry:
        return
    kb = xbmc.Keyboard(entry.get('background') or '', tr('رابط الصورة (poster/banner/fanart)'))
    kb.doModal()
    if not kb.isConfirmed():
        return
    new_url = kb.getText().strip()
    try:
        _collections_mod.update_entry(set_id, entry_id, {'background': new_url})
        notify('تم تحديث الصورة')
    except Exception as exc:
        error('فشل التحديث: %s' % exc)
    xbmc.executebuiltin('Container.Refresh')


def collection_entry_edit_name(set_id, entry_id):
    row = _collections_mod.get_set(set_id)
    if not row:
        return
    entry = next((e for e in (row.get('entries') or []) if e.get('id') == entry_id), None)
    if not entry:
        return
    kb = xbmc.Keyboard(entry.get('name') or '', tr('اسم العنصر'))
    kb.doModal()
    if not kb.isConfirmed():
        return
    new_name = kb.getText().strip()
    if not new_name:
        return
    try:
        _collections_mod.update_entry(set_id, entry_id, {'name': new_name})
        notify('تم تحديث الاسم')
    except Exception as exc:
        error('فشل التحديث: %s' % exc)
    xbmc.executebuiltin('Container.Refresh')


def collection_entry_toggle_layout(set_id, entry_id):
    row = _collections_mod.get_set(set_id)
    if not row:
        return
    entry = next((e for e in (row.get('entries') or []) if e.get('id') == entry_id), None)
    if not entry:
        return
    current = (entry.get('layout') or 'Poster').strip().lower()
    new_layout = 'Wide' if current == 'poster' else 'Poster'
    try:
        _collections_mod.update_entry(set_id, entry_id, {'layout': new_layout})
        notify('التخطيط الآن: %s' % new_layout)
    except Exception as exc:
        error('فشل: %s' % exc)
    xbmc.executebuiltin('Container.Refresh')


def collection_entry_toggle_open_mode(set_id, entry_id):
    row = _collections_mod.get_set(set_id)
    if not row:
        return
    entry = next((e for e in (row.get('entries') or []) if e.get('id') == entry_id), None)
    if not entry:
        return
    selected = _pick_collection_open_mode(entry.get('open_mode') or 'normal')
    if not selected:
        return
    try:
        _collections_mod.update_entry(set_id, entry_id, {'open_mode': selected})
        notify('تم تحديث وضع الفتح')
    except Exception as exc:
        error('فشل التحديث: %s' % exc)
    xbmc.executebuiltin('Container.Refresh')




def _collection_source_label(src, idx=0):
    """Compact user-facing label for one multiCatalog source."""
    src = src or {}
    addon_id = str(src.get('addonId') or src.get('addon_id') or '').strip()
    catalog_id = str(src.get('catalogId') or src.get('catalog_id') or '').strip()
    catalog_type = str(src.get('catalogType') or src.get('type') or 'movie').strip()
    genre = str(src.get('genre') or '').strip()
    extra = src.get('extra') if isinstance(src.get('extra'), dict) else {}
    base = '[%s] %s' % (catalog_type or 'movie', catalog_id or 'catalog')
    if genre:
        base += ' / genre=%s' % genre
    if extra:
        try:
            base += ' / ' + ', '.join('%s=%s' % (k, v) for k, v in list(extra.items())[:2])
        except Exception:
            pass
    if addon_id:
        provider = _provider_for_addon_ref(addon_id)
        base += ' — %s' % ((provider or {}).get('name') or addon_id)
    return '%02d. %s' % (idx + 1, base)


def _select_dialog(title, labels, preselect=0):
    try:
        return xbmcgui.Dialog().select(tr(title), [tr(x) for x in labels], preselect=preselect)
    except TypeError:
        return xbmcgui.Dialog().select(tr(title), [tr(x) for x in labels])


def _catalog_source_extra_options(catalog_def):
    """Return catalog extras that can behave like folders/categories."""
    out = []
    try:
        for extra in (catalog_def.get('extra') or []):
            if not isinstance(extra, dict):
                continue
            name = str(extra.get('name') or '').strip()
            if not name or name in ('skip', 'search', 'limit'):
                continue
            opts = [str(o) for o in (extra.get('options') or []) if o not in (None, '')]
            if not opts:
                continue
            # Keep the chooser useful and close to Stremio folder/category UX.
            if _extra_mode(name, catalog_def) == 'folder' or name.lower() in ('genre', 'category', 'year', 'language', 'country', 'network', 'studio', 'collection', 'type'):
                out.append((name, opts))
    except Exception:
        pass
    return out


def _pick_catalog_source_extra(catalog_def, current=None):
    """Optional Stremio extra/category picker for one selected catalog.

    Returns ({name: value}, genre_value) or None when the user cancels.
    Empty dict means no preset filter.
    """
    current = current or {}
    extra_defs = _catalog_source_extra_options(catalog_def or {})
    if not extra_defs:
        return {}, ''
    labels = ['بدون فلتر / افتح الكتالوج كامل'] + ['%s (%d)' % (_filter_label(name), len(opts)) for name, opts in extra_defs]
    idx = _select_dialog('اختيار مجلد/فلتر من الكتالوج', labels, preselect=0)
    if idx < 0:
        return None
    if idx == 0:
        return {}, ''
    name, opts = extra_defs[idx - 1]
    current_value = ''
    if isinstance(current.get('extra'), dict):
        current_value = str(current.get('extra', {}).get(name) or '')
    if not current_value and name == 'genre':
        current_value = str(current.get('genre') or '')
    pre = opts.index(current_value) if current_value in opts else 0
    opt_idx = _select_dialog('اختر %s' % _filter_label(name), opts, preselect=pre)
    if opt_idx < 0:
        return None
    value = opts[opt_idx]
    if name == 'genre':
        return {'genre': value}, value
    return {name: value}, ''


def _collection_provider_catalog_rows():
    rows = []
    for provider in store.list_providers() or []:
        manifest = provider.get('manifest') or {}
        for catalog in manifest.get('catalogs') or []:
            if not isinstance(catalog, dict):
                continue
            cid = str(catalog.get('id') or '').strip()
            ctype = str(catalog.get('type') or '').strip() or 'movie'
            if not cid:
                continue
            pname = provider.get('name') or manifest.get('name') or provider.get('id') or 'Stremio'
            cname = catalog.get('name') or cid
            label = '%s  •  [%s] %s' % (pname, ctype, cname)
            if cid != cname:
                label += '  (%s)' % cid
            rows.append({'provider': provider, 'catalog': catalog, 'label': label})
    rows.sort(key=lambda r: (str((r.get('provider') or {}).get('name') or '').lower(), str((r.get('catalog') or {}).get('name') or '').lower()))
    return rows


def _pick_stremio_catalog_source(src=None):
    """Pick a Stremio catalog from the registered manifests, like Stremio UI."""
    src = src or {}
    rows = _collection_provider_catalog_rows()
    if not rows:
        error('لا توجد إضافات Stremio مسجلة. أضف manifest أولًا من المصادر.')
        return None
    default_idx = 0
    current_addon = str(src.get('addonId') or src.get('addon_id') or '').strip()
    current_catalog = str(src.get('catalogId') or src.get('catalog_id') or '').strip()
    current_type = str(src.get('catalogType') or src.get('type') or '').strip()
    for i, row in enumerate(rows):
        provider = row.get('provider') or {}
        catalog = row.get('catalog') or {}
        refs = [str(provider.get('manifest_url') or '').strip(), str(provider.get('id') or '').strip(), str((provider.get('manifest') or {}).get('id') or '').strip()]
        if current_addon and current_addon in refs and current_catalog == str(catalog.get('id') or '') and (not current_type or current_type == str(catalog.get('type') or '')):
            default_idx = i
            break
    labels = [r.get('label') or 'Catalog' for r in rows]
    idx = _select_dialog('اختر كتالوج Stremio', labels, preselect=default_idx)
    if idx < 0:
        return None
    row = rows[idx]
    provider = row.get('provider') or {}
    catalog = row.get('catalog') or {}
    extra_pick = _pick_catalog_source_extra(catalog, current=src)
    if extra_pick is None:
        return None
    extra_dict, genre_value = extra_pick
    out = {
        # Use manifest_url so configured/private manifests keep their token exactly like Stremio.
        'addonId': str(provider.get('manifest_url') or (provider.get('manifest') or {}).get('id') or provider.get('id') or '').strip(),
        'catalogId': str(catalog.get('id') or '').strip(),
        'catalogType': str(catalog.get('type') or 'movie').strip() or 'movie',
        'genre': genre_value or '',
    }
    if extra_dict:
        out['extra'] = dict(extra_dict)
    return out


def _manual_collection_catalog_source(src=None):
    src = src or {}
    addon_id = _prompt_text(str(src.get('addonId') or src.get('addon_id') or ''), 'رابط manifest أو Addon ID')
    if addon_id is None:
        return None
    addon_id = str(addon_id or '').strip()
    if not addon_id:
        error('Addon ID / manifest فارغ')
        return None

    catalog_id = _prompt_text(str(src.get('catalogId') or src.get('catalog_id') or ''), 'Catalog ID')
    if catalog_id is None:
        return None
    catalog_id = str(catalog_id or '').strip()
    if not catalog_id:
        error('Catalog ID فارغ')
        return None

    current_type = str(src.get('catalogType') or src.get('type') or 'movie').strip().lower() or 'movie'
    choices = ['movie', 'series', 'anime']
    default_idx = choices.index(current_type) if current_type in choices else 0
    idx = _select_dialog('نوع الكتالوج', choices, preselect=default_idx)
    if idx < 0:
        return None
    catalog_type = choices[idx]

    genre = _prompt_text(str(src.get('genre') or ''), 'Genre / Extra اختياري')
    if genre is None:
        return None

    out = {
        'addonId': addon_id,
        'catalogId': catalog_id,
        'catalogType': catalog_type,
        'genre': str(genre or '').strip(),
    }
    extra = src.get('extra')
    if isinstance(extra, dict) and extra:
        out['extra'] = extra
    return out


def _collection_prompt_catalog_source(src=None):
    """Pick or type a Stremio catalog source for collection folders."""
    src = src or {}
    modes = ['اختيار من إضافات Stremio المسجلة', 'إدخال يدوي متقدم']
    default_idx = 0 if store.list_providers() else 1
    mode = _select_dialog('طريقة اختيار المصدر', modes, preselect=default_idx)
    if mode < 0:
        return None
    if mode == 0:
        return _pick_stremio_catalog_source(src)
    return _manual_collection_catalog_source(src)


def _collection_edit_multi_sources(payload):
    """Edit/add/remove a source inside a multiCatalog payload.

    Returns a new sources list, or None when the user cancels.
    """
    sources = []
    for src in (payload.get('sources') or []):
        if isinstance(src, dict):
            sources.append(dict(src))
    labels = [_collection_source_label(src, i) for i, src in enumerate(sources)]
    labels.append('+ إضافة مصدر جديد')
    choice = xbmcgui.Dialog().select(tr('مصادر الفولدر'), labels)
    if choice < 0:
        return None

    if choice >= len(sources):
        new_src = _collection_prompt_catalog_source({})
        if not new_src:
            return None
        sources.append(new_src)
        return sources

    action = xbmcgui.Dialog().select(tr('تعديل المصدر'), [tr('تعديل هذا المصدر'), tr('حذف هذا المصدر'), tr('إضافة مصدر جديد')])
    if action < 0:
        return None
    if action == 1:
        if not xbmcgui.Dialog().yesno('Dex Hub', tr('حذف هذا المصدر؟')):
            return None
        del sources[choice]
        return sources
    if action == 2:
        new_src = _collection_prompt_catalog_source({})
        if not new_src:
            return None
        sources.append(new_src)
        return sources

    edited = _collection_prompt_catalog_source(sources[choice])
    if not edited:
        return None
    sources[choice] = edited
    return sources

def collection_entry_edit_source(set_id, entry_id):
    row = _collections_mod.get_set(set_id)
    if not row:
        return
    entry = next((e for e in (row.get('entries') or []) if e.get('id') == entry_id), None)
    if not entry:
        return
    kind = (entry.get('kind') or '').strip()
    payload = entry.get('payload') or {}
    updates = {}
    if kind == 'addonCatalog':
        edit_modes = ['اختيار كتالوج من إضافات Stremio', 'تصفح إضافة Kodi', 'إدخال يدوي متقدم']
        mode = _select_dialog('تعديل الرابط/المصدر', edit_modes, preselect=0)
        if mode < 0:
            return
        if mode == 0:
            src = _pick_stremio_catalog_source(payload)
            if not src:
                return
            media_filter = _pick_collection_media_filter(src.get('catalogType') or payload.get('mediaFilter') or 'auto')
            if media_filter is None:
                return
            updates.update({'kind': 'addonCatalog', 'payload.addonId': src.get('addonId') or '', 'payload.catalogId': src.get('catalogId') or '', 'payload.catalogType': src.get('catalogType') or 'movie', 'payload.genre': src.get('genre') or '', 'payload.extra': src.get('extra') or {}, 'payload.mediaFilter': media_filter})
            try:
                _collections_mod.ensure_addon_registered(src.get('addonId') or '')
            except Exception as exc:
                xbmc.log('[DexHub] auto-register failed after source edit: %s' % exc, xbmc.LOGWARNING)
        elif mode == 1:
            addon_row = _pick_installed_video_addon()
            if not addon_row:
                return
            route_url, route_label = _pick_kodi_plugin_route(addon_row)
            if not route_url:
                return
            media_filter = _pick_collection_media_filter(payload.get('mediaFilter') or 'auto')
            if media_filter is None:
                return
            updates.update({'kind': 'kodiPluginRoute', 'payload.addonId': addon_row.get('id') or '', 'payload.addonName': addon_row.get('name') or addon_row.get('id') or '', 'payload.route': route_url, 'payload.mediaFilter': media_filter, 'payload.thumbnail': addon_row.get('thumbnail') or '', 'payload.fanart': addon_row.get('fanart') or ''})
            if route_label:
                updates['name'] = route_label
        else:
            src = _manual_collection_catalog_source(payload)
            if not src:
                return
            media_filter = _pick_collection_media_filter(payload.get('mediaFilter') or src.get('catalogType') or 'auto')
            if media_filter is None:
                return
            updates.update({'kind': 'addonCatalog', 'payload.addonId': src.get('addonId') or '', 'payload.catalogId': src.get('catalogId') or '', 'payload.catalogType': src.get('catalogType') or 'movie', 'payload.genre': src.get('genre') or '', 'payload.extra': src.get('extra') or {}, 'payload.mediaFilter': media_filter})
            try:
                _collections_mod.ensure_addon_registered(src.get('addonId') or '')
            except Exception as exc:
                xbmc.log('[DexHub] auto-register failed after source edit: %s' % exc, xbmc.LOGWARNING)
    elif kind == 'multiCatalog':
        edit_modes = ['إدارة مصادر Stremio داخل الفولدر', 'تحويل هذا العنصر إلى مسار Kodi']
        mode = _select_dialog('تعديل الرابط/المصدر', edit_modes, preselect=0)
        if mode < 0:
            return
        if mode == 1:
            addon_row = _pick_installed_video_addon()
            if not addon_row:
                return
            route_url, route_label = _pick_kodi_plugin_route(addon_row)
            if not route_url:
                return
            media_filter = _pick_collection_media_filter(payload.get('mediaFilter') or 'auto')
            if media_filter is None:
                return
            updates.update({'kind': 'kodiPluginRoute', 'payload.addonId': addon_row.get('id') or '', 'payload.addonName': addon_row.get('name') or addon_row.get('id') or '', 'payload.route': route_url, 'payload.mediaFilter': media_filter, 'payload.thumbnail': addon_row.get('thumbnail') or '', 'payload.fanart': addon_row.get('fanart') or ''})
            if route_label:
                updates['name'] = route_label
        else:
            new_sources = _collection_edit_multi_sources(payload)
            if new_sources is None:
                return
            if not new_sources:
                error('لا يمكن ترك الفولدر بدون مصادر')
                return
            updates['kind'] = 'multiCatalog'
            updates['payload.sources'] = new_sources
            for src in new_sources:
                addon_ref = str((src or {}).get('addonId') or '').strip()
                if addon_ref.startswith(('http://', 'https://')):
                    try:
                        _collections_mod.ensure_addon_registered(addon_ref)
                    except Exception as exc:
                        xbmc.log('[DexHub] auto-register failed after multi source edit: %s' % exc, xbmc.LOGWARNING)
    elif kind == 'traktList':
        default_url = payload.get('url') or ('https://trakt.tv/users/%s/lists/%s' % (payload.get('username') or '', payload.get('listSlug') or payload.get('slug') or ''))
        raw_url = _prompt_text(str(default_url or ''), 'رابط قائمة Trakt')
        if raw_url is None:
            return
        parsed = _parse_trakt_list_url(raw_url)
        if not parsed:
            error('رابط Trakt غير صالح')
            return
        media_filter = _pick_collection_media_filter(payload.get('mediaFilter') or 'auto')
        if media_filter is None:
            return
        updates.update({'payload.username': parsed['username'], 'payload.listSlug': parsed['slug'], 'payload.slug': parsed['slug'], 'payload.listName': payload.get('listName') or parsed.get('name') or '', 'payload.url': parsed['url'], 'payload.mediaFilter': media_filter})
    elif kind == 'mdblistList':
        default_url = payload.get('url') or ('https://mdblist.com/lists/%s/%s' % (payload.get('username') or '', payload.get('listSlug') or payload.get('slug') or ''))
        raw_url = _prompt_text(str(default_url or ''), 'رابط قائمة MDBList')
        if raw_url is None:
            return
        parsed = _parse_mdblist_list_url(raw_url)
        if not parsed:
            error('رابط MDBList غير صالح')
            return
        media_filter = _pick_collection_media_filter(payload.get('mediaFilter') or 'auto')
        if media_filter is None:
            return
        updates.update({'payload.username': parsed['username'], 'payload.listSlug': parsed['slug'], 'payload.slug': parsed['slug'], 'payload.listName': payload.get('listName') or parsed.get('name') or '', 'payload.url': parsed['url'], 'payload.mediaFilter': media_filter})
    elif kind == 'kodiPluginRoute':
        addon_row = _pick_installed_video_addon()
        if not addon_row:
            return
        route_url, _route_label = _pick_kodi_plugin_route(addon_row, default_route=str(payload.get('route') or 'plugin://%s/' % addon_row.get('id')))
        if not route_url:
            return
        media_filter = _pick_collection_media_filter(payload.get('mediaFilter') or 'auto')
        if media_filter is None:
            return
        updates.update({'payload.addonId': addon_row.get('id') or '', 'payload.addonName': addon_row.get('name') or addon_row.get('id') or '', 'payload.route': route_url, 'payload.mediaFilter': media_filter, 'payload.thumbnail': addon_row.get('thumbnail') or '', 'payload.fanart': addon_row.get('fanart') or ''})
    elif kind == 'localJsonCatalog':
        file_path = _prompt_local_json_file()
        if file_path is None or not str(file_path).strip():
            return
        try:
            raw_text = _read_text_from_path(file_path)
            _rows, _meta = _parse_local_json_catalog(raw_text)
        except Exception as exc:
            error('فشل قراءة ملف JSON: %s' % exc)
            return
        media_filter = _pick_collection_media_filter(payload.get('mediaFilter') or 'auto')
        if media_filter is None:
            return
        limit_text = _prompt_text(str(payload.get('limit') or '60'), 'عدد العناصر (0 = بدون حد)')
        if limit_text is None:
            return
        try:
            limit = max(0, int(limit_text or '0'))
        except Exception:
            limit = int(payload.get('limit') or 60)
        updates.update({'payload.filePath': str(file_path).strip(), 'payload.mediaFilter': media_filter, 'payload.limit': limit})
    else:
        error('نوع غير مدعوم للتعديل')
        return
    try:
        _collections_mod.update_entry(set_id, entry_id, updates)
        notify('تم تحديث المصدر')
    except Exception as exc:
        error('فشل التحديث: %s' % exc)
    xbmc.executebuiltin('Container.Refresh')

def collection_entry_remove(set_id, entry_id):
    if not xbmcgui.Dialog().yesno('Dex Hub', tr('هل تريد إزالة هذا العنصر؟')):
        return
    try:
        _collections_mod.remove_entry(set_id, entry_id)
        notify('تم الإزالة')
    except Exception as exc:
        error('فشل: %s' % exc)
    xbmc.executebuiltin('Container.Refresh')


def collection_entry_add(set_id):
    choices = [tr('رابط Trakt'), tr('رابط MDBList'), tr('كتالوج إضافة Stremio'), tr('مسار إضافة Kodi'), tr('ملف JSON محلي')]
    source_idx = xbmcgui.Dialog().select(tr('مصدر العنصر'), choices)
    if source_idx < 0:
        return

    payload = {}
    kind = ''
    default_name = ''

    if source_idx == 0:
        raw_url = _prompt_text('', 'رابط قائمة Trakt')
        if raw_url is None:
            return
        parsed = _parse_trakt_list_url(raw_url)
        if not parsed:
            error('رابط Trakt غير صالح')
            return
        default_name = parsed.get('name') or ''
        media_filter = _pick_collection_media_filter('auto')
        if media_filter is None:
            return
        payload = {'username': parsed['username'], 'listSlug': parsed['slug'], 'slug': parsed['slug'], 'listName': default_name, 'url': parsed['url'], 'mediaFilter': media_filter}
        kind = 'traktList'
    elif source_idx == 1:
        raw_url = _prompt_text('', 'رابط قائمة MDBList')
        if raw_url is None:
            return
        parsed = _parse_mdblist_list_url(raw_url)
        if not parsed:
            error('رابط MDBList غير صالح')
            return
        default_name = parsed.get('name') or ''
        media_filter = _pick_collection_media_filter('auto')
        if media_filter is None:
            return
        payload = {'username': parsed['username'], 'listSlug': parsed['slug'], 'slug': parsed['slug'], 'listName': default_name, 'url': parsed['url'], 'mediaFilter': media_filter}
        kind = 'mdblistList'
    elif source_idx == 2:
        src = _collection_prompt_catalog_source({})
        if not src:
            return
        media_filter = _pick_collection_media_filter(src.get('catalogType') or 'movie')
        if media_filter is None:
            return
        payload = {'addonId': src.get('addonId') or '', 'catalogId': src.get('catalogId') or '', 'catalogType': src.get('catalogType') or 'movie', 'genre': src.get('genre') or '', 'extra': src.get('extra') or {}, 'mediaFilter': media_filter}
        default_name = _derive_name_from_slug(src.get('catalogId') or '')
        try:
            _collections_mod.ensure_addon_registered(payload.get('addonId', ''))
        except Exception as exc:
            notify('لم يتم تسجيل المصدر تلقائيًا: %s' % exc)
        kind = 'addonCatalog'
    elif source_idx == 3:
        addon_row = _pick_installed_video_addon()
        if not addon_row:
            return
        route_url, route_label = _pick_kodi_plugin_route(addon_row)
        if not route_url:
            return
        media_filter = _pick_collection_media_filter('auto')
        if media_filter is None:
            return
        payload = {'addonId': addon_row.get('id') or '', 'addonName': addon_row.get('name') or addon_row.get('id') or '', 'route': route_url, 'mediaFilter': media_filter, 'thumbnail': addon_row.get('thumbnail') or '', 'fanart': addon_row.get('fanart') or ''}
        default_name = route_label or addon_row.get('name') or addon_row.get('id') or 'Kodi'
        kind = 'kodiPluginRoute'
    else:
        file_path = _prompt_local_json_file()
        if file_path is None or not str(file_path).strip():
            return
        media_filter = _pick_collection_media_filter('auto')
        if media_filter is None:
            return
        try:
            raw_text = _read_text_from_path(file_path)
            _rows, meta = _parse_local_json_catalog(raw_text)
        except Exception as exc:
            error('فشل قراءة ملف JSON: %s' % exc)
            return
        limit_text = _prompt_text('60', 'عدد العناصر (0 = بدون حد)')
        if limit_text is None:
            return
        try:
            limit = max(0, int(limit_text or '0'))
        except Exception:
            limit = 60
        payload = {'filePath': str(file_path).strip(), 'mediaFilter': media_filter, 'limit': limit}
        default_name = str((meta or {}).get('title') or os.path.splitext(os.path.basename(str(file_path)))[0] or 'Local JSON').strip()
        kind = 'localJsonCatalog'

    background = _prompt_text('', 'رابط الصورة (اختياري)')
    if background is None:
        return

    open_mode = _pick_collection_open_mode('normal')
    if open_mode is None:
        return

    name = _prompt_text(default_name, 'اسم العنصر')
    if name is None:
        return
    name = name or default_name or 'Collection'

    try:
        _collections_mod.add_custom_entry(set_id, name, kind, payload, background=background, open_mode=open_mode)
        notify('تم إضافة العنصر')
    except Exception as exc:
        error('فشل: %s' % exc)
    xbmc.executebuiltin('Container.Refresh')

def collection_set_refresh(set_id):
    try:
        _collections_mod.refresh_set(set_id, manifest_resolver=_make_addon_manifest_resolver(''))
        notify('تم تحديث المجموعة')
    except Exception as exc:
        error('تعذّر التحديث: %s' % exc)
    xbmc.executebuiltin('Container.Refresh')


def collection_set_remove(set_id):
    try:
        _collections_mod.remove_set(set_id)
        notify('تم إزالة المجموعة')
    except Exception as exc:
        error('تعذّر الإزالة: %s' % exc)
    xbmc.executebuiltin('Container.Refresh')


def collection_set_create_empty():
    kb = xbmc.Keyboard(tr('مجموعتي'), tr('اسم المجموعة الجديدة'))
    kb.doModal()
    if not kb.isConfirmed():
        return
    name = kb.getText().strip()
    if not name:
        return
    try:
        new_set = _collections_mod.create_empty_set(name)
        notify('تم إنشاء: %s' % new_set.get('name'))
    except Exception as exc:
        error('فشل: %s' % exc)
    xbmc.executebuiltin('Container.Refresh')


def collection_entry_open(set_id, entry_id):
    """Dispatch one collection entry to the right browser."""
    row = _collections_mod.get_set(set_id)
    if not row:
        error('المجموعة غير موجودة')
        return end_dir()
    entry = None
    for e in row.get('entries') or []:
        if e.get('id') == entry_id:
            entry = e
            break
    if not entry:
        error('العنصر غير موجود')
        return end_dir()
    kind = entry.get('kind')
    payload = entry.get('payload') or {}
    if kind == 'addonCatalog':
        return _open_addon_catalog_entry(entry, payload)
    if kind == 'traktList':
        return _open_trakt_list_entry(entry, payload)
    if kind == 'mdblistList':
        return _open_mdblist_list_entry(entry, payload)
    if kind == 'multiCatalog':
        return _open_multi_catalog_entry(entry, payload)
    if kind == 'kodiPluginRoute':
        return _open_kodi_plugin_route_entry(entry, payload)
    if kind == 'localJsonCatalog':
        return _render_local_json_catalog(entry, payload)
    error('نوع اختصار غير مدعوم: %s' % kind)
    return end_dir()



def _catalog_extra_from_source(src):
    src = src or {}
    extra = src.get('extra') if isinstance(src.get('extra'), dict) else {}
    genre = str(src.get('genre') or '').strip()
    if genre:
        return 'genre', genre
    if extra:
        for k, v in extra.items():
            if k and v not in (None, ''):
                return str(k), str(v)
    return '', ''


def _open_catalog_from_collection_source(provider_id, catalog_type, catalog_id, label='', src=None, skip=False):
    extra_name, extra_value = _catalog_extra_from_source(src or {})
    if extra_name and extra_value:
        # catalog_extra uses the same preset mechanism as Dex Hub's native
        # folder filters, so collection shortcuts can target a Stremio folder
        # without asking for manual IDs every time.
        return catalog_extra(provider_id, catalog_type, catalog_id, label=label, extra_name=extra_name, extra_value=extra_value, force_remote='1')
    if skip:
        return catalog_all(provider_id, catalog_type, catalog_id, label=label, genre=str((src or {}).get('genre') or ''), force_remote='1')
    return catalog(provider_id, catalog_type, catalog_id, label=label, genre=str((src or {}).get('genre') or ''), force_remote='1')

def _open_multi_catalog_entry(entry, payload):
    """Open/aggregate collection folders backed by Stremio catalogSources.

    Nuvio/Fusion exports usually store one or more catalog sources per folder:
        {"addonId": "pw.ers.netflix-catalog", "catalogId": "nfx", "type": "movie"}

    Dex Hub now resolves addonId -> provider automatically for known public
    manifests, prompts only for configured/private manifests, and directly opens
    a single-source folder to reduce the extra click/back-stack.
    """
    sources = payload.get('sources') or []
    if not sources:
        error('لا توجد مصادر داخل هذا الفولدر')
        return end_dir()

    win = xbmcgui.Window(WINDOW_ID)
    if entry.get('background'):
        win.setProperty('fanart', entry['background'])

    resolved = []
    missing_addons = set()
    # Browse path must stay non-blocking: do not prompt for missing/configured
    # manifests here. Known public manifests can still auto-register; private
    # sources (e.g. Plexio) are surfaced as missing with an Add Provider action.
    resolver = None

    for src in sources:
        addon_id = (src.get('addonId') or '').strip()
        catalog_id = (src.get('catalogId') or '').strip()
        catalog_type = (src.get('catalogType') or src.get('type') or 'movie').strip()
        catalog_genre = str(src.get('genre') or '').strip()
        if not addon_id or not catalog_id:
            continue
        provider = None
        try:
            provider = _collections_mod.resolve_or_register_addon(
                addon_id,
                manifest_resolver=resolver,
                share_url='',
            )
        except Exception as exc:
            xbmc.log('[DexHub] collection source resolve failed %s: %s' % (addon_id, exc), xbmc.LOGWARNING)
            provider = None
        if not provider:
            missing_addons.add(addon_id)
            continue

        manifest = provider.get('manifest') or {}
        cat_name = catalog_id
        for cat in manifest.get('catalogs', []):
            if isinstance(cat, dict) and cat.get('id') == catalog_id and cat.get('type') == catalog_type:
                cat_name = cat.get('name') or catalog_id
                break
        resolved.append({
            'provider': provider,
            'addon_id': addon_id,
            'catalog_id': catalog_id,
            'catalog_type': catalog_type,
            'catalog_name': cat_name,
            'genre': catalog_genre,
            'source': src,
        })

    # Most Nuvio folders point to a single catalog. Opening it directly makes
    # collections feel like native skin widgets and avoids one redundant folder.
    if len(resolved) == 1 and not missing_addons:
        row = resolved[0]
        provider = row.get('provider') or {}
        return _open_catalog_from_collection_source(provider.get('id'), row.get('catalog_type'), row.get('catalog_id'), label=entry.get('name') or row.get('catalog_name') or row.get('catalog_id'), src=row.get('source') or row, skip=_collection_skip_gate_enabled(entry))

    rendered = 0
    for row in resolved:
        provider = row.get('provider') or {}
        catalog_type = row.get('catalog_type') or 'movie'
        type_label = {'movie': 'أفلام', 'series': 'مسلسلات', 'anime': 'أنمي'}.get(catalog_type, catalog_type)
        cat_name = row.get('catalog_name') or row.get('catalog_id') or 'Catalog'
        label = '[%s] %s — %s' % (type_label, cat_name, provider.get('name') or row.get('addon_id'))
        extra_name, extra_value = _catalog_extra_from_source(row.get('source') or row)
        if extra_name and extra_value:
            url_args = dict(action='catalog_extra', provider_id=provider.get('id'),
                            media_type=catalog_type, catalog_id=row.get('catalog_id'),
                            label=cat_name, extra_name=extra_name, extra_value=extra_value,
                            force_remote='1')
        else:
            url_args = dict(action='catalog', provider_id=provider.get('id'),
                            media_type=catalog_type, catalog_id=row.get('catalog_id'),
                            label=cat_name, force_remote='1')
            if row.get('genre'):
                url_args['genre'] = row.get('genre')
        url = build_url(**url_args)
        add_item(label, url,
                 info={'title': cat_name, 'plot': 'من إضافة %s' % (provider.get('name') or row.get('addon_id'))},
                 art={'poster': entry.get('background') or '', 'fanart': entry.get('background') or ''})
        rendered += 1

    if missing_addons:
        names = ', '.join(sorted(missing_addons))
        add_item(
            '[COLOR yellow]⚠ مصادر تحتاج Manifest مُعدّ: %s[/COLOR]' % names,
            build_url(action='add_provider'),
            is_folder=False,
            art=root_art('add'),
            info={'title': 'مصادر مفقودة', 'plot': 'الصق manifest.json لهذه الإضافات. Plexio مثلًا يحتاج رابطًا مُعدًا بحسابك حتى تظهر كتالوجاته.'},
        )

    if rendered == 0 and not missing_addons:
        add_item('[COLOR grey]لا توجد مصادر صالحة[/COLOR]',
                 build_url(action='collection_entry_open', set_id=entry.get('_set_id', ''), entry_id=entry.get('id', '')),
                 is_folder=False)

    end_dir()

def _open_addon_catalog_entry(entry, payload):
    addon_ref = (payload.get('addonId') or '').strip()
    catalog_id = (payload.get('catalogId') or '').strip()
    media_filter = (payload.get('mediaFilter') or 'auto').strip().lower()
    if media_filter == 'movie':
        catalog_type = 'movie'
    elif media_filter == 'anime':
        catalog_type = 'anime'
    elif media_filter in ('series', 'show', 'tv'):
        catalog_type = 'series'
    else:
        catalog_type = (payload.get('catalogType') or 'movie').strip()
    if catalog_type not in ('movie', 'series', 'anime'):
        catalog_type = 'movie'
    if not addon_ref or not catalog_id:
        error('اختصار غير مكتمل')
        return end_dir()

    try:
        provider = _collections_mod.resolve_or_register_addon(
            addon_ref,
            manifest_resolver=_make_addon_manifest_resolver(''),
            share_url='',
        )
    except Exception as exc:
        error('تعذّر تسجيل المصدر: %s' % exc)
        return end_dir()
    if not provider:
        error('الإضافة غير مثبّتة أو تحتاج Manifest مُعدّ: %s' % addon_ref)
        return end_dir()

    return _open_catalog_from_collection_source(provider.get('id'), catalog_type, catalog_id, label=entry.get('name') or catalog_id, src=payload, skip=_collection_skip_gate_enabled(entry))


def _open_trakt_list_entry(entry, payload):
    username = (payload.get('username') or '').strip()
    slug = (payload.get('listSlug') or payload.get('slug') or '').strip()
    if not username or not slug:
        error('اختصار Trakt غير مكتمل')
        return end_dir()
    return trakt_list_browse(username, slug, title=entry.get('name') or slug, background=entry.get('background') or '', media_filter=payload.get('mediaFilter') or 'auto', force_remote='1')


def _open_mdblist_list_entry(entry, payload):
    username = (payload.get('username') or '').strip()
    slug = (payload.get('listSlug') or payload.get('slug') or '').strip()
    if not username or not slug:
        error('اختصار MDBList غير مكتمل')
        return end_dir()
    return mdblist_list_browse(username, slug, title=entry.get('name') or slug, background=entry.get('background') or '', media_filter=payload.get('mediaFilter') or 'auto', force_remote='1')


def _content_type_from_plugin_rows(rows):
    # Plugin directories are mixed by nature; keep files unless labels strongly
    # indicate a media-only page. This mirrors how skins use arbitrary plugin
    # widget paths without forcing Kodi to rescan/sort them as movies.
    return 'files'


def kodi_route_browse(route='', title='', background='', page='0'):
    route_url = str(route or '').strip()
    if not route_url.startswith('plugin://'):
        error('رابط plugin غير صالح')
        return end_dir(content='files')
    rows = _list_plugin_directory_items(route_url)
    if not rows:
        # Last-resort fallback: some plugins refuse JSON-RPC directory reads but
        # work with a native Container.Update. Use replace to avoid a deep back
        # stack and duplicate helper windows.
        try:
            xbmc.executebuiltin('Container.Update(%s,replace)' % route_url)
            return
        except Exception:
            error('المسار فارغ أو غير قابل للقراءة')
            return end_dir(content='files')

    page_num, _ps, visible, has_more = _page_slice(rows, page)
    win = xbmcgui.Window(WINDOW_ID)
    if background:
        win.setProperty('fanart', background)
    root_label = title or route_url
    for row in visible:
        item_url = str(row.get('file') or '').strip()
        label = row.get('label') or item_url or 'Item'
        thumb = _wrap_tokenized_url(row.get('thumbnail') or '')
        fanart = _wrap_tokenized_url(row.get('fanart') or '') or background or addon_fanart()
        art = {'thumb': thumb or fanart, 'poster': thumb or fanart, 'fanart': fanart, 'landscape': fanart}
        info = {'title': label, 'plot': row.get('plot') or '', 'mediatype': 'video'}
        if row.get('is_folder'):
            path = build_url(action='kodi_route_browse', route=item_url, title=label, background=fanart or background, page='0')
            ctx_menu = [('فتح بالمسار الأصلي', 'Container.Update(%s)' % item_url)]
            add_item(label, path, is_folder=True, info=info, art=art, context_menu=ctx_menu)
        else:
            # Keep playable plugin items in Dex Hub's list. Kodi will hand them
            # back to their own addon on click, which is how skins like Arctic
            # Fuse use plugin widget/folder paths.
            add_item(label, item_url, is_folder=False, info=info, art=art, properties={'IsPlayable': 'true'}, context_menu=[('فتح بالمسار الأصلي', 'RunPlugin(%s)' % item_url)])
    if has_more:
        add_item('المزيد', build_url(action='kodi_route_browse', route=route_url, title=root_label, background=background, page=str(page_num + 1)), info={'title': 'المزيد', 'plot': 'تحميل عناصر إضافية من هذا المسار'}, art=root_art('catalogs'))
    end_dir(content=_content_type_from_plugin_rows(rows), cache=False)


def _open_kodi_plugin_route_entry(entry, payload):
    route_url = str(payload.get('route') or payload.get('url') or '').strip()
    if not route_url:
        error('اختصار غير مكتمل')
        return end_dir()
    return kodi_route_browse(route=route_url, title=entry.get('name') or payload.get('addonName') or route_url, background=entry.get('background') or payload.get('fanart') or '')


def trakt_list_browse(username, slug, title='', background='', media_filter='auto', page='0', force_remote=''):
    """Render a public Trakt user list as a folder of movies/shows.

    Uses Trakt extended metadata and enriches artwork from TMDb Helper cache,
    with direct TMDb fallback when available.
    """
    force_remote = _force_remote_posters_enabled(force_remote)
    try:
        rows = trakt.fetch_user_list(username, slug) or []
    except Exception as exc:
        error('فشل قراءة قائمة Trakt: %s' % exc)
        return end_dir()
    if not rows:
        error('القائمة فارغة أو غير متاحة')
        return end_dir()

    media_filter = str(media_filter or 'auto').strip().lower()
    if media_filter in ('movie', 'movies'):
        rows = [r for r in rows if (str((r.get('type') or '')).lower() == 'movie' or r.get('movie'))]
    elif media_filter in ('series', 'show', 'shows', 'tv', 'anime'):
        rows = [r for r in rows if (str((r.get('type') or '')).lower() == 'show' or r.get('show'))]
    page_num, _page_size, visible_rows, has_more = _page_slice(rows, page)

    win = xbmcgui.Window(WINDOW_ID)
    if background:
        win.setProperty('fanart', background)

    any_series = False
    any_movie = False
    first_fanart = background or ''
    for row in visible_rows:
        item_type = (row.get('type') or '').lower()
        meta = row.get(item_type) if item_type in ('movie', 'show') else (row.get('movie') or row.get('show'))
        if not isinstance(meta, dict):
            continue
        ids = meta.get('ids') or {}
        name = meta.get('title') or ''
        year = meta.get('year') or ''
        imdb = str(ids.get('imdb') or '').strip()
        tmdb = str(ids.get('tmdb') or '').strip()
        tvdb = str(ids.get('tvdb') or '').strip()

        if imdb:
            canonical = imdb if imdb.startswith('tt') else 'tt%s' % imdb
        elif tmdb:
            canonical = 'tmdb:%s' % tmdb
        elif tvdb:
            canonical = 'tvdb:%s' % tvdb
        else:
            continue

        is_series = item_type == 'show' or bool(row.get('show'))
        media_type = 'series' if is_series else 'movie'
        if is_series:
            any_series = True
            action = 'series_meta'
        else:
            any_movie = True
            action = 'streams'

        explicit_virtual_source = _target_meta_source_is_explicit('virtual.collection.trakt')
        art_bundle = {} if explicit_virtual_source else _trakt_art_bundle(ids, media_type, title=name, year=year, meta=meta, force_remote=force_remote, allow_direct=False)
        virtual_meta = _virtual_meta_override('virtual.collection.trakt', media_type, {
            'id': canonical,
            'name': name,
            'title': name,
            'year': year,
            'poster': art_bundle.get('poster') or '',
            'background': art_bundle.get('fanart') or art_bundle.get('landscape') or '',
            'fanart': art_bundle.get('fanart') or art_bundle.get('landscape') or '',
            'landscape': art_bundle.get('landscape') or art_bundle.get('fanart') or '',
            'clearlogo': art_bundle.get('clearlogo') or '',
            'logo': art_bundle.get('clearlogo') or '',
        })
        if explicit_virtual_source:
            fanart = virtual_meta.get('background') or virtual_meta.get('fanart') or virtual_meta.get('landscape') or background or addon_fanart()
        else:
            fanart = virtual_meta.get('background') or virtual_meta.get('fanart') or virtual_meta.get('landscape') or art_bundle.get('fanart') or art_bundle.get('landscape') or background or addon_fanart()
        if fanart and not first_fanart:
            first_fanart = fanart
        if explicit_virtual_source:
            art = {
                'thumb': virtual_meta.get('poster') or '',
                'poster': virtual_meta.get('poster') or '',
                'fanart': fanart,
                'landscape': virtual_meta.get('landscape') or virtual_meta.get('fanart') or '',
                'clearlogo': virtual_meta.get('clearlogo') or '',
            }
        else:
            art = {
                'thumb': virtual_meta.get('poster') or art_bundle.get('poster') or root_art('trakt').get('poster') or '',
                'poster': virtual_meta.get('poster') or art_bundle.get('poster') or root_art('trakt').get('poster') or '',
                'fanart': fanart,
                'landscape': virtual_meta.get('landscape') or art_bundle.get('landscape') or art_bundle.get('fanart') or '',
                'clearlogo': virtual_meta.get('clearlogo') or art_bundle.get('clearlogo') or '',
            }
        if art.get('clearlogo'):
            art['logo'] = art.get('clearlogo')
            art['tvshow.clearlogo'] = art.get('clearlogo')
        info = _trakt_info(meta, media_type)
        ids_out = {'imdb_id': imdb if imdb.startswith('tt') else ('tt%s' % imdb if imdb else ''), 'tmdb_id': tmdb, 'tvdb_id': tvdb}
        try:
            _meta_mem_put(media_type, canonical, virtual_meta, source_provider_id='virtual.collection.trakt')
        except Exception:
            pass
        path, path_is_folder = _content_click_path(media_type=media_type, canonical_id=canonical, title=name, tmdb_id=tmdb, imdb_id=ids_out.get('imdb_id') or '', tvdb_id=tvdb, source_provider_id='virtual.collection.trakt')
        ctx_menu = [('تغيير مصدر الميتاداتا', 'RunPlugin(%s)' % build_url(action='meta_pick_target', target_key='virtual.collection.trakt', title='الكوليكشن • عناصر Trakt'))] + _build_source_picker_menu(media_type=media_type, canonical_id=canonical, title=name, source_provider_id='virtual.collection.trakt') + _build_player_chooser_menu(
            media_type=media_type,
            canonical_id=canonical,
            title=name,
            tmdb_id=tmdb,
            imdb_id=ids_out.get('imdb_id') or '',
            tvdb_id=tvdb,
            source_provider_id='virtual.collection.trakt',
        )
        tmdbh_url = _tmdbh_url_from_ids(media_type=media_type, tmdb_id=tmdb, imdb_id=ids_out.get('imdb_id') or '', tvdb_id=tvdb, title=name)
        # TMDb Helper already available via "اختيار المشغّل…"; skip duplicate direct entry.
        add_item(name, path, is_folder=path_is_folder, info=info, art=art, ids=ids_out, context_menu=ctx_menu)

    if has_more:
        add_item(
            'المزيد',
            build_url(action='trakt_list_browse', username=username, slug=slug, title=title, background=background, media_filter=media_filter, page=str(page_num + 1), **_force_remote_query(force_remote)),
            info={'title': 'المزيد', 'plot': 'تحميل المزيد من عناصر قائمة Trakt'},
            art=root_art('trakt'),
        )
    if first_fanart:
        win.setProperty('fanart', first_fanart)
    content = 'tvshows' if any_series and not any_movie else 'movies'
    end_dir(content=content)

def mdblist_list_browse(username, slug, title='', background='', media_filter='auto', cursor='', force_remote=''):
    force_remote = _force_remote_posters_enabled(force_remote)
    try:
        rows, next_cursor = mdblist.fetch_items(username, slug, media_filter=media_filter, cursor=cursor, limit=_listing_page_size())
    except Exception as exc:
        error('فشل قراءة قائمة MDBList: %s' % exc)
        return end_dir()
    if not rows:
        error('القائمة فارغة أو غير متاحة')
        return end_dir()

    win = xbmcgui.Window(WINDOW_ID)
    if background:
        win.setProperty('fanart', background)

    any_series = False
    any_movie = False
    first_fanart = background or ''
    for meta in rows:
        item_type = str(meta.get('_type') or meta.get('mediatype') or '').lower()
        is_series = item_type in ('show', 'series', 'tv', 'anime')
        media_type = 'series' if is_series else 'movie'
        ids = dict(meta.get('ids') or {})
        imdb = str(ids.get('imdb') or meta.get('imdb_id') or '').strip()
        tmdb = str(ids.get('tmdb') or meta.get('id') or '').strip()
        tvdb = str(ids.get('tvdb') or meta.get('tvdb_id') or '').strip()
        ids.update({'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb})
        name = meta.get('title') or ''
        year = meta.get('release_year') or meta.get('year') or ''

        if imdb:
            canonical = imdb if imdb.startswith('tt') else 'tt%s' % imdb
        elif tmdb:
            canonical = 'tmdb:%s' % tmdb
        elif tvdb:
            canonical = 'tvdb:%s' % tvdb
        else:
            continue

        action = 'series_meta' if is_series else 'streams'
        if is_series:
            any_series = True
        else:
            any_movie = True

        explicit_virtual_source = _target_meta_source_is_explicit('virtual.collection.trakt')
        art_bundle = {} if explicit_virtual_source else _trakt_art_bundle(ids, media_type, title=name, year=year, meta=meta, force_remote=force_remote, allow_direct=False)
        virtual_meta = _virtual_meta_override('virtual.collection.trakt', media_type, {
            'id': canonical, 'name': name, 'title': name, 'year': year,
            'poster': art_bundle.get('poster') or '',
            'background': art_bundle.get('fanart') or art_bundle.get('landscape') or '',
            'fanart': art_bundle.get('fanart') or art_bundle.get('landscape') or '',
            'landscape': art_bundle.get('landscape') or art_bundle.get('fanart') or '',
            'clearlogo': art_bundle.get('clearlogo') or '',
            'logo': art_bundle.get('clearlogo') or '',
        })
        if explicit_virtual_source:
            fanart = virtual_meta.get('background') or virtual_meta.get('fanart') or virtual_meta.get('landscape') or background or addon_fanart()
        else:
            fanart = virtual_meta.get('background') or virtual_meta.get('fanart') or virtual_meta.get('landscape') or art_bundle.get('fanart') or art_bundle.get('landscape') or background or addon_fanart()
        if fanart and not first_fanart:
            first_fanart = fanart
        if explicit_virtual_source:
            art = {
                'thumb': virtual_meta.get('poster') or '',
                'poster': virtual_meta.get('poster') or '',
                'fanart': fanart,
                'landscape': virtual_meta.get('landscape') or virtual_meta.get('fanart') or '',
                'clearlogo': virtual_meta.get('clearlogo') or '',
            }
        else:
            art = {
                'thumb': virtual_meta.get('poster') or art_bundle.get('poster') or root_art('catalogs').get('poster') or '',
                'poster': virtual_meta.get('poster') or art_bundle.get('poster') or root_art('catalogs').get('poster') or '',
                'fanart': fanart,
                'landscape': virtual_meta.get('landscape') or art_bundle.get('landscape') or art_bundle.get('fanart') or '',
                'clearlogo': virtual_meta.get('clearlogo') or art_bundle.get('clearlogo') or '',
            }
        if art.get('clearlogo'):
            art['logo'] = art.get('clearlogo')
            art['tvshow.clearlogo'] = art.get('clearlogo')
        info = {'title': name, 'sorttitle': name, 'plot': meta.get('overview') or meta.get('description') or '', 'mediatype': 'tvshow' if is_series else 'movie'}
        if year:
            try:
                info['year'] = int(year)
            except Exception:
                pass
        ids_out = {'imdb_id': imdb if imdb.startswith('tt') else ('tt%s' % imdb if imdb else ''), 'tmdb_id': tmdb, 'tvdb_id': tvdb}
        try:
            _meta_mem_put(media_type, canonical, virtual_meta, source_provider_id='virtual.collection.trakt')
        except Exception:
            pass
        path, path_is_folder = _content_click_path(media_type=media_type, canonical_id=canonical, title=name, tmdb_id=tmdb, imdb_id=ids_out.get('imdb_id') or '', tvdb_id=tvdb, source_provider_id='virtual.collection.trakt')
        ctx_menu = [('تغيير مصدر الميتاداتا', 'RunPlugin(%s)' % build_url(action='meta_pick_target', target_key='virtual.collection.trakt', title='الكوليكشن • عناصر Trakt'))] + _build_source_picker_menu(media_type=media_type, canonical_id=canonical, title=name, source_provider_id='virtual.collection.trakt') + _build_player_chooser_menu(media_type=media_type, canonical_id=canonical, title=name, tmdb_id=tmdb, imdb_id=ids_out.get('imdb_id') or '', tvdb_id=tvdb, source_provider_id='virtual.collection.trakt')
        add_item(name, path, is_folder=path_is_folder, info=info, art=art, ids=ids_out, context_menu=ctx_menu)

    if next_cursor:
        add_item('المزيد', build_url(action='mdblist_list_browse', username=username, slug=slug, title=title, background=background, media_filter=media_filter, cursor=next_cursor, **_force_remote_query(force_remote)), info={'title': 'المزيد', 'plot': 'تحميل المزيد من عناصر قائمة MDBList'}, art=root_art('catalogs'))
    if first_fanart:
        win.setProperty('fanart', first_fanart)
    content = 'tvshows' if any_series and not any_movie else 'movies'
    end_dir(content=content)


# ─── NextUp helpers (Issue #10) ────────────────────────────────────────

def _series_videos_cached(canonical_id, media_type='series', title=''):
    return _nextup_series_videos_cached(
        canonical_id,
        window=xbmcgui.Window(WINDOW_ID),
        prop_prefix=SERIES_PROP_PREFIX,
        provider_order_for_id=_provider_order_for_id,
        fetch_meta=fetch_meta,
        fast_timeout_value=fast_timeout('meta'),
        item_fallback_art=_item_fallback_art,
        resolve_meta_art=_resolve_meta_art,
        provider_prefers_native_art=_provider_prefers_native_art,
        media_type=media_type,
        title=title,
    )


def _nextup_items_cached(limit=40):
    return _nextup_items_cached_logic(
        limit=limit,
        window=xbmcgui.Window(WINDOW_ID),
        trakt_mod=trakt,
        playback_store_mod=playback_store,
        series_videos_loader=_series_videos_cached,
        log_prefix='[DexHub]',
    )


def nextup():
    rows = _nextup_items_cached(limit=60)
    if not rows:
        notify('لا توجد حلقات قادمة بعد. شاهد حلقة من أي مسلسل ليظهر هنا.')
        return end_dir(content='episodes', cache=False)

    # Bug fix (3.7.90): previously, art backfill was deferred to a background
    # thread that wrote results to playback_store, but the *current* render
    # had already happened with empty/stale art — users saw blank posters
    # until they re-opened Next Up. We now resolve missing art INLINE before
    # rendering. The resolver hits TMDb Helper's local sqlite first (no
    # network), so the cost is small. Rows that already have non-tokenized
    # art skip the resolver entirely via the fast path.
    def _row_needs_art(r):
        if not (r.get('poster') and r.get('background') and r.get('clearlogo')):
            return True
        # Stale Plex/Emby tokens count as missing.
        if _row_poster_looks_provider_tokenized(r.get('poster')):
            return True
        return False

    rows_needing_art = [(i, r) for i, r in enumerate(rows) if _row_needs_art(r)]

    # Resolve missing art in parallel — bounded pool, capped wait.
    if rows_needing_art:
        try:
            from concurrent.futures import ThreadPoolExecutor
            def _one(idx_row):
                i, r = idx_row
                try:
                    art = _resolve_row_art(r)
                    new_poster    = art.get('poster')    or ''
                    new_fanart    = art.get('fanart')    or ''
                    new_clearlogo = art.get('clearlogo') or ''
                    new_wide      = _nextup_row_wide_art(r, art) or new_fanart
                    # Replace stale tokenized poster only if we actually got a
                    # better remote one (don't blank a working URL).
                    if new_poster and new_poster != _favorite_default_poster(r.get('media_type') or 'series'):
                        r['poster'] = new_poster
                    if new_wide:
                        r['background'] = new_wide
                        r['landscape'] = new_wide
                        r['banner'] = new_wide
                    elif new_fanart:
                        r['background'] = new_fanart
                    if new_clearlogo:
                        r['clearlogo'] = new_clearlogo
                    # Persist to playback_store so subsequent visits skip the
                    # resolver entirely (no double work).
                    if new_poster or new_fanart or new_clearlogo:
                        playback_store.update_art(
                            (r.get('media_type') or 'series').lower(),
                            r.get('canonical_id') or '',
                            r.get('video_id') or r.get('canonical_id') or '',
                            poster=new_poster,
                            background=(new_wide or new_fanart),
                            clearlogo=new_clearlogo,
                        )
                except Exception:
                    pass
            with ThreadPoolExecutor(max_workers=6) as pool:
                list(pool.map(_one, rows_needing_art))
            # Drop the cached Next Up snapshot so the new art is reflected
            # next open (not strictly needed since we just rendered fresh,
            # but cheap insurance).
            try:
                _nextup_invalidate_cache(xbmcgui.Window(WINDOW_ID))
            except Exception:
                pass
        except Exception as exc:
            xbmc.log('[DexHub] nextup inline art fill failed: %s' % exc, xbmc.LOGDEBUG)

    for row in rows:
        try:
            title     = row.get('title') or ''
            ep_title  = row.get('episode_title') or ''
            season    = int(row.get('season') or 0)
            episode   = int(row.get('episode') or 0)
            if season <= 0 or episode <= 0:
                continue
            display = '%s — S%02dE%02d%s' % (
                title, season, episode,
                (' — %s' % ep_title) if ep_title else '')
            canonical = row.get('canonical_id') or ''
            video_id  = row.get('video_id') or canonical
            row_ids   = _merge_seed_ids(
                extract_ids({'id': canonical}), _get_tmdbh_seed_ids(canonical))
            path, path_is_folder = _content_click_path(
                media_type='series', canonical_id=canonical,
                video_id=video_id, season=season, episode=episode,
                title=title or canonical,
                tmdb_id=row_ids.get('tmdb_id') or '',
                imdb_id=row_ids.get('imdb_id') or '',
                tvdb_id=row_ids.get('tvdb_id') or '',
            )
            art = _make_art_dict(
                row.get('poster') or '',
                row.get('background') or '',
                row.get('clearlogo') or '',
                'series',
            )
            # Next Up is an episode shelf; show it as a wide banner/landscape
            # card instead of the vertical show poster. Many Kodi skins pick
            # thumb/poster first even in horizontal widgets, so mirror the wide
            # image into those keys for this screen only.
            _nextup_wide = _nextup_row_wide_art(row, art, ids=row_ids)
            # Some skins still read ListItem.Art(poster/thumb) for this shelf.
            # Therefore Next Up must put the *wide* image into poster/thumb too.
            # If the real wide art is missing, use the Next Up wide fallback
            # instead of leaking the vertical show poster into the banner row.
            if not _nextup_wide:
                _fallback_nextup_art = root_art('nextup') or {}
                _nextup_wide = (_fallback_nextup_art.get('landscape') or
                                _fallback_nextup_art.get('fanart') or
                                addon_fanart() or
                                _fallback_nextup_art.get('poster') or
                                _fallback_nextup_art.get('thumb') or '')
            if _nextup_wide:
                art = _force_wide_art_keys(art, _nextup_wide)
            info = {
                'title':      display,
                'tvshowtitle': title,
                'season':     season,
                'episode':    episode,
                'mediatype':  'episode',
                'plot':       row.get('plot') or '',
                'playcount':  0,
            }
            ctx_menu = _build_source_picker_menu(
                media_type=row.get('media_type') or 'series',
                canonical_id=canonical, title=title or canonical,
                season=season, episode=episode, video_id=video_id,
                preferred_provider_name=row.get('provider_name') or '',
            ) + _build_player_chooser_menu(
                media_type=row.get('media_type') or 'series',
                canonical_id=canonical, title=title or canonical,
                tmdb_id=row_ids.get('tmdb_id') or '',
                imdb_id=row_ids.get('imdb_id') or '',
                tvdb_id=row_ids.get('tvdb_id') or '',
                season=season, episode=episode, video_id=video_id,
            ) + [
                ('فتح بيانات المسلسل', 'Container.Update(%s)' % build_url(
                    action='series_meta', media_type='series',
                    canonical_id=canonical, title=title or canonical)),
                ('إضافة إلى المفضلة', 'RunPlugin(%s)' % build_url(
                    action='fav_add', media_type='series',
                    canonical_id=canonical, title=title or canonical,
                    poster=art.get('poster') or '',
                    background=art.get('fanart') or '',
                    clearlogo=art.get('clearlogo') or '')),
            ]
            props = {'IsPlayable': 'true'} if not path_is_folder else {}
            add_item(display, path, is_folder=path_is_folder,
                     info=info, art=art, properties=props, context_menu=ctx_menu)
        except Exception as exc:
            xbmc.log('[DexHub] nextup row failed: %s' % exc, xbmc.LOGWARNING)
            continue
    end_dir(content='episodes', cache=False)


# ─── Favorites helpers (Issue #11) ──────────────────────────────────────

def _favorite_default_poster(media_type='movie'):
    media_type = (media_type or 'movie').lower()
    return media_path('default_series_poster.png' if media_type in ('series', 'anime', 'tv', 'show') else 'default_movie_poster.png')



def _art_from_tmdbh_db(ids, media_type):
    """Try TMDb Helper local DB first (no network, fast). Returns bundle or {}."""
    tmdb_id = str(ids.get('tmdb_id') or '').strip()
    imdb_id = str(ids.get('imdb_id') or '').strip()
    if not tmdb_id and not imdb_id:
        return {}
    try:
        return _tmdb_art_db.get_art_bundle_from_db(
            tmdb_id=tmdb_id,
            imdb_id=imdb_id,
            media_type='tv' if media_type in ('series', 'anime', 'show', 'tv') else 'movie',
        ) or {}
    except Exception:
        return {}


def _row_poster_looks_provider_tokenized(value):
    """True when a stored poster URL looks like a Plex/Plexio/Emby tokenized
    URL — those frequently break (token expires, server unreachable, etc.).

    For Next Up / Continue Watching backfill, we should NOT short-circuit on
    these URLs and should instead reach the remote-art fallback chain. The
    user reported empty posters in Next Up; many of those rows had stale
    Plex tokens cached in playback_store.
    """
    text = str(value or '').lower()
    if not text:
        return False
    if 'x-plex-token=' in text:
        return True
    if '/photo/:/transcode' in text or '/library/metadata/' in text:
        return True
    # Emby auth token query
    if 'api_key=' in text and ('/items/' in text or '/emby/' in text):
        return True
    return False


def _resolve_row_art(row):
    """Resolve poster / fanart / clearlogo for a stored row (favorites / CW / nextup).

    Lookup chain (stops as soon as all three fields are found):
      1. Row itself (fast path — zero I/O if the row was written with art)
      2. TMDb Helper local DB — instant, no network
      3. Trakt art bundle (TMDb Helper DB + tmdb_direct API), force_remote=True
      4. tmdb_direct API directly

    Returns a Kodi-ready art dict.
    """
    row = row or {}
    media_type = (row.get('media_type') or 'movie').lower()
    canonical = row.get('canonical_id') or ''
    title = row.get('title') or canonical
    
    try:
        _year_int = int(row.get('year') or 0)
    except Exception:
        _year_int = 0
    year = str(_year_int) if _year_int > 0 else ''

    poster    = row.get('poster') or ''
    fanart    = row.get('background') or ''
    clearlogo = row.get('clearlogo') or ''

    # Bug fix (3.7.90): if the cached poster looks like a Plex/Emby tokenized
    # URL, treat it as missing so the remote chain kicks in. These URLs go
    # stale frequently and produced empty Next Up posters for users.
    if _row_poster_looks_provider_tokenized(poster):
        poster = ''
    if _row_poster_looks_provider_tokenized(fanart):
        fanart = ''

    # Fast path — row already has everything (and none of it is a stale token).
    if poster and fanart and clearlogo:
        return _make_art_dict(poster, fanart, clearlogo, media_type)

    # Build a rich id seed from the canonical_id prefix.
    canonical_lower = (canonical or '').lower()
    seed = {'id': canonical}
    if canonical_lower.startswith('tmdb:'):
        seed['tmdb_id'] = canonical.split(':', 1)[-1].strip()
    elif canonical_lower.startswith('tvdb:'):
        seed['tvdb_id'] = canonical.split(':', 1)[-1].strip()
    elif canonical_lower.startswith('tt'):
        seed['imdb_id'] = canonical.strip()

    try:
        ids = extract_ids(seed)
    except Exception:
        ids = {}

    # Step 2: TMDb Helper local DB (no network).
    if not (poster and fanart and clearlogo):
        db_b = _art_from_tmdbh_db(ids, media_type)
        poster    = poster    or db_b.get('poster')    or ''
        fanart    = fanart    or db_b.get('fanart')    or db_b.get('landscape') or ''
        clearlogo = clearlogo or db_b.get('clearlogo') or ''

    # Step 3: Trakt art bundle. force_remote=True so 'Local only' mode
    # doesn't blank the poster — virtual rows have no local provider.
    if not (poster and fanart and clearlogo):
        try:
            bundle = _trakt_art_bundle(ids, media_type, title=title, year=year, force_remote=True) or {}
        except Exception:
            bundle = {}
        poster    = poster    or bundle.get('poster')    or ''
        fanart    = fanart    or bundle.get('fanart')    or bundle.get('landscape') or ''
        clearlogo = clearlogo or bundle.get('clearlogo') or ''

    # Step 4: tmdb_direct API directly (needs API key; silent no-op if missing).
    if not (poster and fanart and clearlogo):
        try:
            direct = _tmdb_direct.art_for(
                tmdb_id=ids.get('tmdb_id') or '',
                imdb_id=ids.get('imdb_id') or '',
                media_type='tv' if media_type in ('series', 'anime', 'show', 'tv') else 'movie',
                title=title,
                year=year,
            ) or {}
        except Exception:
            direct = {}
        poster    = poster    or direct.get('poster')    or ''
        fanart    = fanart    or direct.get('fanart')    or direct.get('landscape') or ''
        clearlogo = clearlogo or direct.get('clearlogo') or ''

    return _make_art_dict(poster, fanart, clearlogo, media_type)


def _art_values_same(a, b):
    try:
        aa = str(a or '').strip()
        bb = str(b or '').strip()
        if not aa or not bb:
            return False
        return aa == bb
    except Exception:
        return False


def _nextup_row_wide_art(row, resolved_art=None, ids=None):
    """Return a real wide image for Next Up, never the vertical poster.

    Kodi skins often prefer `poster`/`thumb` even when a row is meant to be a
    horizontal widget. For Next Up we therefore compute a dedicated wide image
    and later mirror it into all art keys. The important part is to avoid
    `_make_art_dict()`'s fallback where `landscape` becomes the poster.
    """
    row = row or {}
    resolved_art = resolved_art or {}
    poster = _wrap_tokenized_url(row.get('poster') or resolved_art.get('poster') or '')

    candidates = []
    for value in (
        row.get('banner'), row.get('landscape'), row.get('background'), row.get('fanart'), row.get('backdrop'),
        resolved_art.get('banner'), resolved_art.get('landscape'), resolved_art.get('fanart'),
    ):
        value = _wrap_tokenized_url(value or '')
        if value and not _art_values_same(value, poster):
            candidates.append(value)

    media_type = (row.get('media_type') or 'series').lower()
    title = row.get('title') or row.get('canonical_id') or ''
    try:
        _year_int = int(row.get('year') or 0)
    except Exception:
        _year_int = 0
    year = str(_year_int) if _year_int > 0 else ''

    if not ids:
        seed = {'id': row.get('canonical_id') or ''}
        cid = str(seed.get('id') or '').lower()
        if cid.startswith('tmdb:'):
            seed['tmdb_id'] = cid.split(':', 1)[-1]
        elif cid.startswith('tvdb:'):
            seed['tvdb_id'] = cid.split(':', 1)[-1]
        elif cid.startswith('tt'):
            seed['imdb_id'] = seed.get('id')
        try:
            ids = extract_ids(seed)
        except Exception:
            ids = {}

    try:
        db_b = _art_from_tmdbh_db(ids or {}, media_type) or {}
        for value in (db_b.get('landscape'), db_b.get('fanart')):
            value = _wrap_tokenized_url(value or '')
            if value and not _art_values_same(value, poster):
                candidates.append(value)
    except Exception:
        pass

    try:
        direct = _tmdb_direct.art_for(
            tmdb_id=(ids or {}).get('tmdb_id') or '',
            imdb_id=(ids or {}).get('imdb_id') or '',
            media_type='tv' if media_type in ('series', 'anime', 'show', 'tv') else 'movie',
            title=title,
            year=year,
        ) or {}
        for value in (direct.get('landscape'), direct.get('fanart')):
            value = _wrap_tokenized_url(value or '')
            if value and not _art_values_same(value, poster):
                candidates.append(value)
    except Exception:
        pass

    seen = set()
    for value in candidates:
        if not value or value in seen:
            continue
        seen.add(value)
        return value
    return ''


def _force_wide_art_keys(art, wide):
    art = dict(art or {})
    wide = _wrap_tokenized_url(wide or '')
    if not wide:
        return art
    for key in (
        'thumb', 'icon', 'poster', 'banner', 'landscape', 'fanart',
        'tvshow.poster', 'tvshow.thumb', 'tvshow.banner', 'tvshow.landscape', 'tvshow.fanart',
        'episode.thumb', 'episode.poster', 'episode.banner', 'episode.landscape',
    ):
        art[key] = wide
    return art


def _make_art_dict(poster, fanart, clearlogo, media_type='movie'):
    poster    = poster    or _favorite_default_poster(media_type)
    fanart    = fanart    or poster or addon_fanart()
    landscape = fanart or poster or ''
    d = {
        'thumb':    poster,
        'poster':   poster,
        'fanart':   fanart,
        'landscape': landscape,
        'banner': landscape,
        'clearlogo': clearlogo,
        'logo':      clearlogo or '',
    }
    if media_type in ('series', 'anime', 'show', 'tv'):
        d['tvshow.clearlogo'] = clearlogo or ''
    return d


def _favorite_row_art(row):
    """Resolve art for a favorites row. Persists resolved art back to SQLite
    so the next visit is instant (no network needed)."""
    row = row or {}
    art = _resolve_row_art(row)
    # Persist non-empty resolved art back to favorites DB so it's cached
    # for all future visits without any lookup.
    poster    = art.get('poster')    or ''
    fanart    = art.get('fanart')    or ''
    clearlogo = art.get('clearlogo') or ''
    had_poster    = bool(row.get('poster'))
    had_fanart    = bool(row.get('background'))
    had_clearlogo = bool(row.get('clearlogo'))
    if (poster and not had_poster) or (fanart and not had_fanart) or (clearlogo and not had_clearlogo):
        try:
            favorites_store.add(
                (row.get('media_type') or 'movie').lower(),
                row.get('canonical_id') or '',
                row.get('title') or '',
                poster=poster if not had_poster else '',
                background=fanart if not had_fanart else '',
                clearlogo=clearlogo if not had_clearlogo else '',
                year=int(row.get('year') or 0),
                plot=row.get('plot') or '',
                source=row.get('source') or 'local',
            )
        except Exception:
            pass
    return art




def _refresh_visible_favorites_container():
    try:
        current = xbmc.getInfoLabel('Container.FolderPath') or ''
        if 'plugin.video.dexhub' in current and 'action=favorites' in current:
            xbmc.executebuiltin('Container.Refresh')
    except Exception:
        pass



def _refresh_trakt_favorites_mirror():
    """Pull Trakt watchlist into the local mirror table. Best-effort, silent."""
    try:
        if not trakt.enabled():
            favorites_store.replace_trakt_mirror([])
            return
        rows = trakt.fetch_watchlist(limit=200) or []
        favorites_store.replace_trakt_mirror(rows)
    except Exception as exc:
        xbmc.log('[DexHub] favorites trakt mirror failed: %s' % exc, xbmc.LOGDEBUG)


def favorites():
    # Refresh the Trakt mirror in the background once per session.
    win = xbmcgui.Window(WINDOW_ID)
    if not win.getProperty('dexhub.fav_mirror_done') and not win.getProperty('dexhub.fav_mirror_syncing'):
        try:
            win.setProperty('dexhub.fav_mirror_syncing', '1')
            def _bg():
                try:
                    _refresh_trakt_favorites_mirror()
                finally:
                    try:
                        win.setProperty('dexhub.fav_mirror_done', '1')
                        win.clearProperty('dexhub.fav_mirror_syncing')
                    except Exception:
                        pass
                    _refresh_visible_favorites_container()
            threading.Thread(target=_bg, daemon=True).start()
        except Exception:
            try:
                win.clearProperty('dexhub.fav_mirror_syncing')
            except Exception:
                pass

    rows = favorites_store.list_favorites(limit=300) or []
    if not rows:
        if win.getProperty('dexhub.fav_mirror_syncing'):
            add_item('[COLOR grey]جارِ تحميل المفضلة…[/COLOR]', build_url(action='favorites'), is_folder=False,
                     info={'title': 'المفضلة', 'plot': 'يتم تجهيز المفضلة المحلية ونسخة Trakt.'},
                     art=root_art('favorites'))
            return end_dir(content='movies')
        notify('قائمة المفضلة فارغة. أضف عنصراً عبر "إضافة إلى المفضلة" من قائمة السياق.')
        return end_dir(content='movies')

    any_series = any((r.get('media_type') or '').lower() in ('series', 'anime', 'tv', 'show') for r in rows)
    any_movie = any((r.get('media_type') or '').lower() == 'movie' for r in rows)
    content_type = 'movies' if any_movie and not any_series else ('tvshows' if any_series and not any_movie else 'movies')

    if win.getProperty('dexhub.fav_mirror_syncing'):
        add_item('[COLOR grey]جارِ تحديث مزامنة Trakt للمفضلة…[/COLOR]', build_url(action='favorites'), is_folder=False,
                 info={'title': 'مزامنة Trakt', 'plot': 'يتم تحديث نسخة المفضلة المحلية من Trakt في الخلفية.'},
                 art=root_art('trakt'))

    # Parallel art resolve: rows that need a backfill (missing poster /
    # fanart / clearlogo) hit Trakt + TMDb-direct sequentially inside
    # _favorite_row_art. With 30+ favorites this serialises into seconds
    # of empty-poster lag on the first paint. Fan out across 8 workers
    # so the whole list resolves in roughly the time of the slowest
    # single lookup. Local rows that already have all 3 art fields skip
    # the network entirely (same-thread, very fast).
    art_map = {}
    try:
        from concurrent.futures import ThreadPoolExecutor
        def _resolve_one(idx_row):
            idx, row = idx_row
            try:
                return idx, _favorite_row_art(row)
            except Exception:
                return (idx, _favorite_row_art({})) if row else (idx, {})
        with ThreadPoolExecutor(max_workers=8) as pool:
            for idx, art in pool.map(_resolve_one, list(enumerate(rows))):
                art_map[idx] = art
    except Exception as exc:
        xbmc.log('[DexHub] favorites parallel art resolve failed, falling back to serial: %s' % exc, xbmc.LOGWARNING)
        for idx, row in enumerate(rows):
            try:
                art_map[idx] = _favorite_row_art(row)
            except Exception:
                art_map[idx] = {}

    for idx, row in enumerate(rows):
        try:
            media_type = (row.get('media_type') or 'movie').lower()
            canonical = row.get('canonical_id') or ''
            title = row.get('title') or canonical
            year = int(row.get('year') or 0)
            display_title = '%s (%d)' % (title, year) if year > 0 else title
            path, path_is_folder = _content_click_path(media_type=media_type, canonical_id=canonical, title=title)
            art = art_map.get(idx) or _favorite_row_art(row)
            info = {
                'title': title,
                'year': year,
                'plot': row.get('plot') or '',
                'mediatype': 'tvshow' if media_type in ('series', 'anime', 'tv', 'show') else 'movie',
            }
            ctx_menu = _build_source_picker_menu(media_type=media_type, canonical_id=canonical, title=title) + [
                ('إزالة من المفضلة', 'RunPlugin(%s)' % build_url(
                    action='fav_remove', media_type=media_type, canonical_id=canonical,
                )),
            ]
            if 'trakt' in (row.get('sources') or []):
                ctx_menu.append(('مزامنة مع Trakt الآن', 'RunPlugin(%s)' % build_url(action='fav_sync_trakt')))
            add_item(display_title, path, is_folder=path_is_folder, info=info, art=art, context_menu=ctx_menu, is_favorite=True)
        except Exception:
            continue
    end_dir(content=content_type, cache=False)


def fav_add(media_type='movie', canonical_id='', title='', poster='', background='', clearlogo='', year='0', plot=''):
    if not canonical_id:
        return
    try:
        favorites_store.add(media_type or 'movie', canonical_id, title or canonical_id,
                            poster=poster or '', background=background or '',
                            clearlogo=clearlogo or '', year=int(year or 0), plot=plot or '',
                            source='local')
        notify('تمت الإضافة إلى المفضلة')
    except Exception as exc:
        error('تعذّر الإضافة: %s' % exc)
    xbmc.executebuiltin('Container.Refresh')


def fav_remove(media_type='', canonical_id=''):
    if not canonical_id:
        return
    try:
        favorites_store.remove(media_type or '', canonical_id)
        notify('تمت الإزالة من المفضلة')
    except Exception as exc:
        error('تعذّر الإزالة: %s' % exc)
    xbmc.executebuiltin('Container.Refresh')


def fav_sync_trakt():
    try:
        _refresh_trakt_favorites_mirror()
        notify('تمت مزامنة المفضلة مع Trakt')
    except Exception as exc:
        error('فشل المزامنة: %s' % exc)
    xbmc.executebuiltin('Container.Refresh')


# ─── DexWorld Pro mandatory folders (Issue #5) ──────────────────────────

def _provider_is_dexworld_pro(provider):
    """True if this provider is the DexWorld Pro IPTV/catalog backend.

    Detection is loose on purpose so user-renamed installs still match.
    """
    if not provider:
        return False
    haystack = ' '.join([
        str(provider.get('name') or ''),
        str(provider.get('id') or ''),
        str(provider.get('manifest_url') or ''),
        str((provider.get('manifest') or {}).get('name') or ''),
        str((provider.get('manifest') or {}).get('id') or ''),
    ]).lower()
    return ('dexworld' in haystack and 'pro' in haystack) or 'dexworld_pro' in haystack or 'dexworld-pro' in haystack


def _force_folders_for_provider(provider):
    """Some providers (DexWorld Pro) ship internal sub-catalogs that should
    ALWAYS be presented as folders, never as a flat list. The setting can
    be flipped off; default is on per the user's request."""
    if not provider:
        return False
    if (ADDON.getSetting('dexworld_force_folders') or 'true').lower() == 'false':
        return False
    return _provider_is_dexworld_pro(provider)


def run():
    params = dict(parse_qsl(sys.argv[2].lstrip('?')))
    action = params.get('action')
    if not action:
        return home()
    if action == 'add_provider':
        return add_provider()
    if action == 'first_run_wizard':
        return first_run_wizard()
    if action == 'dexworld_info':
        return dexworld_info()
    if action == 'providers':
        return providers()
    if action == 'provider_menu':
        return provider_menu(params.get('provider_id'))
    if action == 'refresh_provider':
        return refresh_provider(params.get('provider_id'))
    if action == 'remove_provider':
        return remove_provider(params.get('provider_id'))
    if action == 'catalog':
        return catalog(params.get('provider_id'), params.get('media_type'), params.get('catalog_id'), params.get('label', ''), params.get('page', '0'), genre=params.get('genre', ''), year=params.get('year', ''), force_remote=params.get('force_remote', ''))
    if action == 'catalog_all':
        return catalog_all(params.get('provider_id'), params.get('media_type'), params.get('catalog_id'), params.get('label', ''), params.get('page', '0'), params.get('genre', ''), params.get('year', ''), params.get('force_remote', ''))
    if action == 'catalog_extra':
        return catalog_extra(params.get('provider_id'), params.get('media_type'), params.get('catalog_id'), params.get('label', ''), params.get('page', '0'), extra_name=params.get('extra_name', ''), extra_value=params.get('extra_value', ''), force_remote=params.get('force_remote', ''))
    if action == 'filters_menu':
        return filters_menu(params.get('provider_id'), params.get('media_type'), params.get('catalog_id'), params.get('force_remote', ''))
    if action == 'select_filter':
        return select_filter(params.get('provider_id'), params.get('media_type'), params.get('catalog_id'), params.get('filter_name'), params.get('force_remote', ''))
    if action == 'clear_filters':
        return clear_filters(params.get('provider_id'), params.get('media_type'), params.get('catalog_id'), params.get('force_remote', ''))
    if action == 'search':
        return search(params.get('media_type', 'movie'), params.get('provider_id'))
    if action == 'streams':
        return streams(params.get('media_type', 'movie'), params.get('canonical_id', ''), params.get('title', ''), resume_seconds=params.get('resume_seconds', '0'), resume_percent=params.get('resume_percent', ''), preferred_provider_name=params.get('preferred_provider_name', ''), source_provider_id=params.get('source_provider_id', ''))
    if action == 'series_meta':
        return series_meta(params.get('media_type', 'series'), params.get('canonical_id', ''), params.get('title', ''), source_provider_id=params.get('source_provider_id', ''))
    if action == 'item_open':
        return item_open(params.get('media_type', 'movie'), params.get('canonical_id', ''), params.get('title', ''), tmdb_id=params.get('tmdb_id', ''), imdb_id=params.get('imdb_id', ''), tvdb_id=params.get('tvdb_id', ''), source_provider_id=params.get('source_provider_id', ''))
    if action == 'play_item':
        return play_item(media_type=params.get('media_type', 'movie'), canonical_id=params.get('canonical_id', ''), title=params.get('title', ''), video_id=params.get('video_id', ''), season=params.get('season', ''), episode=params.get('episode', ''), resume_seconds=params.get('resume_seconds', '0'), preferred_provider_name=params.get('preferred_provider_name', ''), tmdb_id=params.get('tmdb_id', ''), imdb_id=params.get('imdb_id', ''), tvdb_id=params.get('tvdb_id', ''), source_provider_id=params.get('source_provider_id', ''))
    if action == 'season':
        return season(params.get('canonical_id', ''), params.get('season', 1), params.get('title', ''), params.get('media_type', ''))
    if action == 'episode_streams':
        return episode_streams(params.get('canonical_id', ''), params.get('video_id', ''), params.get('season', 1), params.get('episode', 1), params.get('title', ''), params.get('media_type', ''), resume_seconds=params.get('resume_seconds', '0'), resume_percent=params.get('resume_percent', ''), preferred_provider_name=params.get('preferred_provider_name', ''), source_provider_id=params.get('source_provider_id', ''))
    if action == 'continue':
        return continue_watching(page=params.get('page', '0'))
    if action == 'cw_resume':
        return cw_resume(media_type=params.get('media_type', ''), canonical_id=params.get('canonical_id', ''), video_id=params.get('video_id', ''), season=params.get('season', ''), episode=params.get('episode', ''), title=params.get('title', ''), position=params.get('position', '0'), resume_percent=params.get('resume_percent', ''), provider_name=params.get('provider_name', ''), direct=params.get('direct', '0'), source_provider_id=params.get('source_provider_id', ''))
    if action == 'cw_play_from_start':
        return cw_play_from_start(media_type=params.get('media_type', ''), canonical_id=params.get('canonical_id', ''), video_id=params.get('video_id', ''), season=params.get('season', ''), episode=params.get('episode', ''), title=params.get('title', ''), provider_name=params.get('provider_name', ''))
    if action == 'cw_remove':
        return cw_remove(media_type=params.get('media_type', ''), canonical_id=params.get('canonical_id', ''), video_id=params.get('video_id', ''))
    if action == 'cw_mark_watched':
        return cw_mark_watched(media_type=params.get('media_type', ''), canonical_id=params.get('canonical_id', ''), video_id=params.get('video_id', ''))
    if action == 'collection_sets':
        return collection_sets()
    if action == 'collection_set_add':
        return collection_set_add()
    if action == 'collection_set_browse':
        return collection_set_browse(set_id=params.get('set_id', ''))
    if action == 'collection_set_refresh':
        return collection_set_refresh(set_id=params.get('set_id', ''))
    if action == 'collection_set_export':
        return collection_set_export(set_id=params.get('set_id', ''))
    if action == 'collection_set_import_backup':
        return collection_set_import_backup()
    if action == 'collection_set_remove':
        return collection_set_remove(set_id=params.get('set_id', ''))
    if action == 'collection_set_rename':
        return collection_set_rename(set_id=params.get('set_id', ''))
    if action == 'collection_set_create_empty':
        return collection_set_create_empty()
    if action == 'collection_entry_edit_bg':
        return collection_entry_edit_bg(set_id=params.get('set_id', ''), entry_id=params.get('entry_id', ''))
    if action == 'collection_entry_toggle_open_mode':
        return collection_entry_toggle_open_mode(set_id=params.get('set_id', ''), entry_id=params.get('entry_id', ''))
    if action == 'collection_entry_edit_name':
        return collection_entry_edit_name(set_id=params.get('set_id', ''), entry_id=params.get('entry_id', ''))
    if action == 'collection_entry_meta_source':
        return collection_entry_meta_source(set_id=params.get('set_id', ''), entry_id=params.get('entry_id', ''))
    if action == 'collection_entry_toggle_layout':
        return collection_entry_toggle_layout(set_id=params.get('set_id', ''), entry_id=params.get('entry_id', ''))
    if action == 'collection_entry_edit_source':
        return collection_entry_edit_source(set_id=params.get('set_id', ''), entry_id=params.get('entry_id', ''))
    if action == 'collection_entry_remove':
        return collection_entry_remove(set_id=params.get('set_id', ''), entry_id=params.get('entry_id', ''))
    if action == 'collection_entry_add':
        return collection_entry_add(set_id=params.get('set_id', ''))
    if action == 'collection_entry_open':
        return collection_entry_open(set_id=params.get('set_id', ''), entry_id=params.get('entry_id', ''))
    if action == 'trakt_list_browse':
        return trakt_list_browse(username=params.get('username', ''), slug=params.get('slug', ''), title=params.get('title', ''), background=params.get('background', ''), media_filter=params.get('media_filter', 'auto'), page=params.get('page', '0'), force_remote=params.get('force_remote', ''))
    if action == 'mdblist_list_browse':
        return mdblist_list_browse(username=params.get('username', ''), slug=params.get('slug', ''), title=params.get('title', ''), background=params.get('background', ''), media_filter=params.get('media_filter', 'auto'), cursor=params.get('cursor', ''), force_remote=params.get('force_remote', ''))
    if action == 'kodi_route_browse':
        return kodi_route_browse(route=params.get('route', ''), title=params.get('title', ''), background=params.get('background', ''), page=params.get('page', '0'))
    if action == 'trakt_menu':
        return trakt_menu()
    if action == 'integrations_menu':
        return integrations_menu()
    if action == 'clear_cache':
        return clear_cache()
    if action == 'formatter_refresh':
        return formatter_refresh()
    if action == 'open_settings':
        return open_settings_action()
    if action == 'meta_sources_menu':
        return meta_sources_menu()
    if action == 'meta_pick_for_provider':
        return meta_pick_for_provider(provider_id=params.get('provider_id', ''))
    if action == 'meta_pick_target':
        return _meta_pick_target(params.get('target_key', ''), params.get('title', ''))
    if action == 'meta_sources_dialog':
        return meta_sources_dialog()
    if action == 'meta_reset_all':
        return meta_reset_all()
    if action == 'trakt_auth':
        return trakt_auth()
    if action == 'trakt_logout':
        return trakt_logout()
    if action == 'trakt_settings':
        return trakt_settings()
    if action == 'trakt_import':
        return trakt_import()
    if action == 'choose_player':
        return choose_player(media_type=params.get('media_type', 'movie'), canonical_id=params.get('canonical_id', ''), title=params.get('title', ''), tmdb_id=params.get('tmdb_id', ''), imdb_id=params.get('imdb_id', ''), tvdb_id=params.get('tvdb_id', ''), season=params.get('season', ''), episode=params.get('episode', ''), video_id=params.get('video_id', ''), source_provider_id=params.get('source_provider_id', ''))
    if action == 'tmdb_player':
        return tmdb_player(video_type=params.get('video_type', 'movie'), tmdb_id=params.get('tmdb_id', ''), imdb_id=params.get('imdb_id', ''), tvdb_id=params.get('tvdb_id', ''), title=params.get('title', ''), year=params.get('year', ''), showname=params.get('showname', ''), season=params.get('season', ''), episode=params.get('episode', ''))
    if action == 'tmdbh_install':
        return tmdbh_install()
    if action == 'tmdbh_uninstall':
        return tmdbh_uninstall()
    if action == 'play':
        return play(params.get('stream_key', ''), resume_seconds=params.get('resume_seconds', ''), resume_percent=params.get('resume_percent', ''))
    if action == 'nextup':
        return nextup()
    if action == 'favorites':
        return favorites()
    if action == 'fav_add':
        return fav_add(media_type=params.get('media_type', 'movie'), canonical_id=params.get('canonical_id', ''),
                       title=params.get('title', ''), poster=params.get('poster', ''),
                       background=params.get('background', ''), clearlogo=params.get('clearlogo', ''),
                       year=params.get('year', '0'), plot=params.get('plot', ''))
    if action == 'fav_remove':
        return fav_remove(media_type=params.get('media_type', ''), canonical_id=params.get('canonical_id', ''))
    if action == 'fav_sync_trakt':
        return fav_sync_trakt()
    return home()
