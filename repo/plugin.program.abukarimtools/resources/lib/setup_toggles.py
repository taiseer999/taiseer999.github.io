# -*- coding: utf-8 -*-
"""
setup_toggles.py - Installation Wizard: every Toggles-menu switch on one page (4.7.9).

The Toggles menu holds one entry per feature, each with its own dialogs,
confirmations and (for the tabs and Font Size) its own Kodi restart. The
wizard asks them all on ONE page instead (toggle_ui.option_list), at the end
of the questions, and applies them silently in the 'toggles' step - no
dialog, no restart of its own: setup ends with a restart anyway.

    rows(answers)  -> the page rows for this box (Skin Selection is left out)
    ask(answers)   -> {key: value} of the rows the user CHANGED only
    apply(changes) -> (status, detail, changed)

Only changed rows are kept: a backup restored in the same setup keeps its
own values for everything the user did not touch on the page.

Rows that need Arctic Fuse 3 are listed only while AF3 is the active skin
(the Skin Installer runs before the questions, so the skin is known here).
"""

import os

import xbmc
import xbmcgui

from resources.lib.i18n import T

AF3 = 'skin.arctic.fuse.3'
ICON_SKINS = ('skin.arctic.fuse.3', 'skin.arctic.zephyr.rounded')
TABS = (('dplex', '1104', 30970), ('korean', '1103', 30971))


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools SetupToggles] %s' % msg, level)


def _af3_active():
    return xbmc.getSkinDir() == AF3


# ---------------------------------------------------------------------------
# current values
# ---------------------------------------------------------------------------

def _icons_dirs():
    from resources.lib import icons_toggle
    skin = icons_toggle._active_skin()
    if not skin:
        return None
    extras = icons_toggle._extras(skin)
    dirs = tuple(os.path.join(extras, n) for n in ('icons', 'icons_color', 'icons_bw'))
    return dirs if all(os.path.isdir(d) for d in dirs) else None


def _icons_colored():
    from resources.lib import icons_toggle
    live, color, bw = _icons_dirs()
    return icons_toggle._current_mode(color, bw, live) != 'mono'


def _lucent_rows(answers):
    """Glass Theme rows: add-ons on the box or ticked in the Add-on Portal."""
    from resources.lib import lucent_toggle
    ticked = set(answers.get('addons') or ())
    out = []
    for prof, aid, label in lucent_toggle.ADDONS:
        if aid in ticked or xbmc.getCondVisibility('System.HasAddon(%s)' % aid):
            out.append(('lucent.' + prof, T(30973) % label, lucent_toggle.enabled(prof), None))
    if out:
        st = lucent_toggle._load()
        out.append(('lucent.' + lucent_toggle.LAYER1, T(30811),
                    bool(st.get(lucent_toggle.LAYER1, True)), None))
        out.append(('lucent.' + lucent_toggle.SEARCH, T(30814),
                    lucent_toggle.search_on(), None))
    return out


def rows(answers):
    out = []
    af3 = _af3_active()
    if af3:
        from resources.lib import tab_toggle
        for key, slot, lab in TABS:
            out.append((key, T(lab), bool(tab_toggle._current_state(slot)), None))
    try:
        if _icons_dirs():
            out.append(('icons', T(30972), _icons_colored(), None))
    except Exception as e:
        _log('icons row left out: %s' % e, xbmc.LOGWARNING)
    try:
        out += _lucent_rows(answers)
    except Exception as e:
        _log('Glass Theme rows left out: %s' % e, xbmc.LOGWARNING)
    if af3:
        from resources.lib.af3_trailers import config as tcfg
        from resources.lib import af3_waves_toggle, af3_lucent_toggle, af3_plotright_toggle
        out.append(('trailers', T(30430), bool(tcfg.load()['enabled']), None))
        out.append(('waves', T(30603), bool(af3_waves_toggle.waves_on()), None))
        out.append(('af3_lucent', T(30850), af3_lucent_toggle.get_mode(),
                    [(m, T(30857) if m == 'off' else T(l))
                     for m, _c, l in af3_lucent_toggle.MODES]))
        out.append(('plotright', T(30890), bool(af3_plotright_toggle.plot_right_on()), None))
    from resources.lib import font_scale
    out.append(('font_scale', T(30740), font_scale.get_mode(),
                [(m, T(l)) for m, _f, l in font_scale.MODES]))
    return out


def ask(answers, prev=None):
    """The page. prev = the changes from an earlier round (Change answers)."""
    rs = rows(answers)
    start = {k: v for k, _l, v, _c in rs}
    if prev:
        rs = [(k, l, prev.get(k, v), c) for k, l, v, c in rs]
    from resources.lib import toggle_ui
    picked = toggle_ui.option_list(T(30974), rs)
    changes = {k: v for k, v in picked.items() if start.get(k) != v}
    _log('page: %d row(s), changed: %s' % (len(rs), changes or 'nothing'))
    return changes


def summary(changes, answers=None):
    if not changes:
        return T(30975)
    try:
        names = {k: l for k, l, _v, _c in rows(answers or {})}
    except Exception:
        names = {}
    parts = []
    for k, v in changes.items():
        if isinstance(v, bool):
            parts.append('%s: %s' % (names.get(k, k), T(30436) if v else T(30437)))
        else:
            parts.append('%s: %s' % (names.get(k, k), _choice_label(k, v)))
    return ', '.join(parts)


def _choice_label(key, value):
    try:
        if key == 'font_scale':
            from resources.lib import font_scale
            return font_scale.mode_label(value)
        if key == 'af3_lucent':
            from resources.lib import af3_lucent_toggle
            return af3_lucent_toggle.mode_label(value)
    except Exception:
        pass
    return str(value)


# ---------------------------------------------------------------------------
# apply (silent: no dialogs, no restart)
# ---------------------------------------------------------------------------

def _set_tab(slot, key, on):
    from resources.lib import tab_toggle as tt
    src = os.path.join(tt.ADDON_PATH, 'resources', 'data', key,
                       'settings_on.xml' if on else 'settings_off.xml')
    snapshot = tt._read(src)
    if os.path.isfile(tt.TARGET):
        merged, n = tt._merge_slot(tt._read(tt.TARGET), snapshot, slot)
        tt._write_atomic(tt.TARGET, merged)
    else:
        tt._write_atomic(tt.TARGET, snapshot)
        n = -1
    if _af3_active():           # in-memory copy, so the shutdown flush keeps it
        setting = 'homeswitcher.%s.toggle' % slot
        xbmc.executebuiltin('Skin.SetString(%s,true)' % setting if on
                            else 'Skin.Reset(%s)' % setting)
    return 'slot %s: %d setting(s)' % (slot, n)


def _set_icons(colored):
    from resources.lib import icons_toggle as it
    live, color, bw = _icons_dirs()
    n = it._apply(color if colored else bw, live)
    xbmc.executebuiltin('Skin.SetString(NodeIcons.Mode,%s)' % ('color' if colored else 'mono'))
    it._bust_texture_cache(live)
    return '%d icons' % n


def _set_lucent(sub):
    """sub: {profile / 'layer1' / 'search': bool} - same order as Toggles."""
    from resources.lib import lucent_toggle as lt
    states = lt._load()
    for p, _a, _l in lt.ADDONS:
        states.setdefault(p, lt.enabled(p))
    notes, failed = [], []
    search_was = lt.search_on()
    for p, aid, label in lt.ADDONS:
        if p not in sub:
            continue
        states[p] = bool(sub[p])
        if xbmc.getCondVisibility('System.HasAddon(%s)' % aid):
            ok, msg = lt._set(p, aid, states[p])
            _log('Glass Theme %s -> %s: %s' % (label, sub[p], msg))
            if not ok:
                failed.append(label)
        notes.append('%s %s' % (label, 'on' if sub[p] else 'off'))
    if lt.LAYER1 in sub:
        states[lt.LAYER1] = bool(sub[lt.LAYER1])
        notes.append('totals %s' % ('on' if sub[lt.LAYER1] else 'off'))
    if lt.SEARCH in sub:
        states[lt.SEARCH] = bool(sub[lt.SEARCH])
    lt._save(states)            # before _set_search: the patcher reads it
    if lt.SEARCH in sub and bool(sub[lt.SEARCH]) != search_was:
        if not lt._set_search(bool(sub[lt.SEARCH])):
            failed.append('Search All')
        notes.append('search %s' % ('on' if sub[lt.SEARCH] else 'off'))
    if failed:
        raise RuntimeError('Glass Theme failed for %s' % ', '.join(failed))
    return ', '.join(notes)


def _set_trailers(on):
    from resources.lib.af3_trailers import config as tcfg
    from resources.lib import af3_trailers_toggle as at
    cfg = tcfg.load()
    cfg['enabled'] = bool(on)
    tcfg.save(cfg)
    if on:
        at._ensure_engine()
    return 'trailers %s' % ('on' if on else 'off')


def _set_waves(on):
    from resources.lib import af3_waves_toggle as aw
    # the switch reads "waves shown"; the skin bool means "no waves"
    xbmc.executebuiltin('Skin.Reset(%s)' % aw.SETTING if on
                        else 'Skin.SetBool(%s)' % aw.SETTING)
    return 'waves %s' % ('on' if on else 'off')


def _set_plotright(on):
    from resources.lib import af3_plotright_toggle as ap
    if on:
        xbmc.executebuiltin('Skin.SetBool(%s)' % ap.SETTING)
        if not ap._tworow_on():
            xbmc.executebuiltin('Skin.SetBool(%s)' % ap.TWOROW)
            ap._save(dict(ap._load(), tworow_set=True))
    else:
        xbmc.executebuiltin('Skin.Reset(%s)' % ap.SETTING)
        state = ap._load()
        if state.pop('tworow_set', False) and ap._tworow_on():
            xbmc.executebuiltin('Skin.Reset(%s)' % ap.TWOROW)
        ap._save(state)
    return 'plot right %s' % ('on' if on else 'off')


def _set_af3_lucent(mode):
    from resources.lib import af3_lucent_toggle as al
    if mode != 'off' and not al._files_present():
        raise RuntimeError('Lucent Look files are not in the skin')
    al.apply(mode)
    return 'Lucent Look %s' % mode


def _set_font(mode):
    from resources.lib import font_scale as fs
    fs.set_mode(mode)
    fs.guard_reset()
    skin_dir = fs._active_skin_dir()
    if not skin_dir:
        return 'font size %s (saved, no skin folder)' % mode
    written, errors = fs.apply(skin_dir, mode)
    if errors:
        raise RuntimeError('font size: %s' % '; '.join(errors))
    return 'font size %s (%d file(s))' % (mode, written)


def apply(changes):
    """Returns (status, detail, changed). Each row is fenced on its own."""
    if not changes:
        return 'skipped', 'no changes', False
    af3_keys = ('dplex', 'korean', 'trailers', 'waves', 'af3_lucent', 'plotright')
    if any(k in changes for k in af3_keys) and not _af3_active():
        _log('Arctic Fuse 3 is not the active skin - its rows wait', xbmc.LOGWARNING)
    else:
        try:                    # AF3 rows read the AF3 patch files: put them in first
            from resources.lib import patcher
            if any(k in changes for k in af3_keys + ('font_scale',)):
                patcher.apply_set(addon_ids=[AF3])
        except Exception as e:
            _log('AF3 patch run failed: %s' % e, xbmc.LOGWARNING)
    done, failed = [], []
    lucent_sub = {k.split('.', 1)[1]: v for k, v in changes.items() if k.startswith('lucent.')}
    jobs = []
    for key, slot, _lab in TABS:
        if key in changes:
            jobs.append((key, lambda s=slot, k=key: _set_tab(s, k, changes[k])))
    if 'icons' in changes:
        jobs.append(('icons', lambda: _set_icons(changes['icons'])))
    if lucent_sub:
        jobs.append(('glass', lambda: _set_lucent(lucent_sub)))
    for key, fn in (('trailers', _set_trailers), ('waves', _set_waves),
                    ('plotright', _set_plotright), ('af3_lucent', _set_af3_lucent),
                    ('font_scale', _set_font)):
        if key in changes:
            jobs.append((key, lambda f=fn, k=key: f(changes[k])))
    for key, fn in jobs:
        if key in af3_keys and not _af3_active():
            failed.append('%s (Arctic Fuse 3 not active)' % key)
            continue
        try:
            note = fn()
            done.append(note)
            _log('%s: %s' % (key, note))
        except Exception as e:
            failed.append('%s (%s)' % (key, e))
            _log('%s failed: %s' % (key, e), xbmc.LOGWARNING)
    detail = '; '.join(done)
    if failed:
        detail = (detail + ' - ' if detail else '') + 'failed: ' + ', '.join(failed)
    return ('failed' if failed else 'ok'), detail, bool(done)
