# -*- coding: utf-8 -*-
"""'Understanding' sync: Gemini listens to the film's audio and tells us WHEN each
subtitle line is actually said (matching by meaning, even across languages).

Flow:
  1. Cut the audio into ~6-minute clips (ffmpeg → small mp3).
  2. For each clip send the audio + the subtitle lines that should fall inside it
     (with their current approximate time) to Gemini; it returns, for every line it
     hears, the start/end in seconds inside the clip.
  3. Clean the answers (keep chronological order, drop outliers), then move every
     line: matched lines to where they were heard, unmatched lines by interpolation
     between their matched neighbours.
  4. Snap each line onto the exact start of speech detected in the audio (VAD) so
     the result is frame-accurate even though Gemini's clock is ~0.5 s precise.
"""
import base64
import bisect
import concurrent.futures
import json
import threading

from . import arabic
from .audiosync import AudioSyncError, extract_clip, media_source
from .common import http, log

API = 'https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent'

PROMPT = (
    'You are a professional subtitle timing engine.\n'
    'The attached audio is a %(dur)d-second excerpt from a film or TV episode. '
    'Below is a JSON list of subtitle lines (Arabic translation; the spoken dialogue may be '
    'in English or another language). Each line has an "id", its text "t" and "approx", '
    'the second inside this excerpt where it is currently placed (may be wrong by up to '
    'about a minute, or the line may not be in this excerpt at all).\n'
    'Listen to the dialogue. For every line whose dialogue is actually spoken in this '
    'audio, return its id and the exact time the speaker STARTS saying it and FINISHES, '
    'in seconds from the beginning of this audio, with one decimal (e.g. 83.4). '
    'Match by meaning, not by words. Lines are in chronological order and so are the '
    'answers. Omit lines you cannot clearly hear in this excerpt; never guess. '
    'Ignore songs, background TV and crowd noise unless the line is a translation of them.\n'
    'Subtitle lines:\n%(lines)s'
)

SCHEMA = {
    'type': 'ARRAY',
    'items': {'type': 'OBJECT',
              'properties': {'id': {'type': 'INTEGER'},
                             'start': {'type': 'NUMBER'},
                             'end': {'type': 'NUMBER'}},
              'required': ['id', 'start', 'end']},
}

CLIP = 360.0      # seconds of audio per request
OVERLAP = 20.0
MARGIN = 75.0     # include lines currently placed this far outside the clip
MAX_CLIPS = 12    # cap on uploads per film (~70 min of a 2 h film)


def _ask(api_key, model, audio, mime, lines, dur):
    body = {
        'contents': [{'role': 'user', 'parts': [
            {'inline_data': {'mime_type': mime, 'data': base64.b64encode(audio).decode('ascii')}},
            {'text': PROMPT % {'dur': int(dur), 'lines': json.dumps(lines, ensure_ascii=False)}},
        ]}],
        'generationConfig': {'responseMimeType': 'application/json', 'responseSchema': SCHEMA},
    }
    from . import gemini
    text = gemini.generate(body, timeout=150)
    out = []
    for d in json.loads(text):
        try:
            s, e = float(d['start']), float(d['end'])
            if 0 <= s <= dur + 1 and e >= s:
                out.append((int(d['id']), s, min(e, s + 20)))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _lis(pairs):
    """Longest chain increasing in both id and time (drops out-of-order matches)."""
    pairs = sorted(pairs)                       # by id
    tails, prev, idx = [], [-1] * len(pairs), []
    for i, (_cid, t) in enumerate(pairs):
        k = bisect.bisect_left(tails, t)
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


def collect_anchors(cues, ffmpeg, path, duration_s, api_key, model,
                    progress=None, abort=None, workers=2, asker=None):
    """Ask Gemini clip by clip. Returns {cue_index: (start_ms, end_ms)}."""
    src, args, _remote = media_source(path)
    if not duration_s:
        duration_s = max(c.end for c in cues) / 1000.0 + 30
    clips = []
    t = 0.0
    while t < duration_s - 5:
        clips.append((t, min(CLIP, duration_s - t)))
        t += CLIP - OVERLAP
    if len(clips) > MAX_CLIPS:
        # long films: listen to evenly spread clips only (less upload, faster);
        # lines between them are placed from their neighbours + the speech detector
        step = (len(clips) - 1) / float(MAX_CLIPS - 1)
        clips = [clips[int(round(k * step))] for k in range(MAX_CLIPS)]
    ask = asker or _ask
    found = {}             # idx -> (start_ms, end_ms, edge_distance)
    lock = threading.Lock()
    done = [0]
    errors = []

    def work(clip):
        if abort and abort():
            return
        c0, cd = clip
        lines = []
        for i, c in enumerate(cues):
            st = c.start / 1000.0
            if c0 - MARGIN <= st <= c0 + cd + MARGIN:
                txt = arabic.plain(c.text).replace('\n', ' ')
                lines.append({'id': i, 't': txt, 'approx': round(st - c0, 1)})
        if not lines:
            res = []
        else:
            try:
                audio, mime = extract_clip(ffmpeg, src, args, c0, cd)
                res = ask(api_key, model, audio, mime, lines, cd)
            except Exception as e:
                errors.append(e)
                log('understand clip %.0f failed: %s' % (c0, e))
                res = []
        with lock:
            for cid, s, e in res:
                edge = min(s, cd - s)
                a = (int((c0 + s) * 1000), int((c0 + e) * 1000), edge)
                if cid not in found or found[cid][2] < edge:
                    found[cid] = a
            done[0] += 1
            if progress:
                progress(int(done[0] * 70 / len(clips)) + 10,
                         'فهم الكلام في الفيلم (%d/%d)...' % (done[0], len(clips)))

    # don't block on in-flight requests: when playback stops we leave at once
    ex = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
    futs = [ex.submit(work, c) for c in clips]
    try:
        while True:
            done, pending = concurrent.futures.wait(futs, timeout=0.5)
            if not pending:
                break
            if abort and abort():
                for f in pending:
                    f.cancel()
                raise AudioSyncError('aborted')
    finally:
        ex.shutdown(wait=False)
    if abort and abort():
        raise AudioSyncError('aborted')
    if not found and errors:
        raise AudioSyncError('gemini: %s' % errors[0])
    return {k: (v[0], v[1]) for k, v in found.items()}


def _speech_overlap(s, e, speech, sp_starts):
    k = max(0, bisect.bisect_right(sp_starts, s) - 1)
    tot = 0
    while k < len(speech) and speech[k].start < e:
        a, b = max(s, speech[k].start), min(e, speech[k].end)
        if b > a:
            tot += b - a
        k += 1
    return tot / float(max(1, e - s))


def _best_shift(c, prior, cons, speech, sp_starts, radius=1800, heard=None):
    """Pick the shift for one line: near what was heard (prior), landing on real speech."""
    base = c.start + prior
    cands = {prior, cons}
    refs = [cons] + ([heard] if heard is not None else [])
    k0 = bisect.bisect_left(sp_starts, base - radius)
    k1 = bisect.bisect_right(sp_starts, base + radius)
    for k in range(k0, k1):
        cands.add(sp_starts[k] - c.start)          # line starts exactly when speech starts
    dur = c.end - c.start
    best, best_sc = prior, -9
    for d in cands:
        s = c.start + d
        ov = _speech_overlap(s, s + min(dur, 4000), speech, sp_starts)
        onset = 0.15 if any(abs(s - x) < 60 for x in sp_starts[max(0, k0 - 1):k1 + 1]) else 0
        sc = ov + onset - min(abs(d - r) for r in refs) / 2500.0
        if sc > best_sc:
            best, best_sc = d, sc
    return best


def apply_anchors(cues, anchors, speech=None, max_jump=8000, snap=500):
    """Move cues using anchors. Returns (new_cues, info)."""
    from .subtitle import Cue
    n = len(cues)
    chain = _lis([(i, anchors[i][0]) for i in anchors if 0 <= i < n])
    # drop anchors whose shift disagrees strongly with their neighbours
    deltas = [(i, t - cues[i].start) for i, t in chain]
    good = []
    for k, (i, d) in enumerate(deltas):
        neigh = [x[1] for x in deltas[max(0, k - 6):k + 7]]
        if abs(d - _median(neigh)) <= 6000:
            good.append((i, d))
    info = {'matched': len(anchors), 'kept': len(good), 'lines': n}
    if len(good) < max(8, n * 0.15):
        info['reason'] = 'few_matches'
        return None, info
    idxs = [i for i, _ in good]
    dmap = dict(good)
    sp_starts = [x.start for x in speech] if speech else []
    out = []
    fixed_lines = 0
    for i, c in enumerate(cues):
        # consensus shift from neighbouring anchors (more precise than one answer)
        k = bisect.bisect_left(idxs, i)
        lo, hi = max(0, k - 5), min(len(good), k + 5)
        neigh = [good[j] for j in range(lo, hi) if good[j][0] != i]
        if neigh:
            # split on a cut: use the side the line is closer to if neighbours disagree a lot
            left = [d for j, d in neigh if j < i]
            right = [d for j, d in neigh if j > i]
            if left and right and abs(_median(left) - _median(right)) > 1500:
                prev_i = max(j for j, _ in neigh if j < i)
                next_i = min(j for j, _ in neigh if j > i)
                near_left = abs(c.start - cues[prev_i].start) <= abs(cues[next_i].start - c.start)
                cons = _median(left if near_left else right)
            else:
                cons = _median([d for _, d in neigh])
        else:
            cons = good[0][1]
        d = cons
        if i in dmap and abs(dmap[i] - cons) > 1200:
            fixed_lines += 1
        misplaced = i in dmap and abs(dmap[i] - cons) > 1200
        prior = dmap[i] if misplaced else cons
        if speech:
            d = _best_shift(c, prior, cons, speech, sp_starts, heard=dmap.get(i))
        else:
            d = prior if i in dmap and abs(dmap[i] - cons) > 1200 else cons
        out.append(Cue(c.start + int(d), c.end + int(d), c.text))
    info['fixed_lines'] = fixed_lines
    out.sort(key=lambda c: c.start)
    info['moved'] = sum(1 for a, b in zip(cues, sorted(out, key=lambda c: c.start))
                        if abs(a.start - b.start) > 300)
    return out, info


def describe(info):
    msg = 'تم فهم %d من %d سطراً' % (info.get('kept', 0), info.get('lines', 0))
    if info.get('fixed_lines'):
        msg += '، وتصحيح %d سطراً كان في غير موضعه' % info['fixed_lines']
    return msg
