# -*- coding: utf-8 -*-
"""
search_nextep.py - ABUKARIM TOOLS 4.7.23

Search All and the episode that just finished.

kodi.log 2026-11-06 08:40:32: an episode Search All played (TMDbHelper ->
"AB Search All" -> Red Light) reached the end; Kodi then started the item it
was launched from again - TMDbHelper's ?info=play URL of THAT episode - and
TMDbHelper's default player opened Search All for the episode just watched.
(Red Light's own next episode was 0.2 s too late: its scrape finished after
the file ended.)

So: when Search All is asked for exactly the episode it played and that
episode ended by itself (not stopped) a moment ago, the request is Kodi's
replay, not the user's: Search All does nothing and the add-on that played
the episode starts the next one its own way (ab_search.replay_after_end()).
(4.7.22 searched the next episode itself instead.)

The service keeps one xbmc.Player here:
  onAVStarted      a real file (not TMDbHelper's dummy.mp4) that starts within
                   a few minutes of a Search All pick is that pick
  onPlayBackEnded  that pick ended by itself -> Home abk.search.ended
  onPlayBackStopped / another file  -> forget it
"""
import json
import threading
import time

import xbmc
import xbmcgui

PICK_PROP = 'abk.search.pick'        # ab_search: {tmdb_id, season, episode, ts} at every episode pick
ENDED_PROP = 'abk.search.ended'      # here: the pick that ended by itself, {..., ts}
_PICK_TO_PLAY = 300                   # s from pick to picture (scrape + resolve)
_ENDED_MAX_AGE = 180                  # s from end to the replay request

_PLAYER = []


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools Search All] %s' % msg, level)


def _home():
    return xbmcgui.Window(10000)


def _get(prop):
    try:
        return json.loads(_home().getProperty(prop) or '{}')
    except Exception:
        return {}


def _same(a, b):
    return all(str(a.get(k)) == str(b.get(k)) for k in ('tmdb_id', 'season', 'episode'))


# ───────────────────────── written by ab_search ─────────────────────────

def mark_pick(media):
    """Search All picked a source: remember the episode (movies: forget)."""
    win = _home()
    if media.get('media_type') != 'episode':
        win.clearProperty(PICK_PROP)
        return
    win.setProperty(PICK_PROP, json.dumps({'tmdb_id': media['tmdb_id'], 'season': media['season'],
                                           'episode': media['episode'], 'ts': time.time()}))


def take_ended(media):
    """True (once) when `media` is the Search All episode that just ended by itself."""
    m = _get(ENDED_PROP)
    if not m or not _same(m, media):
        return False
    _home().clearProperty(ENDED_PROP)
    return time.time() - float(m.get('ts') or 0) <= _ENDED_MAX_AGE


# ───────────────────────── service side ─────────────────────────

class _Player(xbmc.Player):
    def __init__(self):
        super().__init__()
        self.bound = None

    def _file(self):
        try:
            return self.getPlayingFile() or ''
        except Exception:
            return ''

    def onAVStarted(self):
        f = self._file()
        if not f or f.endswith('dummy.mp4'):
            return              # TMDbHelper's stand-in: neither the pick nor another file
        pick = _get(PICK_PROP)
        if pick and time.time() - float(pick.get('ts') or 0) <= _PICK_TO_PLAY:
            self.bound = pick
            _home().clearProperty(PICK_PROP)     # one playback per pick
            _home().clearProperty(ENDED_PROP)
            _log('playing the S%sE%s picked in Search All' % (pick.get('season'), pick.get('episode')))
        else:
            self.bound = None

    def onPlayBackEnded(self):
        if self.bound:
            m = dict(self.bound, ts=time.time())
            _home().setProperty(ENDED_PROP, json.dumps(m))
            _log('S%sE%s ended by itself - Kodi replaying it will be ignored'
                 % (m.get('season'), m.get('episode')))
        self.bound = None

    def onPlayBackStopped(self):
        self.bound = None


def start(monitor):
    """Service: keep the player listening for the rest of the session."""
    def _keep():
        _PLAYER.append(_Player())
        while not monitor.waitForAbort(60):
            pass
        del _PLAYER[:]
    threading.Thread(target=_keep, name='abk-search-nextep', daemon=True).start()
