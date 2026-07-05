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
    # Confirm the 'Add-on required / enable this add-on?' dialog the SAME way
    # the (working) binary installer does: detect with IsActive(yesnodialog)
    # and click control 11 (Yes) on the named yesnodialog window. The build's
    # confirm dialog responds to this; targeting it by numeric id / bare Select
    # did not. We keep trying for several seconds in case it appears slightly
    # after the set and needs a moment to accept input.
    waited = 0
    answered = False
    while waited < 12000:
        active = (xbmc.getCondVisibility('Window.IsActive(yesnodialog)')
                  or xbmc.getCondVisibility('Window.IsActive(DialogConfirm.xml)')
                  or xbmc.getCondVisibility('Window.IsActive(10100)'))
        if active:
            try:
                fc  = xbmc.getInfoLabel('System.CurrentControlId')
                win = xbmc.getInfoLabel('System.CurrentWindow')
                xbmc.log('[AbukarimTools SkinSwitcher] confirm dialog up '
                         '(window=%s focusedControl=%s)' % (win, fc), xbmc.LOGINFO)
            except Exception:
                pass
            # YES is control 11 on this 'Yes / No dialog' (NO is the focused
            # control 10 — so we must NOT use Action(Select), which would
            # activate No and cause the revert/loop). Click control 11 only.
            xbmc.executebuiltin('SendClick(yesnodialog, 11)')   # 11 = Yes
            xbmc.sleep(60)
            xbmc.executebuiltin('SendClick(11)')                # backup, same id
            answered = True
            xbmc.sleep(250)
            still = (xbmc.getCondVisibility('Window.IsActive(yesnodialog)')
                     or xbmc.getCondVisibility('Window.IsActive(DialogConfirm.xml)')
                     or xbmc.getCondVisibility('Window.IsActive(10100)'))
            if not still:
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

    # Stop any playback and let it fully tear down before swapping skins.
    if xbmc.Player().isPlaying():
        xbmc.Player().stop()
        waited = 0
        while xbmc.Player().isPlaying() and waited < 5000:
            xbmc.sleep(200)
            waited += 200
        xbmc.sleep(500)

    _swap_skin(chosen_id)
