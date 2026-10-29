# -*- coding: utf-8 -*-
# AB Tools "Search All" bridge - injected by AB Tools (plugin.program.abukarimtools).
# ABK_DEVICE_SELECT_VERSION = 3
#
# Gives Red Light, POV and Umbrella Fen Light's device-select modes, so AB Tools
# can collect their sources next to the other add-ons' and play the one picked:
#   app_list_sources  scrape with no window, save the results to
#                     addon_data/<add-on>/device_select/<request_id>.json, list them
#   app_play_source   load that file and play results[selected_index] with the
#                     add-on's own resolver (failover through the rest)
# (Red Light / POV read 'mode', Umbrella reads 'action'.)
# Only xbmc* modules here: the same file serves all three add-ons.
import os
import sys
import time
import json
import traceback

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

KEEP_SECONDS = 900
_ENDED = []
_ADDED = '_abk_added'           # keys added for AB Tools' list, removed again before playing


def _log(msg):
	xbmc.log('[AB Search bridge] %s' % msg, xbmc.LOGINFO)


def _aid():
	return xbmcaddon.Addon().getAddonInfo('id')


def _store_path(request_id):
	base = xbmcvfs.translatePath('special://profile/addon_data/%s/device_select/' % _aid())
	if not os.path.isdir(base):
		try: os.makedirs(base)
		except Exception: pass
	now = time.time()
	try:
		for name in os.listdir(base):
			path = os.path.join(base, name)
			try:
				if now - os.path.getmtime(path) > KEEP_SECONDS: os.remove(path)
			except Exception: pass
	except Exception: pass
	return os.path.join(base, '%s.json' % request_id)


def _handle():
	try: return int(sys.argv[1])
	except Exception: return -1


def _end_if_open():
	# the add-on can bail out early (busy lock, no debrid, no meta): always answer
	if _ENDED: return
	handle = _handle()
	if handle > 0:
		try: xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)
		except Exception: pass
	_ENDED.append(True)


def _params(src):
	return getattr(src, 'abk_params', None) or getattr(src, 'params', None) or {}


# ───────────────────────── entry (router hook) ─────────────────────────

def app_mode(mode, params):
	aid = _aid()
	p = dict(params)
	for k in ('play_type', 'nextep_settings', 'nextep_stash_play'): p.pop(k, None)
	if mode == 'app_list_sources':
		del _ENDED[:]       # the module outlives one call when the add-on reuses its interpreter
		try:
			return _run(aid, 'list', p)
		except Exception as e:
			_log('list failed: %s\n%s' % (e, traceback.format_exc()))
		finally:
			_end_if_open()
		return
	return _run(aid, 'play', p)


def _none(v):
	return None if v in (None, '', 'None') else v


def _run(aid, kind, p):
	if aid == 'plugin.video.umbrella':
		from resources.lib.modules import sources as umb
		src = umb.Sources(p.get('all_providers'))
		src.abk_mode, src.abk_params = kind, p
		g = p.get
		restore = _silence_umbrella(umb, src) if kind == 'list' else None
		try:
			return src.play(_none(g('title')), _none(g('year')), _none(g('imdb')), _none(g('tmdb')), _none(g('tvdb')),
							_none(g('season')), _none(g('episode')), _none(g('tvshowtitle')), _none(g('premiered')), None, '0')
		finally:
			if restore: restore()
	from modules.sources import Sources
	if aid == 'plugin.video.pov' and kind == 'list':
		import modules.sources as pov
		restore = _guard_pov(pov)
		try:
			p.update({'device_list': 'true', 'background': 'true', 'autoplay': 'false', 'prescrape': 'false'})
			return Sources().source_select(p)
		finally:
			restore()
	if kind == 'list':
		p.update({'device_list': 'true', 'background': 'true', 'autoplay': 'false', 'prescrape': 'false'})
	else:
		p.update({'play_selected': p.get('request_id', ''), 'autoplay': 'false'})
	if aid == 'plugin.video.pov':
		return Sources().source_select(p)
	return Sources().playback_prep(p)


# ───────────────────────── POV: results with odd field types ─────────────────────────
# Some scraper results reach POV with a size given as text or an info field
# that is not text; POV's sort / filter then raise (kodi.log 2026-10-29:
# "'<' not supported between instances of 'str' and 'int'", "argument of type
# 'int' is not a container or iterable") and the whole list is lost. For AB
# Tools' list only: on such an error clean the fields and run POV's own
# processing again (put back afterwards: POV may keep this interpreter).

_POV_TEXT = ('extraInfo', 'cache_provider', 'quality', 'name', 'display_name', 'scrape_provider',
			 'debrid', 'source', 'provider', 'name_info', 'size_label')


def _clean_pov(item, ranks):
	for k in _POV_TEXT:
		if k in item and not isinstance(item[k], str):
			item[k] = '' if item[k] is None else str(item[k])
	try: item['size'] = float(item.get('size') or 0)
	except Exception: item['size'] = 0.0
	if ranks and item.get('quality') not in ranks: item['quality'] = 'SD'
	item.setdefault('extraInfo', '')
	item.setdefault('cache_provider', '')
	item.setdefault('scrape_provider', 'external')
	return item


def _guard_pov(pov):
	rp = pov.ResultsProcessor
	orig = rp.process
	ranks = getattr(pov, 'quality_ranks', None)
	def process(self, results):
		try:
			return orig(self, results)
		except Exception:
			_log('POV could not sort its results, cleaning them and retrying:\n%s' % traceback.format_exc())
		clean = [_clean_pov(dict(i), ranks) for i in (results or []) if isinstance(i, dict)]
		try:
			return orig(self, clean)
		except Exception:
			_log('POV still failing, listing the cleaned results unsorted:\n%s' % traceback.format_exc())
			return [i for i in clean if 'Uncached' not in i['cache_provider']]
	rp.process = process
	def restore():
		rp.process = orig
	return restore


class _Silent(object):
	"""Stands in for Umbrella's scrape progress dialog while AB Tools collects."""
	def create(self, *a, **k): pass
	def update(self, *a, **k): pass
	def close(self, *a, **k): pass
	def iscanceled(self): return False
	def isFinished(self): return False


def _silence_umbrella(umb, src):
	"""No progress window and no custom-title prompt during a background scrape.
	Put back afterwards: Umbrella may keep this interpreter for later calls."""
	old_setting, old_bg = umb.getSetting, umb.control.progressDialogBG
	def setting(key, *a, **k):
		if key == 'progress.dialog': return 'abk'          # -> the background dialog branch
		if key == 'dialogs.useumbrelladialog': return 'false'
		return old_setting(key, *a, **k)
	umb.getSetting = setting
	umb.control.progressDialogBG = _Silent()
	try: src.custom_query = 'false'
	except Exception: pass
	def restore():
		umb.getSetting = old_setting
		umb.control.progressDialogBG = old_bg
	return restore


# ───────────────────────── listing ─────────────────────────

def _umbrella_view(item):
	"""Umbrella's fields -> the ones AB Tools reads (Fen Light style)."""
	add = {}
	get = item.get
	def put(k, v):
		if k not in item:
			add[k] = v
	try: size = float(get('size') or 0)
	except Exception: size = 0
	src = str(get('source') or '')
	put('display_name', get('name', ''))
	put('extraInfo', str(get('info') or ''))
	put('size_label', '%.2f GB' % size if size else 'N/A')
	put('scrape_provider', 'external')
	put('abk_site', get('provider', ''))
	put('cache_provider', ('Uncached ' if src.lower().startswith('uncached') else '') + str(get('debrid') or ''))
	if add:
		item.update(add)
		item[_ADDED] = list(add)
	return item


def output_sources_directory(src, results):
	params = _params(src)
	request_id = params.get('request_id') or str(int(time.time() * 1000))
	results = list(results or [])
	if _aid() == 'plugin.video.umbrella':
		results = [_umbrella_view(dict(i)) for i in results if isinstance(i, dict)]
	try:
		with open(_store_path(request_id), 'w') as f:
			json.dump(results, f, default=str)
	except Exception as e:
		_log('could not save results: %s' % e)
	handle = _handle()
	if handle > 0:
		items = []
		for index, item in enumerate(results):
			get = item.get
			label = '%s | %s | %s' % ((get('debrid') or get('source') or '').upper(), (get('quality') or 'SD').upper(), get('size_label', 'N/A'))
			li = xbmcgui.ListItem(label, offscreen=True)
			items.append(('plugin://%s/?abk_index=%d' % (_aid(), index), li, False))
		try:
			xbmcplugin.addDirectoryItems(handle, items)
			xbmcplugin.setContent(handle, 'files')
			xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)
		except Exception as e:
			_log('listing: %s' % e)
	_ENDED.append(True)
	_log('%d sources listed for request %s' % (len(results), request_id))


# ───────────────────────── playing ─────────────────────────

def _notify(text):
	try: xbmcgui.Dialog().notification('AB Search All', text, xbmcgui.NOTIFICATION_INFO, 3500)
	except Exception: pass


def play_selected_source(src, title=None):
	params = _params(src)
	request_id = params.get('play_selected') or params.get('request_id', '')
	try: index = int(params.get('selected_index', 0))
	except Exception: index = 0
	results = []
	try:
		with open(_store_path(request_id)) as f:
			results = json.load(f)
	except Exception:
		pass
	if not results:
		return _notify('Source list expired - search again')
	if index < 0 or index >= len(results): index = 0
	_log('play %s #%d of %d' % (request_id, index, len(results)))
	if _aid() == 'plugin.video.umbrella':
		for item in results:
			for k in item.pop(_ADDED, []):
				item.pop(k, None)
		source = results[index]
		meta = getattr(src, 'meta', None) or {}
		return src.playItem(title or '', json.dumps(results), json.dumps([source]), json.dumps(meta))
	source = results[index]
	if 'Uncached' in str(source.get('cache_provider', '')):
		try:
			from modules.debrid import manual_add_magnet_to_cloud
			return manual_add_magnet_to_cloud({'mode': 'manual_add_magnet_to_cloud',
											   'provider': source.get('debrid'), 'magnet_url': source.get('url')})
		except Exception:
			pass
	return src.play_file(results, source)
