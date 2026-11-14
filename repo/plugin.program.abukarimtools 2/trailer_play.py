# -*- coding: utf-8 -*-
"""AF3 Trailer buttons through the auto-trailer sources (ABUKARIM TOOLS 3.2.52).

Arctic Fuse 3's own "Trailer" shortcuts - the Trailer button of the info page,
the Trailer entry of the context menu, the trailer lists and the Repeat button
of the trailer dialog - all end in AF3's trailer dialog (window 1123), which
used to PlayMedia() the item's trailer link as is. That link is TMDbHelper's
plugin://plugin.video.youtube/... address, which does not play without a
working YouTube add-on. The patcher points the dialog at this script instead,
so the button plays the trailer the way the auto-trailers do:

  * the source set in Toggles > AF3 auto-trailers comes first
    (NewPipe = the title's YouTube trailer through plugin.video.newpipe,
     IMDb = IMDb's own MP4 at the chosen quality), the other one second;
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

from resources.lib.af3_trailers import config, imdb, newpipe  # noqa: E402

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
        li.setProperty('IsPlayable', 'true')     # NewPipe answers with setResolvedUrl
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


def _from_newpipe(link, imdb_id, tmdb_id, dbtype, title):
    if not newpipe.installed():
        _log('NewPipe is not installed/enabled - skipped')
        return None
    vid = newpipe.youtube_id(link)
    how = 'trailer link'
    if not vid and (tmdb_id or imdb_id):
        from resources.lib.af3_trailers import engine
        vid = newpipe.tmdb_youtube_id(engine._tmdb_key(), tmdb_id, dbtype, imdb_id, log=_log)
        how = 'TMDb'
    if not vid:
        return None
    _log('"%s": NewPipe trailer %s (from %s)' % (title, vid, how))
    return {'url': newpipe.plugin_url(vid, title), 'mime': None}


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
    # 3.2.52: only in the "Trailer button only" mode of AF3 Auto Trailers;
    # in the other modes (or with Auto Trailers off) the button plays AF3's
    # own link exactly as before - and with no link at all (3.4.15) it
    # falls through to the NewPipe/IMDb search below rather than doing nothing
    if not (cfg.get('enabled') and cfg.get('show') == 'buttons') and link:
        _log('"%s": Trailer-button mode is off - AF3 link as is' % title)
        xbmc.executebuiltin('PlayMedia("%s",False,1)' % link.replace('"', '\\"'))
        return
    imdb_id, tmdb_id, dbtype = _ids()
    _log('button: "%s" link=%s imdb=%s tmdb=%s (%s) source=%s'
         % (title, link[:120], imdb_id or '-', tmdb_id or '-', dbtype, cfg.get('source')))

    order = ('imdb', 'newpipe') if cfg.get('source') == 'imdb' else ('newpipe', 'imdb')
    for source in order:
        try:
            if source == 'newpipe':
                found = _from_newpipe(link, imdb_id, tmdb_id, dbtype, title)
            else:
                found = _from_imdb(imdb_id, tmdb_id, dbtype, title, cfg.get('quality', 720))
        except Exception as exc:
            _log('%s lookup failed: %s' % (source, exc), xbmc.LOGWARNING)
            found = None
        if not _still_wanted(token):
            _log('dialog closed (or a newer press) - nothing played')
            return
        if found:
            _play(found['url'], title, found.get('mime'))
            return

    youtube_dead = (link.startswith('plugin://plugin.video.youtube')
                    and not xbmc.getCondVisibility('System.HasAddon(plugin.video.youtube) + '
                                                   'System.AddonIsEnabled(plugin.video.youtube)'))
    if link and not youtube_dead:
        _log('no trailer from NewPipe/IMDb - playing the original link')
        xbmc.executebuiltin('PlayMedia("%s",False,1)' % link.replace('"', '\\"'))
    else:
        from resources.lib.i18n import T
        xbmcgui.Dialog().notification(title, T(30649), xbmcgui.NOTIFICATION_INFO, 3000)
        xbmc.executebuiltin('Dialog.Close(%d)' % DIALOG_ID)


if __name__ == '__main__':
    run()
