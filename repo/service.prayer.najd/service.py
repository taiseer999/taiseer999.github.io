# -*- coding: utf-8 -*-
"""Persistent prayer scheduler + on-video countdown.

The loop wakes every second: the countdown over the video refreshes each second,
while prayer-time checks run every 15 seconds as before.
"""
import time

import xbmc, xbmcaddon, xbmcvfs
from resources.lib.services.scheduler import Scheduler
from resources.lib.gui.osd_countdown import OsdCountdown

TICK_EVERY = 15  # seconds between prayer-time checks


def main():
    addon=xbmcaddon.Addon(); monitor=xbmc.Monitor()
    profile=xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    addon_path=addon.getAddonInfo('path')
    scheduler=Scheduler(addon,profile,xbmc,__import__('xbmcgui'),addon_path)
    osd=OsdCountdown(addon_path)
    xbmc.log('[NajdPrayer] service started',xbmc.LOGINFO)
    last_tick=0.0; upcoming=None; last_next=0.0
    while not monitor.abortRequested():
        now=time.time()
        if now-last_tick >= TICK_EVERY:
            last_tick=now
            try: scheduler.tick()
            except Exception as exc: xbmc.log('[NajdPrayer] scheduler failure: %s'%exc,xbmc.LOGERROR)
        try:
            # recompute the next prayer at most every 15 s, or once it has passed
            if upcoming is None or now-last_next >= TICK_EVERY or upcoming[1].timestamp() <= now:
                upcoming=scheduler.next_salah(); last_next=now
            osd.update(addon.getSetting('osd_countdown') != 'false', upcoming)
        except Exception as exc:
            xbmc.log('[NajdPrayer] osd countdown failure: %s'%exc,xbmc.LOGERROR)
        # poll quickly while a video plays so the countdown appears with the bar
        if monitor.waitForAbort(0.25 if xbmc.Player().isPlayingVideo() else 1.0): break
    osd.detach()
    xbmc.log('[NajdPrayer] service stopped',xbmc.LOGINFO)

if __name__=='__main__': main()
