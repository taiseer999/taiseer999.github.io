# -*- coding: utf-8 -*-

"""Combined recently added with global time sort and lightweight preview paging."""

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import xbmcplugin  # pylint: disable=import-error

from ..addon.common import get_handle
from ..addon.containers import GUIItem, Item
from ..addon.items.episode import create_episode_item
from ..addon.items.gui import create_gui_item
from ..addon.items.movie import create_movie_item
from ..addon.logger import Logger
from ..plex import plex

LOG = Logger()


def _dt(value):
    if not value:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        pass
    for fmt in ('%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S'):
        try:
            return int(datetime.strptime(str(value), fmt).timestamp())
        except ValueError:
            continue
    return 0


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


def _build_nav_item(context, title, mode, content_type, start, page_size, view_all='1'):
    details = {'title': title}
    extra_data = {
        'type': 'Folder',
        'mode': mode,
        'parameters': {
            'content_type': content_type,
            'start': start,
            'page_size': page_size,
            'view_all': view_all,
        }
    }
    return create_gui_item(context, GUIItem('http://combined/recentlyAdded', details, extra_data))


def run(context):
    context.plex_network = plex.Plex(context.settings, load=True)
    content_type = context.params.get('content_type')
    server_list = context.plex_network.get_server_list()
    view_all = str(context.params.get('view_all', '0')) == '1'
    start = max(0, _read_int(context, 'start', 0))
    default_page_size = _page_size(context) if view_all else _preview_limit(context)
    page_size = _read_int(context, 'page_size', default_page_size or 0)
    if default_page_size is None and page_size <= 0:
        page_size = 0
    elif page_size <= 0:
        page_size = max(1, default_page_size or 1)

    preview_limit = _preview_limit(context)
    fetch_candidates = [context.settings.recently_added_item_count()]
    if page_size > 0:
        fetch_candidates.append(start + page_size + 1)
    if preview_limit is not None:
        fetch_candidates.append(preview_limit + 1)
    fetch_size = max(fetch_candidates)
    hide_watched = not context.settings.recently_added_include_watched()

    raw_items = []

    def _fetch(srv, sec):
        try:
            t = srv.get_recently_added(section=int(sec.get_key()), size=fetch_size, hide_watched=hide_watched)
            return srv, t, sec.get_title() if hasattr(sec, 'get_title') else ''
        except Exception:
            return srv, None, ''

    tasks = [(s, sec) for s in server_list for sec in s.get_sections() if sec.content_type() == content_type]
    results = []
    if tasks:
        with ThreadPoolExecutor(max_workers=min(8, len(tasks))) as pool:
            for r in as_completed([pool.submit(_fetch, s, sec) for s, sec in tasks]):
                try: results.append(r.result())
                except Exception: pass

    for server, tree, library_title in results:
        if tree is None:
            continue
        for content in tree.iter('Video'):
            item_type = (content.get('type') or '').lower()
            if item_type not in ('episode', 'movie'):
                continue
            raw_items.append((
                max(_dt(content.get('addedAt')), _dt(content.get('originallyAvailableAt')), _dt(content.get('year'))),
                server, tree, content, library_title
            ))

    if not raw_items:
        xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=False)
        return

    raw_items.sort(key=lambda entry: entry[0], reverse=True)
    visible_items = raw_items[start:start + page_size]
    has_more = start + page_size < len(raw_items)

    items = []
    for _, server, tree, content, library_title in visible_items:
        if library_title:
            content.set('library_title_tag', library_title)
        if hasattr(server, 'get_name'):
            content.set('server_name_tag', server.get_name() or '')
        item = Item(server, server.get_url_location(), tree, content)
        if content.get('type') == 'episode':
            items.append(create_episode_item(context, item))
        elif content.get('type') == 'movie':
            items.append(create_movie_item(context, item))

    if items:
        xbmcplugin.setContent(get_handle(), content_type)
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))

    mode = context.params.get('mode')
    try:
        mode = int(mode)
    except (TypeError, ValueError):
        mode = 0

    nav_items = []
    if not view_all and len(raw_items) > page_size:
        nav_items.append(_build_nav_item(context, 'View All', mode, content_type, 0, _page_size(context), '1'))
    elif has_more:
        nav_items.append(_build_nav_item(context, 'Next ›', mode, content_type, start + page_size, page_size, '1'))

    if nav_items:
        xbmcplugin.addDirectoryItems(get_handle(), nav_items, len(nav_items))

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=False)
