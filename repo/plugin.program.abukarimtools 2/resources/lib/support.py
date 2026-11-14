# -*- coding: utf-8 -*-
"""Support ABUKARIM - shows the Buy Me a Coffee QR (3.2.33).

The QR is a static PNG shipped with the add-on (resources/media/support), so
nothing is generated or downloaded at run time.
"""
import os
import time

import xbmc
import xbmcgui

from resources.lib import paths
from resources.lib.i18n import T

URL = 'https://buymeacoffee.com/taiseer999'
MEDIA = os.path.join(paths.ADDON_PATH, 'resources', 'media', 'support')


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
        'title': T(30611),
        'text': T(30612),
        'url': URL.replace('https://', ''),
        'hint': T(30613),
        'qr': os.path.join(MEDIA, 'bmc_qr.png'),
        'logo': os.path.join(MEDIA, 'bmc_logo.png'),
    }
    for attempt in range(3):
        started = time.time()
        dlg = _Dialog('abk_support.xml', paths.ADDON_PATH, 'Default', '1080i', props=props)
        dlg.doModal()
        del dlg
        if time.time() - started > 1.5:
            break
        xbmc.log('[AbukarimTools Support] dialog closed instantly - reopening', xbmc.LOGINFO)
        xbmc.sleep(1500)
