# -*- coding: utf-8 -*-

"""
Copyright (C) 2019-2026 DPlex (plugin.video.composite_for_plex)
"""

import xbmcplugin  # pylint: disable=import-error

from ..addon.common import get_handle
from ..addon.containers import Item
from ..addon.items.episode import create_episode_item
from ..addon.items.movie import create_movie_item
from ..addon.logger import Logger
from ..plex import plex

LOG = Logger()

def _resolution_rank(content):
    """4K=0, 1080p=1, 720p=2, SD=3"""
    media = content.find('.//Media')
    if media is None:
        return 99
    res = media.get('videoResolution', '').lower()
    try:
        r = int(res)
        if r > 1088: return 0
        if r >= 1080: return 1
        if r >= 720:  return 2
        return 3
    except ValueError:
        if res == '4k': return 0
        return 99

def _group_key(content):
    """مفتاح تجميع نفس الحلقة/الفيلم"""
    title = (
        content.get('grandparentTitle') or
        content.get('title') or
        ''
    ).lower()
    season  = int(content.get('parentIndex', 0))
    episode = int(content.get('index', 0))
    return (title, season, episode)

def _global_sort_by_quality(raw_items):
    """
    ترتيب شامل: يجمع كل السيرفرات مع بعض،
    يحافظ على الترتيب الزمني، ويرفع الـ 4K فوق!
    """
    indexed = list(enumerate(raw_items))

    first_seen = {}
    for idx, (server, tree, content) in indexed:
        key = _group_key(content)
        if key not in first_seen:
            first_seen[key] = idx

    result = sorted(
        indexed,
        key=lambda x: (first_seen[_group_key(x[1][2])], _resolution_rank(x[1][2]))
    )
    return [item for _, item in result]

def run(context):
    context.plex_network = plex.Plex(context.settings, load=True)
    content_type = context.params.get('content_type')
    LOG.debug('content_type received: %s' % content_type)
    server_list = context.plex_network.get_server_list()

    raw_items = []
    LOG.debug('Using list of %s servers' % len(server_list))
    
    # 1. جمع كل المواد من كل السيرفرات في سلة واحدة أولاً
    for server in server_list:
        sections = server.get_sections()
        for section in sections:
            if section.content_type() == content_type:
                tree = server.get_ondeck(section=int(section.get_key()))
                if tree is not None:
                    branches = list(tree.iter('Video'))
                    for content in branches:
                        raw_items.append((server, tree, content))

    if not raw_items:
        xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=False)
        return

    # 2. تطبيق الترتيب الشامل على السلة كاملة
    sorted_raw_items = _global_sort_by_quality(raw_items)

    # 3. بناء واجهة كودي وعرض العناصر المرتبة
    items = []
    for server, tree, content in sorted_raw_items:
        # 🟢 السر هنا: زرع اسم السيرفر عشان تقرأه ملفات episode_item و movie_item
        server_name = server.get_name() if hasattr(server, 'get_name') else ''
        if server_name:
            content.set('server_name_tag', server_name)

        item = Item(server, server.get_url_location(), tree, content)
        if content.get('type') == 'episode':
            items.append(create_episode_item(context, item))
        elif content.get('type') == 'movie':
            items.append(create_movie_item(context, item))

    if items:
        xbmcplugin.setContent(get_handle(), content_type)
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=False)
