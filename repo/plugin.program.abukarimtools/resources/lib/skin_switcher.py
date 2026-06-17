# -*- coding: utf-8 -*-
"""
Skin Switcher – switch between installed skins.
Adapted from script.skinswitcher.
"""

import os
import glob

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

try:
    from resources.lib import tools as _tools
    _HAS_TOOLS = True
except Exception:
    _HAS_TOOLS = False

HOME   = xbmcvfs.translatePath('special://home/')
ADDONS = os.path.join(HOME, 'addons')
TITLE  = 'ABUKARIM – Skin Switcher'

try:
    _ver_str = xbmc.getInfoLabel('System.BuildVersion').split()[0]
    KODI_VER = float(_ver_str[:4])
except (ValueError, IndexError):
    KODI_VER = 20.0


def _curr_skin():
    skin_id   = xbmc.getSkinDir()
    try:
        return xbmcaddon.Addon(skin_id).getAddonInfo('name')
    except Exception:
        return skin_id


def _set_setting(key, value):
    try:
        query = ('{"jsonrpc":"2.0","method":"Settings.SetSettingValue",'
                 '"params":{"setting":"%s","value":"%s"},"id":1}' % (key, value))
        xbmc.executeJSONRPC(query)
    except Exception:
        pass


def _confirm_keep_dialog(timeout_ms=8000):
    """Answer Kodi's 'Keep this skin?' confirmation with Yes.

    When lookandfeel.skin changes, Kodi loads the new skin and shows a yes/no
    dialog that auto-reverts to the previous skin after ~10s if not confirmed.
    The affirmative button is not reliably control 11 across Kodi versions, so
    rather than SendClick a fixed id we move focus to the Yes side and select
    it, and keep doing so until the dialog is gone. This is what stops the
    silent revert back to Estuary.
    """
    waited = 0
    answered = False
    while waited < timeout_ms:
        if xbmc.getCondVisibility('Window.IsVisible(DialogYesNo.xml)') \
                or xbmc.getCondVisibility('Window.isVisible(yesnodialog)') \
                or xbmc.getCondVisibility('System.HasModalDialog'):
            # 'Yes'/keep is the right-hand button (control 11). Answer it by
            # every reliable means, targeting the dialog window explicitly so
            # the click can't land on the wrong window.
            xbmc.executebuiltin('SendClick(10100,11)')   # DialogYesNo window id
            xbmc.executebuiltin('SetFocus(11)')
            xbmc.sleep(40)
            xbmc.executebuiltin('SendClick(11)')
            xbmc.sleep(40)
            xbmc.executebuiltin('Action(Select)')
            answered = True
            xbmc.sleep(250)
            if not (xbmc.getCondVisibility('Window.isVisible(yesnodialog)')
                    or xbmc.getCondVisibility('Window.IsVisible(DialogYesNo.xml)')):
                break
        elif answered:
            break
        xbmc.sleep(100)
        waited += 100
    return answered


def _swap_skin(addonid):
    _set_setting('lookandfeel.skin', addonid)
    _confirm_keep_dialog()


def run():
    xbmc.executebuiltin('Dialog.Close(busydialog)')
    xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

    skin_folders = glob.glob(os.path.join(ADDONS, 'skin*'))
    names     = []
    addon_ids = []

    for folder in sorted(skin_folders):
        foldername = os.path.basename(folder.rstrip(os.sep))
        xml_path   = os.path.join(folder, 'addon.xml')
        if not os.path.exists(xml_path):
            continue
        try:
            with open(xml_path, encoding='utf-8') as f:
                content = f.read()
            # Parse addon id — try tools.parseDOM if available, else simple find
            if _HAS_TOOLS:
                match = _tools.parseDOM(content, 'addon', ret='id')
                addon_id = foldername if not match else match[0]
            else:
                import re
                m = re.search(r'<addon[^>]+id=["\']([^"\']+)["\']', content)
                addon_id = m.group(1) if m else foldername
            addon = xbmcaddon.Addon(id=addon_id)
            names.append(addon.getAddonInfo('name'))
            addon_ids.append(addon_id)
        except Exception:
            pass

    if not names:
        xbmcgui.Dialog().ok(TITLE, 'No installed skins found.')
        return

    choices = ['Current Skin — %s' % _curr_skin()] + names
    idx     = xbmcgui.Dialog().select('Choose a skin', choices)
    if idx <= 0:
        return

    chosen_id = addon_ids[idx - 1]
    _swap_skin(chosen_id)
