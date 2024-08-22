# -*- coding: utf-8 -*-
"""
	OneMoar Add-on
"""

from threading import Thread
from resources.lib.modules.control import addonFanart, jsonrpc, setting as getSetting, homeWindow, sleep
from resources.lib.windows.base import BaseDialog

class SourceProgress(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, args)
		self.closed = False
		self.monitor = None
		try:
			self.meta = kwargs.get('meta')
		except:
			self.meta = None
		self.imdb = self.meta.get('imdb')
		self.tvdb = self.meta.get('tvdb')
		self.year = self.meta.get('year')
		self.season = self.meta.get('season')
		self.episode = self.meta.get('episode')
		self.icon_only = 'true' if getSetting('progress.dialog') == '3' else 'false'
		self.use_fanart = getSetting('sources.dialog.fanartBG') == 'true'
		self.source_color = getSetting('sources.highlight.color')
		self.set_controls()

	def _monitor(self):
		while homeWindow.getProperty('infinity.source_progress_is_alive') == 'true': sleep(200)
		try: self.doClose()
		except: pass

	def create(self):
		self.monitor = True
		Thread(target=self.run).start()

	def run(self):
		homeWindow.setProperty('infinity.source_progress_is_alive', 'true')
		if self.monitor: Thread(target=self._monitor).start()
		self.doModal()
		self.clearProperties()
		homeWindow.clearProperty('infinity.source_progress_is_alive')

	def onAction(self, action):
		if action in self.closing_actions or action in self.selection_actions:
			self.doClose()

	def doClose(self):
		self.closed = True
		self.close()
		del self

	def iscanceled(self):
		return self.closed

	def set_controls(self):
		if self.meta == None:
			self.meta = self.checkLocalMeta()
		if self.meta:
			if self.meta.get('fanart') and self.use_fanart: self.setProperty('infinity.fanart', self.meta.get('fanart'))
			else: self.setProperty('infinity.fanart', addonFanart())
			if self.meta.get('clearlogo'): self.setProperty('infinity.clearlogo', self.meta.get('clearlogo'))
			if self.meta.get('title'): self.setProperty('infinity.title', self.meta.get('title'))
			if 'tvshowtitle' in self.meta: self.setProperty('infinity.tvtitle', self.meta.get('tvshowtitle'))
			if self.meta.get('plot'): self.setProperty('infinity.plot', self.meta.get('plot', ''))
		else:
			self.setProperty('infinity.fanart', addonFanart())
		self.setProperty('infinity.icononly', self.icon_only)
		self.setProperty('infinity.sources_highlight_color', self.source_color)

	def update(self, percent=0, content=''):
		try:
			self.getControl(2001).setText(content)
			self.getControl(5000).setPercent(percent)
		except: pass

	def checkLocalMeta(self):
		from json import dumps as jsdumps, loads as jsloads
		from urllib.parse import unquote
		try:
			def cleanLibArt(art):
				if not art: return ''
				art = unquote(art.replace('image://', ''))
				if art.endswith('/'): art = art[:-1]
				return art
			self.media_type = 'movie' if self.season is None or self.episode is None else 'episode'
			if self.media_type == 'movie':
				# do not add IMDBNUMBER as tmdb scraper puts their id in the key value
				meta = jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["title", "originaltitle", "uniqueid", "year", "premiered", "genre", "studio", "country", "runtime", "rating", "votes", "mpaa", "director", "writer", "cast", "plot", "plotoutline", "tagline", "thumbnail", "art", "file"]}, "id": 1}' % (self.year, str(int(self.year) + 1), str(int(self.year) - 1)))
				meta = jsloads(meta)['result']['movies']
				meta = [i for i in meta if i.get('uniqueid', []).get('imdb', '') == self.imdb]
				if meta: meta = meta[0]
				else: raise Exception()
				if 'mediatype' not in meta: meta.update({'mediatype': 'movie'})
				fanart = cleanLibArt(meta.get('art').get('fanart', '')) or self.fanart
				clearlogo = cleanLibArt(meta.get('art').get('clearlogo', ''))
				meta.update({'imdb': self.imdb, 'tvdb': self.tvdb, 'fanart': fanart, 'clearlogo': clearlogo})
				return meta
			else:
				if self.media_type != 'episode': raise Exception()
				# do not add IMDBNUMBER as tmdb scraper puts their id in the key value
				show_meta = jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["title", "originaltitle", "uniqueid", "mpaa", "year", "genre", "runtime", "thumbnail", "file"]}, "id": 1}' % (self.year, str(int(self.year)+1), str(int(self.year)-1)))
				show_meta = jsloads(show_meta)['result']['tvshows']
				show_meta = [i for i in show_meta if i.get('uniqueid', []).get('imdb', '') == self.imdb]
				if show_meta: show_meta = show_meta[0]
				else: raise Exception()
				tvshowid = show_meta['tvshowid']
				meta = jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params":{"tvshowid": %d, "filter":{"and": [{"field": "season", "operator": "is", "value": "%s"}, {"field": "episode", "operator": "is", "value": "%s"}]}, "properties": ["title", "season", "episode", "showtitle", "firstaired", "runtime", "rating", "director", "writer", "cast", "plot", "thumbnail", "art", "file"]}, "id": 1}' % (tvshowid, self.season, self.episode))
				meta = jsloads(meta)['result']['episodes']
				if meta: meta = meta[0]
				else: raise Exception()
				if 'mediatype' not in meta: meta.update({'mediatype': 'episode'})
				if 'tvshowtitle' not in meta: meta.update({'tvshowtitle': meta.get('showtitle')})
				if 'premiered' not in meta: meta.update({'premiered': meta.get('firstaired')})
				if 'year' not in meta: meta.update({'year': show_meta.get('year')}) # shows year not year episode aired
				fanart = cleanLibArt(meta.get('art').get('tvshow.fanart', '')) or self.poster
				clearlogo = cleanLibArt(meta.get('art').get('tvshow.clearlogo', ''))
				meta.update({'imdb': self.imdb, 'tvdb': self.tvdb, 'fanart': fanart,'clearlogo': clearlogo})
				return meta
		except:
			from resources.lib.modules import log_utils
			log_utils.log('Checking Local Meta Exception', log_utils.LOGDEBUG)
			return None
