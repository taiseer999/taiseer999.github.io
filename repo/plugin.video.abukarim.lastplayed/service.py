# -*- coding: utf-8 -*-
"""Last Played (ABUKARIM) - recording service.

Flow
  * While you browse, the last few playable add-on items you focus are
    remembered (path + title + ids). Internet add-ons play through source
    pickers and temporary debrid links, so the item you CLICKED is the link
    worth keeping for replay.
  * onAVStarted (stream really playing, metadata final): read the item from
    the player, skip TMDbHelper's dummy.mp4 / AF3 background trailers, work
    out movie / episode from the metadata and ids, pick the replay link.
  * After `min_seconds` of real playback the entry is written (so a crash or
    power cut still keeps it); position is saved every 30 s and on stop.
Every decision is logged at INFO level as one line, so a kodi.log always
shows why something was or wasn't recorded.
"""

import os
import sys
import time
import json
import threading
from urllib.parse import parse_qsl

import xbmc
import xbmcaddon
import xbmcgui

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'lib'))
import store  # noqa: E402

ADDON_ID = store.ADDON_ID
TMDBH = 'plugin.video.themoviedb.helper'
CLICK_TTL = 1800          # s a focused item stays a replay candidate
LAUNCH_TTL = 900          # s between TMDbHelper splash and the real stream


def _rpc(method, params):
    try:
        r = json.loads(xbmc.executeJSONRPC(json.dumps(
            {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})))
        return r.get('result') or {}
    except Exception:
        return {}


def _plugin_id(url):
    if url and url.startswith('plugin://'):
        return url[9:].split('/')[0].split('?')[0]
    return ''


def _addon_name(aid):
    try:
        return xbmcaddon.Addon(aid).getAddonInfo('name') or aid
    except Exception:
        return aid


def _norm(t):
    return ''.join(ch for ch in str(t or '').lower() if ch.isalnum())


def _int(v, default=-1):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


_VEXT = ('.mkv', '.mp4', '.avi', '.m2ts', '.ts', '.mov', '.webm', '.m4v', '.wmv', '.iso')


def _filename_title(t, stream=''):
    t = (t or '').strip()
    if not t:
        return True
    if t.lower().endswith(_VEXT):
        return True
    base = stream.split('|')[0].split('?')[0].rstrip('/').split('/')[-1]
    return bool(base) and (t == base or t == base.rsplit('.', 1)[0])


def _clean_name(name):
    """'Husbands.in.Action.2026.iTA-KOR.WEBDL.2160p...mkv' -> ('Husbands in Action', 2026)"""
    import re
    base = name.split('|')[0].split('?')[0].rstrip('/').split('/')[-1]
    if base.lower().endswith(_VEXT):
        base = base.rsplit('.', 1)[0]
    base = re.sub(r'[._]+', ' ', base)
    m = re.search(r'^(.*?)[ (\[]*((?:19|20)\d{2})\b', base)
    if m and m.group(1).strip():
        return m.group(1).strip(' -'), int(m.group(2))
    m = re.search(r'^(.*?)\b(?:S\d{1,2}E\d{1,3}|2160p|1080p|720p|480p|WEB|BluRay|HDTV)', base, re.I)
    return (m.group(1) if m else base).strip(' -'), ''


def _weak(e):
    """No ids, not library, title is just the file name."""
    ids = e.get('ids') or {}
    return (not ids.get('tmdb') and not ids.get('imdb') and not ids.get('tvdb')
            and (e.get('dbid') or 0) <= 0
            and (e.get('type') not in ('movie', 'episode') or _filename_title(e.get('title'), e.get('stream', ''))))


class Settings(object):
    def __init__(self):
        self.reload()

    def reload(self):
        a = xbmcaddon.Addon(ADDON_ID)

        def b(k, d):
            try:
                return a.getSettingBool(k)
            except Exception:
                return d

        def i(k, d):
            try:
                return a.getSettingInt(k)
            except Exception:
                return d

        self.movies = b('rec_movies', True)
        self.episodes = b('rec_episodes', True)
        self.other = b('rec_other', False)
        self.min_seconds = max(0, i('min_seconds', 30))
        self.limit = max(10, i('limit', 100))
        try:
            ex = a.getSettingString('exclude')
        except Exception:
            ex = ''
        self.exclude = [x.strip().lower() for x in (ex or '').split(',') if x.strip()]


class Recorder(object):
    def __init__(self):
        self.cfg = Settings()
        self.clicked = []            # newest first
        self.launcher = ('', 0.0)
        self.current = None          # entry being played
        self.written = False
        self.started = 0.0
        self.last_save = 0.0
        self.lock = threading.RLock()

    # ---------------------------------------------------------- browsing
    def track_focus(self):
        gi = xbmc.getInfoLabel
        path = gi('ListItem.FileNameAndPath')
        if not path.startswith('plugin://') or path.startswith('plugin://%s' % ADDON_ID):
            return
        if xbmc.getCondVisibility('ListItem.IsFolder'):
            return
        for c in self.clicked:
            if c['path'] == path:
                c['t'] = time.time()
                self.clicked.remove(c)
                self.clicked.insert(0, c)
                return
        self.clicked.insert(0, {
            'path': path, 't': time.time(),
            'title': gi('ListItem.Title') or gi('ListItem.Label'),
            'show': gi('ListItem.TVShowTitle'), 'year': gi('ListItem.Year'),
            'season': gi('ListItem.Season'), 'episode': gi('ListItem.Episode'),
            'tmdb': gi('ListItem.UniqueID(tmdb)'), 'imdb': gi('ListItem.IMDBNumber'),
            'playable': gi('ListItem.Property(IsPlayable)').lower() != 'false',
        })
        del self.clicked[8:]

    def _clicked_for(self, e):
        now = time.time()
        recent = [c for c in self.clicked if now - c['t'] <= CLICK_TTL]
        ids, show = e['ids'], e['show']
        se = (str(e['season']), str(e['episode']))
        for c in recent:          # ids first: a "sources as folder" row never wins
            if ids.get('imdb') and c['imdb'] == ids['imdb'] and (not show or not c['season'] or (c['season'], c['episode']) == se):
                return c
            if ids.get('tmdb') and c['tmdb'] == str(ids['tmdb']) and (not show or (c['season'], c['episode']) == se):
                return c
        for c in recent:
            if show:
                if _norm(show) == _norm(c['show']) and (c['season'], c['episode']) == se:
                    return c
            elif _norm(e['title']) and _norm(e['title']) == _norm(c['title']):
                if not e['year'] or not c['year'] or str(e['year']) == c['year']:
                    return c
        return None

    # ---------------------------------------------------------- playback
    def on_av_started(self, player):
        try:
            if not player.isPlaying():
                return
            playing = player.getPlayingFile() or ''
        except RuntimeError:
            return
        full = xbmc.getInfoLabel('Player.FilenameAndPath') or playing
        low = playing.replace('\\', '/').lower()

        if low.endswith('/dummy.mp4') or low == 'dummy.mp4':
            for cand in (full, xbmc.getInfoLabel('Player.Folderpath')):
                if cand.startswith('plugin://%s/' % TMDBH) and 'info=play' in cand:
                    self.launcher = (cand, time.time())
            store.log('skip: TMDbHelper splash (launcher kept)')
            return
        if (xbmc.getInfoLabel('Window(Home).Property(abk.trailer)')
                or any(k in low for k in ('plugin.video.youtube', 'googlevideo.com',
                                          'youtube.com/', 'imdb-video', 'media-imdb.com'))):
            store.log('skip: trailer %s' % playing[:80])
            return

        if self.current:
            self.on_stop(False)       # playlist / next episode without a stop
        entry = self._read_item(player, playing, full)
        # Fen Light & co. start the stream first and fill the info tag a moment
        # later - give it a few seconds before falling back to other hints
        tries = 0
        replay = bool(xbmcgui.Window(10000).getProperty(store.REPLAY_PROP))
        while entry and not replay and _weak(entry) and tries < 8:
            xbmc.sleep(500)
            tries += 1
            try:
                if not player.isPlayingVideo():
                    return
            except RuntimeError:
                return
            entry = self._read_item(player, playing, full, consume=False)
        if entry and tries:
            store.log('metadata after %.1fs: %s "%s" ids=%s' % (tries * 0.5, entry['type'], entry['title'], entry['ids']))
        if entry and not replay and _weak(entry):
            entry = self._enrich(entry)
            entry = self._finish(entry, full, playing)
        elif entry:
            entry = self._finish(entry, full, playing)
        if not entry:
            return
        reason = self._reject(entry)
        if reason:
            store.log('skip: %s "%s" (%s)' % (entry['type'], entry['title'], reason))
            return
        with self.lock:
            self.current, self.written = entry, False
            self.started, self.last_save = time.time(), 0.0
        store.log('playing: %s "%s" from %s -> %s'
                  % (entry['type'], entry['title'], entry['source'] or '?', entry['path'][:120]))
        if self.cfg.min_seconds == 0:
            self._write()

    def _read_item(self, player, playing, full, consume=True):
        is_video = xbmc.getCondVisibility('Player.HasVideo')
        if not is_video:
            return None
        item = (_rpc('Player.GetItem', {'playerid': 1, 'properties': [
            'title', 'year', 'art', 'showtitle', 'season', 'episode', 'file',
            'uniqueid', 'plot', 'runtime', 'imdbnumber', 'tvshowid']}) or {}).get('item') or {}
        try:
            tag = player.getVideoInfoTag()
        except Exception:
            tag = None

        def tg(fn, *a):
            try:
                return getattr(tag, fn)(*a) if tag is not None else ''
            except Exception:
                return ''

        mtype = (item.get('type') or '').lower()
        if mtype in ('', 'unknown'):
            mtype = (tg('getMediaType') or '').lower()
        title = item.get('title') or tg('getTitle') or item.get('label') or ''
        year = item.get('year') or tg('getYear') or ''
        show = item.get('showtitle') or tg('getTVShowTitle') or ''
        season = _int(item.get('season'), -1)
        episode = _int(item.get('episode'), -1)
        if season < 0:
            season = _int(tg('getSeason'), -1)
        if episode < 0:
            episode = _int(tg('getEpisode'), -1)
        dbid = _int(item.get('id'), -1)
        if dbid <= 0:
            dbid = _int(tg('getDbId'), -1)
        ids = {k: str(v) for k, v in (item.get('uniqueid') or {}).items() if v}
        for k in ('tmdb', 'imdb', 'tvdb'):
            if not ids.get(k):
                v = tg('getUniqueID', k)
                if v:
                    ids[k] = str(v)
        imdb = item.get('imdbnumber') or tg('getIMDBNumber') or ''
        if not ids.get('imdb') and str(imdb).startswith('tt'):
            ids['imdb'] = imdb

        if mtype not in ('movie', 'episode', 'musicvideo'):
            if show and season >= 0 and episode > 0:
                mtype = 'episode'
            elif ids.get('tmdb') or ids.get('imdb') or (year and title):
                mtype = 'movie'
            else:
                mtype = 'video'

        art = dict(item.get('art') or {})
        for k in ('poster', 'fanart', 'thumb', 'clearlogo', 'landscape',
                  'tvshow.poster', 'tvshow.fanart', 'tvshow.clearlogo'):
            if not art.get(k):
                v = xbmc.getInfoLabel('Player.Art(%s)' % k)
                if v:
                    art[k] = v
        art = {k: v for k, v in art.items() if v and isinstance(v, str)}

        e = {
            'key': '%d' % int(time.time() * 1000), 'type': mtype, 'title': title,
            'year': year or '', 'show': show, 'season': season, 'episode': episode,
            'dbid': dbid if dbid > 0 else 0, 'ids': ids,
            'plot': item.get('plot') or tg('getPlot') or '', 'art': art,
            'stream': playing, 'played_at': int(time.time()),
            'position': 0, 'total': 0,
        }

        e['_item_file'] = item.get('file') or ''
        return e

    def _finish(self, e, full, playing):
        """Pick the replay link / source for a fully read entry."""
        item = {'file': e.pop('_item_file', '')}
        # started from our own list? keep the stored sources link, only the
        # stream/time get refreshed (a saved-link replay must not turn the
        # temporary stream URL into the replay link)
        rp = self._take_replay()
        if rp:
            old = store.get(rp.get('key', ''))
            if old and (rp.get('mode') == 'saved' or store.same(old, e)):
                self.launcher = ('', 0.0)
                e['path'] = old.get('path') or playing
                e['playable'] = old.get('playable', True)
                e['source_id'] = old.get('source_id') or ''
                e['source'] = old.get('source') or ''
                if rp.get('mode') == 'saved':
                    e['dbid'] = old.get('dbid') or 0
                    for k in ('type', 'title', 'year', 'show', 'season', 'episode', 'ids', 'plot'):
                        if old.get(k) not in (None, '', {}, -1):
                            e[k] = old[k]
                store.log('replay (%s) of "%s" - keeping stored link' % (rp.get('mode'), old.get('title')))
                return e

        # replay link
        path, src, playable = '', '', True
        lp, lt = self.launcher
        self.launcher = ('', 0.0)
        if lp and time.time() - lt < LAUNCH_TTL:
            path = lp
        if not path and e['dbid'] <= 0:
            c = self._clicked_for(e)
            if c:
                path, playable = c['path'], c.get('playable', True)
        if not path and full.startswith('plugin://'):
            path = full
        if not path and e['dbid'] <= 0:
            path = self._tmdbh_link(e)
            if path:
                recent = [c for c in self.clicked if time.time() - c['t'] < CLICK_TTL]
                src = _plugin_id(recent[0]['path']) if recent else ''
        if not path:
            path = item.get('file') or full or playing
        e['path'] = path
        e['playable'] = playable
        e['source_id'] = src or _plugin_id(path)
        if e['dbid'] > 0:
            e['source'] = xbmc.getLocalizedString(14022)       # "Library"
        else:
            e['source'] = _addon_name(e['source_id']) if e['source_id'] else ''
        return e

    def _enrich(self, e):
        """Player gave no ids: use Home(script.trakt.ids), the TMDbHelper
        launcher and the last item focused before playback."""
        ids = e['ids']
        try:
            tk = json.loads(xbmc.getInfoLabel('Window(Home).Property(script.trakt.ids)') or '{}')
        except ValueError:
            tk = {}
        for k in ('tmdb', 'imdb', 'tvdb'):
            if tk.get(k) and not ids.get(k):
                ids[k] = str(tk[k])
        lp, lt = self.launcher
        ltype = ''
        if lp and time.time() - lt < LAUNCH_TTL:
            q = dict(parse_qsl(lp.split('?', 1)[-1]))
            ltype = q.get('tmdb_type', '')
            if q.get('tmdb_id') and not ids.get('tmdb'):
                ids['tmdb'] = q['tmdb_id']
            if q.get('imdb_id') and not ids.get('imdb'):
                ids['imdb'] = q['imdb_id']
            if ltype == 'tv':
                if e['season'] < 0:
                    e['season'] = _int(q.get('season'), -1)
                if e['episode'] < 0:
                    e['episode'] = _int(q.get('episode'), -1)
        if ids.get('imdb') and not str(ids['imdb']).startswith('tt'):
            ids.pop('imdb')

        c = self._clicked_for(e) if (ids.get('tmdb') or ids.get('imdb')) else None
        if not c:
            # nothing to match on: the item focused right before playback
            # (source pickers take a while, so allow a few minutes)
            now = time.time()
            recent = [x for x in self.clicked if now - x['t'] <= 300]
            remote = e['stream'].lower().startswith(('http://', 'https://'))
            if recent and remote and not (ids.get('tmdb') or ids.get('imdb')):
                c = recent[0]
            elif recent:
                for x in recent:
                    if (x['tmdb'] and x['tmdb'] == ids.get('tmdb')) or (x['imdb'] and x['imdb'] == ids.get('imdb')):
                        c = x
                        break
        if c:
            if _filename_title(e['title'], e['stream']) and c.get('title'):
                e['title'] = c['title']
            for k in ('show', 'year'):
                if not e[k] and c.get(k):
                    e[k] = c[k]
            if e['season'] < 0:
                e['season'] = _int(c.get('season'), -1)
            if e['episode'] < 0:
                e['episode'] = _int(c.get('episode'), -1)
            if c.get('tmdb') and not ids.get('tmdb'):
                ids['tmdb'] = c['tmdb']
            if c.get('imdb', '').startswith('tt') and not ids.get('imdb'):
                ids['imdb'] = c['imdb']
        if e['type'] not in ('movie', 'episode', 'musicvideo'):
            if ltype == 'tv' or (e['show'] and e['season'] >= 0 and e['episode'] > 0):
                e['type'] = 'episode'
            elif ltype == 'movie' or ids.get('tmdb') or ids.get('imdb'):
                e['type'] = 'movie'
        if _filename_title(e['title'], e['stream']):
            t, y = _clean_name(e['title'] or e['stream'])
            if t:
                e['title'] = t
            if y and not e['year']:
                e['year'] = y
        store.log('enriched: %s "%s" ids=%s (trakt.ids=%s launcher=%s focused=%s)' % (
            e['type'], e['title'], ids, bool(tk), bool(ltype), c['title'] if c else None))
        return e

    def on_started(self, player):
        """onPlayBackStarted: catch the TMDbHelper launcher even when its
        dummy.mp4 is gone before onAVStarted fires."""
        try:
            playing = player.getPlayingFile() or ''
        except RuntimeError:
            playing = ''
        for cand in (xbmc.getInfoLabel('Player.FilenameAndPath'), playing,
                     xbmc.getInfoLabel('Player.Folderpath')):
            if cand.startswith('plugin://%s/' % TMDBH) and 'info=play' in cand:
                self.launcher = (cand, time.time())
                store.log('launcher: %s' % cand[:120])
                return

    @staticmethod
    def _take_replay():
        home = xbmcgui.Window(10000)
        raw = home.getProperty(store.REPLAY_PROP)
        if not raw:
            return None
        home.clearProperty(store.REPLAY_PROP)
        try:
            rp = json.loads(raw)
        except ValueError:
            return None
        if time.time() - float(rp.get('t') or 0) > LAUNCH_TTL:
            return None
        return rp

    @staticmethod
    def _tmdbh_link(e):
        if not xbmc.getCondVisibility('System.HasAddon(%s)' % TMDBH):
            return ''
        ids = e['ids']
        base = 'plugin://%s/?info=play' % TMDBH
        if e['type'] == 'movie':
            if ids.get('tmdb'):
                return '%s&tmdb_type=movie&tmdb_id=%s' % (base, ids['tmdb'])
            if ids.get('imdb'):
                return '%s&tmdb_type=movie&imdb_id=%s' % (base, ids['imdb'])
        if e['type'] == 'episode' and e['season'] >= 0 and e['episode'] > 0 and ids.get('tmdb'):
            return '%s&tmdb_type=tv&tmdb_id=%s&season=%s&episode=%s' % (
                base, ids['tmdb'], e['season'], e['episode'])
        return ''

    def _reject(self, e):
        if not e['title']:
            return 'no title'
        t = e['type']
        if t == 'movie' and not self.cfg.movies:
            return 'movies off'
        if t == 'episode' and not self.cfg.episodes:
            return 'episodes off'
        if t not in ('movie', 'episode') and not self.cfg.other:
            return 'other videos off'
        hay = ('%s %s %s' % (e['source_id'], e['path'], e['stream'])).lower()
        for x in self.cfg.exclude:
            if x in hay or x == (e['source'] or '').lower():
                return 'excluded: %s' % x
        return ''

    def _write(self):
        with self.lock:
            e = self.current
            if not e:
                return
            try:
                e = store.upsert(dict(e), self.cfg.limit)
                self.current['key'] = e['key']
                self.written = True
                store.log('recorded: %s "%s"' % (e['type'], e['title']))
            except Exception as ex:
                store.log('write failed: %s' % ex, xbmc.LOGWARNING)

    def tick(self, player):
        """Called every second while playing."""
        with self.lock:
            if not self.current:
                return
            try:
                pos, tot = player.getTime(), player.getTotalTime()
            except RuntimeError:
                return
            self.current['position'], self.current['total'] = int(pos), int(tot)
            if not self.written and time.time() - self.started >= self.cfg.min_seconds:
                self._write()
            elif self.written and time.time() - self.last_save >= 30:
                self.last_save = time.time()
                store.update(self.current['key'], position=int(pos), total=int(tot))

    def on_stop(self, ended=False):
        with self.lock:
            e, self.current = self.current, None
            if not e or not self.written:
                if e:
                    store.log('not kept: "%s" played < %ss' % (e['title'], self.cfg.min_seconds))
                return
            pos = e['total'] if ended else e['position']
            store.update(e['key'], position=pos, total=e['total'], played_at=int(time.time()))


class Player(xbmc.Player):
    def __init__(self, rec):
        super(Player, self).__init__()
        self.rec = rec

    def onPlayBackStarted(self):
        try:
            self.rec.on_started(self)
        except Exception:
            pass

    def onAVStarted(self):
        try:
            self.rec.on_av_started(self)
        except Exception as ex:
            store.log('capture failed: %r' % ex, xbmc.LOGWARNING)

    def onPlayBackStopped(self):
        self.rec.on_stop(False)

    def onPlayBackEnded(self):
        self.rec.on_stop(True)

    def onPlayBackError(self):
        self.rec.current = None


class Monitor(xbmc.Monitor):
    def __init__(self, rec):
        super(Monitor, self).__init__()
        self.rec = rec

    def onSettingsChanged(self):
        self.rec.cfg.reload()


HEARTBEAT = 'abk.lastplayed.alive'


def main():
    # one copy per session: Kodi's own start, or ABUKARIM TOOLS' guardian when
    # Kodi skipped this service at boot (seen on Kodi 22 / Python 3.14)
    home = xbmcgui.Window(10000)
    if home.getProperty(HEARTBEAT):
        store.log('service already running - this copy exits')
        return
    home.setProperty(HEARTBEAT, str(int(time.time())))
    try:
        store.migrate_old()
    except Exception as ex:
        store.log('migration failed: %r' % ex, xbmc.LOGWARNING)
    rec = Recorder()
    mon = Monitor(rec)
    player = Player(rec)
    store.log('service started')
    while not mon.abortRequested():
        try:
            if player.isPlayingVideo():
                rec.tick(player)
            if not xbmc.getCondVisibility('Window.IsActive(fullscreenvideo)'):
                rec.track_focus()
        except Exception:
            pass
        if mon.waitForAbort(1):
            break
    rec.on_stop(False)
    home.clearProperty(HEARTBEAT)
    del player


main()
