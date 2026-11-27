# -*- coding: utf-8 -*-
"""فهرس نجد — the shared index of finished Najd AI translations.

When someone's Najd finishes an AI translation, it is shared here (if they allow it), so the
next person who plays the same film / episode gets it at once — no AI work, no waiting.
The files live in a Telegram channel; a small Cloudflare server keeps the list and serves them.

Only the video's ids (IMDb / TMDb, season, episode), its length, its release name and the
subtitle text are sent. Nothing about the viewer."""
import hashlib
import os
import re
import threading
import time

from ..common import http, log, setting, cache_get, cache_put

BASE = 'https://najd-index.l68802270.workers.dev'
APP_KEY = 'najd_uqNehahsWSSTc78Iw8kh_Dk1kueU6UAJ'     # identifies the add-on, not a secret
LABEL = 'فهرس نجد'


def _h():
    return {'X-Najd-Key': APP_KEY, 'Accept': 'application/json'}


def available():
    return setting('use_index', 'true') == 'true'


def sharing():
    return setting('share_index', 'true') == 'true'


def _int(x):
    try:
        return int(str(x).strip())
    except (ValueError, TypeError):
        return None


def ids(video):
    """{'imdb','tmdb','season','episode'} for the index, or None when the video can't be named.
    Episodes use the SHOW's ids (the same for everyone), films their own."""
    if video.get('is_episode'):
        s, e = _int(video.get('season')), _int(video.get('episode'))
        imdb, tmdb = video.get('show_imdb') or '', video.get('show_tmdb') or ''
        if s is None or e is None:
            return None
        if not imdb and not tmdb:
            # no show ids: the player's own ids for this episode still name it the same way
            # for everyone who plays it from that add-on (a mismatch only means no result)
            imdb, tmdb = video.get('imdb') or '', video.get('tmdb') or ''
    else:
        s = e = None
        imdb, tmdb = video.get('imdb') or '', video.get('tmdb') or ''
    imdb = imdb if re.match(r'^tt\d{5,10}$', imdb or '') else ''
    tmdb = str(tmdb) if re.match(r'^\d{1,9}$', str(tmdb or '')) else ''
    if not imdb and not tmdb:
        return None
    out = {'imdb': imdb, 'tmdb': tmdb}
    if s is not None:
        out['season'], out['episode'] = s, e
    return out


def _duration(video):
    d = 0.0
    try:
        d = float(video.get('duration') or 0)
    except (TypeError, ValueError):
        d = 0.0
    if d <= 0:
        try:
            import xbmc
            p = xbmc.Player()
            if p.isPlayingVideo() and (not video.get('path') or p.getPlayingFile() == video.get('path')):
                d = float(p.getTotalTime() or 0)
        except Exception:
            pass
    return round(d, 1) if d > 0 else None


def search(video, langs):
    if 'ar' not in langs:
        return []
    q = ids(video)
    if not q:
        log('index: no IMDb/TMDb id for this video — skipped')
        return []
    params = dict(q)
    dur = _duration(video)
    if dur:
        params['duration'] = dur
    data = http(BASE + '/v1/find', params=params, headers=_h(), timeout=12)
    out = []
    for r in (data or {}).get('results') or []:
        rid = _int(r.get('id'))
        if rid is None:
            continue
        diff = r.get('diff')
        bonus = 10.0                     # a finished Najd translation of this very episode / film
        if diff is not None:             # same length as this video: made from the same release
            bonus += 25 if diff <= 2 else 8 if diff <= 30 else 0
        rel = r.get('release') or ''
        out.append({
            'provider': 'najdindex',
            'id': str(rid),
            'lang': 'ar',
            'release': rel or 'ترجمة نجد',
            'releases': [rel] if rel else [],
            'hi': False,
            'hash_match': False,
            'episode': q.get('episode', ''),
            'source': LABEL,
            'ai': r.get('source') == 'ai',
            'downloads': _int(r.get('downloads')) or 0,
            'bonus': bonus,
        })
    return out


def download(item):
    rid = str(item.get('id') or '')
    if not rid.isdigit():
        raise Exception('رقم ترجمة غير صحيح في الفهرس')
    return http(BASE + '/v1/get', params={'id': rid}, headers=_h(), raw=True, timeout=30, retries=1)


# ---------------------------------------------------------------- sharing a finished translation
def _upload(body, mark):
    try:
        res = http(BASE + '/v1/upload', json_body=body, headers=_h(), timeout=40)
        log('index: shared (%s)' % {k: res.get(k) for k in ('ok', 'id', 'duplicate', 'error') if k in res})
        cache_put(mark, str(int(time.time())))
    except Exception as e:
        t = str(e)
        log('index: share failed: %s' % t[:200])
        if any(x in t for x in ('not_arabic', 'too_few', 'too_large', 'enough_versions', 'removed_by_admin', 'need_imdb')):
            cache_put(mark, 'refused')       # the server will never take this one: don't retry


def share(video, cues, source='ai'):
    """Send a finished translation to the index in the background (once per video)."""
    try:
        if not available() or not sharing() or not cues:
            return
        q = ids(video)
        if not q:
            return
        from .. import subtitle
        clean = [subtitle.Cue(c.start, c.end, c.text) for c in cues]
        srt = subtitle.to_srt(subtitle.fix_timing(clean))
        if len(srt.encode('utf-8')) > 800 * 1024:
            return
        rel = os.path.splitext(video.get('filename') or '')[0]
        key = '%s|%s|%s|%s|%s' % (q.get('imdb'), q.get('tmdb'), q.get('season'), q.get('episode'), rel)
        mark = 'idxup_%s.json' % hashlib.sha1(key.encode('utf-8')).hexdigest()[:16]
        if cache_get(mark, 365 * 86400):
            return
        body = dict(q)
        body.update({
            'title': (video.get('tvshow') if video.get('is_episode') else video.get('title')) or '',
            'year': video.get('year') or '',
            'duration': _duration(video),
            'fps': video.get('fps') or None,
            'release': rel[:120],
            'source': source,
            'srt': srt,
        })
        t = threading.Thread(target=_upload, args=(body, mark))
        t.daemon = True
        t.start()
    except Exception as e:
        log('index: share skipped: %s' % e)
