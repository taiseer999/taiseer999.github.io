# -*- coding: utf-8 -*-
"""Fast smart sync WITHOUT audio: match every Arabic line to the English line(s) it
translates (by meaning, with Gemini — text only, a few KB per request) and copy the
English timing, which is already in sync with the video. The same request also
proofreads the Arabic text, so correction + sync is one pass.

English reference = a subtitle for the SAME release (hash match / same release name)."""
import bisect
import concurrent.futures
import json


def _workers(n):
    try:
        from . import llm
        return max(n, min(4, 1 + len(llm.available())))
    except Exception:
        return n

from . import arabic, sync
from .common import http, log, setting, HttpError
from .subtitle import Cue

API = 'https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent'

PROMPT = (
    'You align and proofread subtitles. "en" are the original English subtitle lines '
    '(perfectly timed). "ar" are Arabic subtitle lines for the same film (a translation, '
    'possibly with different line splits). For EVERY Arabic line return:\n'
    '  "i": its id,\n'
    '  "e": the ids of the English lines it translates (usually one; two or more if the '
    'Arabic line merges them; [] if it has no English counterpart),\n'
    '  "t": the Arabic line corrected — fix spelling, grammar, hamzas, broken or reversed '
    'letters, misplaced punctuation and clumsy machine-like wording, without changing the '
    'meaning, adding information, merging or splitting lines. Keep " | " (line break), '
    'keep <i>/<b> tags, names and numbers. If it is already correct return it unchanged.\n'
    'Match strictly by meaning and keep chronological order. Return only JSON: a list of objects {"i", "e", "t"}.\n'
    'Work title: %(title)s\nen = %(en)s\nar = %(ar)s'
)

SCHEMA = {
    'type': 'ARRAY',
    'items': {'type': 'OBJECT',
              'properties': {'i': {'type': 'INTEGER'},
                             'e': {'type': 'ARRAY', 'items': {'type': 'INTEGER'}},
                             't': {'type': 'STRING'}},
              'required': ['i', 'e', 't']},
}

_NO_THINK = [None]


class SemSyncError(Exception):
    pass


def _ask(api_key, model, title, en_items, ar_items):
    from . import llm
    data, pid = llm.ask_json('', PROMPT % {
        'title': title or '-',
        'en': json.dumps(en_items, ensure_ascii=False),
        'ar': json.dumps(ar_items, ensure_ascii=False)})
    out = {}
    for d in data:
        try:
            out[int(d['i'])] = ([int(x) for x in d.get('e') or []], d.get('t') or '')
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _lis(pairs):
    pairs = sorted(pairs)
    tails, prev, idx = [], [-1] * len(pairs), []
    for i, (_a, t) in enumerate(pairs):
        k = bisect.bisect_right(tails, t)      # non-decreasing: split lines share a start
        if k == len(tails):
            tails.append(t)
            idx.append(i)
        else:
            tails[k] = t
            idx[k] = i
        prev[i] = idx[k - 1] if k else -1
    out, i = [], idx[-1] if idx else -1
    while i >= 0:
        out.append(pairs[i])
        i = prev[i]
    return out[::-1]


def _median(v):
    s = sorted(v)
    return s[len(s) // 2] if s else 0


def _split_shared(spans, cues):
    """Arabic lines that got the same (or overlapping) English time — e.g. one English
    sentence split over two Arabic lines — share that time in proportion to their
    text length instead of sitting on top of each other."""
    import re
    idx = sorted(spans)
    out = dict(spans)
    k = 0
    while k < len(idx):
        group = [idx[k]]
        s0, e0 = spans[idx[k]]
        j = k + 1
        while j < len(idx) and idx[j] == group[-1] + 1 and spans[idx[j]][0] < e0 - 200:
            group.append(idx[j])
            s0, e0 = min(s0, spans[idx[j]][0]), max(e0, spans[idx[j]][1])
            j += 1
        if len(group) > 1:
            weights = [max(4, len(re.sub(r'<[^>]+>|\s', '', cues[i].text))) for i in group]
            total = float(sum(weights))
            t = s0
            for i, w in zip(group, weights):
                d = int((e0 - s0) * w / total)
                out[i] = (t, t + d - 40)
                t += d
        k = j
    return out


def apply_matches(cues, en, matches, max_dev=None):
    """matches: {ar_index: [en indexes]} → new cues with English timing.
    Wrong/out-of-order matches are dropped; unmatched lines follow their neighbours.
    max_dev: the cues are already roughly aligned, so a match that would move a line
    further than this (ms) is the AI pairing it with the wrong scene — ignored."""
    n = len(cues)
    raw = {}
    far = 0
    for i, es in matches.items():
        es = [e for e in es if 0 <= e < len(en)]
        if 0 <= i < n and es:
            span = (min(en[e].start for e in es), max(en[e].end for e in es))
            if span[1] - span[0] > 20000:          # "merged" lines far apart: not a real match
                continue
            if max_dev is not None and abs(span[0] - cues[i].start) > max_dev:
                far += 1
                continue
            raw[i] = span
    chain = dict(_lis([(i, raw[i][0]) for i in raw]))
    deltas = [(i, chain[i] - cues[i].start) for i in sorted(chain)]
    good = []
    for k, (i, d) in enumerate(deltas):
        neigh = [x[1] for x in deltas[max(0, k - 6):k + 7]]
        if abs(d - _median(neigh)) <= 15000:
            good.append((i, d))
    info = {'lines': n, 'matched': len(raw), 'kept': len(good)}
    if far:
        info['far'] = far
    if len(good) < max(5, len(matches) * 0.2):
        info['reason'] = 'few_matches'
        return None, info
    gmap = dict(good)
    idxs = [i for i, _ in good]
    spans = _split_shared({i: raw[i] for i in idxs}, cues)
    out = []
    for i, c in enumerate(cues):
        if i in gmap:
            s, e = spans[i]
            out.append(Cue(s, max(e, s + 500), c.text))
            continue
        k = bisect.bisect_left(idxs, i)
        left = [d for _, d in good[max(0, k - 4):k]]
        right = [d for _, d in good[k:k + 4]]
        if left and right and abs(_median(left) - _median(right)) > 1500:
            # a cut between neighbours: follow the nearer side in time
            li, ri = idxs[k - 1], idxs[k]
            d = _median(left) if c.start - cues[li].start <= cues[ri].start - c.start else _median(right)
        else:
            d = _median(left + right)
        out.append(Cue(c.start + int(d), c.end + int(d), c.text))
    out.sort(key=lambda x: x.start)
    return out, info


def plan_chunks(starts, now, chunk=120, first_ms=300000, first_cap=60):
    """Line indexes grouped into requests. The first request is SMALL and holds only the
    next ~5 minutes from where you are, so it comes back fast and is shown right away;
    the rest of the film follows in bigger requests (upcoming first, already-seen last)."""
    n = len(starts)
    first = [i for i in range(n) if now - 2000 <= starts[i] <= now + first_ms][:first_cap]
    if len(first) < 8:                    # quiet start: take the next lines whatever their time
        k = bisect.bisect_left(starts, now)
        first = list(range(k, min(n, k + 30)))
    taken = set(first)
    rest_idx = [i for i in range(n) if i not in taken]
    rest = [rest_idx[s:s + chunk] for s in range(0, len(rest_idx), chunk)]

    def order(ch):
        t0, t1 = starts[ch[0]], starts[ch[-1]]
        if t1 < now - 60000:
            return (2, -t0)
        return (0 if t1 >= now else 1, abs(t0 - now))
    rest.sort(key=order)
    return ([first] if first else []) + rest


def semantic_sync(cues, en, title='', position=None, progress=None, abort=None,
                  on_partial=None, chunk=90, workers=2, asker=None):
    """Returns (new_cues or None, info). Also corrects the Arabic text."""
    from . import llm
    if asker is None and not llm.any_available():
        raise SemSyncError('no_key')
    api_key, model = '', 'multi'
    ask = asker or _ask

    # 1) quick timing pre-alignment so each chunk sees the right English lines
    pre, pinfo = sync.align(cues, en, local=True, min_lift=1.3, min_quality=0.25)
    base = pre if pre is not None else [Cue(c.start, c.end, c.text) for c in cues]
    base.sort(key=lambda c: c.start)
    # after the pre-alignment the real differences are a few seconds (cuts: a little more);
    # without it, allow more room
    max_dev = 30000 if pre is not None else 180000
    en = sorted(en, key=lambda c: c.start)
    en_starts = [c.start for c in en]
    texts = [arabic.plain(c.text).replace('\n', ' | ') for c in base]

    now = 0
    try:
        now = int(position()) if position else 0
    except Exception:
        now = 0
    chunks = plan_chunks([c.start for c in base], now, chunk=chunk)

    results = {}
    errors = []

    def run(ch):
        lo = bisect.bisect_left(en_starts, base[ch[0]].start - 45000)
        hi = bisect.bisect_right(en_starts, base[ch[-1]].end + 45000)
        en_items = [{'id': k, 't': en[k].text.replace('\n', ' ')} for k in range(lo, hi)]
        ar_items = [{'i': i, 't': texts[i]} for i in ch]
        if not en_items:
            return {}
        from . import gemini
        if any(isinstance(x, gemini.QuotaExhausted) for x in errors):
            return {}
        def attempt(items):
            try:
                return ask(api_key, model, title, en_items, items)
            except ValueError as e:              # answer cut off / broken JSON: halve and retry
                if len(items) > 15:
                    h = len(items) // 2
                    log('semantic: broken answer, retrying in two halves')
                    r = attempt(items[:h])
                    r.update(attempt(items[h:]))
                    return r
                raise
        try:
            return attempt(ar_items)
        except Exception as e:
            errors.append(e)
            log('semantic chunk failed: %s' % e)
            return {}

    ex = concurrent.futures.ThreadPoolExecutor(max_workers=_workers(workers))
    futs = {ex.submit(run, ch): k for k, ch in enumerate(chunks)}
    first_wave = set(f for f, k in futs.items() if k == 0)     # the next 5 minutes
    partial_sent = False
    done = 0
    try:
        pending = set(futs)
        while pending:
            done_set, pending = concurrent.futures.wait(pending, timeout=0.5)
            for f in done_set:
                results.update(f.result())
                done += 1
                if progress:
                    progress(int(done * 100 / len(chunks)), done, len(chunks))
            if on_partial and not partial_sent and pending and not (first_wave & pending) and results:
                partial_sent = True
                part, pinfo2 = _build(base, en, texts, results, max_dev)
                if part is not None:
                    on_partial(part, pinfo2)
            if pending and abort and abort():
                for f in pending:
                    f.cancel()
                raise SemSyncError('aborted')
    finally:
        ex.shutdown(wait=False)
    if not results and errors:
        raise errors[0]
    out, info = _build(base, en, texts, results, max_dev)
    info['pre'] = sync.describe(pinfo) if pre is not None else ''
    # how far apart the two subtitles really were, measured from the AI's line matches
    orig = sorted(cues, key=lambda c: c.start)
    deltas = []
    if len(orig) == len(base):
        for i, (es, _t) in results.items():
            es = [e for e in es if 0 <= e < len(en)]
            if es and 0 <= i < len(orig):
                deltas.append(min(en[e].start for e in es) - orig[i].start)
    info['diff'] = _diff_summary(deltas)
    return out, info


def _build(base, en, texts, results, max_dev=None):
    from .ai import _sane
    fixed = [Cue(c.start, c.end, c.text) for c in base]
    corrected = 0
    for i, (_es, t) in results.items():
        if 0 <= i < len(fixed) and t:
            t = t.strip()
            if t != texts[i] and _sane(texts[i], t):
                fixed[i].text = '\n'.join(p.strip() for p in t.split('|'))
                corrected += 1
    matches = {i: es for i, (es, _t) in results.items()}
    out, info = apply_matches(fixed, en, matches, max_dev=max_dev)
    info['corrected'] = corrected
    if out is None:
        # still return the text corrections on the pre-aligned timing
        info['text_only'] = True
        return fixed, info
    return out, info


def _diff_summary(deltas):
    if len(deltas) < 8:
        return ''
    d = sorted(deltas)
    med, p10, p90 = d[len(d) // 2], d[len(d) // 10], d[len(d) * 9 // 10]
    if p90 - p10 <= 700:
        return 'الفرق بين الترجمتين ثابت: %+.1f ث' % (med / 1000.0)
    return 'الفرق بين الترجمتين متغير (من %+.1f إلى %+.1f ث) — يوجد قص أو اختلاف في النسخة' % (
        p10 / 1000.0, p90 / 1000.0)


def describe(info):
    msg = 'طابق %d من %d سطراً مع الإنجليزية' % (info.get('kept', 0), info.get('lines', 0))
    if info.get('diff'):
        msg = info['diff'] + ' | ' + msg
    if info.get('corrected'):
        msg += '، وصحّح %d سطراً' % info['corrected']
    return msg
