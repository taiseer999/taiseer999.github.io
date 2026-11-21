# -*- coding: utf-8 -*-
"""Listen to the film's own speech with Whisper (Groq's free tier) and get every spoken
sentence with its exact time, translated to English. That becomes the timing reference
for the Arabic subtitle — whatever release it was made for, however sloppy its timing.

No heavy library on the box: ffmpeg cuts small WAV pieces, Groq does the listening."""
import json
import time
import uuid

try:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
except ImportError:                                     # pragma: no cover
    from urllib2 import Request, urlopen, HTTPError, URLError

from .common import log, cache_get, cache_put
from .subtitle import Cue

URL = 'https://api.groq.com/openai/v1/audio/translations'
MODEL = 'whisper-large-v3'          # the one that can translate to English
RATE = 16000
LOCAL_CHUNK = 360                   # a local file: listen to all of it, 6 minutes at a time
STREAM_WINDOWS = 12                 # a stream: 12 pieces spread over the film...
STREAM_LEN = 90                     # ...of 90 s each (little to download)


class WhisperError(Exception):
    pass


def api_key():
    try:
        from . import llm
        return llm.key_for('groq') or ''
    except Exception:
        return ''


def available():
    return bool(api_key())


def _wav(pcm):
    import struct
    n = len(pcm)
    return (b'RIFF' + struct.pack('<I', 36 + n) + b'WAVEfmt ' +
            struct.pack('<IHHIIHH', 16, 1, 1, RATE, RATE * 2, 2, 16) + b'data' + struct.pack('<I', n) + pcm)


def _post(wav, key, timeout=120):
    boundary = uuid.uuid4().hex
    parts = []
    for name, val in (('model', MODEL), ('response_format', 'verbose_json'), ('temperature', '0')):
        parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n'
                      % (boundary, name, val)).encode('utf-8'))
    parts.append(('--%s\r\nContent-Disposition: form-data; name="file"; filename="a.wav"\r\n'
                  'Content-Type: audio/wav\r\n\r\n' % boundary).encode('utf-8') + wav + b'\r\n')
    body = b''.join(parts) + ('--%s--\r\n' % boundary).encode('utf-8')
    req = Request(URL, data=body, headers={'Authorization': 'Bearer ' + key,
                                           'Content-Type': 'multipart/form-data; boundary=' + boundary,
                                           'User-Agent': 'najdsmart'})
    for attempt in range(3):
        try:
            return json.loads(urlopen(req, timeout=timeout).read().decode('utf-8'))
        except HTTPError as e:
            if e.code == 429:
                wait = 20
                try:
                    wait = int(float(e.headers.get('retry-after') or 20)) + 1
                except (TypeError, ValueError):
                    pass
                if wait > 90 or attempt >= 2:
                    # the hourly/daily allowance is used up: stop, keep what was heard, go on later
                    raise WhisperError('limit')
                log('whisper: Groq says wait %ds' % wait)
                time.sleep(wait)
                continue
            if e.code in (401, 403):
                raise WhisperError('key')
            raise WhisperError('http_%d' % e.code)
        except (URLError, OSError, ValueError) as e:
            if attempt < 2:
                time.sleep(5)
                continue
            raise WhisperError('net: %s' % e)
    raise WhisperError('busy')


def segments(data, offset_ms):
    out = []
    for s in data.get('segments') or []:
        text = (s.get('text') or '').strip()
        # Whisper's "made up" lines over music/silence come with a high no-speech score
        if not text or float(s.get('no_speech_prob') or 0) > 0.6:
            continue
        a = offset_ms + int(float(s.get('start') or 0) * 1000)
        b = offset_ms + int(float(s.get('end') or 0) * 1000)
        if b > a:
            out.append(Cue(a, b, text))
    return out


def listen(ffmpeg, src, args, start_s, dur_s, key, abort=None):
    """One piece of the film → English sentences with their times in the film."""
    """Returns (cues, seconds actually heard) — a damaged or short piece only covers what was read."""
    pcm = _pcm16(ffmpeg, src, args, start_s, dur_s, abort)
    heard = len(pcm) / float(RATE * 2)
    if heard < 5:
        return [], 0
    return segments(_post(_wav(pcm), key), int(start_s * 1000)), heard


def _pcm16(ffmpeg, src, args, start_s, dur_s, abort):
    """16 kHz mono speech audio (Whisper's own rate); the dialogue channel when there is one."""
    import subprocess
    import sys
    import threading
    from . import audiosync
    pre = 'pan=mono|c0=FC,' if audiosync._has_center(ffmpeg, src, args, None) else ''
    cmd = [ffmpeg, '-nostdin', '-hide_banner', '-loglevel', 'error']
    if start_s:
        cmd += ['-ss', '%.3f' % start_s]
    cmd += args + ['-i', src, '-t', '%.3f' % dur_s, '-map', '0:a:0', '-vn', '-sn', '-dn',
                   '-af', pre + 'aformat=channel_layouts=mono', '-ar', str(RATE), '-f', 's16le', '-']
    kw = {'creationflags': 0x08000000} if sys.platform.startswith('win') else {}
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, **kw)
    timer = threading.Timer(300, proc.kill)
    timer.start()
    chunks = []
    try:
        while True:
            buf = proc.stdout.read(1 << 16)
            if not buf:
                break
            chunks.append(buf)
            if abort and abort():
                proc.kill()
                raise WhisperError('aborted')
        proc.wait()
    finally:
        timer.cancel()
    return b''.join(chunks)


PROBE_WINDOWS = 8                   # first look: 8 one-minute pieces spread over the film
PROBE_LEN = 60
MORE_STREAM = 16                    # a sloppy subtitle on a stream: 16 more minutes
FREE_DAY_S = 8 * 3600               # Groq's free tier: about 8 hours of sound a day


def _spread(duration_s, n, length, phase=0.0):
    lo, hi = 0.03 * duration_s, 0.95 * duration_s - length
    if hi <= lo:
        return [(0, int(min(duration_s, length)))]
    step = (hi - lo) / float(n)
    return [(int(lo + (k + phase) * step), length) for k in range(n)]


def _overlaps(a, b, covered):
    return any(a * 1000 < y and x < b * 1000 for x, y in covered)


def plan(duration_s, remote, position_s=0, stage='probe', covered=()):
    """Which pieces to listen to: (start_s, length_s), most useful first."""
    n = PROBE_WINDOWS if duration_s >= 40 * 60 else 5       # a short episode: fewer pieces
    if stage == 'probe':
        wins = _spread(duration_s, n, PROBE_LEN, 0.5)
    elif stage == 'probe2':
        wins = _spread(duration_s, n, PROBE_LEN, 0.0)
    elif remote:
        wins = _spread(duration_s, MORE_STREAM, PROBE_LEN, 0.5)    # between the probe pieces
    else:
        # a local file: every gap between what was already heard, in pieces of up to 6 minutes
        wins, t = [], 0
        for x, y in sorted(covered) + [(int(duration_s * 1000), None)]:
            gap_end = x / 1000
            while gap_end - t >= 5:
                n = int(min(LOCAL_CHUNK, gap_end - t))
                wins.append((int(t), n))
                t += n
            t = max(t, (y or 0) / 1000)
        return _order(wins, position_s)
    wins = [(s, n) for s, n in wins if not _overlaps(s, s + n, covered)]
    return _order(wins, position_s)


def _order(wins, position_s):
    if position_s:
        # from where the viewer is onwards first; what is already behind them comes last
        wins.sort(key=lambda w: (w[0] + w[1] < position_s, abs(w[0] - position_s)))
    return wins


# ---- daily budget (free tier is shared by everything on this key)
def _usage():
    from .common import cache_json
    d = cache_json('whisper_usage.json', 3 * 86400) or {}
    return d if d.get('day') == time.strftime('%Y-%m-%d') else {'day': time.strftime('%Y-%m-%d'), 'used': 0}


def budget_left():
    from .common import setting_int
    cap = min(FREE_DAY_S, max(10, setting_int('whisper_daily_min', 120)) * 60)
    return cap - int(_usage().get('used', 0))


def _spend(seconds):
    u = _usage()
    u['used'] = int(u.get('used', 0) + max(10, seconds))     # Groq bills at least 10 s a request
    cache_put('whisper_usage.json', json.dumps(u))


def used_today():
    return int(_usage().get('used', 0))


def reference(video, key_name, ffmpeg, progress=None, abort=None, position_s=0, stage='probe'):
    """English sentences with exact times, from the film's own sound (cached and added to).
    stage 'probe' = a few minutes spread over the film; 'more' = the rest (a local file:
    all of it, from where you are watching; a stream: more pieces).
    Returns (cues, covered [(a_ms, b_ms)])."""
    from . import audiosync
    cache_name = 'whisper_%s.json' % key_name
    cues, covered, stages = [], [], []
    c = cache_get(cache_name, 365 * 86400)
    if c:
        try:
            d = json.loads(c.decode('utf-8'))
            cues = [Cue(a, b, t) for a, b, t in d['cues']]
            covered = [tuple(x) for x in d['covered']]
            stages = d.get('stages') or ['probe', 'more']
        except (ValueError, KeyError, TypeError):
            cues, covered, stages = [], [], []
    if stage in stages:
        return cues, covered
    key = api_key()
    if not key:
        raise WhisperError('no_key')
    if not ffmpeg or ffmpeg == getattr(audiosync, 'MF', None):
        raise WhisperError('no_ffmpeg')
    src, args, remote = audiosync.media_source(video.get('path'))
    dur = float(video.get('duration') or 0)
    if dur < 60:
        raise WhisperError('no_duration')
    pieces = plan(dur, remote, position_s, stage, covered)
    complete = True

    def save():
        cues.sort(key=lambda c: c.start)
        cache_put(cache_name, json.dumps({'cues': [[c.start, c.end, c.text] for c in cues],
                                          'covered': covered,
                                          'stages': stages + ([stage] if complete else [])},
                                         ensure_ascii=False))

    for k, (s, ln) in enumerate(pieces):
        if abort and abort():
            save()                                      # what was heard is kept for next time
            raise WhisperError('aborted')
        if budget_left() < ln:
            log('whisper: daily limit reached (%d s used today)' % used_today())
            complete = False
            break
        if progress:
            progress(int(100 * k / len(pieces)), 'Whisper يسمع كلام الفيلم (%d/%d)...' % (k + 1, len(pieces)))
        try:
            got, heard = listen(ffmpeg, src, args, s, ln, key, abort)
        except WhisperError as e:
            if str(e) in ('key', 'aborted'):
                save()
                raise
            if str(e) == 'limit':
                log('whisper: Groq allowance used up for now; the rest comes next time')
                complete = False
                break
            log('whisper: piece @%ds failed: %s' % (s, e))
            continue
        if heard < 5:
            log('whisper: piece @%ds could not be read' % s)
            continue
        _spend(heard)
        cues.extend(got)
        covered.append((int(s * 1000), int((s + heard) * 1000)))
        log('whisper: piece @%ds (%.0fs heard) → %d sentences' % (s, heard, len(got)))
    save()
    if len(cues) < 10:
        raise WhisperError('too_little_speech')
    covered.sort()
    return cues, covered
