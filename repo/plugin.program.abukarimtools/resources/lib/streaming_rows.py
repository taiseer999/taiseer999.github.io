# -*- coding: utf-8 -*-
"""
streaming_rows.py - ABUKARIM TOOLS (4.6.14)

"AF3: Streaming Services" (Setup & Install): rows of the streaming services
of a country on the Arctic Fuse 3 HOME page, after the streaming rows of the
Lucent skin by djdirty60 (1.31.42 / 1.31.43) - built only with TMDb Helper,
no Lucent add-on:

  - one row of service logos: TMDb Helper's own info=watch_providers list,
    limited to the picked services through its provider_allowlist setting
    (a click opens that service's titles in TMDb Helper);
  - per picked service a row of its popular movies and / or series:
    info=discover&with_watch_providers=<id>&watch_region=<country>.

The rows are widget items appended to the AF3 home widgets file
(script.skinvariables nodes, skinvariables-shortcut-homewidgets.json), like
the anime rows of trakt_hubs.py. Everything written carries a guid starting
with "guid-abks"; picking no service removes exactly those rows and puts
TMDb Helper's previous allowlist back. ensure() (called from
trakt_hubs.ensure at boot) re-appends the rows - without network - when the
home file was replaced wholesale.
"""
import json
import os
import urllib.parse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

TMDBH = 'plugin.video.themoviedb.helper'
AF3_ID = 'skin.arctic.fuse.3'
TITLE = 'ABUKARIM TOOLS'
PREFIX = 'guid-abks'
_DATA = xbmcvfs.translatePath('special://profile/addon_data/')
NODES = os.path.join(_DATA, 'script.skinvariables', 'nodes', AF3_ID)
W_HOME = 'skinvariables-shortcut-homewidgets.json'
STATE_FILE = os.path.join(_DATA, 'plugin.program.abukarimtools', 'streaming_rows.json')
WIDGET_SUFFIX = '&widget=true&reload=$INFO[Window(Home).Property(TMDbHelper.Widgets.Reload)]'
LOGO = 'https://image.tmdb.org/t/p/w300%s'
STYLE = {'movie': 'Flyer', 'tv': 'Landscape'}

# country code, English, Arabic (Modern Standard Arabic)
REGIONS = (('JO', 'Jordan', 'الأردن'), ('SA', 'Saudi Arabia', 'السعودية'), ('AE', 'United Arab Emirates', 'الإمارات'),
           ('KW', 'Kuwait', 'الكويت'), ('QA', 'Qatar', 'قطر'), ('BH', 'Bahrain', 'البحرين'), ('OM', 'Oman', 'عُمان'),
           ('EG', 'Egypt', 'مصر'), ('LB', 'Lebanon', 'لبنان'), ('IQ', 'Iraq', 'العراق'), ('MA', 'Morocco', 'المغرب'),
           ('DZ', 'Algeria', 'الجزائر'), ('TN', 'Tunisia', 'تونس'), ('US', 'United States', 'الولايات المتحدة'),
           ('GB', 'United Kingdom', 'المملكة المتحدة'), ('CA', 'Canada', 'كندا'), ('DE', 'Germany', 'ألمانيا'),
           ('FR', 'France', 'فرنسا'), ('NL', 'Netherlands', 'هولندا'), ('TR', 'Turkey', 'تركيا'))

# TMDb Helper's 'language' setting is an index into this table (its
# addon/consts.py LANGUAGES, 6.19.x); the country is the last two letters.
_TMDBH_LANGUAGES = (
    'ar-AE', 'ar-SA', 'be-BY', 'bg-BG', 'bn-BD', 'ca-ES', 'ch-GU', 'cs-CZ', 'da-DK', 'de-AT', 'de-CH',
    'de-DE', 'el-GR', 'en-AU', 'en-CA', 'en-GB', 'en-IE', 'en-NZ', 'en-US', 'eo-EO', 'es-ES', 'es-MX',
    'et-EE', 'eu-ES', 'fa-IR', 'fi-FI', 'fr-CA', 'fr-FR', 'gl-ES', 'he-IL', 'hi-IN', 'hu-HU', 'id-ID',
    'it-IT', 'ja-JP', 'ka-GE', 'kk-KZ', 'kn-IN', 'ko-KR', 'lt-LT', 'lv-LV', 'ml-IN', 'ms-MY', 'ms-SG',
    'nb-NO', 'nl-NL', 'no-NO', 'pl-PL', 'pt-BR', 'pt-PT', 'ro-RO', 'ru-RU', 'si-LK', 'sk-SK', 'sl-SI',
    'sq-AL', 'sr-RS', 'sv-SE', 'ta-IN', 'te-IN', 'th-TH', 'tl-PH', 'tr-TR', 'uk-UA', 'vi-VN', 'zh-CN',
    'zh-HK', 'zh-TW', 'zu-ZA')


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools Streaming] %s' % msg, level)


def _arabic():
    try:
        return xbmc.getLanguage(xbmc.ISO_639_1) == 'ar'
    except Exception:
        return False


# ───────────────────────── state ─────────────────────────

def _load():
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(data):
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    except Exception as e:
        _log('state not saved: %s' % e, xbmc.LOGWARNING)


# ───────────────────────── TMDb ─────────────────────────

def _tmdbh():
    try:
        return xbmcaddon.Addon(TMDBH)
    except Exception:
        return None


def tmdbh_region():
    """Country TMDb Helper uses (from its language setting), else 'US'."""
    a = _tmdbh()
    try:
        idx = int(a.getSetting('language') or 0) if a else 0
    except Exception:
        idx = 0
    if 0 < idx < len(_TMDBH_LANGUAGES):            # TMDb Helper reads 0 as en-US
        return _TMDBH_LANGUAGES[idx][-2:]
    return 'US'


def fetch_providers(region):
    """[{'id', 'name', 'logo', 'prio', 'types'}] for movies and series of a
    country, most prominent first. [] on any network problem."""
    from resources.lib.ab_search import _tmdb
    lang = 'ar-%s' % region if _arabic() else 'en-US'
    found = {}
    for kind in ('movie', 'tv'):
        try:
            res = _tmdb('watch/providers/%s?watch_region=%s' % (kind, region), lang).get('results') or []
        except Exception as e:
            _log('providers %s %s failed: %s' % (kind, region, e), xbmc.LOGWARNING)
            continue
        for r in res:
            pid = r.get('provider_id')
            if not pid:
                continue
            prio = (r.get('display_priorities') or {}).get(region, r.get('display_priority', 999))
            cur = found.setdefault(pid, {'id': pid, 'name': r.get('provider_name') or str(pid),
                                         'logo': r.get('logo_path') or '', 'prio': prio, 'types': []})
            cur['prio'] = min(cur['prio'], prio)
            cur['types'].append(kind)
    return sorted(found.values(), key=lambda p: (p['prio'], p['name'].lower()))


# ───────────────────────── home widgets file ─────────────────────────

def _home():
    return os.path.join(NODES, W_HOME)


def _ours(item):
    return isinstance(item, dict) and str(item.get('guid') or '').startswith(PREFIX)


def _safe(text):
    """Same XML / format-safe label rule as trakt_hubs (skinvariables)."""
    from resources.lib.trakt_hubs import _clean
    return _clean(text)


def _discover(p, kind, region):
    q = urllib.parse.quote
    return ('plugin://%s/?info=discover&tmdb_type=%s&with_watch_providers=%s&watch_region=%s'
            '&with_id=True&plugin_category=%s' % (TMDBH, kind, p['id'], region, q(p['name'], safe='')))


def rows(state):
    """Widget items for the saved picks (no network)."""
    region, kinds, picks = state.get('region') or 'US', state.get('kinds') or ['movie', 'tv'], state.get('services') or []
    if not picks:
        return []
    # TMDb Helper lists the services of ONE type: movies only when every pick
    # has movies there (Shahid VIP, for one, is listed for series only)
    logo_kind = 'movie' if 'movie' in kinds and all('movie' in (p.get('types') or ['movie']) for p in picks) else 'tv'
    out = [{'label': _safe(T(30867)), 'icon': 'special://skin/extras/icons/tv.png',
            'path': 'plugin://%s/?info=watch_providers&tmdb_type=%s%s' % (TMDBH, logo_kind, WIDGET_SUFFIX),
            'target': 'videos', 'guid': '%s-logos' % PREFIX, 'widget_style': 'Square'}]
    for p in picks:
        for kind in ('movie', 'tv'):
            if kind not in kinds or (p.get('types') and kind not in p['types']):
                continue
            out.append({'label': _safe(T(30868 if kind == 'movie' else 30869) % p['name']),
                        'icon': LOGO % p['logo'] if p.get('logo') else 'special://skin/extras/icons/tv.png',
                        'path': _discover(p, kind, region) + WIDGET_SUFFIX,
                        'target': 'videos', 'guid': '%s-%s-%s' % (PREFIX, kind, p['id']),
                        'widget_style': STYLE[kind]})
    return out


def _write_home(items):
    """Our old rows out, items appended. True when the file changed, None when
    there is no AF3 home widgets file."""
    path = _home()
    if not os.path.isfile(path):
        _log('%s not found' % W_HOME, xbmc.LOGWARNING)
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            before = f.read()
        data = json.loads(before)
        if not isinstance(data, list):
            return None
    except Exception as e:
        _log('%s unreadable: %s' % (W_HOME, e), xbmc.LOGWARNING)
        return None
    data = [it for it in data if not _ours(it)] + list(items)
    text = json.dumps(data, ensure_ascii=False, indent=4)
    if text == before:
        return False
    tmp = path + '.abk.part'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(text)
    os.replace(tmp, path)
    return True


def _set_allowlist(state, picks):
    """TMDb Helper's provider list shows only the picked services; the value
    it had before is kept and put back when the rows are removed."""
    a = _tmdbh()
    if not a:
        return
    try:
        cur = a.getSetting('provider_allowlist')
        if picks:
            if 'prev_allowlist' not in state:
                state['prev_allowlist'] = cur
            a.setSetting('provider_allowlist', ' | '.join(p['name'] for p in picks))
        elif 'prev_allowlist' in state:
            a.setSetting('provider_allowlist', state.pop('prev_allowlist') or '')
    except Exception as e:
        _log('allowlist not set: %s' % e, xbmc.LOGWARNING)


def ensure():
    """Boot: picks saved but the home file lost our rows (restore, Widgets
    Layout, a skin profile) -> append them again. Returns files written."""
    st = _load()
    if not st.get('services') or not os.path.isfile(_home()):
        return []
    try:
        with open(_home(), 'r', encoding='utf-8') as f:
            if PREFIX in f.read():
                return []
    except Exception:
        return []
    return [W_HOME] if _write_home(rows(st)) else []


# ───────────────────────── dialogs ─────────────────────────

def _pick_region(current):
    ar = _arabic()
    codes = [c for c, _e, _a in REGIONS]
    if current not in codes:
        codes.insert(0, current)
    labels = [next(((a if ar else e) for c2, e, a in REGIONS if c2 == c), c) + '  (%s)' % c for c in codes]
    pick = xbmcgui.Dialog().select(T(30861), labels, preselect=codes.index(current))
    return codes[pick] if pick >= 0 else None


def _pick_services(provs, cur_ids):
    items, pre = [], []
    for i, p in enumerate(provs):
        li = xbmcgui.ListItem(p['name'], offscreen=True)
        if p['logo']:
            li.setArt({'icon': LOGO % p['logo'], 'thumb': LOGO % p['logo']})
        items.append(li)
        if p['id'] in cur_ids:
            pre.append(i)
    sel = xbmcgui.Dialog().multiselect(T(30862), items, preselect=pre, useDetails=True)
    return None if sel is None else [provs[i] for i in sel]


def _pick_kinds(current):
    opts = ((['movie', 'tv'], 30864), (['movie'], 30865), (['tv'], 30866))
    pre = next((i for i, (k, _l) in enumerate(opts) if k == current), 0)
    pick = xbmcgui.Dialog().select(T(30863), [T(l) for _k, l in opts], preselect=pre)
    return opts[pick][0] if pick >= 0 else None


def _rebuild():
    try:
        from resources.lib import trakt_hubs
        trakt_hubs._rebuild()
    except Exception as e:
        _log('rebuild failed: %s' % e, xbmc.LOGWARNING)


def run():
    if not os.path.isdir(xbmcvfs.translatePath('special://home/addons/%s/' % AF3_ID)):
        xbmcgui.Dialog().ok(TITLE, T(30440))          # AF3 is not installed
        return
    if not _tmdbh():
        xbmcgui.Dialog().ok(TITLE, T(30874))
        return
    if not os.path.isfile(_home()):
        xbmcgui.Dialog().ok(TITLE, T(30873))
        return
    st = _load()
    region = _pick_region(st.get('region') or tmdbh_region())
    if not region:
        return
    progress = xbmcgui.DialogProgress()
    progress.create(T(30860), T(30861) + ': ' + region)
    try:
        provs = fetch_providers(region)
    finally:
        progress.close()
    if not provs:
        xbmcgui.Dialog().ok(TITLE, T(30872))
        return
    cur_ids = {p['id'] for p in st.get('services') or []} if st.get('region') == region else set()
    picks = _pick_services(provs, cur_ids)
    if picks is None:
        return
    if picks:
        kinds = _pick_kinds(st.get('kinds') or ['movie', 'tv'])
        if kinds is None:
            return
    else:
        kinds = st.get('kinds') or ['movie', 'tv']
    st.update({'region': region, 'kinds': kinds,
               'services': [{k: p[k] for k in ('id', 'name', 'logo', 'types')} for p in picks]})
    _set_allowlist(st, picks)
    _save(st)
    items = rows(st)
    changed = _write_home(items)
    _log('region %s, %d service(s), kinds %s -> %d row(s), file %s'
         % (region, len(picks), '+'.join(kinds), len(items), 'written' if changed else 'unchanged'))
    if changed:
        _rebuild()
    msg = (T(30870) % len(items)) if items else T(30871)
    xbmcgui.Dialog().notification(TITLE, msg, xbmcgui.NOTIFICATION_INFO, 4000)
