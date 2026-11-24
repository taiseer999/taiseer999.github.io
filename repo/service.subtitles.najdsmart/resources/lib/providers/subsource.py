# -*- coding: utf-8 -*-
"""SubSource — https://subsource.net (API key from the API tab of your account)."""
from ..common import http, setting

BASE = 'https://api.subsource.net/api/v1'
LANG = {'ar': 'arabic', 'en': 'english', 'fr': 'french', 'es': 'spanish', 'de': 'german', 'it': 'italian',
        'pt': 'portuguese', 'tr': 'turkish', 'ru': 'russian', 'ja': 'japanese', 'ko': 'korean',
        'zh': 'chinese'}
REV = {v: k for k, v in LANG.items()}


def available():
    return bool(setting('subsource_key')) and setting('use_subsource', 'true') == 'true'


def _h():
    return {'X-API-Key': setting('subsource_key'), 'Accept': 'application/json'}


def _find_title(video):
    season = video['season'] if video['is_episode'] else ''
    imdb = video.get('show_imdb') if video['is_episode'] else video.get('imdb')
    name = video['tvshow'] if video['is_episode'] else video['title']
    results = []
    if imdb:
        results = http(BASE + '/movies/search',
                       params={'searchType': 'imdb', 'imdb': imdb, 'season': season},
                       headers=_h(), timeout=25).get('data') or []
    if not results and name:
        results = http(BASE + '/movies/search',
                       params={'searchType': 'text', 'q': name.lower(), 'season': season},
                       headers=_h(), timeout=25).get('data') or []
    if not results:
        return None
    year = str(video.get('year') or '')
    lname = (name or '').lower()

    def rank(r):
        s = 0
        if (r.get('title') or '').lower() == lname or (r.get('alternateTitle') or '').lower() == lname:
            s += 2
        if year and not video['is_episode'] and str(r.get('releaseYear')) == year:
            s += 2
        if season and str(r.get('season')) == str(season):
            s += 3
        return s
    results.sort(key=rank, reverse=True)
    return results[0].get('movieId')


def search(video, langs):
    mid = _find_title(video)
    if not mid:
        return []
    out = []
    for lang in langs:
        if lang not in LANG:
            continue
        params = [('language', LANG[lang]), ('limit', 100), ('movieId', mid)]
        if video['is_episode']:
            params += [('seasonNumber', video['season']), ('episodeNumber', video['episode'])]
        data = http(BASE + '/subtitles', params=params, headers=_h(), timeout=25)
        for s in data.get('data') or []:
            rel = s.get('releaseInfo') or []
            if isinstance(rel, str):
                rel = [rel]
            out.append({
                'provider': 'subsource',
                'id': str(s.get('subtitleId')),
                'lang': REV.get((s.get('language') or '').lower(), lang),
                'release': rel[0] if rel else '',
                'releases': rel,
                'hi': bool(s.get('hearingImpaired')),
                'hash_match': False,
                'episode': '',
                'downloads': s.get('downloads', 0) or 0,
            })
    return out


def download(item):
    return http(BASE + '/subtitles/%s/download' % item['id'], headers=_h(),
                raw=True, timeout=40, retries=2)
