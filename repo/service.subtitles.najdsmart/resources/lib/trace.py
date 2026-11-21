# -*- coding: utf-8 -*-
"""Per-episode record of what the add-on did, for the problem report.

One small JSON file per video in PROFILE/traces: what subtitle was chosen, what the sync
steps found, the raw timing data of every listening window (subtitle lines and detected
speech, as numbers only — no audio, no text), the final result and the viewer's own
verdict. The raw windows let the developer replay the sync on the real data."""
import base64
import json
import os
import time
import zlib

from .common import ADDON, PROFILE, log

DIR = os.path.join(PROFILE, 'traces')
KEEP = 12


def _key(video):
    from .pipeline import _video_key
    return _video_key(video or {})


def _path(video):
    return os.path.join(DIR, _key(video) + '.json')


def _load(video):
    try:
        with open(_path(video), encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def _save(video, d):
    try:
        if not os.path.isdir(DIR):
            os.makedirs(DIR)
        d['updated'] = int(time.time())
        with open(_path(video), 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, separators=(',', ':'))
        files = sorted((os.path.join(DIR, n) for n in os.listdir(DIR)), key=os.path.getmtime)
        for old in files[:-KEEP]:
            os.remove(old)
    except Exception as e:
        log('trace: %s' % e)


def _get(video):
    d = _load(video)
    if d is None:
        v = video or {}
        d = {'title': v.get('tvshow') or v.get('title') or '', 'season': v.get('season') or '',
             'episode': v.get('episode') or '', 'duration': int(v.get('duration') or 0),
             'remote': str(v.get('path') or '').startswith(('http://', 'https://')),
             'events': [], 'windows': {}, 'started': int(time.time())}
    return d


def start(video, item, how=''):
    """A new subtitle was chosen for this video: start its record afresh."""
    try:
        os.remove(_path(video))
    except OSError:
        pass
    d = _get(video)
    it = item or {}
    d['version'] = ADDON.getAddonInfo('version')
    d['subtitle'] = {'source': it.get('source') or it.get('provider') or '', 'release': it.get('release') or '',
                     'how': how}
    _save(video, d)


def event(video, text):
    d = _get(video)
    d['events'] = (d.get('events') or [])[-40:] + ['%s %s' % (time.strftime('%H:%M:%S'), text)]
    _save(video, d)


def put(video, key, value):
    d = _get(video)
    d[key] = value
    _save(video, d)


def windows(video, kind, data, extra=None):
    """data: [(time_ms, subtitle_lines, speech)] — stored relative to each window, in 10 ms."""
    rows = []
    for t, ins, sp in data:
        rows.append([int(t // 10), [[(a - t) // 10, (b - a) // 10] for a, b in ins],
                     [[(a - t) // 10, (b - a) // 10] for a, b in sp]])
    d = _get(video)
    w = d.get('windows') or {}
    w[kind] = {'rows': rows, 'extra': extra or {}}
    d['windows'] = w
    _save(video, d)


def feedback(video, answer):
    put(video, 'viewer', answer)


def has_sync(video):
    d = _load(video)
    return bool(d and (d.get('windows') or d.get('result')))


# ---------------------------------------------------------------- report ----

def _mmss(sec):
    sec = int(sec or 0)
    return '%d:%02d' % (sec // 60, sec % 60)


def summary_lines():
    """Readable per-episode summary, newest first."""
    if not os.path.isdir(DIR):
        return []
    out = []
    files = sorted((os.path.join(DIR, n) for n in os.listdir(DIR)), key=os.path.getmtime, reverse=True)
    for p in files:
        try:
            with open(p, encoding='utf-8') as f:
                d = json.load(f)
        except Exception:
            continue
        name = d.get('title') or '?'
        if d.get('season') and d.get('episode'):
            name += ' S%02dE%02d' % (int(d['season']), int(d['episode']))
        out.append('== %s | v%s | %s | %s' % (
            name, d.get('version', '?'), time.strftime('%m-%d %H:%M', time.localtime(d.get('started', 0))),
            'stream' if d.get('remote') else 'local file'))
        sub = d.get('subtitle') or {}
        if sub:
            out.append('  subtitle: [%s] %s (%s)' % (sub.get('source'), sub.get('release'), sub.get('how') or '-'))
        for kind, w in (d.get('windows') or {}).items():
            ex = w.get('extra') or {}
            out.append('  %s: %d windows, %s' % (kind, len(w.get('rows') or []),
                                                 ', '.join('%s=%s' % kv for kv in sorted(ex.items()))))
        for e in (d.get('events') or [])[-12:]:
            out.append('  · ' + e)
        if d.get('result'):
            out.append('  result: ' + ' | '.join(d['result']))
        if d.get('took'):
            out.append('  took: %ss' % d['took'])
        out.append('  viewer says: %s' % (d.get('viewer') or '-'))
    return out


def blob():
    """All records, compressed — the raw data for replaying the sync."""
    if not os.path.isdir(DIR):
        return ''
    alld = []
    for n in sorted(os.listdir(DIR)):
        try:
            with open(os.path.join(DIR, n), encoding='utf-8') as f:
                alld.append(json.load(f))
        except Exception:
            pass
    if not alld:
        return ''
    raw = base64.b64encode(zlib.compress(json.dumps(alld, separators=(',', ':')).encode('utf-8'), 9)).decode()
    return '\n'.join(raw[i:i + 100] for i in range(0, len(raw), 100))
