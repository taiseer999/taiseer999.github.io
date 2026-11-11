# -*- coding: utf-8 -*-
"""
seek_preview_toggle.py - ABUKARIM TOOLS (4.8.12)

Toggles entry "Seek Preview": on/off, picture size, frames made ahead of
time (off / local files only / always) and hiding subtitles while skipping.
Saved to addon_data seek_preview.json; the engine thread (started by the
service, resources/lib/seek_preview/engine.py) picks the change up within
two seconds, no restart. Turning it on without ffmpeg offers to install the
CoreELEC "FFmpeg Tools" add-on.
"""
import xbmc
import xbmcgui

from resources.lib.i18n import T
from resources.lib.seek_preview import engine
from resources.lib import toggle_ui

TITLE = 'ABUKARIM TOOLS'
FFMPEG_ADDON = 'tools.ffmpeg-tools'


def _log(msg):
    xbmc.log('[AbukarimTools SeekPreview] %s' % msg, xbmc.LOGINFO)


def _ensure_ffmpeg():
    """True when an ffmpeg runs here; otherwise offer FFmpeg Tools."""
    if engine.find_ffmpeg()[0]:
        return True
    if xbmc.getCondVisibility('System.Platform.Android'):
        xbmcgui.Dialog().ok(TITLE, T(30046))
        return False
    if not xbmc.getCondVisibility('System.HasAddon(%s)' % FFMPEG_ADDON):
        if xbmcgui.Dialog().yesno(TITLE, T(30047)):
            xbmc.executebuiltin('InstallAddon(%s)' % FFMPEG_ADDON, True)
            for _ in range(60):
                xbmc.sleep(1000)
                if engine.find_ffmpeg()[0]:
                    return True
    xbmcgui.Dialog().ok(TITLE, T(30048))
    return False


def run():
    cfg = engine.load_config()
    rows = [
        ('enabled', T(30024), cfg['enabled'], None),
        ('size', T(30040), cfg['size'], [(0, T(30041)), (1, T(30042)), (2, T(30043))]),
        ('ahead', T(30044), cfg['ahead'], [(0, T(30437)), (1, T(30045)), (2, T(30049))]),
        ('hidesubs', T(30039), cfg['hidesubs'], None),
    ]
    new = toggle_ui.option_list(T(30024), rows)
    if not new:
        return
    if new['enabled'] and not cfg['enabled'] and not _ensure_ffmpeg():
        new['enabled'] = False
    cfg.update(new)
    engine.save_config(cfg)
    _log('settings: %s' % cfg)
    xbmcgui.Dialog().notification(TITLE, '%s: %s' % (T(30024), toggle_ui.state_text(cfg['enabled'])),
                                  xbmcgui.NOTIFICATION_INFO, 3000)
    xbmc.executebuiltin('Container.Refresh')
