# -*- coding: utf-8 -*-
"""Last Played (ABUKARIM) - lists.

Widget paths (newest first, optional &limit=N):
    plugin://plugin.video.abukarim.lastplayed/?list=all
    plugin://plugin.video.abukarim.lastplayed/?list=movies
    plugin://plugin.video.abukarim.lastplayed/?list=episodes
    plugin://plugin.video.abukarim.lastplayed/?list=inprogress
    plugin://plugin.video.abukarim.lastplayed/?list=other
"""

import os
import sys
import time
from urllib.parse import parse_qsl, urlencode

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'lib'))
import store  # noqa: E402

ADDON = xbmcaddon.Addon()
L = ADDON.getLocalizedString
BASE = sys.argv[0]
HANDLE = int(sys.argv[1]) if len(sys.argv) > 1 else -1
ARGS = dict(parse_qsl(sys.argv[2][1:])) if len(sys.argv) > 2 else {}
MEDIA = os.path.join(ADDON.getAddonInfo('path'), 'resources', 'media')


def url(**kw):
    return '%s?%s' % (BASE, urlencode(kw))


def _pct(e):
    try:
        tot = float(e.get('total') or 0)
        return int(round(100.0 * float(e.get('position') or 0) / tot)) if tot > 0 else 0
    except (TypeError, ValueError):
        return 0


def _when(ts):
    if not ts:
        return ''
    lt = time.localtime(ts)
    today = time.localtime()
    hm = time.strftime('%H:%M', lt)
    if lt.tm_year == today.tm_year and lt.tm_yday == today.tm_yday:
        return '%s %s' % (L(30060), hm)
    if lt.tm_year == today.tm_year and lt.tm_yday == today.tm_yday - 1:
        return '%s %s' % (L(30061), hm)
    return time.strftime('%Y-%m-%d', lt)


def _filter(items, which):
    if which == 'movies':
        return [i for i in items if i.get('type') == 'movie']
    if which == 'episodes':
        return [i for i in items if i.get('type') == 'episode']
    if which == 'other':
        return [i for i in items if i.get('type') not in ('movie', 'episode')]
    if which == 'inprogress':
        return [i for i in items if 3 <= _pct(i) <= 92]
    return items


def _label(e):
    if e.get('type') == 'episode' and e.get('show'):
        s, ep = e.get('season', -1), e.get('episode', -1)
        try:
            if int(s) >= 0 and int(ep) > 0:
                return '%s S%02dE%02d - %s' % (e['show'], int(s), int(ep), e.get('title', ''))
        except (TypeError, ValueError):
            pass
        return '%s - %s' % (e['show'], e.get('title', ''))
    return e.get('title', '')


def _listitem(e):
    li = xbmcgui.ListItem(_label(e), _when(e.get('played_at')), offscreen=True)
    path = e.get('path') or e.get('stream') or ''
    li.setPath(path)
    tag = li.getVideoInfoTag()
    mtype = e.get('type') if e.get('type') in ('movie', 'episode', 'musicvideo') else 'video'
    tag.setMediaType(mtype)
    tag.setTitle(e.get('title') or '')
    try:
        if e.get('year'):
            tag.setYear(int(e['year']))
    except (TypeError, ValueError):
        pass
    if e.get('plot'):
        tag.setPlot(e['plot'])
    if mtype == 'episode':
        tag.setTvShowTitle(e.get('show') or '')
        try:
            if int(e.get('season', -1)) >= 0:
                tag.setSeason(int(e['season']))
            if int(e.get('episode', -1)) > 0:
                tag.setEpisode(int(e['episode']))
        except (TypeError, ValueError):
            pass
    ids = {k: str(v) for k, v in (e.get('ids') or {}).items() if v}
    if ids:
        tag.setUniqueIDs(ids, 'tmdb' if 'tmdb' in ids else list(ids)[0])
        if ids.get('imdb'):
            tag.setIMDBNumber(ids['imdb'])
    if e.get('dbid'):
        try:
            tag.setDbId(int(e['dbid']))
        except Exception:
            pass
    if e.get('total'):
        tag.setDuration(int(e['total']))
    if e.get('played_at'):
        tag.setLastPlayed(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(e['played_at'])))
    pct = _pct(e)
    # resume point only where Kodi plays the path itself (library / direct file);
    # plugin links re-resolve and their player add-on handles resume.
    if pct and not path.startswith('plugin://') and e.get('total'):
        tag.setResumePoint(float(e.get('position') or 0), float(e['total']))
    li.setProperty('PercentPlayed', str(pct))
    li.setProperty('abk.source', e.get('source') or '')
    li.setProperty('abk.played', _when(e.get('played_at')))

    art = dict(e.get('art') or {})
    if mtype == 'episode':
        art.setdefault('poster', art.get('tvshow.poster', ''))
        art.setdefault('fanart', art.get('tvshow.fanart', ''))
    art.setdefault('thumb', art.get('thumb') or art.get('landscape') or art.get('poster', ''))
    art.setdefault('icon', art.get('poster') or art.get('thumb') or '')
    li.setArt({k: v for k, v in art.items() if v})

    li.setProperty('IsPlayable', 'true' if e.get('playable', True) else 'false')
    cm = [(L(30050), 'RunPlugin(%s)' % url(action='remove', key=e.get('key', ''))),
          (L(30051), 'RunPlugin(%s)' % url(action='clear')),
          (L(30052), 'Addon.OpenSettings(%s)' % store.ADDON_ID)]
    li.addContextMenuItems(cm)
    return li


def show_list(which, limit):
    items = _filter(store.load(), which)
    if limit:
        items = items[:limit]
    content = {'movies': 'movies', 'episodes': 'episodes'}.get(which, 'videos')
    xbmcplugin.setContent(HANDLE, content)
    xbmcplugin.setPluginCategory(HANDLE, ADDON.getAddonInfo('name'))
    for e in items:
        li = _listitem(e)
        xbmcplugin.addDirectoryItem(HANDLE, li.getPath(), li, isFolder=False)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LASTPLAYED)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_TITLE)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def root():
    items = store.load()
    entries = [(30010, 'all', 'all.png'), (30011, 'movies', 'movies.png'),
               (30012, 'episodes', 'episodes.png'), (30013, 'inprogress', 'inprogress.png')]
    if any(i.get('type') not in ('movie', 'episode') for i in items):
        entries.append((30014, 'other', 'all.png'))
    for sid, which, icon in entries:
        n = len(_filter(items, which))
        li = xbmcgui.ListItem('%s (%d)' % (L(sid), n), offscreen=True)
        ic = os.path.join(MEDIA, icon)
        li.setArt({'icon': ic, 'thumb': ic, 'fanart': os.path.join(MEDIA, 'fanart.jpg')})
        xbmcplugin.addDirectoryItem(HANDLE, url(list=which), li, isFolder=True)
    li = xbmcgui.ListItem(L(30051), offscreen=True)
    ic = os.path.join(MEDIA, 'clear.png')
    li.setArt({'icon': ic, 'thumb': ic})
    xbmcplugin.addDirectoryItem(HANDLE, url(action='clear'), li, isFolder=False)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def main():
    action = ARGS.get('action')
    if action == 'remove':
        store.remove(ARGS.get('key', ''))
        xbmc.executebuiltin('Container.Refresh')
        return
    if action == 'clear':
        if xbmcgui.Dialog().yesno(ADDON.getAddonInfo('name'), L(30053)):
            store.clear()
            xbmc.executebuiltin('Container.Refresh')
        return
    which = ARGS.get('list')
    if which:
        try:
            limit = int(ARGS.get('limit') or 0)
        except ValueError:
            limit = 0
        show_list(which, limit)
    else:
        root()


main()
