# -*- coding: utf-8 -*-
"""
trakt_hubs.py - "My Lists" (قوائمي; "Trakt Lists" before 3.3.5): which Trakt
lists the Arctic Fuse 3 Movies / TV Shows / Korean hubs carry, and (3.3.6)
which Otaku anime lists the HOME page carries. Shown in the Installation
Wizard right after Widgets Layout, and from Setup & Install in the menu.

All its texts are ARABIC (Modern Standard Arabic) on purpose, like
af3_shortcuts: the window uses the add-on's Arabic-capable fonts and Kodi's
dialogs fall back to the Arabic arial.ttf the add-on installs.

    Original  the hubs stay exactly as the build ships them
    Custom    (card "Trakt") the user's Trakt likes + the best Trakt lists
    Anime     (3.3.6, replaces the 3.3.5 Simkl card) Otaku lists the user
              ticks become widget rows on the HOME page (homewidgets) - see
              ANIME_ENTRIES. Independent of the hub choice: the Movies / TV
              / Korean hubs are not touched by it, and Original / Trakt do
              not touch the anime rows.

What Custom touches (and nothing else) - since 3.2.63 the picks are WIDGET
rows, appended to the hub widgets files in the hub's own widget style:

    1101widgets (Movies)   picked movie lists (liked first)
    1102widgets (TV)       picked TV lists
    1103widgets (Korean)   picked Korean movie + series lists

The hub sub-menus (1101/1102/1103submenu) are not changed any more; what
3.2.57-3.2.62 added there (two groups, Korean sub-menu entries, hidden build
lists) is removed / restored automatically. The build's own Korean lists
stay in the Korean sub-menu and are not offered in the picker.

Never touched: the Home page (homesubmenu / homewidgets) and the ABUKARIM
lists on Trakt (user taiseer999) - they are not even offered in the picker.

Everything this module adds carries a guid starting with "guid-abkt";
everything it hides carries "abk_trakt": "off". Original removes / restores
exactly those, so it is a clean undo. Every field written is a plain str
(skinvariables passes every item field to ListItem.setProperties - see the
3.2.3 note in menu_reconcile).

The picks are saved in addon_data/plugin.program.abukarimtools/
trakt_hubs.json. At boot, ensure() re-applies them - WITHOUT network - but
only to a hub file that carries none of our markers any more (it was
replaced wholesale: a restore, Widgets Layout, a skin profile or the
wizard's Patch GUI). A hub the user edited by hand is left alone.

Trakt access goes through TMDb Helper: its public client id and, for the
likes, the token it stores in its own 'trakt_token' setting (linking runs
TMDb Helper's own authorize - the QR that the patcher injects). This module
never writes TMDb Helper's token.
"""

import hashlib
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib.strings_map import STRINGS


def AR(sid):
    """Arabic text of a string id, whatever Kodi's UI language is."""
    pair = STRINGS.get(int(sid)) or ('', '')
    return pair[1] or pair[0]


ORIGINAL, CUSTOM, ANIME = 'original', 'custom', 'anime'
MODES = (ORIGINAL, CUSTOM, ANIME)      # order = cards in the window
LIST_MODES = (CUSTOM,)                   # hub modes that write widget rows

TMDBH = 'plugin.video.themoviedb.helper'
AF3_ID = 'skin.arctic.fuse.3'
# TMDb Helper's own public client id (resources/tmdbhelper/lib/api/api_keys/
# trakt.py). Read from the installed copy first, so a rotated id keeps
# matching the token TMDb Helper stored.
DEFAULT_CLIENT_ID = 'e6fde6173adf3c6af8fd1b0694b9b84d7c519cefc24482310e1de06c6abe5467'
API = 'https://api.trakt.tv/'
UA = 'ABUKARIM-TOOLS/trakt-hubs (Kodi)'

FIXED_USERS = {'taiseer999'}          # ABUKARIM lists - always kept, never offered

ADDON_DATA = xbmcvfs.translatePath('special://profile/addon_data/')
NODES = os.path.join(ADDON_DATA, 'script.skinvariables', 'nodes', AF3_ID)
PROFILE = os.path.join(ADDON_DATA, 'plugin.program.abukarimtools')
STATE_FILE = os.path.join(PROFILE, 'trakt_hubs.json')

HUB_MOVIES = 'skinvariables-shortcut-1101submenu.json'
HUB_TV = 'skinvariables-shortcut-1102submenu.json'
HUB_KOREAN = 'skinvariables-shortcut-1103submenu.json'
W_MOVIES = 'skinvariables-shortcut-1101widgets.json'
W_TV = 'skinvariables-shortcut-1102widgets.json'
W_KOREAN = 'skinvariables-shortcut-1103widgets.json'
# 3.2.66: style of OUR rows by content - movies "Flyer" (منشور), series
# "Landscape" (صورة افقية); AF3 widgets_include_row.xml names
STYLE_BY_CAT = {'movies': 'Flyer', 'kr_movies': 'Flyer',
                'tv': 'Landscape', 'kr_tv': 'Landscape'}
STYLE_VERSION = 3              # 3: 3.2.67 drops the live liked-lists row
LIKED_FOLDER = 'likedfolder'   # picker entry: TMDb Helper's live liked-lists folder
KEEP, ADD, REPLACE = 'keep', 'add', 'replace'    # existing hub widgets
WIDGET_SUFFIX = ('&widget=true&reload=$INFO[Window(Home).Property('
                 'TMDbHelper.Widgets.Reload)]')

# picker categories: key, heading string id
CATS = (('movies', 30673), ('tv', 30674), ('kr_movies', 30675), ('kr_tv', 30676))
BEST_PER_CAT = 25

GUID_PREFIX = 'guid-abkt'
OFF_TAG = 'abk_trakt'
ICON_LIST = 'special://skin/extras/icons/playlist.png'
ICON_KOREAN = 'special://skin/extras/icons/kdramaw.png'

_KR_WORDS = re.compile(r'korea|\bk[- ]?dramas?\b|\bk[- ]?movies?\b|hallyu|한국|كوري', re.I)
_SESSION = {'applied': False}
_LAST = {'r429': 0, 'likes_limited': False, 'unauthorized': False,
         'mdb_nokey': False}
NOLINK = 'nolink'              # _custom(): Trakt not linked -> Original            # 429s of the last fetch (for the message)


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools TraktHubs] %s' % msg, level)


# ---------------------------------------------------------------------------
# state
# ---------------------------------------------------------------------------

def _load_state():
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            st = json.load(f)
        return st if isinstance(st, dict) else {}
    except Exception:
        return {}


def _save_state(st):
    # 3.3.6: the hub flows write a fresh dict - keep the anime picks (home
    # page) unless this save sets them itself.
    if 'anime' not in st:
        old = _load_state().get('anime')
        if isinstance(old, list):
            st = dict(st, anime=old)
    try:
        os.makedirs(PROFILE, exist_ok=True)
        tmp = STATE_FILE + '.part'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(st, f, ensure_ascii=False, indent=1)
        os.replace(tmp, STATE_FILE)
    except Exception as e:
        _log('state not saved: %s' % e, xbmc.LOGWARNING)


def current_mode():
    st = _load_state()
    return st.get('mode') if st.get('mode') in MODES else None


# ---------------------------------------------------------------------------
# Trakt access (through TMDb Helper's client id / token)
# ---------------------------------------------------------------------------

def _tmdbh_installed():
    return os.path.isfile(os.path.join(
        xbmcvfs.translatePath('special://home/addons/'), TMDBH, 'addon.xml'))


def _client_id():
    p = os.path.join(xbmcvfs.translatePath('special://home/addons/'), TMDBH,
                     'resources', 'tmdbhelper', 'lib', 'api', 'api_keys', 'trakt.py')
    try:
        with open(p, 'r', encoding='utf-8') as f:
            m = re.search(r"CLIENT_ID\s*=\s*'([0-9a-f]{64})'", f.read())
        if m:
            return m.group(1)
    except Exception:
        pass
    return DEFAULT_CLIENT_ID


def _token_info():
    """(access_token, state) from TMDb Helper.

    3.2.58: its session copy (Home window property TMDbHelper.TraktUserToken)
    is read first, then the 'trakt_token' setting. Only the token's own
    expiry decides - TMDb Helper's "[session token expired]" in kodi.log just
    means its startup check got HTTP 429 from Trakt, the token itself is fine
    (log 2026-10-12 06:20).
    """
    sources = []
    try:
        sources.append(('window', xbmcgui.Window(10000).getProperty('TMDbHelper.TraktUserToken')))
    except Exception:
        pass
    try:
        sources.append(('setting', xbmcaddon.Addon(TMDBH).getSetting('trakt_token')))
    except Exception as e:
        _log('TMDb Helper setting not readable: %s' % e, xbmc.LOGWARNING)
    state = 'missing'
    for where, raw in sources:
        try:
            tok = json.loads(raw) if raw else {}
        except Exception:
            tok = {}
        at = tok.get('access_token') if isinstance(tok, dict) else ''
        if not at:
            continue
        try:
            exp = int(tok.get('created_at') or 0) + int(tok.get('expires_in') or 0)
        except Exception:
            exp = 0
        if exp and exp < time.time() + 60:
            state = 'expired (%s)' % where
            continue
        return at, 'valid (%s)' % where
    return '', state


def _token():
    return _token_info()[0]


class _RateLimited(Exception):
    pass


class _Trakt(object):
    """Small Trakt client. It shares TMDb Helper's client id, so it is kept
    gentle: few calls, 2 at a time, and one shared back-off - a 429 longer
    than MAX_WAIT stops the run instead of hammering (TMDb Helper's own
    widgets use the same id)."""

    MAX_WAIT = 20

    def __init__(self, token=''):
        self.cid = _client_id()
        self.token = token
        self.lock = threading.Lock()
        self.calls = 0
        self.r429 = 0
        self.until = 0.0
        self.stopped = False
        self.in_a_row = 0          # consecutive 429s

    def _pause(self):
        while True:
            with self.lock:
                if self.stopped:
                    raise _RateLimited()
                wait = self.until - time.time()
            if wait <= 0:
                return
            time.sleep(min(wait, 1))

    def get(self, path, params=None, auth=False, tries=3):
        url = API + path
        if params:
            url += '?' + urllib.parse.urlencode(params)
        hdr = {'trakt-api-version': '2', 'trakt-api-key': self.cid,
               'Content-Type': 'application/json', 'User-Agent': UA}
        if auth and self.token:
            hdr['Authorization'] = 'Bearer %s' % self.token
        for attempt in range(tries):
            self._pause()
            with self.lock:
                self.calls += 1
            try:
                req = urllib.request.Request(url, headers=hdr)
                with urllib.request.urlopen(req, timeout=20) as r:
                    data = json.loads(r.read().decode('utf-8') or 'null')
                with self.lock:
                    self.in_a_row = 0
                return data
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    # 3.2.59: Trakt's Cloudflare answers a blocked address with
                    # an HTML "Access denied" page and no Retry-After (log
                    # 2026-10-12 06:28) - retrying only digs the hole deeper.
                    try:
                        body = e.read(2048).decode('utf-8', 'replace').lower()
                    except Exception:
                        body = ''
                    blocked = 'cloudflare' in body or 'access denied' in body
                    try:
                        wait = float(e.headers.get('Retry-After') or 2)
                    except Exception:
                        wait = 2
                    with self.lock:
                        self.r429 += 1
                        self.in_a_row += 1
                        stop = blocked or wait > self.MAX_WAIT or self.in_a_row >= 3
                        if stop:
                            self.stopped = True
                        self.until = max(self.until, time.time() + wait)
                    _log('HTTP 429 on %s (Retry-After %ss%s)'
                         % (path, wait, ', Cloudflare block' if blocked else ''),
                         xbmc.LOGWARNING)
                    if stop:
                        raise _RateLimited()
                    continue
                if e.code in (401, 403) and auth:
                    raise
                _log('GET %s -> HTTP %s' % (path, e.code), xbmc.LOGWARNING)
                return None
            except _RateLimited:
                raise
            except Exception as e:
                if attempt + 1 < tries:
                    time.sleep(1)
                    continue
                _log('GET %s failed: %s' % (path, e), xbmc.LOGWARNING)
                return None
        return None


def _norm(raw, source, liked=False):
    """Trakt list object -> candidate dict, or None when unusable."""
    lst = raw.get('list') if isinstance(raw, dict) and 'list' in raw else raw
    if not isinstance(lst, dict):
        return None
    ids = lst.get('ids') or {}
    slug = ids.get('slug') or ''
    if lst.get('type') == 'official':
        user, uname = 'official', 'Trakt'
    else:
        u = lst.get('user') or {}
        user = (u.get('ids') or {}).get('slug') or u.get('username') or ''
        uname = u.get('name') or u.get('username') or user
    if not slug or not user or user.lower() in FIXED_USERS:
        return None
    if user != 'official' and (lst.get('privacy') or 'public') != 'public':
        return None
    try:
        count = int(lst.get('item_count') or 0)
    except Exception:
        count = 0
    try:
        likes = int(lst.get('likes') or raw.get('like_count') or 0)
    except Exception:
        likes = 0
    return {
        'name': _clean(lst.get('name') or slug) or slug,
        'user': user, 'uname': uname, 'slug': slug,
        'likes': likes, 'count': count, 'liked': bool(liked),
        'desc': (lst.get('description') or '')[:300],
        'src': source,
    }


# 3.2.62: script.skinvariables escapes only "&" when it builds the AF3 menus;
# a Trakt list name with " < > (or a control character) broke the whole build
# (log 2026-10-12 07:31:57: ExpatError not well-formed, line 5248) and AF3
# kept its old menus. Names are made XML/format-safe before they are written.
_UNSAFE = {'"': '”', "'": '’', '<': '‹', '>': '›',
           '{': '(', '}': ')', '$': '＄', '\\': '/'}
_CTRL = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ufffe\uffff]')


def _clean(text):
    text = _CTRL.sub('', str(text or ''))
    for a, b in _UNSAFE.items():
        text = text.replace(a, b)
    return re.sub(r'\s+', ' ', text).strip()


def _is_unsafe(text):
    return _clean(text) != str(text or '').strip() or bool(_CTRL.search(str(text or '')))


def _key(c):
    if c.get('prov') == 'mdblist':
        return 'mdb/%s' % c.get('mid')
    return '%s/%s' % (c['user'], c['slug'])


_MOVIE_WORDS = re.compile(r'\b(movies?|films?|cinema|filmography|oscars?|box ?office)\b|أفلام|افلام|فيلم', re.I)
_TV_WORDS = re.compile(r'\b(tv|shows?|series|sitcoms?|seasons?|miniseries|k-?dramas?|dramas)\b|مسلسل', re.I)


def _guess(c):
    """Category from the list name alone when it is unambiguous, else None.
    Saves one Trakt call per list."""
    text = c['name'] + ' ' + c['slug'].replace('-', ' ')
    m, t = bool(_MOVIE_WORDS.search(text)), bool(_TV_WORDS.search(text))
    if m == t:
        return None
    kind = 'movies' if m else 'tv'
    return ('kr_' + kind) if _KR_WORDS.search(text) else kind


def _classify(trakt, c):
    """Look at the first items: movie vs show majority, Korean by country."""
    if c['user'] == 'official':
        path = 'lists/%s/items' % c['slug']
    else:
        path = 'users/%s/lists/%s/items' % (urllib.parse.quote(c['user']),
                                            urllib.parse.quote(c['slug']))
    items = trakt.get(path, {'limit': 15, 'page': 1, 'extended': 'full'}) or []
    movies = shows = kr = 0
    for it in items if isinstance(items, list) else []:
        t = it.get('type')
        if t in ('season', 'episode'):
            t = 'show'
        media = it.get('movie') or it.get('show') or {}
        if t == 'movie':
            movies += 1
        elif t == 'show':
            shows += 1
        else:
            continue
        if (media.get('country') or '').lower() == 'kr' or \
                (media.get('language') or '').lower() == 'ko':
            kr += 1
    total = movies + shows
    if not total:
        return None
    korean = kr * 2 >= total or (kr * 10 >= total * 3 and
                                 _KR_WORDS.search(c['name'] + ' ' + c['desc']))
    kind = 'movies' if movies >= shows else 'tv'
    return ('kr_' + kind) if korean else kind


MDBLIST_API = 'https://api.mdblist.com/'


def _mdblist_key():
    try:
        return (xbmcaddon.Addon(TMDBH).getSetting('mdblist_apikey') or '').strip()
    except Exception:
        return ''


def _mdb_get(path, key, **params):
    params['apikey'] = key
    url = MDBLIST_API + path + '?' + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode('utf-8') or 'null')
    except urllib.error.HTTPError as e:
        _log('MDBList %s -> HTTP %s' % (path, e.code), xbmc.LOGWARNING)
        return []
    except Exception as e:
        _log('MDBList %s failed: %s' % (path, e), xbmc.LOGWARNING)
        return []
    if isinstance(data, dict):                    # some endpoints wrap the list
        for k in ('lists', 'results', 'items'):
            if isinstance(data.get(k), list):
                return data[k]
        return []
    return data if isinstance(data, list) else []


def _mdb_norm(raw, src, mine=False):
    if not isinstance(raw, dict) or not raw.get('id'):
        return None
    if raw.get('private') in (True, 'true', 1) and not mine:
        return None
    name = _clean(raw.get('name') or raw.get('slug') or '')
    if not name:
        return None
    def _int(*ks):
        for k in ks:
            try:
                if raw.get(k) is not None:
                    return int(raw.get(k))
            except Exception:
                pass
        return 0
    return {'name': name, 'prov': 'mdblist', 'mid': str(raw['id']),
            'user': str(raw.get('user_name') or 'mdblist'),
            'uname': str(raw.get('user_name') or 'MDBList'),
            'slug': str(raw.get('slug') or raw['id']),
            'likes': _int('likes'), 'count': _int('items', 'item_count'),
            'liked': False, 'mine': bool(mine), 'src': src,
            'desc': (raw.get('description') or '')[:300],
            'mediatype': str(raw.get('mediatype') or raw.get('type') or '').lower()}


def fetch_mdblist():
    """MDBList lists through TMDb Helper's own API key: top lists, the
    user's own lists and a Korean search. {cat: [candidate]} - empty when
    TMDb Helper has no MDBList key."""
    key = _mdblist_key()
    cats = {k: [] for k, _ in CATS}
    _LAST['mdb_nokey'] = not key
    if not key:
        _log('MDBList: no API key in TMDb Helper - skipped')
        return cats, False
    found = {}
    for path, params, src, mine in (('lists/user', {}, 'mdb_mine', True),
                                     ('lists/top', {'limit': 50}, 'mdb_top', False),
                                     ('lists/search', {'query': 'korean'}, 'mdb_top', False)):
        for raw in _mdb_get(path, key, **params):
            c = _mdb_norm(raw, src, mine)
            if c and (mine or c['count'] >= 5) and _key(c) not in found:
                found[_key(c)] = c
    for c in found.values():
        mt = c.pop('mediatype', '')
        kind = 'movies' if mt == 'movie' else 'tv' if mt in ('show', 'tv') else None
        text = c['name'] + ' ' + c['desc']
        kind = kind or (_guess(c) or 'movies').replace('kr_', '')
        cats[('kr_' + kind) if _KR_WORDS.search(text) else kind].append(c)
    for k in cats:
        cats[k].sort(key=lambda c: (not c.get('mine'), -c['likes']))
        cats[k] = cats[k][:BEST_PER_CAT]
    _log('MDBList: %s' % ', '.join('%s=%d' % (k, len(v)) for k, v in cats.items()))
    return cats, True


CACHE_DAYS = 30
CLASSIFY_BUDGET = 60          # Trakt item calls per run, liked lists first


def _load_cache():
    st = _load_state()
    cache = st.get('class_cache') if isinstance(st.get('class_cache'), dict) else {}
    limit = time.time() - CACHE_DAYS * 86400
    return {k: v for k, v in cache.items()
            if isinstance(v, list) and len(v) == 2 and v[1] > limit}


def fetch(progress=None):
    """{'cats': {cat: [candidate, ...]}, 'liked_ok': bool, 'cache': {...}}
    or None (offline / rate limited before anything came back)."""
    t0 = time.time()
    _LAST['likes_limited'] = False
    _LAST['unauthorized'] = False
    tok, tstate = _token_info()
    _log('fetch: TMDb Helper Trakt token %s' % tstate)
    trakt = _Trakt(tok)
    found = {}
    liked_ok = False

    def add(raws, source, liked=False):
        for raw in raws if isinstance(raws, list) else []:
            c = _norm(raw, source, liked)
            if not c:
                continue
            old = found.get(_key(c))
            if old:
                old['liked'] = old['liked'] or c['liked']
                old['likes'] = max(old['likes'], c['likes'])
            else:
                found[_key(c)] = c

    def step(pct, msg):
        if progress:
            progress.update(pct, msg)
            return not progress.iscanceled()
        return True

    if not step(2, AR(30670)):
        return None
    online = False
    try:
        if tok:
            try:
                for page in (1, 2, 3):
                    r = trakt.get('users/likes/lists', {'limit': 50, 'page': page}, auth=True)
                    add(r, 'liked', liked=True)
                    liked_ok = liked_ok or r is not None
                    if not r or len(r) < 50:
                        break
            except urllib.error.HTTPError as e:
                # 3.2.61: a refused token means "not linked" - Custom needs the
                # link, so stop here and let _custom() ask for it.
                _log('likes refused (HTTP %s) - TMDb Helper needs a new Trakt link'
                     % e.code, xbmc.LOGWARNING)
                _LAST['unauthorized'] = True
                return None
            except _RateLimited:
                # 3.2.60: the limit on the ACCOUNT (log 06:38: Retry-After 524 s
                # on users/likes/lists) is not the limit on public lists -
                # carry on without the likes.
                _LAST['likes_limited'] = True
                _log('likes rate limited on this Trakt account - continuing '
                     'with public lists only', xbmc.LOGWARNING)
                with trakt.lock:
                    trakt.stopped = False
                    trakt.until = 0.0
                    trakt.in_a_row = 0
        online = liked_ok
        for path, params in (('lists/popular', {'limit': 50}),
                             ('lists/trending', {'limit': 25})):
            r = trakt.get(path, params)
            online = online or r is not None
            add(r, 'best')
        if not step(6, AR(30670)):
            return None
        for q in ('korean', 'kdrama', 'korean movies'):
            r = trakt.get('search/list', {'query': q, 'fields': 'name', 'limit': 25})
            online = online or r is not None
            add([raw for raw in (r if isinstance(r, list) else [])
                 if (_norm(raw, 'search') or {}).get('count', 0) >= 8
                 and (_norm(raw, 'search') or {}).get('likes', 0) >= 2], 'best')
    except _RateLimited:
        _log('Trakt rate limit while listing - continuing with what came back',
             xbmc.LOGWARNING)
    _LAST['r429'] = trakt.r429
    _log('fetch: liked=%s, %d lists found, %d calls, %d x 429'
         % (liked_ok, len(found), trakt.calls, trakt.r429))
    if not online or not found:
        return None

    todo = [c for c in found.values() if c['liked'] or c['count'] >= 5]
    cache = _load_cache()
    now = int(time.time())
    cats = {k: [] for k, _ in CATS}
    need = []
    for c in todo:
        hit = cache.get(_key(c))
        # 3.2.63: liked lists are always checked by their items (country
        # decides Korean) - a name alone cannot tell a Korean list apart
        cat = hit[0] if hit else (None if c['liked'] else _guess(c))
        if cat in cats:
            cats[cat].append(c)
        elif hit and hit[0] == '-' and not c['liked']:
            continue                              # known empty / unusable
        else:
            need.append(c)
    # liked first, then the most liked - within the call budget
    need.sort(key=lambda c: (not c['liked'], -c['likes']))
    budget = max(CLASSIFY_BUDGET, sum(1 for c in need if c['liked']))
    skipped = max(0, len(need) - budget)
    need = need[:budget]
    _log('classify: %d by name/cache, %d via Trakt, %d over budget'
         % (len(todo) - len(need) - skipped, len(need), skipped))

    done = 0
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futs = {pool.submit(_classify, trakt, c): c for c in need}
            for fut in as_completed(futs):
                c = futs[fut]
                done += 1
                try:
                    cat = fut.result()
                except _RateLimited:
                    raise
                except Exception:
                    cat = None
                cache[_key(c)] = [cat or '-', now]
                if cat:
                    cats[cat].append(c)
                if progress:
                    progress.update(8 + int(90 * done / max(1, len(need))),
                                    AR(30671) % (done, len(need)))
                    if progress.iscanceled():
                        for f in futs:
                            f.cancel()
                        return None
    except _RateLimited:
        _log('Trakt rate limit while sorting - %d of %d sorted, the rest left out'
             % (done, len(need)), xbmc.LOGWARNING)
    # 3.2.65: every liked list is offered - one Trakt could not sort (rate
    # limit, empty first page, HTTP 400 on official lists) goes by its name,
    # else to Movies, instead of disappearing
    placed = {_key(c) for v in cats.values() for c in v}
    lost = 0
    for c in todo:
        if c['liked'] and _key(c) not in placed:
            cats[_guess(c) or 'movies'].append(c)
            lost += 1
    if lost:
        _log('%d liked list(s) placed by name (Trakt could not sort them)' % lost)
    for k in cats:
        liked = sorted((c for c in cats[k] if c['liked']), key=lambda c: c['name'].lower())
        best = sorted((c for c in cats[k] if not c['liked']), key=lambda c: -c['likes'])
        cats[k] = liked + best[:BEST_PER_CAT]
    _log('fetch done in %.1fs: %s, %d calls, %d x 429'
         % (time.time() - t0, ', '.join('%s=%d' % (k, len(v)) for k, v in cats.items()),
            trakt.calls, trakt.r429))
    try:
        if progress:
            progress.update(99, 'MDBList...')
        mcats, _ok = fetch_mdblist()
        for k, v in mcats.items():
            cats[k] = cats.get(k, []) + v
    except Exception as e:
        _log('MDBList skipped: %s' % e, xbmc.LOGWARNING)
    return {'cats': cats, 'liked_ok': liked_ok, 'cache': cache}


# ---------------------------------------------------------------------------
# node files
# ---------------------------------------------------------------------------

def _hub(name):
    return os.path.join(NODES, name)


def _read(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else None
    except Exception:
        return None


def _write(path, data, before):
    text = json.dumps(data, ensure_ascii=False, indent=4)
    if text == before:
        return False
    tmp = path + '.abk.part'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(text)
    os.replace(tmp, path)
    return True


def _guid(*parts):
    return '%s-%s' % (GUID_PREFIX, hashlib.sha1('/'.join(parts).encode('utf-8')).hexdigest()[:10])


def _ours(item):
    return isinstance(item, dict) and str(item.get('guid') or '').startswith(GUID_PREFIX)


def _path(c, cat='movies'):
    q = urllib.parse.quote
    if c.get('prov') == 'mdblist':
        # TMDb Helper route; it uses its own mdblist_apikey setting
        return ('plugin://%s/?info=mdblist_userlist&list_id=%s&list_name=%s'
                '&plugin_category=%s&tmdb_type=both'
                % (TMDBH, q(str(c['mid']), safe=''), q(c['name'], safe=''),
                   q(c['name'], safe='')))
    return ('plugin://%s/?info=trakt_userlist&list_name=%s&list_slug=%s'
            '&plugin_category=%s&tmdb_type=both&user_slug=%s'
            % (TMDBH, q(c['name'], safe=''), q(c['slug'], safe=''),
               q(c['name'], safe=''), q(c['user'], safe='')))


def _item(c, hub, icon):
    return {'label': _clean(c['name']) or c['slug'], 'path': _path(c), 'icon': icon,
            'target': 'videos', 'guid': _guid(hub, c['user'], c['slug'])}


def _group(label_id, hub, items):
    return {'label': AR(label_id), 'path': 'Custom_Submenu', 'icon': ICON_LIST,
            'target': '', 'guid': _guid(hub, 'group', str(label_id)),
            'submenu': items}


def _params(path):
    try:
        return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(path).query))
    except Exception:
        return {}


def _item_key(item):
    p = _params(str(item.get('path') or ''))
    if p.get('info') != 'trakt_userlist' or not p.get('list_slug'):
        return None
    return '%s/%s' % (p.get('user_slug') or 'me', p['list_slug'])


def _strip(data):
    """Remove what Custom added and un-hide what it hid (in place, also
    returned)."""
    def walk(lst):
        out = []
        for it in lst:
            if _ours(it):
                continue
            if isinstance(it, dict):
                if it.get(OFF_TAG):
                    tag = str(it.pop(OFF_TAG, None))
                    if not it.get('abk_hidden'):          # menu_reconcile's own hide
                        if tag.startswith('off:'):
                            it['disabled'] = tag[4:]
                        else:
                            it.pop('disabled', None)
                if isinstance(it.get('submenu'), list):
                    it['submenu'] = walk(it['submenu'])
            out.append(it)
        return out
    data[:] = walk(data)
    return data


def _korean_groups(data):
    """(movies group, tv group) of hub 1103 - created when missing."""
    mg = tg = None
    for g in data:
        if not isinstance(g, dict) or _ours(g):
            continue
        ic = str(g.get('icon') or '')
        if mg is None and 'moviessort' in ic:
            mg = g
        elif tg is None and 'tvsort' in ic:
            tg = g
    real = [g for g in data if isinstance(g, dict) and not _ours(g)]
    if mg is None and real and real[0] is not tg:
        mg = real[0]
    if tg is None:
        rest = [g for g in real if g is not mg]
        tg = rest[0] if rest else None
    if mg is None:
        mg = {'label': AR(30686), 'path': 'Custom_Submenu',
              'icon': 'special://skin/extras/icons/moviessort.png', 'target': '',
              'guid': _guid('1103', 'group', 'movies'), 'submenu': []}
        data.append(mg)
    if tg is None:
        tg = {'label': AR(30687), 'path': 'Custom_Submenu',
              'icon': 'special://skin/extras/icons/tvsort.png', 'target': '',
              'guid': _guid('1103', 'group', 'tv'), 'submenu': []}
        data.append(tg)
    for g in (mg, tg):
        if not isinstance(g.get('submenu'), list):
            g['submenu'] = []
    return mg, tg


def korean_defaults():
    """{'kr_movies': [...], 'kr_tv': [...]} - the build's own third-party
    Korean lists (ABUKARIM's excluded), as picker candidates."""
    out = {'kr_movies': [], 'kr_tv': []}
    data = _read(_hub(HUB_KOREAN))
    if not data:
        return out
    data = _strip(data)
    mg, tg = _korean_groups(data)
    for cat, g in (('kr_movies', mg), ('kr_tv', tg)):
        for it in g['submenu']:
            if not isinstance(it, dict) or it.get('abk_hidden') or \
                    str(it.get('disabled') or '').lower() == 'true':
                continue
            k = _item_key(it)
            if not k:
                continue
            user, slug = k.split('/', 1)
            if user.lower() in FIXED_USERS:
                continue
            p = _params(it.get('path', ''))
            out[cat].append({'name': it.get('label') or p.get('list_name') or slug,
                             'user': user, 'uname': user, 'slug': slug,
                             'likes': 0, 'count': 0, 'liked': False,
                             'desc': '', 'src': 'build'})
    return out


def _widget(c, hub, style, cat='movies'):
    return {'label': _clean(c['name']) or c['slug'],
            'icon': ICON_KOREAN if hub == '1103' else ICON_LIST,
            'path': _path(c, cat) + WIDGET_SUFFIX,
            'target': 'videos',
            'guid': _guid('w', hub, *_key(c).split('/', 1)),
            'widget_style': style}


def _apply_widgets(data, hub, picks, mode=ADD):
    """picks: [(candidate, category)]."""
    """Hub widgets file: our old rows out, the picks in (liked first).
    mode REPLACE also hides the hub's own widgets (disabled + abk_trakt tag,
    so Original brings them back); ADD keeps them in front."""
    _strip(data)
    if mode == REPLACE and picks:
        for it in data:
            if isinstance(it, dict) and str(it.get('disabled') or '').lower() != 'true':
                # remember an existing (empty) "disabled" so Original restores
                # the file exactly: 'off' = key was absent, 'off:<v>' = was <v>
                it[OFF_TAG] = 'off:%s' % it['disabled'] if 'disabled' in it else 'off'
                it['disabled'] = 'True'
    seen = set()
    for c, cat in sorted(picks, key=lambda p: not p[0].get('liked')):
        if c.get('src') in ('build', LIKED_FOLDER) or _key(c) in seen:
            continue                      # build lists stay in the sub-menu;
                                          # 3.2.65's live folder row is gone
        seen.add(_key(c))
        data.append(_widget(c, hub, STYLE_BY_CAT.get(cat, 'Flyer'), cat))
    return data


def _apply_files(mode, picks, only=None, wmode=ADD):
    """Write the hub files. only = set of file names to touch (None = all).
    3.2.63: the picks are WIDGET rows (hub widgets files); the sub-menu files
    are only cleaned of what 3.2.57-3.2.62 put there. Returns files written."""
    written = []
    jobs = ((HUB_MOVIES, None), (HUB_TV, None), (HUB_KOREAN, None),
            (W_MOVIES, ('1101', ('movies',))),
            (W_TV, ('1102', ('tv',))),
            (W_KOREAN, ('1103', ('kr_movies', 'kr_tv'))))
    for name, widget in jobs:
        if only is not None and name not in only:
            continue
        path = _hub(name)
        if not os.path.isfile(path):
            _log('%s not found - skipped' % name)
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                before = f.read()
            data = json.loads(before)
            if not isinstance(data, list):
                continue
        except Exception as e:
            _log('%s unreadable: %s' % (name, e), xbmc.LOGWARNING)
            continue
        if mode in LIST_MODES and widget:
            hub, cats = widget
            sel = [(c, cat) for cat in cats for c in (picks.get(cat) or [])]
            data = _apply_widgets(data, hub, sel, wmode)
        else:
            data = _strip(data)
        if _write(path, data, before):
            written.append(name)
    return written


def _has_unsafe_label(path):
    """One of OUR items carries a label skinvariables cannot build (3.2.61)."""
    data = _read(path) or []
    stack = list(data)
    while stack:
        it = stack.pop()
        if not isinstance(it, dict):
            continue
        if _ours(it) and _is_unsafe(it.get('label')):
            return True
        if isinstance(it.get('submenu'), list):
            stack.extend(it['submenu'])
    return False


def _has_marker(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            t = f.read()
        return GUID_PREFIX in t or ('"%s"' % OFF_TAG) in t
    except Exception:
        return True


def wait_rebuild(max_s=120):
    """Block until the AF3 rebuild this module started has finished (or
    max_s). The Installation Wizard's next step - the patcher - must not run
    under a script.skinvariables build or its skin reload."""
    if not _SESSION.get('rebuilt'):
        return True
    try:
        from resources.lib import skin_rebuild
    except Exception:
        return True
    mon = xbmc.Monitor()
    started = time.time()
    quiet = 0
    while time.time() - started < max_s:
        reason = skin_rebuild.busy()
        reloading = xbmc.getCondVisibility('Window.IsActive(busydialog) | '
                                           'Window.IsActive(busydialognocancel) | '
                                           'Window.IsActive(progressdialog) | '
                                           'Window.IsActive(extendedprogressdialog)')
        if reason or reloading:
            quiet = 0
        else:
            quiet += 1
            if quiet >= 3:
                _log('AF3 rebuild finished after %ds' % int(time.time() - started))
                _SESSION['rebuilt'] = False
                return True
        if mon.waitForAbort(1):
            return False
    _log('AF3 rebuild still busy after %ds - continuing' % max_s, xbmc.LOGWARNING)
    return False


def _rebuild():
    try:
        from resources.lib import menu_reconcile
        menu_reconcile.run(rebuild=False)
    except Exception as e:
        _log('menu reconcile failed: %s' % e, xbmc.LOGWARNING)
    try:
        from resources.lib import skin_rebuild
        if skin_rebuild.force(AF3_ID):
            _SESSION['rebuilt'] = True
    except Exception as e:
        _log('rebuild failed: %s' % e, xbmc.LOGWARNING)


def ensure(rebuild=True):
    """Boot / end of setup: put saved picks back into a hub or home file
    that lost them wholesale. No network. Returns files written."""
    written = _ensure_hubs() + _ensure_anime()
    if written:
        _log('picks re-applied to %s' % ', '.join(written))
        if rebuild:
            _rebuild()
    return written


def _ensure_hubs():
    st = _load_state()
    if st.get('mode') == 'simkl':
        # 3.3.6: Simkl was removed - its rows pointed at a route that no
        # longer exists. Hubs back to the build's lists, Simkl files gone.
        written = _apply_files(ORIGINAL, {})
        _save_state({'mode': ORIGINAL, 'time': int(time.time()),
                     'class_cache': st.get('class_cache') or {}})
        for name in ('simkl_token.json', 'simkl_token.lock'):
            try:
                os.remove(os.path.join(PROFILE, name))
            except OSError:
                pass
        try:
            import shutil
            shutil.rmtree(os.path.join(PROFILE, 'simkl_cache'), ignore_errors=True)
        except Exception:
            pass
        _log('Simkl (removed in 3.3.6) cleaned up: %s' % (', '.join(written) or 'no hub rows'))
        return written
    if st.get('mode') not in LIST_MODES or not isinstance(st.get('picks'), dict):
        return []
    picks = st['picks']
    for lst in picks.values():
        for c in lst if isinstance(lst, list) else []:
            if isinstance(c, dict) and c.get('name'):
                c['name'] = _clean(c['name']) or c.get('slug') or ''
    need = set()
    for name, cats in ((W_MOVIES, ('movies',)), (W_TV, ('tv',)),
                       (W_KOREAN, ('kr_movies', 'kr_tv'))):
        if not any(c.get('src') != 'build' for cat in cats for c in (picks.get(cat) or [])):
            continue
        p = _hub(name)
        if os.path.isfile(p) and (not _has_marker(p) or _has_unsafe_label(p)):
            need.add(name)
    for name in (HUB_MOVIES, HUB_TV, HUB_KOREAN):
        p = _hub(name)
        if os.path.isfile(p) and _has_marker(p):
            need.add(name)                # 3.2.57-3.2.62 sub-menu entries
    if st.get('style_v') != STYLE_VERSION:
        need |= {n for n in (W_MOVIES, W_TV, W_KOREAN) if os.path.isfile(_hub(n))}
    if not need:
        return []
    written = _apply_files(st['mode'], picks, only=need,
                           wmode=st.get('wmode') or ADD)
    if st.get('style_v') != STYLE_VERSION:
        st['style_v'] = STYLE_VERSION
        _save_state(st)
    return written


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

def _addon_path():
    return xbmcvfs.translatePath(
        xbmcaddon.Addon('plugin.program.abukarimtools').getAddonInfo('path'))


_CARDS = (  # mode, label, description, note, icon
    (ORIGINAL, 30661, 30662, 30666, 'traktsc_original.png'),
    (CUSTOM,   30663, 30664, 30667, 'traktsc_custom.png'),
    (ANIME,    30709, 30710, 30711, 'traktsc_anime.png'),
)


class _Window(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.hint = kwargs.get('hint', 30668)
        self.result = -1

    def onInit(self):
        try:
            base = _addon_path()
            self.setProperty('background', os.path.join(
                base, 'resources', 'media', 'backgroundpiers.jpg'))
            cur = current_mode()
            panel = self.getControl(100)
            panel.reset()
            for mode, lab, desc, note, icon in _CARDS:
                li = xbmcgui.ListItem(AR(lab), AR(desc))
                ic = os.path.join(base, 'resources', 'icons', icon)
                li.setArt({'icon': ic, 'thumb': ic})
                li.setProperty('note', AR(note))
                if mode == cur or (mode == ANIME and anime_picks()):
                    li.setProperty('current', 'true')
                    li.setProperty('current_label', AR(30644))
                panel.addItem(li)
            self.getControl(9001).setLabel(AR(30660))
            self.getControl(9003).setLabel(AR(30665))
            self.getControl(9002).setLabel(AR(self.hint))
            for _ in range(10):
                self.setFocusId(100)
                if self.getFocusId() == 100:
                    break
                xbmc.sleep(100)
        except Exception as e:
            _log('window init: %s' % e, xbmc.LOGERROR)

    def onClick(self, control_id):
        if control_id == 100:
            self.result = self.getControl(100).getSelectedPosition()
        self.close()

    def onAction(self, action):
        if action.getId() in (xbmcgui.ACTION_NAV_BACK,
                              xbmcgui.ACTION_PREVIOUS_MENU,
                              xbmcgui.ACTION_STOP):
            self.close()


def _ask(hint):
    w = _Window('trakt_hubs.xml', _addon_path(), 'Default', '1080i', hint=hint)
    w.doModal()
    idx = w.result
    del w
    return idx


def choose(wait_clear=None, settle=None, from_menu=False):
    """Original / Custom, or None (menu: Back = cancel). Setup: Back (confirmed) =
    Original; a window torn down instantly is shown again (af3_shortcuts rule)."""
    attempt = 0
    while attempt < 6:
        if wait_clear:
            wait_clear()
        started = time.time()
        idx = _ask(30643 if from_menu else 30668)
        if idx >= 0:
            return MODES[idx]
        if time.time() - started > 1.5:
            if from_menu:
                return None
            # 3.4.21: setup - Back asks before skipping; "Back to the step"
            # shows the cards again.
            from resources.lib import skip_guard
            from resources.lib.i18n import T
            if skip_guard.confirm(T(30660)):
                return ORIGINAL
            continue
        attempt += 1
        _log('window closed instantly (attempt %d) - showing it again' % attempt)
        if settle and not settle(2):
            break
    return None if from_menu else ORIGINAL


def _link_trakt(force=False):
    """Ask for TMDb Helper's Trakt authorize (QR) - required for Custom.
    Returns the token or ''. force: the stored token was refused, so a
    token that is already there does not count until a new one arrives."""
    old = _token() if force else ''
    yes = xbmcgui.Dialog().yesno(AR(30660), AR(30669))
    _log('link Trakt now: %s' % ('yes' if yes else 'no'))
    if not yes:
        return ''
    xbmc.executebuiltin('RunScript(%s,authenticate_trakt)' % TMDBH)
    mon = xbmc.Monitor()
    started = time.time()
    seen_dialog = False
    while time.time() - started < 600:
        if mon.waitForAbort(1):
            return ''
        tok = _token()
        if tok and tok != old:
            xbmc.sleep(1500)             # let TMDb Helper close its dialog
            return tok
        if xbmc.getCondVisibility('System.HasModalDialog'):
            seen_dialog = True
        elif seen_dialog or time.time() - started > 20:
            break                         # closed (or never shown) without a token
    tok, state = _token_info()
    _log('after linking: token %s' % state)
    return tok if tok and tok != old else ''



def _label2(c):
    if c.get('src') == 'build':
        return AR(30688)
    if c.get('prov') == 'mdblist':
        s = AR(30701) % (c.get('uname') or 'MDBList', c.get('likes', 0), c.get('count', 0))
        return ('[COLOR FFFF7A1A]%s[/COLOR]  •  %s' % (AR(30702), s)) if c.get('mine') else s
    s = AR(30679) % (c.get('uname') or c['user'], c.get('likes', 0), c.get('count', 0))
    if c.get('liked'):
        s = '[COLOR FFFF7A1A]%s[/COLOR]  •  %s' % (AR(30680), s)
    return s


NOPREVIEW_PROP = 'abk.nopreview'


class _no_preview(object):
    """While set, the patched AF3 DialogSelect hides its artwork "Preview"
    (معاينة) button (patcher entry 'AF3 - no Preview in ABUKARIM pickers');
    every other select dialog in the skin keeps it."""

    def __enter__(self):
        xbmcgui.Window(10000).setProperty(NOPREVIEW_PROP, '1')
        return self

    def __exit__(self, *exc):
        xbmcgui.Window(10000).clearProperty(NOPREVIEW_PROP)
        return False


def _settle_dialogs(max_s=6):
    """Wait until the progress window is really gone and no dialog is up -
    a select opened while it is still closing is torn down at once
    (log 2026-10-12 06:28:12: both Korean pickers closed in 0.2 s)."""
    mon = xbmc.Monitor()
    clear = 0
    for _ in range(int(max_s * 4)):
        if xbmc.getCondVisibility('System.HasModalDialog | '
                                  'Window.IsActive(progressdialog) | '
                                  'Window.IsActive(busydialog) | '
                                  'Window.IsActive(busydialognocancel)'):
            clear = 0
        else:
            clear += 1
            if clear >= 2:
                break
        if mon.waitForAbort(0.25):
            break
    xbmc.sleep(300)


TMDBH_API_CATEGORY = 3      # TMDb Helper settings: general, widgets, library, API keys


def _offer_mdblist():
    """No MDBList key in TMDb Helper -> a button that opens TMDb Helper's
    settings on its API keys page (MDbList API key). Returns True when a
    key is there afterwards."""
    if _mdblist_key():
        return True
    if not xbmcgui.Dialog().yesno(AR(30660), AR(30703), nolabel=AR(30704),
                                  yeslabel=AR(30705)):
        _log('MDBList: user skipped the authorisation')
        return False
    _log('MDBList: opening TMDb Helper settings (API keys)')
    xbmc.executebuiltin('Addon.OpenSettings(%s)' % TMDBH)
    mon = xbmc.Monitor()
    for _ in range(40):                       # wait for the settings window
        if xbmc.getCondVisibility('Window.IsActive(addonsettings)'):
            break
        if mon.waitForAbort(0.25):
            return False
    xbmc.sleep(300)
    # category buttons are -200 + index (Kodi GUIDialogSettingsBase)
    xbmc.executebuiltin('SetFocus(%d)' % (-200 + TMDBH_API_CATEGORY))
    started = time.time()
    while xbmc.getCondVisibility('Window.IsActive(addonsettings)'):
        if mon.waitForAbort(0.5) or time.time() - started > 900:
            break
    xbmc.sleep(500)
    ok = bool(_mdblist_key())
    _log('MDBList key after the settings: %s' % ('set' if ok else 'still missing'))
    return ok


def _ask_widget_mode():
    """What happens to the hub's current widgets: add / replace / keep.
    Back (or a picker torn down 5 times) = keep - nothing changes."""
    opts = ((ADD, 30693, 30694), (REPLACE, 30695, 30697), (KEEP, 30698, 30699))
    items = []
    icon = os.path.join(_addon_path(), 'resources', 'icons', 'traktsc_custom.png')
    for _m, lab, desc in opts:
        li = xbmcgui.ListItem(AR(lab), AR(desc))
        li.setArt({'icon': icon, 'thumb': icon})
        items.append(li)
    idx = -1
    for attempt in range(1, 6):
        _settle_dialogs()
        started = time.time()
        with _no_preview():
            idx = xbmcgui.Dialog().select(AR(30692), items, useDetails=True)
        if idx >= 0 or time.time() - started > 1.5:
            break
        _log('widget-mode question closed instantly (attempt %d)' % attempt)
    mode = opts[idx][0] if idx >= 0 else KEEP
    _log('current hub widgets: %s' % mode)
    return mode


def _pick(heading_id, cands, all_ids=(30696, 30700)):
    if not cands:
        _log('picker %s: nothing to offer' % AR(heading_id))
        return []
    icon = os.path.join(_addon_path(), 'resources', 'icons', 'traktsc_custom.png')
    # 3.2.67: nothing is pre-ticked. When the category has liked lists, the
    # first row selects ALL of them at once (the rest are picked one by one).
    liked = [c for c in cands if c.get('liked')]
    rows = ([None] if liked else []) + list(cands)
    items, pre = [], []
    for c in rows:
        if c is None:
            li = xbmcgui.ListItem('[B]%s[/B]' % AR(all_ids[0]), AR(all_ids[1]) % len(liked))
        else:
            li = xbmcgui.ListItem(c['name'], _label2(c))
        li.setArt({'icon': icon, 'thumb': icon})
        items.append(li)
    sel = None
    for attempt in range(1, 6):
        _settle_dialogs()
        started = time.time()
        with _no_preview():
            sel = xbmcgui.Dialog().multiselect(AR(heading_id), items,
                                               preselect=pre, useDetails=True)
        if sel is not None or time.time() - started > 1.5:
            break
        _log('picker %s closed instantly (attempt %d) - showing it again'
             % (AR(heading_id), attempt))
    if sel is None:                       # Back = nothing from this list
        sel = []
    out, seen = [], set()
    if liked and 0 in sel:
        for c in liked:
            out.append(c)
            seen.add(_key(c))
    for i in sel:
        c = rows[i]
        if c is not None and _key(c) not in seen:
            out.append(c)
            seen.add(_key(c))
    _log('picker %s: %d of %d%s' % (AR(heading_id), len(out), len(cands),
                                     ' (all liked)' if liked and 0 in sel else ''))
    return out


def _slim(c):
    return {k: c.get(k) for k in ('name', 'user', 'uname', 'slug', 'likes',
                                  'count', 'liked', 'src', 'prov', 'mid', 'mine')}


def _custom():
    """Fetch, pick, save, write. True when Custom is in place."""
    if not _tmdbh_installed():
        xbmcgui.Dialog().ok(AR(30660), AR(30683))
        return False
    # 3.2.61: Custom REQUIRES the Trakt link (TMDb Helper). No link -> Original.
    tok, state = _token_info()
    _log('TMDb Helper Trakt token %s' % state)
    if not tok and not _link_trakt():
        return NOLINK
    wmode = _ask_widget_mode()
    if wmode == KEEP:
        return KEEP
    _offer_mdblist()
    res = None
    for attempt in (1, 2):
        dp = xbmcgui.DialogProgress()
        dp.create(AR(30660), AR(30670))
        try:
            res = fetch(dp)
        finally:
            dp.close()
        _settle_dialogs()
        if res is None and _LAST.get('unauthorized') and attempt == 1:
            # stored token refused by Trakt: link again (same QR), then retry
            if not _link_trakt(force=True):
                return NOLINK
            continue
        break
    if res is None and _LAST.get('unauthorized'):
        return NOLINK
    if res is None:
        xbmcgui.Dialog().ok(AR(30660), AR(30689 if _LAST['r429'] else 30672))
        return False
    cats = res['cats']
    if _LAST.get('likes_limited'):
        xbmcgui.Dialog().notification(AR(30660), AR(30690),
                                      xbmcgui.NOTIFICATION_WARNING, 6000)
    # 3.2.63: the picks become widget rows; the build's own Korean lists
    # stay in the Korean sub-menu and are not offered again
    have = set()
    for defaults in korean_defaults().values():
        have |= {_key(c) for c in defaults}
    for cat in ('kr_movies', 'kr_tv'):
        cats[cat] = [c for c in cats.get(cat, []) if _key(c) not in have]
    if not any(cats.values()):
        xbmcgui.Dialog().ok(AR(30660), AR(30685))
        return False
    picks = {}
    for cat, heading in CATS:
        picks[cat] = [_slim(c) for c in _pick(heading, cats.get(cat) or [])]
    _log('picks: %s' % ', '.join('%s=%d' % (k, len(v)) for k, v in picks.items()))
    written = _apply_files(CUSTOM, picks, wmode=wmode)
    _save_state({'mode': CUSTOM, 'time': int(time.time()), 'picks': picks,
                 'wmode': wmode, 'style_v': STYLE_VERSION,
                 'liked_ok': res.get('liked_ok'),
                 'class_cache': res.get('cache') or {}})
    _log('custom applied, files written: %s' % (', '.join(written) or 'none'))
    if written:
        _rebuild()
    _SESSION['applied'] = True
    return True


# ---------------------------------------------------------------------------
# Anime (3.3.6): Otaku lists as widget rows on the HOME page
# ---------------------------------------------------------------------------

OTAKU = 'plugin.video.otaku'
OTAKU_REPO = 'repository.otaku'
W_HOME = 'skinvariables-shortcut-homewidgets.json'
ANIME_PREFIX = 'guid-abkn'          # not GUID_PREFIX: the hub code never strips these
_OTAKU_ICONS = 'special://home/addons/context.otaku/resources/images/icons/colouredv2/'

# route, label id, icon (context.otaku colouredv2), widget style.
# From the user's Otaku favourites list (2026-10-14). Left out: OpenWizard
# (not anime) and airing_calendar - that route opens a full-screen window
# (Anichart doModal), so as a widget it would pop up every time Home loads.
# trending / popular / genres are Otaku sub-menus (category tiles).
ANIME_ENTRIES = (
    ('next_up',            30719, 'next_up.png',      'Landscape'),
    ('airing_last_season', 30720, 'airing_anime.png', 'Flyer'),
    ('airing_this_season', 30721, 'airing_anime.png', 'Flyer'),
    ('airing_next_season', 30722, 'airing_anime.png', 'Flyer'),
    ('trending',           30723, 'trending.png',     'Landscape'),
    ('popular',            30724, 'popular.png',      'Landscape'),
    ('top_100',            30725, 'top_100_anime.png', 'Flyer'),
    ('genres',             30726, 'genres_&_tags.png', 'Landscape'),
)
_ANIME_BY_ROUTE = {e[0]: e for e in ANIME_ENTRIES}


def anime_picks():
    st = _load_state()
    picks = st.get('anime')
    return [r for r in picks if r in _ANIME_BY_ROUTE] if isinstance(picks, list) else []


def _otaku_installed():
    return os.path.isfile(os.path.join(
        xbmcvfs.translatePath('special://home/addons/'), OTAKU, 'addon.xml'))


def _anime_ours(item):
    return isinstance(item, dict) and str(item.get('guid') or '').startswith(ANIME_PREFIX)


def _anime_widget(route):
    _r, lab, icon, style = _ANIME_BY_ROUTE[route]
    return {'label': AR(lab), 'icon': _OTAKU_ICONS + icon,
            'path': 'plugin://%s/%s' % (OTAKU, route), 'target': 'videos',
            'guid': '%s-%s' % (ANIME_PREFIX, route), 'widget_style': style}


def _apply_anime(routes):
    """Home widgets file: our anime rows out, the picks appended (in the
    ANIME_ENTRIES order). Everything else on the home page stays. Returns
    True when the file was written."""
    path = _hub(W_HOME)
    if not os.path.isfile(path):
        _log('%s not found - anime rows not written' % W_HOME, xbmc.LOGWARNING)
        return False
    try:
        with open(path, 'r', encoding='utf-8') as f:
            before = f.read()
        data = json.loads(before)
        if not isinstance(data, list):
            return False
    except Exception as e:
        _log('%s unreadable: %s' % (W_HOME, e), xbmc.LOGWARNING)
        return False
    data = [it for it in data if not _anime_ours(it)]
    want = set(routes)
    data += [_anime_widget(e[0]) for e in ANIME_ENTRIES if e[0] in want]
    return _write(path, data, before)


def _ensure_anime():
    """Boot: anime picks saved but the home file lost them (restore, Widgets
    Layout, Patch GUI replaced it wholesale) -> append them again."""
    routes = anime_picks()
    path = _hub(W_HOME)
    if not routes or not os.path.isfile(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            if ANIME_PREFIX in f.read():
                return []
    except Exception:
        return []
    return [W_HOME] if _apply_anime(routes) else []


def _install_otaku():
    try:
        from resources.lib import addon_portal
        res = addon_portal._install_selection([(OTAKU, 'Otaku', OTAKU_REPO)])
        _log('Otaku install: %s' % res)
    except Exception as e:
        _log('Otaku install failed: %s' % e, xbmc.LOGWARNING)
    _settle_dialogs()
    return _otaku_installed()


def _pick_anime():
    """Multiselect of ANIME_ENTRIES, current picks ticked. None = Back."""
    cur = set(anime_picks())
    items, pre = [], []
    for i, (route, lab, icon, _st) in enumerate(ANIME_ENTRIES):
        li = xbmcgui.ListItem(AR(lab), AR(30727) if route == 'next_up' else '')
        ic = xbmcvfs.translatePath(_OTAKU_ICONS + icon)
        li.setArt({'icon': ic, 'thumb': ic})
        items.append(li)
        if route in cur:
            pre.append(i)
    sel = None
    for attempt in range(1, 6):
        _settle_dialogs()
        started = time.time()
        with _no_preview():
            sel = xbmcgui.Dialog().multiselect(AR(30712), items, preselect=pre,
                                               useDetails=True)
        if sel is not None or time.time() - started > 1.5:
            break
        _log('anime picker closed instantly (attempt %d)' % attempt)
    if sel is None:
        return None
    return [ANIME_ENTRIES[i][0] for i in sel]


def run_anime():
    """Card "Anime": pick Otaku lists -> widget rows on the home page.
    The hubs are not touched. True when the home page ends up as picked."""
    if not _otaku_installed():
        if not xbmcgui.Dialog().yesno(AR(30660), AR(30713)):
            return False
        if not _install_otaku():
            xbmcgui.Dialog().ok(AR(30660), AR(30714))
            return False
    routes = _pick_anime()
    if routes is None:
        _log('anime: Back - home page left as it is')
        xbmcgui.Dialog().notification(AR(30660), AR(30717),
                                      xbmcgui.NOTIFICATION_INFO, 3000)
        return False
    written = _apply_anime(routes)
    st = _load_state()
    st['anime'] = routes
    if st.get('mode') not in MODES:
        st['mode'] = ORIGINAL
    _save_state(st)
    _log('anime on home: %s (file %s)' % (', '.join(routes) or 'none',
                                          'written' if written else 'unchanged'))
    if written:
        _rebuild()
    msg = (AR(30715) % len(routes)) if routes else AR(30716)
    xbmcgui.Dialog().notification(AR(30660), msg, xbmcgui.NOTIFICATION_INFO, 4000)
    return True



def _plain(text):
    return re.sub(r'\[/?(?:COLOR[^\]]*|B|I)\]', '', text or '')


def phone_fetch():
    """3.3.7 phone setup: the Trakt candidates without any dialog.
    Returns {'ok': True, 'cats': {cat: [{'key','name','info','liked'}]}} or
    {'ok': False, 'error': 'tmdbh'|'nolink'|'busy'|'offline'|'empty'}.
    The full candidates are kept for phone_apply()."""
    if not _tmdbh_installed():
        return {'ok': False, 'error': 'tmdbh'}
    if not _token():
        return {'ok': False, 'error': 'nolink'}
    res = fetch(None)
    if res is None:
        if _LAST.get('unauthorized'):
            return {'ok': False, 'error': 'nolink'}
        return {'ok': False, 'error': 'busy' if _LAST.get('r429') else 'offline'}
    cats = res['cats']
    have = set()
    for defaults in korean_defaults().values():
        have |= {_key(c) for c in defaults}
    for cat in ('kr_movies', 'kr_tv'):
        cats[cat] = [c for c in cats.get(cat, []) if _key(c) not in have]
    if not any(cats.values()):
        return {'ok': False, 'error': 'empty'}
    _SESSION['phone_cands'] = {k: {_key(c): c for c in v} for k, v in cats.items()}
    _SESSION['phone_cache'] = res.get('cache') or {}
    _SESSION['phone_liked_ok'] = res.get('liked_ok')
    out = {}
    for cat, heading in CATS:
        out[cat] = {'title': AR(heading),
                    'items': [{'key': _key(c), 'name': c['name'],
                               'by': c.get('uname') or c.get('user') or '',
                               'likes': int(c.get('likes') or 0),
                               'count': int(c.get('count') or 0),
                               'src': 'MDBList' if c.get('prov') == 'mdblist' else '',
                               'mine': bool(c.get('mine')),
                               'liked': bool(c.get('liked'))}
                              for c in cats.get(cat) or []]}
    return {'ok': True, 'cats': out}


def phone_apply(keys_by_cat, wmode=ADD):
    """Write the phone's Trakt picks (keys from phone_fetch). True / False."""
    cands = _SESSION.get('phone_cands')
    if not cands:
        return False
    if wmode not in (ADD, REPLACE):
        wmode = ADD
    picks = {}
    for cat, _h in CATS:
        pool = cands.get(cat) or {}
        picks[cat] = [_slim(pool[k]) for k in (keys_by_cat.get(cat) or []) if k in pool]
    written = _apply_files(CUSTOM, picks, wmode=wmode)
    _save_state({'mode': CUSTOM, 'time': int(time.time()), 'picks': picks,
                 'wmode': wmode, 'style_v': STYLE_VERSION,
                 'liked_ok': _SESSION.get('phone_liked_ok'),
                 'class_cache': _SESSION.get('phone_cache') or {}})
    _log('phone: custom applied (%s), files written: %s'
         % (', '.join('%s=%d' % (k, len(v)) for k, v in picks.items()),
            ', '.join(written) or 'none'))
    if written:
        _rebuild()
    return True


def phone_original():
    written = _apply_files(ORIGINAL, {})
    _save_state({'mode': ORIGINAL, 'time': int(time.time()),
                 'class_cache': _load_state().get('class_cache') or {}})
    if written:
        _rebuild()
    return True


def phone_anime(routes):
    """Anime rows on the home page from the phone (Otaku must be there)."""
    routes = [r for r in routes if r in _ANIME_BY_ROUTE]
    written = _apply_anime(routes)
    st = _load_state()
    st['anime'] = routes
    if st.get('mode') not in MODES:
        st['mode'] = ORIGINAL
    _save_state(st)
    if written:
        _rebuild()
    return True


def apply(mode):
    """Apply a choice. Returns True when the box ends up as requested."""
    if mode == ANIME:
        return run_anime()
    if mode == CUSTOM:
        res = _custom()
        if res == KEEP:
            _log('hub widgets kept as they are - nothing changed')
            xbmcgui.Dialog().notification(AR(30660), AR(30682),
                                          xbmcgui.NOTIFICATION_INFO, 3000)
            return True
        if res is True:
            xbmcgui.Dialog().notification(AR(30660), AR(30681) % AR(30663),
                                          xbmcgui.NOTIFICATION_INFO, 4000)
            return True
        if res == NOLINK:
            # 3.2.61: no Trakt link -> Original (as announced in the dialog)
            _log('Trakt not linked - applying Original')
            written = _apply_files(ORIGINAL, {})
            _save_state({'mode': ORIGINAL, 'time': int(time.time()),
                         'class_cache': _load_state().get('class_cache') or {}})
            if written:
                _rebuild()
            xbmcgui.Dialog().notification(AR(30660), AR(30691),
                                          xbmcgui.NOTIFICATION_WARNING, 5000)
            return False
        # 3.2.58: failed / offline / rate limited - leave the box exactly as
        # it is (a working Custom from an earlier run is NOT wiped).
        _log('custom not applied - hubs left as they are')
        if current_mode() is None:
            _save_state({'mode': ORIGINAL, 'time': int(time.time()),
                         'class_cache': _load_state().get('class_cache') or {}})
        return False
    written = _apply_files(ORIGINAL, {})
    _save_state({'mode': ORIGINAL, 'time': int(time.time()),
                 'class_cache': _load_state().get('class_cache') or {}})
    if written:
        _log('original restored in %s' % ', '.join(written))
        _rebuild()
    return True


def run_step(wait_clear=None, settle=None):
    """Installation Wizard entry point."""
    mode = choose(wait_clear, settle)
    _log('choice: %s' % mode)
    ok = apply(mode)
    wait_rebuild()                        # 3.2.59: the patcher comes next
    _log('step finished')
    return ok


def run_menu():
    """Setup & Install -> My Lists (قوائمي)."""
    mode = choose(from_menu=True)
    _log('menu choice: %s' % mode)
    if mode is None:
        return False
    ok = apply(mode)
    if mode == ORIGINAL:
        xbmcgui.Dialog().notification(AR(30660), AR(30681) % AR(30661),
                                      xbmcgui.NOTIFICATION_INFO, 3000)
    return ok
