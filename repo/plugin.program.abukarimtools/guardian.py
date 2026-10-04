# -*- coding: utf-8 -*-
"""Service guardian (ABUKARIM TOOLS 3.2.14).

On Kodi 22 / Python 3.14 some add-on services are simply never started at
boot: the 2026-10-04 logs show no line at all from the ABUKARIM TOOLS service
(and none from DexHub or Last Played) while a dozen other services start
normally. Nothing crashes - the invocation never happens or never gets past
interpreter start-up.

Arctic Fuse 3's Home window runs this script once per session (patched
onload). It waits for boot to settle, then starts every watched service whose
heartbeat property is still missing, as a plain script. Each service guards
itself against a second copy with the same property, so a late normal start
is harmless.

    RunScript(special://home/addons/plugin.program.abukarimtools/guardian.py)
"""
import os

import xbmc
import xbmcgui
import xbmcvfs

PROP = 'abukarimtools.guardian'
WAIT_S = 25

# (heartbeat property on Window(Home), add-on id, script inside the add-on)
WATCH = [
    ('abukarimtools.service.alive', 'plugin.program.abukarimtools', 'service.py'),
    ('abk.lastplayed.alive', 'plugin.video.abukarim.lastplayed', 'service.py'),
]


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools Guardian] %s' % msg, level)


def _enabled(addon_id):
    return xbmc.getCondVisibility('System.AddonIsEnabled(%s)' % addon_id)


def main():
    home = xbmcgui.Window(10000)
    if home.getProperty(PROP):
        return
    home.setProperty(PROP, 'waiting')
    mon = xbmc.Monitor()
    if mon.waitForAbort(WAIT_S):
        return
    started = []
    for prop, aid, script in WATCH:
        if home.getProperty(prop):
            continue
        path = xbmcvfs.translatePath('special://home/addons/%s/%s' % (aid, script))
        if not os.path.isfile(path):
            continue
        if not _enabled(aid):
            _log('%s is installed but DISABLED - its service cannot run' % aid, xbmc.LOGWARNING)
            continue
        _log('%s service did not start at boot - starting it now' % aid, xbmc.LOGWARNING)
        xbmc.executebuiltin('RunScript(%s)' % path)
        started.append(aid)
    home.setProperty(PROP, 'done:%s' % (','.join(started) or 'none'))
    if not started:
        _log('all watched services are running')


if __name__ == '__main__':
    main()
