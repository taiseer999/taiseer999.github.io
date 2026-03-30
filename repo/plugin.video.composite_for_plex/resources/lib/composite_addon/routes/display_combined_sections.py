# -*- coding: utf-8 -*-

"""
Copyright (C) 2020-2026 DPlex (plugin.video.composite_for_plex)

This file is part of Composite (plugin.video.composite_for_plex)

SPDX-License-Identifier: GPL-2.0-or-later
See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import xbmcplugin  # pylint: disable=import-error

from ..addon.common import get_handle
from ..addon.constants import MODES
from ..addon.containers import GUIItem
from ..addon.items.gui import create_gui_item
from ..addon.logger import Logger
from ..addon.strings import i18n
from ..plex import plex

LOG = Logger()

def run(context):
    context.plex_network = plex.Plex(context.settings, load=True)
    xbmcplugin.setContent(get_handle(), 'files')

    items = get_menu_items(context)

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=True)

def get_menu_items(context):
    items = []

    # (عنوان, mode, path, content_type)
    # content_type=None للأقسام التي لا تحتاجه
    menu_structure = [
        (i18n('TV Shows on Deck'),         MODES.TVSHOWS_ON_DECK,        '/library/onDeck',           'show'),
        (i18n('Movies on Deck'),            MODES.MOVIES_ON_DECK,         '/library/onDeck',           'movie'),
        (i18n('Recently Added Episodes'),   MODES.EPISODES_RECENTLY_ADDED, '/library/recentlyAdded',   'show'),
        (i18n('Recently Added Movies'),     MODES.MOVIES_RECENTLY_ADDED,  '/library/recentlyAdded',    'movie'),
        (i18n('All Movies'),               MODES.MOVIES_ALL,             '/library/all_movies',        None),
        (i18n('All Shows'),                MODES.TVSHOWS_ALL,            '/library/all_shows',         None),
        (i18n('All Artists'),              MODES.ARTISTS_ALL,            '/library/all_artists',       None),
        (i18n('All Photos'),               MODES.PHOTOS_ALL,             '/library/all_photos',        None),
        (i18n('Search Movies...'),         MODES.MOVIES_SEARCH_ALL,      '/library/search_all_movies', None),
        (i18n('Search Shows...'),          MODES.TVSHOWS_SEARCH_ALL,     '/library/search_all_shows',  None),
        (i18n('Search Episodes...'),       MODES.EPISODES_SEARCH_ALL,    '/library/search_all_episodes', None),
        (i18n('Search Artists...'),        MODES.ARTISTS_SEARCH_ALL,     '/library/search_all_artists', None),
        (i18n('Search Albums...'),         MODES.ALBUMS_SEARCH_ALL,      '/library/search_all_albums', None),
        (i18n('Search Tracks...'),         MODES.TRACKS_SEARCH_ALL,      '/library/search_all_tracks', None),
    ]

    for title, mode, path, content_type in menu_structure:
        details = {'title': title}
        extra_data = {
            'type': 'Folder',
            'mode': mode,
        }
        
        # إضافة الباراميتر بذكاء إذا كان موجوداً
        if content_type:
            extra_data['parameters'] = {'content_type': content_type}

        gui_item = GUIItem(path, details, extra_data)
        items.append(create_gui_item(context, gui_item))

    return items
