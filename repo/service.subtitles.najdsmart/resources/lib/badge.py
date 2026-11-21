# -*- coding: utf-8 -*-
"""Small status badge drawn on top of the fullscreen video (window 12005).

Controls are added to Kodi's own video window, so the badge never takes focus or
remote-control input. It shows:
  - always while the add-on is working (searching / listening / understanding),
  - together with the player's OSD / seek bar otherwise,
  - and hides itself when playback stops."""
import os
import threading
import time

import xbmc
import xbmcgui

from .common import ADDON, ADDON_NAME, get_status, setting_bool, log

MEDIA = os.path.join(ADDON.getAddonInfo('path'), 'resources', 'media')
OSD_VISIBLE = ('Window.IsVisible(videoosd) | Window.IsVisible(seekbar) | '
               'Player.ShowInfo | Player.Seeking | Player.DisplayAfterSeek | '
               'Window.IsVisible(osdsubtitlesettings) | Window.IsVisible(subtitlesearch)')


class Badge(object):
    def __init__(self, monitor):
        self.monitor = monitor
        self.win = None
        self.ctrls = None
        self.shown = False
        self._stop = False
        self.ok_until = 0

    def _build(self):
        self.win = xbmcgui.Window(12005)
        try:
            ww, wh = self.win.getWidth(), self.win.getHeight()
        except Exception:
            ww, wh = 1920, 1080
        scale = ww / 1920.0
        w, h = int(520 * scale), int(50 * scale)
        x, y = ww - w - int(40 * scale), int(30 * scale)
        bg = xbmcgui.ControlImage(x, y, w, h, os.path.join(MEDIA, 'badge_bg.png'))
        dot = xbmcgui.ControlImage(x + w - int(38 * scale), y + int(13 * scale),
                                   int(24 * scale), int(24 * scale), os.path.join(MEDIA, 'dot_busy.png'))
        label = xbmcgui.ControlLabel(x + int(18 * scale), y, w - int(66 * scale), h, '',
                                     font='font12', textColor='FFFFFFFF', alignment=0x00000001 | 0x00000004)
        self.win.addControls([bg, dot, label])
        self.ctrls = (bg, dot, label)
        self._set_visible(False)

    def _set_visible(self, v):
        if self.ctrls:
            for c in self.ctrls:
                c.setVisible(v)
        self.shown = v

    def _remove(self):
        if self.win and self.ctrls:
            try:
                self.win.removeControls(list(self.ctrls))
            except Exception:
                pass
        self.ctrls = None
        self.shown = False

    def run(self):
        last_text = None
        last_state = None
        while not self.monitor.abortRequested() and not self._stop:
            try:
                playing = xbmc.getCondVisibility('Player.HasVideo') and \
                    xbmc.getCondVisibility('Window.IsActive(fullscreenvideo)')
                enabled = setting_bool('show_badge', True)
                if not playing or not enabled:
                    if self.ctrls:
                        self._remove()
                    self.monitor.waitForAbort(1)
                    continue
                if self.ctrls is None:
                    self._build()
                    last_text = last_state = None
                text, state = get_status()
                if not text:
                    text, state = 'ترجمة نجد الذكية — جاهزة', 'ok'
                if text != last_text:
                    self.ctrls[2].setLabel('[B]%s[/B]' % text)
                    last_text = text
                if state != last_state:
                    dot = {'busy': 'dot_busy.png', 'err': 'dot_err.png'}.get(state, 'dot_ok.png')
                    self.ctrls[1].setImage(os.path.join(MEDIA, dot))
                    if state == 'ok' and last_state == 'busy':
                        self.ok_until = time.time() + 6      # show the result for a moment
                    last_state = state
                want = state == 'busy' or time.time() < self.ok_until or \
                    xbmc.getCondVisibility(OSD_VISIBLE)
                if want != self.shown:
                    self._set_visible(want)
            except Exception as e:
                log('badge: %s' % e)
                self._remove()
                self.monitor.waitForAbort(3)
                continue
            self.monitor.waitForAbort(0.4)
        self._remove()

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()

    def stop(self):
        self._stop = True
