# -*- coding: utf-8 -*-

from json import dumps as jsdumps, loads as jsloads
import sys
import xbmc
try: #Py2
	from urlparse import parse_qsl
	from urllib import quote_plus
except ImportError: #Py3
	from urllib.parse import parse_qsl, quote_plus

if __name__ == '__main__':
	item = sys.listitem
	# message = item.getLabel()
	path = item.getPath()
	plugin = 'plugin://plugin.video.infinity/'
	args = path.split(plugin, 1)
	params = dict(parse_qsl(args[1].replace('?', '')))

	year = params.get('year', '')
	imdb = params.get('imdb', '')
	tmdb = params.get('tmdb', '')
	tvdb = params.get('tvdb', '')
	season = params.get('season', '')
	episode = params.get('episode', '')
	tvshowtitle = params.get('tvshowtitle', '')
	systvshowtitle = quote_plus(tvshowtitle)
	meta = jsloads(params['meta'])
	sysmeta = quote_plus(jsdumps(meta))

# to browse by Progress
	xbmc.executebuiltin('ActivateWindow(Videos,plugin://plugin.video.infinity/?action=episodes&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&meta=%s&season=%s&episode=%s,return)' % (systvshowtitle, year, imdb, tmdb, tvdb, sysmeta, season, episode))

# # to browse full episode list
	# xbmc.executebuiltin('ActivateWindow(Videos,plugin://plugin.video.infinity/?action=episodes&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&meta=%s&season=%s,return)' % (systvshowtitle, year, imdb, tmdb, tvdb, sysmeta, season))
