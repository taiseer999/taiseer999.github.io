# -*- coding: utf-8 -*-
"""
dexhub_toggle.py  -  ABUKARIM TOOLS

DexHub home-widget PLOTS on/off.

DexHub builds its home widget from a fast "lightweight" snapshot that ships
art only - the plot/overview is deferred until an item is selected, so the
Arctic Fuse 3 info panel shows no description for a focused Dex Hub card.

This toggle flips DexHub between two coherent profiles by writing its own
user settings file (never the bundled one):

    PLOTS (Hybrid)                     FAST (default)
    --------------------------------   --------------------------------
    lightweight_mode = false           lightweight_mode = true
    index_mode       = Hybrid (rec.)   index_mode       = Live (current)
    deep_meta_enrich = true            deep_meta_enrich = false
    meta_cache_ttl   = 14400           meta_cache_ttl   = 3600

In PLOTS mode DexHub builds a background index that includes the plot and
caches it in SQLite, so the widget still renders quickly (cache reads) once
the first index is built - the cost moves to a periodic background sync.
FAST mode restores the original speed-first behaviour (no plots on cards).

The write is slot-scoped to just these four ids: every other DexHub setting
in the live file is preserved. A timestamped backup is written first. Kodi
is then restarted (systemctl on CoreELEC, RestartApp elsewhere) so the
service re-reads the new profile.
"""

import os
import shutil
import datetime
import xml.etree.ElementTree as ET

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

from resources.lib.i18n import T

ADDON      = xbmcaddon.Addon()
ADDON_NAME = 'ABUKARIM TOOLS'
DEX_ID     = 'plugin.video.dexhub'
DEX_DIR    = xbmcvfs.translatePath('special://profile/addon_data/' + DEX_ID)
TARGET     = os.path.join(DEX_DIR, 'settings.xml')

DIALOG = xbmcgui.Dialog()

# id -> (plots_value, fast_value)
PROFILE = {
    'lightweight_mode': ('false',                'true'),
    'index_mode':       ('Hybrid (recommended)', 'Live (current)'),
    'deep_meta_enrich': ('true',                 'false'),
    'meta_cache_ttl':   ('14400',               '3600'),
}


def _log(msg):
    xbmc.log('[AbukarimTools DexHubToggle] %s' % msg, xbmc.LOGINFO)


def _read(path):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def _backup(path):
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    dst = '%s.bak-%s' % (path, stamp)
    shutil.copy2(path, dst)
    return dst


def _current_state():
    """True (plots) / False (fast) / None (unknown) from index_mode."""
    if not os.path.isfile(TARGET):
        return None
    try:
        root = ET.parse(TARGET).getroot()
    except (ET.ParseError, OSError):
        return None
    for el in root.findall('.//setting'):
        if el.get('id') == 'index_mode':
            return (el.text or '').strip() == PROFILE['index_mode'][0]
    return None


def _apply(enable):
    """Write the chosen profile into DexHub's user settings.xml.

    Returns (ok, error). Creates the file from scratch if DexHub has never
    saved settings yet, so the toggle works before DexHub's first launch.
    """
    idx = 0 if enable else 1  # 0 = plots value, 1 = fast value

    try:
        if os.path.isfile(TARGET):
            root = ET.parse(TARGET).getroot()
        else:
            os.makedirs(DEX_DIR, exist_ok=True)
            root = ET.Element('settings')
            root.set('version', '2')
    except (ET.ParseError, OSError) as e:
        return False, e

    by_id = {}
    for el in root.findall('.//setting'):
        sid = el.get('id')
        if sid:
            by_id[sid] = el

    for sid, values in PROFILE.items():
        val = values[idx]
        el = by_id.get(sid)
        if el is None:
            el = ET.SubElement(root, 'setting')
            el.set('id', sid)
            el.set('default', 'false')
            el.text = val
        else:
            el.text = val
            # Kodi ignores the stored text while default="true"; drop it.
            if 'default' in el.attrib:
                del el.attrib['default']

    try:
        if os.path.isfile(TARGET):
            bak = _backup(TARGET)
            _log('Backup written: %s' % bak)
        tmp = TARGET + '.tmp'
        ET.ElementTree(root).write(tmp, encoding='utf-8', xml_declaration=True)
        os.replace(tmp, TARGET)
        _log('Wrote %s profile to %s' % ('PLOTS' if enable else 'FAST', TARGET))
    except OSError as e:
        return False, e
    return True, None


def _is_coreelec():
    if os.path.isdir('/etc/coreelec'):
        return True
    try:
        with open('/etc/os-release') as f:
            return any('coreelec' in line.lower() for line in f)
    except OSError:
        return False


def _restart_kodi():
    if _is_coreelec():
        _log('Restarting Kodi via systemctl (CoreELEC).')
        os.system('systemctl restart kodi &')
    else:
        _log('Restarting Kodi via RestartApp builtin.')
        xbmc.executebuiltin('RestartApp')


def run():
    label = 'DexHub'

    if not xbmc.getCondVisibility('System.HasAddon(%s)' % DEX_ID):
        DIALOG.ok(ADDON_NAME, T(30281))
        return

    state = _current_state()
    if state is True:
        state_lbl = T(30261)
    elif state is False:
        state_lbl = T(30262)
    else:
        state_lbl = T(30263)

    # DexHub-specific option labels (plots vs fast), not the tab wording.
    choice = DIALOG.select(
        T(30282) % state_lbl,
        [T(30283),   # Enable plots (Hybrid)
         T(30284)])  # Fast mode (no plots)
    if choice == -1:
        return

    enable = (choice == 0)

    if not DIALOG.yesno(
            ADDON_NAME,
            T(30285) % (T(30268) if enable else T(30269)),
            yeslabel=T(30270), nolabel=T(30052)):
        return

    ok, err = _apply(enable)
    if not ok:
        DIALOG.ok(ADDON_NAME, T(30271) % (TARGET, err))
        return

    DIALOG.notification(
        ADDON_NAME,
        T(30286) % (T(30273) if enable else T(30274)),
        xbmcgui.NOTIFICATION_INFO, 3000)
    xbmc.sleep(1500)

    # In PLOTS mode the first index has to be built once; tell DexHub to do it
    # now so plots appear on the very next boot instead of after the first
    # scheduled sync. Best-effort - ignored if DexHub isn't ready yet.
    if enable:
        try:
            xbmc.executebuiltin(
                'RunPlugin(plugin://%s/?action=index_refresh_all)' % DEX_ID)
            xbmc.sleep(800)
        except Exception:
            pass

    _restart_kodi()
