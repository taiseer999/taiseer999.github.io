# -*- coding: utf-8 -*-
"""whats_new.py - ABUKARIM TOOLS (4.8.61)

"What's New" screen: after AB Tools updates, the first time the user opens
the add-on (a tap on it - not a widget, a service run or a RunPlugin from
somewhere else) it shows what changed in the last 10 versions, then the
add-on opens as usual. Shown once per update.

The text is resources/whats_new.json - the final result of each release
(or run of releases), not the in-between fixes that changelog.txt keeps.
English or Arabic follows Kodi's language. The text scrolls by itself;
Up / Down scroll it by hand, OK or Back closes it.

A fresh install (no addon_data yet) does not show it, it only records the
version; a box updated from a version before 4.8.61 has addon_data but no
record, so it sees the screen.
"""
import json
import os

import xbmc
import xbmcgui

from resources.lib import paths
from resources.lib.i18n import T

SEEN = os.path.join(paths.PROFILE, 'whats_new_seen.txt')
DATA = os.path.join(paths.ADDON_PATH, 'resources', 'whats_new.json')
XML = 'abk_whatsnew.xml'
LAST = 10                       # versions shown
S_TITLE, S_HINT = 32218, 32219


def _log(msg):
    xbmc.log('[AB Tools What\'s New] %s' % msg, xbmc.LOGINFO)


def _version():
    import xbmcaddon
    return xbmcaddon.Addon(paths.ADDON_ID).getAddonInfo('version')


def _vt(v):
    out = []
    for part in str(v or '0').split('.'):
        digits = ''.join(c for c in part if c.isdigit())
        out.append(int(digits or 0))
    return tuple(out)


def _read_seen():
    try:
        with open(SEEN, 'r') as f:
            return f.read().strip() or None
    except Exception:
        return None


def _write_seen(v):
    try:
        os.makedirs(paths.PROFILE, exist_ok=True)
        with open(SEEN, 'w') as f:
            f.write(v)
    except Exception as e:
        _log('cannot record %s: %s' % (v, e))


def _fresh_install():
    """No addon_data besides what this run may have made."""
    try:
        names = [n for n in os.listdir(paths.PROFILE) if n != os.path.basename(SEEN)]
    except Exception:
        return True
    return not names


def _arabic():
    try:
        return (xbmc.getLanguage(xbmc.ISO_639_1) or '').lower() == 'ar'
    except Exception:
        return False


def _span(entry):
    a, b = _vt(entry.get('from') or entry['v']), _vt(entry['v'])
    if a[:-1] == b[:-1] and len(a) == len(b):
        return max(1, b[-1] - a[-1] + 1)
    return 1


def entries(current=None, last=LAST):
    """The entries for the newest `last` versions up to `current`."""
    try:
        with open(DATA, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        _log('no data: %s' % e)
        return []
    cur = _vt(current) if current else None
    out, count = [], 0
    for e in data.get('entries', []):
        if cur and _vt(e.get('from') or e['v']) > cur:
            continue                    # newer than this build (never happens)
        out.append(e)
        count += _span(e)
        if count >= last:
            break
    return out


def text(items, arabic):
    key = 'ar' if arabic else 'en'
    blocks = []
    for e in items:
        v = e['v'] if (e.get('from') or e['v']) == e['v'] else '%s - %s' % (e['from'], e['v'])
        lines = e.get(key) or e.get('en') or []
        blocks.append('[B][COLOR FF7FD1FF]v%s[/COLOR][/B]\n%s' % (v, '\n'.join('•  ' + l for l in lines)))
    return '\n\n'.join(blocks)


class _Window(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.props = kwargs.pop('props', {})
        super().__init__(*args, **kwargs)

    def onInit(self):
        for k, v in self.props.items():
            self.setProperty(k, v)
        self.line = 0
        self.box = None
        try:
            self.box = self.getControl(101 if self.props.get('dir') == 'rtl' else 100)
        except Exception:
            pass

    def onAction(self, action):
        aid = action.getId()
        if aid in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN,
                   xbmcgui.ACTION_PAGE_UP, xbmcgui.ACTION_PAGE_DOWN) and self.box:
            step = {xbmcgui.ACTION_MOVE_UP: -2, xbmcgui.ACTION_MOVE_DOWN: 2,
                    xbmcgui.ACTION_PAGE_UP: -10, xbmcgui.ACTION_PAGE_DOWN: 10}[aid]
            self.line = max(0, self.line + step)
            try:
                self.box.scroll(self.line)
            except Exception:
                pass
            return
        if aid in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK,
                              xbmcgui.ACTION_SELECT_ITEM, xbmcgui.ACTION_STOP):
            self.close()

    def onClick(self, control_id):
        self.close()


def show(version=None):
    version = version or _version()
    items = entries(version)
    if not items:
        return False
    arabic = _arabic()
    props = {'title': T(S_TITLE), 'version': 'v' + version, 'hint': T(S_HINT),
             'text': text(items, arabic), 'dir': 'rtl' if arabic else 'ltr'}
    dlg = _Window(XML, paths.ADDON_PATH, 'Default', '1080i', props=props)
    dlg.doModal()
    del dlg
    return True


def maybe_show():
    """Call when the user opened the add-on. Shows the screen once after an
    update; never raises."""
    try:
        cur = _version()
        seen = _read_seen()
        if seen == cur:
            return False
        if seen is None and _fresh_install():
            _write_seen(cur)
            return False
        if seen and _vt(seen) > _vt(cur):
            _write_seen(cur)            # downgrade: nothing new to tell
            return False
        _write_seen(cur)                # recorded first: a crash in the window never repeats it
        _log('updated %s -> %s' % (seen or '?', cur))
        return show(cur)
    except Exception as e:
        _log('failed: %s' % e)
        return False
