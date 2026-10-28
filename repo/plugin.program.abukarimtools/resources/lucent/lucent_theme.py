# -*- coding: utf-8 -*-
# Lucent theme helper - injected by AB Tools (plugin.program.abukarimtools).
# LUCENT_HELPER_VERSION = 4
#
# Normalises each add-on's own source-list and meta properties into one shared
# 'lucent.*' property set, so a single Lucent window layout works for Fen Light,
# Red Light, POV and Umbrella. Everything here is best-effort: any failure is
# swallowed so the add-on's own window always keeps working.
import re

# Property names each add-on already puts on its source list items.
_ITEM_KEYS = {
	'fen': {'name': 'name', 'quality': 'quality', 'provider': 'provider', 'type': 'source_type',
			'size': 'size_label', 'site': 'source_site', 'info': 'extraInfo', 'icon': 'provider_icon'},
	'pov': {'name': 'tikiskins.name', 'quality': 'tikiskins.quality', 'provider': 'tikiskins.provider',
			'type': 'tikiskins.source_type', 'size': 'tikiskins.size_label', 'site': 'tikiskins.source_site',
			'info': 'tikiskins.extra_info', 'icon': 'tikiskins.provider_icon'},
	'umbrella': {'name': 'umbrella.name', 'quality': 'umbrella.quality', 'provider': 'umbrella.debrid',
				'type': 'umbrella.source', 'size': 'umbrella.size_label', 'site': 'umbrella.provider',
				'info': 'umbrella.extra_info', 'icon': ''},
}

# Release tag (as any of the add-ons spell it) -> Lucent badge file name.
_BADGES = {
	'DV': 'DV', 'D/VISION': 'DV', 'DOLBY-VISION': 'DV', 'DOLBY VISION': 'DV', 'DOLBY_VISION': 'DV', 'DOVI': 'DV',
	'HDR': 'HDR', 'HDR10': 'HDR', 'HDR10+': 'HDR', 'HDR10PLUS': 'HDR', 'HDR_TRUE': 'HDR',
	'SDR': 'SDR', 'HYBRID': 'HYBRID',
	'HEVC': 'HEVC', 'H265': 'HEVC', 'H.265': 'HEVC', 'X265': 'HEVC', 'CODEC_H265': 'HEVC',
	'AVC': 'AVC', 'H264': 'AVC', 'H.264': 'AVC', 'X264': 'AVC', 'CODEC_H264': 'AVC',
	'AV1': 'AV1', 'CODEC_AV1': 'AV1', 'VP9': 'VP9', 'XVID': 'XVID', 'DIVX': 'DIVX',
	'MPEG': 'MPEG', 'WMV': 'WMV', 'MP4': 'MP4',
	'3D': '3D', 'VIDEO_3D': '3D',
	'REMUX': 'REMUX', 'BLURAY': 'BLURAY', 'BLU-RAY': 'BLURAY', 'BDRIP': 'BLURAY',
	'WEB': 'WEB', 'WEB-DL': 'WEB', 'WEBDL': 'WEB', 'WEBRIP': 'WEB',
	'HDTV': 'HDTV', 'PDTV': 'PDTV', 'HDRIP': 'HD-RIP', 'HD-RIP': 'HD-RIP', 'DVD': 'DVDRIP', 'DVDRIP': 'DVDRIP',
	'CAM': 'CAM', 'SCR': 'SCR', 'TELE': 'CAM', 'HC': 'HC',
	'ATMOS': 'ATMOS',
	'TRUEHD': 'TRUEHD', 'DOLBY-TRUEHD': 'TRUEHD', 'DOLBY_TRUEHD': 'TRUEHD', 'DOLBY TRUEHD': 'TRUEHD',
	'DTS-X': 'DTS-X', 'DTSX': 'DTS-X', 'DTS:X': 'DTS-X',
	'DTS-HD MA': 'DTS-HDMA', 'DTS-HDMA': 'DTS-HDMA', 'DTS_HDMA': 'DTS-HDMA', 'DTS-HD HR': 'DTS-HDHR', 'DTS-HDHR': 'DTS-HDHR',
	'DTS-HD': 'DTS-HD', 'DTS_HD': 'DTS-HD', 'DTS': 'DTS', 'DTS_PLAIN': 'DTS',
	'DD+': 'DD+', 'DDP': 'DD+', 'EAC3': 'DD+', 'E-AC3': 'DD+', 'DOLBY_DIGITALPLUS': 'DD+', 'DOLBYDIGITALPLUS': 'DD+',
	'DD': 'DD', 'DD-EX': 'DD', 'AC3': 'DD', 'DOLBYDIGITAL': 'DD', 'DOLBY_DIGITALEX': 'DD',
	'AAC': 'AAC', 'MP3': 'MP3', 'OPUS': 'OPUS', 'WMA': 'WMA',
	'8CH': '7.1', '7CH': '7.1', '7.1': '7.1', 'AUDIO_8CH': '7.1', 'AUDIO_7CH': '7.1',
	'6CH': '5.1', '5.1': '5.1', 'AUDIO_6CH': '5.1', '2CH': '2.0', '2.0': '2.0', 'AUDIO_2CH': '2.0',
}
# Display order: release type, picture, codec, audio, channels, extras.
_ORDER = ('CAM', 'SCR', 'HC', 'REMUX', 'BLURAY', 'WEB', 'HDTV', 'PDTV', 'HD-RIP', 'DVDRIP',
		'DV', 'HDR', 'HYBRID', 'SDR', 'HEVC', 'AV1', 'AVC', 'VP9', 'XVID', 'DIVX', 'MPEG', 'WMV', 'MP4',
		'ATMOS', 'TRUEHD', 'DTS-X', 'DTS-HDMA', 'DTS-HDHR', 'DTS-HD', 'DTS', 'DD+', 'DD', 'AAC', 'OPUS', 'MP3', 'WMA',
		'7.1', '5.1', '2.0', '3D')
_RANK = {b: n for n, b in enumerate(_ORDER)}
# Within a family only the best badge is kept (DTS-X beats DTS-HD beats DTS ...).
_FAMILY = {'DTS-X': 'dts', 'DTS-HDMA': 'dts', 'DTS-HDHR': 'dts', 'DTS-HD': 'dts', 'DTS': 'dts',
		'DD+': 'dd', 'DD': 'dd', '7.1': 'ch', '5.1': 'ch', '2.0': 'ch',
		'REMUX': 'src', 'BLURAY': 'src', 'WEB': 'src', 'HDTV': 'src', 'PDTV': 'src', 'HD-RIP': 'src', 'DVDRIP': 'src'}
_MAX_BADGES = 7
_LOWQ = ('CAM', 'SCR', 'TELE', 'HC')
_TAG_RE = re.compile(r'\[/?(?:B|I|UPPERCASE|LOWERCASE|CAPITALIZE|COLOR[^\]]*)\]', re.I)
_SPLIT_RE = re.compile(r'\s*[|/]\s*')


def _clean(text):
	try: return _TAG_RE.sub('', str(text or '')).strip()
	except Exception: return ''


def badges(info, quality=''):
	"""Ordered list of Lucent badge names for an info string."""
	found = []
	text = _clean(info).upper().replace('D/VISION', 'DV')
	for token in _SPLIT_RE.split(text):
		token = token.strip()
		if not token: continue
		badge = _BADGES.get(token)
		if badge is None: badge = _BADGES.get(token.replace(' ', '-'))
		if badge is None and token.endswith(' PACK'): continue
		if badge and badge not in found: found.append(badge)
	q = _clean(quality).upper()
	if q in ('CAM', 'SCR', 'TELE') and _BADGES[q] not in found: found.append(_BADGES[q])
	found.sort(key=lambda b: _RANK.get(b, 999))
	seen_family, result = set(), []
	for b in found:
		fam = _FAMILY.get(b)
		if fam:
			if fam in seen_family: continue
			seen_family.add(fam)
		result.append(b)
	return result[:_MAX_BADGES]


# Approximate advance widths (px at 1080p) of a skin's font12. Text is fitted in
# Python because Kodi trims an overflowing label from the START when the GUI
# language is right-to-left (Arabic), which hid the first characters.
_TITLE_PX, _META_PX = 690, 690


def _px(text):
	w = 0.0
	for ch in text:
		if ch in ' .,:;|\'!': w += 7
		elif ch in '-_()[]/': w += 10
		elif ch.isdigit(): w += 15.5
		elif ch.isupper(): w += 17
		elif ch == '·': w += 8
		else: w += 13.5
	return w


def _fit(text, limit):
	if _px(text) <= limit: return text
	while text and _px(text + '…') > limit: text = text[:-1]
	return text.rstrip(' .-_') + '…'


# Resolution flag (Arctic Fuse 3 media/flags/color/resolution) per quality.
_RES = {'8K': '8k', '4K': '4k', '2160P': '4k', 'UHD': '4k', '1080P': '1080', '1080': '1080', 'FHD': '1080',
		'720P': '720', '720': '720', 'HD': '720', 'SD': '480', '480P': '480', '576P': '480'}
# Debrid / service icon (AB Wizard account manager artwork) per provider name.
_PROVIDERS = (('realdebrid', ('REAL-DEBRID', 'REALDEBRID', 'RD', 'RD_CLOUD', 'RD CLOUD')),
			('alldebrid', ('ALLDEBRID', 'AD', 'AD_CLOUD', 'AD CLOUD')),
			('premiumize', ('PREMIUMIZE', 'PREMIUMIZE.ME', 'PM', 'PM_CLOUD', 'PM CLOUD')),
			('torbox', ('TORBOX', 'TB', 'TB_CLOUD', 'TB CLOUD')),
			('offcloud', ('OFFCLOUD', 'OC', 'OC_CLOUD', 'OC CLOUD')),
			('easydebrid', ('EASYDEBRID', 'ED')),
			('easynews', ('EASYNEWS', 'EN')))
_PROVIDER_OF = {alias: icon for icon, aliases in _PROVIDERS for alias in aliases}


def _provider_icon(*names):
	for name in names:
		key = _clean(name).upper().strip()
		if key in _PROVIDER_OF: return 'lucent/providers/%s.png' % _PROVIDER_OF[key]
		for alias, icon in _PROVIDER_OF.items():
			if len(alias) > 3 and alias in key: return 'lucent/providers/%s.png' % icon
	return ''


def lucent_item(listitem, profile):
	"""Add lucent.* properties to one source list item (reads the add-on's own ones)."""
	try:
		keys = _ITEM_KEYS[profile]
		get = listitem.getProperty
		name = _clean(get(keys['name']))
		quality = _clean(get(keys['quality'])).upper()
		provider = _clean(get(keys['provider']))
		source_type = _clean(get(keys['type']))
		size = _clean(get(keys['size']))
		site = _clean(get(keys['site']))
		meta = []
		for part in (provider, source_type, size, site):
			if not part or part.upper() in ('N/A', 'NA', 'NONE'): continue
			if any(part.upper() in m.upper() or m.upper() in part.upper() for m in meta): continue
			meta.append(part)
		while len(meta) > 1 and _px('  ·  '.join(meta).upper()) > _META_PX: meta.pop()
		props = {'lucent.title': _fit(name, _TITLE_PX), 'lucent.quality': quality or 'SD',
				'lucent.meta': _fit('  ·  '.join(meta), _META_PX),
				'lucent.lowq': 'true' if quality in _LOWQ else '',
				'lucent.uncached': 'true' if 'UNCACHED' in source_type.upper() else '',
				'lucent.res': '' if quality in _LOWQ else _RES.get(quality, ''),
				'lucent.icon': _provider_icon(provider, site)}
		found = badges(get(keys['info']), quality)
		for n in range(_MAX_BADGES):
			props['lucent.badge_%d' % (n + 1)] = found[n] if n < len(found) else ''
		listitem.setProperties(props)
	except Exception:
		pass


def _num(value):
	try: return int(value)
	except Exception: return None


def _from_focused_item(meta):
	"""Logo / rating / MPAA / genre of the focused Kodi item - only when its
	TMDb or IMDb id is the one being played (Umbrella started from TMDbHelper
	gets a slim meta without them)."""
	try:
		import xbmc
		info = xbmc.getInfoLabel
		ids = set()
		for k in ('tmdb', 'tmdb_id', 'imdb', 'imdb_id', 'imdbnumber'):
			v = str(meta.get(k) or '').strip()
			if v and v not in ('0', 'None'): ids.add(v)
		if not ids: return {}
		seen = {info(i).strip() for i in ('ListItem.UniqueID(tmdb)', 'ListItem.UniqueID(imdb)', 'ListItem.IMDBNumber',
				'ListItem.UniqueID(tvshow.tmdb)', 'ListItem.Property(tvshow.tmdb_id)', 'ListItem.Property(tmdb_id)')}
		if not ids & (seen - {''}): return {}
		return {'clearlogo': info('ListItem.Art(clearlogo)') or info('ListItem.Art(tvshow.clearlogo)'),
				'rating': info('ListItem.Rating'), 'mpaa': info('ListItem.Mpaa'), 'genre': info('ListItem.Genre').replace(' / ', ', '),
				'year': info('ListItem.Year'), 'fanart': info('ListItem.Art(fanart)')}
	except Exception:
		return {}


_COUNTS_RE = re.compile(r'4K:\s*(\d+)\s*\|\s*1080p:\s*(\d+)\s*\|\s*720p:\s*(\d+)\s*\|\s*SD:\s*(\d+)(?:\s*\|\s*Total:\s*(\d+))?', re.I)


def lucent_progress(window, content, percent=0):
	"""Umbrella / POV progress: pull the 4K/1080p/720p/SD counts out of the text
	into lucent.c_* properties (shown as tiles) and return the rest of the text."""
	try:
		text = str(content or '')
		lines = re.split(r'\[CR\]|\n', text)
		totals, kept, found = [0, 0, 0, 0], [], False
		for line in lines:
			m = _COUNTS_RE.search(_clean(line))
			if m:
				found = True
				for n in range(4): totals[n] += int(m.group(n + 1))
			else:
				kept.append(line)
		if found: window._lucent_counts_seen = True
		seen = getattr(window, '_lucent_counts_seen', False)
		window.setProperty('lucent.counts', 'true' if found else '')
		if found:
			for key, value in zip(('c_4k', 'c_1080p', 'c_720p', 'c_sd'), totals):
				window.setProperty('lucent.' + key, str(value))
			window.setProperty('lucent.c_total', str(sum(totals)))
		window.setProperty('lucent.heading', 'Searching for streams' if found else ('Opening stream' if seen else ''))
		try: window.setProperty('lucent.percent', str(int(float(percent))))
		except Exception: pass
		if not found: return content
		while kept and not _clean(kept[0]): kept.pop(0)
		return '[CR]'.join(kept)
	except Exception:
		return content


def lucent_window(window, meta, fanart='', clearlogo=None):
	"""Add lucent.* title/meta properties to a results or progress window."""
	try:
		meta = dict(meta or {})
		extra = {}
		if not (clearlogo or meta.get('clearlogo')) or not meta.get('rating') or not meta.get('mpaa'):
			extra = _from_focused_item(meta)
		for k, v in extra.items():
			if v and not meta.get(k): meta[k] = v
		if not clearlogo and extra.get('clearlogo'): clearlogo = extra['clearlogo']
		get = meta.get
		season, episode = _num(get('season')), _num(get('episode'))
		is_episode = season is not None and episode is not None and get('media_type', get('mediatype', 'episode')) != 'movie'
		if is_episode and 'ep_name' in meta:
			show, ep_title = get('title') or '', get('ep_name') or ''
		elif is_episode and get('tvshowtitle'):
			show, ep_title = get('tvshowtitle') or '', get('title') or ''
		else:
			show, ep_title = get('title') or get('tvshowtitle') or '', ''
		year = str(get('year') or '').strip()
		if year in ('0', 'None'): year = ''
		try:
			rating = float(get('rating') or 0)
			rating = '%.1f' % rating if rating > 0 else ''
		except Exception: rating = ''
		mpaa = str(get('mpaa') or '').strip()
		if mpaa.upper() in ('NA', 'N/A', 'NONE', 'NR', 'NOT RATED'): mpaa = ''
		genre = get('genre') or ''
		if isinstance(genre, (list, tuple)): genre = ', '.join(str(i) for i in genre[:3])
		plot = get('plot') or get('tvshow_plot') or ''
		ep_code = 'S%02d · E%02d' % (season, episode) if is_episode else ''
		subtitle = '   '.join(i for i in (ep_code, ep_title) if i) if is_episode else '  ·  '.join(i for i in (year, mpaa, genre) if i)
		window.setProperty('lucent.show_title', _clean(show))
		window.setProperty('lucent.ep_code', ep_code)
		window.setProperty('lucent.ep_title', _clean(ep_title))
		window.setProperty('lucent.year', year)
		window.setProperty('lucent.rating', rating)
		window.setProperty('lucent.mpaa', mpaa)
		window.setProperty('lucent.genre', _clean(genre))
		window.setProperty('lucent.plot', _clean(plot))
		window.setProperty('lucent.subtitle', _clean(subtitle))
		window.setProperty('lucent.fanart', fanart or get('fanart') or '')
		window.setProperty('lucent.clearlogo', clearlogo if clearlogo is not None else (get('clearlogo') or ''))
	except Exception:
		pass


# ───────────── Umbrella: RIGHT on the stream list opens a filter ─────────────
_RIGHT, _BACK = 2, (9, 10, 13, 92)
_Q_ORDER = ('4K', '1080P', '720P', 'SD', 'SCR', 'CAM')


def _apply_filter(window, list_id, items, info):
	ctrl = window.getControl(list_id)
	ctrl.reset()
	ctrl.addItems(items)
	window.item_list = items
	window.setProperty('umbrella.total_results', str(len(items)))
	window.setProperty('lucent.filter_info', info)
	try: window.setFocusId(list_id); ctrl.selectItem(0)
	except Exception: pass


def lucent_filter(window, action_id, list_id):
	"""Umbrella result windows: RIGHT on the list -> filter menu, BACK -> clear.
	Returns True when the action was handled here."""
	try:
		full = getattr(window, '_lucent_full', None)
		if action_id in _BACK and full is not None:
			window._lucent_full = None
			_apply_filter(window, list_id, full, '')
			return True
		if action_id != _RIGHT or window.getFocusId() != list_id: return False
		import xbmcgui
		dialog = xbmcgui.Dialog()
		items = full if full is not None else list(window.item_list)
		if not items: return True
		get = lambda li, k: _clean(li.getProperty(k))
		qualities = sorted({get(i, 'umbrella.quality').upper() for i in items} - {''},
						key=lambda q: _Q_ORDER.index(q) if q in _Q_ORDER else 99)
		services = sorted({get(i, 'umbrella.debrid') for i in items} - {''})
		sites = sorted({get(i, 'umbrella.provider') for i in items} - {''})
		choices = [('Show %s only' % q, 'quality', q) for q in qualities]
		choices += [('Show %s only' % d, 'debrid', d) for d in services]
		choices += [('Source: %s' % p, 'site', p) for p in sites]
		choices += [('Filter by title...', 'title', ''), ('Filter by info (HDR, Atmos ...)...', 'info', '')]
		if full is not None: choices.insert(0, ('Show all results', 'all', ''))
		pick = dialog.select('Filter results', [c[0] for c in choices])
		if pick < 0: return True
		label, kind, value = choices[pick]
		if kind == 'all':
			window._lucent_full = None
			_apply_filter(window, list_id, items, '')
			return True
		if kind in ('quality', 'debrid', 'site'): label = value
		if kind == 'quality': result = [i for i in items if get(i, 'umbrella.quality').upper() == value]
		elif kind == 'debrid': result = [i for i in items if get(i, 'umbrella.debrid') == value]
		elif kind == 'site': result = [i for i in items if get(i, 'umbrella.provider') == value]
		elif kind == 'title':
			text = dialog.input('Keywords (comma separated)')
			words = [w.strip().upper() for w in (text or '').split(',') if w.strip()]
			if not words: return True
			result = [i for i in items if all(w in get(i, 'umbrella.name').upper() for w in words)]
			label = 'Title: ' + ', '.join(words)
		else:
			present = []
			for i in items:
				for n in range(1, _MAX_BADGES + 1):
					b = i.getProperty('lucent.badge_%d' % n)
					if b and b not in present: present.append(b)
			present.sort(key=lambda b: _RANK.get(b, 999))
			if not present: return True
			sel = dialog.multiselect('Filter by info', present)
			if not sel: return True
			want = [present[n] for n in sel]
			result = [i for i in items if all(w in [i.getProperty('lucent.badge_%d' % n) for n in range(1, _MAX_BADGES + 1)] for w in want)]
			label = ' + '.join(want)
		if not result:
			dialog.ok('Filter results', 'No results')
			return True
		window._lucent_full = items
		_apply_filter(window, list_id, result, label)
		return True
	except Exception:
		return False
