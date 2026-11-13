# -*- coding: utf-8 -*-
"""
af3_lucent_colours.py - ABUKARIM TOOLS (4.8.48)

The "Colours" window of Toggles > AF3: Lucent Look (abk_colours.xml):

  - colour schemes (cards): an AF3 colour theme + the highlight it comes
    with. Picking a card sets that highlight at once; the colour theme
    itself is applied when the window closes, because a colour theme change
    reloads the skin (one reload at most).
  - highlight colours (swatches): change only the highlight, live.
  - more colours (palette): Lucent's 14 colour themes, a custom hex colour,
    or the user's own Arctic Fuse 3 focus colour.
  - turn off: the Lucent Look off, previous colours back.

    show() -> None   (everything is applied here)
"""
import re

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib import af3_lucent_toggle as al
from resources.lib.af3_lucent_schemes import SCHEMES, SWATCHES, LUCENT_ACCENTS, text_on
from resources.lib.i18n import T

ADDON_ID = 'plugin.program.abukarimtools'
XML = 'abk_colours.xml'
_BACK = (9, 10, 92, 216, 247, 257, 275, 61467, 61448)


def _log(msg):
    xbmc.log('[AbukarimTools AF3 Colours] %s' % msg, xbmc.LOGINFO)


class ColoursWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.media = kwargs.get('media', '')
        self.current = al.get_mode()                       # 'off' or a scheme id
        self.pending = None if self.current == 'off' else self.current
        self.turn_off = False

    # -- state --------------------------------------------------------------
    def _refresh(self):
        focus = al.highlight()
        own = al.own_focus()
        try:
            cards = self.getControl(100)
            for i, sc in enumerate(SCHEMES):
                cards.getListItem(i).setProperty('selected', 'true' if sc['id'] == self.pending else '')
            sw = self.getControl(200)
            for i, (col, _txt) in enumerate(SWATCHES):
                sw.getListItem(i).setProperty('selected', 'true' if (not own and col == focus) else '')
        except Exception as e:
            _log('refresh: %s' % e)
        custom = own or (focus and focus not in [c for c, _t in SWATCHES])
        self.setProperty('abk.col.custom', 'true' if custom and not own else '')
        self.setProperty('abk.col.customcolour', focus or '')

    def onInit(self):
        self.setProperty('abk.col.title', T(32216))
        self.setProperty('abk.col.header', T(32217))
        self.setProperty('abk.col.hint', T(32218))
        self.setProperty('abk.col.off', T(32219))
        self.setProperty('abk.col.on', '' if self.current == 'off' else 'true')
        cards = []
        for sc in SCHEMES:
            li = xbmcgui.ListItem(T(sc['label']), offscreen=True)
            li.setArt({'thumb': '%scard_%s.png' % (self.media, sc['id'])})
            cards.append(li)
        swatches = []
        for col, _txt in SWATCHES:
            li = xbmcgui.ListItem('', offscreen=True)
            li.setProperty('colour', col)
            swatches.append(li)
        self.getControl(100).addItems(cards)
        self.getControl(200).addItems(swatches)
        ids = [sc['id'] for sc in SCHEMES]
        try:
            self.getControl(100).selectItem(ids.index(self.pending or 'glass'))
            self.setFocusId(100)
        except Exception:
            pass
        self._refresh()

    # -- actions ------------------------------------------------------------
    def onClick(self, cid):
        if cid == 100:
            sc = SCHEMES[self.getControl(100).getSelectedPosition()]
            self.pending = sc['id']
            al.set_highlight(sc['focus'], sc['onfocus'])
            self.setProperty('abk.col.on', 'true')
        elif cid == 200:
            col, txt = SWATCHES[self.getControl(200).getSelectedPosition()]
            al.set_highlight(col, txt)
        elif cid == 300:
            self._palette()
        elif cid == 400:
            self.turn_off = True
            self.close()
            return
        elif cid == 900:
            self.close()
            return
        self._refresh()

    def _palette(self):
        labels = [T(l) for _i, l, _c, _t in LUCENT_ACCENTS] + [T(32221), T(32222)]
        pick = xbmcgui.Dialog().select(T(32220), labels)
        if pick < 0:
            return
        if pick < len(LUCENT_ACCENTS):
            _i, _l, col, txt = LUCENT_ACCENTS[pick]
            al.set_highlight(col, txt)
        elif pick == len(LUCENT_ACCENTS):
            cur = (al.highlight() or 'ff00b8d4')[-6:].upper()
            val = xbmcgui.Dialog().input(T(32221), cur).strip().lstrip('#')
            if not val:
                return
            if not re.fullmatch(r'[0-9a-fA-F]{6}', val):
                xbmcgui.Dialog().notification(al.TITLE, T(32244), xbmcgui.NOTIFICATION_WARNING, 3000)
                return
            col = 'ff' + val.lower()
            al.set_highlight(col, text_on(col))
        else:
            al.set_own_focus(True)

    def onAction(self, action):
        if action.getId() in _BACK:
            self.close()


def show():
    addon = xbmcaddon.Addon(ADDON_ID)
    path = addon.getAddonInfo('path')
    media = path.rstrip('/\\') + '/resources/skins/Default/media/abk_col/'
    win = ColoursWindow(XML, path, 'Default', '1080i', media=media)
    try:
        win.doModal()
        current, pending, turn_off = win.current, win.pending, win.turn_off
    finally:
        del win
    if turn_off:
        target = 'off'
    elif pending and pending != current:
        target = pending
    else:
        return None
    _log('scheme %s -> %s' % (current, target))
    return target
