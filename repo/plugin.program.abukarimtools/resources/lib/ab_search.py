# -*- coding: utf-8 -*-
"""
ab_search.py - ABUKARIM TOOLS (3.4.48)

"Search All": one stream list collected from every supported video add-on,
in the style of Dex Hub's source browser (filter chips per add-on and per
quality, one row per release with the add-ons that found it).

How the streams are collected - each add-on scrapes with its own settings,
scrapers and debrid accounts, and plays with its own resolver:

  plugin://<add-on>/?mode=app_list_sources&request_id=<id>&media_type=...
      run through JSON-RPC Files.GetDirectory, one thread per add-on. The
      add-on scrapes with no window and saves its sorted results to
      addon_data/<add-on>/device_select/<id>.json (Fen Light's own
      device-select protocol; Red Light gets the same two modes from the
      "Search All bridge" patch, lucent_sources.SPECS['redlight_search']).
  RunPlugin(plugin://<add-on>/?mode=app_play_source&request_id=<id>&selected_index=N...)
      plays results[N] through that add-on (resolve + failover through the rest).

Started from TMDbHelper's player list ("AB Search All", players JSON injected
by the patcher) as plugin://plugin.program.abukarimtools/?mode=ab_search&...
"""
import json
import os
import re
import threading
import time
from urllib.parse import urlencode

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

ADDON_ID = 'plugin.program.abukarimtools'
ADDON_PATH = xbmcvfs.translatePath('special://home/addons/%s/' % ADDON_ID)
MEDIA = 'special://home/addons/%s/resources/lucent/media/' % ADDON_ID
_DATA = xbmcvfs.translatePath('special://profile/addon_data/')

# (key, add-on id, name, tag) in play priority order; key picks the colour in ab_search.xml
ADDONS = (('rl', 'plugin.video.redlight', 'Red Light', 'RL'),
          ('fl', 'plugin.video.fenlight', 'Fen Light', 'FL'),
          ('umb', 'plugin.video.umbrella', 'Umbrella', 'UM'),
          ('pov', 'plugin.video.pov', 'POV', 'POV'))
_MODULES = os.path.join('resources', 'lib', 'modules')
# file that carries the device-select modes, and the text that proves it
_SUPPORT = {'fl': ('router.py', 'app_list_sources'), 'rl': ('router.py', 'abk_device_select'),
            'umb': ('router.py', 'abk_device_select'), 'pov': ('entry.py', 'abk_device_select')}
# Search All bridge patch (lucent_sources.SPECS) per add-on; Fen Light has the modes natively
_BRIDGE = {'rl': 'redlight_search', 'umb': 'umbrella_search', 'pov': 'pov_search'}

LIST, CHIPS = 2000, 2300
_QUALITIES = ('4K', '1080P', '720P', 'SD')
_QRANK = {'4K': 0, '1080P': 1, '720P': 2, 'SD': 3}
_ACTION_BACK = (9, 10, 92, 216, 247, 257, 275, 61467, 61448)
_ACTION_MENU = (101, 117)            # long press / context menu: "Play with ..."
_ACTION_RIGHT = 2                    # RIGHT on the stream list: filter menu
_SCRAPE_TIMEOUT = 240                # a listing that never answers stops counting after this


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools Search All] %s' % msg, level)


# ───────────────────────── Glass theme helper (shared) ─────────────────────────

_THEME = []


def _theme():
    """resources/lucent/lucent_theme.py - the helper the add-ons' Glass windows use
    (badges, resolution flags, service icons, title/meta properties)."""
    if not _THEME:
        mod = None
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                'abk_lucent_theme', os.path.join(ADDON_PATH, 'resources', 'lucent', 'lucent_theme.py'))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except Exception as e:
            _log('theme helper failed: %s' % e, xbmc.LOGWARNING)
        _THEME.append(mod)
    return _THEME[0]


# ───────────────────────── add-ons ─────────────────────────

def _addon_dir(aid):
    return xbmcvfs.translatePath('special://home/addons/%s/' % aid)


def _supported(key, aid):
    try:
        rel, mark = _SUPPORT[key]
        with open(os.path.join(_addon_dir(aid), _MODULES, rel), 'r', encoding='utf-8', errors='replace') as f:
            return mark in f.read()
    except Exception:
        return False


def _ensure_bridge(key, aid):
    """Bridge missing (add-on just installed / updated): add it now."""
    if key not in _BRIDGE or _supported(key, aid):
        return
    try:
        from resources.lib import lucent_sources
        ok, msg = lucent_sources.apply(_addon_dir(aid), _BRIDGE[key])
        _log('bridge: %s' % msg)
    except Exception as e:
        _log('bridge failed: %s' % e, xbmc.LOGWARNING)


def available_addons():
    """[(key, aid, name, tag, supported)] for the installed add-ons."""
    out = []
    for key, aid, name, tag in ADDONS:
        if not xbmc.getCondVisibility('System.HasAddon(%s)' % aid):
            continue
        _ensure_bridge(key, aid)
        out.append((key, aid, name, tag, _supported(key, aid)))
    return out


# ───────────────────────── collecting ─────────────────────────

class Session(object):
    def __init__(self, media, addons):
        self.media = media
        self.rid = 'abs%d' % int(time.time() * 1000)
        self.addons = addons
        self.lock = threading.Lock()
        self.started = time.time()
        self.state = {}
        for key, aid, name, tag, ok in addons:
            self.state[key] = {'state': 'searching' if ok else 'unsupported', 'results': [], 'took': 0}
        self.listener = None
        self.closed = False
        self.started_threads = False

    def request_id(self, key):
        return '%s_%s' % (self.rid, key)

    def url(self, key, aid, kind, index=None):
        """plugin:// URL of an add-on's list ('list') or play ('play') mode."""
        m = self.media
        if key == 'umb':
            m = getattr(self, 'umb_media', None) or m
        mode = 'app_list_sources' if kind == 'list' else 'app_play_source'
        if key == 'umb':                    # Umbrella: action=..., needs the names and the other ids
            params = {'action': mode, 'title': m.get('title', ''), 'year': m.get('year', ''),
                      'imdb': m.get('imdb', ''), 'tmdb': m['tmdb_id'], 'tvdb': m.get('tvdb', ''),
                      'premiered': m.get('premiered', '')}
            if m['media_type'] == 'episode':
                params.update({'tvshowtitle': m.get('tvshowtitle', ''), 'season': m['season'], 'episode': m['episode']})
        else:
            params = {'mode': mode, 'media_type': m['media_type'], 'tmdb_id': m['tmdb_id']}
            if m['media_type'] == 'episode':
                params.update({'season': m['season'], 'episode': m['episode']})
            if kind == 'list':
                params.update({'autoplay': 'false', 'prescrape': 'false'})
        params['request_id'] = self.request_id(key)
        if index is not None:
            params['selected_index'] = index
        return 'plugin://%s/?%s' % (aid, urlencode(params))

    def start(self):
        for key, aid, name, tag, ok in self.addons:
            if ok:
                threading.Thread(target=self._run, args=(key, aid, name), name='abs_' + key).start()

    def done(self):
        return all(s['state'] != 'searching' for s in self.state.values())

    def _run(self, key, aid, name):
        rid = self.request_id(key)
        if key == 'umb':
            self.umb_media = _english_names(self.media)
        url = self.url(key, aid, 'list')
        path = os.path.join(_DATA, aid, 'device_select', '%s.json' % rid)
        t0 = time.time()
        _log('%s: %s' % (name, url))
        answer = ''
        try:
            answer = xbmc.executeJSONRPC(json.dumps({
                'jsonrpc': '2.0', 'id': 1, 'method': 'Files.GetDirectory',
                'params': {'directory': url, 'media': 'files'}}))
        except Exception as e:
            answer = str(e)
        results, found = [], False
        for _ in range(10):                    # the file is written just before the listing ends
            if os.path.isfile(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        results = json.load(f)
                    found = True
                    break
                except Exception:
                    pass
            xbmc.sleep(200)
        took = time.time() - t0
        if not found:
            _log('%s: no result file after %.1fs - %s' % (name, took, (answer or '')[:300]), xbmc.LOGWARNING)
        else:
            _log('%s: %d sources in %.1fs' % (name, len(results), took))
        with self.lock:
            self.state[key] = {'state': 'done' if found else 'failed', 'results': results if isinstance(results, list) else [],
                               'took': took}
        listener = self.listener
        if listener and not self.closed:
            try:
                listener()
            except Exception as e:
                _log('update failed: %s' % e, xbmc.LOGWARNING)


# ───────────────────────── Umbrella: English names ─────────────────────────
# Umbrella scrapes by title. With Kodi in Arabic, TMDbHelper (and the focused
# item) give the Arabic title, and title-based scrapers then find nothing
# (kodi.log 2026-10-29: "Koko" sent as "كوكو", 0 results). Ask TMDb for the
# English names, with Umbrella's own TMDb key.

_UMB_TMDB_KEY = 'edde6b5e41246ab79a2697cd125e1781'     # Umbrella's built-in default


def _latin(text):
    return all(ord(c) < 0x250 for c in str(text or ''))


def _tmdb(path, lang='en-US'):
    import urllib.request
    key = ''
    try:
        import xbmcaddon
        key = xbmcaddon.Addon('plugin.video.umbrella').getSetting('tmdb.apikey')
    except Exception:
        pass
    url = 'https://api.themoviedb.org/3/%s%sapi_key=%s&language=%s' % (path, '&' if '?' in path else '?', key or _UMB_TMDB_KEY, lang)
    with urllib.request.urlopen(url, timeout=6) as r:
        return json.loads(r.read().decode('utf-8'))


def _english_names(media):
    m = dict(media)
    if _latin(m.get('title')) and _latin(m.get('tvshowtitle')) and m.get('imdb'):
        return m
    try:
        if m['media_type'] == 'movie':
            d = _tmdb('movie/%s?append_to_response=external_ids' % m['tmdb_id'])
            m['title'] = d.get('title') or m.get('title', '')
            m['year'] = (d.get('release_date') or '')[:4] or m.get('year', '')
            m['imdb'] = m.get('imdb') or d.get('imdb_id') or ''
        else:
            d = _tmdb('tv/%s?append_to_response=external_ids' % m['tmdb_id'])
            ext = d.get('external_ids') or {}
            m['tvshowtitle'] = d.get('name') or m.get('tvshowtitle', '')
            m['year'] = (d.get('first_air_date') or '')[:4] or m.get('year', '')
            m['imdb'] = m.get('imdb') or ext.get('imdb_id') or ''
            m['tvdb'] = m.get('tvdb') or str(ext.get('tvdb_id') or '')
            try:
                e = _tmdb('tv/%s/season/%s/episode/%s' % (m['tmdb_id'], m['season'], m['episode']))
                m['title'] = e.get('name') or m.get('title', '')
            except Exception:
                pass
        _log('Umbrella names: %s / %s (%s) %s' % (m.get('title'), m.get('tvshowtitle'), m.get('year'), m.get('imdb')))
    except Exception as e:
        _log('Umbrella names from TMDb failed (%s) - using the ones given' % e, xbmc.LOGWARNING)
    return m


# ───────────────────────── window meta from TMDb ─────────────────────────
# Logo, backdrop, plot, rating, certificate and genres for the left column.
# TMDbHelper's player URL carries only ids and names, and the focused item is
# often not the title any more by the time AB Tools runs (screenshot
# 2026-10-29: title and year only). Kodi's language first, English fallback.

_IMG = 'https://image.tmdb.org/t/p/%s%s'


def _ui_lang():
    try:
        return xbmc.getLanguage(xbmc.ISO_639_1) or 'en'
    except Exception:
        return 'en'


def _pick_logo(logos, lang):
    for want in (lang, 'en', None):
        for lg in logos or []:
            if lg.get('iso_639_1') == want and lg.get('file_path', '').endswith('.png'):
                return _IMG % ('w500', lg['file_path'])
    return ''


def tmdb_window_meta(media):
    """{'fanart', 'clearlogo', 'plot', 'rating', 'mpaa', 'genre', 'year', ...} or {}."""
    lang = _ui_lang()
    tag = 'en-US' if lang == 'en' else lang
    imgs = 'include_image_language=%s,en,null' % lang
    out = {}
    try:
        if media['media_type'] == 'movie':
            d = _tmdb('movie/%s?append_to_response=images,release_dates&%s' % (media['tmdb_id'], imgs), tag)
            out['year'] = (d.get('release_date') or '')[:4]
            for c in (d.get('release_dates') or {}).get('results', []):
                if c.get('iso_3166_1') == 'US':
                    cert = [r.get('certification') for r in c.get('release_dates', []) if r.get('certification')]
                    if cert:
                        out['mpaa'] = cert[0]
        else:
            d = _tmdb('tv/%s?append_to_response=images,content_ratings&%s' % (media['tmdb_id'], imgs), tag)
            out['year'] = (d.get('first_air_date') or '')[:4]
            for c in (d.get('content_ratings') or {}).get('results', []):
                if c.get('iso_3166_1') == 'US' and c.get('rating'):
                    out['mpaa'] = c['rating']
            try:
                e = _tmdb('tv/%s/season/%s/episode/%s' % (media['tmdb_id'], media['season'], media['episode']), tag)
                out['ep_plot'] = e.get('overview') or ''
                out['ep_runtime'] = e.get('runtime') or 0
                out['ep_name_tmdb'] = e.get('name') or ''
            except Exception:
                pass
        out['plot'] = out.pop('ep_plot', '') or d.get('overview') or ''
        if not out['plot'] and tag != 'en-US':
            try:
                path = 'movie/%s' if media['media_type'] == 'movie' else 'tv/%s'
                out['plot'] = _tmdb(path % media['tmdb_id']).get('overview') or ''
            except Exception:
                pass
        if d.get('backdrop_path'):
            out['fanart'] = _IMG % ('w1280', d['backdrop_path'])
        out['clearlogo'] = _pick_logo((d.get('images') or {}).get('logos'), lang)
        if d.get('vote_average'):
            out['rating'] = d['vote_average']
        out['genre'] = ', '.join(g.get('name', '') for g in (d.get('genres') or [])[:3])
        # running time (minutes) for the bitrate estimate
        if media['media_type'] == 'movie':
            out['runtime'] = d.get('runtime') or 0
        else:
            out['runtime'] = out.pop('ep_runtime', 0) or ((d.get('episode_run_time') or [0])[0])
    except Exception as e:
        _log('window meta from TMDb failed: %s' % e, xbmc.LOGWARNING)
        return {}
    return {k: v for k, v in out.items() if v}


# ───────────────────────── merging ─────────────────────────

_TAG_RE = re.compile(r'\[/?(?:B|I|UPPERCASE|LOWERCASE|CAPITALIZE|COLOR[^\]]*)\]', re.I)


def _clean(text):
    return _TAG_RE.sub('', str(text or '')).strip()


def _quality(item):
    q = _clean(item.get('quality') or 'SD').upper()
    if q in ('2160P', 'UHD', '8K'):
        return '4K'
    return q or 'SD'


def _group(q):
    return q if q in _QRANK else 'SD'


def _provider(item):
    get = item.get
    sp = get('scrape_provider', '')
    if sp == 'folders':
        return _clean(get('source', ''))
    if sp == 'external' or get('debrid'):
        return _clean(get('debrid') or get('source', '')).replace('.me', '')
    return _clean(sp or get('source', ''))


def _site(item):
    return _clean(item.get('abk_site') or ((item.get('source') or item.get('provider'))
                                           if item.get('scrape_provider') == 'external' else ''))


_PRETTY = {'ALLDEBRID': 'AllDebrid', 'REAL-DEBRID': 'Real-Debrid', 'REALDEBRID': 'Real-Debrid', 'TORBOX': 'TorBox',
           'PREMIUMIZE': 'Premiumize', 'OFFCLOUD': 'Offcloud', 'EASYNEWS': 'Easynews', 'EASYDEBRID': 'EasyDebrid',
           'DEBRID-LINK': 'Debrid-Link', 'DEBRIDLINK': 'Debrid-Link'}


# 4.5.8: short service code on the card (replaces the coloured icon)
_SHORT = (('REAL', 'RD'), ('ALLDEBRID', 'AD'), ('ALL-DEBRID', 'AD'), ('PREMIUMIZE', 'PM'),
          ('TORBOX', 'TB'), ('OFFCLOUD', 'OC'), ('EASYNEWS', 'EN'), ('EASYDEBRID', 'ED'),
          ('DEBRID-LINK', 'DL'), ('DEBRIDLINK', 'DL'))


def _service_code(provider):
    up = (provider or '').upper().replace(' ', '')
    for key, code in _SHORT:
        if up.startswith(key):
            return code
    if up in ('RD', 'AD', 'PM', 'TB', 'OC', 'EN', 'ED', 'DL'):
        return up
    return ''


_SERVICE_ORDER = ('RD', 'AD', 'PM', 'TB', 'OC', 'EN', 'ED', 'DL')


def _row_service(row):
    code = row.get('svc')
    if code is None:
        code = row['svc'] = _service_code(_provider(row['item']))
    return code


def _pretty(name):
    return _PRETTY.get(name.upper(), name.title() if name.isupper() else name)


# Title fit for the stream cards, narrower than the add-ons' windows: the
# skin font here ran wider and Kodi in Arabic cut the overflow from the START
# ("sion 2025 ..." for "Obsession 2025 ..."), screenshot 2026-10-29.
_TITLE_PX = 600

# size buckets in the filter menu (GB, string id)
_SIZES = ((0, 5, 30830), (5, 15, 30831), (15, 40, 30832), (40, 1e9, 30833))
# estimated bitrate buckets (Mbit/s, string id)
_BITRATES = ((40, 1e9, 30837), (20, 40, 30838), (10, 20, 30839), (0, 10, 30840))


def _size(item):
    try:
        return float(item.get('size') or 0)
    except Exception:
        return 0.0


def _row_key(item):
    h = str(item.get('hash') or '').strip().lower()
    if h:
        return 'h:' + h
    return 'n:%s|%s' % (_clean(item.get('name') or item.get('display_name')).lower(), _clean(item.get('size_label')))


def merge(session):
    """One row per release: {'item', 'refs': [(key, index)], 'q', 'group', 'size', 'order'}."""
    rows, order = {}, 0
    with session.lock:
        snapshot = [(key, list(session.state.get(key, {}).get('results') or [])) for key, _a, _n, _t, _ok in session.addons]
    for key, results in snapshot:
        for idx, item in enumerate(results):
            if not isinstance(item, dict) or 'Uncached' in str(item.get('cache_provider', '')):
                continue
            rk = _row_key(item)
            row = rows.get(rk)
            if row is None:
                q = _quality(item)
                rows[rk] = {'item': item, 'refs': [(key, idx)], 'q': q, 'group': _group(q),
                            'size': _size(item), 'order': order}
                order += 1
            elif all(k != key for k, _i in row['refs']):
                row['refs'].append((key, idx))
    out = list(rows.values())
    out.sort(key=lambda r: (_QRANK.get(r['group'], 9), r['q'] != r['group'], -r['size'], r['order']))
    return out


# ───────────────────────── the window ─────────────────────────

class SearchWindow(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.session = kwargs['session']
        self.meta = kwargs.get('meta') or {}
        self.tags = {key: (name, tag) for key, _a, name, tag, _ok in self.session.addons}
        self.rows, self.shown = [], []
        self.f_addon, self.f_quality = None, None
        self.f_service = None         # 4.5.9: service chip (RD / AD / PM ...)
        self.chips = []
        self.picked = None
        self.ui_lock = threading.RLock()
        self.ready = False
        self.focused_key = None
        self.runtime = 0              # minutes, from TMDb: bitrate = size / running time
        self.filters = []            # filter menu (RIGHT / "Filter" chip): [{'kind', 'value', 'label'}]
        self._badge_cache = {}

    # ---- life cycle ----
    def onInit(self):
        th = _theme()
        if th:
            try:
                th.lucent_window(self, self.meta, fanart=self.meta.get('fanart', ''), clearlogo=self.meta.get('clearlogo', ''))
            except Exception as e:
                _log('window meta: %s' % e)
        self.setProperty('abs.heading', T(30817))
        self.setProperty('abs.addons_heading', T(30818))
        # always: besides any missing art / plot it brings the running time
        threading.Thread(target=self._fill_meta, name='abs_meta').start()
        self.ready = True
        self.session.listener = self.refresh
        self.refresh()
        self._focus(CHIPS)
        if not self.session.started_threads:
            self.session.started_threads = True
            self.session.start()

    def close(self):
        self.session.closed = True
        super().close()

    def _fill_meta(self):
        extra = tmdb_window_meta(self.session.media)
        if not extra or self.session.closed:
            return
        try:
            runtime = int(extra.pop('runtime', 0) or 0)
        except Exception:
            runtime = 0
        if runtime > 0 and not self.runtime:
            self.runtime = runtime
            _log('running time %d min - bitrate estimates on' % runtime)
            with self.ui_lock:
                self.shown = []               # rebuild the cards with the estimate
                self._chips()
                self._rows()
        meta = dict(self.meta)
        for k, v in extra.items():
            if not meta.get(k):
                meta[k] = v
        self.meta = meta
        th = _theme()
        if th:
            try:
                th.lucent_window(self, meta, fanart=meta.get('fanart', ''), clearlogo=meta.get('clearlogo', ''))
            except Exception as e:
                _log('window meta: %s' % e)

    def _focus(self, cid):
        # no <defaultcontrol>: the chips are empty until onInit fills them, and
        # Kodi then logs "Control 2300 ... can't focus". Focus once they exist.
        for _ in range(40):
            try:
                self.setFocusId(cid)
                if self.getFocusId() == cid:
                    return
            except Exception:
                pass
            xbmc.sleep(25)

    # ---- building ----
    def refresh(self):
        if not self.ready or self.session.closed:
            return
        with self.ui_lock:
            self.rows = merge(self.session)
            self._status()
            self._chips()
            self._rows()

    def _status(self):
        st = self.session.state
        n = 0
        for key, _aid, name, _tag, ok in self.session.addons:
            n += 1
            s = st[key]
            if s['state'] == 'searching':
                text = T(30819)
            elif s['state'] == 'done':           # playable rows only (uncached left out)
                text = T(30820) % sum(1 for r in self.rows if any(k == key for k, _i in r['refs']))
            elif s['state'] == 'unsupported':
                text = T(30829)
            else:
                text = T(30821)
            self.setProperty('abs.s%d.key' % n, key)
            self.setProperty('abs.s%d.name' % n, name)
            self.setProperty('abs.s%d.state' % n, s['state'])
            self.setProperty('abs.s%d.status' % n, text)
        searching = sum(1 for s in st.values() if s['state'] == 'searching')
        active = len({k for r in self.rows for k, _i in r['refs']})
        if searching:
            self.setProperty('abs.subhead', T(30822) % searching)
            self.setProperty('abs.waitmsg', T(30828))
            self.setProperty('abs.empty', '')
        else:
            sub = T(30823) % (len(self.rows), active, int(time.time() - self.session.started))
            if self.filters:
                sub += '  ·  ' + T(30836) % ' + '.join(f['label'] for f in self.filters)
            self.setProperty('abs.subhead', sub)
            self.setProperty('abs.waitmsg', T(30824))
            self.setProperty('abs.empty', 'true')

    def _chip_defs(self):
        st = self.session.state
        chips = [('all', None, T(30825), len(self.rows), '', False)]
        for key, _aid, name, _tag, ok in self.session.addons:
            if not ok:
                continue
            count = sum(1 for r in self.rows if any(k == key for k, _i in r['refs']))
            chips.append(('addon', key, name, count, key, st[key]['state'] == 'searching'))
        for q in _QUALITIES:
            count = sum(1 for r in self.rows if r['group'] == q)
            if count:
                chips.append(('quality', q, q.replace('P', 'p'), count, '', False))
        # 4.5.9: one chip per debrid service, only when there are two or more
        svc = {}
        for r in self.rows:
            code = _row_service(r)
            if code:
                svc[code] = svc.get(code, 0) + 1
        if len(svc) > 1:
            for code in _SERVICE_ORDER:
                if code in svc:
                    chips.append(('service', code, code, svc[code], '', False))
        if self.rows:
            chips.append(('filter', None, T(30835), len(self.filters) or '', '', False))
        return chips

    def _chips(self):
        defs = self._chip_defs()
        ctl = self.getControl(CHIPS)
        same = [(d[0], d[1]) for d in defs] == [(d[0], d[1]) for d in self.chips]
        if not same:
            pos = ctl.getSelectedPosition()
            ctl.reset()
            for _d in defs:
                ctl.addItem(xbmcgui.ListItem(''))
            if 0 <= pos < len(defs):
                ctl.selectItem(pos)
        self.chips = defs
        for n, (kind, value, label, count, key, loading) in enumerate(defs):
            li = ctl.getListItem(n)
            li.setLabel(label)
            li.setLabel2('' if loading else str(count))
            li.setProperty('abs.key', key)
            li.setProperty('abs.loading', 'true' if loading else '')
            active = (kind == 'all' and not self.f_addon and not self.f_quality and not self.f_service
                      and not self.filters) or \
                     (kind == 'addon' and value == self.f_addon) or (kind == 'quality' and value == self.f_quality) or \
                     (kind == 'service' and value == self.f_service) or \
                     (kind == 'filter' and bool(self.filters))
            li.setProperty('abs.active', 'true' if active else '')

    def _chip_rows(self):
        out = []
        for r in self.rows:
            if self.f_addon and all(k != self.f_addon for k, _i in r['refs']):
                continue
            if self.f_quality and r['group'] != self.f_quality:
                continue
            if self.f_service and _row_service(r) != self.f_service:
                continue
            out.append(r)
        return out

    def _visible_rows(self):
        return [r for r in self._chip_rows() if all(self._match(r, f) for f in self.filters)]

    # ---- filter menu ----
    def _badges(self, row):
        item = row['item']
        found = self._badge_cache.get(id(item))
        if found is None:
            th = _theme()
            try:
                found = th.badges(item.get('extraInfo', ''), row['q']) if th else []
            except Exception:
                found = []
            self._badge_cache[id(item)] = found
        return found

    def _mbps(self, row):
        """Average bitrate estimate in Mbit/s: size x 8 / running time. None for
        season / show packs (one size for many episodes) or unknown size."""
        item = row['item']
        if not self.runtime or row['size'] <= 0:
            return None
        if item.get('package') or item.get('pack') or item.get('last_season'):
            return None
        return row['size'] * 8000.0 / (self.runtime * 60.0)

    def _match(self, row, f):
        kind, value, item = f['kind'], f['value'], row['item']
        if kind == 'bitrate':
            lo, hi = value
            rate = self._mbps(row)
            return rate is not None and lo <= rate < hi
        if kind == 'service':
            return _provider(item).upper() == value
        if kind == 'site':
            return _site(item).upper() == value
        if kind == 'size':
            lo, hi = value
            return row['size'] > 0 and lo <= row['size'] < hi       # unknown size fits no bucket
        if kind == 'title':
            name = _clean(item.get('display_name') or item.get('name')).upper()
            return all(w in name for w in value)
        if kind == 'info':
            have = self._badges(row)
            return all(w in have for w in value)
        return True

    def _filter_menu(self):
        th = _theme()
        if not th:
            return
        th._addon_root = lambda: ADDON_PATH.rstrip('/\\')       # AB Tools' own lucent_select.xml
        _t = th._t
        base = self._visible_rows()
        if not base and not self.filters:
            return
        choices = []                    # (label, kind, value, count)
        if self.filters:
            choices.append((_t('Show all results'), 'clear', None, len(self._chip_rows())))
        def counted(kind, value, label):
            n = sum(1 for r in base if self._match(r, {'kind': kind, 'value': value}))
            if 0 < n < len(base):       # a filter that keeps everything (or nothing) is no filter
                choices.append((label, kind, value, n))
        services = sorted({_provider(r['item']).upper() for r in base} - {''})
        for s in services:
            counted('service', s, _t('Show %s only') % _pretty(s))
        for lo, hi, sid in _SIZES:
            counted('size', (lo, hi), T(sid))
        if self.runtime:
            for lo, hi, sid in _BITRATES:
                counted('bitrate', (lo, hi), T(sid))
        sites = {}
        for r in base:
            s = _site(r['item']).upper()
            if s:
                sites[s] = sites.get(s, 0) + 1
        for s in sorted(sites, key=lambda k: -sites[k])[:12]:
            counted('site', s, _t('Source: %s') % s.title())
        choices.append((_t('Filter by title...'), 'title', None, None))
        choices.append((_t('Filter by info (HDR, Atmos ...)...'), 'info', None, None))
        pick = th.lucent_select(_t('Filter results'), [c[0] for c in choices], _t('%s results') % len(base),
                                counts=[c[3] for c in choices])
        if pick is None or pick < 0:
            return
        label, kind, value, _n = choices[pick]
        if kind == 'clear':
            self.filters = []
            return self._apply_filters()
        if kind == 'title':
            text = xbmcgui.Dialog().input(_t('Keywords (comma separated)'))
            words = [w.strip().upper() for w in (text or '').split(',') if w.strip()]
            if not words:
                return
            value, label = words, _t('Title: %s') % ', '.join(words)
        elif kind == 'info':
            present = []
            for r in base:
                for b in self._badges(r):
                    if b not in present:
                        present.append(b)
            present.sort(key=lambda b: th._RANK.get(b, 999))
            if not present:
                return
            sets = [set(self._badges(r)) for r in base]
            def live(checked):
                want = [present[c] for c in checked]
                pool = [s for s in sets if all(w in s for w in want)]
                out = {None: len(pool)}
                for i, b in enumerate(present):
                    out[i] = len(pool) if i in checked else sum(1 for s in pool if b in s)
                return out
            sel = th.lucent_select(_t('Filter by info'), present, multi=True,
                                   counts=[sum(1 for s in sets if b in s) for b in present], live=live)
            if not sel:
                return
            value = [present[n] for n in sel]
            label = ' + '.join(value)
        elif kind == 'service':
            label = _pretty(value)
        elif kind == 'site':
            label = value.title()
        new = self.filters + [{'kind': kind, 'value': value, 'label': label}]
        if not any(all(self._match(r, f) for f in new) for r in self._chip_rows()):
            xbmcgui.Dialog().notification(_t('Filter results'), _t('No results'), xbmcgui.NOTIFICATION_INFO, 2500)
            return
        self.filters = new
        _log('filter: %s' % ' + '.join(f['label'] for f in self.filters))
        self._apply_filters()

    def _apply_filters(self):
        with self.ui_lock:
            self.focused_key = None
            self._status()
            self._chips()
            self._rows()
        if self.shown:
            self._focus(LIST)
            try:
                self.getControl(LIST).selectItem(0)
            except Exception:
                pass

    def _rows(self):
        ctl = self.getControl(LIST)
        try:
            pos = ctl.getSelectedPosition()
            if 0 <= pos < len(self.shown):
                self.focused_key = _row_key(self.shown[pos]['item'])
        except Exception:
            pass
        shown = self._visible_rows()
        if [id(r['item']) for r in shown] == [id(r['item']) for r in self.shown] and \
                [len(r['refs']) for r in shown] == [len(r['refs']) for r in self.shown]:
            return
        items = [self._listitem(r) for r in shown]
        ctl.reset()
        if items:
            ctl.addItems(items)
        self.shown = shown
        if self.focused_key:
            for n, r in enumerate(shown):
                if _row_key(r['item']) == self.focused_key:
                    ctl.selectItem(n)
                    break
        if not shown and self.getFocusId() == LIST:
            self.setFocusId(CHIPS)

    def _listitem(self, row):
        th = _theme()
        item, q = row['item'], row['q']
        li = xbmcgui.ListItem(_clean(item.get('display_name') or item.get('name')))
        provider = _provider(item)
        site = _site(item)
        size = _clean(item.get('size_label'))
        meta = []
        rate = self._mbps(row)
        rate = ('~%d Mbps' % round(rate)) if rate else ''
        for part in (provider, size, rate, site):
            if part and part.upper() not in ('N/A', 'NA', 'NONE') and \
                    not any(part.upper() in m.upper() or m.upper() in part.upper() for m in meta):
                meta.append(part)
        ntags = min(len(row['refs']), 4)
        meta_px = 610 - ntags * 70
        title = _clean(item.get('display_name') or item.get('name'))
        props = {'lucent.quality': q, 'lucent.lowq': 'true' if q in ('CAM', 'SCR', 'TELE', 'HC') else '',
                 'lucent.uncached': '', 'lucent.res': '', 'lucent.icon': '',
                 'abs.svc': _service_code(provider)}
        if th:
            try:
                # too long: drop the site first, then the service name, keep
                # size and the bitrate estimate longest
                for drop in (site, provider, rate):
                    if len(meta) <= 1 or th._px('  ·  '.join(meta).upper()) <= meta_px:
                        break
                    if drop in meta:
                        meta.remove(drop)
                while len(meta) > 1 and th._px('  ·  '.join(meta).upper()) > meta_px:
                    meta.pop()
                props['lucent.title'] = th._fit(title, _TITLE_PX)
                props['lucent.meta'] = th._fit('  ·  '.join(meta), meta_px)
                # 4.5.7: Search All shows no coloured resolution flags and no
                # service/source icons - plain quality pill only (lucent.res /
                # lucent.icon stay empty). The Glass Theme of the four add-ons'
                # own source windows is unchanged.
                found = self._badges(row)
            except Exception:
                found = []
        else:
            props['lucent.title'], props['lucent.meta'], found = title, '  ·  '.join(meta), []
        for n in range(7):
            props['lucent.badge_%d' % (n + 1)] = found[n] if n < len(found) else ''
        for n in range(4):
            key = row['refs'][n][0] if n < len(row['refs']) else ''
            props['abs.tag_%d' % (n + 1)] = key
            props['abs.tagtxt_%d' % (n + 1)] = self.tags.get(key, ('', ''))[1] if key else ''
        li.setProperties(props)
        return li

    # ---- input ----
    def onClick(self, cid):
        if cid == CHIPS:
            pos = self.getControl(CHIPS).getSelectedPosition()
            if 0 <= pos < len(self.chips):
                kind, value = self.chips[pos][0], self.chips[pos][1]
                if kind == 'filter':
                    return self._filter_menu()
                with self.ui_lock:
                    if kind == 'all':
                        self.f_addon = self.f_quality = self.f_service = None
                    elif kind == 'addon':
                        self.f_addon = None if self.f_addon == value else value
                    elif kind == 'service':
                        self.f_service = None if self.f_service == value else value
                    else:
                        self.f_quality = None if self.f_quality == value else value
                    self.focused_key = None
                    self._chips()
                    self._rows()
                if self.shown:
                    self.setFocusId(LIST)
        elif cid == LIST:
            self._play(None)

    def onAction(self, action):
        aid = action.getId()
        if aid in _ACTION_BACK:
            if self.filters:                    # Back first drops the filter-menu filters
                self.filters = []
                return self._apply_filters()
            if self.getFocusId() == LIST and (self.f_addon or self.f_quality or self.f_service):
                self.setFocusId(CHIPS)          # first Back from a filtered list: back to the chips
                return
            self.close()
            return
        if aid in _ACTION_MENU and self.getFocusId() == LIST:
            self._play(choose=True)
        elif aid == _ACTION_RIGHT and self.getFocusId() == LIST:
            self._filter_menu()

    def _current(self):
        pos = self.getControl(LIST).getSelectedPosition()
        return self.shown[pos] if 0 <= pos < len(self.shown) else None

    def _play(self, choose=None):
        row = self._current()
        if not row:
            return
        refs = list(row['refs'])
        if choose and len(refs) > 1:
            pick = xbmcgui.Dialog().contextmenu([T(30826) % self.tags[k][0] for k, _i in refs])
            if pick < 0:
                return
            refs = [refs[pick]]
        self.picked = refs[0]
        self.close()


# ───────────────────────── entry ─────────────────────────

def _focused_meta(tmdb_id):
    """Logo / fanart / plot of the item TMDbHelper was started from."""
    info = xbmc.getInfoLabel
    ids = {info(i).strip() for i in ('ListItem.UniqueID(tmdb)', 'ListItem.Property(tmdb_id)',
                                     'ListItem.UniqueID(tvshow.tmdb)', 'ListItem.Property(tvshow.tmdb_id)')}
    if not tmdb_id or tmdb_id not in ids:
        return {}
    return {'clearlogo': info('ListItem.Art(clearlogo)') or info('ListItem.Art(tvshow.clearlogo)'),
            'fanart': info('ListItem.Art(fanart)') or info('ListItem.Art(tvshow.fanart)'),
            'plot': info('ListItem.Plot'), 'rating': info('ListItem.Rating'), 'mpaa': info('ListItem.Mpaa'),
            'genre': info('ListItem.Genre').replace(' / ', ', '), 'year': info('ListItem.Year'),
            'tvshowtitle': info('ListItem.TVShowTitle'), 'title': info('ListItem.Title'),
            'imdb': info('ListItem.UniqueID(imdb)') or info('ListItem.IMDBNumber'),
            'show_imdb': info('ListItem.UniqueID(tvshow.imdb)') or info('ListItem.Property(tvshow.imdb_id)'),
            'tvdb': info('ListItem.UniqueID(tvdb)'), 'show_tvdb': info('ListItem.UniqueID(tvshow.tvdb)'),
            'premiered': info('ListItem.Premiered')}


def run(params):
    media_type = 'episode' if params.get('media_type') in ('episode', 'tv', 'tvshow') else 'movie'
    tmdb_id = str(params.get('tmdb_id') or params.get('tmdb') or '').strip()
    if not tmdb_id:
        _log('no tmdb_id in %s' % params, xbmc.LOGWARNING)
        return
    media = {'media_type': media_type, 'tmdb_id': tmdb_id}
    if media_type == 'episode':
        media['season'] = str(params.get('season', ''))
        media['episode'] = str(params.get('episode', ''))
    addons = available_addons()
    if not any(ok for *_x, ok in addons):
        xbmcgui.Dialog().ok('ABUKARIM TOOLS', T(30827))
        return
    focused = _focused_meta(tmdb_id)
    meta = {k: v for k, v in params.items() if v and k in ('title', 'tvshowtitle', 'year', 'plot', 'fanart', 'clearlogo', 'ep_name')}
    if params.get('showname') and not meta.get('tvshowtitle'):
        meta['tvshowtitle'] = params['showname']
    # the focused item's own labels win for names: a title with "&" arrives cut from TMDbHelper's URL
    for k in ('title', 'tvshowtitle'):
        if focused.get(k):
            meta[k] = focused[k]
    for k, v in focused.items():
        if v and not meta.get(k):
            meta[k] = v
    # names and other ids for Umbrella (it scrapes by title / IMDb id)
    if media_type == 'episode':
        imdb = focused.get('show_imdb') or params.get('imdb') or ''
        tvdb = focused.get('show_tvdb') or params.get('tvdb') or ''
    else:
        imdb = params.get('imdb') or focused.get('imdb') or ''
        tvdb = ''
    media.update({'title': meta.get('title', ''), 'tvshowtitle': meta.get('tvshowtitle', ''),
                  'year': str(params.get('year') or meta.get('year') or ''), 'imdb': imdb if str(imdb).startswith('tt') else '',
                  'tvdb': tvdb, 'premiered': params.get('premiered') or focused.get('premiered') or ''})
    for k in ('imdb', 'show_imdb', 'tvdb', 'show_tvdb', 'premiered'):
        meta.pop(k, None)
    meta.update({'media_type': media_type, 'tmdb_id': tmdb_id})
    if media_type == 'episode':
        meta.update({'season': media['season'], 'episode': media['episode']})
        if meta.get('tvshowtitle'):          # lucent_window: title = show, ep_name = episode
            meta.setdefault('ep_name', meta.get('title', ''))
            meta['title'] = meta['tvshowtitle']
    session = Session(media, addons)
    win = SearchWindow('ab_search.xml', ADDON_PATH, 'Default', '1080i', session=session, meta=meta)
    win.doModal()
    picked = win.picked
    del win
    session.closed = True
    if not picked:
        return
    key, index = picked
    aid = dict((k, a) for k, a, _n, _t, _ok in addons)[key]
    url = session.url(key, aid, 'play', index)
    _log('play: %s' % url)
    xbmc.executebuiltin('RunPlugin(%s)' % url)
