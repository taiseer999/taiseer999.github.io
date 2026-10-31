# -*- coding: utf-8 -*-
"""
af3_plotright_toggle.py - ABUKARIM TOOLS (4.6.15, 4.6.18)

Toggles entry "AF3: Plot on the Right". On the Arctic Fuse 3 Home page
(Spotlight and the combined hub info) the plot leaves the left column - the
ratings / meta lines move up, no gap is left - and shows complete in a glass
box on the empty right side. Flips the AF3 skin bool abk.plotright; the
always-on patcher entries (patcher.py, "AF3: Plot on the Right") read it, so
the switch shows at once (no skin reload unless the XML was just patched).

4.6.18: switching on also turns on AF3's "Two-line information bar"
(InfoBar.TwoRow) when it is off, so the info line stays short beside the box;
switching off resets it again only when AB Tools was the one that set it.
InfoBar.TwoRow is read by an include condition, so that change reloads the skin.
"""
import json
import os

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

SKIN_ID = 'skin.arctic.fuse.3'
SETTING = 'abk.plotright'
TITLE = 'ABUKARIM TOOLS'
MARK = '<!-- ABUKARIM: plot on the right -->'
TWOROW = 'InfoBar.TwoRow'
_STATE = os.path.join(xbmcvfs.translatePath('special://profile/addon_data/'),
                      'plugin.program.abukarimtools', 'af3_plotright.json')


def _load():
    try:
        with open(_STATE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(data):
    try:
        os.makedirs(os.path.dirname(_STATE), exist_ok=True)
        with open(_STATE, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except Exception as e:
        _log('state not saved: %s' % e, xbmc.LOGWARNING)


def _tworow_on():
    return bool(xbmc.getCondVisibility('Skin.HasSetting(%s)' % TWOROW))


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools PlotRight] %s' % msg, level)


def plot_right_on():
    return bool(xbmc.getCondVisibility('Skin.HasSetting(%s)' % SETTING))


def _ensure_patch():
    """(patched_ok, xml_changed)."""
    try:
        from resources.lib import patcher
        _ok, _failed, changed, _r = patcher.apply_set(addon_ids=[SKIN_ID])
    except Exception as exc:
        _log('skin patch failed: %s' % exc, xbmc.LOGWARNING)
        return False, False
    try:
        path = os.path.join(xbmcvfs.translatePath('special://home/addons/%s/' % SKIN_ID), '1080i', 'Includes_Hubs.xml')
        with open(path, 'r', encoding='utf-8') as f:
            ok = f.read().count(MARK) >= 2
    except Exception:
        ok = False
    return ok, changed > 0


def run():
    if not xbmc.getCondVisibility('System.HasAddon(%s)' % SKIN_ID):
        xbmcgui.Dialog().ok(TITLE, T(30440))          # AF3 is not installed
        return
    if xbmc.getSkinDir() != SKIN_ID:
        xbmcgui.Dialog().ok(TITLE, T(30602))          # switch to AF3 first
        return
    ok, reload_needed = _ensure_patch()
    if plot_right_on():
        xbmc.executebuiltin('Skin.Reset(%s)' % SETTING)
        state = _load()
        if state.pop('tworow_set', False) and _tworow_on():
            xbmc.executebuiltin('Skin.Reset(%s)' % TWOROW)        # we turned it on: back off
            reload_needed = True
            _log('two-line information bar: back off')
        _save(state)
        msg = T(30892)
        _log('plot on the right: OFF')
    else:
        if not ok:
            xbmcgui.Dialog().ok(TITLE, T(30893))
            return
        xbmc.executebuiltin('Skin.SetBool(%s)' % SETTING)
        if not _tworow_on():
            xbmc.executebuiltin('Skin.SetBool(%s)' % TWOROW)
            _save(dict(_load(), tworow_set=True))
            reload_needed = True                               # include condition: reload
            _log('two-line information bar: on')
        msg = T(30891)
        _log('plot on the right: ON')
    xbmcgui.Dialog().notification(TITLE, msg, xbmcgui.NOTIFICATION_INFO, 3000)
    if reload_needed:
        xbmc.sleep(300)
        xbmc.executebuiltin('ReloadSkin()')
    else:
        xbmc.executebuiltin('Container.Refresh')
