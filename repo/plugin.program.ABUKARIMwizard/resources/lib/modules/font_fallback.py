# -*- coding: utf-8 -*-
"""
font_fallback.py - make Arabic readable in the ABUKARIMwizard menu (and every
other skin surface) by installing an Arabic-capable global fallback font.

Why the wizard needs its own copy
---------------------------------
The wizard's Main Menu is an ordinary Kodi plugin directory listing; its font
is chosen by the ACTIVE SKIN, not the wizard, so when the skin's font (or
Kodi's default fallback arial.ttf) lacks Arabic glyphs every label renders as
tofu (empty boxes) on a fresh install. An add-on cannot set a font on a
directory listing - the only lever is Kodi's GLOBAL FALLBACK font at
special://home/media/fonts/arial.ttf, which every skin drops to for any glyph
its own font is missing.

plugin.program.abukarimtools already installs that fallback, but the wizard
must not DEPEND on the tools add-on having booted first (order isn't
guaranteed, and the wizard's own startup/notify popups appear early). So the
wizard installs the fallback itself. It prefers the font shipped by the tools
add-on when present (single source of truth for the paired ecosystem) and
falls back to the copy shipped inside the wizard, so it works even if the
tools add-on isn't installed.

Kodi loads media/fonts/arial.ttf once at start, so a freshly written file takes
effect on the NEXT Kodi start. We size-compare first and only write when it
differs. Fully fenced: never raises into the caller (startup must continue).
"""

import os
import shutil

import xbmc
import xbmcvfs

# Prefer the tools add-on's shipped font (paired ecosystem, one source of
# truth); fall back to the copy shipped inside the wizard itself so this is
# self-sufficient when the tools add-on is absent.
_SRC_CANDIDATES = (
    'special://home/addons/plugin.program.abukarimtools/resources/fonts/Noto-Regular.ttf',
    'special://home/addons/plugin.program.ABUKARIMwizard/resources/fonts/Noto-Regular.ttf',
)

_DEST_VFS = 'special://home/media/fonts/arial.ttf'


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[ABUKARIMwizard FallbackFont] %s' % msg, level)


def _size(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return -1


def _first_existing_src():
    for vfs in _SRC_CANDIDATES:
        p = xbmcvfs.translatePath(vfs)
        if os.path.exists(p):
            return p
    return None


def install(force=False):
    """Copy an Arabic-capable font over Kodi's global fallback arial.ttf.

    Returns True if the fallback file was (re)written, False otherwise.
    Never raises.
    """
    try:
        src = _first_existing_src()
        if not src:
            _log('No Arabic source font found - cannot install fallback.',
                 xbmc.LOGWARNING)
            return False

        dest_dir = xbmcvfs.translatePath('special://home/media/fonts/')
        dest     = xbmcvfs.translatePath(_DEST_VFS)

        try:
            os.makedirs(dest_dir, exist_ok=True)
        except OSError as e:
            _log('Could not create %s: %s' % (dest_dir, e), xbmc.LOGWARNING)
            return False

        # Only write when the destination differs, so we don't churn the file
        # on every boot. Both shipped sources are identical fixed files, so an
        # identical size means the fallback is already Arabic-capable.
        if not force and _size(dest) == _size(src):
            _log('Fallback arial.ttf already Arabic-capable - no change.')
            return False

        shutil.copyfile(src, dest)
        _log('Installed Arabic-capable fallback font from %s -> %s (takes '
             'effect on next Kodi start).' % (src, dest))
        return True
    except Exception as e:  # never propagate into startup
        _log('Fallback font install failed (ignored): %s' % e, xbmc.LOGERROR)
        return False
