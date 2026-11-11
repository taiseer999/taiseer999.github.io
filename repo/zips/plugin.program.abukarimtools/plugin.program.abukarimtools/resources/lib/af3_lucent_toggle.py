# -*- coding: utf-8 -*-
"""
af3_lucent_toggle.py - ABUKARIM TOOLS (4.6.8)

Toggles entry "AF3: Lucent Look" - phase 1 of the Lucent port to Arctic
Fuse 3 (design after the Lucent skin by djdirty60):

  Off                  AF3 exactly as it is (bool reset, previous colours back)
  Lucent Glass         navy glass colour theme + glass dialog frames
  Lucent Glass AMOLED  the same on true black

The always-on patcher entries (patcher.py, "AF3: Lucent Look") install the two
colour themes into skin.arctic.fuse.3/colors/, the glass textures into
media/abk_lucent/, and make Part_Background draw the Lucent glass body while
the skin bool abk.lucent is set. This module only flips that bool and the
lookandfeel.skincolors setting; changing skincolors makes Kodi reload the skin
by itself, so there is at most ONE skin reload per switch.
"""
import json
import os

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

SKIN_ID = 'skin.arctic.fuse.3'
SETTING = 'abk.lucent'
OWNFOCUS = 'abk.lucent.ownfocus'      # 4.6.12: keep the user's focus colour
TITLE = 'ABUKARIM TOOLS'
COLORS_KEY = 'lookandfeel.skincolors'
# (mode, colour theme file name without .xml, label id)
MODES = (('off', None, 30851), ('glass', 'Lucent Glass', 30852), ('amoled', 'Lucent Glass AMOLED', 30853))
OURS = {c for _m, c, _l in MODES if c}
_STATE = os.path.join(xbmcvfs.translatePath('special://profile/addon_data/'),
                      'plugin.program.abukarimtools', 'af3_lucent.json')


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools AF3 Lucent] %s' % msg, level)


def _rpc(method, params):
    try:
        out = json.loads(xbmc.executeJSONRPC(json.dumps(
            {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})))
    except Exception as e:
        _log('%s failed: %s' % (method, e), xbmc.LOGWARNING)
        return None
    if 'error' in out:
        _log('%s error: %s' % (method, out['error']), xbmc.LOGWARNING)
        return None
    return out.get('result')


def _colors():
    res = _rpc('Settings.GetSettingValue', {'setting': COLORS_KEY})
    return (res or {}).get('value') or 'SKINDEFAULT'


def _set_colors(value):
    return _rpc('Settings.SetSettingValue', {'setting': COLORS_KEY, 'value': value}) is not None


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


def get_mode():
    """'off' / 'glass' / 'amoled' (AF3 must be the active skin to tell)."""
    if xbmc.getSkinDir() != SKIN_ID or not xbmc.getCondVisibility('Skin.HasSetting(%s)' % SETTING):
        return 'off'
    return 'amoled' if _colors() == 'Lucent Glass AMOLED' else 'glass'


def own_focus():
    """True when the user keeps their own focus colour under the Lucent Look."""
    return bool(xbmc.getCondVisibility('Skin.HasSetting(%s)' % OWNFOCUS))


def set_own_focus(on):
    """Live: the AF3 focus variables read the bool on every frame, no reload."""
    xbmc.executebuiltin('Skin.SetBool(%s)' % OWNFOCUS if on else 'Skin.Reset(%s)' % OWNFOCUS)
    _log('focus colour: %s' % ('own' if on else 'Lucent white'))


def mode_label(mode=None):
    mode = mode or get_mode()
    if mode == 'off':
        return T(30857)
    return T(dict((m, l) for m, _c, l in MODES)[mode])


def _ensure_patch():
    """(installed_ok, xml_changed) - applies the AF3 entries now."""
    try:
        from resources.lib import patcher
        _ok, failed, changed, _r = patcher.apply_set(addon_ids=[SKIN_ID])
        return failed == 0, changed > 0
    except Exception as exc:
        _log('skin patch failed: %s' % exc, xbmc.LOGWARNING)
        return False, False


def _files_present():
    skin = xbmcvfs.translatePath('special://home/addons/%s/' % SKIN_ID)
    need = [os.path.join(skin, 'colors', c + '.xml') for c in OURS] + \
           [os.path.join(skin, 'media', 'abk_lucent', t)
            for t in ('panel.png', 'panel_edge.png', 'panel_shadow.png', 'pill6.png', 'pill60.png')] + \
           [os.path.join(skin, '1080i', 'Includes_ABK_Lucent.xml')] + \
           [os.path.join(skin, 'media', 'abk_lucent', 'icons', i + '.png')          # 4.6.14
            for i in ('play', 'pause', 'forward', 'rewind', 'prev', 'next', 'stop', 'info',
                      'audio', 'subtitles', 'video', 'list', 'record',
                      'subcycler', 'dexsync', 'substyle', 'ppi')]   # 4.6.22
    # 4.6.9: the player include file must also be registered, or the
    # Lucent player includes would be missing once the bool is set
    marks = (('Dialog_Parts.xml', '<!-- ABUKARIM: Lucent glass dialogs -->'),
             ('Includes.xml', 'Includes_ABK_Lucent.xml'),
             ('Includes_Images.xml', '<!-- ABUKARIM: Lucent icons'))
    for name, mark in marks:
        try:
            with open(os.path.join(skin, '1080i', name), 'r', encoding='utf-8') as f:
                if mark not in f.read():
                    return False
        except Exception:
            return False
    return all(os.path.isfile(p) for p in need)


def apply(mode):
    """Switch to mode; returns the notification text."""
    cur_colors = _colors()
    state = _load()
    if mode == 'off':
        xbmc.executebuiltin('Skin.Reset(%s)' % SETTING)
        target = state.get('prev_colors') or 'SKINDEFAULT'
        if cur_colors not in OURS:          # the user picked other colours meanwhile: keep them
            target = cur_colors
        msg = T(30855)
    else:
        if cur_colors not in OURS:          # remember what to go back to
            state['prev_colors'] = cur_colors
            _save(state)
        xbmc.executebuiltin('Skin.SetBool(%s)' % SETTING)
        target = dict((m, c) for m, c, _l in MODES)[mode]
        msg = T(30854) % mode_label(mode)
    _log('mode %s: colours %s -> %s' % (mode, cur_colors, target))
    if target != cur_colors:
        if not _set_colors(target):          # Kodi reloads the skin itself on success
            return msg, True
        return msg, False
    return msg, None


def run():
    if not xbmc.getCondVisibility('System.HasAddon(%s)' % SKIN_ID):
        xbmcgui.Dialog().ok(TITLE, T(30440))          # AF3 is not installed
        return
    if xbmc.getSkinDir() != SKIN_ID:
        xbmcgui.Dialog().ok(TITLE, T(30602))          # switch to AF3 first
        return
    current = get_mode()
    pre = [m for m, _c, _l in MODES].index(current)
    labels = [T(l) for _m, _c, l in MODES]
    # 4.6.12: last row - Lucent white focus or the user's own focus colour
    labels.append(T(30859) if own_focus() else T(30858))
    pick = xbmcgui.Dialog().select(T(30850), labels, preselect=pre)
    if pick < 0:
        return
    if pick == len(MODES):
        set_own_focus(not own_focus())
        xbmcgui.Dialog().notification(TITLE, T(30859) if own_focus() else T(30858),
                                      xbmcgui.NOTIFICATION_INFO, 3000)
        xbmc.executebuiltin('Container.Refresh')
        return
    if MODES[pick][0] == current:
        return
    mode = MODES[pick][0]
    _ok, xml_changed = _ensure_patch()
    if mode != 'off' and not _files_present():
        _log('files missing after the patch run', xbmc.LOGWARNING)
        xbmcgui.Dialog().ok(TITLE, T(30856))
        return
    msg, reload_self = apply(mode)
    xbmcgui.Dialog().notification(TITLE, msg, xbmcgui.NOTIFICATION_INFO, 3000)
    # One reload at most: a colour change already reloads the skin.
    if reload_self or (reload_self is None and xml_changed):
        xbmc.sleep(300)
        xbmc.executebuiltin('ReloadSkin()')
    elif reload_self is None:
        xbmc.executebuiltin('Container.Refresh')
