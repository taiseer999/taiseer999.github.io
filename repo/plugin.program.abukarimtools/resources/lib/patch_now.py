# -*- coding: utf-8 -*-
"""
patch_now.py - ABUKARIM TOOLS (4.7.33)

One patch pass in a FRESH Python process, so it runs the code of the AB Tools
version now on disk. Started by the service's update watch when AB Tools is
updated while Kodi is running: Kodi keeps the old service (and its auto-patch
watchdog, with the old patch list) until a restart, so the new version's skin
and add-on patches used to wait for the next reboot.

    RunScript(special://home/addons/plugin.program.abukarimtools/resources/lib/patch_now.py)

A write into the active skin is followed by ReloadSkin (deferred while a video
plays or a dialog is open - the running watchdog fires it later).
"""
import os
import sys

import xbmc
import xbmcvfs

ROOT = xbmcvfs.translatePath('special://home/addons/plugin.program.abukarimtools/')
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main():
    reason = sys.argv[1] if len(sys.argv) > 1 else 'AB Tools update'
    try:
        from resources.lib import patch_watchdog
        changed, failed = patch_watchdog.patch_after_install(reason=reason)
        xbmc.log('[AbukarimTools PatchNow] %s: %d written, %d failed'
                 % (reason, changed, failed), xbmc.LOGINFO)
    except Exception as exc:
        xbmc.log('[AbukarimTools PatchNow] failed: %s' % exc, xbmc.LOGERROR)
    # the Lucent Player Back keymap / leftover Lucent keymaps (4.7.32+)
    try:
        from resources.lib import lucent_back
        lucent_back.sync_keymap()
    except Exception:
        pass


if __name__ == '__main__':
    main()
