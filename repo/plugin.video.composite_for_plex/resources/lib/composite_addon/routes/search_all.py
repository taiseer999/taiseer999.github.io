# -*- coding: utf-8 -*-

"""
Copyright (C) 2020-2026 DPlex (plugin.video.composite_for_plex)
Advanced Global Search with Media Info Injection (Multi-Threaded).
Supports direct GUID search (imdb_id/tvdb_id) with title fallback.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote, unquote

import xbmc
import xbmcgui
import xbmcplugin

from ..addon.common import get_handle
from ..addon.containers import Item
from ..addon.items.episode import create_episode_item
from ..addon.items.movie import create_movie_item
from ..addon.logger import Logger
from ..addon.strings import i18n
from ..plex import plex

LOG = Logger()


def _fetch_full_metadata(server, rating_key):
    try:
        url = '/library/metadata/%s?includeGuids=1' % rating_key
        try:
            from .plex_request import cached_get
            tree = cached_get(server, url)
        except ImportError:
            tree = server.processed_xml(url)
        if tree is None:
            return None
        return tree.find('.//Video') or tree.find('Video')
    except Exception as e:
        LOG.debug('Error fetching metadata: %s' % str(e))
        return None


def _get_media_info(element):
    if element is None:
        return '', ''

    media = element.find('Media') or element.find('.//Media')
    if media is None:
        return '', ''

    parts = []

    res = media.get('videoResolution', '')
    if res:
        try:
            r = int(res)
            res_label = '4K' if r > 1088 else ('1080p' if r >= 1080 else ('720p' if r >= 720 else 'SD'))
        except ValueError:
            res_label = res.upper()
        parts.append('[ %s ]' % res_label)

    part_el = media.find('Part') or media.find('.//Part')
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
        amap = {
            'truehd': 'TrueHD', 'dca': 'DTS', 'dts': 'DTS',
            'dtshd': 'DTS-HD', 'eac3': 'EAC3', 'ac3': 'AC3',
            'aac': 'AAC', 'mp3': 'MP3', 'flac': 'FLAC',
        }
        a_label = amap.get(a_codec, a_codec.upper())
        if audio_extra:
            a_label += ' ' + audio_extra
        if a_ch:
            ch_map = {'1': '1.0', '2': '2.0', '6': '5.1', '8': '7.1'}
            a_label += ' ' + ch_map.get(str(a_ch), '%sch' % a_ch)
        parts.append('[ %s ]' % a_label)

    size_str = ''
    if part_el is not None:
        sz = part_el.get('size', '')
        if sz:
            try:
                gb = int(sz) / (1024 ** 3)
                size_str = ('[ %.1f GB ]' % gb) if gb >= 1 else ('[ %.0f MB ]' % (int(sz) / (1024 ** 2)))
                parts.append(size_str)
            except ValueError:
                pass

    return ' • '.join(parts), size_str


def _build_list_item(server, res, video_type, media_info, size_str, srv_name):
    if video_type == 'movie':
        year = res.get('year', '')
        main_title = '%s (%s)' % (res.get('title', ''), year) if year else res.get('title', '')
    else:
        main_title = '%s  S%sE%s - %s' % (
            res.get('grandparentTitle', ''),
            str(res.get('parentIndex', '')).zfill(2),
            str(res.get('index', '')).zfill(2),
            res.get('title', i18n('Unknown')),
        )

    list_item = xbmcgui.ListItem(label=main_title)

    sub = []
    quality = media_info.replace(size_str, '').rstrip(' •').strip() if media_info else ''
    if quality:
        sub.append(quality)
    if srv_name:
        sub.append('[%s]' % srv_name)
    if size_str:
        sub.append(size_str)
    if sub:
        list_item.setLabel2('  |  '.join(p for p in sub if p))

    thumb = res.get('thumb') or res.get('grandparentThumb') or res.get('parentThumb') or ''
    if thumb:
        try:
            art_url = server.get_formatted_url(thumb)
            list_item.setArt({'thumb': art_url, 'poster': art_url, 'icon': art_url})
        except Exception as e:
            LOG.debug('Art error: %s' % str(e))

    return list_item


def _search_by_guid(srv, guid_url):
    """Search Plex by GUID (imdb:// or tvdb://) — returns list of (uuid, xml, element)"""
    results = []
    try:
        url = '/library/all?guid=%s&includeGuids=1' % quote(guid_url)
        xml = srv.processed_xml(url)
        if xml is not None and xml.get('size', '0') != '0':
            results = [(srv.get_uuid(), xml, x) for x in xml]
    except Exception as e:
        LOG.debug('GUID search error on %s: %s' % (srv.get_uuid(), str(e)))
    return results


def _search_section(srv, sec, c_type, s_type, query):
    """Search in one section by title — called in parallel"""
    results = []
    try:
        if sec.get_type() != c_type:
            return results
        url = '%s/all?type=%s&title=%s' % (sec.get_path(), s_type, query)
        xml = srv.processed_xml(url)
        if xml is not None and xml.get('size', '0') != '0':
            results = [(srv.get_uuid(), xml, x) for x in xml]
    except Exception as e:
        LOG.debug('Section search error: %s' % str(e))
    return results


def _get_servers_and_sections(context):
    servers = []
    search_tasks = []
    for srv in context.plex_network.get_server_list():
        try:
            servers.append(srv)
            for sec in srv.get_sections():
                search_tasks.append((srv, sec))
        except Exception as e:
            LOG.debug('Server error: %s' % str(e))
    return servers, search_tasks


def run(context):
    context.plex_network = plex.Plex(context.settings, load=True)
    p = context.params

    if 'video_type' not in p:
        return

    v_type = p['video_type']
    c_type = {'movie': 'movie', 'episode': 'show'}.get(v_type)
    s_type = {'movie': '1', 'episode': '4'}.get(v_type)

    if not c_type or not s_type:
        xbmcplugin.endOfDirectory(get_handle(), succeeded=False, cacheToDisc=False)
        return

    servers, search_tasks = _get_servers_and_sections(context)

    raw_results = []

    # ── 1. GUID Search (imdb_id / tvdb_id) ─────────────────────────────
    imdb_id = p.get('imdb_id', '')
    tvdb_id = p.get('tvdb_id', '')

    guid_url = ''
    if imdb_id and v_type == 'movie':
        guid_url = 'imdb://%s' % imdb_id
    elif tvdb_id and v_type == 'episode':
        guid_url = 'tvdb://%s' % tvdb_id

    if guid_url:
        LOG.debug('Searching by GUID: %s' % guid_url)
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(_search_by_guid, srv, guid_url): srv for srv in servers}
            for future in as_completed(futures):
                try:
                    raw_results.extend(future.result())
                except Exception as e:
                    LOG.debug('GUID future error: %s' % str(e))

    # ── 2. Title Search (fallback or primary if no GUID) ────────────────
    if not raw_results:
        if not p.get('query'):
            p['query'] = _get_search_query()
        if not p.get('query'):
            xbmcplugin.endOfDirectory(get_handle(), succeeded=False, cacheToDisc=False)
            return

        p['query'] = quote(unquote(p['query']))
        context.params = p

        LOG.debug('Falling back to title search: %s' % p['query'])
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                executor.submit(_search_section, srv, sec, c_type, s_type, p['query']): (srv, sec)
                for srv, sec in search_tasks
            }
            for future in as_completed(futures):
                try:
                    raw_results.extend(future.result())
                except Exception as e:
                    LOG.debug('Title future error: %s' % str(e))

    if not raw_results:
        xbmcgui.Dialog().notification(
            i18n('Search'), i18n('No results found'),
            xbmcgui.NOTIFICATION_INFO, 3000
        )
        xbmcplugin.endOfDirectory(get_handle(), succeeded=False, cacheToDisc=False)
        return

    # ── 3. Fetch metadata in parallel ──────────────────────────────────
    items = []
    dialog_items = []

    def _process_result(entry):
        s_uuid, tree, res = entry
        try:
            srv = context.plex_network.get_server_from_uuid(s_uuid)
            s_name = srv.get_name() if hasattr(srv, 'get_name') else ''
            rk = res.get('ratingKey', '')
            full = _fetch_full_metadata(srv, rk) if rk else None
            elem = full if full is not None else res
            m_info, s_str = _get_media_info(elem)

            orig_title = res.get('title', i18n('Unknown'))
            if m_info:
                res.set('title', '%s  %s' % (orig_title, m_info))

            li = _build_list_item(srv, res, v_type, m_info, s_str, s_name)
            item = Item(srv, '', tree, res)
            return li, item
        except Exception as e:
            LOG.debug('Process error: %s' % str(e))
            return None

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(_process_result, entry) for entry in raw_results]
        for future in as_completed(futures):
            result = future.result()
            if result:
                li, item = result
                dialog_items.append(li)
                items.append(item)

    if not items:
        xbmcplugin.endOfDirectory(get_handle(), succeeded=False, cacheToDisc=False)
        return

    # ── 4. If single result from GUID → play directly ──────────────────
    if guid_url and len(items) == 1:
        sel = 0
    else:
        combined = list(zip(dialog_items, items))
        combined.sort(key=lambda x: x[1].data.get('title', '').lower())
        dialog_items, items = map(list, zip(*combined)) if combined else ([], [])
        sel = xbmcgui.Dialog().select(i18n('Select to play'), dialog_items, useDetails=True)

    if sel >= 0:
        final_item = items[sel]
        if v_type == 'movie':
            ready = create_movie_item(context, final_item)
        else:
            ready = create_episode_item(context, final_item)

        xbmcplugin.addDirectoryItems(get_handle(), [ready], 1)
        xbmcplugin.setContent(get_handle(), 'movies' if v_type == 'movie' else 'episodes')
        xbmcplugin.endOfDirectory(get_handle(), succeeded=True, cacheToDisc=False)
    else:
        xbmcplugin.endOfDirectory(get_handle(), succeeded=False, cacheToDisc=False)


def _get_search_query():
    kb = xbmc.Keyboard('', i18n('Search...'))
    kb.setHeading(i18n('Enter search term'))
    kb.doModal()
    if kb.isConfirmed():
        text = kb.getText().strip()
        return text if text else ''
    return ''

