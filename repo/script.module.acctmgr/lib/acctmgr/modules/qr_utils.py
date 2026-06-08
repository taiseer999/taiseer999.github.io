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

def make_qr(url):
    """Generate a QR PNG for url, return temp file path or empty string on failure."""
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
        log_utils.error(f"QR generation failed: {e}")
        return ''

def remove_qr(path):
    """Clean up temp QR file."""
    if path:
        try:
            os.remove(path)
        except Exception:
            pass
