# -*- coding: utf-8 -*-
"""Register Dex Hub as a TMDb Helper player.

This module copies the bundled player JSON (resources/players/dexhub.json)
into the TMDb Helper addon's players folder so it shows up in the
"Play with..." dialog and the autoplay settings.

TMDb Helper looks for player files in:
    special://profile/addon_data/plugin.video.themoviedb.helper/players/

We never touch TMDb Helper's own files — we only drop our JSON alongside.
"""
import os
import shutil
from functools import lru_cache

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from .i18n import tr

TMDBH_ID = 'plugin.video.themoviedb.helper'
PLAYER_FILENAME = 'dexhub.json'


def _addon():
    return xbmcaddon.Addon()


def _addon_path():
    return _addon().getAddonInfo('path')


def _bundled_player_path():
    return os.path.join(_addon_path(), 'resources', 'players', PLAYER_FILENAME)


def _tmdbh_players_dir():
    return xbmcvfs.translatePath(
        'special://profile/addon_data/%s/players/' % TMDBH_ID
    )


@lru_cache(maxsize=1)
def has_tmdbhelper():
    """Check if TMDb Helper is installed. Result cached for the lifetime of
    this Python invocation — install/uninstall is rare and never happens
    inside a single plugin call, so the per-item lookup overhead is wasted."""
    try:
        return bool(xbmc.getCondVisibility('System.HasAddon(%s)' % TMDBH_ID))
    except Exception:
        return False


def player_installed():
    """True if our player JSON is already present in TMDb Helper's folder."""
    target = os.path.join(_tmdbh_players_dir(), PLAYER_FILENAME)
    try:
        return os.path.exists(target)
    except Exception:
        return False


def install(silent=False):
    """Copy resources/players/dexhub.json into TMDb Helper's players folder.

    Returns True if the file is now in place, False otherwise.
    When silent=False, shows user-facing notifications on failure.
    """
    if not has_tmdbhelper():
        if not silent:
            xbmcgui.Dialog().notification(
                'Dex Hub',
                tr('TMDb Helper غير مثبّت'),
                xbmcgui.NOTIFICATION_WARNING,
                3500,
            )
        return False

    src = _bundled_player_path()
    if not os.path.exists(src):
        if not silent:
            xbmcgui.Dialog().notification(
                'Dex Hub',
                tr('ملف المشغّل غير موجود داخل الإضافة'),
                xbmcgui.NOTIFICATION_ERROR,
                3500,
            )
        xbmc.log('[DexHub] tmdbh player source missing: %s' % src, xbmc.LOGERROR)
        return False

    dst_dir = _tmdbh_players_dir()
    try:
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir, exist_ok=True)
    except Exception as exc:
        xbmc.log('[DexHub] tmdbh players dir create failed: %s' % exc, xbmc.LOGERROR)
        if not silent:
            xbmcgui.Dialog().notification(
                'Dex Hub',
                tr('تعذّر إنشاء مجلد مشغّلات TMDb Helper'),
                xbmcgui.NOTIFICATION_ERROR,
                3500,
            )
        return False

    dst = os.path.join(dst_dir, PLAYER_FILENAME)
    try:
        shutil.copyfile(src, dst)
    except Exception as exc:
        xbmc.log('[DexHub] tmdbh player copy failed: %s' % exc, xbmc.LOGERROR)
        if not silent:
            xbmcgui.Dialog().notification(
                'Dex Hub',
                tr('تعذّر نسخ ملف المشغّل'),
                xbmcgui.NOTIFICATION_ERROR,
                3500,
            )
        return False

    xbmc.log('[DexHub] registered as TMDb Helper player at %s' % dst, xbmc.LOGINFO)
    if not silent:
        xbmcgui.Dialog().notification(
            'Dex Hub',
            tr('تم تسجيل Dex Hub كمشغّل TMDb Helper'),
            xbmcgui.NOTIFICATION_INFO,
            3000,
        )
    return True


def uninstall(silent=False):
    """Remove the Dex Hub player JSON from TMDb Helper's folder."""
    dst = os.path.join(_tmdbh_players_dir(), PLAYER_FILENAME)
    try:
        if os.path.exists(dst):
            os.remove(dst)
            if not silent:
                xbmcgui.Dialog().notification(
                    'Dex Hub',
                    tr('تم إزالة Dex Hub من TMDb Helper'),
                    xbmcgui.NOTIFICATION_INFO,
                    2500,
                )
            return True
    except Exception as exc:
        xbmc.log('[DexHub] tmdbh player uninstall failed: %s' % exc, xbmc.LOGWARNING)
    return False


def ensure_installed_once():
    """Ensure the Dex Hub TMDb Helper player exists and is up to date."""
    if not has_tmdbhelper():
        return False
    src = _bundled_player_path()
    dst = os.path.join(_tmdbh_players_dir(), PLAYER_FILENAME)
    try:
        if os.path.exists(src) and os.path.exists(dst):
            try:
                with open(src, 'rb') as fh:
                    src_bytes = fh.read()
                with open(dst, 'rb') as fh:
                    dst_bytes = fh.read()
                if src_bytes == dst_bytes:
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return install(silent=True)
