# -*- coding: utf-8 -*-
"""Persistent prayer scheduler. Similar lifecycle separation to Najd subtitles autoservice."""
import xbmc, xbmcaddon, xbmcvfs
from resources.lib.services.scheduler import Scheduler

def main():
    addon=xbmcaddon.Addon(); monitor=xbmc.Monitor()
    profile=xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    addon_path=addon.getAddonInfo('path')
    scheduler=Scheduler(addon,profile,xbmc,__import__('xbmcgui'),addon_path)
    xbmc.log('[NajdPrayer] service started',xbmc.LOGINFO)
    while not monitor.abortRequested():
        try: scheduler.tick()
        except Exception as exc: xbmc.log('[NajdPrayer] scheduler failure: %s'%exc,xbmc.LOGERROR)
        if monitor.waitForAbort(15): break
    xbmc.log('[NajdPrayer] service stopped',xbmc.LOGINFO)

if __name__=='__main__': main()
