# -*- coding: utf-8 -*-
"""OpenSubtitles.com REST API (needs a free consumer API key; login raises the daily quota)."""
import json

from ..common import http, setting, cache_get, cache_put, HttpError, log

BASE = 'https://api.opensubtitles.com/api/v1'


def available():
    return bool(setting('os_key')) and setting('use_opensubtitles', 'true') == 'true'


def _headers(with_token=False):
    h = {'Api-Key': setting('os_key'), 'Accept': 'application/json'}
    if with_token:
        tok = _token()
        if tok:
            h['Authorization'] = 'Bearer ' + tok['token']
    return h


def _token(force=False):
    user, pwd = setting('os_user'), setting('os_pass')
    if not user or not pwd:
        return None
    if not force:
        c = cache_get('os_token.json', 12 * 3600)
        if c:
            return json.loads(c.decode('utf-8'))
    try:
        r = http(BASE + '/login', json_body={'username': user, 'password': pwd},
                 headers={'Api-Key': setting('os_key'), 'Accept': 'application/json'})
        tok = {'token': r['token'], 'base': r.get('base_url') or 'api.opensubtitles.com'}
        cache_put('os_token.json', json.dumps(tok))
        return tok
    except Exception as e:
        log('opensubtitles login failed: %s' % e)
        return None


def _imdb_num(x):
    return str(int(x[2:])) if x and x.startswith('tt') and x[2:].isdigit() else ''


def search(video, langs):
    params = [('languages', ','.join(sorted(langs)))]
    if video.get('hash'):
        params.append(('moviehash', video['hash']))
    if video['is_episode']:
        params += [('season_number', video['season']), ('episode_number', video['episode'])]
        if video.get('show_imdb'):
            params.append(('parent_imdb_id', _imdb_num(video['show_imdb'])))
        elif video.get('imdb'):
            params.append(('imdb_id', _imdb_num(video['imdb'])))
        else:
            params.append(('query', video['tvshow'].lower()))
    else:
        if video.get('imdb'):
            params.append(('imdb_id', _imdb_num(video['imdb'])))
        elif video.get('tmdb'):
            params.append(('tmdb_id', video['tmdb']))
        else:
            params.append(('query', video['title'].lower()))
            if video.get('year'):
                params.append(('year', video['year']))
    params = sorted([(k, str(v)) for k, v in params if v not in (None, '')])
    data = http(BASE + '/subtitles', params=params, headers=_headers(), timeout=25)
    out = []
    for d in data.get('data') or []:
        a = d.get('attributes') or {}
        files = a.get('files') or []
        if not files:
            continue
        lang = (a.get('language') or '').lower()[:2]
        if lang not in langs:
            continue
        fd = a.get('feature_details') or {}
        out.append({
            'provider': 'opensubtitles',
            'id': str(files[0]['file_id']),
            'lang': lang,
            'release': a.get('release') or files[0].get('file_name') or '',
            'hi': bool(a.get('hearing_impaired')),
            'hash_match': bool(a.get('moviehash_match')),
            'episode': fd.get('episode_number', ''),
            'downloads': a.get('download_count', 0),
            'ai': bool(a.get('ai_translated') or a.get('machine_translated')),
        })
    return out


def download(item):
    tok = _token()
    base = 'https://' + (tok['base'] if tok else 'api.opensubtitles.com') + '/api/v1'
    try:
        r = http(base + '/download', json_body={'file_id': int(item['id']), 'sub_format': 'srt'},
                 headers=_headers(with_token=True), timeout=30)
    except HttpError as e:
        if e.code == 401 and tok:
            _token(force=True)
            r = http(BASE + '/download', json_body={'file_id': int(item['id']), 'sub_format': 'srt'},
                     headers=_headers(with_token=True), timeout=30)
        elif e.code in (406, 429):
            raise Exception('quota')
        else:
            raise
    link = r.get('link')
    if not link:
        raise Exception('no link: %s' % r.get('message'))
    return http(link, raw=True, timeout=40, retries=2)
