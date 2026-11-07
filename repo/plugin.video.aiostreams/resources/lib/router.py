# -*- coding: utf-8 -*-
import json
import os
import sys
from urllib.parse import parse_qsl

import xbmc
import xbmcgui
import xbmcplugin

from . import kodi, items, streams as st
from .api import AIOMetadata, AIOStreams, ApiError, cache_clear, normalise_manifest_url

HISTORY_FILE = os.path.join(kodi.PROFILE, 'search_history.json')
LAST_STREAMS = os.path.join(kodi.PROFILE, 'last_streams.json')


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _client():
    if not kodi.setting('manifest_url'):
        return None
    return AIOStreams()


def _meta_configured():
    return bool(kodi.setting('meta_url'))


def _sources():
    """Catalog sources in display order: 'm' = AIOMetadata, 'a' = AIOStreams."""
    mode = kodi.setting_int('catalog_source', 1)  # 0 AIOStreams, 1 AIOMetadata, 2 both
    if not _meta_configured() or mode == 0:
        return ['a']
    return ['m'] if mode == 1 else ['m', 'a']


def _src(params):
    # URLs without src (widgets made before 1.1.0) keep pointing at AIOStreams
    src = params.get('src') or 'a'
    return 'm' if src == 'm' and _meta_configured() else 'a'


def _cat_client(src):
    return AIOMetadata() if src == 'm' else AIOStreams()


def _search_cats():
    """(src, catalog) pairs that accept a search. Falls back to AIOStreams'
    own search when the chosen source (AIOMetadata) offers none."""
    cats = []
    for src in _sources():
        try:
            cats += [(src, c) for c in _cat_client(src).catalogs() if _extra(c, 'search')]
        except ApiError as e:
            kodi.log('search catalogs (%s) failed: %s' % (src, e))
    if not cats and 'a' not in _sources():
        try:
            cats = [('a', c) for c in AIOStreams().catalogs() if _extra(c, 'search')]
        except ApiError as e:
            kodi.log('search catalogs (fallback) failed: %s' % e)
    return cats


def _stream_id(params):
    """AIOMetadata movie ids can be tmdb:/tvdb:; map them to IMDb for AIOStreams."""
    type_, vid = params['type'], params['id']
    if params.get('src') == 'm' and type_ == 'movie' and _meta_configured() \
            and kodi.setting_bool('prefer_imdb') and not vid.startswith('tt'):
        return AIOMetadata().imdb_for(type_, vid)
    return vid


def _end(content=None, cache=True, sort=False):
    if content:
        xbmcplugin.setContent(kodi.HANDLE, content)
    if sort:
        xbmcplugin.addSortMethod(kodi.HANDLE, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(kodi.HANDLE, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(kodi.HANDLE, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
    xbmcplugin.endOfDirectory(kodi.HANDLE, succeeded=True, cacheToDisc=cache)


def _fail(err):
    kodi.log('error: %s' % err, xbmc.LOGERROR)
    kodi.notify(str(err)[:200], kodi.s(30103))
    if kodi.HANDLE >= 0:
        xbmcplugin.endOfDirectory(kodi.HANDLE, succeeded=False)


def _add(url, li, folder=True):
    xbmcplugin.addDirectoryItem(kodi.HANDLE, url, li, isFolder=folder)


def _load_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _save_json(path, data):
    kodi.ensure_dir(os.path.dirname(path))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f)


def _extra(cat, name):
    for ex in cat.get('extra') or []:
        if ex.get('name') == name:
            return ex
    # legacy manifests
    if name in (cat.get('extraSupported') or []):
        return {'name': name, 'isRequired': name in (cat.get('extraRequired') or [])}
    return None


def _context_for_meta(type_, meta_id, name, src='a'):
    ctx = [(kodi.s(30040), 'Container.Update(%s)' % kodi.build_url(action='streams', type=type_, id=meta_id, title=name, src=src))]
    if type_ == 'movie':
        ctx.append((kodi.s(30041), 'PlayMedia(%s)' % kodi.build_url(action='play', type=type_, id=meta_id, auto=1, src=src)))
    return ctx


# --------------------------------------------------------------------------
# root / catalogs
# --------------------------------------------------------------------------

def root(params):
    client = _client()
    if client is None:
        li = items.folder_item('[B]%s[/B]' % kodi.s(30020), icon=items.icon('manifest'))
        _add(kodi.build_url(action='set_manifest'), li, folder=False)
        li = items.folder_item(kodi.s(30027), icon=items.icon('settings'))
        _add(kodi.build_url(action='settings'), li, folder=False)
        return _end(cache=False)
    try:
        manifest = client.manifest()
    except ApiError as e:
        li = items.folder_item('[COLOR red]%s[/COLOR]' % e, icon=items.icon('error'), plot=str(e))
        _add(kodi.build_url(action='settings'), li, folder=False)
        li = items.folder_item(kodi.s(30020), icon=items.icon('manifest'))
        _add(kodi.build_url(action='set_manifest'), li, folder=False)
        return _end(cache=False)

    sources = _sources()
    loaded = []
    for src in sources:
        c = client if src == 'a' else _cat_client(src)
        try:
            m = c.manifest()
        except ApiError as e:
            li = items.folder_item('[COLOR red]AIOMetadata: %s[/COLOR]' % e, icon=items.icon('error'), plot=str(e))
            _add(kodi.build_url(action='set_meta'), li, folder=False)
            continue
        loaded.append((src, c, m))
    if not loaded:  # AIOMetadata down: fall back to AIOStreams' own catalogs
        loaded = [('a', client, manifest)]

    if _search_cats():
        _add(kodi.build_url(action='search'), items.folder_item('[B]%s[/B]' % kodi.s(30021), icon=items.icon('search')))
    group = kodi.setting_bool('group_by_type')
    for src, c, m in loaded:
        if len(loaded) > 1:
            _add(kodi.build_url(action='noop'),
                 items.folder_item('[COLOR grey]-- %s --[/COLOR]' % (m.get('name') or src),
                                  icon=items.icon('metadata' if src == 'm' else 'server')), folder=False)
        types_seen = []
        for cat in c.catalogs():
            search = _extra(cat, 'search')
            if search and search.get('isRequired'):
                continue  # search-only catalog
            if group:
                if cat.get('type') not in types_seen:
                    types_seen.append(cat.get('type'))
                continue
            _add_catalog_entry(cat, src)
        for t in types_seen:
            _add(kodi.build_url(action='type', type=t, src=src), items.folder_item(items.type_label(t), icon=items.type_icon(t)))

    _add(kodi.build_url(action='play_id'), items.folder_item(kodi.s(30022), icon=items.icon('play_id')), folder=True)
    _add(kodi.build_url(action='tools'), items.folder_item(kodi.s(30023), icon=items.icon('tools')))
    xbmcplugin.setPluginCategory(kodi.HANDLE, manifest.get('name') or kodi.ADDON_NAME)
    _end(cache=False)


def _add_catalog_entry(cat, src='a', with_type=True):
    label = cat.get('name') or cat.get('id')
    if with_type:
        label = '%s [COLOR grey](%s)[/COLOR]' % (label, items.type_label(cat.get('type')))
    genre = _extra(cat, 'genre')
    url_kw = dict(action='catalog', type=cat.get('type'), cid=cat.get('id'), src=src)
    if genre and genre.get('isRequired'):
        url_kw['action'] = 'genres'
    url = kodi.build_url(**url_kw)
    li = items.folder_item(label, icon=items.catalog_icon(cat))
    li.addContextMenuItems([(kodi.s(30082), 'RunPlugin(%s)' % kodi.build_url(action='widget_path', path=url))])
    _add(url, li)


def by_type(params):
    src = _src(params)
    client = _cat_client(src)
    for cat in client.catalogs():
        search = _extra(cat, 'search')
        if cat.get('type') == params['type'] and not (search and search.get('isRequired')):
            _add_catalog_entry(cat, src, with_type=False)
    _end()


def genres(params):
    src = _src(params)
    client = _cat_client(src)
    cat = client.find_catalog(params['type'], params['cid'])
    ex = _extra(cat or {}, 'genre') or {}
    for g in ex.get('options') or []:
        _add(kodi.build_url(action='catalog', type=params['type'], cid=params['cid'], genre=g, src=src),
             items.folder_item(g, icon=items.icon('genres')))
    _end()


def catalog(params):
    src = _src(params)
    client = _cat_client(src)
    type_, cid = params['type'], params['cid']
    skip = int(params.get('skip') or 0)
    cat = client.find_catalog(type_, cid) or {}
    extras = []
    if params.get('search'):
        extras.append(('search', params['search']))
    if params.get('genre'):
        extras.append(('genre', params['genre']))
    if skip:
        extras.append(('skip', skip))

    genre_ex = _extra(cat, 'genre')
    if not skip and not params.get('genre') and not params.get('search') and genre_ex and genre_ex.get('options'):
        _add(kodi.build_url(action='genres', type=type_, cid=cid, src=src),
             items.folder_item('[B]%s[/B]' % kodi.s(30024), icon=items.icon('genres')))

    with kodi.Busy():
        metas, errors = client.catalog(type_, cid, extras)
    for err in errors:
        kodi.notify(st.clean(err.get('description') or err.get('name') or ''), kodi.s(30103))

    _list_metas(metas, type_, src)

    if metas and _extra(cat, 'skip') and not params.get('search'):
        nxt = dict(params, skip=skip + len(metas), src=src)
        nxt['action'] = 'catalog'
        page = (skip // max(len(metas), 1)) + 2
        _add(kodi.build_url(**nxt), items.folder_item('[B]%s[/B]' % (kodi.s(30025) % page), icon=items.icon('next')))
    _end('movies' if type_ == 'movie' else 'tvshows', sort=False)


def _list_metas(metas, default_type, src='a'):
    for meta in metas:
        mtype = meta.get('type') or default_type
        mid = meta.get('id')
        if not mid:
            continue
        name = meta.get('name') or mid
        if mtype == 'movie':
            url = kodi.build_url(action=_movie_action(), type=mtype, id=mid, title=name, src=src)
            li = items.meta_item(meta, mtype, playable=_movie_action() == 'play', path=url)
            li.addContextMenuItems(_context_for_meta(mtype, mid, name, src))
            _add(url, li, folder=_movie_action() != 'play')
        else:
            url = kodi.build_url(action='show', type=mtype, id=mid, src=src)
            li = items.meta_item(meta, mtype)
            li.addContextMenuItems([(kodi.s(30040), 'Container.Update(%s)' % kodi.build_url(
                action='streams', type=mtype, id=mid, title=name, src=src))])
            _add(url, li)


def _movie_action():
    # 0 = select dialog, 1 = stream directory, 2 = autoplay first
    return 'streams' if kodi.setting_int('stream_select', 0) == 1 else 'play'


# --------------------------------------------------------------------------
# series
# --------------------------------------------------------------------------

def _videos(meta):
    vids = [v for v in meta.get('videos') or [] if v.get('id')]
    return vids


def show(params):
    src = _src(params)
    client = _cat_client(src)
    type_, mid = params['type'], params['id']
    try:
        with kodi.Busy():
            meta = client.meta(type_, mid)
    except ApiError as e:
        if src != 'm':
            return _fail(e)
        kodi.log('AIOMetadata meta failed for %s, using AIOStreams: %s' % (mid, e))
        meta = None
    if not meta and src == 'm':
        src, client = 'a', AIOStreams()
        try:
            with kodi.Busy():
                meta = client.meta(type_, mid)
        except ApiError as e:
            return _fail(e)
    if not meta:
        return _fail(kodi.s(30104))
    vids = _videos(meta)
    if not vids:
        # single video item (e.g. a channel / tv entry without episodes)
        url = kodi.build_url(action='play', type=type_, id=mid, title=meta.get('name'), src=src)
        li = items.meta_item(meta, type_, playable=True, path=url)
        li.setLabel('[B]%s[/B] %s' % (kodi.s(30042), meta.get('name') or ''))
        _add(url, li, folder=False)
        return _end('videos')
    seasons = sorted({v.get('season') for v in vids if v.get('season') is not None},
                     key=lambda x: (x == 0, x))
    if params.get('season') is not None or len(seasons) <= 1 or kodi.setting_bool('flatten_seasons'):
        season = params.get('season')
        return _episodes(client, meta, type_, vids, int(season) if season is not None else None, src)
    for se in seasons:
        label = kodi.s(30030) if se == 0 else kodi.s(30031) % se
        li = items.meta_item(meta, type_, label=label)
        li.getVideoInfoTag().setMediaType('season')
        li.getVideoInfoTag().setSeason(int(se))
        count = sum(1 for v in vids if v.get('season') == se)
        li.setProperty('TotalEpisodes', str(count))
        _add(kodi.build_url(action='show', type=type_, id=mid, season=se, src=src), li)
    xbmcplugin.setPluginCategory(kodi.HANDLE, meta.get('name') or '')
    _end('seasons')


def _episodes(client, meta, type_, vids, season, src='a'):
    if season is not None:
        vids = [v for v in vids if v.get('season') == season]
    vids = sorted(vids, key=lambda v: (v.get('season') or 0, v.get('episode') or v.get('number') or 0))
    hide_future = kodi.setting_bool('hide_unaired')
    import datetime
    today = datetime.date.today().isoformat()
    for v in vids:
        rel = str(v.get('released') or '')[:10]
        if hide_future and rel and rel > today:
            continue
        url = kodi.build_url(action='play' if kodi.setting_int('stream_select', 0) != 1 else 'streams',
                             type=type_, id=v['id'], title=meta.get('name'), src=src)
        li = items.episode_item(meta, v, type_, url)
        li.addContextMenuItems([(kodi.s(30040), 'Container.Update(%s)' % kodi.build_url(
            action='streams', type=type_, id=v['id'], title=meta.get('name'), src=src))])
        _add(url, li, folder=kodi.setting_int('stream_select', 0) == 1)
    xbmcplugin.setPluginCategory(kodi.HANDLE, meta.get('name') or '')
    _end('episodes')


# --------------------------------------------------------------------------
# streams / playback
# --------------------------------------------------------------------------

def _fetch_streams(client, type_, vid):
    with kodi.Busy():
        raw = client.streams(type_, vid)
    playable, notices = st.filter_streams(raw)
    return playable, notices


def _notice_text(notices):
    out = []
    for n in notices:
        out.append('%s: %s' % (st.clean(n.get('name')), st.clean(n.get('description'))))
    return '\n'.join(out)


def streams_dir(params):
    """List streams as a directory of playable items."""
    client = _client()
    type_, vid = params['type'], _stream_id(params)
    try:
        playable, notices = _fetch_streams(client, type_, vid)
    except ApiError as e:
        return _fail(e)
    _save_json(LAST_STREAMS, {'type': type_, 'id': vid, 'title': params.get('title'), 'streams': playable})
    if not playable:
        kodi.notify(kodi.s(30105))
    show_notices = not kodi.setting_bool('hide_notices')
    if show_notices:
        for n in notices:
            li = items.folder_item('[COLOR grey]%s[/COLOR]' % st.clean(n.get('name')).replace('\n', ' '),
                                   icon=items.icon('info'), plot=st.clean(n.get('description')))
            _add(kodi.build_url(action='noop'), li, folder=False)
    for i, stream in enumerate(playable):
        label, label2, plot = st.labels(stream)
        li = xbmcgui.ListItem(label, label2, offscreen=True)
        tag = li.getVideoInfoTag()
        tag.setTitle(params.get('title') or label)
        tag.setPlot(plot)
        tag.setMediaType('video')
        li.setArt({'icon': items.icon('stream'), 'thumb': items.icon('stream'), 'fanart': kodi.FANART})
        li.setProperty('IsPlayable', 'true')
        _add(kodi.build_url(action='play_index', idx=i), li, folder=False)
    xbmcplugin.setPluginCategory(kodi.HANDLE, params.get('title') or '')
    _end('videos', cache=False)


def _choose(playable, notices, title, auto):
    if not playable:
        msg = kodi.s(30105)
        if notices:
            msg += '\n\n' + _notice_text(notices)
        kodi.ok(msg, title)
        return None
    if auto or kodi.setting_int('stream_select', 0) == 2:
        return 0
    lis = []
    for stream in playable:
        label, label2, _ = st.labels(stream)
        li = xbmcgui.ListItem(label, label2, offscreen=True)
        li.setArt({'icon': items.icon('stream'), 'thumb': items.icon('stream')})
        lis.append(li)
    heading = '%s - %s' % (title, kodi.s(30043) % len(playable)) if title else kodi.s(30043) % len(playable)
    idx = xbmcgui.Dialog().select(heading, lis, useDetails=True)
    return idx if idx >= 0 else None


def play(params):
    """Resolve a movie/episode id: fetch streams, choose, resolve."""
    client = _client()
    type_, vid = params['type'], _stream_id(params)
    title = params.get('title') or ''
    try:
        playable, notices = _fetch_streams(client, type_, vid)
    except ApiError as e:
        return _resolve_fail(e)
    idx = _choose(playable, notices, title, params.get('auto') == '1')
    if idx is None:
        return _resolve_fail(None)
    _resolve(client, playable[idx], type_, vid, title, direct=params.get('direct') == '1')


def play_index(params):
    data = _load_json(LAST_STREAMS, {})
    try:
        stream = data['streams'][int(params['idx'])]
    except (KeyError, IndexError, ValueError):
        return _resolve_fail(kodi.s(30106))
    _resolve(_client(), stream, data.get('type'), data.get('id'), data.get('title') or '')


def _resolve_fail(err):
    if err:
        kodi.log('resolve failed: %s' % err, xbmc.LOGERROR)
        kodi.notify(str(err)[:200], kodi.s(30103))
    if kodi.HANDLE >= 0:
        xbmcplugin.setResolvedUrl(kodi.HANDLE, False, xbmcgui.ListItem(offscreen=True))


def _resolve(client, stream, type_, vid, title, direct=False):
    path = st.play_path(stream)
    if not path:
        return _resolve_fail(kodi.s(30107))
    label, _, plot = st.labels(stream)
    li = xbmcgui.ListItem(title or label, path=path, offscreen=True)
    tag = li.getVideoInfoTag()
    tag.setTitle(title or label)
    tag.setPlot(plot)
    hints = stream.get('behaviorHints') or {}
    sd = stream.get('streamData') or {}
    filename = hints.get('filename') or sd.get('filename')
    if filename:
        li.setProperty('original_filename', filename)
    if st.stream_kind(stream) == 'url':
        li.setContentLookup(False)
        mime = _mime(filename or stream.get('url', ''))
        if mime:
            li.setMimeType(mime)
        subs = st.collect_subtitles(stream, client, type_, vid)
        if subs:
            li.setSubtitles(subs)
    kodi.log('playing %s via %s' % (vid, path.split('|')[0][:120]))
    if direct or kodi.HANDLE < 0:
        xbmc.Player().play(path, li)
    else:
        xbmcplugin.setResolvedUrl(kodi.HANDLE, True, li)


def _mime(name):
    name = (name or '').lower().split('?')[0]
    for ext, mime in (('.mkv', 'video/x-matroska'), ('.mp4', 'video/mp4'), ('.m3u8', 'application/vnd.apple.mpegurl'),
                      ('.ts', 'video/mp2t'), ('.avi', 'video/x-msvideo'), ('.webm', 'video/webm')):
        if name.endswith(ext):
            return mime
    return None


# --------------------------------------------------------------------------
# search
# --------------------------------------------------------------------------

def search(params):
    history = _load_json(HISTORY_FILE, [])
    _add(kodi.build_url(action='search_new'), items.folder_item('[B]%s[/B]' % kodi.s(30026), icon=items.icon('search_new')))
    for q in history:
        li = items.folder_item(q, icon=items.icon('history'))
        li.addContextMenuItems([(kodi.s(30044), 'RunPlugin(%s)' % kodi.build_url(action='search_del', q=q))])
        _add(kodi.build_url(action='search_query', q=q), li)
    _end(cache=False)


def search_new(params):
    q = xbmcgui.Dialog().input(kodi.s(30021))
    if not q:
        return _end(cache=False)
    history = [h for h in _load_json(HISTORY_FILE, []) if h != q]
    history.insert(0, q)
    _save_json(HISTORY_FILE, history[:30])
    search_query({'q': q})


def search_del(params):
    history = [h for h in _load_json(HISTORY_FILE, []) if h != params.get('q')]
    _save_json(HISTORY_FILE, history)
    xbmc.executebuiltin('Container.Refresh')


def search_query(params):
    q = params['q']
    cats = _search_cats()
    if len(cats) == 1:
        src, cat = cats[0]
        return catalog({'type': cat['type'], 'cid': cat['id'], 'search': q, 'src': src})
    for src, cat in cats:
        label = '%s [COLOR grey](%s)[/COLOR]' % (cat.get('name') or cat.get('id'), items.type_label(cat.get('type')))
        _add(kodi.build_url(action='catalog', type=cat['type'], cid=cat['id'], search=q, src=src), items.folder_item(label, icon=items.catalog_icon(cat)))
    xbmcplugin.setPluginCategory(kodi.HANDLE, q)
    _end()


# --------------------------------------------------------------------------
# play by id
# --------------------------------------------------------------------------

def play_id(params):
    _add(kodi.build_url(action='play_id_input', type='movie'), items.folder_item(kodi.s(30028), icon=items.icon('movie')))
    _add(kodi.build_url(action='play_id_input', type='series'), items.folder_item(kodi.s(30029), icon=items.icon('series')))
    _end(cache=False)


def play_id_input(params):
    type_ = params['type']
    hint = 'tt0111161' if type_ == 'movie' else 'tt0944947:1:1'
    vid = xbmcgui.Dialog().input('%s  (%s)' % (kodi.s(30022), hint))
    if not vid:
        return _end(cache=False)
    vid = vid.strip()
    if type_ == 'series' and vid.count(':') < 2 and not vid.startswith(('kitsu', 'mal', 'anilist', 'anidb')):
        return show({'type': type_, 'id': vid, 'src': 'm' if _meta_configured() else 'a'})
    return streams_dir({'type': type_, 'id': vid, 'title': vid})


# --------------------------------------------------------------------------
# tools
# --------------------------------------------------------------------------

def tools(params):
    entries = [
        (30020, 'set_manifest', 'manifest'), (30050, 'test', 'test'),
        (30080, 'set_meta', 'metadata'), (30081, 'test_meta', 'test'),
        (30051, 'clear_cache', 'clear_cache'),
        (30052, 'install_tmdbh', 'tmdbh'), (30027, 'settings', 'settings'),
    ]
    for sid, action, ic in entries:
        _add(kodi.build_url(action=action), items.folder_item(kodi.s(sid), icon=items.icon(ic)), folder=False)
    _end(cache=False)


def set_manifest(params):
    current = kodi.setting('manifest_url')
    url = xbmcgui.Dialog().input(kodi.s(30060), defaultt=current)
    if not url:
        return
    try:
        base, query = normalise_manifest_url(url)
    except ApiError as e:
        return kodi.ok(str(e))
    full = base + '/manifest.json' + ('?' + query if query else '')
    kodi.set_setting('manifest_url', full)
    cache_clear()
    test({'manifest': full})
    xbmc.executebuiltin('Container.Refresh')


def set_meta(params):
    url = xbmcgui.Dialog().input(kodi.s(30083), defaultt=kodi.setting('meta_url'))
    if not url:
        if kodi.setting('meta_url') and xbmcgui.Dialog().yesno(kodi.ADDON_NAME, kodi.s(30086)):
            kodi.set_setting('meta_url', '')
            kodi.notify(kodi.s(30085))
            xbmc.executebuiltin('Container.Refresh')
        return
    try:
        base, query = normalise_manifest_url(url)
    except ApiError as e:
        return kodi.ok(str(e))
    full = base + '/manifest.json' + ('?' + query if query else '')
    kodi.set_setting('meta_url', full)
    cache_clear()
    test({'manifest': full, 'meta': '1'})
    xbmc.executebuiltin('Container.Refresh')


def test_meta(params):
    if not _meta_configured():
        return set_meta(params)
    test({'meta': '1'})


def widget_path(params):
    xbmcgui.Dialog().textviewer(kodi.s(30084), params.get('path', ''))


def test(params):
    try:
        cls = AIOMetadata if params.get('meta') == '1' else AIOStreams
        client = cls(params.get('manifest'))
        with kodi.Busy():
            m = client.manifest(force=True)
        cats = len(client.catalogs())
        kodi.ok(kodi.s(30061) % (m.get('name', '?'), m.get('version', '?'), cats))
    except ApiError as e:
        kodi.ok('%s\n%s' % (kodi.s(30103), e))


def clear_cache_action(params):
    n = cache_clear()
    kodi.notify(kodi.s(30062) % n)


def install_tmdbh(params):
    from . import tmdbh
    tmdbh.install()


def settings(params):
    kodi.ADDON.openSettings()


def noop(params):
    pass


ROUTES = {
    None: root, 'root': root, 'type': by_type, 'genres': genres, 'catalog': catalog,
    'show': show, 'streams': streams_dir, 'play': play, 'play_index': play_index,
    'search': search, 'search_new': search_new, 'search_query': search_query, 'search_del': search_del,
    'play_id': play_id, 'play_id_input': play_id_input, 'tools': tools,
    'set_manifest': set_manifest, 'test': test, 'clear_cache': clear_cache_action,
    'install_tmdbh': install_tmdbh, 'settings': settings, 'noop': noop,
    'set_meta': set_meta, 'test_meta': test_meta, 'widget_path': widget_path,
}


def run(argv=None):
    argv = argv or sys.argv
    params = dict(parse_qsl(argv[2][1:])) if len(argv) > 2 and argv[2] else {}
    action = params.get('action')
    handler = ROUTES.get(action)
    if handler is None:
        kodi.log('unknown action %s' % action, xbmc.LOGWARNING)
        return
    try:
        handler(params)
    except ApiError as e:
        if action in ('play', 'play_index'):
            _resolve_fail(e)
        else:
            _fail(e)
