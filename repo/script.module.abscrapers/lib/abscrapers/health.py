# -*- coding: utf-8 -*-
"""
	AB Scrapers - provider health check (adapted from Gears/Magneto).
	Runs a movie search through every provider (or every enabled one) and
	shows per-provider timing, result count and which engines answered.
"""

from concurrent.futures import ThreadPoolExecutor as Pool, as_completed
from time import monotonic
import requests
import xbmcaddon, xbmcgui
from abscrapers.common import ADDON_ID
from abscrapers.strings import ls

total_str = 'TOTAL: [COLOR red][B]%s[/B][/COLOR]  |  4K: [COLOR red][B]%d[/B][/COLOR]  |  1080p: [COLOR red][B]%d[/B][/COLOR]  |  720p: [COLOR red][B]%d[/B][/COLOR]  |  SD: [COLOR red][B]%d[/B][/COLOR]'
movie_check_url = 'https://v2.sg.media-imdb.com/suggestion/t/%s.json'
heading, resolutions = 'AB Scrapers', ('4K', '1080p', '720p', 'SD')


def _probe(m):
	try:
		start = monotonic()
		m.results = m.sources(m.data, {})
		m.elapsed = round(monotonic() - start, 3)
		for r in m.results or []:
			q = r.get('quality')
			m.metrics[q if q in m.metrics else 'SD'] += 1
	except Exception as e:
		m.results, m.error = None, str(e)
	return m


def run():
	addon = xbmcaddon.Addon(ADDON_ID)
	icon = addon.getAddonInfo('icon')
	dialog = xbmcgui.Dialog()
	mode = dialog.select(heading, [ls('Test enabled providers only'), ls('Test every provider')])
	if mode < 0: return
	data = {'imdb': 'tt0120903', 'title': 'X-Men', 'aliases': [], 'year': 2000, 'poster': icon}
	imdb_id = dialog.input(ls('Enter a valid movie IMDb id:'), defaultt=data['imdb'])
	if not imdb_id: return
	progress = xbmcgui.DialogProgress()
	progress.create(heading, ls('Please wait...'))
	try:
		res = requests.get(movie_check_url % imdb_id, timeout=6).json()
		item = next((i for i in res.get('d', []) if i.get('id') == imdb_id), None)
		if not item:
			progress.close()
			return dialog.notification(heading, ls('Movie %s not found') % imdb_id, icon, 3000)
		data.update({'imdb': item['id'], 'title': item.get('l'), 'year': item.get('y'), 'poster': (item.get('i') or {}).get('imageUrl') or icon})
	except Exception: pass
	data['year'] = str(data['year'])
	import abscrapers
	modules = []
	for provider, cls in abscrapers.sources(ret_all=(mode == 1)):
		if not getattr(cls, 'hasMovies', True): continue
		try: m = cls()
		except Exception: continue
		m.name, m.data, m.results, m.elapsed, m.error = provider, data, None, 0, None
		m.engines = getattr(cls, 'ab_engines', None) or (cls.__module__.split('.')[2],)
		m.metrics = dict.fromkeys(resolutions, 0)
		modules.append(m)
	total = len(modules) or 1
	line0 = '%s (%s)' % (data['title'], data['year'])
	with Pool(min(total, 24)) as pool:
		futures = [pool.submit(_probe, m) for m in modules]
		for i, f in enumerate(as_completed(futures), 1):
			m = f.result()
			if progress.iscanceled(): break
			progress.update(int(i / total * 100), '[CR]'.join((line0, m.name.upper(), '%.2fs  |  %d' % (m.elapsed, sum(m.metrics.values())))))
	progress.close()
	modules.sort(key=lambda m: (not m.results, m.elapsed))
	items = []
	for m in modules:
		values = [m.metrics[r] for r in resolutions]
		li = xbmcgui.ListItem('%s  [COLOR grey][%s][/COLOR]: %.2fs' % (m.name.upper(), '+'.join(m.engines), m.elapsed),
							total_str % ('NONE' if m.results is None else sum(values), *values), offscreen=True)
		li.setArt({'icon': data['poster']})
		items.append(li)
	dialog.select('%s - %s' % (heading, line0), items, useDetails=True)
