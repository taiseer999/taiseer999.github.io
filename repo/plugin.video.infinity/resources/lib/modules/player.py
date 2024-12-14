# -*- coding: utf-8 -*-
"""
	OneMoar Add-on
"""

from hashlib import md5
from json import dumps as jsdumps, loads as jsloads
from sys import argv, exit as sysexit
from sqlite3 import dbapi2 as database
from urllib.parse import quote_plus, unquote
import xbmc
from resources.lib.database.cache import clear_local_bookmarks
from resources.lib.database.metacache import fetch as fetch_metacache
from resources.lib.database.traktsync import fetch_bookmarks
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules import playcount
from resources.lib.indexers import trakt

LOGINFO = 1
getLS = control.lang
getSetting = control.setting
homeWindow = control.homeWindow
playerWindow = control.playerWindow


class Player(xbmc.Player):
	def __init__(self):
		xbmc.Player.__init__(self)
		self.play_next_triggered = False
		self.preScrape_triggered = False
		self.playbackStopped_triggered = False
		self.playback_resumed = False
		self.onPlayBackStopped_ran = False
		self.media_type = None
		self.DBID = None
		self.offset = '0'
		self.media_length = 0
		self.current_time = 0
		self.meta = {}
		self.enable_playnext = getSetting('enable.playnext') == 'true'
		self.playnext_time = int(getSetting('playnext.time')) or 60
		self.traktCredentials = trakt.getTraktCredentialsInfo()
		self.markwatched_percentage = int(getSetting('markwatched.percent')) or 85
		self.multi_season = getSetting('infinity.multiSeason') == 'true'
		self.playnext_percentage = int(getSetting('playnext.percent')) or 80
		self.playnext_min = int(getSetting('playnext.min.seconds'))
		self.playnext_method = getSetting('playnext.method')

	def play_source(self, title, year, season, episode, imdb, tmdb, tvdb, url, meta, debridPackCall=False):
		try:
			from sys import argv # some functions like ActivateWindow() throw invalid handle less this is imported here.
			if not url: raise Exception
			self.media_type = 'movie' if season is None or episode is None else 'episode'
			self.title, self.year = title, str(year)
			if self.media_type == 'movie':
				self.name, self.season, self.episode = '%s (%s)' % (title, self.year), None, None
			elif self.media_type == 'episode':
				self.name, self.season, self.episode = '%s S%02dE%02d' % (title, int(season), int(episode)), '%01d' % int(season), '%01d' % int(episode)
			self.imdb, self.tmdb, self.tvdb = imdb or '', tmdb or '', tvdb or ''
			self.ids = {'imdb': self.imdb, 'tmdb': self.tmdb, 'tvdb': self.tvdb}
## - compare meta received to database and use largest(eventually switch to a request to fetch missing db meta for item)
			self.imdb_user = getSetting('imdbuser').replace('ur', '')
			self.tmdb_key = getSetting('tmdb.apikey')
#			if not self.tmdb_key: self.tmdb_key = ''
			self.tvdb_key = getSetting('tvdb.apikey')
			if self.media_type == 'episode': self.user = str(self.imdb_user) + str(self.tvdb_key)
			else: self.user = str(self.tmdb_key)
			self.lang = control.apiLanguage()['tvdb']
			meta1 = dict((k, v) for k, v in iter(meta.items()) if v is not None and v != '') if meta else None
			meta2 = fetch_metacache([{'imdb': self.imdb, 'tmdb': self.tmdb, 'tvdb': self.tvdb}], self.lang, self.user)[0]
			if meta2 != self.ids: meta2 = dict((k, v) for k, v in iter(meta2.items()) if v is not None and v != '')
			if meta1 is not None:
				try:
					if len(meta2) > len(meta1):
						meta2.update(meta1)
						meta = meta2
					else: meta = meta1
				except: log_utils.error()
			else: meta = meta2 if meta2 != self.ids else meta1
##################
			self.poster = meta.get('poster') if meta else ''
			self.fanart = meta.get('fanart') if meta else ''
			self.meta = meta
			poster, thumb, season_poster, fanart, banner, clearart, clearlogo, discart, meta = self.getMeta(meta)
			self.offset = Bookmarks().get(name=self.name, imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, year=self.year, runtime=meta.get('duration') if meta else 0)

			if self.offset == '-1':
				log_utils.log('User requested playback cancel', level=log_utils.LOGDEBUG)
				control.notification(message=32328)
				return control.cancelPlayback()

			item = control.item(path=url)
			if self.media_type == 'episode':
				item.setArt({'tvshow.clearart': clearart, 'tvshow.clearlogo': clearlogo, 'tvshow.discart': discart, 'thumb': thumb, 'tvshow.poster': season_poster, 'season.poster': season_poster, 'tvshow.fanart': fanart})
			else:
				item.setArt({'clearart': clearart, 'clearlogo': clearlogo, 'discart': discart, 'thumb': thumb, 'poster': poster, 'fanart': fanart})
			control.set_info(item, meta, self.ids, url)
			item.setProperty('IsPlayable', 'true')
			if self.media_type == 'episode' and self.enable_playnext: self.buildSeasonPlaylist(url, item)
			if debridPackCall: control.player.play(url, item) # seems this is only way browseDebrid pack files will play and have meta marked as watched
			elif control.playlist.getposition() == -1 and control.playlist.size(): control.player.play(control.playlist)
			else: control.resolve(int(argv[1]), True, item)
			homeWindow.setProperty('script.trakt.ids', jsdumps(self.ids))
			self.keepAlive()
			homeWindow.clearProperty('script.trakt.ids')
		except:
			log_utils.error()
			return control.cancelPlayback()

	def buildSeasonPlaylist(self, link, link_item):
		try:
			if control.playlist.getposition() == -1:
				control.player.stop() ; control.playlist.clear()
				control.playlist.add(url=link, listitem=link_item)
			from resources.lib.menus import seasons, episodes
			seasons = seasons.Seasons().tmdb_list(tvshowtitle='', imdb='', tmdb=self.tmdb, tvdb='', art=None)
			seasons = [int(i['season']) for i in seasons]
			ep_data = [episodes.Episodes().get(self.meta.get('tvshowtitle'), self.meta.get('year'), self.imdb, self.tmdb, self.tvdb, self.meta, season=i, create_directory=False) for i in seasons]
			items = [i for e in ep_data for i in e if i.get('unaired') != 'true']
			index = next((idx for idx, i in enumerate(items) if i['season'] == int(self.season) and i['episode'] == int(self.episode)), None)
			if index is None: return
			try: item = items[index+1]
			except: return
			if item.get('season') and item.get('season') > int(self.season) and not self.multi_season: return
			items = episodes.Episodes().episodeDirectory([item], next=False, playlist=True)
			for url, li, folder in items: control.playlist.add(url=url, listitem=li)
		except: log_utils.error()

	def getMeta(self, meta):
		try:
			if not meta or ('videodb' in control.infoLabel('ListItem.FolderPath')): raise Exception()
			poster = meta.get('poster3') or meta.get('poster2') or meta.get('poster') #poster2 and poster3 may not be passed anymore
			thumb = meta.get('thumb')
			thumb = thumb or poster or control.addonThumb()
			season_poster = meta.get('season_poster') or poster
			fanart = meta.get('fanart')
			banner = meta.get('banner')
			clearart = meta.get('clearart')
			clearlogo = meta.get('clearlogo')
			discart = meta.get('discart')
			if 'mediatype' not in meta:
				meta.update({'mediatype': 'episode' if self.episode else 'movie'})
				if self.episode: meta.update({'tvshowtitle': self.title, 'season': self.season, 'episode': self.episode})
			return (poster, thumb, season_poster, fanart, banner, clearart, clearlogo, discart, meta)
		except: log_utils.error()
		try:
			def cleanLibArt(art):
#				from urllib.parse import unquote
				if not art: return ''
				art = unquote(art.replace('image://', ''))
				if art.endswith('/'): art = art[:-1]
				return art
			def sourcesDirMeta(metadata): # pass player minimal meta needed from lib pull
				if not metadata: return metadata
				allowed = ['mediatype', 'imdb', 'tmdb', 'tvdb', 'poster', 'season_poster', 'fanart', 'banner', 'clearart', 'clearlogo', 'discart', 'thumb', 'title', 'tvshowtitle', 'year', 'premiered', 'rating', 'plot', 'duration', 'mpaa', 'season', 'episode', 'castandrole']
				return {k: v for k, v in iter(metadata.items()) if k in allowed}
			poster, thumb, season_poster, fanart, banner, clearart, clearlogo, discart, meta = '', '', '', '', '', '', '', '', {'title': self.name}
			if self.media_type != 'movie': raise Exception()
			# do not add IMDBNUMBER as tmdb scraper puts their id in the key value
			meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["title", "originaltitle", "uniqueid", "year", "premiered", "genre", "studio", "country", "runtime", "rating", "votes", "mpaa", "director", "writer", "cast", "plot", "plotoutline", "tagline", "thumbnail", "art", "file"]}, "id": 1}' % (self.year, str(int(self.year) + 1), str(int(self.year) - 1)))
			meta = jsloads(meta)['result']['movies']
			meta = [i for i in meta if (i.get('uniqueid', []).get('imdb', '') == self.imdb) or (i.get('uniqueid', []).get('unknown', '') == self.imdb)] # scraper now using "unknown"
			if meta: meta = meta[0]
			else: raise Exception()
			if 'mediatype' not in meta: meta.update({'mediatype': 'movie'})
			if 'duration' not in meta: meta.update({'duration': meta.get('runtime')}) # Trakt scrobble resume needs this for lib playback
			if 'castandrole' not in meta: meta.update({'castandrole': [(i['name'], i['role']) for i in meta.get('cast')]})
			thumb = cleanLibArt(meta.get('art').get('thumb', ''))
			poster = cleanLibArt(meta.get('art').get('poster', '')) or self.poster
			fanart = cleanLibArt(meta.get('art').get('fanart', '')) or self.fanart
			banner = cleanLibArt(meta.get('art').get('banner', '')) # not sure this is even used by player
			clearart = cleanLibArt(meta.get('art').get('clearart', ''))
			clearlogo = cleanLibArt(meta.get('art').get('clearlogo', ''))
			discart = cleanLibArt(meta.get('art').get('discart'))
			if 'plugin' not in control.infoLabel('Container.PluginName'):
				self.DBID = meta.get('movieid')
			meta = sourcesDirMeta(meta)
			return (poster, thumb, '', fanart, banner, clearart, clearlogo, discart, meta)
		except: log_utils.error()
		try:
			if self.media_type != 'episode': raise Exception()
			# do not add IMDBNUMBER as tmdb scraper puts their id in the key value
			show_meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["title", "originaltitle", "uniqueid", "mpaa", "year", "genre", "runtime", "thumbnail", "file"]}, "id": 1}' % (self.year, str(int(self.year)+1), str(int(self.year)-1)))
			show_meta = jsloads(show_meta)['result']['tvshows']
			show_meta = [i for i in show_meta if i['uniqueid']['imdb'] == self.imdb]
			show_meta = [i for i in show_meta if (i.get('uniqueid', []).get('imdb', '') == self.imdb) or (i.get('uniqueid', []).get('unknown', '') == self.imdb)] # scraper now using "unknown"
			if show_meta: show_meta = show_meta[0]
			else: raise Exception()
			tvshowid = show_meta['tvshowid']
			meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params":{"tvshowid": %d, "filter":{"and": [{"field": "season", "operator": "is", "value": "%s"}, {"field": "episode", "operator": "is", "value": "%s"}]}, "properties": ["showtitle", "title", "season", "episode", "firstaired", "runtime", "rating", "director", "writer", "cast", "plot", "thumbnail", "art", "file"]}, "id": 1}' % (tvshowid, self.season, self.episode))
			meta = jsloads(meta)['result']['episodes']
			if meta: meta = meta[0]
			else: raise Exception()
			if 'mediatype' not in meta: meta.update({'mediatype': 'episode'})
			if 'tvshowtitle' not in meta: meta.update({'tvshowtitle': meta.get('showtitle')})
			if 'castandrole' not in meta: meta.update({'castandrole': [(i['name'], i['role']) for i in meta.get('cast')]})
			if 'genre' not in meta: meta.update({'genre': show_meta.get('genre')})
			if 'duration' not in meta: meta.update({'duration': meta.get('runtime')}) # Trakt scrobble resume needs this for lib playback but Kodi lib returns "0" for shows or episodes
			if 'mpaa' not in meta: meta.update({'mpaa': show_meta.get('mpaa')})
			if 'premiered' not in meta: meta.update({'premiered': meta.get('firstaired')})
			if 'year' not in meta: meta.update({'year': show_meta.get('year')}) # shows year not year episode aired
			thumb = cleanLibArt(meta.get('art').get('thumb', ''))
			season_poster = poster = cleanLibArt(meta.get('art').get('season.poster', '')) or self.poster
			fanart = cleanLibArt(meta.get('art').get('tvshow.fanart', '')) or self.poster
			banner = cleanLibArt(meta.get('art').get('tvshow.banner', '')) # not sure this is even used by player
			clearart = cleanLibArt(meta.get('art').get('tvshow.clearart', ''))
			clearlogo = cleanLibArt(meta.get('art').get('tvshow.clearlogo', ''))
			discart = cleanLibArt(meta.get('art').get('discart'))
			if 'plugin' not in control.infoLabel('Container.PluginName'):
				self.DBID = meta.get('episodeid')
			meta = sourcesDirMeta(meta)
			return (poster, thumb, season_poster, fanart, banner, clearart, clearlogo, discart, meta)
		except:
			log_utils.error()
			return (poster, thumb, season_poster, fanart, banner, clearart, clearlogo, discart, meta)

	def getWatchedPercent(self):
		if self.isPlayback():
			try:
				position = self.getTime()
				if position != 0: self.current_time = position
				total_length = self.getTotalTime()
				if total_length != 0: self.media_length = total_length
			except: pass
		current_position = self.current_time
		total_length = self.media_length
		watched_percent = 0
		if int(total_length) != 0:
			try:
				watched_percent = float(current_position) / float(total_length) * 100
				if watched_percent > 100: watched_percent = 100
			except: log_utils.error()
		return watched_percent

	def getRemainingTime(self):
		remaining_time = 0
		if self.isPlayback():
			try:
				current_position = self.getTime()
				remaining_time = int(self.media_length) - int(current_position)
			except: pass
		return remaining_time

	def keepAlive(self):
		control.hide()
		control.sleep(200)
		pname = '%s.player.overlay' % control.addonInfo('id')
		homeWindow.clearProperty(pname)
		for i in range(0, 500):
			if self.isPlayback():
				control.closeAll()
				break
			xbmc.sleep(200)

		xbmc.sleep(5000)
		playlist_skip = False
		try: running_path = self.getPlayingFile() # original video that playlist playback started with
		except: running_path = ''

		if playerWindow.getProperty('infinity.playlistStart_position'): pass
		else:
			if control.playlist.size() > 1: playerWindow.setProperty('infinity.playlistStart_position', str(control.playlist.getposition()))

		while self.isPlayingVideo() and not control.monitor.abortRequested():
			try:
				if running_path != self.getPlayingFile(): # will not match if user hits "Next" so break from keepAlive()
					playlist_skip = True
					break

				try:
					self.current_time = self.getTime()
					self.media_length = self.getTotalTime()
				except: pass
				watcher = (self.getWatchedPercent() >= int(self.markwatched_percentage))
				property = homeWindow.getProperty(pname)

				if self.media_type == 'movie':
					try:
						if watcher and property != '5':
							homeWindow.setProperty(pname, '5')
							playcount.markMovieDuringPlayback(self.imdb, '5')
					except: pass
					xbmc.sleep(2000)

				elif self.media_type == 'episode':
					try:
						if watcher and property != '5':
							homeWindow.setProperty(pname, '5')
							playcount.markEpisodeDuringPlayback(self.imdb, self.tvdb, self.season, self.episode, '5')
						if self.enable_playnext and not self.play_next_triggered:
							if int(control.playlist.size()) > 1:
								if self.preScrape_triggered == False:
									xbmc.executebuiltin('RunPlugin(plugin://plugin.video.infinity/?action=play_preScrapeNext)')
									self.preScrape_triggered = True
								remaining_time = self.getRemainingTime()
								if remaining_time < (self.playnext_time + 1) and remaining_time != 0:
									xbmc.executebuiltin('RunPlugin(plugin://plugin.video.infinity/?action=play_nextWindowXML)')
									self.play_next_triggered = True
					except: log_utils.error()
					xbmc.sleep(1000)

			except:
				log_utils.error()
				xbmc.sleep(1000)
		homeWindow.clearProperty(pname)
		if playlist_skip: pass
		else:
			# # self.onPlayBackEnded() # check, kodi may at times not issue "onPlayBackEnded" callback
			# if self.media_length - self.current_time > 60: # kodi may at times not issue "onPlayBackStopped" callback
			if (int(self.current_time) > 180 and (self.getWatchedPercent() < int(self.markwatched_percentage))): # kodi may at times not issue "onPlayBackStopped" callback
				self.playbackStopped_triggered = True
				self.onPlayBackStopped()

	def isPlayingFile(self):
		if self._running_path is None or self._running_path.startswith("plugin://"):
			return False

	def isPlayback(self):
		# Kodi often starts playback where isPlaying() is true and isPlayingVideo() is false, since the video loading is still in progress, whereas the play is already started.
		return self.isPlaying() and self.isPlayingVideo() and self.getTime() > 0

	def libForPlayback(self):
		if self.DBID is None: return
		try:
			if self.media_type == 'movie':
				rpc = '{"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": {"movieid": %s, "playcount": 1 }, "id": 1 }' % str(self.DBID)
			elif self.media_type == 'episode':
				rpc = '{"jsonrpc": "2.0", "method": "VideoLibrary.SetEpisodeDetails", "params": {"episodeid": %s, "playcount": 1 }, "id": 1 }' % str(self.DBID)
			control.jsonrpc(rpc)
		except: log_utils.error()

### Kodi player callback methods ###
	def onAVStarted(self): # Kodi docs suggests "Use onAVStarted() instead of onPlayBackStarted() as of v18"
		for i in range(0, 500):
			if self.isPlayback(): break
			else: control.sleep(200)
		homeWindow.clearProperty('infinity.source_progress_is_alive')
		control.sleep(500)
		control.closeAll()
		if self.offset != '0' and self.playback_resumed is False:
			control.sleep(200)
			if self.traktCredentials and getSetting('resume.source') == '1': # re-adjust the resume point since dialog is based on meta runtime vs. getTotalTime() and inaccurate
				try:
					total_time = self.getTotalTime()
					progress = float(fetch_bookmarks(self.imdb, self.tmdb, self.tvdb, self.season, self.episode))
					self.offset = (progress / 100) * total_time
				except: pass
			else:
				try: self.offset = float(self.offset)
				except: self.offset = 0
			self.seekTime(self.offset)
			self.playback_resumed = True
		if getSetting('subtitles') == 'true': Subtitles().get(self.title, self.year, self.imdb, self.season, self.episode)
		if   self.media_type == 'episode' and self.enable_playnext and self.playnext_method == '2': # subtitle
			try:
				if not playerWindow.getProperty(f"infinity.sub_end.{self.imdb}"):
					Subtitles().get(self.title, self.year, self.imdb, self.season, self.episode, False)
				value = playerWindow.getProperty(f"infinity.sub_end.{self.imdb}") or 0
				if not value:
					if getSetting('playnext.sub.backupmethod') == '1':
						value = int(getSetting('playnext.sub.percent'))
						value = int(total_time - (total_time * value / 100))
					else: value = int(getSetting('playnext.sub.seconds'))
				self.playnext_time = max((int(value), self.playnext_min))
			except: self.playnext_time = self.playnext_min
		elif self.media_type == 'episode' and self.enable_playnext and self.playnext_method == '1': # percent
			total_time = self.getTotalTime()
			self.playnext_time = int(total_time - (total_time * self.playnext_percentage / 100))
		if self.traktCredentials:
			trakt.scrobbleReset(imdb=self.imdb, tmdb=self.tmdb, tvdb=self.tvdb, season=self.season, episode=self.episode, refresh=False) # refresh issues container.refresh()
		log_utils.log('onAVStarted callback', level=log_utils.LOGDEBUG)

	def onPlayBackSeek(self, time, seekOffset):
		seekOffset /= 1000

	def onPlayBackSeekChapter(self, chapter):
		log_utils.log('onPlayBackSeekChapter callback', level=log_utils.LOGDEBUG)

	def onQueueNextItem(self):
		log_utils.log('onQueueNextItem callback', level=log_utils.LOGDEBUG)

	def onPlayBackStarted(self):
		control.hide()

	def onPlayBackStopped(self):
		try:
			playerWindow.clearProperty('infinity.preResolved_nextUrl')
			playerWindow.clearProperty('infinity.playlistStart_position')
			homeWindow.clearProperty('infinity.source_progress_is_alive')
			clear_local_bookmarks() # clear all infinity bookmarks from kodi database

			if not self.onPlayBackStopped_ran or (self.playbackStopped_triggered and not self.onPlayBackStopped_ran): # Kodi callback unreliable and often not issued
				self.onPlayBackStopped_ran = True
				self.playbackStopped_triggered = False
				Bookmarks().reset(self.current_time, self.media_length, self.name, self.year)
				if self.traktCredentials and (getSetting('trakt.scrobble') == 'true'):
					Bookmarks().set_scrobble(self.current_time, self.media_length, self.media_type, self.imdb, self.tmdb, self.tvdb, self.season, self.episode)
				watcher = self.getWatchedPercent()
				seekable = (int(self.current_time) > 180 and (watcher < int(self.markwatched_percentage)))
				if watcher >= int(self.markwatched_percentage): self.libForPlayback() # only write playcount to local lib

				if getSetting('crefresh') == 'true' and seekable:
					log_utils.log('container.refresh issued', level=log_utils.LOGDEBUG)
					control.refresh() #not all skins refresh after playback stopped
				control.playlist.clear()
				#control.trigger_widget_refresh() # skinshortcuts handles widget refresh
				log_utils.log('onPlayBackStopped callback', level=log_utils.LOGDEBUG)
		except: log_utils.error()

	def onPlayBackEnded(self):
		Bookmarks().reset(self.current_time, self.media_length, self.name, self.year)
		# if self.traktCredentials:
			# trakt.scrobbleReset(imdb=self.imdb, tmdb=self.tmdb, tvdb=self.tvdb, season=self.season, episode=self.episode, refresh=False) # refresh issues container.refresh()
		self.libForPlayback()
		if control.playlist.getposition() == control.playlist.size() or control.playlist.size() == 1 or (control.playlist.getposition() == 0 and playerWindow.getProperty('playnextPlayPressed') == '0'):
			control.playlist.clear()
		log_utils.log('onPlayBackEnded callback', level=log_utils.LOGDEBUG)

	def onPlayBackError(self):
		playerWindow.clearProperty('infinity.preResolved_nextUrl')
		playerWindow.clearProperty('infinity.playlistStart_position')
		homeWindow.clearProperty('infinity.source_progress_is_alive')

		Bookmarks().reset(self.current_time, self.media_length, self.name, self.year)
		log_utils.error()
		log_utils.log('onPlayBackError callback', level=log_utils.LOGDEBUG)
		sysexit(1)

	def onPlayBackPaused(self):
		log_utils.log('onPlayBackPaused callback', level=log_utils.LOGDEBUG)
		watcher = self.getWatchedPercent()
		if watcher <= int(self.markwatched_percentage):
			Bookmarks().reset(self.current_time, self.media_length, self.name, self.year)
			if self.traktCredentials and (getSetting('trakt.scrobble') == 'true'):
				log_utils.log('Paused: Sending scrobble to trakt.', level=log_utils.LOGDEBUG)
				Bookmarks().set_scrobble(self.current_time, self.media_length, self.media_type, self.imdb, self.tmdb, self.tvdb, self.season, self.episode)
		else:
			log_utils.log('Paused, but no scrobble due to being past mark watched percentage.', level=log_utils.LOGDEBUG)
##############################

class PlayNext(xbmc.Player):
	def __init__(self):
		super(PlayNext, self).__init__()
		self.enable_playnext = getSetting('enable.playnext') == 'true'
		self.stillwatching_count = int(getSetting('stillwatching.count'))
		self.playing_file = None
		self.providercache_hours = int(getSetting('cache.providers'))
		self.playnext_theme = getSetting('playnext.theme')

	def display_xml(self):
		try:
			self.playing_file = self.getPlayingFile()
		except:
			log_utils.error("Kodi did not return a playing file, killing playnext xml's")
			return
		if control.playlist.size() > 0 and control.playlist.getposition() != (control.playlist.size() - 1):
			if self.isStill_watching(): target = self.show_stillwatching_xml
			elif self.enable_playnext: target = self.show_playnext_xml
			else: return
			if self.playing_file != self.getPlayingFile(): return
			if not self.isPlayingVideo(): return
			if control.getCurrentWindowId != 12005: return
			target()

	def isStill_watching(self):
		# still_watching = float(control.playlist.getposition() + 1) / self.stillwatching_count # this does not work if you start playback on a divisible position with "stillwatching_count"
		playlistStart_position = playerWindow.getProperty('infinity.playlistStart_position')
		if playlistStart_position: still_watching = float(control.playlist.getposition() - int(playlistStart_position) + 1) / self.stillwatching_count
		else: still_watching = float(control.playlist.getposition() + 1) / self.stillwatching_count
		if still_watching == 0: return False
		return still_watching.is_integer()

	def getNext_meta(self):
		try:
			from urllib.parse import parse_qsl
			current_position = control.playlist.getposition()
			next_url = control.playlist[current_position + 1].getPath()
			# next_url=videodb://tvshows/titles/16/2/571?season=2&tvshowid=16 # library playback returns this
			params = dict(parse_qsl(next_url.replace('?', '')))
			next_meta = jsloads(params.get('meta')) if params.get('meta') else '' # not available for library playback
			return next_meta
		except:
			log_utils.error()
			return ''

	def show_playnext_xml(self):
		try:
			next_meta = self.getNext_meta()
			if not next_meta: raise Exception()
			if   self.playnext_theme == '2' and control.skin in ('skin.auramod'): theme = 'auraplaynext.xml'
			elif self.playnext_theme == '2' and control.skin not in ('skin.auramod'): theme = 'auraplaynext2.xml'
			elif self.playnext_theme == '1' and control.skin in ('skin.arctic.horizon.2'): theme = 'ahplaynext2.xml'
			elif self.playnext_theme == '1' and control.skin in ('skin.arctic.fuse'): theme = 'ahplaynext3.xml'
			elif self.playnext_theme == '1' and control.skin not in ('skin.arctic.horizon.2') and control.skin not in ('skin.arctic.fuse'):
				theme = 'ahplaynext2.xml'
			elif self.playnext_theme == '3': theme = 'ahplaynext4.xml'
			else: theme = 'playnext.xml'
			log_utils.log('Show Playnext Theme: %s' % theme, level=log_utils.LOGDEBUG)
			from resources.lib.windows.playnext import PlayNextXML
			window = PlayNextXML(theme, control.addonPath(control.addonId()), meta=next_meta)
			window.run()
			del window
			self.play_next_triggered = True
		except:
			log_utils.error()
			self.play_next_triggered = True

	def show_stillwatching_xml(self):
		try:
			next_meta = self.getNext_meta()
			if not next_meta: raise Exception()
			if   self.playnext_theme == '2' and control.skin in ('skin.auramod'): theme = 'auraplaynext_stillwatching.xml'
			elif self.playnext_theme == '2' and control.skin not in ('skin.auramod'): theme = 'auraplaynext_stillwatching2.xml'
			elif self.playnext_theme == '1' and control.skin in ('skin.arctic.horizon.2'): theme = 'ahplaynext_stillwatching2.xml'
			elif self.playnext_theme == '1' and control.skin in ('skin.arctic.fuse'): theme = 'ahplaynext_stillwatching3.xml'
			elif self.playnext_theme == '1' and control.skin not in ('skin.arctic.horizon.2') and control.skin not in ('skin.arctic.fuse'):
				theme = 'ahplaynext_stillwatching2.xml'
			elif self.playnext_theme == '3': theme = 'ahplaynext_stillwatching4.xml'
			else: theme = 'playnext_stillwatching.xml'
			from resources.lib.windows.playnext_stillwatching import StillWatchingXML
			window = StillWatchingXML(theme, control.addonPath(control.addonId()), meta=next_meta)
			window.run()
			del window
			self.play_next_triggered = True
		except:
			log_utils.error()
			self.play_next_triggered = True

	def prescrapeNext(self):
		try:
			if control.playlist.size() > 0 and control.playlist.getposition() != (control.playlist.size() - 1):
				from resources.lib.modules import sources
				from resources.lib.database import providerscache
				next_meta=self.getNext_meta()
				if not next_meta: raise Exception()
				title = next_meta.get('title')
				year = next_meta.get('year')
				imdb = next_meta.get('imdb')
				tmdb = next_meta.get('tmdb')
				tvdb = next_meta.get('tvdb')
				season = next_meta.get('season')
				episode = next_meta.get('episode')
				tvshowtitle = next_meta.get('tvshowtitle')
				premiered = next_meta.get('premiered')
				next_sources = providerscache.get(sources.Sources().getSources, self.providercache_hours, title, year, imdb, tmdb, tvdb, str(season), str(episode), tvshowtitle, premiered, next_meta, True)
				if not self.isPlayingVideo():
					return playerWindow.clearProperty('infinity.preResolved_nextUrl')
				sources.Sources().preResolve(next_sources, next_meta)
			else:
				playerWindow.clearProperty('infinity.preResolved_nextUrl')
		except:
			log_utils.error()
			playerWindow.clearProperty('infinity.preResolved_nextUrl')


class Subtitles:
	def get(self, title, year, imdb, season, episode, ck=True):
		try:
			import codecs
			import re, requests
			from resources.lib.modules.source_utils import seas_ep_filter
		except: return log_utils.error()
		try:
			langDict = {'Afrikaans': 'afr', 'Albanian': 'alb', 'Arabic': 'ara', 'Armenian': 'arm', 'Basque': 'baq', 'Bengali': 'ben',
			'Bosnian': 'bos', 'Breton': 'bre', 'Bulgarian': 'bul', 'Burmese': 'bur', 'Catalan': 'cat', 'Chinese': 'chi', 'Croatian': 'hrv',
			'Czech': 'cze', 'Danish': 'dan', 'Dutch': 'dut', 'English': 'eng', 'Esperanto': 'epo', 'Estonian': 'est', 'Finnish': 'fin',
			'French': 'fre', 'Galician': 'glg', 'Georgian': 'geo', 'German': 'ger', 'Greek': 'ell', 'Hebrew': 'heb', 'Hindi': 'hin',
			'Hungarian': 'hun', 'Icelandic': 'ice', 'Indonesian': 'ind', 'Italian': 'ita', 'Japanese': 'jpn', 'Kazakh': 'kaz', 'Khmer': 'khm',
			'Korean': 'kor', 'Latvian': 'lav', 'Lithuanian': 'lit', 'Luxembourgish': 'ltz', 'Macedonian': 'mac', 'Malay': 'may',
			'Malayalam': 'mal', 'Manipuri': 'mni', 'Mongolian': 'mon', 'Montenegrin': 'mne', 'Norwegian': 'nor', 'Occitan': 'oci',
			'Persian': 'per', 'Polish': 'pol', 'Portuguese': 'por,pob', 'Portuguese(Brazil)': 'pob,por', 'Romanian': 'rum', 'Russian': 'rus',
			'Serbian': 'scc', 'Sinhalese': 'sin', 'Slovak': 'slo', 'Slovenian': 'slv', 'Spanish': 'spa', 'Swahili': 'swa', 'Swedish': 'swe',
			'Syriac': 'syr', 'Tagalog': 'tgl', 'Tamil': 'tam', 'Telugu': 'tel', 'Thai': 'tha', 'Turkish': 'tur', 'Ukrainian': 'ukr', 'Urdu': 'urd'}
			codePageDict = {'ara': 'cp1256', 'ar': 'cp1256', 'ell': 'cp1253', 'el': 'cp1253', 'heb': 'cp1255',
									'he': 'cp1255', 'tur': 'cp1254', 'tr': 'cp1254', 'rus': 'cp1251', 'ru': 'cp1251'}
			openDict = {'chi': 'zh-cn', 'por': 'pt-pt', 'pob': 'pt-br'}
			quality = ['bluray', 'hdrip', 'brrip', 'bdrip', 'dvdrip', 'webrip', 'hdtv']

			langs = langDict[getSetting('subtitles.lang.1')].split(',')
			for i in langDict[getSetting('subtitles.lang.2')].split(','):
				if i not in langs: langs += [i]

			if ck:
				try: subLang = xbmc.Player().getSubtitles()
				except: subLang = ''
				if subLang == 'gre': subLang = 'ell'
				if subLang == langs[0]: 
					if getSetting('subtitles.notification') == 'true':
						if Player().isPlayback():
							control.sleep(1000)
							control.notification(message=getLS(32393) % subLang.upper(), time=5000)
					return log_utils.log(getLS(32393) % subLang.upper(), level=log_utils.LOGDEBUG)
				try:
					subLangs = xbmc.Player().getAvailableSubtitleStreams()
					if 'gre' in subLangs: subLangs[subLangs.index('gre')] = 'ell'
					subLang = [i for i in subLangs if i in langs][0]
				except: subLangs = subLang = ''
				if subLangs and subLang in langs:
					control.sleep(1000)
					xbmc.Player().setSubtitleStream(subLangs.index(subLang))
					if getSetting('subtitles.notification') == 'true':
						if Player().isPlayback():
							control.sleep(1000)
							control.notification(message=getLS(32394) % subLang.upper(), time=5000)
					return log_utils.log(getLS(32394) % subLang.upper(), level=log_utils.LOGDEBUG)

			user_agent = 'Infinity v' + control.getInfinityVersion()
			api_key = getSetting('opensubs.apikey')
			token = getSetting('opensubstoken')
			headers = {
				'Content-Type': 'application/json',
				'User-Agent': user_agent,
				'Api-Key': api_key,
				'Authorization': 'Bearer ' + token
			}
			base_url = 'https://api.opensubtitles.com/api/v1'
			timeout = 3.05

			langs = [openDict[i] if i in openDict else xbmc.convertLanguage(i, xbmc.ISO_639_1) for i in langs]
			if not (season is None or episode is None):
				params = {
					'episode_number': episode,
					'languages': ','.join(sorted(langs)),
					'parent_imdb_id': imdb.lstrip('t0'),
					'season_number': season,
				}
				fmt = ['hdtv']
			else:
				params = {'imdb_id': imdb.lstrip('t0'), 'languages': ','.join(sorted(langs))}
				try: vidPath = xbmc.Player().getPlayingFile()
				except: vidPath = ''
				fmt = re.split(r'\.|\(|\)|\[|\]|\s|\-', vidPath)
				fmt = [i.lower() for i in fmt]
				fmt = [i for i in fmt if i in quality]
			response = requests.get(base_url + '/subtitles', params=params, headers=headers, timeout=timeout)
			result = response.json()['data']

			filter = []
			for lang in langs:
				for item in result:
					ilang = item['attributes']['language'].lower()
					items = [
						{'language': ilang, 'file_id': i['file_id'], 'file_name': i['file_name']}
						for i in item['attributes']['files']
						if ilang == lang and i
					]
					if season: items = [i for i in items if seas_ep_filter(season, episode, i['file_name'])]
					filter += [i for i in items if not i in filter and any(x in i['file_name'].lower() for x in fmt)]
					filter += [i for i in items if not i in filter and any(x in i['file_name'].lower() for x in quality)]
					filter += [i for i in items if not i in filter and i['language'] == lang]
			if not filter: return control.notification(message=getLS(32395)) if ck else None

			try: lang = xbmc.convertLanguage(filter[0]['language'], xbmc.ISO_639_1) or filter[0]['language']
			except: lang = filter[0]['language']
			filename = filter[0]['file_name']
			if not filename.endswith('.srt'): filename += f".{lang}.srt"
			log_utils.log('downloaded subtitle=%s' % filename, level=log_utils.LOGDEBUG)

			file_id = filter[0]['file_id']
			response = requests.post(base_url + '/download', json={'file_id':file_id}, headers=headers, timeout=timeout)
			file_link = response.json()['link']
			response = requests.get(file_link, headers=headers, stream=True, timeout=timeout)
			content = response.content
			subtitle = control.transPath('special://temp/')
			subtitle = control.joinPath(subtitle, filename)
			log_utils.log('subtitle file = %s' % subtitle, level=log_utils.LOGDEBUG)

#			if getSetting('subtitles.utf') == 'true':
#				codepage = codePageDict.get(lang, '')
#				if codepage and not filter[0].get('SubEncoding', '').lower() == 'utf-8':
#					try:
#						content_encoded = codecs.decode(content, codepage)
#						content = codecs.encode(content_encoded, 'utf-8')
#					except: pass

			if ck:
				file = control.openFile(subtitle, 'w')
				file.write(content)
				file.close()
				xbmc.sleep(1000)
				xbmc.Player().setSubtitles(subtitle)
				if getSetting('subtitles.notification') == 'true':
					if Player().isPlayback():
						control.sleep(500)
						control.notification(title=filename, message=getLS(32191) % lang.upper())

			pattern = r'(^\d{2}:\d{2}:\d{2})'
			try: times = re.findall(pattern, content.decode('utf-8'), re.MULTILINE)
			except: times = re.findall(pattern, content, re.MULTILINE)
			total_time = xbmc.Player().getTotalTime()
			for i in times[-3::-1]: # last two sometimes translator credit
				h, m, s = str(i).split(':')
				final = int(h)*3600 + int(m)*60 + int(s)
				if final < total_time: break
			final = int(total_time - final)
			playerWindow.setProperty(f"infinity.sub_end.{imdb}", str(final))
		except: log_utils.error()


class Bookmarks:
	def __init__(self):
		self.markwatched_percentage = int(getSetting('markwatched.percent')) or 85
		self.traktCredentials = trakt.getTraktCredentialsInfo()

	def get(self, name, imdb=None, tmdb=None, tvdb=None, season=None, episode=None, year='0', runtime=None, ck=False):
		offset = '0'
		scrobbble = 'Local Bookmark'
		if getSetting('bookmarks') != 'true': return offset
		if self.traktCredentials and getSetting('resume.source') == '1':
			scrobbble = 'Trakt Scrobble'
			try:
				if not runtime or runtime == 'None': return offset # TMDB sometimes return None as string. duration pulled from kodi library if missing from meta
				progress = float(fetch_bookmarks(imdb, tmdb, tvdb, season, episode))
				offset = (progress / 100) * runtime # runtime vs. media_length can differ resulting in 10-30sec difference using Trakt scrobble, meta providers report runtime in full minutes
				seekable = (2 <= progress <= int(self.markwatched_percentage))
				if not seekable: return '0'
			except:
				log_utils.error()
				return '0'
		else:
			try:
				dbcon = database.connect(control.bookmarksFile)
				dbcur = dbcon.cursor()
				dbcur.execute('''CREATE TABLE IF NOT EXISTS bookmark (idFile TEXT, timeInSeconds TEXT, Name TEXT, year TEXT, UNIQUE(idFile));''')
				if not year or year == 'None': return offset
				years = [str(year), str(int(year)+1), str(int(year)-1)]
				match = dbcur.execute('''SELECT * FROM bookmark WHERE Name="%s" AND year IN (%s)''' % (name, ','.join(i for i in years))).fetchone() # helps fix random cases where trakt and imdb, or tvdb, differ by a year for eps
			except:
				log_utils.error()
				return offset
			finally:
				dbcur.close() ; dbcon.close()
			if not match: return offset
			offset = str(match[1])
		if ck: return offset
		minutes, seconds = divmod(float(offset), 60)
		hours, minutes = divmod(minutes, 60)
		label = '%02d:%02d:%02d' % (hours, minutes, seconds)
		label = getLS(32502) % label
		if getSetting('bookmarks.auto') == 'false':
			select = control.yesnocustomDialog(label, scrobbble, '', str(name), 'Cancel Playback', getLS(32503), getLS(32501))
			if select == 1: offset = '0'
			elif select == -1 or select == 2: offset = '-1'
		return offset

	def reset(self, current_time, media_length, name, year='0'):
		try:
			clear_local_bookmarks() # clear all infinity bookmarks from kodi database
			if getSetting('bookmarks') != 'true' or media_length == 0 or current_time == 0: return
			timeInSeconds = str(current_time)
			seekable = (int(current_time) > 180 and (current_time / media_length) < (abs(float(self.markwatched_percentage) / 100)))
			idFile = md5()
			try: [idFile.update(str(i)) for i in name]
			except: [idFile.update(str(i).encode('utf-8')) for i in name]
			try: [idFile.update(str(i)) for i in year]
			except: [idFile.update(str(i).encode('utf-8')) for i in year]
			idFile = str(idFile.hexdigest())
			control.makeFile(control.dataPath)
			dbcon = database.connect(control.bookmarksFile)
			dbcur = dbcon.cursor()
			dbcur.execute('''CREATE TABLE IF NOT EXISTS bookmark (idFile TEXT, timeInSeconds TEXT, Name TEXT, year TEXT, UNIQUE(idFile));''')
			years = [str(year), str(int(year) + 1), str(int(year) - 1)]
			dbcur.execute('''DELETE FROM bookmark WHERE Name="%s" AND year IN (%s)''' % (name, ','.join(i for i in years))) #helps fix random cases where trakt and imdb, or tvdb, differ by a year for eps
			if seekable:
				dbcur.execute('''INSERT INTO bookmark Values (?, ?, ?, ?)''', (idFile, timeInSeconds, name, year))
				minutes, seconds = divmod(float(timeInSeconds), 60)
				hours, minutes = divmod(minutes, 60)
				label = ('%02d:%02d:%02d' % (hours, minutes, seconds))
				message = getLS(32660)
				if getSetting('localnotify') == 'true':
					control.notification(title=name, message=message + '(' + label + ')')
			dbcur.connection.commit()
			try: dbcur.close ; dbcon.close()
			except: pass
		except:
			log_utils.error()

	def set_scrobble(self, current_time, media_length, media_type, imdb='', tmdb='', tvdb='', season='', episode=''):
		try:
			if media_length == 0: return
			percent = float((current_time / media_length)) * 100
			seekable = (int(current_time) > 180 and (percent < int(self.markwatched_percentage)))
			if seekable: trakt.scrobbleMovie(imdb, tmdb, percent) if media_type == 'movie' else trakt.scrobbleEpisode(imdb, tmdb, tvdb, season, episode, percent)
			if percent >= int(self.markwatched_percentage): trakt.scrobbleReset(imdb, tmdb, tvdb, season, episode, refresh=False)
		except:
			log_utils.error()
