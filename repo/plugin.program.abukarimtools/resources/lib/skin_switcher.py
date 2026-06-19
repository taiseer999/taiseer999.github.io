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


def _swap_skin(addonid):
    _set_setting('lookandfeel.skin', addonid)
    # When the skin is set, CoreELEC shows the 'Add-on required / enable this
    # add-on?' (or a keep-skin) yes/no dialog. On this dialog YES is the
    # FOCUSED/default button, so the reliable answer is to activate the focused
    # control with Select — clicking a fixed control id (the old SendClick(11))
    # hit the wrong button and sent the switch into a loop. We keep answering
    # for several seconds, because the dialog can appear slightly after the set
    # and must be confirmed before its short countdown reverts it.
    waited = 0
    answered = False
    while waited < 9000:
        if xbmc.getCondVisibility('Window.IsVisible(10100)') \
                or xbmc.getCondVisibility('Window.IsVisible(DialogConfirm.xml)') \
                or xbmc.getCondVisibility('Window.IsVisible(yesnodialog)') \
                or xbmc.getCondVisibility('Window.IsVisible(DialogYesNo.xml)'):
            xbmc.executebuiltin('Action(Select)')   # activate focused = Yes
            xbmc.sleep(40)
            xbmc.executebuiltin('SendClick(10100,11)')
            xbmc.executebuiltin('SendClick(10100,10)')
            xbmc.executebuiltin('SendClick(11)')
            answered = True
            xbmc.sleep(250)
            if not (xbmc.getCondVisibility('Window.IsVisible(10100)')
                    or xbmc.getCondVisibility('Window.IsVisible(DialogConfirm.xml)')
                    or xbmc.getCondVisibility('Window.IsVisible(yesnodialog)')
                    or xbmc.getCondVisibility('Window.IsVisible(DialogYesNo.xml)')):
                break
        elif answered:
            break
        xbmc.sleep(80)
        waited += 80


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
