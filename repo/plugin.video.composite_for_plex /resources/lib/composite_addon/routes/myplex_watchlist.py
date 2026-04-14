# -*- coding: utf-8 -*-
"""
Cloud-backed Plex Watchlist route.
Loads the user's watchlist from Plex Discover, then resolves locally only when an item is opened.
"""

from urllib.parse import quote

import xbmcgui  # pylint: disable=import-error
import xbmcplugin  # pylint: disable=import-error

from ..addon.common import get_handle
from ..addon.containers import GUIItem
from ..addon.items.gui import create_gui_item
from ..addon.logger import Logger
from ..addon.strings import i18n
from ..plex import plex
from ..addon.constants import CONFIG, MODES

LOG = Logger()


def _discover_art(context, plex_network, path):
    if context.settings.skip_images() or not path:
        return ''
    path = str(path)
    if path.startswith('http'):
        return path
    if not path.startswith('/'):
        return ''
    token = plex_network.get_myplex_token().get('token')
    if token:
        separator = '&' if '?' in path else '?'
        return '%s%s%sX-Plex-Token=%s' % (plex_network.discover_server, path, separator, quote(token))
    return '%s%s' % (plex_network.discover_server, path)



def _find_child_image(element, keywords):
    keywords = tuple(str(keyword).lower() for keyword in keywords)
    for child in element.findall('Image'):
        image_type = str(child.get('type', '')).lower()
        if not image_type:
            continue
        if not any(keyword in image_type for keyword in keywords):
            continue
        for attr_name in ('url', 'key', 'path'):
            value = child.get(attr_name, '')
            if value:
                return value
    return ''



def _select_watchlist_art(element):
    poster_candidates = [
        element.get('poster', ''),
        element.get('primaryThumb', ''),
        element.get('grandparentThumb', ''),
        element.get('parentThumb', ''),
        _find_child_image(element, ('poster', 'cover', 'thumb')),
        element.get('thumb', ''),
    ]
    banner_candidates = [
        element.get('banner', ''),
        element.get('landscape', ''),
        _find_child_image(element, ('banner', 'landscape', 'hero', 'coverart')),
        element.get('thumb', ''),
    ]
    art_candidates = [
        element.get('art', ''),
        element.get('fanart', ''),
        _find_child_image(element, ('background', 'fanart', 'art')),
    ]

    def _pick(candidates):
        for candidate in candidates:
            if candidate:
                return candidate
        return ''

    return _pick(poster_candidates), _pick(banner_candidates), _pick(art_candidates)



def _extract_ids(element):
    ids = {'imdb_id': '', 'tmdb_id': '', 'tvdb_id': ''}

    for child in element.findall('Guid'):
        guid_value = child.get('id', '')
        if guid_value.startswith('imdb://'):
            ids['imdb_id'] = guid_value.replace('imdb://', '')
        elif guid_value.startswith('tmdb://'):
            ids['tmdb_id'] = guid_value.replace('tmdb://', '')
        elif guid_value.startswith('tvdb://'):
            ids['tvdb_id'] = guid_value.replace('tvdb://', '')
        elif guid_value.startswith('themoviedb://'):
            ids['tmdb_id'] = guid_value.replace('themoviedb://', '').replace('tv-', '')
        elif guid_value.startswith('thetvdb://'):
            ids['tvdb_id'] = guid_value.replace('thetvdb://', '')

    legacy_guid = element.get('guid', '')
    if not ids['imdb_id'] and 'imdb://' in legacy_guid:
        ids['imdb_id'] = legacy_guid.split('imdb://', 1)[1].split('?', 1)[0]
    if not ids['tmdb_id'] and 'tmdb://' in legacy_guid:
        ids['tmdb_id'] = legacy_guid.split('tmdb://', 1)[1].split('?', 1)[0]
    if not ids['tmdb_id'] and 'themoviedb://' in legacy_guid:
        ids['tmdb_id'] = legacy_guid.split('themoviedb://', 1)[1].split('?', 1)[0].replace('tv-', '')
    if not ids['tvdb_id'] and 'tvdb://' in legacy_guid:
        ids['tvdb_id'] = legacy_guid.split('tvdb://', 1)[1].split('?', 1)[0]
    if not ids['tvdb_id'] and 'thetvdb://' in legacy_guid:
        ids['tvdb_id'] = legacy_guid.split('thetvdb://', 1)[1].split('?', 1)[0]

    return ids


def _fetch_discover_guids(plex_network, rating_key):
    """Fetch GUIDs from Discover metadata endpoint for a single item."""
    import requests as _req
    try:
        headers = plex_network.plex_identification_header()
        url = '%s/library/metadata/%s' % (plex_network.discover_server, rating_key)
        resp = _req.get(url, headers=headers,
                        params={'includeGuids': 1},
                        verify=True, timeout=(3, 10))
        if resp.status_code != 200:
            return {}
        import xml.etree.ElementTree as ET
        tree = ET.fromstring(resp.text.encode('utf-8'))
        item = tree.find('.//Video') or tree.find('.//Directory') or tree
        return _extract_ids(item)
    except Exception:
        return {}


def _resolve_watchlist_guids(plex_network, entries):
    """Pre-fetch GUIDs for watchlist entries that are missing them (parallel)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    to_resolve = []
    for entry in entries:
        ids = _extract_ids(entry)
        if ids.get('imdb_id') or ids.get('tmdb_id') or ids.get('tvdb_id'):
            continue  # already has GUIDs
        rk = entry.get('ratingKey', '')
        if rk:
            to_resolve.append((rk, entry))

    if not to_resolve:
        return

    with ThreadPoolExecutor(max_workers=min(6, len(to_resolve))) as pool:
        futures = {pool.submit(_fetch_discover_guids, plex_network, rk): entry
                   for rk, entry in to_resolve}
        for future in as_completed(futures):
            entry = futures[future]
            try:
                ids = future.result()
                if ids:
                    # Store GUIDs as attributes so _extract_ids picks them up next time
                    for child_id, prefix in [('imdb_id', 'imdb'), ('tmdb_id', 'tmdb'), ('tvdb_id', 'tvdb')]:
                        val = ids.get(child_id, '')
                        if val:
                            import xml.etree.ElementTree as ET
                            guid_el = ET.SubElement(entry, 'Guid')
                            guid_el.set('id', '%s://%s' % (prefix, val))
            except Exception:
                pass



def _preview_limit(context):
    value = context.settings.performance_home_limit()
    return None if value is None else max(1, value)


def _page_size(context):
    page = context.settings.performance_page_size()
    preview = _preview_limit(context)
    if page is None:
        return None
    if preview is None:
        return max(1, page)
    return max(preview, page)


def _read_int(context, name, default):
    try:
        return int(context.params.get(name, default))
    except (TypeError, ValueError):
        return default


def _build_nav_item(context, title, start, page_size, view_all='1'):
    details = {'title': title}
    extra_data = {
        'type': 'Folder',
        'mode': context.params.get('mode', str(MODES.MYPLEXWATCHLIST)),
        'parameters': {'start': start, 'page_size': page_size, 'view_all': view_all}
    }
    return create_gui_item(context, GUIItem('http://watchlist/nav', details, extra_data))


def _iter_watchlist_entries(tree):
    if tree is None:
        return []
    entries = []
    for child in tree:
        media_type = child.get('type', '').lower()
        if media_type in ('movie', 'show'):
            entries.append(child)
    return entries



def _build_watchlist_item(context, plex_network, element):
    media_type = element.get('type', '').lower()
    title = element.get('title', '') or element.get('name', i18n('Unknown'))
    original_title = element.get('originalTitle', '') or element.get('titleSort', '') or title
    summary = element.get('summary', '')
    year = element.get('year', '')
    premiered = element.get('originallyAvailableAt', '')
    title_label = '%s (%s)' % (title, year) if year else title

    ids = _extract_ids(element)
    poster_path, banner_path, fanart_path = _select_watchlist_art(element)
    poster = _discover_art(context, plex_network, poster_path)
    banner = _discover_art(context, plex_network, banner_path)
    fanart = _discover_art(context, plex_network, fanart_path)

    details = {
        'title': title_label,
        'originaltitle': original_title,
        'plot': summary,
        'premiered': premiered,
        'mediatype': 'movie' if media_type == 'movie' else 'tvshow',
        'year': int(year) if str(year).isdigit() else 0,
    }
    extra_data = {
        'type': 'Folder',
        'mode': MODES.SEARCHALL,
        'thumb': poster or CONFIG['icon'],
        'season_thumb': poster or CONFIG['icon'],
        'banner': banner if banner and banner != poster else '',
        'fanart_image': fanart,
        'source': 'movie' if media_type == 'movie' else 'tvshows',
        'parameters': {
            'video_type': 'movie' if media_type == 'movie' else 'show',
            'query': title,
            'title': title,
            'original_title': original_title,
            'year': year,
            'premiered': premiered,
            'imdb_id': ids['imdb_id'],
            'tmdb_id': ids['tmdb_id'],
            'tvdb_id': ids['tvdb_id'],
        }
    }

    gui_item = GUIItem('http://watchlist/%s' % quote(title), details, extra_data)
    return create_gui_item(context, gui_item)



def run(context):
    context.plex_network = plex.Plex(context.settings, load=True)
    view_all = str(context.params.get('view_all', '0')) == '1'
    start = max(0, _read_int(context, 'start', 0))
    default_page_size = _page_size(context) if view_all else _preview_limit(context)
    page_size = _read_int(context, 'page_size', default_page_size or 0)
    if default_page_size is None and page_size <= 0:
        page_size = 0
    elif page_size <= 0:
        page_size = max(1, default_page_size or 1)

    if not context.plex_network.is_myplex_signedin():
        xbmcgui.Dialog().notification(heading=CONFIG['name'],
                                      message=i18n('myPlex not configured'),
                                      icon=CONFIG['icon'])
        xbmcplugin.endOfDirectory(get_handle(), succeeded=False, cacheToDisc=False)
        return

    tree = context.plex_network.get_myplex_watchlist()
    entries = _iter_watchlist_entries(tree)
    if not entries:
        xbmcgui.Dialog().notification(heading=CONFIG['name'],
                                      message=i18n('No results found'),
                                      icon=CONFIG['icon'])
        xbmcplugin.endOfDirectory(get_handle(), succeeded=False, cacheToDisc=False)
        return

    xbmcplugin.setContent(get_handle(), 'videos')

    visible_entries = entries[start:start + page_size] if page_size else entries[start:]
    has_more = (start + page_size) < len(entries) if page_size else False

    # Pre-fetch GUIDs from Discover for items missing them (parallel)
    try:
        _resolve_watchlist_guids(context.plex_network, visible_entries)
    except Exception as error:
        LOG.debug('GUID resolve error (non-fatal): %s' % str(error))

    items = []
    for entry in visible_entries:
        try:
            items.append(_build_watchlist_item(context, context.plex_network, entry))
        except Exception as error:
            LOG.debug('Watchlist item build error: %s' % str(error))

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))

    nav_items = []
    if page_size and not view_all and len(entries) > page_size:
        nav_items.append(_build_nav_item(context, 'View All', 0, _page_size(context), '1'))
    elif has_more:
        nav_items.append(_build_nav_item(context, 'Next ›', start + page_size, page_size, '1'))
    if nav_items:
        xbmcplugin.addDirectoryItems(get_handle(), nav_items, len(nav_items))

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=context.settings.cache_directory())
