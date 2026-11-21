# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""grid_ui.py - ABUKARIM TOOLS (4.9.3)

A choice with pictures as a grid of cards (abk_grid.xml), instead of a
list - first used by "AF3: OSD Flags Style" (4.9.1).

    pick(title, items, preselect=0) -> index, or -1 on Back

items: [{'label', 'desc', 'art', 'fit': 'fill'|'keep', 'current': bool}]
'fill' stretches the picture over the top of the card (made-to-measure
previews, 560x270); 'keep' shows it whole on the dark card (icons, skin
art). If the window cannot be opened, the plain list dialog is used.
"""
import xbmc
import xbmcgui

from resources.lib import paths

XML = 'abk_grid.xml'


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools Grid] %s' % msg, level)


class _Grid(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.items = kwargs.pop('items')
        self.start = kwargs.pop('start', 0)
        self.title = kwargs.pop('title', '')
        self.pick = -1
        super().__init__(*args, **kwargs)

    def onInit(self):
        self.setProperty('title', self.title)
        panel = self.getControl(100)
        panel.reset()
        panel.addItems(self.items)
        panel.selectItem(self.start)
        self.setFocusId(100)

    def onClick(self, control_id):
        if control_id == 100:
            self.pick = self.getControl(100).getSelectedPosition()
            self.close()

    def onAction(self, action):
        if action.getId() in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK):
            self.close()


def _list_items(items):
    out = []
    for it in items:
        li = xbmcgui.ListItem(it.get('label', ''), it.get('desc', ''), offscreen=True)
        art = it.get('art', '')
        li.setArt({'thumb': art, 'icon': art})
        li.setProperty('current', 'true' if it.get('current') else 'false')
        li.setProperty('fit', it.get('fit', 'fill'))
        out.append(li)
    return out


def pick(title, items, preselect=0):
    start = max(0, min(preselect, len(items) - 1)) if items else 0
    try:
        win = _Grid(XML, paths.ADDON_PATH, 'Default', '1080i',
                    items=_list_items(items), start=start, title=title)
        win.doModal()
        res = win.pick
        del win
        return res
    except Exception as e:
        _log('grid failed, using the list: %s' % e, xbmc.LOGWARNING)
    return xbmcgui.Dialog().select(title, _list_items(items), preselect=start, useDetails=True)
