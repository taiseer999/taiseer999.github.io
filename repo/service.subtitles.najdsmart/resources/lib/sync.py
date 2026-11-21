# -*- coding: utf-8 -*-
"""Align a subtitle to a reference subtitle that is already in sync with the video.

Pure Python. Strategy:
 1. Global: for several frame-rate ratios, vote on start-time differences to find
    candidate offsets, then refine each candidate by maximising interval overlap.
 2. Local: walk the subtitle in windows and refine the offset per window
    (handles cuts / added scenes / ads), smoothing the result.
"""
import bisect

FPS_RATIOS = [1.0,
              25 / 23.976, 23.976 / 25,
              25 / 24.0, 24.0 / 25,
              24 / 23.976, 23.976 / 24,
              30 / 29.97, 29.97 / 30,
              25 / 29.97, 29.97 / 25]


def _intervals(cues):
    return [(c.start, c.end) for c in cues if c.end > c.start]


def _overlap(a, b):
    """Total overlap (ms) between two sorted interval lists."""
    i = j = 0
    total = 0
    na, nb = len(a), len(b)
    while i < na and j < nb:
        s = a[i][0] if a[i][0] > b[j][0] else b[j][0]
        e = a[i][1] if a[i][1] < b[j][1] else b[j][1]
        if e > s:
            total += e - s
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return total


def _transform(iv, ratio, offset):
    return [(int(s * ratio + offset), int(e * ratio + offset)) for s, e in iv]


def _vote(a_starts, b_starts, window=150000, bucket=250):
    votes = {}
    for s in a_starts:
        lo = bisect.bisect_left(b_starts, s - window)
        hi = bisect.bisect_right(b_starts, s + window)
        for k in range(lo, hi):
            d = (b_starts[k] - s) // bucket
            votes[d] = votes.get(d, 0) + 1
    # smooth neighbouring buckets
    smooth = {}
    for d, v in votes.items():
        smooth[d] = v + 0.5 * votes.get(d - 1, 0) + 0.5 * votes.get(d + 1, 0)
    best = sorted(smooth.items(), key=lambda x: -x[1])[:4]
    return [(d * bucket + bucket // 2, v) for d, v in best]


def _refine(a, b, ratio, center, span, step):
    """Best offset; on a plateau of equal scores take its middle (padded subs)."""
    scores = []
    off = center - span
    while off <= center + span:
        scores.append((off, _overlap(_transform(a, ratio, off), b)))
        off += step
    best_score = max(sc for _, sc in scores)
    if best_score <= 0:
        return center, 0
    k = max(range(len(scores)), key=lambda i: scores[i][1])
    lo = hi = k
    while lo > 0 and scores[lo - 1][1] >= best_score * 0.997:
        lo -= 1
    while hi < len(scores) - 1 and scores[hi + 1][1] >= best_score * 0.997:
        hi += 1
    mid = (scores[lo][0] + scores[hi][0]) // 2
    return mid, _overlap(_transform(a, ratio, mid), b)


def global_align(cues, ref_cues):
    a = _intervals(cues)
    b = _intervals(ref_cues)
    if len(a) < 10 or len(b) < 10:
        return None
    b_starts = [s for s, _ in b]
    cands = []
    for ratio in FPS_RATIOS:
        a_starts = sorted(int(s * ratio) for s, _ in a)
        for cand, votes in _vote(a_starts, b_starts):
            cands.append((votes, ratio, cand))
    cands.sort(key=lambda x: -x[0])
    best = (1.0, 0, -1)
    for _v, ratio, cand in cands[:8]:
        if True:
            off, sc = _refine(a, b, ratio, cand, 600, 50)
            off, sc = _refine(a, b, ratio, off, 60, 10)
            if sc > best[2]:
                best = (ratio, off, sc)
    ratio, off, score = best
    # chance level: overlap at clearly wrong offsets
    rnd = sorted(_overlap(_transform(a, ratio, off + d), b)
                 for d in list(range(-600000, -150000, 45000)) + list(range(150000, 600000, 45000)))
    chance = rnd[len(rnd) // 2] or 1
    dur_a = sum(e - s for s, e in a)
    dur_b = sum(e - s for s, e in b)
    base = _overlap(a, b)
    return {'ratio': ratio, 'offset': off, 'score': score,
            'quality': score / float(min(dur_a, dur_b) or 1),
            'before': base / float(min(dur_a, dur_b) or 1),
            'lift': score / float(chance)}


def _local_offsets(a, b, window=40, span=9000, step=50, min_abs=0.45):
    """Per-window offset correction after global transform (a already transformed)."""
    res = []
    for w0 in range(0, len(a), window // 2):
        seg = a[w0:w0 + window]
        if len(seg) < 8:
            break
        lo = bisect.bisect_left(b, (seg[0][0] - span - 2000, 0))
        hi = bisect.bisect_right(b, (seg[-1][1] + span + 2000, 0))
        ref = b[lo:hi]
        if len(ref) < 5:
            res.append((w0, 0, 0.0))
            continue
        base = _overlap(seg, ref)
        off, sc = _refine(seg, ref, 1.0, 0, span, step)
        off, sc = _refine(seg, ref, 1.0, off, step, 10)
        seg_dur = sum(e - s for s, e in seg) or 1
        gain = (sc - base) / float(seg_dur)
        res.append((w0, off if gain > 0.06 and sc / float(seg_dur) > min_abs else 0, gain))
    return res


def _median(vals):
    v = sorted(vals)
    return v[len(v) // 2] if v else 0


def align(cues, ref_cues, local=True, min_quality=0.35, min_lift=1.6, local_min_abs=0.45):
    """Returns (new_cues_or_None, info). Modifies copies, not the input."""
    from .subtitle import Cue
    g = global_align(cues, ref_cues)
    if not g:
        return None, {'reason': 'too_few_cues'}
    if g['lift'] < min_lift or g['quality'] < min_quality:
        g['reason'] = 'low_quality'
        return None, g
    ratio, off = g['ratio'], g['offset']
    out = [Cue(int(c.start * ratio + off), int(c.end * ratio + off), c.text) for c in cues]
    g['local_fixes'] = 0
    if local:
        a = _intervals(out)
        b = sorted(_intervals(ref_cues))
        locs = _local_offsets(a, b, min_abs=local_min_abs)
        if locs:
            # assign each cue the median of offsets from windows covering it
            per_cue = [[] for _ in out]
            for w0, o, _gain in locs:
                for k in range(w0, min(w0 + 40, len(out))):
                    per_cue[k].append(o)
            offs = [_median(x) for x in per_cue]
            # smooth: median over 9 neighbours to avoid jitter
            sm = []
            for k in range(len(offs)):
                sm.append(_median(offs[max(0, k - 4):k + 5]))
            if any(sm):
                cand = [Cue(c.start + o, c.end + o, c.text) for c, o in zip(out, sm)]
                if _overlap(sorted(_intervals(cand)), b) > _overlap(sorted(a), b):
                    out = cand
                    g['local_fixes'] = sum(1 for o in sm if o)
        final = _overlap(sorted(_intervals(out)), b)
        dur = min(sum(e - s for s, e in _intervals(out)), sum(e - s for s, e in b)) or 1
        g['quality'] = final / float(dur)
    out.sort(key=lambda c: c.start)
    for c in out:
        if c.start < 0:
            c.start = 0
        if c.end <= c.start:
            c.end = c.start + 500
    return out, g


def describe(info):
    """Short Arabic description of what was done."""
    parts = []
    if abs(info.get('ratio', 1.0) - 1.0) > 1e-4:
        parts.append('تحويل سرعة ×%.4f' % info['ratio'])
    off = info.get('offset', 0) / 1000.0
    if abs(off) >= 0.05:
        parts.append('إزاحة %+.2f ث' % off)
    if info.get('local_fixes'):
        parts.append('تصحيح %d سطر موضعياً' % info['local_fixes'])
    return '، '.join(parts) if parts else 'التوقيت مضبوط أصلاً'
