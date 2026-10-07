# -*- coding: utf-8 -*-
"""AF3 auto-trailers: the background engine (ABUKARIM TOOLS).

3.2.35 - FULL SCREEN mode (the default): the trailer is opened windowed as
before, and the moment its first frames are on screen the engine switches
Kodi to the full-screen video window, so there is no black frame and no
spinner over an empty screen - the background video simply grows to full
screen. Leaving full screen (Back) stops the trailer and returns to the page
with the cursor where it was; the title is not replayed until the cursor
moves. Full-screen trailers always play with sound and also work when AF3's
'Background video' is off. The old behaviour ('Behind the page') is one
setting away in the Toggles entry.

Runs on its own thread inside the ABUKARIM TOOLS service. When the cursor
rests on a movie or TV show on Arctic Fuse 3's Home or one of its hubs, the
title's trailer is looked up on IMDb (see imdb.py) and played WINDOWED. AF3
already draws any playing video as the page background (Background_Video in
Includes_Background.xml, unless Background.DisableVideo is set), so the skin
needs no new controls; the patcher only teaches its Back key and its
now-playing footer to ignore a trailer (Window(Home).Property(abk.trailer)).

Design, borrowed from Dex Hub's trailer director but simplified because this
engine owns its own thread (nothing here runs on Kodi's interface thread, so
blocking on the player is fine):

  * one trailer at a time; moving to another title, leaving Home/the hubs,
    opening the info dialog or the screensaver stops it;
  * a trailer only starts when nothing else is playing, and real playback that
    replaces it is never stopped (the engine only lets go and restores the
    volume);
  * a trailer that finished is not repeated until the cursor moves away;
  * silent trailers turn Kodi's volume to 0 with the SetVolume builtin (no
    volume dialog) and give it back afterwards; a marker file restores it
    after a crash on the next start;
  * the trailer item carries no ids and the generic 'video' media type, so
    scrobblers (Trakt, TMDbHelper) ignore it;
  * while Kodi's busy spinner is up (the stream opening) ListItem.* reads
    the dialog, so a missing title only stops the trailer after a grace time.
"""
import glob
import json
import os
import re
import threading
import time
import traceback
from urllib.request import Request, urlopen

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.af3_trailers import config, imdb, newpipe

HOME_ID = 10000
PROP = 'abk.trailer'
ENGINE_PROP = 'abukarimtools.trailers.engine'
SKIN_ID = 'skin.arctic.fuse.3'
TMDBH_ID = 'plugin.video.themoviedb.helper'
MARKER = os.path.join(config.PROFILE, 'muted_by_trailer')

START_TIMEOUT = 12.0
START_TIMEOUT_NEWPIPE = 25.0   # NewPipe resolves the YouTube stream first
MISS_GRACE = 1.0        # seconds without our title (no dialog open) before stopping
MISS_GRACE_MAX = 15.0   # ... and with a dialog/busy spinner open
PREFETCH_AFTER = 0.3

_PAGES = ('Window.IsActive(home) | Window.IsActive(1101) | Window.IsActive(1102) | '
          'Window.IsActive(1103) | Window.IsActive(1104)')
_BLOCKERS = ('System.ScreenSaverActive | Skin.HasSetting(Background.DisableVideo) | '
             'Window.IsVisible(1123) | Window.IsVisible(movieinformation) | '
             'Window.IsVisible(DialogVideoInfo.xml)')
# full-screen trailers do not need AF3's background video
_BLOCKERS_FS = ('System.ScreenSaverActive | '
                'Window.IsVisible(1123) | Window.IsVisible(movieinformation) | '
                'Window.IsVisible(DialogVideoInfo.xml)')
_FULLSCREEN = 'Window.IsActive(fullscreenvideo)'
FS_FIRST_FRAME = 0.15   # seconds of video played before going full screen
FS_TIMEOUT = 4.0        # full-screen window never came up: keep it windowed
_OPEN_BLOCKERS = 'System.HasActiveModalDialog | Window.IsActive(1180)'
_BUSY = 'Window.IsActive(busydialog) | Window.IsActive(busydialognocancel)'
# 3.2.43~beta4: after any OTHER playback activity (a real stream, TMDbHelper's
# dummy splash, a source picker resolving under the busy spinner, a failed
# ResolvePath) Kodi's playlist player can be left half-reset for a while. A
# trailer posted into that state crashed Kodi in
# CPlayListPlayer::OnApplicationMessage ("item that's out of range", core
# 2026-10-07 20:28:10 - 10 s after Fen Light's resolve failed). So no trailer
# starts until things have been quiet this long:
COOLDOWN_AFTER_PLAYBACK = 30.0
OWN_TEARDOWN = 4.0      # our own trailer closing does not count as activity
_ACTIVITY = 'Player.HasMedia | ' + _BUSY


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools Trailers] %s' % msg, level)


_DIAG_SEEN = set()


def _diag(key, msg):
    """Log a diagnostic line once per distinct key (capped per session)."""
    if key in _DIAG_SEEN or len(_DIAG_SEEN) > 300:
        return
    _DIAG_SEEN.add(key)
    _log(msg)


def _info(label):
    try:
        return xbmc.getInfoLabel(label) or ''
    except Exception:
        return ''


def _cond(expr):
    try:
        return bool(xbmc.getCondVisibility(expr))
    except Exception:
        return False


def _rpc(method, params=None):
    try:
        raw = xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method,
                                              'params': params or {}}))
        return (json.loads(raw) or {}).get('result')
    except Exception:
        return None


def _audio_state():
    result = _rpc('Application.GetProperties', {'properties': ['volume', 'muted']}) or {}
    try:
        volume = int(result.get('volume'))
    except Exception:
        volume = None
    return volume, bool(result.get('muted'))


def _set_volume(percent):
    xbmc.executebuiltin('SetVolume(%d)' % max(0, min(100, int(percent))), True)


def restore_after_crash():
    """Undo a volume a crashed session left at 0, and stale properties."""
    if os.path.exists(MARKER):
        try:
            with open(MARKER, 'r') as handle:
                saved = int(float(handle.read().strip() or 0))
        except Exception:
            saved = 0
        volume, _muted = _audio_state()
        if saved > 0 and volume == 0:
            _set_volume(saved)
            _log('restored volume %d left at 0 by an interrupted trailer' % saved)
        try:
            os.remove(MARKER)
        except Exception:
            pass
    try:
        xbmcgui.Window(HOME_ID).clearProperty(PROP)
    except Exception:
        pass


# ------------------------------------------------------------- TMDb -> IMDb
_TMDB_KEY = {'value': None}
_TMDB_IMDB = {}
_KEY_RE = re.compile(r'''['"]([0-9a-f]{32})['"]''')


def _tmdb_key():
    """TMDbHelper's own API key (read from its installed files, once)."""
    if _TMDB_KEY['value'] is not None:
        return _TMDB_KEY['value']
    key = ''
    root = os.path.join(xbmcvfs.translatePath('special://home/addons/'), TMDBH_ID)
    patterns = ('resources/tmdbhelper/lib/api/api_keys/tmdb*.py',
                'resources/tmdbhelper/lib/api/api_keys/*.py',
                'resources/tmdbhelper/lib/api/tmdb/*.py')
    for pattern in patterns:
        for path in sorted(glob.glob(os.path.join(root, pattern))):
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as handle:
                    text = handle.read()
            except Exception:
                continue
            if 'tmdb' not in os.path.basename(path).lower() and 'TMDB' not in text.upper():
                continue
            match = _KEY_RE.search(text)
            if match:
                key = match.group(1)
                break
        if key:
            break
    _TMDB_KEY['value'] = key
    if not key:
        _log('no TMDb key found in TMDbHelper; titles without an IMDb id get no trailer')
    return key


def _imdb_for_tmdb(tmdb_id, dbtype):
    cache_key = '%s:%s' % (dbtype, tmdb_id)
    if cache_key in _TMDB_IMDB:
        return _TMDB_IMDB[cache_key]
    key = _tmdb_key()
    if not key:
        return ''
    kind = 'tv' if dbtype == 'tvshow' else 'movie'
    url = 'https://api.themoviedb.org/3/%s/%s/external_ids?api_key=%s' % (kind, tmdb_id, key)
    imdb_id = ''
    try:
        with urlopen(Request(url, headers={'Accept': 'application/json'}), timeout=6) as resp:
            data = json.loads(resp.read().decode('utf-8', 'replace')) or {}
        imdb_id = imdb.clean_imdb(data.get('imdb_id'))
    except Exception as exc:
        _log('TMDb id lookup failed for %s: %s' % (cache_key, type(exc).__name__))
        return ''        # network trouble: not cached, tried again next time
    _TMDB_IMDB[cache_key] = imdb_id
    return imdb_id


# ------------------------------------------------------------------ engine
class Engine(object):
    def __init__(self, monitor, origin='service'):
        self.monitor = monitor
        self.origin = origin
        self.player = xbmc.Player()
        self.home = xbmcgui.Window(HOME_ID)
        self.state = 'idle'            # idle | starting | playing
        self.url = ''
        self.key = ''
        self.started = 0.0
        self.cand_key = ''
        self.cand_since = 0.0
        self.done_key = ''             # finished / no trailer: not again until the cursor moves
        self.lookups = {}              # key -> {'event': Event, 'stream': dict|None}
        self.saved_volume = 0
        self.mute_owned = False
        self.resolver = None
        self.quality = None
        self._last_error = 0.0
        self._was_enabled = None
        self.miss_since = None
        self._focus_logs = 0
        self.fs_mode = False           # this trailer is meant to go full screen
        self.fs_asked = 0.0            # when ActivateWindow(fullscreenvideo) was sent
        self.fs_seen = False           # the full-screen window has been up
        self.quiet_until = time.monotonic() + COOLDOWN_AFTER_PLAYBACK   # boot settle
        self.released_at = 0.0         # when our own trailer was let go
        self._quiet_logged = False

    # ------------------------------------------------------------- helpers
    def _resolver(self, quality):
        if self.resolver is None or self.quality != quality:
            self.resolver = imdb.TrailerResolver(config.CACHE_DIR, quality=quality, log=_log)
            self.quality = quality
            self.lookups.clear()
        return self.resolver

    def _playing_file(self):
        try:
            if self.player.isPlaying():
                return self.player.getPlayingFile() or ''
        except Exception:
            pass
        return ''

    def _ours(self, current):
        if not current or not self.url:
            return False
        if current == self.url:
            return True
        # a plugin trailer (NewPipe) plays under its RESOLVED path: the first
        # file that shows up while ours is opening is ours (nothing else was
        # playing when it started - _start is only reached without media)
        if getattr(self, 'via_plugin', False) and self.url.startswith('plugin://'):
            if self.state == 'starting':
                _log('trailer resolved by NewPipe: %s' % current[:120])
                self.url = current
                return True
            return False
        return current.split('?', 1)[0] == self.url.split('?', 1)[0]

    @staticmethod
    def _eligible(fullscreen=False):
        if xbmc.getSkinDir() != SKIN_ID:
            return False
        return _cond('[%s] + ![%s]' % (_PAGES, _BLOCKERS_FS if fullscreen else _BLOCKERS))

    @staticmethod
    def _focused():
        """The focused movie/show: {'key','imdb','tmdb','dbtype','label'} or None."""
        dbtype = _info('ListItem.DBType').lower()
        if dbtype not in ('movie', 'tvshow'):
            return None
        label = _info('ListItem.Label')
        imdb_id = ''
        for lbl in ('ListItem.UniqueID(imdb)', 'ListItem.IMDBNumber',
                    'ListItem.Property(imdb_id)', 'ListItem.Property(tvshow.imdb_id)'):
            imdb_id = imdb.clean_imdb(_info(lbl))
            if imdb_id:
                break
        if not imdb_id:
            # TMDbHelper's monitor publishes the focused item on Home; only
            # trust it when it is about the same title
            tlabel = _info('Window(Home).Property(TMDbHelper.ListItem.Label)')
            if tlabel and tlabel == label:
                for prop in ('UniqueID.imdb', 'imdb_id', 'IMDBNumber'):
                    imdb_id = imdb.clean_imdb(_info('Window(Home).Property(TMDbHelper.ListItem.%s)' % prop))
                    if imdb_id:
                        break
        tmdb_id = ''
        for lbl in ('ListItem.UniqueID(tmdb)', 'ListItem.Property(tmdb_id)'):
            value = _info(lbl).strip()
            if value.isdigit():
                tmdb_id = value
                break
        if imdb_id:
            key = imdb_id
        elif tmdb_id:
            key = 'tmdb:%s:%s' % (dbtype, tmdb_id)
        else:
            _diag('noid:' + label, 'focused %s "%s" carries no IMDb/TMDb id - no trailer'
                  % (dbtype, label))
            return None
        trailer = _info('ListItem.Trailer')
        if not newpipe.youtube_id(trailer):
            tlabel = _info('Window(Home).Property(TMDbHelper.ListItem.Label)')
            if tlabel and tlabel == label:
                trailer = _info('Window(Home).Property(TMDbHelper.ListItem.Trailer)')
        return {'key': key, 'imdb': imdb_id, 'tmdb': tmdb_id, 'dbtype': dbtype, 'label': label,
                'trailer': trailer}

    # -------------------------------------------------------------- lookup
    def _lookup(self, item, quality, source='imdb'):
        if source != getattr(self, 'source', None):
            self.source = source
            self.lookups.clear()
        key = item['key']
        job = self.lookups.get(key)
        if job is not None:
            return job
        if len(self.lookups) > 30:
            self.lookups = {k: v for k, v in self.lookups.items() if not v['event'].is_set()}
        job = {'event': threading.Event(), 'stream': None}
        self.lookups[key] = job
        resolver = self._resolver(quality)

        def work():
            try:
                # 3.2.43~beta1 TEST: YouTube trailer through NewPipe first
                if source == 'newpipe':
                    if newpipe.installed():
                        vid = newpipe.youtube_id(item.get('trailer'))
                        how = 'trailer link'
                        if not vid:
                            vid = newpipe.tmdb_youtube_id(_tmdb_key(), item['tmdb'],
                                                          item['dbtype'], item['imdb'], log=_log)
                            how = 'TMDb'
                        if vid:
                            job['stream'] = {'url': newpipe.plugin_url(vid, item['label']),
                                             'source': 'newpipe', 'height': 'YouTube'}
                            _log('lookup "%s" (%s): NewPipe trailer %s (from %s)'
                                 % (item['label'], item['key'], vid, how))
                            return
                        _log('lookup "%s" (%s): no YouTube trailer - trying IMDb'
                             % (item['label'], item['key']))
                    else:
                        _diag('newpipe-missing', 'trailer source is NewPipe but '
                              'plugin.video.newpipe is not installed/enabled - using IMDb')
                imdb_id = item['imdb'] or _imdb_for_tmdb(item['tmdb'], item['dbtype'])
                if imdb_id:
                    job['stream'] = resolver.resolve(imdb_id, timeout=8.0)
                _log('lookup "%s" (%s): %s' % (item['label'], imdb_id or item['key'],
                     ('trailer found (%sp)' % (job['stream'].get('height') or '?'))
                     if job['stream'] else
                     ('no trailer' if imdb_id else 'no IMDb id')))
            except Exception:
                _log('lookup failed:\n%s' % traceback.format_exc(), xbmc.LOGWARNING)
            finally:
                job['event'].set()

        # not a daemon (Python 3.14 teardown); a lookup ends within its timeouts
        thread = threading.Thread(target=work, name='AbukarimTools-trailer-lookup')
        thread.start()
        return job

    # ---------------------------------------------------------------- audio
    def _silence(self):
        if self.mute_owned:
            return
        volume, muted = _audio_state()
        if volume and not muted:
            self.saved_volume = volume
            try:
                os.makedirs(config.PROFILE, exist_ok=True)
                with open(MARKER, 'w') as handle:
                    handle.write(str(volume))
            except Exception:
                pass
            _set_volume(0)
            self.mute_owned = True

    def _restore_volume(self):
        if not self.mute_owned:
            return
        self.mute_owned = False
        volume, _muted = _audio_state()
        # the user may have turned the volume up meanwhile; keep theirs
        if volume == 0 and self.saved_volume:
            _set_volume(self.saved_volume)
        try:
            os.remove(MARKER)
        except Exception:
            pass

    # ------------------------------------------------------------- control
    def _start(self, item, stream, cfg):
        url = stream.get('url')
        if not url:
            return False
        self.fs_mode = bool(cfg.get('fullscreen', True))
        self.fs_asked = 0.0
        self.fs_seen = False
        if not cfg.get('sound') and not self.fs_mode:
            self._silence()
        li = xbmcgui.ListItem(label=item['label'] or 'Trailer', path=url)
        self.via_plugin = url.startswith('plugin://')
        if self.via_plugin:
            # NewPipe resolves it (setResolvedUrl); the playing file becomes the
            # resolved stream, which _ours() adopts on first sight
            li.setProperty('IsPlayable', 'true')
        else:
            try:
                li.setMimeType(stream.get('mime') or 'video/mp4')
                li.setContentLookup(False)
            except Exception:
                pass
        try:
            tag = li.getVideoInfoTag()
            tag.setTitle(item['label'] or 'Trailer')
            tag.setMediaType('video')
        except Exception:
            pass
        li.setProperty(PROP, '1')
        self.home.setProperty(PROP, '1')
        self.url = url
        self.key = item['key']
        self._label = item['label'] or 'Trailer'
        self.state = 'starting'
        self.started = time.monotonic()
        try:
            self.player.play(url, li, windowed=True)
        except Exception as exc:
            _log('play failed: %s' % type(exc).__name__, xbmc.LOGWARNING)
            self._release()
            return False
        _log('trailer start: %s (%s) - %s, %sp' % (item['label'], item['key'],
             'full screen' if self.fs_mode else 'behind the page', stream.get('height') or '?'))
        return True

    def _go_fullscreen(self):
        """Our trailer is rendering: switch to the full-screen video window."""
        if self.fs_asked or _cond(_FULLSCREEN):
            return
        if _cond(_OPEN_BLOCKERS):
            return              # a dialog opened meanwhile; try on the next tick
        self.fs_asked = time.monotonic()
        xbmc.executebuiltin('ActivateWindow(fullscreenvideo)')
        _log('trailer -> full screen: %s' % self.key)

    def _release(self):
        """Forget the trailer without touching the player."""
        self.state = 'idle'
        self.released_at = time.monotonic()
        self.url = ''
        self.key = ''
        self.via_plugin = False
        self.fs_mode = False
        self.fs_asked = 0.0
        self.fs_seen = False
        try:
            self.home.clearProperty(PROP)
        except Exception:
            pass
        self._restore_volume()

    def _stop(self):
        """Stop our trailer (never anything else) and wait until Kodi has closed it."""
        try:
            deadline = time.monotonic() + 2.0
            # a play request may still be queued in Kodi; let it open first
            while (self.state == 'starting' and not self.player.isPlaying()
                   and time.monotonic() < deadline and not self.monitor.abortRequested()):
                time.sleep(0.05)
            current = self._playing_file()
            if not current and getattr(self, 'via_plugin', False):
                # NewPipe may still be resolving: if its stream opens later,
                # tick() stops it (matched by title + YouTube/local proxy URL)
                self.orphan = (self._label, time.monotonic() + START_TIMEOUT_NEWPIPE)
            if current and self._ours(current):
                self.player.stop()
                deadline = time.monotonic() + 3.0
                while self.player.isPlaying() and time.monotonic() < deadline:
                    time.sleep(0.05)
        except Exception:
            pass
        self._release()

    # ---------------------------------------------------------------- tick
    def tick(self):
        # keep the single-copy marker up (a skin reload could clear it, and
        # the Home launcher would then start a second engine)
        if not self.home.getProperty(ENGINE_PROP):
            self.home.setProperty(ENGINE_PROP, self.origin)
        cfg = config.load_cached()
        now = time.monotonic()
        self._kill_orphan(now)
        # 3.2.36: log every settings change (the show mode too)
        snapshot = tuple(sorted(cfg.items()))
        if snapshot != self._was_enabled:
            self._was_enabled = snapshot
            _log('auto trailers %s (source=%s, show=%s, sound=%s, delay=%ss, quality=%sp, skin=%s)'
                 % ('ON' if cfg.get('enabled') else 'off', cfg.get('source', 'imdb'),
                    'full screen' if cfg.get('fullscreen', True) else 'behind the page',
                    cfg.get('sound'), cfg.get('delay'), cfg.get('quality'), xbmc.getSkinDir()))
        if not cfg.get('enabled'):
            if self.state != 'idle':
                self._stop()
            self.cand_key = ''
            return False

        if self.state != 'idle' and self.fs_mode:
            handled = self._tick_fullscreen(now)
            if handled is not None:
                return handled

        eligible = self._eligible(cfg.get('fullscreen', True))
        item = self._focused() if eligible else None
        key = item['key'] if item else ''

        if self.state != 'idle':
            current = self._playing_file()
            if current and not self._ours(current):
                # real playback took over the player: let go, never stop it
                _log('real playback replaced the trailer')
                self._release()
                return True
            if current and not self.fs_mode and _cond(_FULLSCREEN):
                # the user took the trailer full screen: it is theirs now
                _log('trailer taken full screen - handed over')
                self.done_key = self.key
                self._release()
                return True
            if key and key != self.key:
                # another title is focused: this trailer is done
                self.miss_since = None
                self._stop()
            elif not key:
                # 3.1.20: no title readable right now. While Kodi opens the
                # stream its busy dialog is modal, so ListItem.* reads the dialog
                # (empty) - the 3.1.19 log shows every trailer stopped ~0.2 s
                # after VideoPlayer::OpenFile because of that. Only a page that
                # stays without our title for a while stops the trailer.
                if self.miss_since is None:
                    self.miss_since = now
                elif now - self.miss_since > MISS_GRACE and not _cond(_BUSY + ' | System.HasActiveModalDialog'):
                    self.miss_since = None
                    self._stop()
                elif now - self.miss_since > MISS_GRACE_MAX:
                    self.miss_since = None
                    self._stop()
            elif self.state == 'starting':
                self.miss_since = None
                if current:
                    try:
                        played = self.player.getTime()
                    except Exception:
                        played = 0.0
                    if self.fs_mode and played > FS_FIRST_FRAME:
                        self._go_fullscreen()
                    if played > 0.3:
                        self.state = 'playing'
                elif now - self.started > (START_TIMEOUT_NEWPIPE if getattr(self, 'via_plugin', False)
                                           else START_TIMEOUT):
                    _log('trailer did not open in time: %s' % self.key)
                    try:
                        self.resolver.forget_url(self.url)
                    except Exception:
                        pass
                    self.done_key = self.key
                    self._stop()
            elif not current:
                self.miss_since = None
                # ended by itself (or stopped elsewhere): not again for this title
                self.done_key = self.key
                self._release()
            if self.state != 'idle':
                return True

        # ---- idle: first make sure nothing else has been playing/resolving
        if self._recent_activity(now):
            if item:
                if key != self.cand_key:   # the delay runs during the cooldown
                    self.cand_key = key
                    self.cand_since = now
                    self.done_key = ''
            else:
                self.cand_key = ''
            return eligible

        # ---- idle: find a title to preview
        if not item:
            self.cand_key = ''
            return eligible
        if key != self.cand_key:
            self._focus_logs += 1
            if self._focus_logs <= 500:
                _log('focus: "%s" (%s, %s)' % (item['label'], item['dbtype'], key))
            self.cand_key = key
            self.cand_since = now
            self.done_key = ''
        if key == self.done_key:
            return True
        waited = now - self.cand_since
        if waited >= PREFETCH_AFTER:
            job = self._lookup(item, cfg.get('quality', 720), cfg.get('source', 'imdb'))
        else:
            return True
        if waited < float(cfg.get('delay', 3)):
            return True
        if not job['event'].is_set():
            return True
        stream = job['stream']
        if not stream:
            self.done_key = key          # no trailer for this title
            return True
        if _cond('Player.HasMedia') or _cond(_OPEN_BLOCKERS):
            return True                  # something else plays, or a dialog is open
        if not self._playlist_clean():
            return True                  # cleared a leftover playlist; start next tick
        if not self._start(item, stream, cfg):
            self.done_key = key
        return True

    def _recent_activity(self, now):
        """True while another add-on's playback (or its source picker /
        resolve) is happening or happened less than COOLDOWN ago."""
        own = now - self.released_at < OWN_TEARDOWN
        if not own and _cond(_ACTIVITY):
            if now >= self.quiet_until and not self._quiet_logged:
                _log('playback activity - trailers paused %ds' % COOLDOWN_AFTER_PLAYBACK)
                self._quiet_logged = True
            self.quiet_until = now + COOLDOWN_AFTER_PLAYBACK
            return True
        if now < self.quiet_until:
            return True
        self._quiet_logged = False
        return False

    def _playlist_clean(self):
        """A failed resolve can leave items in Kodi's video playlist. Clear it
        through JSON-RPC (handled on Kodi's main thread, in order with the
        playlist player) and start on a later tick."""
        try:
            length = int(_info('Playlist.Length(video)') or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return True
        _rpc('Playlist.Clear', {'playlistid': 1})
        _log('cleared %d leftover item(s) from the video playlist before a trailer' % length)
        self.quiet_until = time.monotonic() + 2.0
        return False

    def _tick_fullscreen(self, now):
        """Full-screen trailer bookkeeping. None = let the normal tick decide."""
        current = self._playing_file()
        if not current:
            if self.fs_seen:
                # ended by itself (or Stop): Kodi closes full screen on its own
                _log('full-screen trailer ended: %s' % self.key)
                self.done_key = self.key
                self._release()
                return True
            return None
        if not self._ours(current):
            _log('real playback replaced the trailer')
            self._release()
            return True
        if _cond(_FULLSCREEN):
            self.fs_seen = True
            self.state = 'playing'
            self.miss_since = None
            return True             # ListItem.* is empty here - never stop for that
        if self.fs_seen:
            # the user left full screen (Back): the trailer ends with it
            _log('left full screen - trailer stopped: %s' % self.key)
            key = self.key
            self._stop()
            self.done_key = key
            return True
        if self.fs_asked and now - self.fs_asked > FS_TIMEOUT:
            _log('full screen did not open - trailer stays behind the page')
            self.fs_mode = False
            self._release_fs_only()
            return None
        if self.fs_asked:
            return True             # switching right now: the page is unreadable
        try:
            played = self.player.getTime()
        except Exception:
            played = 0.0
        if played > FS_FIRST_FRAME:
            # the cursor moved on, or the page was left, while it opened:
            # the normal checks stop it instead
            if not self._eligible(True):
                return None
            focused = self._focused()
            if focused and focused['key'] != self.key:
                return None
            # frames are on screen: go full screen now, even while the busy
            # spinner still hides the focused title
            self._go_fullscreen()
            if self.fs_asked:
                self.state = 'playing'
                return True
        return None                 # still opening windowed: the normal checks apply

    def _kill_orphan(self, now):
        """Stop a NewPipe trailer that opened after we had given up on it."""
        orphan = getattr(self, 'orphan', None)
        if not orphan:
            return
        label, deadline = orphan
        if now > deadline:
            self.orphan = None
            return
        if self.state != 'idle':
            return
        current = self._playing_file()
        if not current:
            return
        self.orphan = None
        low = current.lower()
        late = (('127.0.0.1' in low or 'localhost' in low or 'googlevideo' in low)
                and _info('VideoPlayer.Title') == label)
        if late:
            _log('late NewPipe trailer stopped: %s' % label)
            try:
                self.player.stop()
            except Exception:
                pass

    def _release_fs_only(self):
        self.fs_asked = 0.0
        self.fs_seen = False

    # ----------------------------------------------------------------- run
    def run(self):
        restore_after_crash()
        _log('engine running')
        try:
            while not self.monitor.abortRequested():
                busy = False
                try:
                    busy = self.tick()
                except Exception:
                    if time.monotonic() - self._last_error > 60:
                        self._last_error = time.monotonic()
                        _log('tick failed:\n%s' % traceback.format_exc(), xbmc.LOGWARNING)
                # 0.1 s while a trailer opens: it goes full screen right after
                # its first frames
                wait = 0.1 if self.state == 'starting' else (0.2 if busy else 1.0)
                if self.monitor.waitForAbort(wait):
                    break
        finally:
            # Kodi is closing: it stops the player itself; only give the volume back
            try:
                self.home.clearProperty(PROP)
            except Exception:
                pass
            self._restore_volume()
            if self.resolver is not None:
                self.resolver.flush()
            _log('engine stopped')


def run_here(monitor, origin):
    """Run the engine in the calling thread (the trailers.py launcher)."""
    home = xbmcgui.Window(HOME_ID)
    if home.getProperty(ENGINE_PROP):
        return False
    # a running engine re-marks itself within a second; give it that chance
    if monitor.waitForAbort(1.5) or home.getProperty(ENGINE_PROP):
        return False
    home.setProperty(ENGINE_PROP, origin)
    _log('engine started by %s' % origin)
    try:
        Engine(monitor, origin).run()
    except Exception:
        _log('engine crashed:\n%s' % traceback.format_exc(), xbmc.LOGERROR)
    finally:
        try:
            home.clearProperty(ENGINE_PROP)
        except Exception:
            pass
    return True


def start(monitor):
    """Start the engine thread once per Kodi session. Returns the thread or None."""
    home = xbmcgui.Window(HOME_ID)
    if home.getProperty(ENGINE_PROP):
        return None
    home.setProperty(ENGINE_PROP, 'service')
    _log('engine started by service')

    def body():
        try:
            Engine(monitor).run()
        except Exception:
            _log('engine crashed:\n%s' % traceback.format_exc(), xbmc.LOGERROR)
        finally:
            try:
                home.clearProperty(ENGINE_PROP)
            except Exception:
                pass

    # not a daemon: it ends by itself when Kodi asks to abort, and Kodi 22 /
    # Python 3.14 dislikes daemon threads still running at interpreter teardown
    thread = threading.Thread(target=body, name='AbukarimTools-trailers')
    thread.start()
    return thread
