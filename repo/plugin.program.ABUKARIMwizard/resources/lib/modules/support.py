# -*- coding: utf-8 -*-
"""Support ABUKARIM - Buy Me a Coffee QR (3.9.29). Static QR in resources/media/support."""
import os
import time

import xbmc
import xbmcgui

from .addonvar import addon_path, local_string

URL = 'https://buymeacoffee.com/taiseer999'
MEDIA = os.path.join(addon_path, 'resources', 'media', 'support')


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
    props = {
        'title': local_string(30991),
        'text': local_string(30992),
        'url': URL.replace('https://', ''),
        'hint': local_string(30993),
        'qr': os.path.join(MEDIA, 'bmc_qr.png'),
        'logo': os.path.join(MEDIA, 'bmc_logo.png'),
    }
    for attempt in range(3):
        started = time.time()
        dlg = _Dialog('abk_support.xml', addon_path, 'Default', '1080i', props=props)
        dlg.doModal()
        del dlg
        if time.time() - started > 1.5:
            break
        xbmc.log('[ABUKARIM Wizard Support] dialog closed instantly - reopening', xbmc.LOGINFO)
        xbmc.sleep(1500)
