# -*- coding: utf-8 -*-
"""
af3_shortcuts.py - "Widgets Layout" (ترتيب الودجتس): which AF3 menus and
widgets the box keeps. Shown in the Installation Wizard right after the
Add-on Portal, and from Setup & Install in the menu.

All its texts are ARABIC on purpose (also during setup, which runs Kodi in
English): the window uses the add-on's own Arabic-capable fonts and Kodi's
dialogs fall back to the Arabic arial.ttf the add-on installs.

    Light     leave userdata/addon_data/script.skinvariables as it is
    Moderate  replace it from ABUKARIM Wizard "No Wipe" Option 1
    Full      replace it from ABUKARIM Wizard "No Wipe" Option 2

Where the two zips come from - exactly what the wizard itself uses
(plugin.program.ABUKARIMwizard resources/lib/modules/addonvar.get_version):

    build file   uservar.buildfile of the installed wizard (Builds.txt)
    Option 1     "gui" of the build named like the wizard's 'buildname'
                 setting (= the wizard's "Patch GUI" entry)
    Option 2     "gui" of the build named "test"

Only the script.skinvariables part of the zip is used; nothing else in it is
extracted. The zip may be rooted at special://home (userdata/addon_data/...)
or at userdata (addon_data/...) - both are recognised.

"Replace" works per folder: every nodes/<skin>/ folder the zip carries is
emptied first and then written from the zip, every loose file the zip carries
is overwritten. Folders / files the zip does not carry (another skin's menus)
are left alone. The previous copy is zipped to
addon_data/plugin.program.abukarimtools/af3_shortcuts_backup/ (3 kept).
"""

import base64
import json
import os
import re
import shutil
import time
import zipfile
import urllib.request

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib.strings_map import STRINGS


def AR(sid):
    """Arabic text of a string id, whatever Kodi's UI language is."""
    pair = STRINGS.get(int(sid)) or ('', '')
    return pair[1] or pair[0]


WIZARD_ID = 'plugin.program.ABUKARIMwizard'
DEFAULT_BUILDFILE = ('https://raw.githubusercontent.com/taiseer999/'
                     'taiseer999.github.io/refs/heads/main/Builds.txt')
OPTION2_BUILD = 'test'                      # same hard-coded name as the wizard
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

LIGHT, MODERATE, FULL = 'light', 'moderate', 'full'
MODES = (LIGHT, MODERATE, FULL)

ADDON_DATA = xbmcvfs.translatePath('special://profile/addon_data/')
SV_DIR     = os.path.join(ADDON_DATA, 'script.skinvariables')
PROFILE    = os.path.join(ADDON_DATA, 'plugin.program.abukarimtools')
BACKUP_DIR = os.path.join(PROFILE, 'af3_shortcuts_backup')
STATE_FILE = os.path.join(PROFILE, 'af3_shortcuts.json')
AF3_ID     = 'skin.arctic.fuse.3'

_SV_RE = re.compile(r'(?:^|/)addon_data/script\.skinvariables/(.+)$')

# Set when Moderate/Full was applied in THIS run, so a skin profile applied
# later in the same setup (skin_profiles.apply_from_bytes) does not overwrite
# the shortcuts the user just picked. Process-local on purpose: the whole
# setup runs in one plugin invocation.
_SESSION_LOCK = False
_LAST_SKINS = []     # nodes/<skin> folders the last replace wrote


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools AF3Shortcuts] %s' % msg, level)


def session_locked():
    return _SESSION_LOCK


# ---------------------------------------------------------------------------
# build file -> option urls
# ---------------------------------------------------------------------------

def _wizard_path():
    return xbmcvfs.translatePath('special://home/addons/%s/' % WIZARD_ID)


def _maybe_b64(s):
    """The wizard accepts a base64 build-file url (addonvar.file_check)."""
    s = (s or '').strip()
    if s.startswith('http'):
        return s
    try:
        d = base64.b64decode(s).decode('utf-8').strip()
        if d.startswith('http'):
            return d
    except Exception:
        pass
    return s


def _buildfile():
    try:
        with open(os.path.join(_wizard_path(), 'uservar.py'), 'r',
                  encoding='utf-8') as f:
            m = re.search(r'''^\s*buildfile\s*=\s*['"]([^'"]+)['"]''',
                          f.read(), re.M)
        if m and m.group(1) not in ('', 'http://CHANGEME'):
            return _maybe_b64(m.group(1))
    except Exception as e:
        _log('uservar.py not readable (%s) - using the default build file' % e)
    return DEFAULT_BUILDFILE


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    return urllib.request.urlopen(req, timeout=timeout)


def _parse_builds(text):
    """Same three formats the wizard reads: JSON, XML, name="..." text."""
    if '"builds"' in text or "'builds'" in text:
        try:
            return [b for b in json.loads(text).get('builds', [])
                    if isinstance(b, dict)]
        except Exception:
            pass
    builds = []
    if '<name>' in text:
        for blk in re.findall(r'<build>(.*?)</build>', text, re.S) or [text]:
            b = {k: (v or '').strip() for k, v in
                 re.findall(r'<(name|version|gui|url)>(.*?)</\1>', blk, re.S)}
            if b.get('name'):
                builds.append(b)
        return builds
    # text format: blocks start at name="..."
    for blk in re.split(r'(?m)^(?=\s*name\s*=)', text):
        b = dict(re.findall(r'(?m)^\s*(\w+)\s*=\s*"(.*?)"\s*$', blk))
        if b.get('name'):
            builds.append(b)
    return builds


def _valid(u):
    return bool(u) and u.strip() not in ('http://', 'https://', 'http://CHANGEME')


def _wizard_buildname():
    try:
        return xbmcaddon.Addon(WIZARD_ID).getSetting('buildname') or ''
    except Exception:
        return ''


def option_url(mode):
    """Download url for MODERATE (Option 1) / FULL (Option 2), or None."""
    try:
        with _get(_buildfile()) as r:
            builds = _parse_builds(r.read().decode('utf-8', 'replace'))
    except Exception as e:
        _log('build file download failed: %s' % e, xbmc.LOGWARNING)
        return None
    if mode == FULL:
        for b in builds:
            if b.get('name') == OPTION2_BUILD and _valid(b.get('gui')):
                return b['gui'].strip()
        _log('no Option 2 ("%s" build gui) in the build file' % OPTION2_BUILD,
             xbmc.LOGWARNING)
        return None
    current = _wizard_buildname()
    for b in builds:
        if current and b.get('name') == current and _valid(b.get('gui')):
            return b['gui'].strip()
    # No build recorded by the wizard (or it has no gui): first real build.
    for b in builds:
        if b.get('name') != OPTION2_BUILD and _valid(b.get('gui')):
            _log('Option 1: wizard build "%s" not found - using "%s"'
                 % (current, b.get('name')))
            return b['gui'].strip()
    _log('no Option 1 (build gui) in the build file', xbmc.LOGWARNING)
    return None


# ---------------------------------------------------------------------------
# download + replace
# ---------------------------------------------------------------------------

def _download(url, dest, title):
    dp = xbmcgui.DialogProgress()
    dp.create(title, AR(30637))
    try:
        with _get(url, timeout=30) as r, open(dest, 'wb') as f:
            total = int(r.headers.get('content-length') or 0)
            done = 0
            while True:
                chunk = r.read(512 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if total:
                    dp.update(min(99, int(done * 100 / total)),
                              '%s[CR]%d / %d MB' % (AR(30637), done >> 20, total >> 20))
                else:
                    dp.update(0, '%s[CR]%d MB' % (AR(30637), done >> 20))
                if dp.iscanceled():
                    return False
        return True
    finally:
        dp.close()


def _members(zf):
    """[(ZipInfo, path relative to script.skinvariables)] - safe entries only."""
    out = []
    for info in zf.infolist():
        name = info.filename.replace('\\', '/')
        if info.is_dir() or name.startswith('__MACOSX'):
            continue
        m = _SV_RE.search(name)
        if not m:
            continue
        rel = m.group(1)
        parts = rel.split('/')
        if '..' in parts or rel.startswith('/') or not rel:
            continue
        out.append((info, rel))
    return out


def _backup():
    if not os.path.isdir(SV_DIR):
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    path = os.path.join(BACKUP_DIR, 'script.skinvariables-%s.zip'
                        % time.strftime('%Y%m%d-%H%M%S'))
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for dp, _dn, fns in os.walk(SV_DIR):
            for fn in fns:
                p = os.path.join(dp, fn)
                zf.write(p, os.path.relpath(p, ADDON_DATA).replace(os.sep, '/'))
    olds = sorted(f for f in os.listdir(BACKUP_DIR)
                  if f.startswith('script.skinvariables-'))
    for f in olds[:-3]:
        try:
            os.remove(os.path.join(BACKUP_DIR, f))
        except OSError:
            pass
    return path


def _replace_from_zip(zip_path):
    """Write the zip's script.skinvariables part. Returns files written."""
    with zipfile.ZipFile(zip_path) as zf:
        members = _members(zf)
        if not members:
            return 0
        # stage first, so a broken zip never leaves a half-replaced folder
        stage = SV_DIR + '.abk.new'
        shutil.rmtree(stage, ignore_errors=True)
        for info, rel in members:
            dest = os.path.join(stage, *rel.split('/'))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with zf.open(info) as s, open(dest, 'wb') as d:
                shutil.copyfileobj(s, d)
    bk = _backup()
    if bk:
        _log('previous skinvariables saved to %s' % bk)
    os.makedirs(SV_DIR, exist_ok=True)
    # nodes/<skin>/ folders carried by the zip are replaced as a whole
    global _LAST_SKINS
    _LAST_SKINS = []
    nodes = os.path.join(stage, 'nodes')
    if os.path.isdir(nodes):
        for skin in os.listdir(nodes):
            if os.path.isdir(os.path.join(nodes, skin)):
                _LAST_SKINS.append(skin)
                shutil.rmtree(os.path.join(SV_DIR, 'nodes', skin),
                              ignore_errors=True)
    written = 0
    for dp, _dn, fns in os.walk(stage):
        for fn in fns:
            src = os.path.join(dp, fn)
            dest = os.path.join(SV_DIR, os.path.relpath(src, stage))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            os.replace(src, dest)
            written += 1
    shutil.rmtree(stage, ignore_errors=True)
    return written


def _after_replace(skins):
    """Hide items for missing add-ons, then make every skin whose nodes were
    replaced really rebuild (skin_rebuild: the node files are not part of
    skinvariables' change check, so a plain rebuild call did nothing)."""
    try:
        from resources.lib import menu_reconcile
        menu_reconcile.run(rebuild=False)
    except Exception as e:
        _log('menu reconcile failed: %s' % e, xbmc.LOGWARNING)
    from resources.lib import skin_rebuild
    for skin in sorted(set(skins) | {AF3_ID}):
        skin_rebuild.force(skin)


def _save_state(mode, ok):
    try:
        os.makedirs(PROFILE, exist_ok=True)
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump({'mode': mode, 'ok': ok, 'time': int(time.time())}, f)
    except Exception:
        pass


def apply(mode):
    """Apply a choice. Returns True when the box ends up as requested."""
    global _SESSION_LOCK
    if mode not in (MODERATE, FULL):
        _log('Light - script.skinvariables left as it is')
        _save_state(LIGHT, True)
        return True
    label = AR(30633 if mode == MODERATE else 30635)
    title = '%s - %s' % (AR(30630), label)
    url = option_url(mode)
    if not url:
        xbmcgui.Dialog().ok(title, AR(30639))
        _save_state(mode, False)
        return False
    tmp = os.path.join(xbmcvfs.translatePath('special://temp/'),
                       'abk_af3_shortcuts.zip')
    try:
        if not _download(url, tmp, title):
            _log('%s: download cancelled' % mode)
            _save_state(mode, False)
            return False
        n = _replace_from_zip(tmp)
    except Exception as e:
        _log('%s failed: %s' % (mode, e), xbmc.LOGERROR)
        xbmcgui.Dialog().ok(title, AR(30639))
        _save_state(mode, False)
        return False
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    if not n:
        _log('%s: the zip has no addon_data/script.skinvariables' % mode,
             xbmc.LOGWARNING)
        xbmcgui.Dialog().ok(title, AR(30640))
        _save_state(mode, False)
        return False
    _log('%s: %d file(s) written to script.skinvariables' % (mode, n))
    _SESSION_LOCK = True
    _after_replace(_LAST_SKINS)
    _save_state(mode, True)
    xbmcgui.Dialog().notification(AR(30630), AR(30638) % label,
                                  xbmcgui.NOTIFICATION_INFO, 4000)
    return True


# ---------------------------------------------------------------------------
# the question - neon card window (same look as Skin Selection)
# ---------------------------------------------------------------------------

def _addon_path():
    return xbmcvfs.translatePath(
        xbmcaddon.Addon('plugin.program.abukarimtools').getAddonInfo('path'))


def current_mode():
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            st = json.load(f)
        return st.get('mode') if st.get('ok') else None
    except Exception:
        return None


_CARDS = (  # mode, label, description, note under the cards, icon
    (LIGHT,    30631, 30632, 30645, 'af3sc_light.png'),
    (MODERATE, 30633, 30634, 30646, 'af3sc_moderate.png'),
    (FULL,     30635, 30636, 30647, 'af3sc_full.png'),
)


class _Window(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.hint = kwargs.get('hint', 30642)
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
            self.getControl(9001).setLabel(AR(30630))
            self.getControl(9003).setLabel(AR(30641))
            self.getControl(9002).setLabel(AR(self.hint))
            for _ in range(10):            # focus can be refused right after a reload
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
    w = _Window('af3_shortcuts.xml', _addon_path(), 'Default', '1080i', hint=hint)
    w.doModal()
    idx = w.result
    del w
    return idx


def choose(wait_clear=None, settle=None, from_menu=False):
    """Light / Moderate / Full, or None (menu: Back = cancel).

    Setup: Back = Light. A window closed instantly (< 1.5 s, torn down by an
    add-on rescan after the portal) is shown again instead of being read as
    Back - the same rule as the restore popup and the repo picker.
    """
    for attempt in range(1, 7):
        if wait_clear:
            wait_clear()
        started = time.time()
        idx = _ask(30643 if from_menu else 30642)
        if idx >= 0:
            return MODES[idx]
        if time.time() - started > 1.5:
            return None if from_menu else LIGHT
        _log('window closed instantly (attempt %d) - showing it again' % attempt)
        if settle and not settle(2):
            break
    return None if from_menu else LIGHT


def run_step(wait_clear=None, settle=None):
    """Installation Wizard entry point."""
    mode = choose(wait_clear, settle)
    _log('choice: %s' % mode)
    return apply(mode)


def run_menu():
    """Setup & Install -> Widgets Layout."""
    mode = choose(from_menu=True)
    _log('menu choice: %s' % mode)
    if mode is None:
        return False
    if mode == LIGHT:
        xbmcgui.Dialog().notification(AR(30630), AR(30648),
                                      xbmcgui.NOTIFICATION_INFO, 3000)
        _save_state(LIGHT, True)
        return True
    return apply(mode)
