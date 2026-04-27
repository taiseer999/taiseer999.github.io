# -*- coding: utf-8 -*-
import json
import os
import sqlite3
import time
import urllib.parse
import urllib.request

import xbmc
import xbmcaddon

from .dexhub.common import profile_path

ADDON = xbmcaddon.Addon()
API_BASE = 'https://api.themoviedb.org/3'
# Bug fix: previously every image (poster, fanart, clearlogo) was fetched at
# /t/p/original, returning 2000+px / 500KB-2MB files for thumbnail-sized
# display slots. The user reported: "tmdb posters downloaded with Plex full
# resolution — please make smaller". TMDb's CDN serves correctly-sized
# variants for free, so we now request appropriate widths per image kind.
# Reference sizes per TMDb docs: posters w185/w342/w500/w780, backdrops
# w300/w780/w1280, logos w92/w154/w300/w500.
IMAGE_BASE_POSTER = 'https://image.tmdb.org/t/p/w500'      # ~70 KB per item
IMAGE_BASE_BACKDROP = 'https://image.tmdb.org/t/p/w1280'   # ~200 KB per item
IMAGE_BASE_LOGO = 'https://image.tmdb.org/t/p/w500'        # logos are small
# Kept for backwards compatibility — used only if a caller passes raw paths
# without specifying a kind.
IMAGE_BASE = IMAGE_BASE_POSTER
CACHE_DB = os.path.join(profile_path(), 'tmdb_direct_cache.sqlite')
POSITIVE_TTL = 30 * 24 * 60 * 60
NEGATIVE_TTL = 6 * 60 * 60
DEFAULT_API_KEY = ''

# In-memory cache (per Python invocation) so a single catalog render doesn't
# reopen sqlite N times for the same items. Bounded to 512 entries with a
# simple FIFO eviction.
_MEM_CACHE = {}
_MEM_CACHE_ORDER = []
_MEM_CACHE_MAX = 512


def _mem_get(key):
    return _MEM_CACHE.get(key)


def _mem_put(key, value):
    if key in _MEM_CACHE:
        return
    _MEM_CACHE[key] = value
    _MEM_CACHE_ORDER.append(key)
    if len(_MEM_CACHE_ORDER) > _MEM_CACHE_MAX:
        old = _MEM_CACHE_ORDER.pop(0)
        _MEM_CACHE.pop(old, None)


def _setting(key, default=''):
    try:
        return ADDON.getSetting(key) or default
    except Exception:
        return default


def _api_key():
    return (_setting('tmdb_api_key', '').strip() or DEFAULT_API_KEY).strip()


def _timeout():
    try:
        return max(4, int(_setting('timeout', '20') or '20'))
    except Exception:
        return 12


def _normalize_media_type(media_type):
    value = str(media_type or 'movie').strip().lower()
    if value in ('tvshow', 'episode', 'season', 'series', 'show', 'tv', 'anime'):
        return 'tv'
    return 'movie'


def _preferred_image_languages():
    raw = (_setting('preferred_subtitle_langs', 'ar,en') or 'ar,en').strip()
    langs = [x.strip().lower().replace('_', '-') for x in raw.split(',') if x.strip()]
    out = []
    # Artwork looks cleaner and clearer in English more often than localized variants.
    # Prefer English assets first, then honor the user language list, then language-neutral.
    for lang in ['en'] + langs + ['null', '']:
        if lang not in out:
            out.append(lang)
    return out or ['en', 'null', '']


def _db_conn():
    os.makedirs(os.path.dirname(CACHE_DB), exist_ok=True)
    conn = sqlite3.connect(CACHE_DB)
    conn.execute(
        'CREATE TABLE IF NOT EXISTS art_cache ('
        ' cache_key TEXT PRIMARY KEY,'
        ' expires_at INTEGER NOT NULL,'
        ' payload TEXT NOT NULL'
        ')'
    )
    return conn


def _cache_get(cache_key):
    # In-memory first (fast path; avoids opening sqlite for repeated items in
    # the same render).
    cached = _mem_get(cache_key)
    if cached is not None:
        return cached
    try:
        conn = _db_conn()
        row = conn.execute('SELECT expires_at, payload FROM art_cache WHERE cache_key=?', (cache_key,)).fetchone()
        if not row:
            conn.close()
            return None
        expires_at, payload = row
        if int(expires_at or 0) < int(time.time()):
            conn.execute('DELETE FROM art_cache WHERE cache_key=?', (cache_key,))
            conn.commit()
            conn.close()
            return None
        conn.close()
        result = json.loads(payload or '{}')
        _mem_put(cache_key, result)
        return result
    except Exception:
        return None


def _cache_set(cache_key, payload, ttl):
    _mem_put(cache_key, payload or {})
    try:
        conn = _db_conn()
        conn.execute(
            'INSERT OR REPLACE INTO art_cache(cache_key, expires_at, payload) VALUES (?, ?, ?)',
            (cache_key, int(time.time() + max(60, int(ttl or NEGATIVE_TTL))), json.dumps(payload or {}, ensure_ascii=False))
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _request(path, params=None):
    api_key = _api_key()
    if not api_key:
        return {}
    query = dict(params or {})
    query['api_key'] = api_key
    url = API_BASE + path + ('?' + urllib.parse.urlencode(query) if query else '')
    req = urllib.request.Request(url, headers={
        'Accept': 'application/json',
        'User-Agent': 'DexHub/3.3.0 (Kodi)',
    })
    with urllib.request.urlopen(req, timeout=_timeout()) as resp:
        body = resp.read().decode('utf-8', 'ignore')
        return json.loads(body) if body else {}


def _image_url(file_path, kind='poster'):
    """Build a TMDb image URL with the appropriate size for `kind`.

    `kind` is one of: 'poster', 'backdrop', 'logo'. We pick a size that's
    large enough for any reasonable display slot in Kodi while keeping
    bandwidth (and the user's Plex download path through Kodi's image
    cache) modest.
    """
    file_path = str(file_path or '').strip()
    if not file_path:
        return ''
    if file_path.startswith('http://') or file_path.startswith('https://'):
        return file_path
    if kind == 'backdrop':
        return IMAGE_BASE_BACKDROP + file_path
    if kind == 'logo':
        return IMAGE_BASE_LOGO + file_path
    return IMAGE_BASE_POSTER + file_path


def _best_image(rows, langs):
    rows = rows or []
    langs = langs or ['en', 'null', '']

    def _lang_rank(row):
        iso = str((row or {}).get('iso_639_1') or '').strip().lower()
        iso_short = iso.split('-')[0] if iso else ''
        for idx, lang in enumerate(langs):
            target = str(lang or '').strip().lower()
            target_short = target.split('-')[0] if target else ''
            if iso == target or (iso_short and target_short and iso_short == target_short):
                return idx
        if not iso:
            return len(langs) + 1
        return len(langs) + 10

    ranked = sorted(
        rows,
        key=lambda row: (
            _lang_rank(row),
            -float((row or {}).get('vote_average') or 0.0),
            -int((row or {}).get('width') or 0),
            -int((row or {}).get('height') or 0),
            -float((row or {}).get('vote_count') or 0.0),
        )
    )
    return ranked[0] if ranked else {}


def _resolve_tmdb_from_imdb(imdb_id, media_type):
    imdb_id = str(imdb_id or '').strip()
    if not imdb_id:
        return ''
    try:
        data = _request('/find/%s' % urllib.parse.quote(imdb_id), {'external_source': 'imdb_id'}) or {}
    except Exception as exc:
        xbmc.log('[DexHub] tmdb_direct imdb lookup failed: %s' % exc, xbmc.LOGDEBUG)
        return ''
    mt = _normalize_media_type(media_type)
    bucket = 'tv_results' if mt == 'tv' else 'movie_results'
    rows = data.get(bucket) or []
    if rows:
        return str(rows[0].get('id') or '')
    return ''


def _resolve_tmdb_from_search(title, year, media_type):
    title = str(title or '').strip()
    if not title:
        return ''
    mt = _normalize_media_type(media_type)
    params = {'query': title}
    year = str(year or '').strip()
    if year.isdigit():
        if mt == 'movie':
            params['year'] = year
        else:
            params['first_air_date_year'] = year
    try:
        data = _request('/search/%s' % mt, params) or {}
    except Exception as exc:
        xbmc.log('[DexHub] tmdb_direct search failed: %s' % exc, xbmc.LOGDEBUG)
        return ''
    rows = data.get('results') or []
    if not rows:
        return ''
    return str(rows[0].get('id') or '')


def _resolve_tmdb_id(tmdb_id='', imdb_id='', media_type='movie', title='', year=''):
    tmdb_id = str(tmdb_id or '').strip()
    if tmdb_id.isdigit():
        return tmdb_id
    imdb_id = str(imdb_id or '').strip()
    if imdb_id:
        resolved = _resolve_tmdb_from_imdb(imdb_id, media_type)
        if resolved:
            return resolved
    return _resolve_tmdb_from_search(title, year, media_type)


def art_for(tmdb_id='', imdb_id='', media_type='movie', title='', year=''):
    mt = _normalize_media_type(media_type)
    cache_key = 'art:%s:%s:%s:%s:%s' % (mt, tmdb_id or '', imdb_id or '', title or '', year or '')
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    if not _api_key():
        return {}

    resolved_tmdb = _resolve_tmdb_id(tmdb_id=tmdb_id, imdb_id=imdb_id, media_type=mt, title=title, year=year)
    if not resolved_tmdb:
        out = {}
        _cache_set(cache_key, out, NEGATIVE_TTL)
        return out

    langs = _preferred_image_languages()
    try:
        images = _request('/%s/%s/images' % (mt, resolved_tmdb), {
            'include_image_language': ','.join([x for x in langs if x and x != 'null'] + ['null'])
        }) or {}
    except Exception as exc:
        xbmc.log('[DexHub] tmdb_direct images failed: %s' % exc, xbmc.LOGDEBUG)
        images = {}

    try:
        ext = _request('/%s/%s/external_ids' % (mt, resolved_tmdb)) or {}
    except Exception:
        ext = {}

    poster = _best_image(images.get('posters') or [], langs)
    backdrop = _best_image(images.get('backdrops') or [], langs)
    logo = _best_image(images.get('logos') or [], langs)
    out = {
        'tmdb_id': resolved_tmdb,
        'imdb_id': str(ext.get('imdb_id') or imdb_id or '').strip(),
        'poster': _image_url((poster or {}).get('file_path') or '', kind='poster'),
        'fanart': _image_url((backdrop or {}).get('file_path') or '', kind='backdrop'),
        'landscape': _image_url((backdrop or {}).get('file_path') or '', kind='backdrop'),
        'clearlogo': _image_url((logo or {}).get('file_path') or '', kind='logo'),
    }
    ttl = POSITIVE_TTL if any(out.get(k) for k in ('poster', 'fanart', 'clearlogo')) else NEGATIVE_TTL
    _cache_set(cache_key, out, ttl)
    return out
