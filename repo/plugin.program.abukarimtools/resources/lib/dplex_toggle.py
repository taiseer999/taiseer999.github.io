# -*- coding: utf-8 -*-
"""
dplex_toggle.py  –  ABUKARIM TOOLS

Standalone tool: enable/disable the DPlex tab in Arctic Fuse 3.

Two full settings.xml variants are bundled with the addon:

    resources/data/dplex/settings_on.xml    (homeswitcher.1104.toggle = true)
    resources/data/dplex/settings_off.xml   (homeswitcher.1104.toggle = empty)

The chosen variant is copied to:

    userdata/addon_data/skin.arctic.fuse.3/settings.xml

and Kodi is force-restarted so the skin reloads the file cleanly
(no chance of the in-memory settings model writing back over it).
"""

import os
import shutil
import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon

ADDON       = xbmcaddon.Addon()
ADDON_NAME  = 'ABUKARIM TOOLS'
ADDON_PATH  = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
SETTING_ID  = 'homeswitcher.1104.toggle'
SKIN_ID     = 'skin.arctic.fuse.3'

DATA_DIR    = os.path.join(ADDON_PATH, 'resources', 'data', 'dplex')
SRC_ON      = os.path.join(DATA_DIR, 'settings_on.xml')
SRC_OFF     = os.path.join(DATA_DIR, 'settings_off.xml')

SKIN_DIR    = xbmcvfs.translatePath(
    'special://profile/addon_data/' + SKIN_ID)
TARGETS     = [os.path.join(SKIN_DIR, 'settings.xml')]

DIALOG = xbmcgui.Dialog()


def _log(msg):
    xbmc.log('[AbukarimTools DPlexToggle] %s' % msg, xbmc.LOGINFO)


def _current_state():
    """
    Return True (enabled) / False (disabled) / None (unknown)
    by reading the toggle value from the live settings.xml files.
    """
    marker = '<setting id="%s" type="string">' % SETTING_ID
    for target in TARGETS:
        try:
            with open(target, 'r', encoding='utf-8', errors='ignore') as f:
                data = f.read()
        except OSError:
            continue
        idx = data.find(marker)
        if idx == -1:
            continue
        end = data.find('</setting>', idx)
        if end == -1:
            continue
        return data[idx + len(marker):end].strip() == 'true'
    return None


def _is_coreelec():
    if os.path.isdir('/etc/coreelec'):
        return True
    try:
        with open('/etc/os-release') as f:
            return any('coreelec' in line.lower() for line in f)
    except OSError:
        return False


def _restart_kodi():
    """Force-restart Kodi (systemd on CoreELEC, RestartApp elsewhere)."""
    if _is_coreelec():
        _log('Restarting Kodi via systemctl (CoreELEC).')
        os.system('systemctl restart kodi &')
    else:
        _log('Restarting Kodi via RestartApp builtin.')
        xbmc.executebuiltin('RestartApp')


def run():
    # Sanity: bundled variants must exist
    for src in (SRC_ON, SRC_OFF):
        if not os.path.isfile(src):
            DIALOG.ok(ADDON_NAME,
                      '[COLOR red]✘[/COLOR]  Missing bundled file:[CR]'
                      '[I]%s[/I]' % src)
            return

    state = _current_state()
    if state is True:
        state_lbl = '[COLOR lime]ENABLED[/COLOR]'
    elif state is False:
        state_lbl = '[COLOR red]DISABLED[/COLOR]'
    else:
        state_lbl = '[COLOR gray]UNKNOWN[/COLOR]'

    choice = DIALOG.select(
        'DPlex Tab  –  currently %s' % state_lbl,
        ['[COLOR lime]Enable[/COLOR]  DPlex tab',
         '[COLOR red]Disable[/COLOR]  DPlex tab'],
        preselect=1 if state is True else 0)
    if choice == -1:
        return

    enable = (choice == 0)
    src    = SRC_ON if enable else SRC_OFF

    if not DIALOG.yesno(
            ADDON_NAME,
            'This will %s the DPlex tab and[CR]'
            '[B]restart Kodi[/B] to apply the change.[CR][CR]Continue?'
            % ('[COLOR lime]enable[/COLOR]' if enable
               else '[COLOR red]disable[/COLOR]'),
            yeslabel='Apply && Restart', nolabel='Cancel'):
        return

    for target in TARGETS:
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            tmp = target + '.tmp'
            shutil.copyfile(src, tmp)
            os.replace(tmp, target)
            _log('Copied %s -> %s' % (os.path.basename(src), target))
        except OSError as e:
            _log('Copy failed: %s' % e)
            DIALOG.ok(ADDON_NAME,
                      '[COLOR red]✘[/COLOR]  Failed to write:[CR][I]%s[/I]'
                      '[CR][CR]%s' % (target, e))
            return

    # If AF3 is the active skin, sync the in-memory skin setting too —
    # otherwise Kodi's skin-settings flush on shutdown would write the
    # old value back over addon_data/skin.arctic.fuse.3/settings.xml
    # during the restart.
    if xbmc.getSkinDir() == SKIN_ID:
        if enable:
            xbmc.executebuiltin('Skin.SetString(%s,true)' % SETTING_ID)
        else:
            xbmc.executebuiltin('Skin.Reset(%s)' % SETTING_ID)
        xbmc.sleep(300)

    xbmcgui.Dialog().notification(
        ADDON_NAME,
        'DPlex tab %s – restarting Kodi…'
        % ('enabled' if enable else 'disabled'),
        xbmcgui.NOTIFICATION_INFO, 3000)
    xbmc.sleep(1500)
    _restart_kodi()
