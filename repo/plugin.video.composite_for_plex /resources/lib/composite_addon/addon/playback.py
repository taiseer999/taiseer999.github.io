# -*- coding: utf-8 -*-

"""
Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
Copyright (C) 2018-2026 DPlex (plugin.video.composite_for_plex)

This file is part of Composite (plugin.video.composite_for_plex)

SPDX-License-Identifier: GPL-2.0-or-later
See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from urllib.parse import unquote

import xbmc  # pylint: disable=import-error
import xbmcgui  # pylint: disable=import-error
import xbmcplugin  # pylint: disable=import-error
import xbmcvfs  # pylint: disable=import-error
from infotagger.listitem import ListItemInfoTag  # pylint: disable=import-error

from .common import get_handle
from .common import is_resuming_video
from .constants import CONFIG
from .constants import StreamControl
from .containers import Item
from .items.common import get_banner_image
from .items.common import get_fanart_image
from .items.common import get_guid_ids
from .items.common import get_thumb_image
from .items.track import create_track_item
from .logger import Logger
from .strings import encode_utf8
from .strings import i18n
from .utils import get_file_type
from .utils import get_xml
from .utils import write_pickled

LOG = Logger()

_clearlogo_cache = {}
_TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/original'

def _get_tmdbhelper_db_path():
    """Return the TMDbHelper database path using Kodi's special:// protocol."""
    return xbmcvfs.translatePath(
        'special://userdata/addon_data/plugin.video.themoviedb.helper/database_07/ItemDetails.db'
    )

def _get_clearlogo_cached(tmdb_id, media_type='movie'):
    """Read clearlogo from TMDbHelper database."""
    if not tmdb_id:
        return ''
    cache_key = '%s*%s' % (tmdb_id, media_type)
    if cache_key in _clearlogo_cache:
        return _clearlogo_cache[cache_key]
    try:
        import sqlite3 as _sq
        parent_id = '%s.%s' % (media_type, tmdb_id)
        conn = _sq.connect(_get_tmdbhelper_db_path())
        cur = conn.cursor()
        cur.execute(
            "SELECT icon FROM art WHERE type='logos' AND parent_id=? "
            "ORDER BY CASE WHEN iso_language='en' THEN 0 ELSE 1 END, rating DESC LIMIT 1",
            (parent_id,)
        )
        row = cur.fetchone()
        conn.close()
        icon = row[0] if row and row[0] else ''
        
        if icon:
            # Clean markdown artifacts like [url](url)/image.png
            if '](' in icon:
                icon = icon.split('](')[-1].replace(')', '')
            
            if icon.startswith('http'):
                logo = icon
            else:
                logo = _TMDB_IMAGE_BASE + icon
        else:
            logo = ''
            
        _clearlogo_cache[cache_key] = logo
        return logo
    except:  # pylint: disable=bare-except
        _clearlogo_cache[cache_key] = ''
        return ''

def _get_premium_info(media):
    parts = []

    res = media.get('videoResolution', '')
    if res:
        try:
            r = int(res)
            res_label = '4K' if r > 1088 else ('1080p' if r >= 1080 else ('720p' if r >= 720 else 'SD'))
        except ValueError:
            res_label = res.upper()
        parts.append('[ %s ]' % res_label)

    part_el = media.find('Part')
    hdr_type = ''
    audio_extra = ''

    if part_el is not None:
        for stream in part_el.findall('.//Stream'):
            stype = stream.get('streamType')
            if stype == '1' and not hdr_type:
                dt = stream.get('displayTitle', '').upper()
                cid = stream.get('codecID', '').upper()
                if stream.get('DOVIBLPresent') == '1' or 'DOVI' in cid or 'DV' in dt:
                    hdr_type = 'DV/HDR' if 'HDR' in dt else 'DV'
                elif 'HDR10+' in dt:
                    hdr_type = 'HDR10+'
                elif 'HDR' in dt or stream.get('colorTransfer') in ('smpte2084', 'arib-std-b67'):
                    hdr_type = 'HDR'
            elif stype == '2' and not audio_extra:
                dt = stream.get('displayTitle', '').upper()
                if 'ATMOS' in dt:
                    audio_extra = 'Atmos'
                elif 'DTS:X' in dt or 'DTSX' in dt:
                    audio_extra = 'DTS:X'
            if hdr_type and audio_extra:
                break

    if hdr_type:
        parts.append('[ %s ]' % hdr_type)

    v_codec = media.get('videoCodec', '').lower()
    if v_codec:
        cmap = {'hevc': 'HEVC', 'h264': 'H.264', 'h265': 'H.265', 'av1': 'AV1'}
        parts.append('[ %s ]' % cmap.get(v_codec, v_codec.upper()))

    a_codec = media.get('audioCodec', '').lower()
    a_ch = media.get('audioChannels', '')
    if a_codec:
        amap = {'truehd': 'TrueHD', 'dca': 'DTS', 'dts': 'DTS', 'dtshd': 'DTS-HD',
                'eac3': 'EAC3', 'ac3': 'AC3'}
        a_label = amap.get(a_codec, a_codec.upper())
        if audio_extra:
            a_label += ' ' + audio_extra
        if a_ch:
            ch_map = {'1': '1.0', '2': '2.0', '6': '5.1', '8': '7.1'}
            a_label += ' ' + ch_map.get(str(a_ch), '%sch' % a_ch)
        parts.append('[ %s ]' % a_label)

    if part_el is not None:
        sz = part_el.get('size', '')
        if sz:
            try:
                gb = int(sz) / (1024 ** 3)
                size_str = ('[ %.1f GB ]' % gb) if gb >= 1 else ('[ %.0f MB ]' % (int(sz) / (1024 ** 2)))
                parts.append(size_str)
            except ValueError:
                pass

    return ' • '.join(parts)


def monitor_channel_transcode_playback(context, server, session_id):
    if context.settings.playback_monitor_disabled():
        return

    count = 0
    monitor = xbmc.Monitor()
    player = xbmc.Player()

    while not player.isPlaying() and not monitor.abortRequested():
        count += 1
        if count >= 10:
            return
        if monitor.waitForAbort(2.0):
            return

    while player.isPlaying() and not monitor.abortRequested():
        if monitor.waitForAbort(0.5):
            break

    server.stop_transcode_session(session_id)


def play_media_id_from_uuid(context, data):
    server = context.plex_network.get_server_from_uuid(data['server_uuid'])
    data['url'] = server.get_formatted_url('/library/metadata/%s' % data['media_id'])
    play_library_media(context, data)


def play_library_media(context, data):
    up_next = True
    if '&upnext=false' in data['url']:
        up_next = False
        data['url'] = data['url'].replace('&upnext=false', '')

    server = context.plex_network.get_server_from_url(data['url'])
    media_id = data['url'].split('?')[0].split('&')[0].split('/')[-1]

    if 'includeMarkers' not in data['url']:
        data['url'] += '&' if '?' in data['url'] else '?'
        data['url'] += 'includeMarkers=1'

    if 'includeGuids' not in data['url']:
        data['url'] += '&includeGuids=1'

    tree = get_xml(context, data['url'])
    if tree is None:
        return

    stream = StreamData(context, server, tree).stream

    stream_data = stream.get('full_data', {})
    stream_media = stream.get('media', {})

    if data.get('force') and stream['type'] == 'music':
        play_playlist(context, server, stream)
        return

    url = MediaSelect(context, server, stream).media_url

    if url is None:
        return

    transcode = is_transcode_required(context, stream.get('details', [{}]), data['transcode'])
    try:
        transcode_profile = int(data['transcode_profile'])
    except ValueError:
        transcode_profile = 0

    url, session = get_playback_url_and_session(server, url, stream, transcode, transcode_profile)

    details = {
        'resume': int(int(stream_media.get('viewOffset', 0)) / 1000),
        'duration': int(int(stream_media.get('duration', 0)) / 1000),
    }

    if isinstance(data.get('force'), int):
        if int(data['force']) > 0:
            details['resume'] = int(int(data['force']) / 1000)
        else:
            details['resume'] = data['force']

    details['resuming'] = is_resuming_video()

    list_item = create_playback_item(url, stream, stream_data, details)

    if stream['type'] in ['music', 'video']:
        server.settings = None
        write_pickled('playback_monitor.pickle', {
            'details': details,
            'media_id': media_id,
            'playing_file': url,
            'session': session,
            'server': server,
            'stream': stream,
            'up_next': up_next,
            'callback_args': {
                'transcode': transcode,
                'transcode_profile': transcode_profile
            }
        })

    xbmcplugin.setResolvedUrl(get_handle(), True, list_item)
    set_now_playing_properties(server, media_id, stream)


def create_playback_item(url, streams, data, details):
    if not data:
        data = {}

    stream_art = streams.get('art', {})
    list_item = xbmcgui.ListItem(path=url, offscreen=True)

    if data:
        fanart = stream_art.get('fanart', '') or stream_art.get('section_art', '')
        thumb = stream_art.get('thumb', '') or stream_art.get('section_art', '') or stream_art.get('fanart', '')

        poster = ''
        media_type = data.get('mediatype', '')
        if media_type == 'movie':
            poster = thumb
            db_media_type = 'movie'
            tmdb_id = streams.get('guid_ids', {}).get('tmdb_id', '')
        elif media_type == 'episode':
            poster = stream_art.get('season_thumb', '') or stream_art.get('show_thumb', '')
            db_media_type = 'tv'
            # Try to use the show TMDB ID extracted in StreamData
            tmdb_id = streams.get('show_tmdb_id', '')
            # Fallback if not found
            if not tmdb_id:
                tmdb_id = streams.get('guid_ids', {}).get('tmdb_id', '')
        else:
            db_media_type = media_type
            tmdb_id = streams.get('guid_ids', {}).get('tmdb_id', '')

        clearlogo = _get_clearlogo_cached(tmdb_id, db_media_type)

        list_item.setArt({
            'icon': thumb,
            'thumb': thumb,
            'poster': poster,
            'fanart': fanart,
            'banner': stream_art.get('banner'),
            'clearlogo': clearlogo,
            'tvshow.clearlogo': clearlogo, # لعيون سكين Arctic Fuse 3
        })

    # remove keys not recognized by infotagger before set_info
    for _key in ('tmdb_id', 'tvdb_id', 'imdb_id'):
        data.pop(_key, None)

    info_tag = ListItemInfoTag(list_item, streams['type'])
    info_tag.set_info(data)
    time_dict = {'TotalTime': int(details['duration'])}
    if details.get('resuming') and details.get('resume'):
        time_dict['ResumeTime'] = int(details['resume'])
        data['playcount'] = '0'

    info_tag.set_resume_point(time_dict)

    if streams['type'] == 'music':
        list_item.setProperty('culrc.source', i18n('Plex powered by LyricFind'))

    guid_ids = streams.get('guid_ids', {})
    if guid_ids.get('imdb_id'):
        list_item.setProperty('IMDBNumber', guid_ids['imdb_id'])
        list_item.setProperty('imdb_id', guid_ids['imdb_id'])
    if guid_ids.get('tmdb_id'):
        list_item.setProperty('tmdb_id', guid_ids['tmdb_id'])
    if guid_ids.get('tvdb_id'):
        list_item.setProperty('tvdb_id', guid_ids['tvdb_id'])

    # --- التعديل الجذري للترجمات لضمان ظهور اللغات ---
    subtitles_all = streams.get('subtitles_all', [])
    LOG.debug('subtitles_all count: %d' % len(subtitles_all))
    
    if subtitles_all:
        import os
        tmp_dir = xbmcvfs.translatePath('special://temp/dplex_subs/')
        try:
            if not xbmcvfs.exists(tmp_dir):
                xbmcvfs.mkdirs(tmp_dir)
        except:
            pass

        sub_paths = []
        for sub in subtitles_all:
            sub_url = sub.get('key')
            if not sub_url:
                continue
                
            lang = sub.get('language') or sub.get('languageCode') or 'und'
            fmt = (sub.get('format') or sub.get('codec') or 'srt').lower()
            stream_id = sub.get('id', '0')
            filename = '%s.%s.%s' % (stream_id, lang, fmt)
            local_path = os.path.join(tmp_dir, filename)

            try:
                # نحمل الترجمة فوراً لتمرير المسار المحلي الذي يحتوي على اسم اللغة لكودي
                if not xbmcvfs.exists(local_path):
                    xbmcvfs.copy(sub_url, local_path)
                
                if xbmcvfs.exists(local_path):
                    sub_paths.append(local_path)
                else:
                    sub_paths.append(sub_url)
            except:
                sub_paths.append(sub_url)

        if sub_paths:
            list_item.setSubtitles(sub_paths)
    # ------------------------------------------------

    return list_item


def set_now_playing_properties(server, media_id, stream=None):
    window = xbmcgui.Window(10000)
    window.setProperty('plugin.video.composite-nowplaying.server', server.get_location())
    window.setProperty('plugin.video.composite-nowplaying.id', media_id)

    if stream:
        guid_ids = stream.get('guid_ids', {})
        if guid_ids.get('imdb_id'):
            window.setProperty('plugin.video.composite-nowplaying.imdb_id', guid_ids['imdb_id'])
        if guid_ids.get('tmdb_id'):
            window.setProperty('plugin.video.composite-nowplaying.tmdb_id', guid_ids['tmdb_id'])
        if guid_ids.get('tvdb_id'):
            window.setProperty('plugin.video.composite-nowplaying.tvdb_id', guid_ids['tvdb_id'])


def get_playback_url_and_session(server, url, streams, transcode, transcode_profile):
    protocol = url.split(':', 1)[0]

    if protocol == 'file':
        return url.split(':', 1)[1], None

    if protocol.startswith('http'):
        if transcode:
            return server.get_universal_transcode(streams['extra']['path'],
                                                  transcode_profile=transcode_profile)
        if 'X-Plex-Token' in url:
            return url, None
        return server.get_formatted_url(url), None

    return url, None


def is_transcode_required(context, stream_details, default=False):
    if context.settings.always_transcode():
        return True

    codec = stream_details[0].get('codec')
    resolution = stream_details[0].get('videoResolution')
    try:
        bit_depth = int(stream_details[0].get('bitDepth', 8))
    except ValueError:
        bit_depth = None

    if codec and (context.settings.transcode_hevc() and codec.lower() == 'hevc'):
        return True
    if resolution and (context.settings.transcode_g1080() and resolution.lower() == '4k'):
        return True
    if bit_depth and (context.settings.transcode_g8bit() and bit_depth > 8):
        return True

    return default


class StreamData:

    def __init__(self, context, server, tree):
        self.context = context
        self.server = server
        self.tree = tree
        self._content = None

        self.data = {
            'contents': 'type',
            'audio': {},
            'audio_count': 0,
            'subtitle': {},
            'subtitles_all': [],
            'sub_count': 0,
            'parts': [],
            'parts_count': 0,
            'media': {},
            'details': [],
            'sub_offset': -1,
            'audio_offset': -1,
            'full_data': {},
            'type': 'video',
            'intro_markers': [],
            'guid_ids': {},
            'extra': {},
            'show_tmdb_id': '', # تمت إضافتها لتخزين ID المسلسل
        }

        self.update_data()

    def update_data(self):
        if not self._get_content():
            return

        self.data['media']['viewOffset'] = self._content.get('viewOffset', 0)
        self.data['media']['duration'] = self._content.get('duration', 12 * 60 * 60)

        if self.data['type'] == 'video':
            self._get_video_data()
        if self.data['type'] == 'music':
            self._get_track_data()

        self._get_art()
        self._get_media_details()

        if (self.data['type'] == 'video' and
                self.context.settings.stream_control() == StreamControl().PLEX):
            self._get_audio_and_subtitles()

    @property
    def stream(self):
        return self.data

    def _get_content(self):
        for tag, media_type in [('Video', 'video'), ('Track', 'music'), ('Photo', 'picture')]:
            content = self.tree.find(tag)
            if content is not None:
                self.data['type'] = media_type
                self.data['extra']['path'] = content.get('key')
                self._content = content
                return True
        return False

    def _get_video_data(self):
        self.data['full_data'] = {
            'plot': encode_utf8(self._content.get('summary', '')),
            'title': encode_utf8(self._content.get('title', i18n('Unknown'))),
            'sorttitle': encode_utf8(
                self._content.get('titleSort', self._content.get('title', i18n('Unknown')))
            ),
            'rating': float(self._content.get('rating', 0)),
            'studio': [encode_utf8(self._content.get('studio', ''))],
            'mpaa': encode_utf8(self._content.get('contentRating', '')),
            'year': int(self._content.get('year', 0) or 0),
            'tagline': self._content.get('tagline', ''),
            'mediatype': 'video'
        }

        if self._content.get('type') == 'movie':
            self.data['full_data']['mediatype'] = 'movie'
        elif self._content.get('type') == 'episode':
            self.data['full_data']['episode'] = int(self._content.get('index', 0))
            self.data['full_data']['aired'] = self._content.get('originallyAvailableAt', '')
            self.data['full_data']['tvshowtitle'] = encode_utf8(
                self._content.get('grandparentTitle', self.tree.get('grandparentTitle', ''))
            )
            self.data['full_data']['season'] = int(
                self._content.get('parentIndex', self.tree.get('parentIndex', 0))
            )
            self.data['full_data']['mediatype'] = 'episode'

            # --- تعديل لاستخراج TMDB ID الخاص بالمسلسل (ضروري للوجوهات) ---
            show_tmdb_id = ''
            gp_guid = self._content.get('grandparentGuid', '')
            if 'themoviedb://' in gp_guid:
                show_tmdb_id = gp_guid.split('themoviedb://')[1].split('?')[0].replace('tv-', '')
            
            # إذا لم يكن موجوداً مباشرة، سنقوم بجلبه من تفاصيل المسلسل من بليكس
            if not show_tmdb_id and self._content.get('grandparentKey'):
                try:
                    gp_url = self.server.get_formatted_url(self._content.get('grandparentKey') + '?includeGuids=1')
                    gp_tree = get_xml(self.context, gp_url)
                    if gp_tree is not None:
                        gp_dir = gp_tree.find('Directory')
                        if gp_dir is not None:
                            gp_guids = get_guid_ids(gp_dir)
                            show_tmdb_id = gp_guids.get('tmdb_id', '')
                except Exception as e:
                    LOG.debug('Failed to fetch grandparent for clearlogo: %s' % str(e))
            
            self.data['show_tmdb_id'] = show_tmdb_id
            # ----------------------------------------------------------------

        if not self.context.settings.skip_metadata():
            tree_genres = self._content.findall('Genre')
            if tree_genres:
                self.data['full_data']['genre'] = \
                    [encode_utf8(x.get('tag', '')) for x in tree_genres]

        self.data['intro_markers'] = self._get_intro_markers()
        self.data['guid_ids'] = get_guid_ids(self._content)
        if self.data['guid_ids'].get('imdb_id'):
            self.data['full_data']['imdbnumber'] = self.data['guid_ids']['imdb_id']
        if self.data['guid_ids'].get('tmdb_id'):
            self.data['full_data']['tmdb_id'] = self.data['guid_ids']['tmdb_id']
        if self.data['guid_ids'].get('tvdb_id'):
            self.data['full_data']['tvdb_id'] = self.data['guid_ids']['tvdb_id']

    def _get_track_data(self):
        track_title = '%s. %s' % (
            str(self._content.get('index', 0)).zfill(2),
            encode_utf8(self._content.get('title', i18n('Unknown')))
        )

        self.data['full_data'] = {
            'TrackNumber': int(self._content.get('index', 0)),
            'discnumber': int(self._content.get('parentIndex', 0)),
            'title': track_title,
            'rating': float(self._content.get('rating', 0)),
            'album': encode_utf8(self._content.get('parentTitle', self.tree.get('parentTitle', ''))),
            'artist': encode_utf8(self._content.get('grandparentTitle', self.tree.get('grandparentTitle', ''))),
            'duration': int(self._content.get('duration', 0)) / 1000,
            'lyrics': self._get_lyrics(),
        }

        self.data['extra']['album'] = self._content.get('parentKey')
        self.data['extra']['index'] = self._content.get('index')

    def _get_intro_markers(self):
        for marker in self._content.iter('Marker'):
            if (marker.get('type') == 'intro' and
                    marker.get('startTimeOffset') and marker.get('endTimeOffset')):
                return [marker.get('startTimeOffset'), marker.get('endTimeOffset')]
        return []

    def _get_lyrics(self):
        lyrics = []
        lyric_priorities = self.context.settings.get_lyrics_priorities()
        if not lyric_priorities:
            return ''

        for stream in self._content.iter('Stream'):
            if (stream.get('provider') == 'com.plexapp.agents.lyricfind' and
                    stream.get('streamType') == '4'):
                lyric = {
                    'codec': stream.get('codec', ''),
                    'title': stream.get('displayTitle', ''),
                    'format': stream.get('format', ''),
                    'id': stream.get('id', ''),
                    'key': stream.get('key', ''),
                    'provider': stream.get('provider', 'com.plexapp.agents.lyricfind'),
                    'streamType': stream.get('streamType', '4'),
                }
                lyric['priority'] = lyric_priorities.get(lyric.get('codec', 'none'), 0)
                lyrics.append(lyric)

        if lyrics:
            lyrics = sorted(lyrics, key=lambda l: l['priority'], reverse=True)
            return self.server.get_lyrics(lyrics[0]['id'])
        return ''

    def _get_art(self):
        art = {'banner': '', 'fanart': '', 'season_thumb': '', 'section_art': '', 'show_thumb': '', 'thumb': ''}

        if self.context.settings.skip_images():
            self.data['art'] = art
            return

        art.update({
            'banner': get_banner_image(self.context, self.server, self.tree),
            'fanart': get_fanart_image(self.context, self.server, self._content),
            'season_thumb': '',
            'section_art': get_fanart_image(self.context, self.server, self.tree),
            'show_thumb': '',
            'thumb': get_thumb_image(self.context, self.server, self._content),
        })

        if '/:/resources/show-fanart.jpg' in art['section_art']:
            art['section_art'] = art.get('fanart', '')
        if art['fanart'] == '':
            art['fanart'] = art.get('section_art', '')

        if (self._content.get('grandparentThumb', '') and
                '/:/resources/show.png' not in self._content.get('grandparentThumb', '')):
            art['show_thumb'] = get_thumb_image(self.context, self.server,
                                                {'thumb': self._content.get('grandparentThumb', '')})

        if (art.get('season_thumb', '') and
                '/:/resources/show.png' not in art.get('season_thumb', '')):
            art['season_thumb'] = get_thumb_image(self.context, self.server,
                                                  {'thumb': art.get('season_thumb')})

        if (not art.get('season_thumb', '') and self._content.get('parentThumb', '') and
                '/:/resources/show.png' not in self._content.get('parentThumb', '')):
            art['season_thumb'] = get_thumb_image(self.context, self.server,
                                                  {'thumb': self._content.get('parentThumb', '')})
        elif not art.get('season_thumb', '') and art['show_thumb']:
            art['season_thumb'] = art['show_thumb']

        self.data['art'] = art

    def _get_media_details(self):
        media = self._content.findall('Media')
        self.data['details'] = []
        self.data['parts'] = []
        self.data['parts_count'] = 0

        for details in media:
            premium_label = _get_premium_info(details)
            media_details = {
                'premium_label': premium_label,
                'bitrate': round(float(details.get('bitrate', 0)) / 1000, 1),
                'bitDepth': details.get('bitDepth', 8),
                'videoResolution': details.get('videoResolution', ''),
                'container': details.get('container', 'unknown'),
                'codec': details.get('videoCodec'),
            }

            for part in details.findall('Part'):
                self.data['parts'].append((part.get('key'), part.get('file')))
                self.data['details'].append(media_details)
                self.data['parts_count'] += 1

    def _get_audio_and_subtitles(self):
        default_to_forced = self.context.settings.default_forced_subtitles()

        audio_offset = 0
        sub_offset = 0

        self.data['contents'] = 'all'
        self.data['audio_count'] = 0
        self.data['sub_count'] = 0
        self.data['subtitles_all'] = []

        forced_subtitle = False

        for bits in self.tree.iter('Stream'):
            stream = dict(bits.items())

            if stream['streamType'] == '2':
                self.data['audio_count'] += 1
                audio_offset += 1
                if stream.get('selected') == '1':
                    self.data['audio'] = stream
                    self.data['audio_offset'] = audio_offset

            elif stream['streamType'] == '3':
                if forced_subtitle:
                    continue

                if sub_offset == -1:
                    sub_offset = int(stream.get('index', -1))
                elif 0 < int(stream.get('index', -1)) < sub_offset:
                    sub_offset = int(stream.get('index', -1))

                forced_subtitle = stream.get('forced') == '1' and default_to_forced
                selected = stream.get('selected') == '1'

                if stream.get('key'):
                    sub_copy = dict(stream)
                    sub_copy['key'] = self.server.get_formatted_url(stream['key'])
                    self.data['subtitles_all'].append(sub_copy)

                if forced_subtitle or selected:
                    self.data['sub_count'] += 1
                    self.data['subtitle'] = stream
                    if stream.get('key'):
                        self.data['subtitle']['key'] = self.server.get_formatted_url(stream['key'])
                    else:
                        self.data['sub_offset'] = int(stream.get('index')) - sub_offset


class MediaSelect:
    def __init__(self, context, server, data):
        self.context = context
        self.server = server
        self.data = data
        self.dvd_playback = False
        self._media_index = None
        self._media_url = None
        self.update_selection()

    def update_selection(self):
        self._select_media()
        self._get_media_url()

    @property
    def media_url(self):
        return self._media_url

    @media_url.setter
    def media_url(self, value):
        self._media_url = value

    def _select_media(self):
        force_dvd = self.context.settings.force_dvd()
        count = self.data['parts_count']
        options = self.data['parts']
        details = self.data['details']

        if count > 1:
            dialog_options = []
            dvd_index = []
            index_count = 0

            main_title = self.data['full_data'].get('title', i18n('Unknown'))
            if self.data['full_data'].get('mediatype') == 'episode':
                show_title = self.data['full_data'].get('tvshowtitle', '')
                s = str(self.data['full_data'].get('season', 0)).zfill(2)
                e = str(self.data['full_data'].get('episode', 0)).zfill(2)
                main_title = '%s  S%sE%s - %s' % (show_title, s, e, main_title)

            art = self.data.get('art', {})
            thumb = art.get('thumb') or art.get('poster') or art.get('fanart') or ''

            for items in options:
                if force_dvd and items[1] and '.ifo' in items[1].lower():
                    dvd_index.append(index_count)

                list_item = xbmcgui.ListItem(label=main_title)
                premium_label = details[index_count].get('premium_label', '')
                list_item.setLabel2(premium_label if premium_label else 'Version %d' % (index_count + 1))

                if thumb:
                    try:
                        art_url = self.server.get_formatted_url(thumb)
                        list_item.setArt({'thumb': art_url, 'poster': art_url, 'icon': art_url})
                    except Exception:
                        pass

                dialog_options.append(list_item)
                index_count += 1

            result = xbmcgui.Dialog().select(i18n('Select version to play'), dialog_options, useDetails=True)

            if result == -1:
                self._media_index = None
            else:
                if result in dvd_index:
                    self.dvd_playback = True
                self._media_index = result
        else:
            if force_dvd and options and options[0][1] and '.ifo' in options[0][1].lower():
                self.dvd_playback = True
            self._media_index = 0


    def _direct_stream_url(self, stream):
        """Return the standard Plex direct stream URL.

        Use query-parameter formatted URLs for playback. Some Kodi builds and
        network stacks fail intermittently with pipe-header formatted HTTPS URLs.
        The standard formatted URL matches the older, more stable behavior.
        """
        return self.server.get_formatted_url(stream)

    def _get_media_url(self):
        if self._media_index is None:
            self.media_url = None
            return

        stream = self.data['parts'][self._media_index][0]
        filename = self.data['parts'][self._media_index][1]

        if self._http(filename, stream):
            return
        file_type = get_file_type(filename)
        if self._auto(filename, file_type, stream):
            return
        if self._smb_afp(filename, file_type):
            return
        self.media_url = self._direct_stream_url(stream)

    def _http(self, filename, stream):
        if filename is None or self.context.settings.get_stream() == '1':
            self.media_url = self._direct_stream_url(stream)
            return True
        return False

    def _auto(self, filename, file_type, stream):
        if self.context.settings.get_stream() == '0':
            if file_type in ['NIX', 'WIN'] and xbmcvfs.exists(filename):
                self.media_url = 'file:%s' % filename
                return True
            if self.dvd_playback:
                self.context.settings.set_stream('2')
            else:
                self.media_url = self._direct_stream_url(stream)
                return True
        return False

    def _smb_afp(self, filename, file_type):
        if self.context.settings.get_stream() in ['2', '3']:
            filename = unquote(filename)
            protocol = 'smb' if self.context.settings.get_stream() == '2' else 'afp'

            if file_type == 'UNC':
                self.media_url = '%s:%s' % (protocol, filename.replace('\\', '/'))
            else:
                server = self.server.get_location().split(':')[0]
                login_string = ''
                override_info = self.context.settings.override_info()

                if override_info.get('override'):
                    if override_info.get('ip_address'):
                        server = override_info.get('ip_address')
                    if override_info.get('user_id'):
                        login_string = '%s:%s@' % (override_info.get('user_id'),
                                                   override_info.get('password'))

                if filename.find('Volumes') > 0:
                    self.media_url = '%s:/%s' % (protocol, filename.replace('Volumes', login_string + server))
                elif file_type == 'WIN':
                    self.media_url = '%s://%s%s/%s' % (protocol, login_string, server, filename[3:].replace('\\', '/'))
                else:
                    self.media_url = '%s://%s%s%s' % (protocol, login_string, server, filename)

            self._nas_override()
            return self.media_url is not None
        return False

    def _nas_override(self):
        override_info = self.context.settings.override_info()
        if override_info.get('override') and override_info.get('root'):
            if '/' + override_info.get('root') + '/' in self.media_url:
                components = self.media_url.split('/')
                index = components.index(override_info.get('root'))
                for _ in range(3, index):
                    components.pop(3)
                self.media_url = '/'.join(components)


def play_playlist(context, server, data):
    playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    playlist.clear()

    url = server.join_url(server.get_url_location(), data['extra'].get('album'), 'children')
    tree = get_xml(context, url)
    if tree is None:
        return

    for track in tree.findall('Track'):
        item = Item(server, None, tree, track)
        track = create_track_item(context, item, listing=False)
        url = track[0]
        details = track[1]
        list_item = xbmcgui.ListItem(details.get('title', i18n('Unknown')), offscreen=True)

        thumb = data['full_data'].get('thumbnail', CONFIG['icon'])
        if 'thumbnail' in data['full_data']:
            del data['full_data']['thumbnail']

        list_item.setArt({'icon': thumb, 'thumb': thumb})
        info_tag = ListItemInfoTag(list_item, 'music')
        info_tag.set_info(details)
        playlist.add(url, list_item)

    index = int(data['extra'].get('index', 0)) - 1
    xbmc.Player().playselected(index)
