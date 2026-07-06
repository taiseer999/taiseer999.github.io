# -*- coding: utf-8 -*-
import sys
import os
import xbmcaddon
from acctmgr.modules import log_utils

def _ensure_qrcode_path():
    """Inject script.module.qrcode and script.module.pil lib paths into sys.path."""
    try:
        # Derive the addons root from our own addon path
        # e.g. .../addons/script.module.acctmgr -> .../addons
        our_path = xbmcaddon.Addon('script.module.acctmgr').getAddonInfo('path')
        addons_root = os.path.dirname(our_path)
        for module in ('script.module.qrcode', 'script.module.pil'):
            lib_path = os.path.join(addons_root, module, 'lib')
            if os.path.isdir(lib_path) and lib_path not in sys.path:
                sys.path.insert(0, lib_path)
    except Exception as e:
        log_utils.error(f"qr_utils path inject failed: {e}")

def _make_qr_local(url):
    """Generate a QR PNG locally via script.module.qrcode, or '' on failure."""
    _ensure_qrcode_path()
    try:
        import qrcode
        import tempfile
        qr = qrcode.make(url)
        tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        qr.save(tmp.name)
        tmp.close()
        return tmp.name
    except Exception as e:
        log_utils.error(f"QR local generation failed: {e}")
        return ''

def _make_qr_remote(url):
    """Fetch a QR PNG from api.qrserver.com, or '' on failure."""
    try:
        import tempfile
        from urllib.request import urlopen
        from urllib.parse import quote
        api = 'https://api.qrserver.com/v1/create-qr-code/?size=348x348&data=' + quote(url, safe='')
        data = urlopen(api, timeout=10).read()
        if not data or data[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError('bad response')
        tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        tmp.write(data)
        tmp.close()
        return tmp.name
    except Exception as e:
        log_utils.error(f"QR remote generation failed: {e}")
        return ''

def make_qr(url):
    """Generate a QR PNG for url (local lib first, remote API fallback).

    Returns a temp file path, or '' if both methods fail; callers should fall
    back to a bundled static QR image in that case."""
    return _make_qr_local(url) or _make_qr_remote(url)

def remove_qr(path):
    """Clean up temp QR file."""
    if path:
        try:
            os.remove(path)
        except Exception:
            pass
