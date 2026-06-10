# -*- coding: utf-8 -*-
"""
QR Code utilities for Seren
يكتب الصورة عبر xbmcvfs ويرجع special:// path
"""
import os
import sys
import xbmc
import xbmcaddon
import xbmcvfs


def _inject_qr_paths():
    try:
        our_path    = xbmcaddon.Addon('plugin.video.seren').getAddonInfo('path')
        addons_root = os.path.dirname(our_path)
        for module in ('script.module.qrcode', 'script.module.pil'):
            lib_path = os.path.join(addons_root, module, 'lib')
            if os.path.isdir(lib_path) and lib_path not in sys.path:
                sys.path.insert(0, lib_path)
    except Exception:
        pass


def _get_qr_special_path():
    """مسار ثابت في addon_data يضمن وصول Kodi إليه"""
    return 'special://profile/addon_data/plugin.video.seren/seren_qr.png'


def _make_qr_local(url, os_path):
    import qrcode
    img = qrcode.make(url)
    img.save(os_path)
    return True


def _make_qr_remote(url, os_path):
    from urllib.request import urlopen
    from urllib.parse   import quote
    api_url = 'https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=' + quote(url, safe='')
    with urlopen(api_url, timeout=10) as resp:
        data = resp.read()
    if len(data) < 100:
        raise ValueError('Empty QR response')
    with open(os_path, 'wb') as f:
        f.write(data)
    return True


def make_qr(url):
    """
    يولّد QR PNG في addon_data ويرجع special:// path
    addon_data مضمون أن Kodi يحمّل منه الصور مباشرة
    """
    _inject_qr_paths()

    special_path = _get_qr_special_path()
    os_path      = xbmcvfs.translatePath(special_path)

    # نتأكد من وجود المجلد
    os.makedirs(os.path.dirname(os_path), exist_ok=True)

    # محاولة 1: محلي
    try:
        _make_qr_local(url, os_path)
        xbmc.log(f'Seren QR local OK: {special_path}', xbmc.LOGINFO)
        return special_path
    except Exception as e:
        xbmc.log(f'Seren QR local failed: {e} — trying remote', xbmc.LOGINFO)

    # محاولة 2: API
    try:
        _make_qr_remote(url, os_path)
        xbmc.log(f'Seren QR remote OK: {special_path}', xbmc.LOGINFO)
        return special_path
    except Exception as e:
        xbmc.log(f'Seren QR remote failed: {e}', xbmc.LOGWARNING)

    return ''


def remove_qr(path):
    try:
        if path:
            os_path = xbmcvfs.translatePath(path) if path.startswith('special://') else path
            if os.path.exists(os_path):
                os.remove(os_path)
    except Exception:
        pass
