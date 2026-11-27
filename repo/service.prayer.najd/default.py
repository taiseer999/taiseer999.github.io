# -*- coding: utf-8 -*-
"""Najd Prayer entry point: RTL dialog UI, plugin widget, and fallback menu."""
import sys
import urllib.parse
from datetime import datetime

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from resources.lib.core.prayer_engine import NAMES, name_of
from resources.lib.gui.window import day_times, next_prayer, ORDER

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')
HANDLE = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip('-').isdigit() else -1


def _s(k, d=''):
    v = ADDON.getSetting(k)
    return v if v not in (None, '') else d


def open_ui():
    # Try the rich RTL dialog; fall back to a plain list if the skin engine refuses.
    try:
        from resources.lib.gui.window import open_dialog
        open_dialog(ADDON, ADDON_PATH)
    except Exception as exc:
        xbmc.log('[NajdPrayer] dialog failed, using text fallback: %s' % exc, xbmc.LOGWARNING)
        _text_dashboard()


def _text_dashboard():
    now = datetime.now()
    data = day_times(ADDON, now.date())
    key, dt, _d = next_prayer(ADDON, now)
    if key and dt:
        mins = max(0, int((dt - now).total_seconds() // 60))
        nextline = 'الصلاة القادمة: %s  —  متبقٍ %02d:%02d' % (name_of(key, dt), mins // 60, mins % 60)
    else:
        nextline = 'تعذّر تحديد الصلاة القادمة؛ راجع الإعدادات.'
    body = nextline + '\n\n' + '  |  '.join('%s %s' % (name_of(k, now), data.get(k) or '--:--') for k in ORDER)
    xbmcgui.Dialog().textviewer('مواقيت نجد للصلاة  |  %s' % _s('city_name', 'الرياض'), body)


def plugin_widget():
    now = datetime.now()
    data = day_times(ADDON, now.date())
    items = []
    key, dt, _d = next_prayer(ADDON, now)
    if key and dt:
        mins = max(0, int((dt - now).total_seconds() // 60))
        li = xbmcgui.ListItem(label='القادمة: %s  |  %02d:%02d' % (name_of(key, dt), mins // 60, mins % 60))
        li.setProperty('prayer_name', name_of(key, dt))
        li.setArt({'icon': ADDON_PATH + '/icon.png'})
        items.append((sys.argv[0] + '?action=open', li, False))
    for k in ORDER:
        li = xbmcgui.ListItem(label='%s  —  %s' % (name_of(k, now), data.get(k) or '--:--'))
        li.setProperty('prayer_name', name_of(k, now))
        li.setProperty('prayer_time', data.get(k) or '')
        items.append((sys.argv[0] + '?action=open', li, False))
    xbmcplugin.addDirectoryItems(HANDLE, items, len(items))
    xbmcplugin.setContent(HANDLE, 'files')
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def main():
    if HANDLE >= 0 and len(sys.argv) > 2:
        q = urllib.parse.parse_qs(sys.argv[2].lstrip('?'))
        action = q.get('action', ['widget'])[0]
        if action == 'widget':
            plugin_widget()
        else:
            open_ui()
    else:
        open_ui()


if __name__ == '__main__':
    main()
