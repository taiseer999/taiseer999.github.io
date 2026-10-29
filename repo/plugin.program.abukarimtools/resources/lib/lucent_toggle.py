# -*- coding: utf-8 -*-
"""
lucent_toggle.py - ABUKARIM TOOLS (3.4.39)

Toggles entry "Lucent Theme": one on/off switch per add-on (Fen Light,
Red Light, POV, Umbrella). Until 3.4.38 the theme was a single entry in the
Apply Patches checklist; it is now a Toggles-menu feature, like the AF3
trailers. The switches are applied straight away (install or restore the
stock windows), and the patcher's 'feature' gate keeps each add-on in the
chosen state after updates (watchdog sweeps re-apply only switched-on ones,
and _revert_disabled restores switched-off ones).

State: addon_data/plugin.program.abukarimtools/lucent.json
       {"fenlight": true, "redlight": false, ...}
A profile with no saved state follows the old patch toggle: on unless the
user had switched "Lucent Theme" off in the Apply Patches checklist.
"""
import json
import os

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

TITLE = 'ABUKARIM TOOLS'
_STATE = os.path.join(xbmcvfs.translatePath('special://profile/addon_data/'),
                      'plugin.program.abukarimtools', 'lucent.json')
# (profile, add-on id, label) in menu order
ADDONS = (('fenlight', 'plugin.video.fenlight', 'Fen Light'),
          ('redlight', 'plugin.video.redlight', 'Red Light'),
          ('pov', 'plugin.video.pov', 'POV'),
          ('umbrella', 'plugin.video.umbrella', 'Umbrella'))
_LEGACY_TOGGLE = 'lucent_sources'


def _log(msg):
    xbmc.log('[AbukarimTools Lucent] %s' % msg, xbmc.LOGINFO)


def _load():
    try:
        with open(_STATE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(states):
    try:
        os.makedirs(os.path.dirname(_STATE), exist_ok=True)
        with open(_STATE, 'w', encoding='utf-8') as f:
            json.dump(states, f, indent=1, sort_keys=True)
        return True
    except Exception as e:
        _log('could not save %s: %s' % (_STATE, e))
        return False


def _legacy_default():
    """3.4.32-3.4.38 had one patch toggle (on by default) - keep its state."""
    try:
        from resources.lib import patcher
        return _LEGACY_TOGGLE not in patcher._load_disabled()
    except Exception:
        return True


COLORED = 'colored'     # state key: colored resolution badges + service icons
LAYER1 = 'layer1'       # state key: totals screen before the stream list (Fen Light / Red Light)
SEARCH = 'search'       # state key: Search All (one stream list from every add-on, 3.4.48)


def search_on():
    return bool(_load().get(SEARCH, True))


def _set_search(on):
    """Red Light bridge + TMDbHelper "AB Search All" player, in or out right now."""
    from resources.lib import patcher
    msgs = []
    if on:
        for p in patcher._all_patches():
            if p.get('feature') == 'ab_search':
                try:
                    ok, msg = patcher._apply_patch(p)
                except Exception as e:
                    ok, msg = False, str(e)
                msgs.append((ok, msg))
    else:
        msgs = list(patcher._revert_search())
    for ok, msg in msgs:
        _log('Search All %s: %s' % ('ON' if on else 'OFF', msg))
    return all(ok for ok, _m in msgs)


def colored_on():
    return False                        # 4.6.0: option removed, always plain


def enabled(profile):
    states = _load()
    if profile in states:
        return bool(states[profile])
    return _legacy_default()


def installed():
    return [(p, a, l) for p, a, l in ADDONS
            if xbmc.getCondVisibility('System.HasAddon(%s)' % a)]


def summary():
    """label2 for the Toggles entry, e.g. '2 / 4 On'."""
    rows = installed()
    if not rows:
        return None
    on = sum(1 for p, _a, _l in rows if enabled(p))
    return T(30802) % (on, len(rows))


def _set(profile, addon_id, on):
    """Install (on) or restore the stock windows (off) right now."""
    from resources.lib import lucent_sources, patcher
    path = patcher._resolve_addon_dir(addon_id)
    if not path:
        return False, '%s not installed' % addon_id
    if on:
        return lucent_sources.apply(path, profile)
    res = lucent_sources.revert(path, profile)
    return res if res else (True, 'already stock')


def run():
    rows = installed()
    if not rows:
        xbmcgui.Dialog().ok(TITLE, T(30803))
        return
    current = {p: enabled(p) for p, _a, _l in rows}
    layer1_was = bool(_load().get(LAYER1, True))
    search_was = search_on()
    picked = None
    try:
        from resources.lib import toggle_ui
        picked = toggle_ui.switch_list(
            T(30801), [(p, l, current[p]) for p, _a, l in rows]
            + [(LAYER1, T(30811), layer1_was),
               (SEARCH, T(30814), search_was)],
            confirm_back=(T(30750), T(30751), T(30752)))
    except Exception as e:
        _log('switch list failed: %s' % e)
    if picked is None:
        return
    states = _load()
    for p, _a, _l in ADDONS:            # freeze every profile, installed or not
        states.setdefault(p, enabled(p))
    turned_on, turned_off, failed = [], [], []
    for p, a, label in rows:
        on = bool(picked.get(p, current[p]))
        states[p] = on
        try:
            ok, msg = _set(p, a, on)
        except Exception as e:
            ok, msg = False, str(e)
        _log('%s -> %s: %s' % (label, 'ON' if on else 'OFF', msg))
        if not ok:
            failed.append(label)
        elif 'Patched OK' in msg:           # something was actually written
            (turned_on if on else turned_off).append(label)
    states[COLORED] = False             # 4.6.0: coloured icons removed
    layer1_now = bool(picked.get(LAYER1, layer1_was))
    states[LAYER1] = layer1_now
    if layer1_now != layer1_was:
        _log('totals screen -> %s' % ('ON' if layer1_now else 'OFF'))
    search_now = bool(picked.get(SEARCH, search_was))
    states[SEARCH] = search_now
    _save(states)                       # before _set_search: the patcher reads the feature state
    if search_now != search_was and not _set_search(search_now):
        failed.append(T(30814))
    lines = []
    if turned_on:
        lines.append(T(30804) % ', '.join(turned_on))
    if turned_off:
        lines.append(T(30805) % ', '.join(turned_off))
    if failed:
        lines.append(T(30806) % ', '.join(failed))
    if layer1_now != layer1_was:
        lines.append(T(30812) if layer1_now else T(30813))
    if search_now != search_was:
        lines.append(T(30815) if search_now else T(30816))
    changed = turned_on or turned_off or layer1_now != layer1_was or search_now != search_was
    if changed:
        lines.append(T(30807))
    if failed:
        xbmcgui.Dialog().ok(TITLE, '[CR]'.join(lines))
    elif changed:
        xbmcgui.Dialog().notification(TITLE, '  |  '.join(lines[:-1]), xbmcgui.NOTIFICATION_INFO, 5000)
    xbmc.executebuiltin('Container.Refresh')
