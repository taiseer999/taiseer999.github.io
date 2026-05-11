# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2020 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from ..constants import MODES
from ..containers import GUIItem
from ..containers import ItemPropertyUnavailable
from ..strings import directory_item_translate
from ..strings import encode_utf8
from ..strings import i18n
from .common import get_fanart_image
from .common import get_link_url
from .common import get_thumb_image
from .gui import create_gui_item


def _safe_item_attr(item, name):
    try:
        return getattr(item, name)
    except ItemPropertyUnavailable:
        return None
    except AttributeError:
        return None


def _safe_get(source, key, default=''):
    if source is None:
        return default
    getter = getattr(source, 'get', None)
    if callable(getter):
        try:
            value = getter(key, default)
        except TypeError:
            value = getter(key)
            if value is None:
                value = default
        return default if value is None else value
    return default


def _placeholder(path):
    path = encode_utf8(path or '')
    return path == '' or '/:/resources/' in path


def _pick_directory_art_source(data_source, tree_source):
    candidates = []
    for source in (data_source, tree_source):
        if source is not None and source not in candidates:
            candidates.append(source)

    fallback = candidates[0] if candidates else None
    for source in candidates:
        thumb = encode_utf8(_safe_get(source, 'thumb', '') or '')
        art = encode_utf8(_safe_get(source, 'art', '') or '')
        if (thumb and not _placeholder(thumb)) or (art and not _placeholder(art)):
            return source
    return fallback


def _pick_directory_title(data_source, tree_source):
    for key in ('title', 'tag', 'label', 'name'):
        for source in (data_source, tree_source):
            value = encode_utf8(_safe_get(source, key, '') or '')
            if value:
                return value
    return i18n('Unknown')


def create_directory_item(context, item):
    is_collection = '/collection' in item.url
    data_source = _safe_item_attr(item, 'data')
    tree_source = _safe_item_attr(item, 'tree')
    image_source = _pick_directory_art_source(data_source, tree_source)

    title = _pick_directory_title(data_source, tree_source)
    translate_thumb = _safe_get(tree_source, 'thumb', '') or _safe_get(image_source, 'thumb', '') or ''
    title = directory_item_translate(title, translate_thumb)

    info_labels = {
        'title': title
    }

    if is_collection:
        info_labels['mediatype'] = 'set'

    thumb = get_thumb_image(context, item.server, image_source, fallback='' if is_collection else None)
    fanart = get_fanart_image(context, item.server, image_source)

    if is_collection:
        if not thumb and fanart:
            thumb = fanart
        if not fanart and thumb:
            fanart = thumb

    extra_data = {
        'thumb': thumb,
        'fanart_image': fanart,
        'mode': MODES.GETCONTENT,
        'type': 'Folder',
        'suppress_default_icon': bool(is_collection and not thumb)
    }

    link_source = data_source if data_source is not None else image_source
    item_url = '%s' % (get_link_url(item.server, item.url, link_source))

    gui_item = GUIItem(item_url, info_labels, extra_data)
    return create_gui_item(context, gui_item)
