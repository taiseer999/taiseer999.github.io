# -*- coding: utf-8 -*-

"""
Copyright (C) 2020-2026 DPlex (plugin.video.composite_for_plex)
"""

import xbmcplugin  # pylint: disable=import-error
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..addon.common import get_handle
from ..addon.constants import MODES
from ..addon.containers import Item
from ..addon.items.artist import create_artist_item
from ..addon.items.movie import create_movie_item
from ..addon.items.photo import create_photo_item
from ..addon.items.show import create_show_item
from ..addon.logger import Logger
from ..plex import plex

LOG = Logger()

def run(context):
    context.plex_network = plex.Plex(context.settings, load=True)
    section_type = get_section_type(context)
    all_sections = context.plex_network.all_sections()

    content_type = None
    items = []

    LOG.debug('Using list of %s sections' % len(all_sections))

    for section in all_sections:
        if section.get_type() == section_type:
            if content_type is None:
                content_type = get_content_type(section)

    def _fetch_section(sec):
        try:
            srv = context.plex_network.get_server_from_uuid(sec.get_server_uuid())
            return _list_content(context, srv, sec.get_path())
        except Exception:
            return []

    matching = [sec for sec in all_sections if sec.get_type() == section_type]
    if matching:
        with ThreadPoolExecutor(max_workers=min(6, len(matching))) as pool:
            for r in as_completed([pool.submit(_fetch_section, sec) for sec in matching]):
                try: items += r.result()
                except Exception: pass

    if items:
        add_sort_methods(content_type)
        xbmcplugin.setContent(get_handle(), content_type)
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=False)

def add_sort_methods(content_type):
    if content_type == 'movies':
        methods = [
            xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE,
            xbmcplugin.SORT_METHOD_DATEADDED,
            xbmcplugin.SORT_METHOD_VIDEO_YEAR,
            xbmcplugin.SORT_METHOD_DATE,
            xbmcplugin.SORT_METHOD_VIDEO_RATING,
            xbmcplugin.SORT_METHOD_VIDEO_RUNTIME,
            xbmcplugin.SORT_METHOD_MPAA_RATING,
            xbmcplugin.SORT_METHOD_UNSORTED
        ]
    elif content_type == 'tvshows':
        methods = [
            xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE,
            xbmcplugin.SORT_METHOD_VIDEO_YEAR,
            xbmcplugin.SORT_METHOD_DATE,
            xbmcplugin.SORT_METHOD_VIDEO_RATING,
            xbmcplugin.SORT_METHOD_MPAA_RATING,
            xbmcplugin.SORT_METHOD_UNSORTED
        ]
    elif content_type == 'artists':
        methods = [
            xbmcplugin.SORT_METHOD_ARTIST_IGNORE_THE,
            xbmcplugin.SORT_METHOD_LASTPLAYED,
            xbmcplugin.SORT_METHOD_VIDEO_YEAR,
            xbmcplugin.SORT_METHOD_UNSORTED
        ]
    else:
        methods = [
            xbmcplugin.SORT_METHOD_UNSORTED,
            xbmcplugin.SORT_METHOD_DATE,
            xbmcplugin.SORT_METHOD_VIDEO_YEAR
        ]
    
    for m in methods:
        xbmcplugin.addSortMethod(get_handle(), m)

def get_section_type(context):
    mode = int(context.params.get('mode', -1))
    if mode == MODES.MOVIES_ALL: return 'movie'
    if mode == MODES.TVSHOWS_ALL: return 'show'
    if mode == MODES.ARTISTS_ALL: return 'artist'
    if mode == MODES.PHOTOS_ALL: return 'photo'
    return ''

def get_content_type(section):
    stype = section.get_type()
    if stype == 'show': return 'tvshows'
    if stype == 'movie': return 'movies'
    if stype == 'artist': return 'artists'
    if stype == 'photo': return 'images'
    return 'files'

def _get_iter_type(section_type):
    if section_type == 'movie': return 'Video'
    return 'Directory'

def _list_content(context, server, section_path):
    LOG.debug('Fetching section path: %s' % section_path)
    
    path = section_path.rstrip('/')
    if not path.endswith('/all'):
        path = '%s/all' % path

    tree = server.processed_xml(path)

    if tree is None:
        return []

    section_type = get_section_type(context)
    iter_type = _get_iter_type(section_type)
    branches = list(tree.iter(iter_type))

    items = []
    for content in branches:
        item = Item(server, server.get_url_location(), tree, content)
        ctype = content.get('type')
        if ctype == 'movie':
            items.append(create_movie_item(context, item))
        elif ctype == 'show':
            items.append(create_show_item(context, item))
        elif ctype == 'artist':
            items.append(create_artist_item(context, item))
        elif ctype == 'photo':
            items.append(create_photo_item(context, item))

    return items
