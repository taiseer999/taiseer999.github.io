# -*- coding: utf-8 -*-
"""1.4.4: TMDb details for IMDb-only items (the FEL catalog).

The bundled catalog has English plot/genres, year and runtime only, so skins
(AF3 info bar) had no MPAA, release date or TMDb id and showed English text
under an Arabic UI. This fills them from TMDb in Kodi's language:
localized title / plot / genres, release date, certification (the language's
country first, then US - TMDb has almost no Saudi certificates), studio and
the TMDb id. Results are cached in the profile (30 days); uncached titles are
fetched in parallel, at most MAX_NEW per listing, so a first listing stays
quick and the rest fill in on the next refresh.
"""
import json
import os
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import xbmc

from . import kodi

CACHE_FILE = os.path.join(kodi.PROFILE, 'tmdb_meta.json')
TTL = 30 * 86400
MAX_NEW = 100
WORKERS = 12
_KEY = 'edde6b5e41246ab79a2697cd125e1781'      # public default key (same as Umbrella / AB Tools)
_lock = threading.Lock()


def _language():
    code = (xbmc.getLanguage(xbmc.ISO_639_1) or 'en').lower()[:2]
    return {'ar': 'ar-SA', 'en': 'en-US', 'pt': 'pt-BR', 'zh': 'zh-CN'}.get(code, code)


def _key():
    try:
        import xbmcaddon
        k = xbmcaddon.Addon('plugin.video.themoviedb.helper').getSetting('tmdb_apikey')
        if k and len(k) >= 30:
            return k
    except Exception:
        pass
    return _KEY


def _get(path, key, lang):
    url = 'https://api.themoviedb.org/3/%s%sapi_key=%s&language=%s' % (path, '&' if '?' in path else '?', key, lang)
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode('utf-8'))


def _cert(details, country):
    rows = (details.get('release_dates') or {}).get('results') or []
    for want in (country, 'US'):
        for row in rows:
            if row.get('iso_3166_1') != want:
                continue
            dates = sorted(row.get('release_dates') or [], key=lambda d: (d.get('type') != 3, d.get('type') or 9))
            for d in dates:
                c = (d.get('certification') or '').strip()
                if c:
                    return c
    return ''


def _fetch(imdb, key, lang):
    found = _get('find/%s?external_source=imdb_id' % imdb, key, lang)
    res = found.get('movie_results') or []
    if not res:
        return {'tmdb_id': '', 'ts': time.time(), 'lang': lang}
    tid = res[0].get('id')
    d = _get('movie/%s?append_to_response=release_dates' % tid, key, lang)
    studios = [c.get('name') for c in d.get('production_companies') or [] if c.get('name')]
    return {
        'tmdb_id': str(tid), 'lang': lang, 'ts': time.time(),
        'title': d.get('title') or '', 'plot': d.get('overview') or '',
        'genres': [g.get('name') for g in d.get('genres') or [] if g.get('name')],
        'released': d.get('release_date') or '',
        'mpaa': _cert(d, lang.split('-')[-1].upper() if '-' in lang else 'US'),
        'studio': studios[:1],
        'tagline': d.get('tagline') or '',
    }


def _load():
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(data):
    try:
        kodi.ensure_dir(kodi.PROFILE)
        tmp = CACHE_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, CACHE_FILE)
    except OSError as e:
        kodi.log('tmdb_meta cache write failed: %s' % e)


def lookup(imdb_ids):
    """{imdb: details} for the given ids (in display order); fetches what is
    missing or stale. Never raises - a failed title just has no entry."""
    lang = _language()
    now = time.time()
    cache = _load()

    def fresh(e):
        return e and e.get('lang') == lang and now - e.get('ts', 0) < TTL

    want = [i for i in dict.fromkeys(imdb_ids) if i and str(i).startswith('tt')]
    missing = [i for i in want if not fresh(cache.get(i))][:MAX_NEW]
    if missing:
        key = _key()
        got = {}

        def work(imdb):
            try:
                r = _fetch(imdb, key, lang)
                with _lock:
                    got[imdb] = r
            except Exception as e:
                kodi.debug('tmdb_meta %s: %s' % (imdb, e))

        t0 = time.time()
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:   # joined before return (no stray threads)
            list(pool.map(work, missing))
        cache.update(got)
        if got:
            _save(cache)
        kodi.log('tmdb_meta: %d/%d fetched (%s) in %.1fs' % (len(got), len(missing), lang, time.time() - t0))
    return {i: cache[i] for i in want if cache.get(i) and cache[i].get('tmdb_id')}


def apply(meta, info):
    """Merge TMDb details into a Stremio-shaped meta (localized text wins,
    the catalog's English stays as fallback)."""
    if not info:
        return meta
    if info.get('title'):
        meta['original_name'] = meta.get('name')
        meta['name'] = info['title']
    if info.get('plot'):
        meta['description'] = info['plot']
    if info.get('genres'):
        meta['genres'] = info['genres']
    if info.get('released'):
        meta['released'] = info['released']
    for k in ('mpaa', 'tmdb_id', 'studio', 'tagline'):
        if info.get(k):
            meta[k] = info[k]
    return meta
