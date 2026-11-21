# -*- coding: utf-8 -*-
"""SubDL — https://subdl.com (free API key from your SubDL account)."""
from ..media import is_arabic_code
from ..common import http, setting

API = 'https://api.subdl.com/api/v1/subtitles'
DL = 'https://dl.subdl.com'
LANG = {'ar': 'AR', 'en': 'EN'}


def available():
    return bool(setting('subdl_key')) and setting('use_subdl', 'true') == 'true'


def search(video, langs):
    key = setting('subdl_key')
    params = {
        'api_key': key,
        'languages': ','.join(LANG[l] for l in langs if l in LANG),
        'subs_per_page': 30,
        'releases': 1,
    }
    if video['is_episode']:
        params['type'] = 'tv'
        params['season_number'] = video['season']
        params['episode_number'] = video['episode']
        if video.get('show_imdb'):
            params['imdb_id'] = video['show_imdb']
        elif video.get('show_tmdb'):
            params['tmdb_id'] = video['show_tmdb']
        else:
            params['film_name'] = video['tvshow']
    else:
        params['type'] = 'movie'
        if video.get('imdb'):
            params['imdb_id'] = video['imdb']
        elif video.get('tmdb'):
            params['tmdb_id'] = video['tmdb']
        else:
            params['film_name'] = video['title']
            if video.get('year'):
                params['year'] = video['year']
    data = http(API, params=params, timeout=25)
    if not data.get('status') and params.get('imdb_id'):
        # retry with name (some titles miss ids on subdl)
        params.pop('imdb_id', None)
        params['film_name'] = video['tvshow'] if video['is_episode'] else video['title']
        data = http(API, params=params, timeout=25)
    out = []
    for s in data.get('subtitles') or []:
        lang = (s.get('lang') or s.get('language') or '').lower()
        lang = 'ar' if is_arabic_code(lang) else 'en' if lang.startswith('en') else lang
        if lang not in langs:
            continue
        url = s.get('url') or ''
        if not url:
            continue
        out.append({
            'provider': 'subdl',
            'id': url,
            'lang': lang,
            'release': s.get('release_name') or s.get('name') or '',
            'releases': s.get('releases') or [s.get('release_name') or ''],
            'hi': bool(s.get('hi')),
            'hash_match': False,
            'episode': s.get('episode') if not s.get('full_season') else '',
            'author': s.get('author') or '',
        })
    return out


def download(item):
    url = item['id']
    if url.startswith('http'):
        if not url.startswith(DL + '/'):
            raise Exception('رابط تنزيل غير معروف')
    else:
        url = DL + (url if url.startswith('/') else '/' + url)
    return http(url, raw=True, timeout=40, retries=2)
