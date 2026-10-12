# -*- coding: utf-8 -*-
"""
trakt_hubs.py - "Trakt Lists" (قوائم تراكت): which Trakt lists the Arctic
Fuse 3 Movies / TV Shows / Korean hubs carry. Shown in the Installation
Wizard right after Widgets Layout, and from Setup & Install in the menu.

All its texts are ARABIC (Modern Standard Arabic) on purpose, like
af3_shortcuts: the window uses the add-on's Arabic-capable fonts and Kodi's
dialogs fall back to the Arabic arial.ttf the add-on installs.

    Original  the hubs stay exactly as the build ships them
    Custom    the user's Trakt likes + the best Trakt lists they tick

What Custom touches (and nothing else):

    hub 1101 (Movies)   two groups appended to its sub-menu:
    hub 1102 (TV)       "قوائم أعجبتني" (liked lists) and
                        "الأفضل في تراكت" (best lists)
    hub 1103 (Korean)   its Movies / Series sub-menus: the build's own
                        third-party Korean lists are offered pre-ticked;
                        unticked ones are hidden (disabled + tagged), the
                        new picks are appended.

Never touched: the Home page (homesubmenu / homewidgets), every hub's
widgets, and the ABUKARIM lists on Trakt (user taiseer999) - they are not
even offered in the picker.

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


ORIGINAL, CUSTOM = 'original', 'custom'
MODES = (ORIGINAL, CUSTOM)

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

# picker categories: key, heading string id
CATS = (('movies', 30673), ('tv', 30674), ('kr_movies', 30675), ('kr_tv', 30676))
BEST_PER_CAT = 25

GUID_PREFIX = 'guid-abkt'
OFF_TAG = 'abk_trakt'
ICON_LIST = 'special://skin/extras/icons/playlist.png'
ICON_KOREAN = 'special://skin/extras/icons/kdramaw.png'

_KR_WORDS = re.compile(r'korea|k-?drama|kdrama|k-?movie|hallyu|한국|كوري', re.I)
_SESSION = {'applied': False}
_LAST = {'r429': 0, 'likes_limited': False, 'unauthorized': False}
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
        'name': (lst.get('name') or slug).strip(),
        'user': user, 'uname': uname, 'slug': slug,
        'likes': likes, 'count': count, 'liked': bool(liked),
        'desc': (lst.get('description') or '')[:300],
        'src': source,
    }


def _key(c):
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
        cat = hit[0] if hit else _guess(c)
        if cat in cats:
            cats[cat].append(c)
        elif hit and hit[0] == '-':
            continue                              # known empty / unusable
        else:
            need.append(c)
    # liked first, then the most liked - within the call budget
    need.sort(key=lambda c: (not c['liked'], -c['likes']))
    skipped = max(0, len(need) - CLASSIFY_BUDGET)
    need = need[:CLASSIFY_BUDGET]
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
    for k in cats:
        liked = sorted((c for c in cats[k] if c['liked']), key=lambda c: c['name'].lower())
        best = sorted((c for c in cats[k] if not c['liked']), key=lambda c: -c['likes'])
        cats[k] = liked + best[:BEST_PER_CAT]
    _log('fetch done in %.1fs: %s, %d calls, %d x 429'
         % (time.time() - t0, ', '.join('%s=%d' % (k, len(v)) for k, v in cats.items()),
            trakt.calls, trakt.r429))
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


def _path(c):
    q = urllib.parse.quote
    return ('plugin://%s/?info=trakt_userlist&list_name=%s&list_slug=%s'
            '&plugin_category=%s&tmdb_type=both&user_slug=%s'
            % (TMDBH, q(c['name'], safe=''), q(c['slug'], safe=''),
               q(c['name'], safe=''), q(c['user'], safe='')))


def _item(c, hub, icon):
    return {'label': c['name'], 'path': _path(c), 'icon': icon,
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
                    it.pop(OFF_TAG, None)
                    if not it.get('abk_hidden'):          # menu_reconcile's own hide
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


def _apply_hub_split(data, hub, liked, best):
    _strip(data)
    if liked:
        data.append(_group(30677, hub, [_item(c, hub, ICON_LIST) for c in liked]))
    if best:
        data.append(_group(30678, hub, [_item(c, hub, ICON_LIST) for c in best]))
    return data


def _apply_korean(data, picks_m, picks_t):
    _strip(data)
    mg, tg = _korean_groups(data)
    for g, picks in ((mg, picks_m), (tg, picks_t)):
        keep = {_key(c) for c in picks}
        present = set()
        for it in g['submenu']:
            k = _item_key(it) if isinstance(it, dict) else None
            if not k or k.split('/', 1)[0].lower() in FIXED_USERS:
                continue
            if k in keep:
                present.add(k)
            elif not str(it.get('disabled') or '').lower() == 'true':
                it['disabled'] = 'True'
                it[OFF_TAG] = 'off'
        for c in picks:
            if _key(c) not in present:
                g['submenu'].append(_item(c, '1103', ICON_KOREAN))
                present.add(_key(c))
    return data


def _apply_files(mode, picks, only=None):
    """Write the hub files. only = set of file names to touch (None = all).
    Returns the list of files written."""
    written = []
    jobs = ((HUB_MOVIES, 'movies'), (HUB_TV, 'tv'), (HUB_KOREAN, 'korean'))
    for name, kind in jobs:
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
        if mode == CUSTOM:
            if kind == 'korean':
                data = _apply_korean(data, picks.get('kr_movies') or [],
                                     picks.get('kr_tv') or [])
            else:
                sel = picks.get(kind) or []
                data = _apply_hub_split(data, kind,
                                        [c for c in sel if c.get('liked')],
                                        [c for c in sel if not c.get('liked')])
        else:
            data = _strip(data)
        if _write(path, data, before):
            written.append(name)
    return written


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
    """Boot / end of setup: put saved Custom picks back into a hub file that
    lost them wholesale. No network. Returns files written."""
    st = _load_state()
    if st.get('mode') != CUSTOM or not isinstance(st.get('picks'), dict):
        return []
    picks = st['picks']
    need = set()
    for name, cats in ((HUB_MOVIES, ('movies',)), (HUB_TV, ('tv',)),
                       (HUB_KOREAN, ('kr_movies', 'kr_tv'))):
        if not any(picks.get(c) for c in cats):
            continue
        p = _hub(name)
        if os.path.isfile(p) and not _has_marker(p):
            need.add(name)
    if not need:
        return []
    written = _apply_files(CUSTOM, picks, only=need)
    if written:
        _log('custom Trakt lists re-applied to %s' % ', '.join(written))
        if rebuild:
            _rebuild()
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
                if mode == cur:
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
    """Original / Custom, or None (menu: Back = cancel). Setup: Back =
    Original; a window torn down instantly is shown again (af3_shortcuts rule)."""
    for attempt in range(1, 7):
        if wait_clear:
            wait_clear()
        started = time.time()
        idx = _ask(30643 if from_menu else 30668)
        if idx >= 0:
            return MODES[idx]
        if time.time() - started > 1.5:
            return None if from_menu else ORIGINAL
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
    s = AR(30679) % (c.get('uname') or c['user'], c.get('likes', 0), c.get('count', 0))
    if c.get('liked'):
        s = '[COLOR FFFF7A1A]%s[/COLOR]  •  %s' % (AR(30680), s)
    return s


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


def _pick(heading_id, cands):
    if not cands:
        _log('picker %s: nothing to offer' % AR(heading_id))
        return []
    icon = os.path.join(_addon_path(), 'resources', 'icons', 'traktsc_custom.png')
    items, pre = [], []
    for i, c in enumerate(cands):
        li = xbmcgui.ListItem(c['name'], _label2(c))
        li.setArt({'icon': icon, 'thumb': icon})
        items.append(li)
        if c.get('liked') or c.get('src') == 'build':
            pre.append(i)
    sel = None
    for attempt in range(1, 6):
        _settle_dialogs()
        started = time.time()
        sel = xbmcgui.Dialog().multiselect(AR(heading_id), items, preselect=pre,
                                           useDetails=True)
        if sel is not None or time.time() - started > 1.5:
            break
        _log('picker %s closed instantly (attempt %d) - showing it again'
             % (AR(heading_id), attempt))
    if sel is None:                       # Back = keep the pre-ticked ones
        sel = pre
    _log('picker %s: %d of %d' % (AR(heading_id), len(sel), len(cands)))
    return [cands[i] for i in sel]


def _slim(c):
    return {k: c.get(k) for k in ('name', 'user', 'uname', 'slug', 'likes',
                                  'count', 'liked', 'src')}


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
    # the build's own Korean lists first (pre-ticked), then Trakt's
    for cat, defaults in korean_defaults().items():
        have = {_key(c) for c in defaults}
        cats[cat] = defaults + [c for c in cats.get(cat, []) if _key(c) not in have]
    if not any(cats.values()):
        xbmcgui.Dialog().ok(AR(30660), AR(30685))
        return False
    picks = {}
    for cat, heading in CATS:
        picks[cat] = [_slim(c) for c in _pick(heading, cats.get(cat) or [])]
    _log('picks: %s' % ', '.join('%s=%d' % (k, len(v)) for k, v in picks.items()))
    written = _apply_files(CUSTOM, picks)
    _save_state({'mode': CUSTOM, 'time': int(time.time()), 'picks': picks,
                 'liked_ok': res.get('liked_ok'),
                 'class_cache': res.get('cache') or {}})
    _log('custom applied, files written: %s' % (', '.join(written) or 'none'))
    if written:
        _rebuild()
    _SESSION['applied'] = True
    return True


def apply(mode):
    """Apply a choice. Returns True when the box ends up as requested."""
    if mode == CUSTOM:
        res = _custom()
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
    """Setup & Install -> Trakt Lists."""
    mode = choose(from_menu=True)
    _log('menu choice: %s' % mode)
    if mode is None:
        return False
    ok = apply(mode)
    if mode == ORIGINAL:
        xbmcgui.Dialog().notification(AR(30660), AR(30681) % AR(30661),
                                      xbmcgui.NOTIFICATION_INFO, 3000)
    return ok
