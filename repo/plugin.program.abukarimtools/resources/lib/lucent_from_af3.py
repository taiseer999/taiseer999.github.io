# -*- coding: utf-8 -*-
"""
lucent_from_af3.py - ABUKARIM TOOLS (4.7.28)

"Lucent: Widgets from AF3". Builds the Lucent skin's side menu (tabs) and
widgets from the Arctic Fuse 3 menu this box already has:

  AF3 (addon_data/skin.arctic.fuse.3)           Lucent (skin strings nuvio.*)
  skinvariables-shortcut-homewidgets.json   ->  the start tab (Home)
  skinvariables-shortcut-hubs.json          ->  one tab per enabled hub
  skinvariables-shortcut-<window>widgets.json   (its widgets)

Lucent holds at most 12 tabs and 10 widgets per tab: a hub with more widgets
is split over extra tabs ("Movies 2", ...) while tabs are free; what still
does not fit is listed at the end. AF3's "Stacked Folder" rows (they follow
the row above them) and hidden rows are left out. Lucent has two row styles:
Landscape / Gatefold / Square -> landscape, everything else -> posters.

The menu is written with Lucent's own scripts/menu.py (Menu.save), so it is
exactly what Lucent's "Menu and widgets" editor would write; Lucent must be
the active skin (skin strings belong to the active skin).
"""
import json
import os
import re
import sys

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

LUCENT = 'skin.lucent'
AF3_DATA = 'special://profile/addon_data/skin.arctic.fuse.3/'
TITLE = 'ABUKARIM TOOLS'
NTABS, NWIDGETS = 12, 10
SHOW_WIDGETS = 'SetFocus(9100)'
LAND = ('landscape', 'gatefold', 'square', 'wide', 'episode', 'thumb')
# AF3 hub icon (file stem) -> Lucent icon
ICON_MAP = (('film', 'movies'), ('movie', 'movies'), ('tv', 'tv'), ('kdrama', 'star'),
            ('addon', 'addons'), ('calendar', 'calendar'), ('livetv', 'tv'), ('plex', 'library'),
            ('music', 'music'), ('search', 'search'), ('star', 'star'))
# AF3's TMDbHelper refresh token: a skin string is not parsed again, so the
# $INFO[] would reach TMDbHelper as text
_RELOAD = re.compile(r'&?reload=\$INFO\[[^\]]*\]')


def _log(msg):
    xbmc.log('[AbukarimTools LucentFromAF3] %s' % msg, xbmc.LOGINFO)


def _load(name):
    path = xbmcvfs.translatePath(AF3_DATA + 'skinvariables-shortcut-%s.json' % name)
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _label(text):
    text = text or ''
    m = re.fullmatch(r'\$LOCALIZE\[(\d+)\]', text.strip())
    if m:
        text = xbmc.getLocalizedString(int(m.group(1))) or text
    return re.sub(r'\[/?(COLOR|B|I|UPPERCASE|LOWERCASE|CAPITALIZE)[^\]]*\]', '', text).strip()


def _widget(item):
    path = (item.get('path') or '').strip()
    if not path or path == 'Stacked_Folder' or '://' not in path:
        return None
    if str(item.get('disabled', '')).lower() == 'true' or item.get('abk_hidden'):
        return None
    path = _RELOAD.sub('', path).replace('?&', '?')
    style = 'land' if (item.get('widget_style') or '').lower() in LAND else 'poster'
    limit = str(item.get('widget_limit') or '')
    return {'label': _label(item.get('label')) or path, 'path': path, 'style': style,
            'sort': '', 'limit': limit if limit.isdigit() else '', 'timg': '', 'bg': '', 'notitle': ''}


def _icon(af3_icon):
    stem = os.path.splitext(os.path.basename(
        (af3_icon or '').replace('%2f', '/').replace('%2F', '/').rstrip('/')))[0].lower()
    for key, icon in ICON_MAP:
        if key in stem:
            return 'icons/%s.png' % icon
    return 'icons/star.png'


def _tab(label, icon, action, widgets=None):
    return {'label': label, 'icon': icon, 'action': action, 'actionlabel': '',
            'widgets': widgets or [], 'slot': 0}


def build(default_tabs):
    """(tabs, start_tab, dropped) from the AF3 files; default_tabs = Lucent's own
    default menu, used for the Search / Add-ons / Settings / Power tabs."""
    by_icon = {t['icon']: t for t in default_tabs}
    search = by_icon.get('icons/search.png', {}).get('action') or 'VideoLibrary.Search'
    if xbmc.getCondVisibility('System.HasAddon(plugin.video.themoviedb.helper)'):   # AF3 searches with TMDbHelper
        search = 'ActivateWindow(Videos,plugin://plugin.video.themoviedb.helper/?info=dir_search,return)'
    head = [_tab(T(32090), 'icons/search.png', search)]
    home = _tab(T(32091), 'icons/home.png', SHOW_WIDGETS,
                [w for w in map(_widget, _load('homewidgets')) if w])
    tail = []
    hubs = []
    for hub in _load('hubs'):
        if str(hub.get('disabled', '')).lower() == 'true':
            continue
        window = str(hub.get('window') or '')
        widgets = [w for w in map(_widget, _load('%swidgets' % window)) if w] if window else []
        label = _label(hub.get('label'))
        if window == '1108' and not widgets:            # AF3 Add-ons hub: Lucent's own Add-ons tab
            addons = by_icon.get('icons/addons.png')
            if addons:
                tail.append(dict(addons, label=label or addons['label'], slot=0))
            continue
        if not widgets:
            continue
        hubs.append((label, _icon(hub.get('icon')), widgets))
    for icon, key in (('icons/settings.png', 32092), ('icons/power.png', 32093)):
        if icon in by_icon:
            tail.append(dict(by_icon[icon], label=T(key), slot=0))

    # tabs left for the hubs; a hub gets as many tabs as it needs while they last
    free = NTABS - len(head) - 1 - len(tail)
    need = [max(1, -(-len(w) // NWIDGETS)) for _l, _i, w in hubs]
    give = [1] * len(hubs)
    free -= len(hubs)
    while free > 0 and any(g < n for g, n in zip(give, need)):
        for i, (g, n) in enumerate(zip(give, need)):
            if free > 0 and g < n:
                give[i] += 1
                free -= 1
    tabs, dropped = [], []
    for (label, icon, widgets), parts in zip(hubs, give):
        size = -(-min(len(widgets), parts * NWIDGETS) // parts)    # spread evenly
        for p in range(parts):
            chunk = widgets[p * size:(p + 1) * size]
            if chunk:
                tabs.append(_tab(label if p == 0 else '%s %d' % (label, p + 1), icon, SHOW_WIDGETS, chunk))
        dropped += ['%s: %s' % (label, w['label']) for w in widgets[parts * size:]]
    dropped += ['%s: %s' % (home['label'], w['label']) for w in home['widgets'][NWIDGETS:]]
    home['widgets'] = home['widgets'][:NWIDGETS]
    all_tabs = (head + [home] + tabs + tail)[:NTABS]
    return all_tabs, home, dropped


def _lucent_menu():
    scripts = xbmcvfs.translatePath('special://skin/scripts/')
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import menu  # Lucent's own menu editor
    return menu


def run():
    if xbmc.getSkinDir() != LUCENT:
        xbmcgui.Dialog().ok(TITLE, T(32094))             # switch to Lucent first
        return
    if not _load('hubs') and not _load('homewidgets'):
        xbmcgui.Dialog().ok(TITLE, T(32095))             # no AF3 menu on this box
        return
    if not xbmcgui.Dialog().yesno(TITLE, T(32096)):      # replaces the Lucent menu?
        return
    try:
        menu = _lucent_menu()
        m = menu.Menu()
        defaults, _start = menu.default_tabs()
        tabs, home, dropped = build(defaults)
        m.tabs = tabs
        m.start = home
        m.save()
    except Exception as e:
        _log('failed: %s' % e)
        xbmcgui.Dialog().ok(TITLE, T(32097) % e)
        return
    n = sum(len(t['widgets']) for t in tabs)
    _log('%d tabs, %d widgets, %d left out' % (len(tabs), n, len(dropped)))
    msg = T(32098) % (len(tabs), n)
    if dropped:
        msg += '[CR][CR]' + T(32099) + '[CR]' + '[CR]'.join(dropped[:12])
        if len(dropped) > 12:
            msg += '[CR]…'
    xbmcgui.Dialog().ok(TITLE, msg)
    xbmc.executebuiltin('ReloadSkin()')


if __name__ == '__main__':
    run()
