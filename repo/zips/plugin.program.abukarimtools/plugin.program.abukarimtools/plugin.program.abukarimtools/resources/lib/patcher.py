# -*- coding: utf-8 -*-
"""
patcher.py  –  ABUKARIM TOOLS
Applies patches to installed Kodi addons:

  1. plugin.video.redlight  –  kodi_utils.py
     addon_themes() → Dark only (removes Light & Medium options)

  2. script.tinyppi  –  overlay.py
     _ALLOW_NON_COREELEC = False  →  True

  3. script.tinyppi  –  resources/lib/properties.py
     get_DoviProfileVar() → strip "Dolby Vision " prefix, return profile part only

  4. script.tinyppi  –  resources/lib/monitor.py
     onNotification() → add _update_hdr_properties() trigger on Player.OnPlay

  5. script.tinyppi  –  resources/lib/monitor.py
     Add _update_hdr_properties() method to KodiMonitor class
"""

import os
import re
import xbmc
import xbmcvfs
import xbmcgui

# ---------------------------------------------------------------------------
ADDON_NAME  = 'ABUKARIM TOOLS'
HOME        = xbmcvfs.translatePath('special://home/')
ADDONS_DIR  = os.path.join(HOME, 'addons')

DIALOG      = xbmcgui.Dialog()

# ---------------------------------------------------------------------------
# Patch definitions
# Each entry:
#   addon_id   – folder name under kodi/addons/
#   rel_path   – path to target file relative to addon root
#   old        – exact string to replace
#   new        – replacement string
#   description – shown to user in notifications
# ---------------------------------------------------------------------------
PATCHES = [
    {
        'addon_id':    'plugin.video.redlight',
        'rel_path':    os.path.join('resources', 'lib', 'modules', 'kodi_utils.py'),
        'old':         (
            "def addon_themes():\n"
            "\treturn [{'name': 'Light', 'value': ('FF434343', 'FF2E2E2E'), 'icon': 'light'}, "
            "{'name': 'Medium', 'value': ('FF373737', 'FF4a4347'), 'icon': 'medium'},\n"
            "\t\t\t{'name': 'Dark', 'value': ('FF1F2020', 'FF4F4F4F'), 'icon': 'dark'}]"
        ),
        'new':         (
            "def addon_themes():\n"
            "\treturn [{'name': 'Dark', 'value': ('FF1F2020', 'FF4F4F4F'), 'icon': 'dark'}]"
        ),
        'description': 'RedLight – window theme locked to Dark only',
        # fallback: if the exact string isn't found (already patched or different
        # version) we fall back to a regex that handles any variant
        'fallback_pattern': r"(def addon_themes\(\):\s*\n\s*return\s*\[).*?(\])",
        'fallback_repl':    (
            r"\g<1>{'name': 'Dark', 'value': ('FF1F2020', 'FF4F4F4F'), 'icon': 'dark'}\g<2>"
        ),
    },
    {
        'addon_id':    'script.tinyppi',
        'rel_path':    os.path.join('resources', 'lib', 'overlay.py'),
        'old':         '_ALLOW_NON_COREELEC = False',
        'new':         '_ALLOW_NON_COREELEC = True',
        'description': 'TinyPPI – _ALLOW_NON_COREELEC enabled',
        'fallback_pattern': r'_ALLOW_NON_COREELEC\s*=\s*False',
        'fallback_repl':    '_ALLOW_NON_COREELEC = True',
    },
    # ------------------------------------------------------------------
    # Patch – RedLight dialogs.py: remove theme selection dialog,
    # silently apply Dark when type='theme' is triggered
    # ------------------------------------------------------------------
    {
        'addon_id':    'plugin.video.redlight',
        'rel_path':    os.path.join('resources', 'lib', 'indexers', 'dialogs.py'),
        'old': (
            "\tif params['type'] == 'theme':\n"
            "\t\tchoices = kodi_utils.addon_themes()\n"
            "\t\tlist_items = [{'line1': i['name'], 'icon': kodi_utils.get_icon(i['icon'], 'themes')} for i in choices]\n"
            "\t\tkwargs = {'items': json.dumps(list_items), 'heading': 'Assign a Theme', 'narrow_window': 'true'}\n"
            "\t\tchoice = kodi_utils.select_dialog(choices, **kwargs)\n"
            "\t\tif choice == None: return\n"
            "\t\twindow_theme, window_theme_contrast, window_theme_name = choice['value'][0][2:], choice['value'][1], choice['name']\n"
            "\t\twindow_theme_opacity = get_setting('redlight.window_theme_opacity', 'CC')\n"
            "\t\tset_setting('window_theme_name', window_theme_name)"
        ),
        'new': (
            "\tif params['type'] == 'theme':\n"
            "\t\t# PATCHED: Dark theme only\n"
            "\t\tdark_theme = kodi_utils.addon_themes()[0]\n"
            "\t\twindow_theme, window_theme_contrast, window_theme_name = dark_theme['value'][0][2:], dark_theme['value'][1], dark_theme['name']\n"
            "\t\twindow_theme_opacity = get_setting('redlight.window_theme_opacity', 'CC')\n"
            "\t\tset_setting('window_theme_name', window_theme_name)"
        ),
        'description': 'RedLight dialogs.py – remove theme picker, auto-apply Dark',
        'fallback_pattern': None,
        'fallback_repl':    None,
        'already_patched_check': 'PATCHED: Dark theme only',
    },
    # ------------------------------------------------------------------
    # Patch – RedLight settings_manager.xml: remove 'Assign Window Theme'
    # clickable item (only Dark theme exists)
    # ------------------------------------------------------------------
    {
        'addon_id':    'plugin.video.redlight',
        'rel_path':    os.path.join('resources', 'skins', 'Default', '1080i', 'settings_manager.xml'),
        'old': (
            '                      <item>\r\n'
            '                          <visible>Container(2000).HasFocus(10)</visible>\r\n'
            '                          <property name="setting_label">Assign Window Theme</property>\r\n'
            '                          <property name="setting_type">action</property>\r\n'
            '                          <property name="setting_value">$INFO[Window(10000).Property(redlight.window_theme_name)]</property>\r\n'
            '                          <property name="setting_description">Choose the theme Red Light will use for custom windows. Choices are Light, Medium and Dark</property>\r\n'
            '                          <onclick>RunPlugin(plugin://plugin.video.redlight/?mode=window_theme_choice&amp;type=theme)</onclick>\r\n'
            '                      </item>\r\n'
        ),
        'new': '',
        'description': 'RedLight settings_manager.xml – remove Assign Window Theme item',
        'fallback_pattern': r'[ \t]*<item>[\s\S]*?<property name="setting_label">Assign Window Theme</property>[\s\S]*?</item>\r?\n',
        'fallback_repl':    '',
        'already_patched_check': None,
        'not_found_ok': True,
    },
    # ------------------------------------------------------------------
    # Patch 3 – properties.py: strip "Dolby Vision " prefix from
    # get_DoviProfileVar() so it returns e.g. "Profile 7 FEL" instead of
    # "Dolby Vision Profile 7 FEL".  The skin uses the DVProfileELVar XML
    # variable to show FEL/MEL colours separately.
    # ------------------------------------------------------------------
    {
        'addon_id':    'script.tinyppi',
        'rel_path':    os.path.join('resources', 'lib', 'properties.py'),
        'old': (
            '        return "Dolby Vision Profile 8.1"\n\n    prof = re.search'
        ),
        'new': (
            '        return "Profile 8.1"\n\n    prof = re.search'
        ),
        'description': 'TinyPPI properties.py – DoviProfileVar strips "Dolby Vision " prefix (fallback)',
        # regex covers all four return statements in get_DoviProfileVar()
        'fallback_pattern': r'"Dolby Vision (Profile [^"]*)"',
        'fallback_repl':    r'"\1"',
    },
    # ------------------------------------------------------------------
    # Patch 4 – monitor.py: replace the entire original KodiMonitor class
    # with the updated version that includes _start_hdr_poll,
    # _poll_hdr_properties, _clear_hdr_properties, and
    # _update_hdr_properties.
    # ------------------------------------------------------------------
    {
        'addon_id':    'script.tinyppi',
        'rel_path':    os.path.join('resources', 'lib', 'monitor.py'),
        'old': (
            'import json\n'
            'import os\n'
            'import sys\n'
            '\n'
            'import xbmc\n'
            'import xbmcaddon\n'
            'import xbmcgui'
        ),
        'new': (
            'import json\n'
            'import os\n'
            'import sys\n'
            'import threading\n'
            '\n'
            'import xbmc\n'
            'import xbmcaddon\n'
            'import xbmcgui'
        ),
        'description': 'TinyPPI monitor.py – add threading import',
        'fallback_pattern': r'(import json\nimport os\nimport sys\n)(\nimport xbmc)',
        'fallback_repl':    r'\1import threading\n\2',
    },
    # ------------------------------------------------------------------
    # Patch 5 – monitor.py: add __init__ poll_thread attribute
    # ------------------------------------------------------------------
    {
        'addon_id':    'script.tinyppi',
        'rel_path':    os.path.join('resources', 'lib', 'monitor.py'),
        'old': (
            '        self.win   = win\n'
            '        self.addon = addon\n'
            '\n'
            '    def onNotification'
        ),
        'new': (
            '        self.win   = win\n'
            '        self.addon = addon\n'
            '        self._poll_thread = None\n'
            '\n'
            '    def onNotification'
        ),
        'description': 'TinyPPI monitor.py – add _poll_thread attribute to __init__',
        'fallback_pattern': r'(self\.win\s+=\s+win\n\s+self\.addon\s+=\s+addon\n)(\n\s+def onNotification)',
        'fallback_repl':    r'\1        self._poll_thread = None\n\2',
    },
    # ------------------------------------------------------------------
    # Patch 6 – monitor.py: replace bare onNotification body with the
    # full version that triggers HDR polling on Player.OnPlay/OnStop
    # ------------------------------------------------------------------
    {
        'addon_id':    'script.tinyppi',
        'rel_path':    os.path.join('resources', 'lib', 'monitor.py'),
        'old': (
            '            _log(f"sender={sender}  method={method}  type={mediatype!r}")\n'
            '\n'
            '        except Exception as exc:\n'
            '            _log(f"Exception in KodiMonitor.onNotification: {exc}", xbmc.LOGERROR)\n'
            '\n'
            '\n'
            '# ---------------------------------------------------------------------------\n'
            '# Entry point'
        ),
        'new': (
            '            _log(f"sender={sender}  method={method}  type={mediatype!r}")\n'
            '\n'
            '            if method == "Player.OnPlay":\n'
            '                self._start_hdr_poll()\n'
            '                self._update_hdr_properties()\n'
            '\n'
            '            if method == "Player.OnStop":\n'
            '                self._clear_hdr_properties()\n'
            '\n'
            '        except Exception as exc:\n'
            '            _log(f"Exception in KodiMonitor.onNotification: {exc}", xbmc.LOGERROR)\n'
            '\n'
            '    def _update_hdr_properties(self) -> None:\n'
            '        """Immediately read and publish HDR/DV properties after playback starts."""\n'
            '        xbmc.sleep(3000)  # wait for player to initialise\n'
            '        _addon_path = xbmcaddon.Addon(_ADDON_ID).getAddonInfo("path")\n'
            '        sys.path.insert(0, os.path.join(_addon_path, "resources", "lib"))\n'
            '        try:\n'
            '            from properties import get_HdmiHdrStatusVar, get_DoviProfileVar\n'
            '            hdr  = get_HdmiHdrStatusVar()\n'
            '            dovi = get_DoviProfileVar()\n'
            '            xbmc.executebuiltin(f"SetProperty(HdmiHdrStatusVar,{hdr},Home)")\n'
            '            xbmc.executebuiltin(f"SetProperty(DoviProfileVar,{dovi},Home)")\n'
            '            _log(f"_update_hdr_properties: hdr={hdr!r}  dovi={dovi!r}", xbmc.LOGINFO)\n'
            '        except Exception as exc:\n'
            '            _log(f"_update_hdr_properties failed: {exc}", xbmc.LOGERROR)\n'
            '\n'
            '    def _start_hdr_poll(self) -> None:\n'
            '        """Start a background thread that polls HDR properties for 30 seconds."""\n'
            '        if self._poll_thread and self._poll_thread.is_alive():\n'
            '            return\n'
            '        self._poll_thread = threading.Thread(target=self._poll_hdr_properties, daemon=True)\n'
            '        self._poll_thread.start()\n'
            '\n'
            '    def _poll_hdr_properties(self) -> None:\n'
            '        """Poll every 2 seconds for 30 seconds until DV profile is found."""\n'
            '        _addon_path = xbmcaddon.Addon(_ADDON_ID).getAddonInfo("path")\n'
            '        sys.path.insert(0, os.path.join(_addon_path, "resources", "lib"))\n'
            '        try:\n'
            '            from properties import get_HdmiHdrStatusVar, get_DoviProfileVar\n'
            '            for _ in range(15):  # 15 attempts x 2 seconds = 30 seconds\n'
            '                xbmc.sleep(2000)\n'
            '                hdr  = get_HdmiHdrStatusVar()\n'
            '                dovi = get_DoviProfileVar()\n'
            '                xbmc.executebuiltin(f"SetProperty(HdmiHdrStatusVar,{hdr},Home)")\n'
            '                xbmc.executebuiltin(f"SetProperty(DoviProfileVar,{dovi},Home)")\n'
            '                _log(f"HDR poll: HdmiHdrStatusVar={hdr!r}  DoviProfileVar={dovi!r}", xbmc.LOGINFO)\n'
            '                if dovi:\n'
            '                    _log("DV profile found — stopping poll", xbmc.LOGINFO)\n'
            '                    break\n'
            '        except Exception as exc:\n'
            '            _log(f"_poll_hdr_properties failed: {exc}", xbmc.LOGERROR)\n'
            '\n'
            '    def _clear_hdr_properties(self) -> None:\n'
            '        """Clear HDR properties from Window(Home) when playback stops."""\n'
            '        xbmc.executebuiltin("ClearProperty(HdmiHdrStatusVar,Home)")\n'
            '        xbmc.executebuiltin("ClearProperty(DoviProfileVar,Home)")\n'
            '\n'
            '\n'
            '# ---------------------------------------------------------------------------\n'
            '# Entry point'
        ),
        'description': 'TinyPPI monitor.py – add HDR poll/update/clear methods',
        'fallback_pattern': None,
        'fallback_repl':    None,
        # already-patched check: shorter sentinel that only exists post-patch
        'already_patched_check': '_update_hdr_properties',
    },
]


# ---------------------------------------------------------------------------
def _log(msg):
    xbmc.log('[AbukarimTools Patcher] %s' % msg, xbmc.LOGINFO)


def _read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def _write(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def _apply_patch(patch):
    """
    Apply a single patch dict.
    Returns (success: bool, message: str)
    """
    addon_path = os.path.join(ADDONS_DIR, patch['addon_id'])
    if not os.path.isdir(addon_path):
        return False, '[%s] Addon not found: %s' % (patch['addon_id'], addon_path)

    target = os.path.join(addon_path, patch['rel_path'])
    if not os.path.isfile(target):
        return False, '[%s] Target file not found: %s' % (patch['addon_id'], patch['rel_path'])

    content = _read(target)

    # Check if already patched — use explicit sentinel if provided, else 'new' string
    already_check = patch.get('already_patched_check', patch['new'])
    if already_check is not None and already_check in content:
        return True, '[%s] Already patched – skipping.' % patch['addon_id']

    # Exact match replacement
    if patch['old'] in content:
        content = content.replace(patch['old'], patch['new'], 1)
        _write(target, content)
        return True, '[%s] Patched OK: %s' % (patch['addon_id'], patch['description'])

    # Fallback: regex replacement
    pattern = patch.get('fallback_pattern')
    repl    = patch.get('fallback_repl')
    if pattern and repl:
        new_content, n = re.subn(pattern, repl, content, count=1, flags=re.DOTALL)
        if n:
            _write(target, new_content)
            return True, '[%s] Patched OK (regex): %s' % (patch['addon_id'], patch['description'])

    if patch.get('not_found_ok'):
        return True, '[%s] Already patched – skipping.' % patch['addon_id']

    return False, '[%s] Patch string not found in %s' % (patch['addon_id'], patch['rel_path'])


# ---------------------------------------------------------------------------
def _reset_redlight_theme():
    DARK_THEME    = 'CC1F2020'
    DARK_CONTRAST = 'FF4a4347'
    try:
        import sqlite3
        db_path = xbmcvfs.translatePath(
            'special://profile/addon_data/plugin.video.redlight/databases/settings.db'
        )
        if xbmcvfs.exists(db_path):
            con = sqlite3.connect(db_path, timeout=10, isolation_level=None)
            con.execute('PRAGMA synchronous = OFF')
            rows = [
                ('window_theme',             'string', 'CC1F2020', DARK_THEME),
                ('window_theme_contrast',    'string', 'FF4a4347', DARK_CONTRAST),
                ('window_theme_name',        'string', 'Dark',     'Dark'),
                ('window_theme_opacity',     'string', 'CC',       'CC'),
                ('window_theme_opacity_name','string', '80%',      '80%'),
            ]
            for row in rows:
                con.execute('INSERT OR REPLACE INTO settings VALUES (?, ?, ?, ?)', row)
            con.close()
            _log('RedLight settings.db updated to Dark theme')
    except Exception as e:
        _log('settings.db write failed: %s' % e)
    try:
        win = xbmcgui.Window(10000)
        win.setProperty('redlight.window_theme',          DARK_THEME)
        win.setProperty('redlight.window_theme_contrast', DARK_CONTRAST)
        win.setProperty('redlight.window_theme_name',     'Dark')
        win.setProperty('redlight.window_theme_opacity',  'CC')
        win.setProperty('redlight.window_theme_opacity_name', '80%')
        _log('RedLight window properties set to Dark theme')
    except Exception as e:
        _log('Window property write failed: %s' % e)



# ---------------------------------------------------------------------------
def run():
    """Entry point called from default.py router."""
    _log('Starting patch run …')

    results   = []
    succeeded = 0
    failed    = 0

    for patch in PATCHES:
        ok, msg = _apply_patch(patch)
        _log(msg)
        results.append((ok, msg))
        if ok:
            succeeded += 1
        else:
            failed += 1

    # Build summary dialog
    lines = []
    for ok, msg in results:
        icon   = '[COLOR lime]✔[/COLOR]' if ok else '[COLOR red]✘[/COLOR]'
        # strip the leading [addon_id] prefix for display
        display = re.sub(r'^\[.*?\]\s*', '', msg)
        lines.append('%s  %s' % (icon, display))

    summary = '[B]Patch Results[/B][CR][CR]' + '[CR]'.join(lines)
    summary += '[CR][CR]%d succeeded,  %d failed.' % (succeeded, failed)

    DIALOG.ok(ADDON_NAME, summary)
    _log('Patch run complete: %d OK, %d failed.' % (succeeded, failed))

    _reset_redlight_theme()
