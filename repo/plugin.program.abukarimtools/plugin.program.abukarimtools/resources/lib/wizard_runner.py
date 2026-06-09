# -*- coding: utf-8 -*-
"""
wizard_runner.py  –  run embedded wizards in-process.

Key techniques:
1. _WizardFinder  – MetaPathFinder that redirects all 'resources.*' / 'uservar'
                    imports to the wizard's own directory.
2. _AddonShim     – fake xbmcaddon.Addon returning correct id/path/settings.
3. addDirectoryItem patch – injects '&wizard=<slug>' into every URL the wizard
                    registers, so sub-page clicks re-enter through our router.
4. sys.argv[0]    – set to plain abukarimtools plugin URL (no trailing params)
                    so wizard URL-building works normally.
"""

import os
import sys
import re
import importlib
import importlib.util
import importlib.machinery
import xbmcaddon
import xbmcplugin
import xbmcvfs

def _load_po_strings(wizard_dir):
    """Parse strings.po and return {int_id: str} for addon-specific string IDs."""
    import re as _re
    po_path = os.path.join(wizard_dir, 'resources', 'language',
                           'resource.language.en_gb', 'strings.po')
    if not os.path.exists(po_path):
        return {}
    try:
        with open(po_path, encoding='utf-8', errors='ignore') as f:
            text = f.read()
        strings = {}
        for m in _re.finditer(r'msgctxt\s+"#(\d+)"\s+msgid\s+"([^"]*)"', text):
            strings[int(m.group(1))] = m.group(2)
        return strings
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Wizard metadata & defaults
# ---------------------------------------------------------------------------

_WIZARD_META = {
    'plugin.program.openwizard': {
        'name': '[COLOR limegreen]Open[/COLOR]Wizard',
        'version': '2.0.8.1',
        'icon': 'icon.png',
        'fanart': 'fanart.png',
        'entry': 'default.py',
        'slug': 'openwizard',
    },
}

_OW_DEFAULTS = {
    'buildname': '', 'buildversion': '', 'buildtheme': '', 'latestversion': '',
    'nextbuildcheck': '2019-01-01 00:00:00', 'disableupdate': 'false',
    'show19': 'true', 'show20': 'true', 'show21': 'true', 'show22': 'true',
    'separate': 'false', 'first_install': 'true', 'enable_all': 'false',
    'time_started': '0', 'installed': 'false', 'extract': '100', 'errors': '0',
    'defaultskin': '', 'defaultskinname': '', 'defaultskinignore': 'false',
    'default.enablerssfeeds': '', 'default.font': '', 'default.rssedit': '',
    'default.skincolors': '', 'default.skintheme': '', 'default.skinzoom': '',
    'default.soundskin': '', 'default.startupwindow': '', 'default.stereostrength': '',
    'default.addonupdate': '', 'oldlog': 'false', 'wizlog': 'false',
    'crashlog': 'false', 'path': 'special://home/', 'autoclean': 'false',
    'clearcache': 'false', 'clearpackages': 'false', 'clearthumbs': 'false',
    'autocleanfreq': '3', 'nextautocleanup': '2019-01-01 00:00:00',
    'includevideo': 'true', 'includeall': 'true', 'includeexodusredux': 'true',
    'includegaia': 'true', 'includenumbers': 'true', 'includescrubs': 'true',
    'includeseren': 'true', 'includethecrew': 'true', 'includevenom': 'true',
    'exodusredux': '', 'fen': '', 'gaia': '', 'numbers': '', 'openmeta': '',
    'premiumizer': '', 'realizer': '', 'scrubs': '', 'seren': '', 'shadow': '',
    'thecrew': '', 'tmdbhelper': '', 'trakt': '', 'venom': '',
    'fenad': '', 'fenpm': '', 'fenrd': '', 'gaiaad': '', 'gaiapm': '', 'gaiard': '',
    'pmzer': '', 'serenad': '', 'serenpm': '', 'serenpm-oauth': '', 'serenrd': '',
    'rurlad': '', 'rurlpm': '', 'rurlrd': '', 'urlad': '', 'urlpm': '', 'urlrd': '',
    'shadowad': '', 'shadowpm': '', 'shadowrd': '',
    'easynews-fen': '', 'furk-fen': '', 'fanart-exodusredux': '',
    'fanart-gaia': '', 'fanart-numbers': '', 'fanart-thecrew': '',
    'fanart-metadatautils': '', 'fanart-premiumizer': '', 'fanart-realizer': '',
    'fanart-scrubs': '', 'fanart-venom': '', 'fanart-seren': '',
    'fanart-tmdbhelper': '', 'imdb-exodusredux': '', 'imdb-gaia': '',
    'imdb-numbers': '', 'imdb-thecrew': '', 'imdb-premiumizer': '',
    'imdb-realizer': '', 'imdb-scrubs': '', 'imdb-venom': '',
    'kitsu-wonderfulsubs': '', 'login-iagl': '', 'login-netflix': '',
    'mal-wonderfulsubs': '', 'omdb-metadatautils': '', 'omdb-metahandler': '',
    'omdb-tmdbhelper': '', 'login-opensubtitles': '', 'login-opensubsbyopensubs': '',
    'login-orion': '', 'tmdb-exodusredux': '', 'tmdb-fen': '', 'login-eis': '',
    'tmdb-gaia': '', 'tmdb-numbers': '', 'tmdb-metadatautils': '', 'tmdb-eis': '',
    'tmdb-openmeta': '', 'tmdb-thecrew': '', 'tmdb-premiumizer': '',
    'tmdb-realizer': '', 'tmdb-scrubs': '', 'tmdb-seren': '',
    'tmdb-tmdbhelper': '', 'tmdb-venom': '', 'trakt-openmeta': '',
    'trakt-seren': '', 'tvdb-metahandler': '', 'tvdb-openmeta': '',
    'tvdb-premiumizer': '', 'tvdb-realizer': '', 'tvdb-seren': '',
    'location-yahoo': '', 'login-youtube': '', 'ws-wonderfulsubs': '',
    'apk_path': '/storage/emulated/0/Download/',
    'keeptrakt': 'true', 'traktnextsave': '2019-01-01 00:00:00',
    'keepdebrid': 'true', 'debridnextsave': '2019-01-01 00:00:00',
    'keeplogin': 'true', 'loginnextsave': '2019-01-01 00:00:00',
    'keepfavourites': 'true', 'keepsources': 'true', 'keepprofiles': 'false',
    'keepplayercore': 'false', 'keepguisettings': 'false', 'keepadvanced': 'true',
    'keeprepos': 'false', 'keepsuper': 'false', 'keepwhitelist': 'false',
    'developer': '', 'adult': 'false', 'auto-view': 'true', 'viewType': '50',
    'notify': 'false', 'noteid': '0', 'debuglevel': '1', 'wizardlog': 'true',
    'autocleanwiz': 'true', 'wizlogcleanby': '1', 'wizlogcleandays': '2',
    'wizlogcleansize': '1', 'wizlogcleanlines': '2',
    'nextwizcleandate': '2019-01-01 00:00:00',
}


_DEFAULTS = {
    'plugin.program.openwizard':     _OW_DEFAULTS,
}

# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------

def _settings_path(addon_id):
    folder = xbmcvfs.translatePath(
        'special://userdata/addon_data/{}/'.format(addon_id))
    return folder, os.path.join(folder, 'settings.xml')


def _load_settings(addon_id):
    folder, path = _settings_path(addon_id)
    if not os.path.exists(path):
        xbmcvfs.mkdirs(folder)
        data = dict(_DEFAULTS.get(addon_id, {}))
        _write_settings(path, data)
        return data
    try:
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
        result = {}
        for m in re.finditer(r'<setting id="([^"]+)">([^<]*)</setting>', text):
            result[m.group(1)] = m.group(2)
        for k, v in _DEFAULTS.get(addon_id, {}).items():
            if k not in result:
                result[k] = v
        return result
    except Exception:
        return dict(_DEFAULTS.get(addon_id, {}))


def _write_settings(path, data):
    lines = ['<settings version="2">']
    for k, v in sorted(data.items()):
        v_esc = str(v).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        lines.append('    <setting id="{}">{}</setting>'.format(k, v_esc))
    lines.append('</settings>')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


# ---------------------------------------------------------------------------
# Addon shim
# ---------------------------------------------------------------------------

import xbmc as _xbmc

class _AddonShim:
    def __init__(self, addon_id, wizard_path):
        self._id   = addon_id
        self._path = wizard_path
        self._meta = _WIZARD_META.get(addon_id, {})
        self._settings = _load_settings(addon_id)
        _, self._settings_file = _settings_path(addon_id)
        self._strings = _load_po_strings(wizard_path)

    def getAddonInfo(self, key):
        if key == 'id':      return self._id
        if key == 'name':    return self._meta.get('name', self._id)
        if key == 'version': return self._meta.get('version', '0')
        if key == 'path':    return self._path
        if key == 'profile': return xbmcvfs.translatePath(
            'special://userdata/addon_data/{}/'.format(self._id))
        if key == 'icon':
            return os.path.join(self._path, self._meta.get('icon', 'icon.png'))
        if key == 'fanart':
            return os.path.join(self._path, self._meta.get('fanart', 'fanart.jpg'))
        return ''

    def getSetting(self, key):
        return str(self._settings.get(key, ''))

    def setSetting(self, key, value):
        self._settings[key] = str(value)
        _write_settings(self._settings_file, self._settings)

    def getLocalizedString(self, string_id):
        if string_id in self._strings:
            return self._strings[string_id]
        try:
            return _xbmc.getLocalizedString(string_id)
        except Exception:
            return ''

    def openSettings(self):
        pass


# ---------------------------------------------------------------------------
# Custom MetaPathFinder
# ---------------------------------------------------------------------------

class _WizardFinder:
    def __init__(self, wizard_dir):
        self._root = wizard_dir

    def _handles(self, fullname):
        return (fullname == 'resources'
                or fullname.startswith('resources.')
                or fullname == 'uservar')

    def find_module(self, fullname, path=None):
        if self._handles(fullname):
            return self
        return None

    def load_module(self, fullname):
        spec = self.find_spec(fullname, None, None)
        if spec is None:
            raise ImportError(fullname)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[fullname] = mod
        spec.loader.exec_module(mod)
        return mod

    def find_spec(self, fullname, path, target=None):
        if not self._handles(fullname):
            return None
        parts = fullname.split('.')
        candidate = os.path.join(self._root, *parts)

        init = os.path.join(candidate, '__init__.py')
        if os.path.isdir(candidate) and os.path.isfile(init):
            loader = importlib.machinery.SourceFileLoader(fullname, init)
            return importlib.util.spec_from_file_location(
                fullname, init, loader=loader,
                submodule_search_locations=[candidate])

        py = candidate + '.py'
        if os.path.isfile(py):
            loader = importlib.machinery.SourceFileLoader(fullname, py)
            return importlib.util.spec_from_file_location(fullname, py, loader=loader)

        return None


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

_BASE_URL = 'plugin://plugin.program.abukarimtools/'

def _make_patched_addDirectoryItem(slug, real_func):
    """
    Return a wrapper around xbmcplugin.addDirectoryItem that appends
    &wizard=<slug> to every folder URL so sub-page clicks re-enter our router.
    """
    def _patched(handle, url, listitem, isFolder=False, totalItems=0):
        if url:
            sep = '&' if '?' in url else '?'
            url = '{}{sep}wizard={slug}'.format(url, sep=sep, slug=slug)
        return real_func(handle, url, listitem, isFolder, totalItems)
    return _patched


def _run_wizard(addon_id, wizard_dir, handle, paramstring=''):
    meta  = _WIZARD_META[addon_id]
    entry = os.path.join(wizard_dir, meta['entry'])
    slug  = meta['slug']

    # 1. Patch xbmcaddon.Addon
    _real_Addon = xbmcaddon.Addon
    shim = _AddonShim(addon_id, wizard_dir)

    def _patched_Addon(id=None):
        if id is None or id == addon_id:
            return shim
        try:
            return _real_Addon(id)
        except Exception:
            return shim

    xbmcaddon.Addon = _patched_Addon

    # 2. Patch xbmcplugin.addDirectoryItem to inject wizard= into folder URLs
    _real_addDirectoryItem = xbmcplugin.addDirectoryItem
    xbmcplugin.addDirectoryItem = _make_patched_addDirectoryItem(slug, _real_addDirectoryItem)

    # 3. Set sys.argv — plain base URL, no wizard= here (it goes in item URLs instead)
    saved_argv = sys.argv[:]
    sys.argv = [_BASE_URL, str(handle), '?' + paramstring]

    # 4. Evict conflicting cached modules
    stale = [k for k in sys.modules
             if k == 'resources' or k.startswith('resources.')
             or k == 'uservar']
    saved_modules = {k: sys.modules.pop(k) for k in stale}

    # 5. Install custom finder
    finder = _WizardFinder(wizard_dir)
    sys.meta_path.insert(0, finder)

    try:
        with open(entry, 'r', encoding='utf-8') as f:
            source = f.read()
        code = compile(source, entry, 'exec')
        globs = {
            '__name__':     '__main__',
            '__file__':     entry,
            '__spec__':     None,
            '__loader__':   None,
            '__package__':  None,
            '__builtins__': __builtins__,
        }
        exec(code, globs)

    finally:
        xbmcaddon.Addon = _real_Addon
        xbmcplugin.addDirectoryItem = _real_addDirectoryItem
        sys.argv = saved_argv
        if finder in sys.meta_path:
            sys.meta_path.remove(finder)
        for k in list(sys.modules):
            if k == 'resources' or k.startswith('resources.') or k == 'uservar':
                del sys.modules[k]
        sys.modules.update(saved_modules)


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def run_openwizard(handle, addon_path, paramstring=''):
    wizard_dir = os.path.join(addon_path, 'resources', 'lib', 'openwizard')
    _run_wizard('plugin.program.openwizard', wizard_dir, handle, paramstring)


