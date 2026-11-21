# -*- coding: utf-8 -*-
"""Quick picture guide: full-screen slides, arrows to move, back to close."""
import os

import xbmcgui

from .common import ADDON

ACT_LEFT, ACT_RIGHT, ACT_UP, ACT_DOWN = 1, 2, 3, 4
ACT_SELECT, ACT_PAGE_UP, ACT_PAGE_DOWN, ACT_MOUSE = 7, 5, 6, 100
ACT_BACK = (9, 10, 13, 92, 110)


class Guide(xbmcgui.WindowDialog):
    def __init__(self, pics):
        super().__init__()
        self.pics = pics
        self.k = 0
        self.img = xbmcgui.ControlImage(0, 0, 1280, 720, pics[0], aspectRatio=0)
        self.addControl(self.img)

    def show_k(self):
        self.img.setImage(self.pics[self.k], False)

    def onAction(self, action):
        a = action.getId()
        if a in ACT_BACK:
            self.close()
        elif a in (ACT_LEFT, ACT_DOWN, ACT_SELECT, ACT_PAGE_DOWN, ACT_MOUSE):
            if self.k == len(self.pics) - 1:
                if a in (ACT_SELECT, ACT_MOUSE):
                    self.close()
                return
            self.k += 1
            self.show_k()
        elif a in (ACT_RIGHT, ACT_UP, ACT_PAGE_UP):
            if self.k > 0:
                self.k -= 1
                self.show_k()


def show():
    folder = os.path.join(ADDON.getAddonInfo('path'), 'resources', 'media', 'guide')
    pics = [os.path.join(folder, '%d.jpg' % i) for i in range(1, 50)
            if os.path.exists(os.path.join(folder, '%d.jpg' % i))]
    if not pics:
        return
    w = Guide(pics)
    w.doModal()
    del w
