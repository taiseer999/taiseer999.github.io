# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from ..addon.data_cache import DATA_CACHE
from ..addon.playback import play_library_media
from ..addon.playback import play_media_id_from_uuid
from ..addon.utils import get_transcode_profile
from ..plex import plex


def run(context, data):
    context.plex_network = plex.Plex(context.settings, load=True)

    # Defensive: not every caller passes every key (e.g. PLAYLIBRARY_TRANSCODE
    # mode passes only url+transcode). Use .get() throughout instead of [].
    transcode = bool(data.get('transcode'))
    transcode_profile = data.get('transcode_profile')

    if transcode and transcode_profile is None:
        transcode_profile = get_transcode_profile(context)
    if transcode_profile is None:
        transcode_profile = 0

    data['transcode'] = transcode
    data['transcode_profile'] = transcode_profile

    url = data.get('url')
    server_uuid = data.get('server_uuid')
    media_id = data.get('media_id')

    # Note: do NOT wipe DATA_CACHE here. The previous behaviour
    # (`DATA_CACHE.delete_cache(True)`) wiped every cached folder XML on
    # every playback start, so pressing Back after watching meant every
    # folder needed a full re-fetch from Plex. The 17.x player monitor
    # already calls `Container.Refresh` after playback ends, which gives
    # Continue Watching / Next Up the freshness they need without nuking
    # unrelated section caches.
    if not url and (server_uuid and media_id):
        play_media_id_from_uuid(context, data)
        return

    if url:
        play_library_media(context, data)
