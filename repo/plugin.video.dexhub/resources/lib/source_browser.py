# -*- coding: utf-8 -*-
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui

from . import cache_store
from . import tmdbhelper as _tmdb_art_db
from . import tmdb_direct as _tmdb_direct
from .i18n import tr

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')

ACTION_SELECT = {7, 100}
ACTION_INFO = {11}
ACTION_BACK = {9, 10, 92, 216, 247, 257, 275, 61467, 61448}
ACTION_CONTEXT = {117}
ACTION_LEFT = {1}
ACTION_RIGHT = {2}
ACTION_MOVE = {3, 4}

MODE_ASK = 'ask'
MODE_PLAY = 'play'
MODE_PLAY_SUBS = 'play_with_subtitles'

QUALITY_FILTERS = [
    ('Q:2160P', 'QUALITY • 4K / 2160P', ('2160P', '2160', '4K', 'UHD')),
    ('Q:1080P', 'QUALITY • 1080P', ('1080P', '1080', 'FHD')),
    ('Q:720P',  'QUALITY • 720P',  ('720P', '720', 'HD')),
    ('Q:480P',  'QUALITY • 480P / SD', ('480P', '480', 'SD')),
    ('Q:HDR',   'QUALITY • HDR', ('HDR', 'HDR10', 'HDR10+')),
    ('Q:DV',    'QUALITY • Dolby Vision', ('DV', 'DOVI', 'DOLBY VISION')),
    ('Q:REMUX', 'QUALITY • REMUX', ('REMUX', 'BDREMUX')),
]


def _row_quality_blob(row):
    bits = []
    for key in ('quality', 'highlight', 'badges', 'video_bits', 'audio_bits', 'extraInfo', 'extraInfo2', 'name', 'label2', 'formatter_summary', 'source_info'):
        value = (row or {}).get(key)
        if isinstance(value, (list, tuple)):
            bits.extend([str(v) for v in value if v])
        elif value:
            bits.append(str(value))
    return ' '.join(bits).upper()


def _quality_filter_label(value):
    for key, label, _tokens in QUALITY_FILTERS:
        if key == value:
            return tr(label)
    return tr(value or '')


def _filter_label(value):
    value = str(value or 'ALL')
    if value == 'ALL':
        return tr('ALL RESULTS')
    if value.startswith('Q:'):
        return _quality_filter_label(value)
    if value.startswith('P:'):
        return tr('PROVIDER • %s') % value[2:]
    return tr(value)


def _row_matches_quality(row, filter_value):
    blob = _row_quality_blob(row)
    for key, _label, tokens in QUALITY_FILTERS:
        if key != filter_value:
            continue
        if key == 'Q:720P':
            return any(t in blob for t in tokens) and '1080' not in blob and '2160' not in blob and '4K' not in blob
        if key == 'Q:480P':
            return any(t in blob for t in tokens) and '720' not in blob and '1080' not in blob and '2160' not in blob and '4K' not in blob
        return any(t in blob for t in tokens)
    return False


def _row_provider_filter(row):
    provider = str((row or {}).get('addon') or (row or {}).get('source_site') or (row or {}).get('provider') or '').strip().upper()
    return ('P:%s' % provider) if provider else ''


def _looks_arabic_text(value):
    text = str(value or '').strip()
    if not text:
        return False
    for ch in text:
        o = ord(ch)
        if 0x0600 <= o <= 0x06FF or 0x0750 <= o <= 0x077F or 0x08A0 <= o <= 0x08FF:
            return True
    return False


def _source_meta_backfill(meta):
    meta = dict(meta or {})
    # Fast path: if meta already has poster + fanart + clearlogo + title,
    # skip the TMDb Helper DB / direct-API lookups entirely. The caller
    # (_show_stream_window) populates these from the live UI state, so
    # they're usually all set by the time we get here. Saves a disk +
    # net hit on the critical sources-window open path.
    if meta.get('poster') and meta.get('fanart') and meta.get('clearlogo') and meta.get('title'):
        return meta
    tmdb_id = str(meta.get('tmdb_id') or '').strip()
    imdb_id = str(meta.get('imdb_id') or '').strip()
    media_type = str(meta.get('media_type') or meta.get('type') or 'movie').strip().lower()
    if media_type in ('show', 'tv', 'anime', 'series', 'tvshow'):
        media_type = 'series'
    title = str(meta.get('originaltitle') or meta.get('title') or meta.get('name') or '').strip()
    year = str(meta.get('year') or '').strip()
    if not (tmdb_id or imdb_id or title):
        return meta

    # User preference for source browser / wait screen / player:
    #   1) Prefer TMDb Helper poster + clearlogo when available
    #   2) Fall back to the original source/XML artwork otherwise
    source_poster = meta.get('poster') or ''
    source_fanart = meta.get('fanart') or meta.get('background') or source_poster or ''
    source_clearlogo = meta.get('clearlogo') or meta.get('logo') or ''

    bundle = {}
    try:
        bundle = _tmdb_art_db.get_art_bundle_from_db(
            tmdb_id=tmdb_id,
            media_type=media_type,
            imdb_id=imdb_id,
            title=title,
            year=year,
        ) or {}
    except Exception:
        bundle = {}

    direct = {}
    if not (bundle.get('poster') and bundle.get('clearlogo')):
        try:
            direct = _tmdb_direct.art_for(
                tmdb_id=tmdb_id,
                imdb_id=imdb_id,
                media_type=media_type,
                title=title,
                year=year,
            ) or {}
        except Exception:
            direct = {}

    tmdb_poster = bundle.get('poster') or direct.get('poster') or ''
    tmdb_clearlogo = bundle.get('clearlogo') or direct.get('clearlogo') or ''
    tmdb_fanart = bundle.get('fanart') or bundle.get('landscape') or direct.get('fanart') or direct.get('landscape') or ''

    if tmdb_poster:
        meta['poster'] = tmdb_poster
    elif source_poster:
        meta['poster'] = source_poster

    # Keep existing/source fanart when present; otherwise fill from TMDb.
    if source_fanart:
        meta['fanart'] = source_fanart
        meta['background'] = source_fanart
    elif tmdb_fanart:
        meta['fanart'] = tmdb_fanart
        meta['background'] = tmdb_fanart

    if tmdb_clearlogo:
        meta['clearlogo'] = tmdb_clearlogo
        meta['logo'] = tmdb_clearlogo
    elif source_clearlogo:
        meta['clearlogo'] = source_clearlogo
        meta['logo'] = source_clearlogo

    try:
        db_title = _tmdb_art_db.get_title_from_db(tmdb_id=tmdb_id, media_type=media_type, imdb_id=imdb_id, title=title, year=year) or ''
    except Exception:
        db_title = ''
    current_title = str(meta.get('title') or '').strip()
    if db_title and (not current_title or _looks_arabic_text(current_title)):
        meta['title'] = db_title

    if not meta.get('fanart') and meta.get('poster'):
        meta['fanart'] = meta.get('poster')
        meta['background'] = meta.get('poster')
    return meta


def _normalize_mode(value):
    raw = str(value or '').strip().lower()
    if raw in (MODE_PLAY_SUBS, 'play_with_subtitles', 'with_subtitles', 'with-subs', 'تشغيل مع ترجمة', 'play with subtitles'):
        return MODE_PLAY_SUBS
    # Legacy/empty/ask values all become normal playback. Playback mode is now
    # controlled from settings only; no per-click prompt.
    return MODE_PLAY


class SourcesWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.results = kwargs.get('results') or []
        self.meta = kwargs.get('meta') or {}
        self.selected = None
        self.active_filter = 'ALL'
        self.filters = []
        self.play_mode = _normalize_mode(kwargs.get('play_mode') or MODE_ASK)
        self.play_with_subtitles = False
        self.session_key = kwargs.get('session_key') or ''
        self._session_version = 0
        self._poll_stop = threading.Event()
        self._poll_thread = None
        # Double-dialog guard. Once a stream is chosen and the play-mode
        # picker has been shown, ALL further input is ignored. This kills the
        # symptom where a single OK press fired both onAction(SELECT) AND
        # onClick(2000) — the second event used to re-open the picker after
        # the first had already finalized the selection.
        self._closing = False
        self._mode_dialog_open = False
        self._action_guard = {}

    def onInit(self):
        try:
            self.meta = _source_meta_backfill(self.meta)
        except Exception:
            self.meta = dict(self.meta or {})
        # Push every visual property up-front so the XML can use $INFO
        # bindings (poster/fanart/clearlogo/title/plot). Imperative setImage
        # gets clobbered by static <texture> tags in the skin so we don't
        # rely on it as the primary path.
        _fanart = self.meta.get('fanart') or self.meta.get('background') or self.meta.get('poster') or ''
        _clearlogo = self.meta.get('clearlogo') or ''
        _poster = self.meta.get('poster') or self.meta.get('thumb') or _fanart or ''
        _title = self.meta.get('title') or self.meta.get('name') or ''
        plot_raw = self.meta.get('plot') or self.meta.get('description') or ''
        _plot = str(plot_raw)[:600] if plot_raw else ''
        _year = str(self.meta.get('year') or '')
        _rating = str(self.meta.get('rating') or '')
        _genre = str(self.meta.get('genre') or '')
        self.setProperty('fanart', _fanart or '')
        self.setProperty('clearlogo', _clearlogo or '')
        self.setProperty('poster', _poster or _fanart or '')
        self.setProperty('title', _title)
        if _plot:
            self.setProperty('plot', _plot)
        self.setProperty('year', _year)
        self.setProperty('rating', _rating)
        self.setProperty('genre', _genre)
        try:
            home = xbmcgui.Window(10000)
            home.setProperty('dexhub.source.fanart', _fanart)
            home.setProperty('dexhub.source.clearlogo', _clearlogo)
            home.setProperty('dexhub.source.poster', _poster or _fanart or '')
            home.setProperty('dexhub.source.thumb', _poster or _fanart or '')
            home.setProperty('dexhub.source.title', _title)
            home.setProperty('dexhub.source.plot', _plot)
            home.setProperty('dexhub.source.year', _year)
            home.setProperty('dexhub.source.rating', _rating)
            home.setProperty('dexhub.source.genre', _genre)
        except Exception:
            pass
        self.setProperty('filters_visible', 'false')
        # Belt-and-braces: also push the poster image directly. Harmless
        # if the XML uses $INFO; covers skins that only honor setImage.
        try:
            self.getControl(200).setImage(_poster or _fanart or 'special://home/addons/plugin.video.dexhub/resources/media/default_video.png')
        except Exception:
            pass
        self._build_filters()
        self._apply_filter('ALL')
        self._update_play_mode_label()
        self._update_loading_state()
        self._start_session_poll()
        try:
            self.setFocusId(2000)
        except Exception:
            pass

    def _update_loading_state(self):
        label = tr('جار جلب نتائج إضافية...') if self.getProperty('loading_more') == 'true' else ''
        self.setProperty('loading_label', label)

    def _apply_session_payload(self, payload):
        if not isinstance(payload, dict):
            return
        rows = payload.get('entries') or []
        if isinstance(rows, list):
            self.results = rows
        done = bool(payload.get('done'))
        self.setProperty('loading_more', 'false' if done else 'true')
        self._update_loading_state()
        old_active = self.active_filter or 'ALL'
        self._build_filters()
        active = old_active if old_active in set(self.filters or ['ALL']) else 'ALL'
        self._apply_filter(active)

    def _poll_session(self):
        while not self._poll_stop.is_set():
            try:
                payload = cache_store.get('stream_session', self.session_key) or {}
                version = int(payload.get('version') or 0)
                if payload and version != self._session_version:
                    self._session_version = version
                    self._apply_session_payload(payload)
                if payload and payload.get('done') and version == self._session_version:
                    self.setProperty('loading_more', 'false')
                    self._update_loading_state()
            except Exception:
                pass
            self._poll_stop.wait(0.5)

    def _start_session_poll(self):
        if not self.session_key:
            self.setProperty('loading_more', 'false')
            return
        try:
            payload = cache_store.get('stream_session', self.session_key) or {}
        except Exception:
            payload = {}
        if payload:
            self._session_version = int(payload.get('version') or 0)
            self._apply_session_payload(payload)
        else:
            self.setProperty('loading_more', 'true')
            self._update_loading_state()
        self._poll_thread = threading.Thread(target=self._poll_session, name='DexHubSourcePoll', daemon=True)
        self._poll_thread.start()

    def _build_filters(self):
        values = ['ALL']
        seen = {'ALL'}
        # Quality filters first so users can quickly narrow by 4K/1080P/HDR/DV.
        for filter_value, _label, _tokens in QUALITY_FILTERS:
            try:
                if any(_row_matches_quality(row, filter_value) for row in self.results if isinstance(row, dict)):
                    seen.add(filter_value)
                    values.append(filter_value)
            except Exception:
                pass
        for row in self.results:
            value = _row_provider_filter(row)
            if value and value not in seen:
                seen.add(value)
                values.append(value)
        self.filters = values
        items = []
        for name in values:
            li = xbmcgui.ListItem(label=_filter_label(name))
            li.setProperty('label', _filter_label(name))
            li.setProperty('filter_value', name)
            items.append(li)
        try:
            control = self.getControl(2100)
            control.reset()
            control.addItems(items)
        except Exception:
            pass

    def _results_for_filter(self, filter_value):
        if not filter_value or filter_value == 'ALL':
            return list(self.results)
        if str(filter_value).startswith('Q:'):
            return [row for row in self.results if _row_matches_quality(row, filter_value)]
        if str(filter_value).startswith('P:'):
            wanted = str(filter_value)[2:]
            return [row for row in self.results if _row_provider_filter(row) == ('P:%s' % wanted)]
        return [row for row in self.results if _row_provider_filter(row) == ('P:%s' % str(filter_value).strip().upper())]

    def _apply_filter(self, filter_value):
        self.active_filter = filter_value or 'ALL'
        visible = self._results_for_filter(self.active_filter)
        loading = self.getProperty('loading_more') == 'true'
        total_label = str(len(visible))
        if loading:
            total_label = '%s +' % total_label
        self.setProperty('total_results', total_label)
        self.setProperty('filter_info', '' if self.active_filter == 'ALL' else u'• %s' % _filter_label(self.active_filter))
        previous_key = ''
        previous_pos = 0
        try:
            control = self.getControl(2000)
            previous_pos = int(control.getSelectedPosition())
            current_item = control.getSelectedItem()
            previous_key = current_item.getProperty('stream_key') if current_item else ''
        except Exception:
            control = None
        items = []
        restore_idx = -1
        for idx, row in enumerate(visible):
            li = xbmcgui.ListItem(label=row.get('name') or '', label2=row.get('label2') or '')
            for key in ('highlight', 'quality', 'provider', 'addon', 'source_site', 'extraInfo', 'extraInfo2', 'size_label', 'count', 'name', 'stream_key', 'badges', 'formatter_summary'):
                li.setProperty(key, str(row.get(key) or ''))
            li.setProperty('video_bits', ' · '.join(row.get('video_bits') or []))
            li.setProperty('audio_bits', ' · '.join(row.get('audio_bits') or []))
            tags = row.get('formatter_tags') or []
            # Native fallback: build tags from video_bits/audio_bits when
            # the formatter preset returns fewer than 2 tags. This ensures
            # HDR / DV / Atmos / 4K badges always show even on first launch
            # before the preset JSON has been fetched.
            if len(tags) < 2:
                vb = row.get('video_bits') or []
                ab = row.get('audio_bits') or []
                # Priority-ordered built-in tag palette.
                _NATIVE_TAGS = [
                    # Resolution
                    ('2160P', 'FF0A1E3C', 'FF33D8F7'), ('4K', 'FF0A1E3C', 'FF33D8F7'),
                    ('1080P', 'FF160A3C', 'FF9B7FFF'), ('720P', 'FF0A1E18', 'FF4AEDA0'),
                    # HDR / DV
                    ('DV',    'FF1C0A3C', 'FFBB86FC'),
                    ('HDR10+','FF3C1E00', 'FFFFB347'), ('HDR10', 'FF2A1600', 'FFFFB347'),
                    ('HDR',   'FF221200', 'FFFFB347'),
                    # Codec
                    ('HEVC', 'FF0A2010', 'FF4CD96C'), ('AV1', 'FF051A10', 'FF2ECC71'),
                    ('H264', 'FF1A2010', 'FF8BC34A'),
                    # Audio
                    ('ATMOS',  'FF1A0C2A', 'FFCF94FF'),
                    ('TRUEHD', 'FF220A30', 'FFBB86FC'),
                    ('DTS-HD', 'FF0C1C3A', 'FF80BFFF'),
                    ('DTS-X',  'FF0C1C3A', 'FF80BFFF'),
                    ('DTS',    'FF0C1C30', 'FF6EA6E0'),
                    ('DD+',    'FF1A1A30', 'FFA0A8FF'),
                    ('DD-EX',  'FF1A1A28', 'FF9090D0'),
                    ('7.1',    'FF181820', 'FFB0B4D0'),
                    ('5.1',    'FF141420', 'FF9698B8'),
                    # Source
                    ('REMUX',   'FF200A0A', 'FFFF6B6B'),
                    ('BLURAY',  'FF0A1020', 'FF6B9EFF'),
                    ('WEB-DL',  'FF0A180A', 'FF6BCC84'),
                    ('WEBDL',   'FF0A180A', 'FF6BCC84'),
                    ('WEBRIP',  'FF0A1804', 'FF9AE06A'),
                    # Other
                    ('DUBBED',  'FF2A2A00', 'FFFFFFA0'),
                    ('MULTI',   'FF001A1A', 'FFA0FFFF'),
                    ('SUBS',    'FF001A1A', 'FF80FFFF'),
                ]
                seen = {t.get('text', '').upper() for t in tags}
                all_bits_up = [b.upper() for b in (vb + ab)]
                for key, bg, fg in _NATIVE_TAGS:
                    if key in all_bits_up and key not in seen:
                        tags = list(tags) + [{'text': key, 'bg': bg, 'fg': fg}]
                        seen.add(key)
                    if len(tags) >= 8:
                        break
            for tag_idx in range(8):
                tag = tags[tag_idx] if tag_idx < len(tags) and isinstance(tags[tag_idx], dict) else {}
                n = tag_idx + 1
                li.setProperty('fmt%d_text' % n, str(tag.get('text') or ''))
                li.setProperty('fmt%d_bg' % n, str(tag.get('bg') or 'FF2B2F3E'))
                li.setProperty('fmt%d_fg' % n, str(tag.get('fg') or 'FFF2F4FB'))
            li.setProperty('source_info', row.get('source_info') or '')
            items.append(li)
            if previous_key and str(row.get('stream_key') or '') == previous_key:
                restore_idx = idx
        try:
            control = control or self.getControl(2000)
            control.reset()
            control.addItems(items)
            if items:
                if restore_idx < 0:
                    restore_idx = min(max(previous_pos, 0), len(items) - 1)
                control.selectItem(restore_idx)
        except Exception:
            pass

    def _guard_action(self, name, interval=0.6):
        # Bumped from 0.35s to 0.6s to give modal dialogs time to fully
        # transfer focus before the next action is allowed.
        now = time.monotonic()
        prev = float(self._action_guard.get(name) or 0.0)
        if (now - prev) < interval:
            return True
        self._action_guard[name] = now
        return False

    def _play_mode_label(self):
        if self.play_mode == MODE_PLAY_SUBS:
            return tr('تشغيل مع ترجمة')
        return tr('تشغيل')

    def _update_play_mode_label(self):
        self.setProperty('play_mode_label', self._play_mode_label())

    def _pick_play_mode(self):
        if self._closing or self._mode_dialog_open:
            return
        self._mode_dialog_open = True
        try:
            options = [
                (tr('تشغيل فقط'), MODE_PLAY),
                (tr('تشغيل مع ترجمة'), MODE_PLAY_SUBS),
            ]
            idx = xbmcgui.Dialog().select(tr('وضع التشغيل'), [label for label, _ in options])
            if idx >= 0:
                self.play_mode = options[idx][1]
                self._update_play_mode_label()
        finally:
            self._mode_dialog_open = False
        try:
            self.setFocusId(2000)
        except Exception:
            pass

    def _resolve_choice_mode(self):
        return self.play_mode

    def _choose(self):
        # Hard guards against the OK-press double-event:
        #   1. window is already closing → drop
        #   2. play-mode dialog is currently up → drop (the in-flight call owns it)
        #   3. selection was already finalized → drop
        if self._closing or self._mode_dialog_open or self.selected:
            return
        try:
            item = self.getControl(2000).getSelectedItem()
        except Exception:
            item = None
        stream_key = item.getProperty('stream_key') if item else None
        if not stream_key:
            return
        chosen_mode = self._resolve_choice_mode()
        if not chosen_mode:
            return
        # Re-check after the modal returns — if something else finalized a
        # selection in the meantime, do not double-fire.
        if self._closing or self.selected:
            return
        self.selected = stream_key
        self.play_with_subtitles = (chosen_mode == MODE_PLAY_SUBS)
        self._closing = True
        self._shutdown()
        self.close()

    def _show_info(self):
        try:
            focus_id = self.getFocusId()
        except Exception:
            focus_id = 2000
        if focus_id == 2100:
            text = tr('Filter: %s') % _filter_label(self.active_filter)
            xbmcgui.Dialog().textviewer('Dex Hub', tr(text))
            return
        try:
            item = self.getControl(2000).getSelectedItem()
        except Exception:
            item = None
        if not item:
            return
        text = item.getProperty('source_info') or item.getProperty('name') or ''
        xbmcgui.Dialog().textviewer('Dex Hub', tr(text))

    def _apply_selected_filter(self):
        try:
            item = self.getControl(2100).getSelectedItem()
        except Exception:
            item = None
        filter_value = item.getProperty('filter_value') if item else 'ALL'
        self._apply_filter(filter_value)
        self.setProperty('filters_visible', 'false')
        try:
            self.setFocusId(2000)
        except Exception:
            pass

    def onClick(self, controlId):
        if self._closing or self._mode_dialog_open:
            return
        if controlId == 2000:
            if not self._guard_action('choose'):
                self._choose()
        elif controlId == 2100:
            if not self._guard_action('filter'):
                self._apply_selected_filter()
        elif controlId == 2200:
            if not self._guard_action('mode'):
                self._pick_play_mode()

    def onAction(self, action):
        if self._closing or self._mode_dialog_open:
            # While the play-mode picker is up (or after a successful pick),
            # ignore every action to prevent stacked dialogs.
            return
        action_id = action.getId()
        try:
            focus_id = self.getFocusId()
        except Exception:
            focus_id = 2000
        if action_id in ACTION_BACK:
            if focus_id == 2100 and self.getProperty('filters_visible') == 'true':
                self.setProperty('filters_visible', 'false')
                try:
                    self.setFocusId(2000)
                except Exception:
                    pass
                return
            self.selected = None
            self._closing = True
            self._shutdown()
            self.close()
            return
        if action_id in ACTION_INFO or action_id in ACTION_CONTEXT:
            self._show_info()
            return
        if focus_id == 2100 and action_id in ACTION_RIGHT:
            if not self._guard_action('filter'):
                self._apply_selected_filter()
            return
        if focus_id == 2100 and action_id in ACTION_SELECT:
            if not self._guard_action('filter'):
                self._apply_selected_filter()
            return
        if focus_id == 2200 and action_id in ACTION_SELECT:
            if not self._guard_action('mode'):
                self._pick_play_mode()
            return
        if focus_id == 2000 and action_id in ACTION_SELECT:
            if not self._guard_action('choose'):
                self._choose()
            return
        if focus_id == 2000 and action_id in ACTION_LEFT and len(self.filters) > 1:
            self.setProperty('filters_visible', 'true')
            xbmc.sleep(20)
            try:
                self.setFocusId(2100)
            except Exception:
                pass
            return

    def _shutdown(self):
        try:
            self._poll_stop.set()
        except Exception:
            pass

    def run(self):
        self.doModal()
        self._shutdown()
        return {
            'stream_key': self.selected,
            'play_with_subtitles': self.play_with_subtitles,
            'play_mode': self.play_mode,
        }


def open_sources_window(results, meta, play_mode=MODE_ASK, session_key=''):
    skin_xml = 'sources_results.xml'
    win = SourcesWindow(skin_xml, ADDON_PATH, 'Default', '1080i', results=results, meta=meta, play_mode=play_mode, session_key=session_key)
    try:
        return win.run()
    finally:
        del win
