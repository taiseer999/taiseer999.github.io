# -*- coding: utf-8 -*-
"""Subtitle status shown through the skin's standard notification (toast).

Piers edition: the old custom overlay drawn on window 12005 is gone. Status
changes published with common.set_status() are shown as regular Kodi
notifications, so they follow the active skin's look and position:
  - only while a video is playing,
  - only when the status text actually changes (no idle "ready" message),
  - progress updates of the same step are throttled,
  - a status that repeats a notify() shown a moment ago is skipped."""
import re
import threading
import time

import xbmc
import xbmcgui

from .common import ADDON, ADDON_NAME, get_status, setting_bool, log

SETTLE = 0.8          # wait for the status to settle (coalesces rapid updates)
BUSY_REPEAT = 15      # same busy step (e.g. a changing percentage): at most once per 15 s
DUP_WINDOW = 3        # skip if notify() just showed a message


def _key(text):
    return re.sub(r'[\d٠-٩.,%٪+\-]+', '', text or '').strip()


class Badge(object):
    def __init__(self, monitor):
        self.monitor = monitor
        self._stop = False

    def _show(self, text, state):
        if state == 'err':
            icon, ms = xbmcgui.NOTIFICATION_ERROR, 6000
        else:
            icon, ms = ADDON.getAddonInfo('icon'), (4000 if state == 'busy' else 5000)
        xbmcgui.Dialog().notification(ADDON_NAME, text, icon, ms, False)

    def run(self):
        seen = None             # (text, state) last handled
        pending = None          # (text, state, since)
        last_key, last_key_at = None, 0.0
        while not self.monitor.abortRequested() and not self._stop:
            try:
                if not setting_bool('show_badge', True) or \
                        not xbmc.getCondVisibility('Player.HasVideo'):
                    seen = pending = None
                    last_key = None
                    self.monitor.waitForAbort(1)
                    continue
                text, state = get_status()
                cur = (text, state)
                now = time.time()
                if cur != seen:
                    seen = cur
                    pending = (text, state, now) if text else None
                if pending and now - pending[2] >= SETTLE:
                    text, state, _ = pending
                    pending = None
                    key = _key(text) + '|' + state
                    win = xbmcgui.Window(10000)
                    try:
                        recent = now - float(win.getProperty('NajdSubs.NotifyTime') or 0) < DUP_WINDOW
                    except ValueError:
                        recent = False
                    if recent:
                        pass
                    elif state == 'busy' and key == last_key and now - last_key_at < BUSY_REPEAT:
                        pass
                    else:
                        self._show(text, state)
                        last_key, last_key_at = key, now
            except Exception as e:
                log('status notify: %s' % e)
                self.monitor.waitForAbort(3)
                continue
            self.monitor.waitForAbort(0.4)

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()

    def stop(self):
        self._stop = True
