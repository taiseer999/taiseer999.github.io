# -*- coding: utf-8 -*-
"""
qr_view.py - full-screen "scan this" dialog: a QR code plus a block of text.

Used by the log sharer and the remote-access screen. The QR image is made
with the segno library already vendored for OpenWizard, so there is no new
dependency; the backdrop is a 1x1 PNG written on the fly.
"""

import hashlib
import os
import struct
import sys
import zlib

import xbmc
import xbmcgui
import xbmcvfs

ADDON_PATH = xbmcvfs.translatePath('special://home/addons/plugin.program.abukarimtools/')
TEMP = xbmcvfs.translatePath('special://temp/')


def _png_1x1(path, rgba):
    raw = b'\x00' + bytes(rgba)
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    data = (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw))
            + chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(data)
    return path


def make_qr(data):
    # segno (BSD) is vendored on its own since 3.1.x dropped the OpenWizard copy.
    seg_dir = os.path.join(ADDON_PATH, 'resources', 'lib', 'vendor')
    if seg_dir not in sys.path:
        sys.path.insert(0, seg_dir)
    import segno
    name = 'abk_qr_%s.png' % hashlib.md5(data.encode('utf-8')).hexdigest()[:12]
    path = os.path.join(TEMP, name)
    if not os.path.isfile(path):
        # The vendored segno is old: default black-on-white, no colour kwargs.
        segno.make(data, error='m').save(path, scale=10, border=2)
    return path


class _QRDialog(xbmcgui.WindowDialog):
    def __init__(self, title, text, qr_path):
        super().__init__()
        bg = os.path.join(TEMP, 'abk_bg_dark.png')
        if not os.path.isfile(bg):
            _png_1x1(bg, (12, 14, 20, 235))
        # WindowDialog uses a 1280x720 coordinate space.
        self.addControl(xbmcgui.ControlImage(0, 0, 1280, 720, bg))
        self.addControl(xbmcgui.ControlLabel(80, 50, 1120, 50, '[B]%s[/B]' % title,
                                             font='font13', textColor='FFFFFFFF'))
        self.addControl(xbmcgui.ControlImage(80, 130, 440, 440, qr_path))
        tb = xbmcgui.ControlTextBox(580, 140, 640, 440, font='font13', textColor='FFDDDDDD')
        self.addControl(tb)
        tb.setText(text)
        self.addControl(xbmcgui.ControlLabel(80, 620, 1120, 40,
                                             'OK / BACK',
                                             font='font13', textColor='FF888888'))

    def onAction(self, action):
        if action.getId() in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU,
                              xbmcgui.ACTION_SELECT_ITEM, 92, 10, 7):
            self.close()


def show(title, text, data):
    try:
        qr = make_qr(data)
    except Exception as e:
        xbmc.log('[AbukarimTools QR] segno failed: %s' % e, xbmc.LOGWARNING)
        xbmcgui.Dialog().ok(title, text)
        return
    dlg = _QRDialog(title, text, qr)
    dlg.doModal()
    del dlg
