# -*- coding: utf-8 -*-
"""
disc_menu.py - ABUKARIM TOOLS (4.7.36)

The runtime half of Toggles > "AF3: Disc Menu for ISO Streams" (skin bool
abk.discmenu, af3_discmenu_toggle.py). Two AF3 OSD buttons call it while a
Blu-ray ISO plays from a stream (http... .iso):

  go=menu    the ISO plays as the main movie (normal AF3 player): reopen the
             same ISO in disc-menu mode (HDMV / BD-J menus).
  go=normal  the ISO plays in disc-menu mode: back to the main movie in the
             normal player, at the same point.

Kodi paths (xbmc/utils/URIUtils.cpp, GetBlurayPath / GetBlurayMenuPath):
  udf://<enc iso url>/                       the ISO opened as a disc
  bluray://<enc udf path>/menu               disc-menu mode
  bluray://<enc udf path>/root/main          directory: the main movie playlist
  bluray://<enc udf path>/BDMV/PLAYLIST/00800.mpls   one playlist = main movie
The new item carries the ListItem property playlist_chosen=true, so Kodi's own
"Blu-ray playback mode" setting (Settings > Player > Discs) does not turn the
path into something else again (ApplicationPlay GetMenuDecisions).
"""
import hashlib
from urllib.parse import unquote

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

TITLE = 'ABUKARIM TOOLS'
_HOME = 10000
_POS_PROP = 'abk.discmenu.pos.%s'
_RFC1738 = '-._!()'                 # what Kodi's URIUtils::URLEncode leaves alone
_MAIN_MIN = 40 * 60                 # a title this long is the movie, not a menu loop


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools DiscMenu] %s' % msg, level)


def _enc(text):
    """Kodi's URIUtils::URLEncode (RFC1738 set, lower-case hex)."""
    out = []
    for b in text.encode('utf-8'):
        c = chr(b)
        if c.isascii() and (c.isalnum() or c in _RFC1738):
            out.append(c)
        else:
            out.append('%%%02x' % b)
    return ''.join(out)


def _host(url, proto):
    """Decoded host part of proto://<host>/... (Kodi encodes nested URLs there)."""
    rest = url[len(proto):]
    return unquote(rest.split('/', 1)[0])


def _iso_url(path):
    """The stream URL of the ISO behind a raw / udf:// / bluray:// path."""
    for _ in range(3):
        low = path.lower()
        if low.startswith('bluray://'):
            path = _host(path, 'bluray://')
        elif low.startswith('udf://'):
            path = _host(path, 'udf://')
        else:
            break
    low = path.lower()
    if low.startswith('http') and '.iso' in low:
        return path
    return ''


def _bluray_base(iso):
    """bluray://<enc udf://<enc iso>/>/ - as URIUtils::GetBlurayPath builds it."""
    return 'bluray://%s/' % _enc('udf://%s/' % _enc(iso))


def _playing_path():
    for label in ('Player.Filenameandpath',):
        p = xbmc.getInfoLabel(label)
        if p and _iso_url(p):
            return p
    try:
        p = xbmc.Player().getPlayingFile()
        if p and _iso_url(p):
            return p
    except Exception:
        pass
    return ''


def _key(iso):
    return hashlib.md5(iso.encode('utf-8')).hexdigest()[:12]


def _listitem(path, start=0.0, chosen=True):
    """A ListItem for path that keeps what the OSD shows (title, art, ids)."""
    gi = xbmc.getInfoLabel
    title = gi('VideoPlayer.Title') or gi('Player.Title')
    li = xbmcgui.ListItem(label=title, path=path, offscreen=True)
    try:
        src = xbmc.Player().getVideoInfoTag()
    except Exception:
        src = None
    tag = li.getVideoInfoTag()

    def _set(fn, *val):
        try:
            if all(v not in (None, '', -1, 0) for v in val):
                fn(*val)
        except Exception:
            pass

    if src is not None:
        _set(tag.setTitle, src.getTitle() or title)
        _set(tag.setOriginalTitle, src.getOriginalTitle())
        _set(tag.setMediaType, src.getMediaType())
        _set(tag.setYear, src.getYear())
        _set(tag.setPlot, src.getPlot())
        _set(tag.setTvShowTitle, src.getTVShowTitle())
        _set(tag.setSeason, src.getSeason())
        _set(tag.setEpisode, src.getEpisode())
        _set(tag.setIMDBNumber, src.getIMDBNumber())
        _set(tag.setGenres, src.getGenres())
        _set(tag.setDuration, src.getDuration())
        try:
            ids = {}
            for k in ('tmdb', 'imdb', 'tvdb', 'trakt'):
                v = src.getUniqueID(k)
                if v:
                    ids[k] = v
            if ids:
                tag.setUniqueIDs(ids, 'tmdb' if 'tmdb' in ids else list(ids)[0])
        except Exception:
            pass
    else:
        _set(tag.setTitle, title)
    art = {}
    for k in ('poster', 'fanart', 'thumb', 'clearlogo', 'landscape', 'banner',
              'keyart', 'discart', 'tvshow.poster', 'tvshow.fanart', 'tvshow.clearlogo'):
        v = gi('Player.Art(%s)' % k)
        if v:
            art[k] = v
    if art:
        li.setArt(art)
    # Kodi's "Blu-ray playback mode" must not rewrite the path we chose
    if chosen:
        li.setProperty('playlist_chosen', 'true')
    if start > 1:
        li.setProperty('StartOffset', '%.3f' % start)
    return li


def _main_playlist(base):
    """bluray://.../BDMV/PLAYLIST/xxxxx.mpls of the main movie, or ''."""
    for sub in ('root/main', 'root/titles'):
        try:
            _dirs, files = xbmcvfs.listdir(base + sub)
        except Exception as e:
            _log('listdir %s failed: %s' % (sub, e), xbmc.LOGWARNING)
            continue
        for f in files:
            if f.lower().endswith('.mpls'):
                _log('main movie playlist (%s): %s' % (sub, f))
                return base + 'BDMV/PLAYLIST/' + f
    return ''


def _play(path, li):
    xbmc.executebuiltin('Dialog.Close(videoosd,true)')
    xbmc.Player().play(path, li)


def _busy(on):
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)' if on
                        else 'Dialog.Close(busydialognocancel,true)')


def _to_menu(iso):
    player = xbmc.Player()
    try:
        pos = player.getTime()
    except Exception:
        pos = 0.0
    xbmcgui.Window(_HOME).setProperty(_POS_PROP % _key(iso), '%.3f' % pos)
    path = _bluray_base(iso) + 'menu'
    _log('to disc menu (left the main movie at %.0fs): %s' % (pos, path))
    xbmcgui.Dialog().notification(TITLE, T(32107), xbmcgui.NOTIFICATION_INFO, 2500)
    _play(path, _listitem(path))


def _to_normal(iso):
    player = xbmc.Player()
    win = xbmcgui.Window(_HOME)
    key = _POS_PROP % _key(iso)
    # Started the movie from the disc menu? Then keep its place; otherwise
    # go back to where the main movie was left for the menu.
    start = 0.0
    try:
        cur, total = player.getTime(), player.getTotalTime()
        if total >= _MAIN_MIN and cur > 5:
            start = cur
    except Exception:
        pass
    if not start:
        try:
            start = float(win.getProperty(key) or 0)
        except ValueError:
            start = 0.0
    win.clearProperty(key)
    base = _bluray_base(iso)
    _busy(True)
    try:
        path = _main_playlist(base)
    finally:
        _busy(False)
    if not path:
        # Not readable here: the plain ISO as the stream add-on played it
        # (Kodi's own Blu-ray playback mode decides; no resume point).
        _log('main movie playlist not found - plain ISO', xbmc.LOGWARNING)
        xbmcgui.Dialog().notification(TITLE, T(32109), xbmcgui.NOTIFICATION_WARNING, 4000)
        _play(iso, _listitem(iso, chosen=False))
        return
    _log('to normal player at %.0fs: %s' % (start, path))
    xbmcgui.Dialog().notification(TITLE, T(32108), xbmcgui.NOTIFICATION_INFO, 2500)
    _play(path, _listitem(path, start))


def run(go):
    if not xbmc.getCondVisibility('Player.HasVideo'):
        return
    path = _playing_path()
    iso = _iso_url(path) if path else ''
    if not iso:
        _log('not an ISO stream: %r' % path)
        xbmcgui.Dialog().notification(TITLE, T(32106), xbmcgui.NOTIFICATION_WARNING, 3000)
        return
    if go == 'normal':
        _to_normal(iso)
    else:
        _to_menu(iso)
