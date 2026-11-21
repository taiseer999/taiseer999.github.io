# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""Seek Preview picture maker (AB Tools 4.12.0, written for AB Tools).

Pictures are cut from the video with ffmpeg, one short ffmpeg run per picture,
and saved as small JPEG files named by their second in the video, on a grid of
``step`` seconds. Work is kept in one priority list:

  priority 0   the picture of the spot the viewer is skipping to (always tried)
  priority 1   the coarse grid (every COARSE seconds) around ``centre``
  priority 2   every ``step`` seconds around ``centre``

``slots`` threads take work from the list; one thread is held back for
priority 0 only, so a skip never queues behind prefetch work.

No Kodi import: this file runs on a PC for tests.
"""
import os
import shutil
import subprocess
import sys
import threading
import time

IS_WINDOWS = sys.platform.startswith('win')
_HIDDEN = 0x08000000 if IS_WINDOWS else 0      # no console window on Windows
COARSE = 30
RUN_LIMIT = 20.0        # seconds one ffmpeg run may take
RETRY_AFTER = 20.0      # a picture that failed is not tried again for this long
GIVE_UP = 6             # prefetch pauses after this many failures in a row


def ffmpeg_ok(path):
    """True when ``path`` is an ffmpeg that starts on this machine."""
    try:
        if not IS_WINDOWS and not os.access(path, os.X_OK):
            os.chmod(path, 0o755)
        out = subprocess.run([path, '-hide_banner', '-version'], capture_output=True,
                             timeout=15, creationflags=_HIDDEN)
    except Exception:
        return False
    return out.returncode == 0 and out.stdout[:200].lower().find(b'ffmpeg') >= 0


def available_memory():
    """Bytes the system can still hand out (Linux /proc/meminfo), else a huge number."""
    try:
        with open('/proc/meminfo', 'r') as fh:
            for row in fh:
                if row.startswith('MemAvailable:'):
                    return int(row.split()[1]) << 10
    except Exception:
        pass
    return 1 << 40


def ffmpeg_args(ffmpeg, src, headers, second, w, h, dest):
    """The command for one picture at ``second``: nearest key frame, fitted into w x h."""
    args = [ffmpeg, '-nostdin', '-hide_banner', '-loglevel', 'error']
    if headers:
        args += ['-headers', headers]
    if src.startswith(('http://', 'https://')):
        args += ['-seekable', '1', '-multiple_requests', '1']
    args += ['-threads', '1', '-probesize', '2M', '-analyzeduration', '1M',
             '-skip_frame', 'nokey', '-skip_loop_filter', 'all',
             '-ss', '%d' % second, '-noaccurate_seek', '-i', src,
             '-map', '0:v:0', '-an', '-sn', '-dn', '-frames:v', '1', '-threads', '1',
             '-sws_flags', 'fast_bilinear',
             '-vf', 'scale=w=%d:h=%d:force_original_aspect_ratio=decrease,'
                    'pad=w=%d:h=%d:x=-1:y=-1:color=black' % (w, h, w, h),
             '-q:v', '5', '-f', 'mjpeg', '-y', dest]
    if not IS_WINDOWS:
        # lowest priority, and the first process the kernel ends when memory runs out
        args = ['sh', '-c', 'echo 1000 >/proc/self/oom_score_adj 2>/dev/null; exec nice -n 15 "$@"',
                'abk-preview'] + args
    return args


class Grabber(object):
    """Pictures of one video. Create, set ``duration``/``centre`` as playback goes, ``start()``."""

    def __init__(self, ffmpeg, src, headers, folder, step=10, width=426, streamed=False,
                 stop_event=None, min_free=250 << 20, settle=20.0, span=180, slots=2, report=None):
        self.ffmpeg, self.src, self.headers, self.folder = ffmpeg, src, headers, folder
        self.step = max(2, int(step))
        self.width = int(width)
        self.height = (self.width * 9 // 16) & ~1
        self.streamed = streamed
        self.min_free = min_free
        self.settle = settle            # prefetch waits this long after the video opens
        self.span = span                # streamed: seconds each way that are made ahead
        self.slots = max(0, int(slots)) # prefetch threads (one more serves skips)
        self.report = report            # callable(kind, text) or None
        self.duration = 0
        self.centre = 0
        self.made = self.failed = 0
        self._streak = 0
        self._failed_at = {}
        self._running = set()
        self._wanted = None
        self._lock = threading.Lock()
        self._wake = threading.Condition(self._lock)
        self._halted = False
        self._outer_stop = stop_event or threading.Event()
        self._opened = time.time()
        self._threads = []
        os.makedirs(folder, exist_ok=True)

    # ------------------------------------------------------------------ files
    def file_for(self, second):
        return os.path.join(self.folder, 'f%07d.jpg' % second)

    def slot(self, t):
        return (int(t) // self.step) * self.step

    def have(self, second):
        return os.path.isfile(self.file_for(second))

    def picture(self, t, reach=20):
        """The picture for ``t``, or one within ``reach`` seconds of it; '' when none is made."""
        base = self.slot(t)
        off = 0
        while off <= reach:
            for s in ((base,) if off == 0 else (base + off, base - off)):
                if s >= 0 and self.have(s):
                    return self.file_for(s)
            off += self.step
        return ''

    # ------------------------------------------------------------------ control
    def want(self, t):
        """The viewer is skipping to ``t``: make that picture before anything else."""
        s = self.slot(t)
        with self._lock:
            if self.have(s) or s in self._running:
                return
            if time.time() - self._failed_at.get(s, 0.0) < RETRY_AFTER:
                return
            self._wanted = s
            self._wake.notify_all()

    def stop(self):
        with self._lock:
            self._halted = True
            self._wake.notify_all()

    def stopped(self):
        return self._halted or self._outer_stop.is_set()

    def start(self):
        jobs = [self._serve_skips] + [self._serve_prefetch] * self.slots
        for n, job in enumerate(jobs):
            th = threading.Thread(target=job, name='abk-seekgrab-%d' % n)
            th.daemon = True
            th.start()
            self._threads.append(th)

    def join(self, timeout=None):
        end = None if timeout is None else time.time() + timeout
        for th in self._threads:
            th.join(None if end is None else max(0.0, end - time.time()))

    # ------------------------------------------------------------------ work
    def _tell(self, kind, text):
        if self.report:
            try:
                self.report(kind, text)
            except Exception:
                pass

    def _next_prefetch(self):
        """The nearest missing slot to ``centre``: coarse grid first, then every step."""
        reach = self.span if self.streamed else max(self.duration, 600)
        now = time.time()
        grids = (COARSE, self.step) if COARSE > self.step else (self.step,)
        for grid in grids:
            centre = (int(self.centre) // grid) * grid
            dist = 0
            while dist <= reach:
                for s in (centre + dist, centre - dist) if dist else (centre,):
                    if s < 0 or (self.duration and s >= self.duration):
                        continue
                    if s in self._running or self.have(s):
                        continue
                    if now - self._failed_at.get(s, 0.0) < RETRY_AFTER:
                        continue
                    return s
                dist += grid
        return None

    def _serve_skips(self):
        while not self.stopped():
            with self._lock:
                if self._wanted is None:
                    self._wake.wait(1.0)
                s, self._wanted = self._wanted, None
                if s is None or s in self._running:
                    continue
                self._running.add(s)
            try:
                self._grab(s, asked=True)
            finally:
                with self._lock:
                    self._running.discard(s)

    def _serve_prefetch(self):
        while not self.stopped():
            with self._lock:
                if time.time() - self._opened < self.settle or self._streak >= GIVE_UP:
                    self._wake.wait(1.0)
                    continue
                s = self._next_prefetch()
                if s is None:
                    self._wake.wait(2.0)
                    continue
                self._running.add(s)
            try:
                self._grab(s, asked=False)
            finally:
                with self._lock:
                    self._running.discard(s)

    def _grab(self, s, asked):
        if self.have(s):
            return
        free = available_memory()
        if free < self.min_free:
            self._tell('lowmem', '%d MB free, %d MB needed' % (free >> 20, self.min_free >> 20))
            with self._lock:
                self._wake.wait(3.0)
            return
        dest = self.file_for(s)
        part, log = dest + '.part', dest + '.log'
        began = time.time()
        late = False
        code = None
        try:
            with open(log, 'wb') as errors:
                proc = subprocess.Popen(ffmpeg_args(self.ffmpeg, self.src, self.headers, s,
                                                    self.width, self.height, part),
                                        stdout=subprocess.DEVNULL, stderr=errors, creationflags=_HIDDEN)
                while True:
                    try:
                        code = proc.wait(timeout=0.05)
                        break
                    except subprocess.TimeoutExpired:
                        pass
                    late = time.time() - began > RUN_LIMIT
                    if late or self.stopped():
                        proc.kill()
                        code = proc.wait()
                        break
            spent = time.time() - began
            if code == 0 and os.path.isfile(part) and os.path.getsize(part):
                os.replace(part, dest)
                with self._lock:
                    self.made += 1
                    self._streak = 0
                    first = self.made == 1
                if first or spent > 3:
                    self._tell('made', 'picture at %ds in %.1fs%s' % (s, spent, ' (skip)' if asked else ''))
            elif not self.stopped():
                self._failure(s)
                try:
                    with open(log, 'rb') as fh:
                        why = fh.read()[-400:].decode('utf-8', 'replace').strip()
                except Exception:
                    why = ''
                self._tell('fail', 'picture at %ds not made after %.1fs (%s, exit %s): %s'
                           % (s, spent, 'too slow' if late else 'error', code, why or '-'))
        except Exception as e:
            self._failure(s)
            self._tell('fail', 'picture at %ds: %s' % (s, e))
        finally:
            for leftover in (part, log):
                try:
                    os.remove(leftover)
                except OSError:
                    pass

    def _failure(self, s):
        with self._lock:
            self.failed += 1
            self._streak += 1
            self._failed_at[s] = time.time()


def keep_recent(root, current, count=3):
    """Delete the picture folders of older videos, keeping ``count`` and ``current``."""
    try:
        folders = [os.path.join(root, n) for n in os.listdir(root)]
        folders = [p for p in folders if os.path.isdir(p)]
        folders.sort(key=os.path.getmtime, reverse=True)
    except OSError:
        return
    for p in folders[count:]:
        if os.path.basename(p) != current:
            shutil.rmtree(p, ignore_errors=True)
