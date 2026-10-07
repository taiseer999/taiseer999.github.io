# -*- coding: utf-8 -*-
"""Last Played (ABUKARIM) - lists.

Widget paths (newest first, optional &limit=N):
    plugin://plugin.video.abukarim.lastplayed/?list=all
    plugin://plugin.video.abukarim.lastplayed/?list=movies
    plugin://plugin.video.abukarim.lastplayed/?list=episodes
    plugin://plugin.video.abukarim.lastplayed/?list=inprogress
    plugin://plugin.video.abukarim.lastplayed/?list=other
"""

import json
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


def _saved_link(e):
    """The stream that actually played last time, if it is replayable on its own."""
    s = (e.get('stream') or '').strip()
    if not s or s.startswith('plugin://'):
        return ''
    low = s.split('|')[0].replace('\\', '/').lower()
    if low.endswith('/dummy.mp4') or low == 'dummy.mp4':
        return ''
    if s == (e.get('path') or ''):
        return ''
    return s


def _is_library(e):
    p = e.get('path') or ''
    return bool(e.get('dbid')) and not p.startswith('plugin://')


def _setting_int(k, d):
    try:
        return ADDON.getSettingInt(k)
    except Exception:
        return d


def _setting_bool(k, d):
    try:
        return ADDON.getSettingBool(k)
    except Exception:
        return d


def _hms(sec):
    sec = int(sec or 0)
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return '%d:%02d:%02d' % (h, m, s) if h else '%d:%02d' % (m, s)


def _link_alive(link):
    """Quick check that a saved stream is still served (debrid links expire)."""
    url_, _, hdr = link.partition('|')
    if not url_.lower().startswith(('http://', 'https://')):
        if url_.startswith(('special://', 'smb://', 'nfs://', '/')) or (len(url_) > 2 and url_[1] == ':'):
            import xbmcvfs
            return xbmcvfs.exists(url_)
        return True                     # other protocols: let the player try
    import urllib.request
    import urllib.error
    headers = {'User-Agent': 'Mozilla/5.0'}
    headers.update(dict(parse_qsl(hdr)))
    headers['Range'] = 'bytes=0-0'
    try:
        req = urllib.request.Request(url_, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status < 400
    except urllib.error.HTTPError as ex:
        return ex.code in (405, 416)    # method/range not allowed but file is there
    except Exception:
        return False


def _play_item(e, path, offset=0.0):
    li = _listitem(e, for_play=True)
    li.setPath(path)
    if offset > 0:
        li.setProperty('StartOffset', '%.1f' % offset)
    xbmc.Player().play(path, li)


def _mark_replay(e, mode):
    xbmcgui.Window(10000).setProperty(store.REPLAY_PROP, json.dumps(
        {'key': e.get('key', ''), 'mode': mode, 't': time.time()}))


def play_saved(e, offset=0.0, fallback=True):
    link = _saved_link(e)
    if link and _setting_bool('check_saved', True):
        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
        try:
            alive = _link_alive(link)
        finally:
            xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
        if not alive:
            store.log('saved link expired for "%s"' % e.get('title'))
            store.update(e.get('key', ''), stream='')
            link = ''
    if not link:
        if fallback and e.get('path'):
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), L(30085),
                                          ADDON.getAddonInfo('icon'), 4000)
            return play_sources(e)
        xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), L(30086),
                                      ADDON.getAddonInfo('icon'), 4000)
        return
    store.log('replay saved link: "%s"' % e.get('title'))
    _mark_replay(e, 'saved')
    _play_item(e, link, offset)


def play_sources(e):
    path = e.get('path') or ''
    if not path:
        return play_saved(e, fallback=False)
    store.log('replay from sources: "%s" -> %s' % (e.get('title'), path[:120]))
    _mark_replay(e, 'sources')
    if path.startswith('plugin://'):
        if e.get('playable', True):
            xbmc.executebuiltin('PlayMedia("%s")' % path)
        else:
            xbmc.executebuiltin('RunPlugin("%s")' % path)
    else:
        _play_item(e, path)


def play(key, force=''):
    e = store.get(key)
    if not e:
        xbmc.executebuiltin('Container.Refresh')
        return
    pos = float(e.get('position') or 0)
    resumable = 3 <= _pct(e) <= 92 and pos > 0
    name = e.get('source') or (_plugin_id(e.get('path')) or '')

    # Kodi library / local file: no sources to pick, just resume or start
    if _is_library(e) and force != 'sources':
        off = 0.0
        if resumable:
            c = xbmcgui.Dialog().contextmenu([L(30080) % _hms(pos), L(30081)])
            if c < 0:
                return
            off = pos if c == 0 else 0.0
        _mark_replay(e, 'library')
        return _play_item(e, e['path'], off)

    saved = _saved_link(e)
    mode = {'saved': 1, 'sources': 2}.get(force, _setting_int('play_mode', 0))
    if not saved:
        mode = 2

    if mode == 2:
        return play_sources(e)

    if mode == 1:                       # saved first, resume prompt like Kodi's
        off = 0.0
        if resumable:
            c = xbmcgui.Dialog().contextmenu([L(30080) % _hms(pos), L(30081)])
            if c < 0:
                return
            off = pos if c == 0 else 0.0
        return play_saved(e, off)

    # ask every time
    opts, acts = [], []
    if resumable:
        opts.append(L(30082) % _hms(pos))
        acts.append(('saved', pos))
    opts.append(L(30083))
    acts.append(('saved', 0.0))
    opts.append(L(30084) % name if name else L(30087))
    acts.append(('sources', 0.0))
    c = xbmcgui.Dialog().select(_label(e), opts)
    if c < 0:
        return
    act, off = acts[c]
    if act == 'saved':
        play_saved(e, off)
    else:
        play_sources(e)


def _plugin_id(p):
    if p and p.startswith('plugin://'):
        return p[9:].split('/')[0].split('?')[0]
    return ''


def _listitem(e, for_play=False):
    li = xbmcgui.ListItem(_label(e), _when(e.get('played_at')), offscreen=True)
    path = e.get('path') or e.get('stream') or ''
    li.setPath(path if for_play else url(action='play', key=e.get('key', '')))
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
    # progress bar in lists only; resuming is decided in play() (StartOffset)
    if pct and e.get('total') and not for_play:
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

    li.setProperty('abk.saved', 'true' if _saved_link(e) else 'false')
    if for_play:
        return li
    # the list item runs our play router (non-playable, it starts the player itself)
    li.setProperty('IsPlayable', 'false')
    key = e.get('key', '')
    cm = []
    if _saved_link(e) and not _is_library(e):
        cm.append((L(30088), 'RunPlugin(%s)' % url(action='play', key=key, mode='saved')))
    if e.get('path') and not _is_library(e):
        cm.append((L(30089), 'RunPlugin(%s)' % url(action='play', key=key, mode='sources')))
    cm += [(L(30050), 'RunPlugin(%s)' % url(action='remove', key=key)),
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
    li.setArt({'icon': ic, 'thumb': ic, 'fanart': os.path.join(MEDIA, 'fanart.jpg')})
    xbmcplugin.addDirectoryItem(HANDLE, url(action='clear'), li, isFolder=False)
    li = xbmcgui.ListItem(L(30070), offscreen=True)
    ic = os.path.join(MEDIA, 'support.png')
    li.setArt({'icon': ic, 'thumb': ic, 'fanart': os.path.join(MEDIA, 'fanart.jpg')})
    xbmcplugin.addDirectoryItem(HANDLE, url(action='support'), li, isFolder=False)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def main():
    action = ARGS.get('action')
    if action == 'play':
        play(ARGS.get('key', ''), ARGS.get('mode', ''))
        return
    if action == 'support':
        import support
        support.show()
        return
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
