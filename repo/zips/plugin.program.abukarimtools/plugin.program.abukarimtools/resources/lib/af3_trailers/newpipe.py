# -*- coding: utf-8 -*-
"""YouTube trailers through NewPipe for the AF3 auto-trailers (ABUKARIM TOOLS).

TEST source (3.2.43~beta1). Instead of IMDb's own MP4s, the title's YouTube
trailer is played through plugin.video.newpipe (no account, no API key - it
resolves the stream locally through ResolveURL/PluginsGR).

Finding the YouTube id, cheapest first:
  1. the focused item's own trailer link (ListItem.Trailer - TMDbHelper fills
     it with plugin://plugin.video.youtube/...video_id=<id>), or the same
     link TMDbHelper publishes on Home for the focused item;
  2. TMDb /videos for the title (TMDbHelper's own API key; an IMDb-only title
     is mapped with /find first). Official YouTube "Trailer" wins, then any
     Trailer, then a Teaser; English and language-less videos only.
Results (ids and misses) are kept in memory for the session.
"""
import json
import re
import threading
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import xbmc

ADDON_ID = 'plugin.video.newpipe'

_YT_ID = r'([A-Za-z0-9_-]{11})'
_YT_PATTERNS = (
    re.compile(r'[?&/]video_id=' + _YT_ID),
    re.compile(r'youtube\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/|v/)' + _YT_ID),
    re.compile(r'youtu\.be/' + _YT_ID),
    re.compile(r'plugin\.video\.newpipe/.*[?&]url=' + _YT_ID),
)

_CACHE = {}            # key -> youtube id ('' = none)
_LOCK = threading.Lock()


def installed():
    return xbmc.getCondVisibility('System.HasAddon(%s) + System.AddonIsEnabled(%s)'
                                  % (ADDON_ID, ADDON_ID))


def youtube_id(text):
    text = str(text or '')
    for pattern in _YT_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return ''


def plugin_url(video_id, title=''):
    """NewPipe's own play route (the same one its listings use)."""
    return 'plugin://%s/?%s' % (ADDON_ID, urlencode(
        {'action': 'play', 'url': video_id, 'title': title or ''}))


def _get(url, timeout=6):
    with urlopen(Request(url, headers={'Accept': 'application/json'}), timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8', 'replace')) or {}


def _pick(videos):
    def rank(v):
        kind = v.get('type')
        return (0 if kind == 'Trailer' else 1,
                0 if v.get('official') else 1,
                0 if (v.get('iso_639_1') or 'en') == 'en' else 1,
                -(v.get('size') or 0))
    usable = [v for v in videos or []
              if v.get('site') == 'YouTube' and v.get('type') in ('Trailer', 'Teaser')
              and re.match('^' + _YT_ID + '$', str(v.get('key') or ''))]
    usable.sort(key=rank)
    return usable[0]['key'] if usable else ''


def tmdb_youtube_id(api_key, tmdb_id='', dbtype='movie', imdb_id='', log=None):
    """YouTube trailer id from TMDb, or ''. None = network trouble (not cached)."""
    if not api_key or not (tmdb_id or imdb_id):
        return ''
    kind = 'tv' if dbtype == 'tvshow' else 'movie'
    cache_key = '%s:%s' % (kind, tmdb_id or imdb_id)
    with _LOCK:
        if cache_key in _CACHE:
            return _CACHE[cache_key]
    try:
        if not tmdb_id:
            found = _get('https://api.themoviedb.org/3/find/%s?api_key=%s&external_source=imdb_id'
                         % (quote(imdb_id), api_key))
            hits = found.get('tv_results' if kind == 'tv' else 'movie_results') or []
            if not hits:
                hits = found.get('movie_results') or found.get('tv_results') or []
                if hits and found.get('tv_results') and not found.get('movie_results'):
                    kind = 'tv'
            tmdb_id = str(hits[0].get('id')) if hits else ''
        vid = ''
        if tmdb_id:
            data = _get('https://api.themoviedb.org/3/%s/%s/videos?api_key=%s'
                        '&include_video_language=en,null' % (kind, tmdb_id, api_key))
            vid = _pick(data.get('results'))
    except Exception as exc:
        if log:
            log('TMDb video lookup failed for %s: %s' % (cache_key, type(exc).__name__))
        return None
    with _LOCK:
        _CACHE[cache_key] = vid
    return vid
