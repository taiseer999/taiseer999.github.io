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


def _set_addon_enabled(addonid, enabled):
    try:
        query = ('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled",'
                 '"params":{"addonid":"%s","enabled":%s},"id":1}'
                 % (addonid, 'true' if enabled else 'false'))
        xbmc.executeJSONRPC(query)
        xbmc.log('[AbukarimTools SkinSwitcher] %s -> enabled=%s'
                 % (addonid, enabled), xbmc.LOGINFO)
    except Exception:
        pass


def _addon_enabled_state(addonid):
    """Return True only if Kodi reports the addon as ENABLED."""
    try:
        import json as _json
        resp = xbmc.executeJSONRPC(
            '{"jsonrpc":"2.0","method":"Addons.GetAddonDetails",'
            '"params":{"addonid":"%s","properties":["enabled"]},"id":1}' % addonid)
        return _json.loads(resp).get('result', {}).get('addon', {}).get('enabled', False)
    except Exception:
        return False


def _wait_enabled_state(addonid, want_enabled, timeout_ms=8000):
    """Poll until the addon reaches the desired enabled/disabled state."""
    waited = 0
    step = 200
    while waited < timeout_ms:
        if _addon_enabled_state(addonid) == want_enabled:
            return True
        xbmc.sleep(step)
        waited += step
    return _addon_enabled_state(addonid) == want_enabled


def _apply_helper_for_skin(skin_id):
    # skin.bingie uses the Bingie TMDbHelper fork; every other skin uses the
    # stock TMDbHelper. Only ONE may be active at a time: running both forks at
    # once makes them fight over the dummy-file/RunPlugin player handoff, which
    # hard-freezes playback (the stock fork grabs a play action meant for the
    # Bingie fork, calls the resolver, and deadlocks waiting for a handback).
    #
    # SetAddonEnabled is asynchronous: a disabled addon's already-running
    # service.py keeps executing until it next checks the abort flag, so we must
    # (1) enable the WANTED fork first, (2) disable the OTHER fork, then
    # (3) BLOCK until Kodi confirms the other fork is actually disabled and give
    # its service a moment to wind down — before returning so the skin swap (and
    # any subsequent playback) happens with exactly one fork live.
    BINGIE_SKIN   = 'skin.bingie'
    STOCK_HELPER  = 'plugin.video.themoviedb.helper'
    BINGIE_HELPER = 'plugin.video.tmdb.bingie.helper'

    if skin_id == BINGIE_SKIN:
        want, drop = BINGIE_HELPER, STOCK_HELPER
    else:
        want, drop = STOCK_HELPER, BINGIE_HELPER

    # 1) Enable the one we want and confirm it's on.
    _set_addon_enabled(want, True)
    _wait_enabled_state(want, True, timeout_ms=8000)

    # 2) Disable the other and BLOCK until Kodi confirms it's off.
    _set_addon_enabled(drop, False)
    if _wait_enabled_state(drop, False, timeout_ms=8000):
        xbmc.log('[AbukarimTools SkinSwitcher] inactive helper disabled: %s'
                 % drop, xbmc.LOGINFO)
    else:
        xbmc.log('[AbukarimTools SkinSwitcher] WARNING: %s still enabled after '
                 'timeout' % drop, xbmc.LOGWARNING)

    # 3) Let the disabled fork's service.py observe the abort and exit before
    #    we hand control back (services poll their monitor roughly once/second).
    xbmc.sleep(1500)


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

    # Switching the active TMDbHelper fork while a video (or its dummy-file
    # resolver) is mid-playback is exactly what deadlocks the player handoff.
    # Stop any playback and let it fully tear down before we touch the forks.
    if xbmc.Player().isPlaying():
        xbmc.Player().stop()
        waited = 0
        while xbmc.Player().isPlaying() and waited < 5000:
            xbmc.sleep(200)
            waited += 200
        xbmc.sleep(500)

    _apply_helper_for_skin(chosen_id)
    _swap_skin(chosen_id)
