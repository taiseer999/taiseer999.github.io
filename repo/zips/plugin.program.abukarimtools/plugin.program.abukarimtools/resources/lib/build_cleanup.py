# -*- coding: utf-8 -*-
"""
build_cleanup.py - Maintenance > Clean Unused Items (3.4.28).

Finds what the build no longer uses and removes only what the user ticks:

  * add-ons in special://home/addons that nothing uses any more:
      - script.module.* / library scripts (xbmc.python.module, or
        xbmc.python.script with no <provides>)
      - resource.* (kodi.resource.*: images, fonts, uisounds, languages...)
      - context.* menus whose target add-on is gone
      - metadata.* scrapers / scraper libraries
    "Used" = required (also optionally) by a used add-on, or named anywhere
    in a used add-on's files, its addon_data (settings.xml, json, sqlite),
    guisettings / sources / favourites / keymaps, or the video library's
    scraper column. Resolved as a fixpoint, so a module used only by another
    unused module goes too. Add-ons with a service, plugin source, skin,
    repository, binary or <provides> are never candidates.
  * userdata: old sources.xml copies (sources.xml.bak, sources_old.xml ...).
  * addon_data folders of add-ons that are not installed (scripts, skins,
    resources, contexts, scrapers pre-ticked; plugin/service data - it can
    hold logins/tokens - listed but NOT pre-ticked).
  * script.skinshortcuts / script.skinvariables files and folders that
    belong to a skin that is not installed (skin.x.hash, skin.x.properties,
    skin.x-mainmenu.DATA.xml, skin.x.userdata.json, nodes/skin.x/ ...).

Conditional rules (3.4.29) - removed even though they are services/scripts
the generic scan never offers, unless an add-on still in use requires them:
  * script.skin.info.service      - when Arctic Zephyr Rounded is not installed
  * AZR companions (id/name with "zephyr", or "Day and Night") - same
  * script.reboottoandroidtv      - when the box is not CoreELEC
  * anything with "bingie" in its id - when no Bingie skin is installed
  These are disabled through JSON-RPC first so a running service stops.

Installed checks are folder based (special://home + special://xbmc addons),
never the add-on manager - same rule as menu_reconcile (3.2.19).
"""

import os
import re
import shutil
import sqlite3
import xml.etree.ElementTree as ET

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

HOME_ADDONS = xbmcvfs.translatePath('special://home/addons/')
SYS_ADDONS = xbmcvfs.translatePath('special://xbmc/addons/')
USERDATA = xbmcvfs.translatePath('special://profile/')
ADDON_DATA = os.path.join(USERDATA, 'addon_data')
DATABASE = os.path.join(USERDATA, 'Database')
PACKAGES = os.path.join(HOME_ADDONS, 'packages')

SELF_ID = 'plugin.program.abukarimtools'

# Never offered for removal, even if no reference is found (their users keep
# the choice in places a text scan cannot see reliably).
KEEP = {
    SELF_ID,
    'plugin.program.ABUKARIMwizard',
    'script.module.acctmgr',
    'script.module.abscrapers',
}

# Programs that are only skin helpers: offered like any module when no
# add-on in use requires or calls them (3.4.30).
SKIN_HELPERS = {'script.skinshortcuts', 'script.globalsearch'}

# Extension points a removable add-on may have. Anything else (service,
# pluginsource, skin, repository, pvr, inputstream, provides...) => kept.
_ALLOWED_EXT = ('xbmc.addon.metadata', 'kodi.addon.metadata',
                'xbmc.python.module', 'xbmc.python.script',
                'xbmc.python.library', 'kodi.context.item')
_ALLOWED_EXT_PREFIX = ('kodi.resource.', 'xbmc.metadata.scraper.')

_SCAN_EXT = ('.py', '.xml', '.json', '.txt', '.ini', '.properties',
             '.db', '.sqlite', '.sqlite3', '.cfg', '.conf', '.js')
_MAX_SCAN = 40 * 1024 * 1024

_SKIN_DATA_ADDONS = ('script.skinshortcuts', 'script.skinvariables')

# addon_data prefixes ticked by default; others (plugin./service.) are shown
# unticked because they may hold account logins.
_DATA_PRESELECT = ('script.', 'skin.', 'resource.', 'context.', 'metadata.')

# kind -> label id
K_MODULE, K_SCRIPT, K_RESOURCE, K_CONTEXT, K_SCRAPER = 'module', 'script', 'resource', 'context', 'scraper'
K_DATA, K_SKINLEFT, K_SOURCES = 'data', 'skinleft', 'sources'
K_ADDON = 'addon'
_ADDON_KINDS = (K_MODULE, K_SCRIPT, K_RESOURCE, K_CONTEXT, K_SCRAPER, K_ADDON)
_KIND_LABEL = {K_ADDON: 30790, K_MODULE: 30791, K_SCRIPT: 30792, K_RESOURCE: 30793,
               K_CONTEXT: 30794, K_SCRAPER: 30795, K_DATA: 30796,
               K_SKINLEFT: 30797, K_SOURCES: 30798}


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools Cleanup] %s' % msg, level)


# ── add-on discovery ─────────────────────────────────────────────────────────
class _Addon(object):
    __slots__ = ('id', 'name', 'path', 'system', 'requires', 'exts', 'provides', 'kind')

    def __init__(self, aid, path, system):
        self.id = aid
        self.name = ''
        self.path = path
        self.system = system
        self.requires = set()
        self.exts = []
        self.provides = False
        self.kind = None


def _parse(folder, system):
    xml_path = os.path.join(folder, 'addon.xml')
    try:
        root = ET.parse(xml_path).getroot()
    except Exception:
        return None
    aid = root.get('id')
    if not aid:
        return None
    a = _Addon(aid, folder, system)
    a.name = re.sub(r'\[/?[A-Z]+[^\]]*\]', '', root.get('name') or '').strip()
    for imp in root.iter('import'):
        dep = imp.get('addon')
        if dep:
            a.requires.add(dep)
    for ext in root.iter('extension'):
        point = ext.get('point') or ''
        a.exts.append(point)
        prov = ext.find('provides')
        if prov is not None and (prov.text or '').strip():
            a.provides = True
    return a


def _list_addons(base, system):
    out = {}
    try:
        names = os.listdir(base)
    except OSError:
        return out
    for name in names:
        if name in ('packages', 'temp'):
            continue
        folder = os.path.join(base, name)
        if not os.path.isfile(os.path.join(folder, 'addon.xml')):
            continue
        a = _parse(folder, system)
        if a:
            out[a.id] = a
    return out


def _classify(a):
    """Kind of a removable add-on, or None if it is never a candidate."""
    if a.system or a.id in KEEP:
        return None
    if a.id in SKIN_HELPERS:
        return K_SCRIPT
    if a.provides:
        return None
    if a.id.startswith(('xbmc.', 'kodi.')):
        return None
    for p in a.exts:
        if p not in _ALLOWED_EXT and not p.startswith(_ALLOWED_EXT_PREFIX):
            return None
    pts = set(a.exts)
    if 'kodi.context.item' in pts:
        return K_CONTEXT
    if any(p.startswith('kodi.resource.') for p in pts):
        return K_RESOURCE
    if any(p.startswith('xbmc.metadata.scraper.') for p in pts) or a.id.startswith('metadata.'):
        return K_SCRAPER
    if 'xbmc.python.module' in pts:
        return K_MODULE
    if 'xbmc.python.script' in pts or 'xbmc.python.library' in pts:
        return K_SCRIPT
    return None


# ── conditional rules ────────────────────────────────────────────────────────
AZR_SKIN = 'skin.arctic.zephyr.rounded'


def _is_coreelec():
    if os.path.isdir('/etc/coreelec'):
        return True
    try:
        with open('/etc/os-release') as f:
            return any('coreelec' in line.lower() for line in f)
    except OSError:
        return False


def _forced(home, skins):
    """{addon id: reason} for add-ons removed by a conditional rule."""
    has_azr = any(s.startswith(AZR_SKIN) for s in skins)
    has_bingie = any('bingie' in s.lower() for s in skins)
    coreelec = _is_coreelec()
    out = {}
    for aid, a in home.items():
        if a.system or aid in KEEP or aid in skins:
            continue
        if not has_azr and (aid == 'script.skin.info.service' or _azr_companion(a)):
            out[aid] = 'Arctic Zephyr Rounded not installed'
        elif aid == 'script.reboottoandroidtv' and not coreelec:
            out[aid] = 'not CoreELEC'
        elif 'bingie' in aid.lower() and not has_bingie:
            out[aid] = 'Bingie skin not installed'
    return out


def _azr_companion(a):
    low_id, low_name = a.id.lower(), a.name.lower()
    if a.id.startswith('skin.') or any(p == 'xbmc.gui.skin' for p in a.exts):
        return False
    return ('zephyr' in low_id or 'zephyr' in low_name or 'zephir' in low_name
            or 'daynight' in low_id or 'day and night' in low_name)


def _disable(aid):
    try:
        import json
        xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1,
                                        'method': 'Addons.SetAddonEnabled',
                                        'params': {'addonid': aid, 'enabled': False}}))
    except Exception as exc:
        _log('disable %s: %r' % (aid, exc))


# ── reference scan ───────────────────────────────────────────────────────────
def _id_regex(ids):
    alts = b'|'.join(re.escape(i.encode('utf-8')) for i in sorted(ids, key=len, reverse=True))
    # not part of a longer id on either side
    return re.compile(b'(?<![A-Za-z0-9_.\\-])(' + alts + b')(?!\\.?[A-Za-z0-9_\\-])')


def _scan_tree(folder, rx, found, depth=8):
    if depth < 0:
        return
    try:
        entries = os.listdir(folder)
    except OSError:
        return
    for name in entries:
        p = os.path.join(folder, name)
        if os.path.isdir(p):
            if name in ('__pycache__', '.git'):
                continue
            _scan_tree(p, rx, found, depth - 1)
            continue
        if not name.lower().endswith(_SCAN_EXT):
            continue
        try:
            if os.path.getsize(p) > _MAX_SCAN:
                continue
            with open(p, 'rb') as f:
                data = f.read()
        except OSError:
            continue
        for m in rx.findall(data):
            found.add(m.decode('utf-8', 'ignore'))


def _userdata_refs(rx):
    found = set()
    for name in ('guisettings.xml', 'sources.xml', 'favourites.xml',
                 'advancedsettings.xml', 'profiles.xml', 'playercorefactory.xml',
                 'mediasources.xml', 'RssFeeds.xml'):
        _scan_file(os.path.join(USERDATA, name), rx, found)
    _scan_tree(os.path.join(USERDATA, 'keymaps'), rx, found, 2)
    _scan_tree(os.path.join(USERDATA, 'library'), rx, found, 3)
    _scan_tree(os.path.join(USERDATA, 'playlists'), rx, found, 3)
    return found


def _scan_file(p, rx, found):
    try:
        with open(p, 'rb') as f:
            for m in rx.findall(f.read()):
                found.add(m.decode('utf-8', 'ignore'))
    except OSError:
        pass


def _library_scrapers():
    """Scrapers set on library sources (MyVideos*.db path.strScraper)."""
    out = set()
    try:
        names = [n for n in os.listdir(DATABASE) if re.match(r'MyVideos\d+\.db$', n)]
    except OSError:
        return out
    for n in names:
        try:
            con = sqlite3.connect('file:%s?mode=ro' % os.path.join(DATABASE, n), uri=True, timeout=3)
            for (s,) in con.execute('SELECT DISTINCT strScraper FROM path WHERE strScraper IS NOT NULL'):
                if s:
                    out.add(s)
            con.close()
        except Exception as exc:
            _log('library scrapers %s: %r' % (n, exc))
    return out


# ── scan ─────────────────────────────────────────────────────────────────────
def _dir_size(p):
    if os.path.isfile(p):
        try:
            return os.path.getsize(p)
        except OSError:
            return 0
    total = 0
    for root, _dirs, files in os.walk(p):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def _human(n):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            return ('%d %s' % (n, unit)) if unit == 'B' else ('%.1f %s' % (n, unit))
        n /= 1024.0


def _skin_owner_installed(name, skins):
    """name starts with 'skin.' - does it belong to an installed skin?"""
    for sid in skins:
        if name == sid or (name.startswith(sid) and name[len(sid)] in '.-_ '):
            return True
    return False


def scan(progress=None):
    """Return a list of item dicts: kind, name, paths, size, preselect."""
    def step(pct, msg):
        if progress:
            progress.update(pct, msg)
            return not progress.iscanceled()
        return True

    if not step(5, T(30782)):
        return None
    home = _list_addons(HOME_ADDONS, False)
    system = _list_addons(SYS_ADDONS, True)
    installed = dict(system)
    installed.update(home)          # home overrides system (updated system add-on)
    for a in home.values():
        a.kind = _classify(a)
    skins = set(i for i, a in installed.items()
                if any(p == 'xbmc.gui.skin' for p in a.exts))
    forced = _forced(home, skins)
    candidates = set(a.id for a in home.values() if a.kind) - set(forced)
    if forced:
        _log('conditional: %s' % ', '.join('%s (%s)' % kv for kv in sorted(forced.items())))
    _log('%d home / %d system add-ons, %d candidates' % (len(home), len(system), len(candidates)))

    items = []
    used = set()
    refs = {}
    if candidates or forced:
        rx = _id_regex(candidates or ['\x00none\x00'])
        n = max(1, len(installed))
        for i, (aid, a) in enumerate(installed.items()):
            if aid in forced:
                continue
            if i % 15 == 0 and not step(10 + int(55.0 * i / n), '%s[CR]%s' % (T(30783), aid)):
                return None
            found = set()
            _scan_tree(a.path, rx, found)
            _scan_tree(os.path.join(ADDON_DATA, aid), rx, found, 4)
            found.discard(aid)
            refs[aid] = found

        if not step(70, T(30784)):
            return None
        root_refs = _userdata_refs(rx) | (_library_scrapers() & candidates)

        # fixpoint from everything that is not a candidate (forced ones are
        # never a source: what only they use becomes unused too)
        queue = [i for i in installed if i not in candidates and i not in forced]
        used = set(queue) | (root_refs & candidates)
        queue += list(root_refs & candidates)
        while queue:
            aid = queue.pop()
            a = installed.get(aid)
            nxt = set(refs.get(aid, ()))
            if a:
                nxt |= a.requires
            for d in nxt:
                if d not in used and d in installed and d not in forced:
                    used.add(d)
                    queue.append(d)

        for aid in sorted(forced):
            blockers = sorted(u for u in used if aid in getattr(installed.get(u), 'requires', ()))
            if blockers:
                _log('keeping %s (%s) - required by %s' % (aid, forced[aid], ', '.join(blockers)))
                continue
            a = home[aid]
            paths = [a.path]
            data = os.path.join(ADDON_DATA, aid)
            if os.path.isdir(data):
                paths.append(data)
            paths += _package_zips(aid)
            items.append({'kind': a.kind or K_ADDON, 'name': aid, 'paths': paths,
                          'size': sum(_dir_size(p) for p in paths), 'preselect': True,
                          'disable': True})

        for aid in sorted(candidates - used):
            a = home[aid]
            if a.kind == K_CONTEXT and not _context_target_missing(a, installed):
                continue   # stand-alone context menu that still works
            paths = [a.path]
            data = os.path.join(ADDON_DATA, aid)
            if os.path.isdir(data):
                paths.append(data)
            paths += _package_zips(aid)
            items.append({'kind': a.kind, 'name': aid, 'paths': paths,
                          'size': sum(_dir_size(p) for p in paths), 'preselect': True})

    if not step(80, T(30784)):
        return None
    removing = set(i['name'] for i in items)

    # userdata: old sources.xml copies
    try:
        for name in sorted(os.listdir(USERDATA)):
            low = name.lower()
            p = os.path.join(USERDATA, name)
            if low != 'sources.xml' and 'sources' in low and '.xml' in low and os.path.isfile(p):
                items.append({'kind': K_SOURCES, 'name': name, 'paths': [p],
                              'size': _dir_size(p), 'preselect': True})
    except OSError:
        pass

    # addon_data of add-ons that are not installed
    try:
        names = sorted(os.listdir(ADDON_DATA))
    except OSError:
        names = []
    for name in names:
        p = os.path.join(ADDON_DATA, name)
        if not os.path.isdir(p) or '.' not in name or name in installed or name in removing:
            continue
        items.append({'kind': K_DATA, 'name': name, 'paths': [p], 'size': _dir_size(p),
                      'preselect': name.startswith(_DATA_PRESELECT)})

    # skinshortcuts / skinvariables leftovers of skins that are not installed
    for owner in _SKIN_DATA_ADDONS:
        base = os.path.join(ADDON_DATA, owner)
        if owner not in installed or owner in removing or not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            for name in list(dirs) + files:
                if not name.startswith('skin.') or _skin_owner_installed(name, skins):
                    continue
                p = os.path.join(root, name)
                if name in dirs:
                    dirs.remove(name)   # whole folder goes, do not descend
                items.append({'kind': K_SKINLEFT,
                              'name': os.path.relpath(p, ADDON_DATA).replace('\\', '/'),
                              'paths': [p], 'size': _dir_size(p), 'preselect': True})
    step(100, '')
    return items


def _context_target_missing(a, installed):
    """A context item is unused when an add-on it points at is gone."""
    if any(d not in installed for d in a.requires
           if not d.startswith(('xbmc.', 'kodi.'))):
        return True
    rx = re.compile(br'(?:plugin://|RunScript\(|RunPlugin\(|RunAddon\(|Addon\(\s*[\'"]|id=[\'"])\s*'
                    br'((?:plugin|script|service)\.[A-Za-z0-9_.\-]+)')
    found = set()
    for root, _d, files in os.walk(a.path):
        for f in files:
            if f.endswith(('.py', '.xml')):
                try:
                    with open(os.path.join(root, f), 'rb') as h:
                        found |= set(m.decode('utf-8', 'ignore').rstrip('./')
                                     for m in rx.findall(h.read()))
                except OSError:
                    pass
    found.discard(a.id)
    return any(t not in installed for t in found)


def _package_zips(aid):
    out = []
    try:
        for n in os.listdir(PACKAGES):
            if n.startswith(aid + '-') and n.endswith('.zip'):
                out.append(os.path.join(PACKAGES, n))
    except OSError:
        pass
    return out


# ── delete ───────────────────────────────────────────────────────────────────
_SAFE_ROOTS = None


def _safe(p):
    global _SAFE_ROOTS
    if _SAFE_ROOTS is None:
        _SAFE_ROOTS = tuple(os.path.realpath(r) + os.sep for r in (HOME_ADDONS, USERDATA))
    rp = os.path.realpath(p)
    return rp.startswith(_SAFE_ROOTS) and rp + os.sep not in _SAFE_ROOTS


def _remove(p):
    if not _safe(p):
        _log('refusing to delete outside home: %s' % p, xbmc.LOGWARNING)
        return False
    try:
        if os.path.isdir(p) and not os.path.islink(p):
            shutil.rmtree(p)
        elif os.path.lexists(p):
            os.remove(p)
        return True
    except OSError as exc:
        _log('delete failed %s: %r' % (p, exc), xbmc.LOGWARNING)
        return False


# ── UI ───────────────────────────────────────────────────────────────────────
def run():
    dlg = xbmcgui.Dialog()
    dp = xbmcgui.DialogProgress()
    dp.create(T(30780), T(30781))
    try:
        items = scan(dp)
    except Exception as exc:
        _log('scan failed: %r' % exc, xbmc.LOGERROR)
        items = []
    finally:
        dp.close()
    if items is None:          # cancelled
        return
    if not items:
        dlg.ok(T(30780), T(30785))
        return

    order = [K_ADDON, K_MODULE, K_SCRIPT, K_RESOURCE, K_CONTEXT, K_SCRAPER, K_SOURCES, K_DATA, K_SKINLEFT]
    items.sort(key=lambda i: (order.index(i['kind']), i['name'].lower()))
    rows = []
    for it in items:
        li = xbmcgui.ListItem('[%s] %s' % (T(_KIND_LABEL[it['kind']]), it['name']),
                              _human(it['size']))
        rows.append(li)
    pre = [n for n, it in enumerate(items) if it['preselect']]
    chosen = dlg.multiselect('%s (%d)' % (T(30786), len(items)), rows,
                             preselect=pre, useDetails=False)
    if not chosen:
        return
    picked = [items[i] for i in chosen]
    total = sum(i['size'] for i in picked)
    if not dlg.yesno(T(30780), T(30787) % (len(picked), _human(total))):
        return

    dp = xbmcgui.DialogProgress()
    dp.create(T(30780), T(30788))
    done = failed = 0
    freed = 0
    removed_addons = False
    for n, it in enumerate(picked):
        dp.update(int(100.0 * n / max(1, len(picked))), '%s[CR]%s' % (T(30788), it['name']))
        if it.get('disable'):
            _disable(it['name'])
            xbmc.sleep(300)
        ok = all([_remove(p) for p in it['paths']])
        _log('%s %s (%s) %s' % ('removed' if ok else 'FAILED', it['name'], it['kind'], _human(it['size'])))
        if ok:
            done += 1
            freed += it['size']
            if it['kind'] in _ADDON_KINDS:
                removed_addons = True
        else:
            failed += 1
    dp.close()
    if removed_addons:
        xbmc.executebuiltin('UpdateLocalAddons')
    msg = T(30789) % (done, _human(freed))
    if failed:
        msg += '[CR]' + T(30799) % failed
    dlg.ok(T(30780), msg)
