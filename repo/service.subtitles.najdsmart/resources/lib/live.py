# -*- coding: utf-8 -*-
"""Live check while you watch: every few minutes listen to the part that is ABOUT to
play, measure how far the subtitle is from the speech there, and if the subtitle drifted
(different cut, ad break, intro) shift everything from that point on and swap it in.

Local files: on by default (reading the file costs no internet).
Internet streams: only when the user enables it (each check downloads ~30 s of video)."""
import os
import threading
import time

import xbmc

from .common import log, setting, setting_bool, set_status
from . import pipeline, subtitle, arabic, sync, audiosync


class LiveChecker(object):
    def __init__(self, player, monitor, path):
        self.player = player
        self.monitor = monitor
        self.path = path            # video being played
        self.stop = False
        self.history = []           # (position_ms, measured_offset_ms)

    def playing(self):
        try:
            return self.player.isPlayingVideo() and self.player.getPlayingFile() == self.path
        except Exception:
            return False

    def _abort(self):
        return self.stop or self.monitor.abortRequested() or not self.playing()

    def run(self):
        video_stub = {'path': self.path}
        stream = pipeline.is_stream(video_stub)
        if stream and not setting_bool('live_stream_check', False):
            return
        if not setting_bool('live_check', True):
            return
        every = (8 if stream else 4) * 60
        win = 30.0 if stream else 50.0
        # first check after things settled (initial processing usually finished)
        if self.monitor.waitForAbort(150):
            return
        while not self._abort():
            try:
                self.check_once(win, stream)
            except Exception as e:
                if 'aborted' in str(e):
                    return
                log('live check: %s' % e)
            for _ in range(int(every)):
                if self._abort() or self.monitor.waitForAbort(1):
                    return

    def check_once(self, win, stream):
        if xbmc.getCondVisibility('Player.Paused'):
            return
        from . import media
        video = media.current()
        last = pipeline.last_for(video)
        if not last or not os.path.exists(last['path']):
            return
        eng = pipeline.ffmpeg_path()
        if not eng:
            return
        src, args, _r = audiosync.media_source(self.path)
        pos = self.player.getTime()
        start = pos + 15.0                       # the part you are about to watch
        total = self.player.getTotalTime() or 0
        if total and start + win > total - 30:
            return
        with open(last['path'], 'rb') as f:
            cues = subtitle.parse(arabic.decode(f.read()))
        a0, a1 = int(start * 1000), int((start + win) * 1000)
        inside = [(c.start, c.end) for c in cues if a0 + 1500 <= c.start <= a1 - 1500]
        if len(inside) < 6:
            return                               # quiet scene: nothing to measure
        set_status('فحص توقيت الجزء التالي...')
        pcm = audiosync._run_ffmpeg(eng, src, args, start=start, dur=win,
                                    abort=self._abort, timeout=90)
        speech = sorted((c.start, c.end) for c in audiosync.detect_speech(pcm, offset_ms=a0))
        if len(speech) < 6:
            set_status('')
            return
        base = sync._overlap(inside, speech)
        d, score = sync._refine(inside, speech, 1.0, 0, 2500, 20)
        confident = score > base * 1.10 and score > 0.35 * sum(e - s for s, e in inside) and \
            pipeline.chance_lift([(inside, speech)], d) >= pipeline.MIN_LIFT
        self.history.append((int(pos * 1000), d if confident else 0))
        log('live check @%ds: shift %d ms (overlap %d → %d, confident=%s)' % (pos, d, base, score, confident))
        recent = [h[1] for h in self.history[-2:]]
        # act on a confirmed drift: big & confident now, or the same small drift twice
        act = confident and (abs(d) >= 400 or (len(recent) == 2 and abs(recent[0] - recent[1]) < 150
                                                and abs(d) >= 150))
        if not act:
            set_status('التوقيت مضبوط ✓', 'ok')
            return
        cut = int(pos * 1000)
        for c in cues:
            if c.start >= cut:
                c.start = max(0, c.start + d)
                c.end = max(c.start + 300, c.end + d)
        cues = subtitle.fix_timing(cues)
        base_path = last['path'][:-4]
        new_path = '%s.live%d.srt' % (base_path.split('.live')[0], int(time.time()) % 100000)
        with open(new_path, 'w', encoding='utf-8-sig') as f:
            f.write(subtitle.to_srt(cues))
        if self.playing():
            self.player.setSubtitles(new_path)
            self.player.showSubtitles(True)
            pipeline.remember_last(new_path, video, last.get('item') or {},
                                   lineage=last.get('lineage') or last['path'])
            self.history = []
            set_status('صُحح التوقيت من الدقيقة %d: %+.2f ث ✓' % (pos // 60, d / 1000.0), 'ok')
            log('live check: shifted %d ms from %ds' % (d, pos))


def start(player, monitor, path):
    chk = LiveChecker(player, monitor, path)
    threading.Thread(target=chk.run, daemon=True).start()
    return chk
