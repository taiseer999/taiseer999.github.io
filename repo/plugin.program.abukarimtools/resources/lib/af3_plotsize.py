# -*- coding: utf-8 -*-
"""
af3_plotsize.py - ABUKARIM TOOLS (4.7.41, layout 4.8.2)

Toggles entry "AF3: Plot Text Size" - Large / Small (a selection dialog).

The "AF3: Vertical Plot" patches (patcher.py) pass a plotfont param at five
call sites: Home hub, Home Spotlight, OSD seek-bar info, library views and
combined views. Until 4.7.40 that was always font_mini_plot (a fixed smaller
plot). Now the size is a choice:

    normal  font_main_plot   "Large": AF3's own plot font (default), 3 lines
    small   font_mini_plot   the old smaller plot, 2 lines

4.8.2 - the plot box follows the size on Home (hub + Spotlight) and in the
OSD: Large = box 120 px (3 whole lines) 50 px under the genre line, Small =
box 80 px 54 px under it (as before). The OSD block also gets the matching
height (top + box), so the ratings row below moves down instead of being
drawn over the plot (AF3's block there is 120, the plot ended at 134).

The choice is saved in addon_data (af3_plotsize.json). reconcile() rewrites
the plotfont value at those call sites in the installed AF3; patcher.apply_set
runs it after every patch pass, so a skin update or a fresh patch run keeps
the chosen size. Fonts are read when the skin loads, so a change reloads the
skin. "Plot on the Right" has its own box sized to font_mini_plot lines and is
not changed.
"""
import json
import os
import re

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

SKIN_ID = 'skin.arctic.fuse.3'
TITLE = 'ABUKARIM TOOLS'
DEFAULT = 'normal'
SIZES = (('normal', 'font_main_plot', 32114),
         ('small', 'font_mini_plot', 32115))
# plot box per size: (top under the genre line, box height); OSD block = top + box
LAYOUT = {'normal': (50, 120), 'small': (54, 80)}
_CHOICE = {'normal': 32125, 'small': 32126}
_FONT = {k: f for k, f, _l in SIZES}
_LABEL = {k: l for k, _f, l in SIZES}
# the call sites the Vertical Plot patches write (Includes_Info.xml only holds
# the font_main_plot defaults of the Info_* chain - never touched)
FILES = ('Includes_Hubs.xml', 'Includes_OSD.xml', 'Includes_Views.xml', 'Includes_Views_Combined.xml')
_SITE_RE = re.compile(r'(<param name="plotfont">)font_(?:mini|main)_plot(</param>)')
_HUB_RE = re.compile(r'(<param name="plottop">)\d+(</param>\s*<param name="plotboxh">)\d+'
                     r'(</param>  <!-- ABUKARIM: plot gap \((?:hub|spotlight)\) -->)')
_OSD_RE = re.compile(r'(<!-- ABUKARIM: vertical plot \(osd\) -->\s*<param name="plotfont">font_\w+</param>'
                     r'\s*<param name="plottop">)\d+(</param>\s*<param name="plotboxh">)\d+(</param>)'
                     r'(?:\n[ \t]*<param name="height">\d+</param>  <!-- ABUKARIM: plot height \(osd\) -->)?')
_OSD_INDENT = ' ' * 20
_STATE = os.path.join(xbmcvfs.translatePath('special://profile/addon_data/'),
                      'plugin.program.abukarimtools', 'af3_plotsize.json')


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools PlotSize] %s' % msg, level)


def get_size():
    try:
        with open(_STATE, 'r', encoding='utf-8') as f:
            size = json.load(f).get('size')
        return size if size in _FONT else DEFAULT
    except Exception:
        return DEFAULT


def set_size(size):
    try:
        os.makedirs(os.path.dirname(_STATE), exist_ok=True)
        with open(_STATE, 'w', encoding='utf-8') as f:
            json.dump({'size': size}, f)
    except Exception as e:
        _log('state not saved: %s' % e, xbmc.LOGWARNING)


def mode_label(size=None):
    return T(_LABEL[size or get_size()])


def _skin_dir():
    try:
        from resources.lib import patcher
        d = patcher._resolve_addon_dir(SKIN_ID)
        if d:
            return d
    except Exception:
        pass
    d = xbmcvfs.translatePath('special://home/addons/%s/' % SKIN_ID)
    return d if os.path.isdir(d) else None


def reconcile(skin_dir=None):
    """Put the chosen plot font on the Vertical Plot call sites.
    Returns (ok, msg, wrote, sites)."""
    skin_dir = skin_dir or _skin_dir()
    if not skin_dir:
        return True, '[plot size] AF3 not installed - skipping.', False, 0
    size = get_size()
    font = _FONT[size]
    top, box = LAYOUT[size]
    wrote, sites = False, 0
    for name in FILES:
        path = os.path.join(skin_dir, '1080i', name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            sites += len(_SITE_RE.findall(content))
            new = _SITE_RE.sub(r'\g<1>%s\g<2>' % font, content)
            new = _HUB_RE.sub(r'\g<1>%d\g<2>%d\g<3>' % (top, box), new)
            new = _OSD_RE.sub(lambda m: '%s%d%s%d%s\n%s<param name="height">%d</param>  <!-- ABUKARIM: plot height (osd) -->'
                              % (m.group(1), top, m.group(2), box, m.group(3), _OSD_INDENT, top + box), new)
            if new != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new)
                wrote = True
        except Exception as e:
            return False, '[plot size] %s: %s' % (name, e), wrote, sites
    if wrote:
        return True, '[plot size] Patched OK: %s, box %d/%d on %d plot(s).' % (font, top, box, sites), True, sites
    return True, '[plot size] %s, box %d/%d on %d plot(s) - nothing to change.' % (font, top, box, sites), False, sites


def run():
    if not xbmc.getCondVisibility('System.HasAddon(%s)' % SKIN_ID):
        xbmcgui.Dialog().ok(TITLE, T(30440))          # AF3 is not installed
        return
    current = get_size()
    keys = [k for k, _f, _l in SIZES]
    pick = xbmcgui.Dialog().select(T(32113), [T(_CHOICE[k]) for k in keys], preselect=keys.index(current))
    if pick < 0:
        return
    size = keys[pick]
    set_size(size)
    try:                                              # Vertical Plot patches in place first
        from resources.lib import patcher
        patcher.apply_set(addon_ids=[SKIN_ID])       # runs reconcile() at the end
    except Exception as e:
        _log('patch run failed: %s' % e, xbmc.LOGWARNING)
    ok, msg, _wrote, sites = reconcile()
    _log('%s -> %s' % (size, msg))
    if not ok or not sites:
        xbmcgui.Dialog().ok(TITLE, T(32117))
        xbmc.executebuiltin('Container.Refresh')
        return
    xbmcgui.Dialog().notification(TITLE, T(32116) % mode_label(size), xbmcgui.NOTIFICATION_INFO, 3000)
    if xbmc.getSkinDir() == SKIN_ID:
        try:                                          # reloading now: no second reload later
            from resources.lib import patcher
            if os.path.exists(patcher._SKIN_RELOAD_MARKER):
                os.remove(patcher._SKIN_RELOAD_MARKER)
        except Exception:
            pass
        xbmc.sleep(300)
        xbmc.executebuiltin('ReloadSkin()')
    else:
        xbmc.executebuiltin('Container.Refresh')
