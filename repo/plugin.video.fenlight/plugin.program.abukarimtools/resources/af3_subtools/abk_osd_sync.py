# -*- coding: utf-8 -*-
# -- DexSubtitles OSD AutoSync launcher (by ABUKARIM TOOLS) --
# Shipped by plugin.program.abukarimtools (toggle "AF3: Subtitle Buttons") and
# run from the Arctic Fuse 3 player OSD:
#   RunScript(special://home/addons/service.subtitles.dexworld/abk_osd_sync.py)
# It lives INSIDE service.subtitles.dexworld so xbmcaddon.Addon() resolves to
# DexSubtitles (its own settings) and `import autosync` loads DexSubtitles' own
# autosync.py. autosync.py has no entry point of its own; the add-on's manual
# "sync the playing subtitle" flow (service._sync_current -> autosync.sync_now)
# is the one that drives it, so this calls exactly that flow - outside the
# subtitle search dialog, which means we always apply the result ourselves.
import os
import sys
import xbmc

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[DexSubtitles.abk_osd_sync] %s' % msg, level)


def main():
    # service.py reads sys.argv[1] as a plugin handle; give it none (-1).
    sys.argv = [sys.argv[0] if sys.argv else __file__]
    import autosync
    import service as dex
    if not xbmc.Player().isPlayingVideo():
        autosync.notify_always('شغّل الفيديو أولاً ثم زامن الترجمة', False)
        return
    # No subtitle dialog here: it would normally copy/apply the returned file.
    # Force the "apply it ourselves" branch and show the result right away
    # (the deferred notice is meant to follow Kodi's own dialog message).
    dex._kodi_copies_to_temp = lambda media: False
    autosync.defer_notify = autosync.notify_always
    dex.sync_current_action()


try:
    main()
except Exception as e:
    _log('failed: %s' % e, xbmc.LOGWARNING)
    try:
        import xbmcgui
        xbmcgui.Dialog().notification('DexSubtitles AutoSync', 'تعذّرت المزامنة الآن',
                                      xbmcgui.NOTIFICATION_WARNING, 4000)
    except Exception:
        pass
