# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""AF3 Trailer buttons through the auto-trailer sources (ABUKARIM TOOLS 3.2.52).

Arctic Fuse 3's own "Trailer" shortcuts - the Trailer button of the info page,
the Trailer entry of the context menu, the trailer lists and the Repeat button
of the trailer dialog - all end in AF3's trailer dialog (window 1123), which
used to PlayMedia() the item's trailer link as is. That link is TMDbHelper's
plugin://plugin.video.youtube/... address, which does not play without a
working YouTube add-on. The patcher points the dialog at this script instead,
so the button plays the trailer the way the auto-trailers do:

  * the source set in Toggles > AF3 auto-trailers comes first
    (YouTube = the title's YouTube trailer through plugin.video.youtube,
     IMDb = IMDb's own MP4 at the chosen quality), the other one second;
  * 4.12.62: when YouTube refuses the video (8.x "confirm you're not a bot")
    nothing opens - IMDb plays instead, AF3's own YouTube link included;
  * the original link is the last resort, exactly as before.

The trailer plays windowed inside AF3's dialog, with sound, and carries no ids
(scrobblers ignore it). It works whether the auto-trailers are on or off.

    RunScript(special://home/addons/plugin.program.abukarimtools/trailer_play.py)
"""
import sys
import time

import xbmc
import xbmcgui
import xbmcvfs

ROOT = xbmcvfs.translatePath('special://home/addons/plugin.program.abukarimtools/')
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from resources.lib.af3_trailers import config, imdb, youtube  # noqa: E402

HOME = xbmcgui.Window(10000)
DIALOG_ID = 1123
TOKEN_PROP = 'abk.trailer.button'
LOOKUP = 'abk://lookup'   # PlayTrailer placeholder: no link, find it by id


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools TrailerButton] %s' % msg, level)


def _info(label):
    try:
        return xbmc.getInfoLabel(label) or ''
    except Exception:
        return ''


def _home(name):
    return _info('Window(Home).Property(%s)' % name)


def _ids():
    """IMDb id, TMDb id and 'movie'/'tvshow' of the title the dialog is for.

    The trailer dialog sets TMDbHelper.ContextMenu, so TMDbHelper keeps its
    Home properties for the item the button was pressed on."""
    imdb_id = ''
    for value in (_home('TMDbHelper.ListItem.UniqueID.imdb'),
                  _home('TMDbHelper.ListItem.imdb_id'),
                  _home('TMDbHelper.ListItem.IMDBNumber'),
                  _home('TMDbHelper.ListItem.tvshow.imdb_id'),
                  _info('ListItem.UniqueID(imdb)'),
                  _info('ListItem.IMDBNumber')):
        imdb_id = imdb.clean_imdb(value)
        if imdb_id:
            break
    tmdb_id = ''
    for value in (_home('TMDbHelper.ListItem.Monitor.TMDb_ID'),
                  _home('TMDbHelper.ListItem.UniqueID.tmdb'),
                  _home('TMDbHelper.ListItem.tmdb_id'),
                  _info('ListItem.UniqueID(tmdb)')):
        value = value.strip()
        if value.isdigit():
            tmdb_id = value
            break
    kind = (_home('TMDbHelper.ListItem.Monitor.TMDb_Type')
            or _home('TMDbHelper.ListItem.base_dbtype')
            or _info('ListItem.DBType')).lower()
    dbtype = 'tvshow' if kind in ('tv', 'tvshow', 'season', 'episode') else 'movie'
    return imdb_id, tmdb_id, dbtype


def _still_wanted(token):
    """The dialog is still open and no newer button press took over."""
    return (xbmc.getCondVisibility('Window.IsVisible(%d)' % DIALOG_ID)
            and HOME.getProperty(TOKEN_PROP) == token)


def _play(url, title, mime=None):
    li = xbmcgui.ListItem(label=title or 'Trailer', path=url, offscreen=True)
    if url.startswith('plugin://'):
        li.setProperty('IsPlayable', 'true')     # YouTube answers with setResolvedUrl
    else:
        try:
            li.setMimeType(mime or 'video/mp4')
            li.setContentLookup(False)
        except Exception:
            pass
    try:
        tag = li.getVideoInfoTag()
        tag.setTitle(title or 'Trailer')
        tag.setMediaType('video')                # no ids: scrobblers leave it alone
    except Exception:
        pass
    xbmc.Player().play(url, li, windowed=True)


def _from_youtube(link, imdb_id, tmdb_id, dbtype, title):
    """The title's YouTube trailer through the YouTube add-on (4.12.61;
    NewPipe removed in 4.12.62)."""
    if not youtube.installed():
        _log('the YouTube add-on is not installed/enabled - skipped')
        return None
    api_key = ''
    if not youtube.youtube_id(link) and (tmdb_id or imdb_id):
        from resources.lib.af3_trailers import engine
        api_key = engine._tmdb_key()
    vid, how = youtube.find_id(link, api_key, tmdb_id, dbtype, imdb_id, log=_log)
    if not vid:
        return None
    _log('"%s": YouTube trailer %s (from %s)' % (title, vid, how))
    return {'url': youtube.plugin_url(vid, title), 'mime': None}


FAIL_GRACE = 6.0      # no stream, no spinner, nothing playing: YouTube refused it
OPEN_TIMEOUT = 25.0


def _playing_video():
    try:
        player = xbmc.Player()
        return player.getPlayingFile() if player.isPlayingVideo() else ''
    except Exception:
        return ''


def _opened(token, before):
    """4.12.62: after a YouTube play request - True once a new video plays,
    False when YouTube gave no stream (8.x bot check), None when the dialog
    closed or a newer press took over."""
    monitor = xbmc.Monitor()
    started = time.monotonic()
    while not monitor.abortRequested():
        current = _playing_video()
        if current and current != before:
            return True
        if not _still_wanted(token):
            return None
        waited = time.monotonic() - started
        if waited > OPEN_TIMEOUT:
            return False
        if (waited > FAIL_GRACE and not current
                and not xbmc.getCondVisibility('Window.IsActive(busydialog) | '
                                               'Window.IsActive(busydialognocancel) | '
                                               'Player.HasMedia')):
            return False
        if monitor.waitForAbort(0.25):
            return None
    return None


def _play_youtube(url, title, token, fallback, as_link=False):
    """Play a YouTube trailer; when YouTube refuses it, ``fallback()`` gives
    the IMDb one ({'url','mime'} or None), which plays instead. ``as_link``:
    AF3's own trailer link, played with PlayMedia as AF3 does."""
    before = _playing_video()
    if as_link:
        xbmc.executebuiltin('PlayMedia("%s",False,1)' % url.replace('"', '\\"'))
    else:
        _play(url, title)
    result = _opened(token, before)
    if result is not False:
        return result
    _log('"%s": YouTube gave no stream - trying IMDb' % title)
    found = fallback()
    if found and _still_wanted(token):
        _play(found['url'], title, found.get('mime'))
        return True
    if _still_wanted(token):
        from resources.lib.i18n import T
        xbmcgui.Dialog().notification(title, T(30649), xbmcgui.NOTIFICATION_INFO, 3000)
        xbmc.executebuiltin('Dialog.Close(%d)' % DIALOG_ID)
    return False


def _from_imdb(imdb_id, tmdb_id, dbtype, title, quality):
    if not imdb_id and tmdb_id:
        from resources.lib.af3_trailers import engine
        imdb_id = engine._imdb_for_tmdb(tmdb_id, dbtype)
    if not imdb_id:
        return None
    resolver = imdb.TrailerResolver(config.CACHE_DIR, quality=quality, log=_log)
    stream = resolver.resolve(imdb_id, timeout=8.0)
    try:
        resolver.flush()
    except Exception:
        pass
    if not stream or not stream.get('url'):
        _log('"%s" (%s): no IMDb trailer' % (title, imdb_id))
        return None
    _log('"%s" (%s): IMDb trailer %sp' % (title, imdb_id, stream.get('height') or '?'))
    return {'url': stream['url'], 'mime': stream.get('mime')}


def run():
    link = HOME.getProperty('PlayTrailer')
    # 3.4.15: AF3 50.11's Trailer button (restored by the patcher) passes
    # LOOKUP when the item carries no trailer link - search by id instead.
    if link == LOOKUP:
        link = ''
    title = HOME.getProperty('PlayTrailerTitle') or 'Trailer'
    token = '%.6f' % time.time()
    HOME.setProperty(TOKEN_PROP, token)
    cfg = config.load()
    quality = cfg.get('quality', 720)
    imdb_box = {}

    def imdb_fallback():
        if 'ids' not in imdb_box:
            imdb_box['ids'] = _ids()
        i_imdb, i_tmdb, i_type = imdb_box['ids']
        try:
            return _from_imdb(i_imdb, i_tmdb, i_type, title, quality)
        except Exception as exc:
            _log('imdb lookup failed: %s' % exc, xbmc.LOGWARNING)
            return None

    # 3.2.52: only in the "Trailer button only" mode of AF3 Auto Trailers;
    # in the other modes (or with Auto Trailers off) the button plays AF3's
    # own link as before - and with no link at all (3.4.15) it falls through
    # to the YouTube/IMDb search below rather than doing nothing.
    # 4.12.62: AF3's link is YouTube's - when YouTube refuses it, IMDb plays.
    if not (cfg.get('enabled') and cfg.get('show') == 'buttons') and link:
        if youtube.is_youtube_link(link) and youtube.installed():
            _log('"%s": Trailer-button mode is off - AF3 link, IMDb if YouTube refuses it'
                 % title)
            _play_youtube(link, title, token, imdb_fallback, as_link=True)
            return
        _log('"%s": Trailer-button mode is off - AF3 link as is' % title)
        xbmc.executebuiltin('PlayMedia("%s",False,1)' % link.replace('"', '\\"'))
        return
    imdb_id, tmdb_id, dbtype = _ids()
    imdb_box['ids'] = (imdb_id, tmdb_id, dbtype)
    _log('button: "%s" link=%s imdb=%s tmdb=%s (%s) source=%s'
         % (title, link[:120], imdb_id or '-', tmdb_id or '-', dbtype, cfg.get('source')))

    order = ('imdb', 'youtube') if cfg.get('source') == 'imdb' else ('youtube', 'imdb')
    for source in order:
        try:
            if source == 'youtube':
                found = _from_youtube(link, imdb_id, tmdb_id, dbtype, title)
            else:
                found = _from_imdb(imdb_id, tmdb_id, dbtype, title, quality)
        except Exception as exc:
            _log('%s lookup failed: %s' % (source, exc), xbmc.LOGWARNING)
            found = None
        if not _still_wanted(token):
            _log('dialog closed (or a newer press) - nothing played')
            return
        if found:
            if source == 'youtube':
                fallback = imdb_fallback if 'imdb' not in order[:order.index(source)] \
                    else (lambda: None)
                _play_youtube(found['url'], title, token, fallback)
            else:
                _play(found['url'], title, found.get('mime'))
            return

    youtube_dead = youtube.is_youtube_link(link) and not youtube.installed()
    if link and not youtube_dead:
        _log('no trailer from YouTube/IMDb - playing the original link')
        xbmc.executebuiltin('PlayMedia("%s",False,1)' % link.replace('"', '\\"'))
    else:
        from resources.lib.i18n import T
        xbmcgui.Dialog().notification(title, T(30649), xbmcgui.NOTIFICATION_INFO, 3000)
        xbmc.executebuiltin('Dialog.Close(%d)' % DIALOG_ID)


if __name__ == '__main__':
    run()
