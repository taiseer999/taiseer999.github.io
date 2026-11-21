# -*- coding: utf-8 -*-
"""Audio-based sync: listen to the video's audio track with ffmpeg, detect where
people speak, and align the subtitle to that speech.

ffmpeg decodes the audio to 8 kHz mono PCM (speech band only); voice activity is
detected per 20 ms frame with an adaptive energy threshold; the resulting speech
segments become a 'reference' for sync.align()."""
import array
import glob
import math
import os
import re
import shutil
import subprocess
import sys
import threading
import urllib.parse

try:
    import audioop  # C speed-up (Python <= 3.12, which Kodi 21 uses)
except ImportError:  # pragma: no cover
    audioop = None

from .subtitle import Cue

_SUMPROD = getattr(math, 'sumprod', None)

RATE = 8000
FRAME_MS = 20
FRAME_BYTES = RATE * FRAME_MS // 1000 * 2


class AudioSyncError(Exception):
    pass


# ------------------------------------------------------------------ ffmpeg
ADDON_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUNDLED = os.path.join(ADDON_DIR, 'bin', 'windows', 'ffmpeg.exe')


def find_ffmpeg(configured=''):
    cands = []
    if configured:
        cands.append(configured)
        if os.path.isdir(configured):
            cands += [os.path.join(configured, 'ffmpeg.exe'), os.path.join(configured, 'ffmpeg'),
                      os.path.join(configured, 'bin', 'ffmpeg.exe')]
    if sys.platform.startswith('win'):
        cands.append(BUNDLED)                     # built into the add-on
    w = shutil.which('ffmpeg')
    if w:
        cands.append(w)
    if sys.platform.startswith('win'):
        la = os.environ.get('LOCALAPPDATA', '')
        pf = os.environ.get('ProgramFiles', r'C:\Program Files')
        cands += [os.path.join(la, 'Microsoft', 'WinGet', 'Links', 'ffmpeg.exe')]
        cands += glob.glob(os.path.join(la, 'Microsoft', 'WinGet', 'Packages', '*FFmpeg*', '*', 'bin', 'ffmpeg.exe'))
        cands += [r'C:\ffmpeg\bin\ffmpeg.exe', os.path.join(pf, 'ffmpeg', 'bin', 'ffmpeg.exe'),
                  r'C:\ProgramData\chocolatey\bin\ffmpeg.exe',
                  os.path.join(os.environ.get('USERPROFILE', ''), 'scoop', 'shims', 'ffmpeg.exe')]
    else:
        cands += ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/opt/homebrew/bin/ffmpeg',
                  '/storage/.kodi/addons/tools.ffmpeg-tools/bin/ffmpeg']
        try:   # Piers edition: CoreELEC's ffmpeg-tools wherever Kodi's home is
            import xbmcvfs
            cands.append(xbmcvfs.translatePath(
                'special://home/addons/tools.ffmpeg-tools/bin/ffmpeg'))
        except Exception:
            pass
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


MF = 'mf'          # engine id for Windows Media Foundation (no ffmpeg)
_engine_cache = {}


def _ffmpeg_runs(path):
    try:
        kw = {'creationflags': 0x08000000} if sys.platform.startswith('win') else {}
        p = subprocess.run([path, '-hide_banner', '-version'], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=20, **kw)
        return p.returncode == 0, ''
    except Exception as e:      # e.g. [WinError 4551] blocked by Smart App Control
        return False, str(e)


def find_engine(configured=''):
    """Best working audio reader: ffmpeg if it is allowed to run, else Windows' own
    Media Foundation. Returns an ffmpeg path, MF, or None."""
    if configured in _engine_cache:
        return _engine_cache[configured]
    engine = None
    seen = set()
    for cand in [find_ffmpeg(configured)] + ([BUNDLED] if sys.platform.startswith('win') else []):
        if cand and cand not in seen and os.path.isfile(cand):
            seen.add(cand)
            ok, err = _ffmpeg_runs(cand)
            if ok:
                engine = cand
                break
            _engine_cache['last_error'] = err
    if engine is None:
        from . import winaudio
        if winaudio.available():
            engine = MF
    _engine_cache[configured] = engine
    return engine


def _wav(pcm, rate=RATE):
    import struct
    return (b'RIFF' + struct.pack('<I', 36 + len(pcm)) + b'WAVEfmt ' +
            struct.pack('<IHHIIHH', 16, 1, 1, rate, rate * 2, 2, 16) +
            b'data' + struct.pack('<I', len(pcm)) + pcm)


def media_source(path):
    """Kodi path → (input for ffmpeg, extra ffmpeg args, is_remote)."""
    if not path:
        raise AudioSyncError('no_path')
    if path.startswith(('plugin://', 'pvr://', 'stack://', 'rtmp')):
        raise AudioSyncError('unsupported_path')
    if path.startswith(('http://', 'https://')):
        url, _, hdrs = path.partition('|')
        args = []
        if hdrs:
            h = dict(urllib.parse.parse_qsl(hdrs))
            ua = h.pop('User-Agent', None)
            if ua:
                args += ['-user_agent', ua]
            if h:
                args += ['-headers', ''.join('%s: %s\r\n' % kv for kv in h.items())]
        return url, args, True
    if path.startswith('smb://') and sys.platform.startswith('win'):
        return '\\\\' + urllib.parse.unquote(path[6:]).replace('/', '\\'), [], False
    if path.startswith(('smb://', 'nfs://', 'ftp://', 'sftp://', 'dav')):
        raise AudioSyncError('unsupported_path')
    return path, [], False


def _run_ffmpeg(ffmpeg, src, args, start=None, dur=None, track=None, timeout=900, abort=None):
    if ffmpeg == MF:
        from . import winaudio
        try:
            return winaudio.read_pcm(src, start or 0.0, dur, abort=abort)
        except winaudio.WinAudioError as e:
            raise AudioSyncError('aborted' if 'aborted' in str(e) else 'windows audio: %s' % e)
    cmd = [ffmpeg, '-nostdin', '-hide_banner', '-loglevel', 'error'] + args
    if start:
        cmd += ['-ss', '%.3f' % start]
    cmd += ['-i', src]
    if dur:
        cmd += ['-t', '%.3f' % dur]
    cmd += ['-map', '0:a:%d?' % track if track is not None else '0:a:0?',
            '-vn', '-sn', '-dn', '-ac', '1', '-ar', str(RATE),
            '-af', 'highpass=f=250,lowpass=f=3400',
            '-f', 's16le', '-']
    kw = {}
    if sys.platform.startswith('win'):
        kw['creationflags'] = 0x08000000  # CREATE_NO_WINDOW
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)
    timer = threading.Timer(timeout, proc.kill)
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
                raise AudioSyncError('aborted')
        err = proc.stderr.read().decode('utf-8', 'replace')
        proc.wait()
    finally:
        timer.cancel()
    data = b''.join(chunks)
    if not data:
        raise AudioSyncError('ffmpeg: %s' % (err.strip()[-300:] or 'no audio'))
    return data


CLIP_FORMATS = [  # (ffmpeg output args, mime) — first one that works is used
    (['-ar', '16000', '-c:a', 'libmp3lame', '-b:a', '32k', '-f', 'mp3'], 'audio/mp3'),
    (['-ar', '16000', '-c:a', 'aac', '-b:a', '40k', '-f', 'adts'], 'audio/aac'),
    (['-ar', '16000', '-c:a', 'libopus', '-b:a', '24k', '-f', 'ogg'], 'audio/ogg'),
    (['-ar', '16000', '-c:a', 'flac', '-f', 'flac'], 'audio/flac'),
    (['-ar', '8000', '-c:a', 'pcm_s16le', '-f', 'wav'], 'audio/wav'),
]
_clip_fmt = [None]


def extract_clip(ffmpeg, src, args, start, dur, track=None, timeout=300):
    """Compressed mono clip (for sending to Gemini). Returns (bytes, mime)."""
    if ffmpeg == MF:
        pcm = _run_ffmpeg(MF, src, args, start=start, dur=dur)
        if len(pcm) < 16000:
            raise AudioSyncError('no audio in clip')
        return _wav(pcm), 'audio/wav'
    kw = {}
    if sys.platform.startswith('win'):
        kw['creationflags'] = 0x08000000
    order = [_clip_fmt[0]] if _clip_fmt[0] is not None else range(len(CLIP_FORMATS))
    last = ''
    for idx in order:
        out_args, mime = CLIP_FORMATS[idx]
        cmd = [ffmpeg, '-nostdin', '-hide_banner', '-loglevel', 'error'] + args + \
              ['-ss', '%.3f' % start, '-i', src, '-t', '%.3f' % dur,
               '-map', '0:a:%d?' % (track or 0), '-vn', '-sn', '-dn', '-ac', '1'] + out_args + ['-']
        try:
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               timeout=timeout, **kw)
        except subprocess.TimeoutExpired:
            raise AudioSyncError('ffmpeg timeout')
        if p.returncode == 0 and len(p.stdout) > 1000:
            _clip_fmt[0] = idx
            return p.stdout, mime
        last = p.stderr.decode('utf-8', 'replace')[-200:]
    raise AudioSyncError('ffmpeg clip: %s' % last)


# ------------------------------------------------------------------ VAD
def _frame_db(pcm):
    n = len(pcm) // FRAME_BYTES
    out = []
    if audioop:
        for i in range(n):
            r = audioop.rms(pcm[i * FRAME_BYTES:(i + 1) * FRAME_BYTES], 2)
            out.append(20 * math.log10(r + 1))
    else:
        a = array.array('h')
        a.frombytes(pcm[:n * FRAME_BYTES])
        if sys.byteorder == 'big':
            a.byteswap()
        step = FRAME_BYTES // 2
        for i in range(n):
            seg = a[i * step:(i + 1) * step]
            # Python 3.12+ (Kodi 22: 3.14) has no audioop; math.sumprod is the
            # C-speed sum of squares (Piers edition), the generator the fallback
            r = math.sqrt((_SUMPROD(seg, seg) if _SUMPROD else sum(x * x for x in seg)) / float(step))
            out.append(20 * math.log10(r + 1))
    return out


def _pct(sorted_vals, p):
    if not sorted_vals:
        return 0
    return sorted_vals[min(len(sorted_vals) - 1, int(len(sorted_vals) * p))]


def detect_speech(pcm, offset_ms=0, block_s=30):
    """PCM → list of speech Cue(start,end) in ms (offset_ms added)."""
    db = _frame_db(pcm)
    if not db:
        return []
    per_block = block_s * 1000 // FRAME_MS
    active = []
    glob_sorted = sorted(db)
    g_floor = _pct(glob_sorted, 0.15)
    for b0 in range(0, len(db), per_block):
        blk = db[b0:b0 + per_block]
        s = sorted(blk)
        floor = max(_pct(s, 0.15), g_floor - 6)
        loud = _pct(s, 0.95)
        rng = loud - floor
        if rng < 6:            # silence / steady noise in this block
            active += [False] * len(blk)
            continue
        hi = floor + rng * 0.45
        lo = floor + rng * 0.30
        on = False
        for v in blk:          # hysteresis
            if on:
                on = v > lo
            else:
                on = v > hi
            active.append(on)
    segs = []
    start = None
    for i, a in enumerate(active + [False]):
        if a and start is None:
            start = i
        elif not a and start is not None:
            segs.append([start * FRAME_MS, i * FRAME_MS])
            start = None
    merged = []
    for s in segs:
        if merged and s[0] - merged[-1][1] < 300:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    return [Cue(s + offset_ms, e + offset_ms, '') for s, e in merged if 250 <= e - s <= 15000]


# ------------------------------------------------------------------ main
def speech_reference(ffmpeg, path, duration_s, mode='auto', track=None,
                     progress=None, abort=None):
    """Return speech segments for the video. mode: full | sample | auto."""
    src, args, remote = media_source(path)
    if mode == 'auto':
        mode = 'sample' if remote else 'full'
    if mode == 'full' or not duration_s or duration_s < 20 * 60:
        if progress:
            progress(5, 'استخراج الصوت من الفيديو...')
        pcm = _run_ffmpeg(ffmpeg, src, args, track=track, abort=abort,
                          timeout=1800 if remote else 900)
        if progress:
            progress(70, 'تحليل الكلام...')
        return detect_speech(pcm)
    # sample mode: several windows across the video (fast, works on streams)
    if remote:
        n, win = 4, 75.0      # light: ~5 min of a stream in total, one piece at a time
    else:
        n, win = 10, 210.0
    starts = [duration_s * (0.03 + 0.92 * k / (n - 1)) for k in range(n)]
    starts = [max(0.0, min(s, duration_s - win)) for s in starts]
    result = [None] * n
    errors = []
    done = [0]
    lock = threading.Lock()

    def work(k):
        try:
            pcm = _run_ffmpeg(ffmpeg, src, args, start=starts[k], dur=win, track=track,
                              abort=abort, timeout=300)
            result[k] = detect_speech(pcm, offset_ms=int(starts[k] * 1000))
        except Exception as e:
            errors.append(e)
        with lock:
            done[0] += 1
            if progress:
                progress(5 + done[0] * 65 // n, 'الاستماع إلى الصوت (%d/%d)...' % (done[0], n))
    threads = []
    for k in range(n):
        t = threading.Thread(target=work, args=(k,))
        t.start()
        threads.append(t)
        if len(threads) >= (1 if remote else 2 if ffmpeg == MF else 3):
            threads.pop(0).join()
    for t in threads:
        t.join()
    segs = [c for r in result if r for c in r]
    if not segs and errors:
        raise AudioSyncError(str(errors[0]))
    return segs


def describe_error(e):
    m = str(e)
    if 'no_ffmpeg' in m:
        return 'أداة قراءة الصوت غير متوفرة على هذا الجهاز'
    if 'windows audio' in m:
        return 'تعذر على ويندوز قراءة صوت هذا الملف (صيغة صوت غير مدعومة مثل DTS)'
    if 'unsupported_path' in m:
        return 'مصدر الفيديو لا يدعم الاستماع إلى الصوت (رابط إضافة أو شبكة غير مدعومة)'
    if 'aborted' in m:
        return 'توقفت المزامنة الصوتية'
    return 'تعذر تحليل الصوت: %s' % m[:120]
