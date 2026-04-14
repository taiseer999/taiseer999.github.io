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
from ..strings import directory_item_translate
from ..strings import encode_utf8
from ..strings import i18n
from .common import get_collection_thumb
from .common import get_fanart_image
from .common import get_link_url
from .common import get_thumb_image
from .gui import create_gui_item


def create_directory_item(context, item):
    title = encode_utf8(item.data.get('title', i18n('Unknown')))
    title = directory_item_translate(title, item.tree.get('thumb'))

    info_labels = {
        'title': title
    }

    is_collection = '/collection' in item.url
    if is_collection:
        info_labels['mediatype'] = 'set'

    if is_collection:
        thumb = get_collection_thumb(context, item.server, item.data)
    else:
        thumb = get_thumb_image(context, item.server, item.data)

    fanart = get_fanart_image(context, item.server, item.data)
    if not fanart:
        fanart = get_fanart_image(context, item.server, item.tree)

    extra_data = {
        'thumb': thumb,
        'fanart_image': fanart,
        'mode': MODES.GETCONTENT,
        'type': 'Folder'
    }

    item_url = '%s' % (get_link_url(item.server, item.url, item.data))

    gui_item = GUIItem(item_url, info_labels, extra_data)
    return create_gui_item(context, gui_item)
