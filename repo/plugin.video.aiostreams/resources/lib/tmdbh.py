# -*- coding: utf-8 -*-
"""Install AIOStreams player files into TMDbHelper's players folder."""
import os
import shutil

import xbmc
import xbmcvfs

from . import kodi

PLAYERS_DIR = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.themoviedb.helper/players/')
SRC_DIR = os.path.join(kodi.ADDON_PATH, 'resources', 'players')


def install():
    if not xbmc.getCondVisibility('System.HasAddon(plugin.video.themoviedb.helper)'):
        return kodi.ok(kodi.s(30070))
    kodi.ensure_dir(PLAYERS_DIR)
    names = []
    for name in sorted(os.listdir(SRC_DIR)):
        if name.endswith('.json'):
            shutil.copyfile(os.path.join(SRC_DIR, name), os.path.join(PLAYERS_DIR, name))
            names.append(name)
    kodi.ok(kodi.s(30071) % ', '.join(names))
