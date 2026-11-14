# Seek Preview frame maker - from service.seekpreview 1.2.0 by easter478
# (https://github.com/easter478/kodi-seek-preview, commit e2b11ad), GPL-3.0-or-later,
# see LICENSE.txt in this folder. Used by AB Tools "Seek Preview" (resources/lib/seek_preview/engine.py).
# AB Tools changes (4.8.13): a frame that was asked for (a skip) is always tried, even after
# failures (prefetch still gives up after 6 in a row); ffmpeg's error text, the time each frame
# took and low-memory skips are reported through self.report; the streamed prefetch span is a
# parameter (span_remote).
# 4.8.14: the whole picture is kept (fit + black bars, no crop of scope films); smaller
# probe so a stream opens faster; a prefetch run is cut short when a skip asks for a frame;
# nearest() only answers within `reach` seconds (no picture from minutes away).
# 4.8.15: one worker kept free for the frame a skip asks for, plus `workers` prefetch workers
# running side by side (kodi.log 2026-11-11: ~4 s per frame on a 4K stream, one at a time);
# prefetch fills a coarse grid first (every 30 s), then the 10 s steps in between; faster
# decode (no loop filter, fast scaler) and one kept-alive HTTP connection per run.
# Frame making for Seek Preview. No Kodi imports here, so this file also runs in tests/ on a PC.
# One ffmpeg run per frame: seek to the nearest keyframe, decode that one picture, scale it, save a small JPEG.
import os, sys, time, shutil, platform, threading, subprocess

WIN = sys.platform.startswith('win')
NO_WINDOW = 0x08000000 if WIN else 0  # CREATE_NO_WINDOW: no console flashing up on Windows


def platform_keys():
    """Folder names under bin/ that can run on this machine, best first."""
    m = platform.machine().lower()
    if WIN:
        return ['windows-x86_64'] if m in ('amd64', 'x86_64') else []
    if sys.platform.startswith('linux'):
        if m in ('aarch64', 'arm64'):
            return ['linux-aarch64', 'linux-armv7']  # a 64-bit kernel usually runs 32-bit ARM programs too
        if m.startswith('arm'):
            return ['linux-armv7']
        if m in ('x86_64', 'amd64'):
            return ['linux-x86_64']
    return []


def runs(path):
    """True when this ffmpeg actually starts here (right CPU, allowed to execute)."""
    try:
        if not WIN and not os.access(path, os.X_OK):
            os.chmod(path, 0o755)  # a zip install drops the execute bit
        r = subprocess.run([path, '-hide_banner', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, creationflags=NO_WINDOW)
        return r.returncode == 0 and b'ffmpeg' in r.stdout[:200].lower()
    except Exception:
        return False


def find_ffmpeg(addon_dir, extra=()):
    """The ffmpeg to use: the one bundled in the add-on, else one already on the system. Returns (path, where)."""
    exe = 'ffmpeg.exe' if WIN else 'ffmpeg'
    for key in platform_keys():
        p = os.path.join(addon_dir, 'bin', key, exe)
        if os.path.isfile(p) and runs(p):
            return p, 'bundled ' + key
    for p in list(extra) + [shutil.which('ffmpeg') or '']:
        if p and os.path.isfile(p) and runs(p):
            return p, 'system'
    return '', ''


def prune(addon_dir, ffmpeg):
    """After install: drop the bundled builds for other kinds of device (about 200 MB), keep the one in use."""
    root = os.path.join(addon_dir, 'bin')
    keep = os.path.basename(os.path.dirname(ffmpeg))
    if os.path.dirname(os.path.dirname(os.path.abspath(ffmpeg))) != os.path.abspath(root):
        return 0  # not running a bundled build: leave everything, a later start may need one
    n = 0
    for d in os.listdir(root):
        p = os.path.join(root, d)
        if os.path.isdir(p) and d != keep:
            shutil.rmtree(p, True); n += 1
    return n


def memfree():
    """Bytes of memory the system can still give out (Linux); huge where it can't be read."""
    try:
        with open('/proc/meminfo') as f:
            return next(int(l.split()[1]) * 1024 for l in f if l.startswith('MemAvailable:'))
    except Exception:
        return 1 << 40


def command(ffmpeg, url, headers, t, width, height, out):
    cmd = []
    if not WIN:
        # low priority, and the first thing the kernel kills if memory runs out (never the player)
        cmd = ['sh', '-c', 'echo 1000 > /proc/self/oom_score_adj 2>/dev/null; exec "$@"', 'ff', 'nice', '-n', '15']
    cmd += [ffmpeg, '-nostdin', '-loglevel', 'error']
    if headers:
        cmd += ['-headers', headers]
    # -threads before -i limits the decoder: frame-threaded 4K HEVC holds a set of frames per core (hundreds of MB)
    if url.startswith(('http://', 'https://')):
        cmd += ['-multiple_requests', '1', '-seekable', '1']
    cmd += ['-threads', '1', '-probesize', '2000000', '-analyzeduration', '1000000',
            '-skip_frame', 'nokey', '-skip_loop_filter', 'all', '-ss', str(int(t)), '-noaccurate_seek', '-i', url, '-map', '0:v:0', '-frames:v', '1', '-an', '-sn', '-dn',
            '-threads', '1', '-sws_flags', 'fast_bilinear', '-vf', 'scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=black'
            % (width, height, width, height), '-q:v', '5', '-f', 'mjpeg', '-y', out]
    return cmd


class Frames(threading.Thread):
    """Makes the frame that was asked for first, then the ones around where the film is."""

    def __init__(self, ffmpeg, url, headers, folder, step=10, width=384, remote=False, stop=None, low_mem=450 << 20, wait=20):
        threading.Thread.__init__(self)
        self.daemon = True
        self.ffmpeg, self.url, self.headers, self.dir = ffmpeg, url, headers, folder
        self.step, self.width, self.height = max(2, int(step)), int(width), int(width) * 9 // 16 // 2 * 2
        self.remote, self.low_mem, self.wait = remote, low_mem, wait
        self.want, self.around, self.dur, self.stop, self.bad = None, 0, 0, False, 0
        self.all_stop = stop or threading.Event()
        self.ev = threading.Event()
        self.born = time.time()
        self.span_remote = 600
        self.report = None          # callable(kind, text) - AB Tools diagnostics
        self.made, self.failed = 0, 0
        self.failed_at = {}         # bucket -> time of its last failure (no retry for 20 s)
        self.workers = 2            # prefetch workers (one more is kept for asked frames)
        self.coarse = 30            # prefetch grid of the first pass, seconds
        self.busy = set()
        self.lock = threading.Lock()
        self.ask_ev = threading.Event()
        os.makedirs(folder, exist_ok=True)

    def _say(self, kind, text):
        if self.report:
            try:
                self.report(kind, text)
            except Exception:
                pass

    def path(self, b):
        return os.path.join(self.dir, '%06d.jpg' % b)

    def bucket(self, t):
        return int(t) // self.step * self.step

    def nearest(self, t, reach=900):
        """The frame for t, or the closest one made so far."""
        b = self.bucket(t)
        for d in range(0, reach, self.step):
            for x in (b - d, b + d):
                if x >= 0 and os.path.exists(self.path(x)):
                    return self.path(x)
        return ''

    def ask(self, t):
        b = self.bucket(t)
        if time.time() - self.failed_at.get(b, 0) < 20:
            return
        if not os.path.exists(self.path(b)) and b not in self.busy:
            self.want = b
            self.ask_ev.set()

    def halt(self):
        self.stop = True
        self.ev.set()
        self.ask_ev.set()

    def make(self, b, asked=False):
        p = self.path(b)
        if os.path.exists(p) or (self.bad > 5 and not asked):
            return
        free = memfree()
        if free < self.low_mem:  # never let a preview cost the player its memory
            self._say('lowmem', '%d MB free (needs %d MB)' % (free >> 20, self.low_mem >> 20))
            self.ev.wait(3); self.ev.clear(); return
        tmp = p + '.tmp'
        err = p + '.err'
        started = time.time()
        timed_out = False
        try:
            with open(err, 'wb') as ef:
                pr = subprocess.Popen(command(self.ffmpeg, self.url, self.headers, b, self.width, self.height, tmp),
                                      stdout=subprocess.DEVNULL, stderr=ef, creationflags=NO_WINDOW)
                end = time.time() + 20
                while pr.poll() is None:
                    if self.stop or self.all_stop.is_set() or time.time() > end:
                        timed_out = time.time() > end
                        pr.kill(); pr.wait(); break
                    time.sleep(0.05)
            took = time.time() - started
            if pr.returncode == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 0:
                os.replace(tmp, p); self.bad = 0; self.made += 1
                if self.made == 1 or took > 3:
                    self._say('made', 'frame %ds in %.1fs%s' % (b, took, ' (asked)' if asked else ''))
            elif not (self.stop or self.all_stop.is_set()):
                self.bad += 1; self.failed += 1; self.failed_at[b] = time.time()
                try:
                    with open(err, 'rb') as ef:
                        msg = ef.read()[-400:].decode('utf-8', 'replace').strip()
                except Exception:
                    msg = ''
                self._say('fail', 'frame %ds failed after %.1fs (%s, exit %s): %s'
                          % (b, took, 'timeout' if timed_out else 'error', pr.returncode, msg or '-'))
        except Exception as e:
            self.bad += 1; self.failed += 1; self.failed_at[b] = time.time()
            self._say('fail', 'frame %ds: %s' % (b, e))
        for x in (tmp, err):
            try:
                if os.path.exists(x): os.remove(x)
            except Exception:
                pass

    def _alive(self):
        return not self.stop and not self.all_stop.is_set()

    def _asked_worker(self):
        while self._alive():
            self.ask_ev.wait(1)
            self.ask_ev.clear()
            b = self.want
            if b is None:
                continue
            self.want = None
            with self.lock:
                if b in self.busy:
                    continue
                self.busy.add(b)
            try:
                self.make(b, asked=True)
            finally:
                with self.lock:
                    self.busy.discard(b)

    def _todo(self):
        """Next prefetch bucket outward from self.around: coarse grid first, then every step."""
        span = self.span_remote if self.remote else max(self.dur, 600)
        now = time.time()
        for grid in ((self.coarse, self.step) if self.coarse > self.step else (self.step,)):
            for d in range(0, int(span) + grid, grid):
                for b in (self.around + d, self.around - d):
                    b = int(b) // grid * grid
                    if (0 <= b and (not self.dur or b < self.dur) and b not in self.busy
                            and now - self.failed_at.get(b, 0) > 20 and not os.path.exists(self.path(b))):
                        return b
        return None

    def _prefetch_worker(self):
        while self._alive():
            # the player allocates most while a film starts (4K decoder, display mode change): prefetch waits
            if time.time() - self.born < self.wait or self.bad > 5:
                self.ev.wait(1); self.ev.clear(); continue
            with self.lock:
                b = self._todo()
                if b is not None:
                    self.busy.add(b)
            if b is None:
                self.ev.wait(2); self.ev.clear(); continue
            try:
                self.make(b)
            finally:
                with self.lock:
                    self.busy.discard(b)

    def run(self):
        threads = [threading.Thread(target=self._asked_worker, daemon=True)]
        threads += [threading.Thread(target=self._prefetch_worker, daemon=True) for _ in range(max(0, self.workers))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()


def tidy(root, keep, most=3):
    """Keep the frame folders of the last few films only."""
    try:
        ds = sorted((os.path.join(root, d) for d in os.listdir(root)), key=os.path.getmtime, reverse=True)
        for d in ds[most:]:
            if os.path.basename(d) != keep:
                shutil.rmtree(d, True)
    except Exception:
        pass
