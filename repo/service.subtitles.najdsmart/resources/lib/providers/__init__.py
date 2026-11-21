# -*- coding: utf-8 -*-
import concurrent.futures
import re

from ..common import log
from ..media import release_tokens
from . import subdl, opensubtitles, subsource, kodiaddons

PROVIDERS = {
    'subdl': subdl,
    'opensubtitles': opensubtitles,
    'subsource': subsource,
    'kodi': kodiaddons,
}


LAST = {'failed': 0, 'total': 0}


def all_failed():
    return LAST['total'] > 0 and LAST['failed'] >= LAST['total']


_EP_RE = re.compile(r'(?<![a-z0-9])s(\d{1,2})[ ._-]?e(\d{1,3})(?:[ ._-]?(?:-|e)[ ._-]?e?(\d{1,3}))?'
                    r'|(?<![a-z0-9.])(\d{1,2})x(?!26[45])(\d{2,3})(?![0-9])', re.I)
_SEASON_RE = re.compile(r'(?<![a-z0-9])(?:s(\d{1,2})(?![0-9]|[ ._-]?e\d)|season[ ._-]?(\d{1,2}))(?![0-9])', re.I)


def _int(x):
    try:
        return int(x)
    except (ValueError, TypeError):
        return None


def episode_fit(item, video):
    """'match' / 'pack' (whole season) / 'other' (another episode or season) / '' (can't tell)."""
    if not video.get('is_episode'):
        return ''
    vs, ve = _int(video.get('season')), _int(video.get('episode'))
    if ve is None:
        return ''
    ie = _int(item.get('episode'))
    if ie is not None and ie > 0:
        return 'match' if ie == ve else 'other'
    found = set()
    for rel in item.get('releases') or [item.get('release', '')]:
        rel = rel or ''
        hit = False
        for m in _EP_RE.finditer(rel):
            hit = True
            s_ = _int(m.group(1) or m.group(4))
            a = _int(m.group(2) or m.group(5))
            b = _int(m.group(3)) or a
            if vs is not None and s_ != vs:
                found.add('other')
            elif a <= ve <= max(a, b):
                found.add('match')
            else:
                found.add('other')
        if not hit:
            m = _SEASON_RE.search(rel)
            if m:
                s_ = _int(m.group(1) or m.group(2))
                found.add('pack' if vs is None or s_ == vs else 'other')
    for k in ('match', 'pack', 'other'):
        if k in found:
            return k
    return ''


def score(item, video):
    s = 0.0
    if item.get('hash_match'):
        s += 100
    vt = release_tokens(video.get('filename'))
    best = 0.0
    for rel in item.get('releases') or [item.get('release', '')]:
        st = release_tokens(rel)
        if vt and st:
            best = max(best, len(vt & st) / float(len(vt | st)))
    s += best * 50
    item['match'] = best
    fit = item.get('fit') or ''
    if fit == 'match':
        s += 15
    elif fit == 'pack':
        s -= 5
    if item.get('hi'):
        s -= 2
    s += min(item.get('downloads', 0), 10000) / 2000.0
    return s


def search_all(video, langs, enabled=None):
    """Search every enabled provider in parallel; returns a sorted list."""
    mods = [(n, m) for n, m in PROVIDERS.items()
            if (enabled is None or n in enabled) and m.available()]
    results = []
    LAST['failed'], LAST['total'] = 0, len(mods)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(mods) or 1) as ex:
        futs = {ex.submit(m.search, video, langs): n for n, m in mods}
        try:
            done_iter = list(concurrent.futures.as_completed(futs, timeout=60))
        except concurrent.futures.TimeoutError:
            done_iter = [f for f in futs if f.done()]
            log('some sources were too slow and were skipped')
        for f in done_iter:
            name = futs[f]
            try:
                items = f.result() or []
                log('%s: %d results' % (name, len(items)))
                results.extend(items)
            except Exception as e:
                LAST['failed'] += 1
                log('%s search failed: %s' % (name, e))
    kept, dropped = [], 0
    for it in results:
        it['fit'] = episode_fit(it, video)
        if it['fit'] == 'other':
            dropped += 1
            continue
        it['score'] = score(it, video)
        kept.append(it)
    if dropped:
        log('dropped %d results for other episodes/seasons' % dropped)
    results = kept
    results.sort(key=lambda x: -x['score'])
    return results


def download(item):
    """Returns raw bytes (zip or subtitle file)."""
    return PROVIDERS[item['provider']].download(item)
