# -*- coding: utf-8 -*-
"""Put a subtitle on the timing of a reference that is known to follow the video (the
film's own speech heard by Whisper, or an English subtitle embedded in the file) —
by timing alone, no AI. Handles a large shift, slow drift, cut scenes and sloppy
line-by-line timing. The reference may cover only parts of the film (a stream)."""
import bisect

from .common import log
from .subtitle import Cue
from . import sync


def _shift(iv, d):
    return [(a + d, b + d) for a, b in iv]


def _inside(t, covered):
    return covered is None or any(a <= t <= b for a, b in covered)


def _score(ar, ref, d, covered):
    pts = [(a + d, b + d) for a, b in ar if _inside(a + d, covered)]
    return sync._overlap(pts, ref), pts


def coarse_shift(cues, ref, covered=None, span=300000):
    """One shift for the whole subtitle, from the timing pattern. (shift_ms, confidence) or None."""
    ar = [(c.start, c.end) for c in cues]
    rf = [(c.start, c.end) for c in ref]
    scores = []
    d = -span
    while d <= span:
        scores.append((_score(ar, rf, d, covered)[0], d))
        d += 500
    scores.sort(reverse=True)
    best_s, best_d = scores[0]
    if best_s <= 0:
        return None
    for d in range(best_d - 500, best_d + 501, 20):
        s = _score(ar, rf, d, covered)[0]
        if s > best_s:
            best_s, best_d = s, d
    # a competitor is another place in the film, not the shoulder of the same (broad) peak
    second = next((s for s, dd in scores if abs(dd - best_d) > 15000), 0)
    # chance level: the same amount of subtitle on the same amount of speech, at random
    s_, pts = _score(ar, rf, best_d, covered)
    span_ms = float(sum(b - a for a, b in covered)) if covered else float(max(1, rf[-1][1] - rf[0][0]))
    dens = min(1.0, sum(b - a for a, b in rf) / span_ms)
    chance = sum(b - a for a, b in pts) * dens
    lift = best_s / chance if chance else 0
    prominence = best_s / float(second) if second else 9.9
    log('refalign: coarse %+d ms lift %.2f prominence %.2f (%d lines in reach)' % (best_d, lift, prominence, len(pts)))
    if lift >= 1.4 and prominence < 1.08 and len(pts) >= 20:
        return 'weak'                   # clearly the same film, but too little heard to be sure where
    if lift < 1.25 or prominence < 1.08 or len(pts) < 20:
        return None
    return best_d, lift


# ---------------------------------------------------------------- votes per piece heard
# Whisper's sentences are long (it joins lines) and their times are rough, so a whole-film
# overlap score is weak. Instead every piece that was heard votes, on its own, for the
# shifts where the subtitle's line starts meet the starts of the spoken sentences. The
# true shift gets votes from piece after piece; a subtitle of another film gets scattered
# votes. Different shifts in different parts of the film (another cut) show up as runs
# of pieces voting for different shifts — each part then gets its own.

def _piece_scores(starts, on, a, b, span, step=250):
    """{shift: line starts that meet a sentence start} for one heard piece."""
    out = {}
    for d in range(-span, span + 1, step):
        lo = bisect.bisect_left(starts, a - d)
        hi = bisect.bisect_right(starts, b - d)
        n = 0
        for t in starts[lo:hi]:
            q = (t + d) // 500
            if q in on or q - 1 in on or q + 1 in on:
                n += 1
        if n:
            out[d] = n
    return out


def vote_sections(cues, ref, covered, span=300000):
    """[(from_ms, d_ms), ...] (in subtitle time, sorted) or None, plus info."""
    if not covered:
        return None, {}
    starts = [c.start for c in cues]
    pieces = []
    for a, b in sorted(covered):
        on = set(c.start // 500 for c in ref if a <= c.start <= b)
        if len(on) < 3:
            continue
        sc = _piece_scores(starts, on, a, b, span)
        top = max(sc.values()) if sc else 0
        if top < 3:
            continue
        pieces.append((a, b, sc, top))
    if len(pieces) < 4:
        return None, {'pieces': len(pieces)}

    def at(i, c):
        sc = pieces[i][2]
        return max(sc.get(d, 0) for d in range(c - 1000, c + 1001, 250))

    def near_best(i, c):
        return at(i, c) >= max(3, 0.75 * pieces[i][3])

    # candidate shifts: the few best of every piece
    cands = set()
    for _a, _b, sc, _top in pieces:
        for d, _n in sorted(sc.items(), key=lambda x: -x[1])[:6]:
            cands.add(int(round(d / 1000.0)) * 1000)
    support = {}
    for c in cands:
        ids = set(i for i in range(len(pieces)) if near_best(i, c))
        # at least two pieces must have it as their very best (not only "close enough")
        if len(ids) >= 3 and sum(1 for i in ids if at(i, c) >= pieces[i][3]) >= 2:
            support[c] = ids
    groups = []
    for c in sorted(support, key=lambda c: (-len(support[c]), c)):
        if any(abs(c - g) <= 2000 for g, _ in groups):
            continue
        # the exact shift: best summed score of its pieces within ±1 s
        ids = support[c]
        best = max(range(c - 1000, c + 1001, 250),
                   key=lambda d: sum(pieces[i][2].get(d, 0) for i in ids))
        groups.append((best, ids))
    # a part of the film = one shift voted by a run of pieces, not scattered votes.
    # Label every piece with the strongest shift it voted for (or none) ...
    gsize = dict((q, len(ids)) for q, ids in groups)
    label = []
    for i in range(len(pieces)):
        mine = [q for q, ids in groups if i in ids]
        label.append(max(mine, key=lambda q: gsize[q]) if mine else None)
    # ... a lone piece voting for something else than both of its neighbours is noise ...
    voted = [i for i in range(len(pieces)) if label[i] is not None]
    for k, i in enumerate(voted):
        prev = label[voted[k - 1]] if k > 0 else None
        nxt = label[voted[k + 1]] if k + 1 < len(voted) else None
        if label[i] != prev and label[i] != nxt and (prev is not None or nxt is not None):
            label[i] = None
    # ... and runs of the same label (pieces without a vote in between do not break it)
    clean = []
    for i in range(len(pieces)):
        q = label[i]
        if q is None:
            continue
        if clean and clean[-1][2] == q:
            f, _l, d, n = clean[-1]
            clean[-1] = (f, i, d, n + 1)
        else:
            clean.append((i, i, q, 1))
    clean = [p for p in clean if p[3] >= 3]
    support = sum(p[3] for p in clean)
    info = {'pieces': len(pieces), 'parts': [(p[2], p[3]) for p in clean], 'support': support}
    info['groups'] = [(g, len(ids)) for g, ids in groups[:6]]
    log('refalign votes: %s' % info)
    if not clean or support < max(3, 0.4 * len(pieces)):
        return None, info
    # a long stretch of pieces that none of the parts explains may be another part of the
    # film with its own shift: do not guess for it — listen to more first
    inside = set()
    for f, l, _d, _n in clean:
        inside.update(range(f, l + 1))
    gap = run = 0
    for i in range(len(pieces)):
        run = 0 if i in inside else run + 1
        gap = max(gap, run)
    info['gap'] = gap
    used = set(p[2] for p in clean)
    rival = max([len(ids) for g, ids in groups if g not in used] + [0])
    info['rival'] = rival
    if gap >= 3 or support < 0.75 * len(pieces) or rival > 0.6 * min(p[3] for p in clean):
        info['weak'] = True
        return None, info
    # boundaries halfway between the last piece of one part and the first of the next
    out = [(-10 ** 9, clean[0][2])]
    for prev, nxt in zip(clean, clean[1:]):
        film_t = (pieces[prev[1]][1] + pieces[nxt[0]][0]) // 2
        out.append((film_t - nxt[2], nxt[2]))
    return out, info


def align(cues, ref, covered=None, tol=1200):
    """Returns (new_cues, info) or (None, reason)."""
    if not cues or len(ref) < 10:
        return None, 'little_reference'
    cues = sorted(cues, key=lambda c: c.start)
    ref = sorted(ref, key=lambda c: c.start)
    secs, vinfo = vote_sections(cues, ref, covered)
    if vinfo.get('weak'):
        return None, 'weak'
    if secs and max(abs(d) for _t, d in secs) < 600:
        # within Whisper's own precision: the subtitle already follows the speech
        return None, 'in_sync'
    if secs:
        lift = 0
        moved = []
        for c in cues:
            d = [d for t, d in secs if c.start >= t][-1]
            moved.append(Cue(c.start + d, c.end + d, c.text))
        # Whisper's sentence times are rough (± a few tenths): a subtitle made for another
        # release is moved as a whole, its own (good) line timing is kept
        new, info = _refine(moved, ref, covered, 0, lift, tol, snap=False)
        # last check: after the move, the heard lines must really sit on the spoken sentences
        if new is None or info.get('tight', 0) < 0.45:
            log('refalign: votes looked right but the lines do not sit on the speech (%s)' % (
                info if new is None else info.get('tight')))
            return None, 'weak'
        info.update({'shift': secs[0][1], 'parts': vinfo.get('parts'), 'how': 'votes'})
        if len(secs) > 1:
            info['shifts'] = [d for _t, d in secs]
        return new, info
    # the whole-film overlap score is only trusted when most of the film was heard
    span = float(max(1, cues[-1].end - cues[0].start))
    heard = sum(b - a for a, b in covered) / span if covered else 1.0
    if heard < 0.4:
        return None, 'no_match'
    co = coarse_shift(cues, ref, covered)
    if co == 'weak':
        return None, 'weak'
    if not co:
        return None, 'no_match'
    d0, lift = co
    return _refine(cues, ref, covered, d0, lift, tol)


def _refine(cues, ref, covered, d0, lift, tol, snap=True):
    rs = [c.start for c in ref]

    # 1) how far each line sits from the nearest reference sentence (only where we listened)
    dev = []
    for c in cues:
        t = c.start + d0
        if not _inside(t, covered):
            dev.append(None)
            continue
        i = bisect.bisect_left(rs, t)
        cand = [rs[j] - t for j in (i - 1, i) if 0 <= j < len(rs)]
        d = min(cand, key=abs) if cand else None
        dev.append(d if d is not None and abs(d) <= 3000 else None)

    # 2) the local drift: a running median where we listened, a straight line in between
    anchors = []
    for k in range(len(cues)):
        if dev[k] is None:
            continue
        near = sorted(x for x in dev[max(0, k - 25):k + 26] if x is not None)
        if len(near) >= 5:
            anchors.append((cues[k].start, near[len(near) // 2]))
    if len(anchors) < 5:
        return None, 'few_anchors'
    at = [a for a, _ in anchors]

    def drift(t):
        i = bisect.bisect_left(at, t)
        if i <= 0:
            return anchors[0][1]
        if i >= len(anchors):
            return anchors[-1][1]
        (t0, d1), (t1, d2) = anchors[i - 1], anchors[i]
        return d1 if t1 == t0 else d1 + (d2 - d1) * (t - t0) / float(t1 - t0)

    # 3) every line moves with the drift; a line that lands next to a reference sentence
    #    takes that sentence's exact start (in order, each sentence used once)
    out, used, snapped = [], -1, 0
    for c in cues:
        dd = d0 + int(drift(c.start))
        a, b = c.start + dd, c.end + dd
        if snap and _inside(a, covered):
            i = bisect.bisect_left(rs, a)
            cand = [(abs(rs[j] - a), j) for j in (i - 1, i, i + 1) if used < j < len(rs)]
            if cand and min(cand)[0] <= tol:
                j = min(cand)[1]
                used = j
                dur = b - a
                a = ref[j].start
                b = a + dur
                snapped += 1
        out.append(Cue(a, b, c.text))
    for k in range(len(out) - 1):                       # never overlap the next line
        if out[k].end > out[k + 1].start - 40:
            out[k].end = max(out[k].start + 300, out[k + 1].start - 40)
    # how clean the subtitle is: lines that already sit on the drift line (± 0.3 s)
    res = [abs(dev[k] - drift(cues[k].start)) for k in range(len(cues)) if dev[k] is not None]
    tight = sum(1 for r in res if r <= 300) / float(len(res)) if res else 0.0
    info = {'shift': d0, 'lift': round(lift, 2), 'snapped': snapped, 'lines': len(out),
            'tight': round(tight, 2), 'heard_lines': len(res),
            'drift_min': min(d for _, d in anchors), 'drift_max': max(d for _, d in anchors)}
    log('refalign: %s' % info)
    return out, info
