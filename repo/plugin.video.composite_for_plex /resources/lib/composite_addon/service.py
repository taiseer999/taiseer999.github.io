# -*- coding: utf-8 -*-
"""

    Copyright (C) 2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import os

import xbmcgui  # pylint: disable=import-error
import xbmcvfs  # pylint: disable=import-error

from .addon.constants import CONFIG
from .addon.logger import Logger
from .addon.monitor import Monitor
from .addon.player import CallbackPlayer
from .addon.settings import AddonSettings
from .companion import companion
from .companion.client import get_client

LOG = Logger('service')

_BUNDLED_PLAYERS = ('composite_for_plex.json',)
_SYNC_INTERVAL_LOOPS = 30  # 5 minutes when sleep_time = 10


def _read_text(path):
    try:
        if not xbmcvfs.exists(path):
            return ''
        fh = xbmcvfs.File(path)
        data = fh.read()
        fh.close()
        if isinstance(data, bytes):
            data = data.decode('utf-8', 'ignore')
        return data or ''
    except Exception as error:  # pylint: disable=broad-except
        LOG.debug('Player sync read error: %s' % str(error))
        return ''



def _write_text(path, content):
    try:
        folder = os.path.dirname(path)
        if folder and not xbmcvfs.exists(folder):
            xbmcvfs.mkdirs(folder)
        fh = xbmcvfs.File(path, 'w')
        fh.write(content)
        fh.close()
        return True
    except Exception as error:  # pylint: disable=broad-except
        LOG.debug('Player sync write error: %s' % str(error))
        return False




def _sync_tmdbhelper_players():
    try:
        addon_path = xbmcvfs.translatePath(CONFIG['addon'].getAddonInfo('path'))
        source_dir = os.path.join(addon_path, 'resources', 'players')
        if not xbmcvfs.exists(source_dir):
            return

        tmdbhelper_addon_path = xbmcvfs.translatePath('special://home/addons/plugin.video.themoviedb.helper')
        if not xbmcvfs.exists(tmdbhelper_addon_path):
            return

        target_dir = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.themoviedb.helper/players')
        if not xbmcvfs.exists(target_dir):
            xbmcvfs.mkdirs(target_dir)

        # Force-install bundled DPlex players every sync run.
        for filename in _BUNDLED_PLAYERS:
            source = os.path.join(source_dir, filename)
            if not xbmcvfs.exists(source):
                continue
            bundled = _read_text(source)
            if not bundled:
                continue
            target = os.path.join(target_dir, filename)
            if _write_text(target, bundled):
                LOG.debug('Force-updated TMDbHelper player: %s' % filename)

    except Exception as error:  # pylint: disable=broad-except
        LOG.debug('TMDbHelper player sync error: %s' % str(error))



def run():
    settings = AddonSettings()

    sleep_time = 10

    LOG.debug('Service initialization...')

    window = xbmcgui.Window(10000)
    player = CallbackPlayer(window=window, settings=settings)
    monitor = Monitor(settings)

    companion_thread = None
    loop_count = 0
    _sync_tmdbhelper_players()

    while not monitor.abortRequested():

        if not companion_thread and settings.use_companion():
            _fresh_settings = AddonSettings()
            companion_thread = companion.CompanionReceiverThread(get_client(_fresh_settings),
                                                                 _fresh_settings)
            del _fresh_settings
        elif companion_thread and not settings.use_companion():
            companion.shutdown(companion_thread)
            companion_thread = None

        loop_count += 1
        if loop_count >= _SYNC_INTERVAL_LOOPS:
            loop_count = 0
            _sync_tmdbhelper_players()

        if monitor.waitForAbort(sleep_time):
            break

    companion.shutdown(companion_thread)
    player.cleanup_threads(only_ended=False)  # clean up any/all playback monitoring threads
