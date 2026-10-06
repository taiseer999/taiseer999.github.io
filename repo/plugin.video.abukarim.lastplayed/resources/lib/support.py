# -*- coding: utf-8 -*-
"""Buy Me a Coffee QR (1.0.2). Static QR in resources/media/support."""
import os
import time

import xbmc
import xbmcaddon
import xbmcgui

URL = 'https://buymeacoffee.com/taiseer999'


class _Dialog(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._props = kwargs.get('props') or {}

    def onInit(self):
        for k, v in self._props.items():
            self.setProperty(k, v)
        try:
            self.setFocusId(9100)
        except Exception:
            pass

    def onClick(self, control_id):
        self.close()

    def onAction(self, action):
        if action.getId() not in (0, 107):
            self.close()


def show():
    addon = xbmcaddon.Addon('plugin.video.abukarim.lastplayed')
    L = addon.getLocalizedString
    path = addon.getAddonInfo('path')
    media = os.path.join(path, 'resources', 'media', 'support')
    props = {'title': L(30071), 'text': L(30072), 'url': URL.replace('https://', ''),
             'hint': L(30073), 'qr': os.path.join(media, 'bmc_qr.png'),
             'logo': os.path.join(media, 'bmc_logo.png')}
    for _ in range(3):
        started = time.time()
        dlg = _Dialog('abk_support.xml', path, 'Default', '1080i', props=props)
        dlg.doModal()
        del dlg
        if time.time() - started > 1.5:
            break
        xbmc.sleep(1500)
