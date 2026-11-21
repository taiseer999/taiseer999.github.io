# -*- coding: utf-8 -*-
import concurrent.futures
import re

from ..common import log, cache_get, cache_put
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
                    r'|(?<![a-z0-9])(?<!\d\.)(\d{1,2})x(?!26[45])(\d{2,3})(?![0-9])', re.I)
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
    ex = concurrent.futures.ThreadPoolExecutor(max_workers=len(mods) or 1)
    futs = {ex.submit(m.search, video, langs): n for n, m in mods}
    try:
        done_iter = list(concurrent.futures.as_completed(futs, timeout=60))
    except concurrent.futures.TimeoutError:
        done_iter = [f for f in futs if f.done()]
        slow = [futs[f] for f in futs if not f.done()]
        LAST['failed'] += len(slow)
        log('too slow, skipped: %s' % ', '.join(slow))
    finally:
        ex.shutdown(wait=False)      # never wait for a source that hangs
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
        if limited(it.get('provider', '')):
            it['score'] -= 1000          # its downloads are used up today: others first
        kept.append(it)
    if dropped:
        log('dropped %d results for other episodes/seasons' % dropped)
    results = kept
    if not (video.get('imdb') or video.get('show_imdb')):
        # searched by name only: 'Prisoner 951' must not take 'Prison Break', nor
        # 'Ripper Street S05' take 'Stargate SG-1 S05'
        words = title_words(video.get('tvshow') or video.get('title') or '')
        # only Latin titles: an Arabic title would never appear in the release names
        if words and all(re.match(r'^[a-z0-9]+$', w) for w in words):
            fit = [it for it in results if names_have(it, words)]
            if len(fit) < len(results):
                log('dropped %d results for another title (wanted: %s)'
                    % (len(results) - len(fit), ' '.join(words)))
            results = fit
    results.sort(key=lambda x: -x['score'])
    return results


_STOP = set('the a an of and in on at to'.split())


def _norm(t):
    return re.sub(r'[^a-z0-9\u0600-\u06ff]+', ' ', (t or '').lower()).split()


def title_words(title):
    return [w for w in _norm(title) if w not in _STOP]


def names_have(it, words):
    names = list(it.get('releases') or []) + [it.get('release') or '', it.get('name') or '',
                                                it.get('title') or '']
    for n in names:
        toks = set(_norm(n))
        if toks and all(w in toks for w in words):
            return True
    return False


NAMES = {'subdl': 'SubDL', 'subsource': 'SubSource', 'opensubtitles': 'OpenSubtitles'}


class DailyLimit(Exception):
    pass


def limited(provider):
    """True while a site has said its free daily downloads are used up."""
    import time
    c = cache_get('limit_%s.json' % provider, 86400)
    try:
        return bool(c) and float(c.decode('utf-8')) > time.time()
    except ValueError:
        return False


def _note_limit(provider, err):
    import time
    m = re.search(r'retryAfterSeconds"?\s*:\s*(\d+)', err)
    wait = int(m.group(1)) if m else 6 * 3600
    cache_put('limit_%s.json' % provider, str(time.time() + min(wait, 86400)))
    log('%s: daily download limit reached — not used for %d min' % (provider, wait // 60))


def download(item):
    """Returns raw bytes (zip or subtitle file)."""
    prov = item['provider']
    if limited(prov):
        raise DailyLimit('%s: نفد حد التنزيل المجاني اليوم' % NAMES.get(prov, prov))
    try:
        return PROVIDERS[prov].download(item)
    except Exception as e:
        t = str(e)
        if '429' in t and ('limit' in t.lower() or 'quota' in t.lower()):
            _note_limit(prov, t)
            raise DailyLimit('%s: نفد حد التنزيل المجاني اليوم' % NAMES.get(prov, prov))
        raise
