"""
	Venom Add-on
"""

from datetime import datetime, timedelta
from json import dumps as jsdumps, loads as jsloads
import re
from threading import Thread
from urllib.parse import quote_plus, urlencode, parse_qsl, urlparse, urlsplit
from resources.lib.database import cache, fanarttv_cache, traktsync
from resources.lib.indexers.tmdb import TVshows as tmdb_indexer
from resources.lib.indexers.fanarttv import FanartTv
from resources.lib.modules import cleangenre
from resources.lib.modules import client
from resources.lib.modules import control
from resources.lib.modules import tools
from resources.lib.indexers import trakt
from resources.lib.modules import views
from resources.lib.modules.playcount import getTVShowIndicators, getEpisodeOverlay, getShowCount, getSeasonIndicators
from resources.lib.modules.player import Bookmarks

getLS = control.lang
getSetting = control.setting
KODI_VERSION = control.getKodiVersion()


class Episodes:
	def __init__(self, notifications=True):
		self.list = []
		self.count = getSetting('page.item.limit')
		self.lang = control.apiLanguage()['tmdb']
		self.notifications = notifications
		self.enable_fanarttv = getSetting('enable.fanarttv') == 'true'
		self.prefer_tmdbArt = getSetting('prefer.tmdbArt') == 'true'
		self.showunaired = getSetting('showunaired') == 'true'
		self.unairedcolor = control.getColor(getSetting('unaired.identify'))
		self.showspecials = getSetting('tv.specials') == 'true'
		self.highlight_color = control.getHighlightColor()
		self.date_time = datetime.now()
		self.today_date = (self.date_time).strftime('%Y-%m-%d')
		self.trakt_user = getSetting('trakt.username').strip()
		self.traktCredentials = trakt.getTraktCredentialsInfo()
		self.trakt_directProgressScrape = getSetting('trakt.directProgress.scrape') == 'true'
		self.trakt_progressFlatten = getSetting('trakt.progressFlatten') == 'true'
		self.trakt_link = 'https://api.trakt.tv'
		self.trakthistory_link = 'https://api.trakt.tv/users/me/history/shows?limit=%s&page=1' % self.count
		self.progress_link = 'https://api.trakt.tv/users/me/watched/shows'
		self.mycalendarRecent_link = 'https://api.trakt.tv/calendars/my/shows/date[30]/33/'
		self.mycalendarUpcoming_link = 'https://api.trakt.tv/calendars/my/shows/date[0]/33/'
		self.mycalendarPremiers_link = 'https://api.trakt.tv/calendars/my/shows/premieres/date[0]/33'
		self.traktunfinished_link = 'https://api.trakt.tv/sync/playback/episodes?limit=40'
		self.animecalendar_link = 'https://api.trakt.tv/calendars/all/shows/date[4]/7?genres=anime'
		self.tvmaze_link = 'https://api.tvmaze.com'
		self.added_link = 'https://api.tvmaze.com/schedule'
		self.calendar_link = 'https://api.tvmaze.com/schedule?date=%s'

	def get(self, tvshowtitle, year, imdb, tmdb, tvdb, meta, season=None, episode=None, create_directory=True):
		self.list = []
		def get_episodes(tvshowtitle, imdb, tmdb, tvdb, meta, season):
			episodes = cache.get(self.tmdb_list, 168, tvshowtitle, imdb, tmdb, tvdb, meta, season)
			if not episodes: pass
			elif episodes[0]['season_isAiring'] == 'true':
				if int(re.sub(r'[^0-9]', '', str(episodes[0]['next_episode_to_air']['air_date']))) <= int(re.sub(r'[^0-9]', '', str(self.today_date))):
					episodes = cache.get(self.tmdb_list, 3, tvshowtitle, imdb, tmdb, tvdb, meta, season)
			all_episodes.extend(episodes)
		try:
			if season is None and episode is None: # for "flatten" setting
				all_episodes = []
				threads = []
				append = threads.append
				if not isinstance(meta, dict): showSeasons = jsloads(meta)
				else: showSeasons = meta
				try:
					for i in showSeasons['seasons']:
						if not self.showspecials and i['season_number'] == 0: continue
						append(Thread(target=get_episodes, args=(tvshowtitle, imdb, tmdb, tvdb, meta, i['season_number'])))
					[i.start() for i in threads]
					[i.join() for i in threads]
					self.list = sorted(all_episodes, key=lambda k: (k['season'], k['episode']), reverse=False)
				except: 
					from resources.lib.modules import log_utils
					log_utils.error()
			elif season and episode: # for "trakt progress-non direct progress scrape" setting
				self.list = cache.get(self.tmdb_list, 168, tvshowtitle, imdb, tmdb, tvdb, meta, season)
				if not self.list: pass
				elif self.list[0]['season_isAiring'] == 'true':
					if int(re.sub(r'[^0-9]', '', str(self.list[0]['next_episode_to_air']['air_date']))) <= int(re.sub(r'[^0-9]', '', str(self.today_date))):
						self.list = cache.get(self.tmdb_list, 3, tvshowtitle, imdb, tmdb, tvdb, meta, season)
				num = [x for x, y in enumerate(self.list) if y['season'] == int(season) and y['episode'] == int(episode)][-1]
				self.list = [y for x, y in enumerate(self.list) if x >= num]
				if self.trakt_progressFlatten:
					all_episodes = []
					threads = []
					append = threads.append
					if not isinstance(meta, dict): showSeasons = jsloads(meta)
					else: showSeasons = meta
					try:
						for i in showSeasons['seasons']:
							if i['season_number'] <= int(season): continue
							append(Thread(target=get_episodes, args=(tvshowtitle, imdb, tmdb, tvdb, meta, i['season_number'])))
						if threads:
							[i.start() for i in threads]
							[i.join() for i in threads]
							self.list += all_episodes
						self.list = sorted(self.list, key=lambda k: (k['season'], k['episode']), reverse=False)
					except: 
						from resources.lib.modules import log_utils
						log_utils.error()
			else: # normal full episode list
				self.list = cache.get(self.tmdb_list, 168, tvshowtitle, imdb, tmdb, tvdb, meta, season)
				if not self.list: pass
				elif self.list[0]['season_isAiring'] == 'true':
					if int(re.sub(r'[^0-9]', '', str(self.list[0]['next_episode_to_air']['air_date']))) <= int(re.sub(r'[^0-9]', '', str(self.today_date))):
						self.list = cache.get(self.tmdb_list, 3, tvshowtitle, imdb, tmdb, tvdb, meta, season)
			if self.list is None: self.list = []
			if create_directory: self.episodeDirectory(self.list)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def unfinished(self, url, create_directory=True):
		self.list = []
		try:
			try: url = getattr(self, url + '_link')
			except: pass
			items = traktsync.fetch_bookmarks(imdb='', ret_all=True, ret_type='episodes')
			if trakt.getPausedActivity() > cache.timeout(self.trakt_episodes_list, url, self.trakt_user, self.lang, items):
				self.list = cache.get(self.trakt_episodes_list, 0, url, self.trakt_user, self.lang, items)
			else: self.list = cache.get(self.trakt_episodes_list, 720, url, self.trakt_user, self.lang, items)
			if self.list is None: self.list = []
			self.list = sorted(self.list, key=lambda k: k['paused_at'], reverse=True)
			if create_directory: self.episodeDirectory(self.list, unfinished=True, next=False)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def unfinishedManager(self):
		try:
			control.busy()
			list = self.unfinished(url='traktunfinished', create_directory=False)
			control.hide()
			from resources.lib.windows.traktepisodeprogress_manager import TraktEpisodeProgressManagerXML
			window = TraktEpisodeProgressManagerXML('traktepisodeprogress_manager.xml', control.addonPath(control.addonId()), results=list)
			selected_items = window.run()
			del window
			if selected_items:
				refresh = 'plugin.video.dradis' in control.infoLabel('Container.PluginName')
				trakt.scrobbleResetItems(imdb_ids=None, tvdb_dicts=selected_items, refresh=refresh, widgetRefresh=True)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			control.hide()

	def upcoming_progress(self, url):
		self.list = []
		try:
			try: url = getattr(self, url + '_link')
			except: pass
			if self.trakt_link in url and url == self.progress_link:
				if trakt.getProgressActivity() > cache.timeout(self.trakt_progress_list, url, self.trakt_user, self.lang, self.trakt_directProgressScrape, True):
					self.list = cache.get(self.trakt_progress_list, 0, url, self.trakt_user, self.lang, self.trakt_directProgressScrape, True)
				else: self.list = cache.get(self.trakt_progress_list, 12, url, self.trakt_user, self.lang, self.trakt_directProgressScrape, True)
				try:
					if not self.list: raise Exception()
					for i in range(len(self.list)):
						if 'premiered' not in self.list[i]: self.list[i]['premiered'] = ''
						if 'airtime' not in self.list[i]: self.list[i]['airtime'] = ''
					self.list = sorted(self.list, key=lambda k: (k['premiered'] if k['premiered'] else '3021-01-01', k['airtime'])) # "3021" date hack to force unknown premiered dates to bottom of list
				except: pass
			if self.list is None: self.list = []
			self.episodeDirectory(self.list, unfinished=False, next=False)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def clr_progress_cache(self, url):
		try: url = getattr(self, url + '_link')
		except: pass
		cache.remove(self.trakt_progress_list, url, self.trakt_user, self.lang, self.trakt_directProgressScrape)
		control.sleep(200)
		control.refresh()

	def calendar(self, url):
		self.list = []
		try:
			try: url = getattr(self, url + '_link')
			except: pass
			isTraktHistory = (url.split('&page=')[0] in self.trakthistory_link)
			if self.trakt_link in url and url == self.progress_link:
				if trakt.getProgressActivity() > cache.timeout(self.trakt_progress_list, url, self.trakt_user, self.lang, self.trakt_directProgressScrape):
					self.list = cache.get(self.trakt_progress_list, 0, url, self.trakt_user, self.lang, self.trakt_directProgressScrape)
				else: self.list = cache.get(self.trakt_progress_list, 12, url, self.trakt_user, self.lang, self.trakt_directProgressScrape)
				self.sort(type='progress')
				if self.list is None: self.list = []
				# place new season ep1's at top of list for 1 week
				prior_week = int(re.sub(r'[^0-9]', '', (self.date_time - timedelta(days=7)).strftime('%Y-%m-%d')))
				sorted_list = []
				top_items = [i for i in self.list if i['episode'] == 1 and i['premiered'] and (int(re.sub(r'[^0-9]', '', str(i['premiered']))) >= prior_week)]
				sorted_list.extend(top_items)
				sorted_list.extend([i for i in self.list if i not in top_items])
				self.list = sorted_list
			elif self.trakt_link in url and (url == self.mycalendarRecent_link) or (url == self.mycalendarUpcoming_link) or (url == self.mycalendarPremiers_link):
				if trakt.getActivity() > cache.timeout(self.trakt_episodes_list, url, self.trakt_user, self.lang):
					self.list = cache.get(self.trakt_episodes_list, 0, url, self.trakt_user, self.lang)
				else: self.list = cache.get(self.trakt_episodes_list, 1, url, self.trakt_user, self.lang)
				if (url == self.mycalendarUpcoming_link) or (url == self.mycalendarPremiers_link):
					if self.list:
						self.list = [i for i in self.list if int(re.sub(r'[^0-9]', '', str(i['premiered']).split('T')[0])) >= int(re.sub(r'[^0-9]', '', str(self.today_date)))]
						for i in range(len(self.list)): self.list[i]['calendar_unaired'] = True
						self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=False)
				elif url == self.mycalendarRecent_link:
					if self.list:
						self.list = [i for i in self.list if int(re.sub(r'[^0-9]', '', str(i['premiered']).split('T')[0])) <= int(re.sub(r'[^0-9]', '', str(self.today_date)))]
						for i in range(len(self.list)): self.list[i]['calendar_recent'] = True
						self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=True)
			elif self.trakt_link in url and url == self.animecalendar_link:
				self.list = cache.get(self.trakt_episodes_list, 1, url, self.trakt_user, self.lang)
				if self.list:
					for i in range(len(self.list)):
						if int(re.sub(r'[^0-9]', '', str(self.list[i]['premiered']).split('T')[0])) >= int(re.sub(r'[^0-9]', '', str(self.today_date))):
							self.list[i]['calendar_unaired'] = True
					self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=True)
			elif isTraktHistory:
				if trakt.getActivity() > cache.timeout(self.trakt_episodes_list, url, self.trakt_user, self.lang):
					self.list = cache.get(self.trakt_episodes_list, 0, url, self.trakt_user, self.lang)
				else: self.list = cache.get(self.trakt_episodes_list, 24, url, self.trakt_user, self.lang)
				if self.list:
					for i in range(len(self.list)): self.list[i]['traktHistory'] = True
					self.list = sorted(self.list, key=lambda k: k['lastplayed'], reverse=True)
			elif self.tvmaze_link in url and url == self.added_link:
				urls = [i['url'] for i in self.calendars(idx=False)][:5]
				self.list = []
				for url in urls: self.list += cache.get(self.tvmaze_list, 720, url, True)
			elif self.tvmaze_link in url:
				self.list = cache.get(self.tvmaze_list, 1, url, False)
			if self.list is None: self.list = []
			hasNext = True if isTraktHistory else False
			self.episodeDirectory(self.list, unfinished=False, next=hasNext)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def sort(self, type='shows'):
		try:
			if not self.list: return
			attribute = int(getSetting('sort.%s.type' % type))
			reverse = int(getSetting('sort.%s.order' % type)) == 1
			if attribute == 0: reverse = False # Sorting Order is not enabled when sort method is "Default"
			if attribute > 0:
				if attribute == 1:
					try: self.list = sorted(self.list, key=lambda k: re.sub(r'(^the |^a |^an )', '', k['tvshowtitle'].lower()), reverse=reverse)
					except: self.list = sorted(self.list, key=lambda k: k['title'].lower(), reverse=reverse)
				elif attribute == 2: self.list = sorted(self.list, key=lambda k: float(k['rating']), reverse=reverse)
				elif attribute == 3: self.list = sorted(self.list, key=lambda k: int(k['votes'].replace(',', '')), reverse=reverse)
				elif attribute == 4:
					for i in range(len(self.list)):
						if 'premiered' not in self.list[i]: self.list[i]['premiered'] = ''
					self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=reverse)
				elif attribute == 5:
					for i in range(len(self.list)):
						if 'added' not in self.list[i]: self.list[i]['added'] = ''
					self.list = sorted(self.list, key=lambda k: k['added'], reverse=reverse)
				elif attribute == 6:
					for i in range(len(self.list)):
						if 'lastplayed' not in self.list[i]: self.list[i]['lastplayed'] = ''
					self.list = sorted(self.list, key=lambda k: k['lastplayed'], reverse=reverse)
			elif reverse:
				self.list = list(reversed(self.list))
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def calendars(self, create_directory=True):
		m = getLS(32060).split('|')
		try: months = [(m[0], 'January'), (m[1], 'February'), (m[2], 'March'), (m[3], 'April'), (m[4], 'May'), (m[5], 'June'), (m[6], 'July'),
					(m[7], 'August'), (m[8], 'September'), (m[9], 'October'), (m[10], 'November'), (m[11], 'December')]
		except: months = []
		d = getLS(32061).split('|')
		try: days = [(d[0], 'Monday'), (d[1], 'Tuesday'), (d[2], 'Wednesday'), (d[3], 'Thursday'), (d[4], 'Friday'), (d[5], 'Saturday'), (d[6], 'Sunday')]
		except: days = []
		for i in range(0, 30):
			try:
				name = (self.date_time - timedelta(days=i))
				name = (getLS(32062) % (name.strftime('%A'), name.strftime('%d %B')))
				for m in months: name = name.replace(m[1], m[0])
				for d in days: name = name.replace(d[1], d[0])
				url = self.calendar_link % (self.date_time - timedelta(days=i)).strftime('%Y-%m-%d')
				self.list.append({'name': name, 'url': url, 'image': 'calendar.png', 'icon': 'DefaultYear.png', 'action': 'calendar'})
			except: pass
		if create_directory: self.addDirectory(self.list)
		return self.list

	def tmdb_list(self, tvshowtitle, imdb, tmdb, tvdb, meta, season):
		if not tmdb and (imdb or tvdb):
			try:
				result = cache.get(tmdb_indexer().IdLookup, 96, imdb, tvdb)
				tmdb = str(result.get('id')) if result.get('id') else ''
			except:
				if getSetting('debug.level') != '1': return
				from resources.lib.modules import log_utils
				return log_utils.log('tvshowtitle: (%s) missing tmdb_id: ids={imdb: %s, tmdb: %s, tvdb: %s}' % (tvshowtitle, imdb, tmdb, tvdb), __name__, log_utils.LOGDEBUG) # log TMDb shows that they do not have
		seasonEpisodes = tmdb_indexer().get_seasonEpisodes_meta(tmdb, season)
		if not seasonEpisodes: return
		if not isinstance(meta, dict): showSeasons = jsloads(meta)
		else: showSeasons = meta
		list = []
		unaired_count = 0
		for item in seasonEpisodes['episodes']:
			try:
				values = {}
				values.update(seasonEpisodes)
				values.update(item)
				values['tvshowtitle'] = tvshowtitle
				values['year'] = showSeasons.get('year')
				values['trailer'] = showSeasons.get('trailer')
				values['imdb'] = imdb or ''
				values['tvdb'] = tvdb or ''
				values['aliases'] = showSeasons.get('aliases', [])
				values['country_codes'] = showSeasons.get('country_codes', [])
				values['total_seasons'] = showSeasons.get('total_seasons')
				values['counts'] = showSeasons.get('counts')
				values['studio'] = showSeasons.get('studio')
				values['genre'] = showSeasons.get('genre')
				try: values['duration'] = int(showSeasons.get('duration')) # showSeasons already converted to seconds
				except: values['duration'] = ''
				values['mpaa'] = showSeasons.get('mpaa')
				values['status'] = showSeasons.get('status')
				values['unaired'] = ''
				try:
					if values['status'].lower() == 'ended': pass
					elif not values['premiered']:
						values['unaired'] = 'true'
						unaired_count += 1
						if not self.showunaired: continue
						pass
					elif int(re.sub(r'[^0-9]', '', str(values['premiered']))) > int(re.sub(r'[^0-9]', '', str(self.today_date))):
						values['unaired'] = 'true'
						unaired_count += 1
						if not self.showunaired: continue
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
				values['poster'] = item.get('poster') or showSeasons.get('poster')
				values['season_poster'] = item.get('season_poster') or showSeasons.get('season_poster')
				values['fanart'] = showSeasons.get('fanart')
				values['icon'] = showSeasons.get('icon')
				values['banner'] = showSeasons.get('banner')
				values['clearlogo'] = showSeasons.get('clearlogo')
				values['clearart'] = showSeasons.get('clearart')
				values['landscape'] = showSeasons.get('landscape')
				values['extended'] = True # used to bypass calling "super_info()", super_info() no longer used as of 4-12-21 so this could be removed.
				for k in ('episodes',): values.pop(k, None) # pop() keys from seasonEpisodes that are not needed anymore
				list.append(values)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		for i in range(0, len(list)): list[i].update({'season_isAiring': 'true' if unaired_count >0 else 'false'}) # update for if "season_isAiring", needed for season pack scraping
		if unaired_count >0:
			for i in range(0, len(list)): list[i].update({'next_episode_to_air': {'air_date': '2022-02-10', 'episode_number': 7}})
		return list

	def trakt_progress_list(self, url, user, lang, direct=False, upcoming=False):
		try:
			url += '?extended=full'
			result = trakt.getTrakt(url).json()
		except: return
		items = []
		progress_showunaired = getSetting('trakt.progress.showunaired') == 'true'
		for item in result:
			try:
				values = {} ; num_1 = 0
				if not upcoming and item['show']['status'].lower() == 'ended': # only chk ended cases for all watched otherwise airing today cases get dropped.
					for i in range(0, len(item['seasons'])):
						if item['seasons'][i]['number'] > 0: num_1 += len(item['seasons'][i]['episodes'])
					num_2 = int(item['show']['aired_episodes']) # trakt slow to update "aired_episodes" count on day item airs
					if num_1 >= num_2: continue
				season_sort = sorted(item['seasons'][:], key=lambda k: k['number'], reverse=False) # trakt sometimes places season0 at end and episodes out of order. So we sort it to be sure.
				values['snum'] = season_sort[-1]['number']
				episode = [x for x in season_sort[-1]['episodes'] if 'number' in x]
				episode = sorted(episode, key=lambda x: x['number'])
				values['enum'] = episode[-1]['number']
				values['added'] = item.get('show').get('updated_at')
				try: values['lastplayed'] = item.get('last_watched_at')
				except: values['lastplayed'] = ''
				values['tvshowtitle'] = item['show']['title']
				if not values['tvshowtitle']: continue
				ids = item.get('show', {}).get('ids', {})
				values['imdb'] = str(ids.get('imdb', '')) if ids.get('imdb') else ''
				values['tmdb'] = str(ids.get('tmdb', '')) if ids.get('tmdb') else ''
				values['tvdb'] = str(ids.get('tvdb', '')) if ids.get('tvdb') else ''
				try: values['trailer'] = control.trailer % item['show']['trailer'].split('v=')[1]
				except: values['trailer'] = ''
				try:
					airs = item['show']['airs']
					values['airday'] = airs.get('day', '')
					values['airtime'] = airs.get('time', '')[:5] # Trakt rarely, but does, include seconds in it's airtime.
					values['airzone'] = airs.get('timezone', '')
				except: pass
				items.append(values)
			except: pass
		try:
			hidden = traktsync.fetch_hidden_progress()
			hidden = [str(i['tvdb']) for i in hidden]
			items = [i for i in items if i['tvdb'] not in hidden] # removes hidden progress items
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

		def items_list(i):
			values = i
			imdb, tmdb, tvdb = i.get('imdb'), i.get('tmdb'), i.get('tvdb')
			if not tmdb and (imdb or tvdb):
				try:
					result = cache.get(tmdb_indexer().IdLookup, 96, imdb, tvdb)
					values['tmdb'] = str(result.get('id', '')) if result.get('id') else ''
				except:
					from resources.lib.modules import log_utils
					return log_utils.log('tvshowtitle: (%s) missing tmdb_id: ids={imdb: %s, tmdb: %s, tvdb: %s}' % (i['tvshowtitle'], imdb, tmdb, tvdb), __name__, log_utils.LOGDEBUG) # log TMDb shows that they do not have
			try:
				showSeasons = cache.get(tmdb_indexer().get_showSeasons_meta, 96, tmdb)
				if not showSeasons: return
				key = i['snum'] - 1 if showSeasons['seasons'][0]['season_number'] != 0 else i['snum']
				try: next_episode_num = i['enum'] + 1 if showSeasons['seasons'][key]['episode_count'] > i['enum'] else 1
				except: return
				next_season_num = i['snum'] if next_episode_num == i['enum'] + 1 else i['snum'] + 1
				if next_season_num > showSeasons['total_seasons']: return
				if not self.showspecials and next_season_num == 0: return
				seasonEpisodes = cache.get(tmdb_indexer().get_seasonEpisodes_meta, 96, tmdb, next_season_num)
				if not seasonEpisodes: return
				seasonEpisodes = dict((k,v) for k, v in iter(seasonEpisodes.items()) if v is not None and v != '') # remove empty keys so .update() doesn't over-write good meta with empty values.
				try: episode_meta = [x for x in seasonEpisodes.get('episodes') if x.get('episode') == next_episode_num][0] # to pull just the episode meta we need
				except: return
				if not episode_meta['plot']: episode_meta['plot'] = showSeasons['plot'] # some plots missing for eps so use season level plot
				values.update(showSeasons)
				values.update(seasonEpisodes)
				values.update(episode_meta)
				# if not self.trakt_progressFlatten or self.trakt_directProgressScrape:
					# for k in ('seasons', 'episodes', 'snum', 'enum'): values.pop(k, None) # pop() keys from showSeasons and seasonEpisodes that are not needed anymore
				for k in ('episodes', 'snum', 'enum'): values.pop(k, None) # pop() keys from showSeasons and seasonEpisodes that are not needed anymore

				try:
					if values.get('premiered') and i.get('airtime'): combined = '%sT%s' % (values['premiered'], values['airtime'])
					else: raise Exception()
					air_datetime_list = tools.convert_time(stringTime=combined, zoneFrom=i.get('airzone', ''), zoneTo='local', formatInput='%Y-%m-%dT%H:%M', formatOutput='%Y-%m-%dT%H:%M').split('T')
					air_date, air_time = air_datetime_list[0], air_datetime_list[1]
				except: air_date, air_time = values.get('premiered', '') if values.get('premiered') else '', i.get('airtime', '') if i.get('airtime') else ''
				values['unaired'] = ''
				if upcoming:
					values['traktUpcomingProgress'] = True
					try:
						if values['status'].lower() == 'ended': return
						elif not air_date: values['unaired'] = 'true'
						elif int(re.sub(r'[^0-9]', '', air_date)) > int(re.sub(r'[^0-9]', '', str(self.today_date))): values['unaired'] = 'true'
						elif int(re.sub(r'[^0-9]', '', air_date)) == int(re.sub(r'[^0-9]', '', str(self.today_date))):
							if air_time:
								time_now = (self.date_time).strftime('%X')
								if int(re.sub(r'[^0-9]', '', air_time)) > int(re.sub(r'[^0-9]', '', str(time_now))[:4]): values['unaired'] = 'true'
								else: return
							else: pass
						else: return
					except:
						from resources.lib.modules import log_utils
						log_utils.error('tvshowtitle = %s' % i['tvshowtitle'])
				else:
					try:
						if values['status'].lower() == 'ended': pass
						elif not air_date:
							values['unaired'] = 'true'
							if not progress_showunaired: return
						elif int(re.sub(r'[^0-9]', '', air_date)) > int(re.sub(r'[^0-9]', '', str(self.today_date))):
							values['unaired'] = 'true'
							if not progress_showunaired: return
						elif int(re.sub(r'[^0-9]', '', air_date)) == int(re.sub(r'[^0-9]', '', str(self.today_date))):
							if air_time:
								time_now = (self.date_time).strftime('%X')
								if int(re.sub(r'[^0-9]', '', air_time)) > int(re.sub(r'[^0-9]', '', str(time_now))[:4]):
									values['unaired'] = 'true'
									if not progress_showunaired: return
							else: pass
					except:
						from resources.lib.modules import log_utils
						log_utils.error('tvshowtitle = %s' % i['tvshowtitle'])
				if not direct: values['action'] = 'episodes' # for direct progress scraping
				values['traktProgress'] = True # for direct progress scraping and multi episode watch counts indicators
				values['extended'] = True # used to bypass calling "super_info()", super_info() no longer used as of 4-12-21 so this could be removed.
				if self.enable_fanarttv:
					extended_art = fanarttv_cache.get(FanartTv().get_tvshow_art, 336, tvdb)
					if extended_art: values.update(extended_art)
				self.list.append(values)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		threads = []
		append = threads.append
		for i in items:
			append(Thread(target=items_list, args=(i,)))
		[i.start() for i in threads]
		[i.join() for i in threads]
		return self.list

	def trakt_list(self, url, user):
		itemlist = []
		try:
			for i in re.findall(r'date\[(\d+)\]', url): url = url.replace('date[%s]' % i, (self.date_time - timedelta(days=int(i))).strftime('%Y-%m-%d'))
			q = dict(parse_qsl(urlsplit(url).query))
			q.update({'extended': 'full'})
			q = (urlencode(q)).replace('%2C', ',')
			u = url.replace('?' + urlparse(url).query, '') + '?' + q
			items = trakt.getTraktAsJson(u)
		except: return
		try:
			q = dict(parse_qsl(urlsplit(url).query)) # should not need this a 2nd time
			if int(q['limit']) != len(items): raise Exception()
			q.update({'page': str(int(q['page']) + 1)})
			q = (urlencode(q)).replace('%2C', ',')
			next = url.replace('?' + urlparse(url).query, '') + '?' + q
		except: next = ''

		for item in items:
			try:
				if 'show' not in item or 'episode' not in item: continue
				title = item['episode']['title']
				if not title: continue
				try:
					season = item['episode']['season']
					episode = item['episode']['number']
				except: continue
				if not self.showspecials and season == 0: continue
				tvshowtitle = item.get('show').get('title')
				if not tvshowtitle: continue
				year = str(item.get('show').get('year'))
				try: progress = item['progress']
				except: progress = None
				ids = item.get('show', {}).get('ids', {})
				imdb = str(ids.get('imdb', '')) if ids.get('imdb') else ''
				tmdb = str(ids.get('tmdb', '')) if ids.get('tmdb') else ''
				tvdb = str(ids.get('tvdb', '')) if ids.get('tvdb') else ''
				episodeIDS = item.get('episode').get('ids', {}) # not used anymore
				premiered = item.get('episode').get('first_aired') #leave timestamp for better sort of same day items
				added = item['episode']['updated_at'] or item.get('show').get('updated_at', '')
				try: lastplayed = item.get('watched_at', '')
				except: lastplayed = ''
				paused_at = item.get('paused_at', '')
				studio = item.get('show').get('network')
				try: genre = ' / '.join([x.title() for x in item.get('show', {}).get('genres')]) or 'NA'
				except: genre = 'NA'
				try: duration = int(item['episode']['runtime']) * 60
				except:
					try:duration = int(item.get('show').get('runtime')) * 60
					except: duration = ''
				rating = str(item.get('episode').get('rating'))
				votes = str(format(int(item.get('episode').get('votes')),',d'))
				mpaa = item.get('show').get('certification')
				plot = item['episode']['overview'] or item['show']['overview']
				if self.lang != 'en':
					try:
						trans_item = trakt.getTVShowTranslation(imdb, lang=self.lang, season=season, episode=episode, full=True)
						title = trans_item.get('title') or title
						plot = trans_item.get('overview') or plot
						tvshowtitle = trakt.getTVShowTranslation(imdb, lang=self.lang) or tvshowtitle
					except:
						from resources.lib.modules import log_utils
						log_utils.error()
				try: trailer = control.trailer % item['show']['trailer'].split('v=')[1]
				except: trailer = ''
				values = {'title': title, 'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered,
							'added': added, 'lastplayed': lastplayed, 'progress': progress, 'paused_at': paused_at, 'status': 'Continuing',
							'studio': studio, 'genre': genre, 'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa, 'plot': plot,
							'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'trailer': trailer, 'episodeIDS': episodeIDS, 'next': next}
				try:
					airs = item['show']['airs']
					values['airday'] = airs.get('day', '')
					values['airtime'] = airs.get('time', '')
					values['airzone'] = airs.get('timezone', '')
				except: pass
				itemlist.append(values)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		return itemlist

	def trakt_episodes_list(self, url, user, lang, items=None, direct=True):
		self.list = []
		if not items: items = self.trakt_list(url, user)
		def items_list(i):
			values = i
			tmdb, tvdb = i['tmdb'], i['tvdb']
			try:
				seasonEpisodes = cache.get(tmdb_indexer().get_seasonEpisodes_meta, 96, tmdb, i['season'])
				if not seasonEpisodes: return
				try: episode_meta = [x for x in seasonEpisodes.get('episodes') if x.get('episode') == i['episode']][0] # to pull just the episode meta we need
				except: return
				if 'premiered' in values and values.get('premiered'):
					episode_meta.pop('premiered') # prefer Trakt premiered because TMDb is fucked for some shows like Family Law off by months
					seasonEpisodes.pop('premiered') # this is series premiered so pop
				values.update(seasonEpisodes)
				values.update(episode_meta)
				for k in ('episodes',): values.pop(k, None) # pop() keys from seasonEpisodes that are not needed anymore
				try: # used for fanart fetch since not available in seasonEpisodes request
					art = cache.get(tmdb_indexer().get_art, 96, tmdb)
					values.update(art)
				except: pass
				if self.enable_fanarttv:
					extended_art = fanarttv_cache.get(FanartTv().get_tvshow_art, 336, tvdb)
					if extended_art: values.update(extended_art)
				values['extended'] = True # used to bypass calling "super_info()", super_info() no longer used as of 4-12-21 so this could be removed.
				if not direct: values['action'] = 'episodes'
				self.list.append(values)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		threads = []
		append = threads.append
		for i in items:
			append(Thread(target=items_list, args=(i,)))
		[i.start() for i in threads]
		[i.join() for i in threads]
		return self.list

	def tvmaze_list(self, url, limit):
		try:
			result = client.request(url, error=True)
			result = jsloads(result)
		except: return
		items = []
		for item in result:
			values = {}
			try:
				if not item['show']['language']: continue
				if 'english' not in item['show']['language'].lower(): continue
				if limit and 'scripted' not in item['show']['type'].lower(): continue
				values['title'] = item.get('name')
				values['season'] = item['season']
				if not values['season']: continue
				if not self.showspecials and values['season'] == 0: continue
				values['episode'] = item['number']
				if values['episode'] is None: continue
				values['premiered'] = item.get('airdate', '')
				try: values['year'] = str(item.get('show', {}).get('premiered', ''))[:4] # shows year
				except: values['year'] = ''
				values['tvshowtitle'] = item.get('show', {}).get('name')
				ids = item.get('show', {}).get('externals', {})
				imdb = str(ids.get('imdb', '')) if ids.get('imdb') else ''
				tmdb = '' # TVMaze does not have tmdb in their api
				tvdb = str(ids.get('thetvdb', '')) if ids.get('thetvdb') else ''
				try: values['poster'] = item['show']['image']['original']
				except: values['poster'] = ''
				try: values['thumb'] = item['image']['original']
				except: values['thumb'] = ''
				if not values['thumb']: values['thumb'] = values['poster']
				studio = item.get('show').get('webChannel') or item.get('show').get('network')
				values['studio'] = studio.get('name') or ''
				values['genre'] = []
				for i in item['show']['genres']: values['genre'].append(i.title())
				try: values['duration'] = int(item.get('show', {}).get('runtime', '')) * 60
				except: values['duration'] = ''
				values['rating'] = str(item.get('show', {}).get('rating', {}).get('average', ''))
				try: values['status'] = str(item.get('show', {}).get('status', ''))
				except: values['status'] = 'Continuing'
				try:
					plot = item.get('show', {}).get('summary', '')
					values['plot'] = re.sub(r'<.+?>|</.+?>|\n', '', plot)
				except: values['plot'] = ''
				try: values['airday'] = item['show']['schedule']['days'][0]
				except: values['airday'] = ''
				values['airtime'] = item['airtime'] or ''
				try: values['airzone'] = item['show']['network']['country']['timezone']
				except: values['airzone'] = ''
				values['extended'] = True
				values['ForceAirEnabled'] = True
				if getSetting('tvshows.calendar.extended') == 'true':
					if imdb: 
						trakt_ids = trakt.IdLookup('imdb', imdb, 'show')
						if trakt_ids:
							if not tvdb: tvdb = str(trakt_ids.get('tvdb', '')) if trakt_ids.get('tvdb') else ''
							tmdb = str(trakt_ids.get('tmdb', '')) if trakt_ids.get('tmdb') else ''
					elif not imdb and tvdb:
						trakt_ids = trakt.IdLookup('tvdb', tvdb, 'show')
						if trakt_ids:
							imdb = str(trakt_ids.get('imdb', '')) if trakt_ids.get('imdb') else ''
							tmdb = str(trakt_ids.get('tmdb', '')) if trakt_ids.get('tmdb') else ''
					if not values['poster'] or not values['thumb']:
						try:
							art = cache.get(tmdb_indexer().get_art, 96, tmdb)
							if not values['poster']: values['poster'] = art['poster3'] or ''
							if not values['thumb']: values['thumb'] = art['fanart3'] or ''
						except: pass
					if not values['thumb']: values['thumb'] = values['poster']
					values['fanart'] = values['thumb']
					values['season_poster'] = values['poster']
					if self.enable_fanarttv:
						extended_art = fanarttv_cache.get(FanartTv().get_tvshow_art, 336, tvdb)
						if extended_art: values.update(extended_art)
				values['imdb'] = imdb
				values['tmdb'] = tmdb
				values['tvdb'] = tvdb
				items.append(values)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		return items

	def episodeDirectory(self, items, unfinished=False, next=True, playlist=False):
		from sys import argv # some functions like ActivateWindow() throw invalid handle less this is imported here.
		if not items: # with reuselanguageinvoker on an empty directory must be loaded, do not use sys.exit()
			control.hide() ; control.notification(title=32326, message=33049)
		sysaddon, syshandle = 'plugin://plugin.video.dradis/', int(argv[1])
		is_widget = 'plugin' not in control.infoLabel('Container.PluginName')
		if not is_widget and not playlist: control.playlist.clear()
		settingFanart = getSetting('fanart') == 'true'
		addonPoster, addonFanart, addonBanner = control.addonPoster(), control.addonFanart(), control.addonBanner()
		try: traktProgress = False if 'traktProgress' not in items[0] else True
		except: traktProgress = False
		if traktProgress and self.trakt_directProgressScrape: progressMenu = getLS(32016)
		else: progressMenu = getLS(32015)
		if traktProgress: isMultiList = True
		else:
			try: multi = [i['tvshowtitle'] for i in items]
			except: multi = []
			isMultiList = True if len([x for y, x in enumerate(multi) if x not in multi[:y]]) > 1 else False
			try:
				if '/users/me/history/' in items[0]['next']: isMultiList = True
			except: pass
		upcoming_prependDate = getSetting('trakt.UpcomingProgress.prependDate') == 'true'
		try: sysaction = items[0]['action']
		except: sysaction = ''
		multi_unwatchedEnabled = getSetting('multi.unwatched.enabled') == 'true'
		try: airEnabled = getSetting('tvshows.air.enabled') if 'ForceAirEnabled' not in items[0] else 'true'
		except: airEnabled = 'false'
		play_mode = getSetting('play.mode')
		rescrape_useDefault = getSetting('rescrape.default') == 'true'
		rescrape_method = getSetting('rescrape.default2')
		enable_playnext = getSetting('enable.playnext') == 'true'
		indicators = getTVShowIndicators() # gives breakdown of (season, ep) watched
		isFolder = False if sysaction != 'episodes' else True
		if airEnabled == 'true':
			airZone, airLocation = getSetting('tvshows.air.zone'), getSetting('tvshows.air.location')
			airFormat, airFormatDay = getSetting('tvshows.air.format'), getSetting('tvshows.air.day')
			airFormatTime, airBold = getSetting('tvshows.air.time'), getSetting('tvshows.air.bold')
			airLabel = getLS(35032)
		if play_mode == '1' or enable_playnext: playbackMenu = getLS(32063)
		else: playbackMenu = getLS(32064)
		if trakt.getTraktIndicatorsInfo(): 
			watchedMenu, unwatchedMenu = getLS(32068), getLS(32069)
		else:
			watchedMenu, unwatchedMenu = getLS(32066), getLS(32067)
		traktManagerMenu, playlistManagerMenu, queueMenu = getLS(32070), getLS(35522), getLS(32065)
		tvshowBrowserMenu, addToLibrary = getLS(32071), getLS(32551)
		rescrapeMenu, progressRefreshMenu, clearSourcesMenu = getLS(32185), getLS(32194), getLS(32611) % 'red'
		if playlist: listitems = [] ; append = listitems.append

		for i in items:
			try:
				tvshowtitle, title, imdb, tmdb, tvdb = i.get('tvshowtitle'), i.get('title'), i.get('imdb', ''), i.get('tmdb', ''), i.get('tvdb', '')
				year, season, episode, premiered = i.get('year', ''), i.get('season'), i.get('episode'), i.get('premiered', '')
				trailer, runtime = i.get('trailer', ''), i.get('duration')
				if 'label' not in i: i['label'] = title
				if (not i['label'] or i['label'] == '0'): label = '%sx%02d . %s %s' % (season, int(episode), 'Episode', episode)
				else: label = '%sx%02d . %s' % (season, int(episode), i['label'])
				if isMultiList: label = '[COLOR %s]%s[/COLOR] - %s' % (self.highlight_color, tvshowtitle, label)
				try: labelProgress = label + '[COLOR %s]  [%s][/COLOR]' % (self.highlight_color, str(round(float(i['progress']), 1)) + '%')
				except: labelProgress = label
				try:
					if i['unaired'] == 'true': labelProgress = '[COLOR %s][I]%s[/I][/COLOR]' % (self.unairedcolor, labelProgress)
				except: pass
				if i.get('traktHistory') is True: # uses Trakt lastplayed in utc
					try:
						air_datetime = tools.convert_time(stringTime=i.get('lastplayed', ''), zoneFrom='utc', zoneTo='local', formatInput='%Y-%m-%dT%H:%M:%S.000Z', formatOutput='%b %d %Y %I:%M %p', remove_zeroes=True)
						labelProgress = labelProgress + '[COLOR %s]  [%s][/COLOR]' % (self.highlight_color, air_datetime)
					except: pass
				if upcoming_prependDate and (i.get('traktUpcomingProgress') is True): # uses TMDb premiered
					try:
						if premiered and i.get('airtime'): combined='%sT%s' % (premiered, i.get('airtime', ''))
						else: raise Exception()
						air_datetime = tools.convert_time(stringTime=combined, zoneFrom=i.get('airzone', ''), zoneTo='local', formatInput='%Y-%m-%dT%H:%M', formatOutput='%b %d %I:%M %p', remove_zeroes=True)
						labelProgress = labelProgress + '[COLOR %s]  [%s][/COLOR]' % (self.highlight_color, air_datetime)
					except: pass
				if i.get('calendar_unaired') is True: # uses Trakt premiered in utc
					try:
						air_datetime = tools.convert_time(stringTime=premiered, zoneFrom='utc', zoneTo='local', formatInput='%Y-%m-%dT%H:%M:%S.000Z', formatOutput='%b %d %I:%M %p', remove_zeroes=True)
						labelProgress = labelProgress + '[COLOR %s]  [%s][/COLOR]' % (self.highlight_color, air_datetime)
						new_date = tools.convert_time(stringTime=premiered, zoneFrom='utc', zoneTo='local', formatInput='%Y-%m-%dT%H:%M:%S.000Z', formatOutput='%Y-%m-%d')
						i.update({'premiered': new_date}) # adjust for Trakt utc
					except: pass
				if i.get('calendar_recent') is True: # uses Trakt premiered in utc
					try:
						new_date = tools.convert_time(stringTime=premiered, zoneFrom='utc', zoneTo='local', formatInput='%Y-%m-%dT%H:%M:%S.000Z', formatOutput='%Y-%m-%d')
						i.update({'premiered': new_date}) # adjust for Trakt utc
					except: pass
				systitle, systvshowtitle, syspremiered = quote_plus(title), quote_plus(tvshowtitle), quote_plus(premiered)
				meta = dict((k, v) for k, v in iter(i.items()) if v is not None and v != '')
				meta.update({'code': imdb, 'imdbnumber': imdb, 'mediatype': 'episode', 'tag': [imdb, tmdb]}) # "tag" and "tagline" for movies only, but works in my skin mod so leave
				try: meta.update({'genre': cleangenre.lang(meta['genre'], self.lang)})
				except: pass
				try: meta.update({'title': i['label']})
				except: pass
				if airEnabled == 'true':
					air = [] ; airday = None ; airtime = None
					if 'airday' in meta and not meta['airday'] is None and meta['airday'] != '': 
						airday = meta['airday']
					if 'airtime' in meta and not meta['airtime'] is None and meta['airtime'] != '':
						airtime = meta['airtime']
						if 'airzone' in meta and not meta['airzone'] is None and meta['airzone'] != '':
							if airZone == '1': zoneTo = meta['airzone']
							elif airZone == '2': zoneTo = 'utc'
							else: zoneTo = 'local'
							if airFormatTime == '1': formatOutput = '%I:%M'
							elif airFormatTime == '2': formatOutput = '%I:%M %p'
							else: formatOutput = '%H:%M'
							abbreviate = airFormatDay == '1'
							airtime = tools.convert_time(stringTime=airtime, stringDay=airday, zoneFrom=meta['airzone'], zoneTo=zoneTo, abbreviate=abbreviate, formatOutput=formatOutput)
							if airday: airday, airtime = airtime[1], airtime[0]
					if airday: air.append(airday)
					if airtime: air.append(airtime)
					if len(air) > 0:
						if airFormat == '0': air = airtime
						elif airFormat == '1': air = airday
						elif airFormat == '2': air = air = ' '.join(air)
#						if airLocation == '0' or airLocation == '1': air = '[COLOR skyblue][%s][/COLOR]' % air
						if airLocation == '0' or airLocation == '1': air = f"[COLOR {self.highlight_color}]{air}[/COLOR]"
						if airBold == 'true': air = '[B]%s[/B]' % str(air)
						if airLocation == '0': labelProgress = '%s %s' % (air, labelProgress)
						elif airLocation == '1': labelProgress = '%s %s' % (labelProgress, air)
						elif airLocation == '2': meta['plot'] = '%s%s\r\n%s' % (airLabel, air, meta['plot'])
						elif airLocation == '3': meta['plot'] = '%s\r\n%s%s' % (meta['plot'], airLabel, air)

				if self.prefer_tmdbArt:
					poster = meta.get('poster3') or meta.get('poster') or meta.get('poster2') or addonPoster
					clearlogo = meta.get('tmdblogo') or meta.get('clearlogo') or ''
				else:
					poster = meta.get('poster2') or meta.get('poster3') or meta.get('poster') or addonPoster
					clearlogo = meta.get('clearlogo') or meta.get('tmdblogo') or ''
				season_poster = meta.get('season_poster') or poster
				fanart = ''
				if settingFanart:
					if self.prefer_tmdbArt: fanart = meta.get('fanart3') or meta.get('fanart') or meta.get('fanart2') or addonFanart
					else: fanart = meta.get('fanart2') or meta.get('fanart3') or meta.get('fanart') or addonFanart
				landscape = meta.get('landscape') or fanart
				thumb = meta.get('thumb') or landscape or fanart or season_poster
				icon = meta.get('icon') or season_poster or poster
				banner = meta.get('banner') or addonBanner
				art = {}
				art.update({'poster': season_poster, 'tvshow.poster': poster, 'season.poster': season_poster, 'fanart': fanart, 'icon': icon, 'thumb': thumb, 'banner': banner,
						'clearlogo': clearlogo, 'tvshow.clearlogo': clearlogo, 'clearart': meta.get('clearart', ''), 'tvshow.clearart': meta.get('clearart', ''), 'landscape': thumb})
				for k in ('metacache', 'poster2', 'poster3', 'fanart2', 'fanart3', 'banner2', 'banner3', 'trailer'): meta.pop(k, None)
				meta.update({'poster': poster, 'fanart': fanart, 'banner': banner, 'thumb': thumb, 'icon': icon, 'clearlogo': clearlogo})
				sysmeta, sysart, syslabelProgress = quote_plus(jsdumps(meta)), quote_plus(jsdumps(art)), quote_plus(labelProgress)
				url = '%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s' % (
										sysaddon, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, syspremiered, sysmeta)
				sysurl = quote_plus(url)
####-Context Menu and Overlays-####
				cm = []
				try:
					watched = getEpisodeOverlay(indicators, imdb, tvdb, season, episode) == '5'
					if self.traktCredentials:
						cm.append((traktManagerMenu, 'RunPlugin(%s?action=tools_traktManager&name=%s&imdb=%s&tvdb=%s&season=%s&episode=%s&watched=%s&unfinished=%s)' % (sysaddon, systvshowtitle, imdb, tvdb, season, episode, watched, unfinished)))
					if watched:
						meta.update({'playcount': 1, 'overlay': 5})
						cm.append((unwatchedMenu, 'RunPlugin(%s?action=playcount_Episode&name=%s&imdb=%s&tvdb=%s&season=%s&episode=%s&query=4)' % (sysaddon, systvshowtitle, imdb, tvdb, season, episode)))
						# meta.update({'lastplayed': trakt.watchedShowsTime(tvdb, season, episode)}) # no skin support
					else:
						meta.update({'playcount': 0, 'overlay': 4})
						cm.append((watchedMenu, 'RunPlugin(%s?action=playcount_Episode&name=%s&imdb=%s&tvdb=%s&season=%s&episode=%s&query=5)' % (sysaddon, systvshowtitle, imdb, tvdb, season, episode)))
				except: pass
				Folderurl = '%s?action=episodes&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&meta=%s&season=%s&episode=%s&art=%s' % (sysaddon, systvshowtitle, year, imdb, tmdb, tvdb, sysmeta, season, episode, sysart)
				if traktProgress:
					cm.append((progressRefreshMenu, 'RunPlugin(%s?action=episodes_clrProgressCache&url=progress)' % sysaddon))
				if isFolder:
					if traktProgress:
						cm.append((progressMenu, 'PlayMedia(%s)' % url))
					url = '%s?action=episodes&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&meta=%s&season=%s&episode=%s&art=%s' % (sysaddon, systvshowtitle, year, imdb, tmdb, tvdb, sysmeta, season, episode, sysart)
				if not isFolder:
					cm.append((playbackMenu, 'RunPlugin(%s?action=alterSources&url=%s&meta=%s)' % (sysaddon, sysurl, sysmeta)))
				cm.append((playlistManagerMenu, 'RunPlugin(%s?action=playlist_Manager&name=%s&url=%s&meta=%s&art=%s)' % (sysaddon, syslabelProgress, sysurl, sysmeta, sysart)))
				cm.append((queueMenu, 'RunPlugin(%s?action=playlist_QueueItem&name=%s)' % (sysaddon, syslabelProgress)))
				cm.append((addToLibrary, 'RunPlugin(%s?action=library_tvshowToLibrary&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s)' % (sysaddon, systvshowtitle, year, imdb, tmdb, tvdb)))
				if isMultiList:
					cm.append((tvshowBrowserMenu, 'Container.Update(%s?action=seasons&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&art=%s,return)' % (sysaddon, systvshowtitle, year, imdb, tmdb, tvdb, sysart)))
					# cm.append((tvshowBrowserMenu, 'Container.Update(%s?action=episodes&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&meta=%s,return)' % (sysaddon, systvshowtitle, year, imdb, tmdb, tvdb, sysmeta)))

				if not isFolder:
					if traktProgress: cm.append((progressMenu, 'Container.Update(%s)' % Folderurl))
					if not rescrape_useDefault:
						cm.append(('Rescrape Options...', 'PlayMedia(%s?action=rescrapeMenu&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s)' % (
											sysaddon, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, syspremiered, sysmeta)))
					else:
						if rescrape_method == '0':
							cm.append((rescrapeMenu, 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&rescrape=true&select=1)' % (
											sysaddon, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, syspremiered, sysmeta)))
						if rescrape_method == '1':
							cm.append((rescrapeMenu, 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&rescrape=true&select=0)' % (
											sysaddon, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, syspremiered, sysmeta)))
						if rescrape_method == '2':
							cm.append((rescrapeMenu, 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&rescrape=true&all_providers=true&select=1)' % (
											sysaddon, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, syspremiered, sysmeta)))
						if rescrape_method == '3':
							cm.append((rescrapeMenu, 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&rescrape=true&all_providers=true&select=0)' % (
											sysaddon, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, syspremiered, sysmeta)))
				cm.append((clearSourcesMenu, 'RunPlugin(%s?action=cache_clearSources)' % sysaddon))
				cm.append(('[COLOR red][B]Dradis Settings[/B][/COLOR]', 'RunPlugin(%s?action=tools_openSettings)' % sysaddon))
####################################
				if trailer: meta.update({'trailer': trailer}) # removed temp so it's not passed to CM items, only infoLabels for skin
				else: meta.update({'trailer': '%s?action=play_Trailer&type=%s&name=%s&year=%s&imdb=%s' % (sysaddon, 'show', syslabelProgress, year, imdb)})
				item = control.item(label=labelProgress, offscreen=True)
				item.setArt(art)
				if isMultiList and multi_unwatchedEnabled:
					if 'ForceAirEnabled' not in i:
						try:
							try: count = getShowCount(getSeasonIndicators(imdb, tvdb)[1], imdb, tvdb) # if indicators and no matching imdb_id in watched items then it returns None and we use TMDb meta to avoid Trakt request
							except: count = None
							if count:
								item.setProperties({'WatchedEpisodes': str(count['watched']), 'UnWatchedEpisodes': str(count['unwatched'])})
								item.setProperties({'TotalSeasons': str(meta.get('total_seasons', '')), 'TotalEpisodes': str(count['total'])})
								item.setProperties({'watchedprogress': str(int(count['watched'] * 100 / count['total']))})
							else:
								if KODI_VERSION < 20: item.setProperties({'WatchedEpisodes': '0', 'UnWatchedEpisodes': str(meta.get('total_aired_episodes', ''))}) # for shows never watched
								else: item.setProperties({'UnWatchedEpisodes': str(meta.get('total_aired_episodes', ''))}) # for shows never watched
								item.setProperties({'TotalSeasons': str(meta.get('total_seasons', '')), 'TotalEpisodes': str(meta.get('total_aired_episodes', ''))})
						except:
							from resources.lib.modules import log_utils
							log_utils.error()
				item.setProperty('IsPlayable', 'true')
				item.setProperty('tvshow.tmdb_id', tmdb)
				if is_widget: item.setProperty('isDradis_widget', 'true')
				blabel = tvshowtitle + ' S%02dE%02d' % (int(season), int(episode))

				if not i.get('unaired') == 'true':
					if not runtime: runtime = 45 * 60 # convert to seconds, inaccurate comment "resumetime and runtime are both in minutes"
					resumetime = Bookmarks().get(name=blabel, imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, year=str(year), runtime=runtime, ck=True)
					# item.setProperty('TotalTime', str(runtime)) # Adding this property causes the Kodi bookmark CM items to be added
					item.setProperty('ResumeTime', str(resumetime)) if KODI_VERSION < 20 else item.getVideoInfoTag().setResumePoint(float(resumetime))
					try:
						watched_percent = round(float(resumetime) / float(runtime) * 100, 1) # resumetime and runtime are both in minutes
						item.setProperties({'percentplayed': str(watched_percent), 'watchedprogress': str(int(watched_percent))})
					except: pass

				try: # Year is the shows year, not the seasons year. Extract year from premier date for infoLabels to have "season_year."
					season_year = re.findall(r'(\d{4})', i.get('premiered', ''))[0]
					meta.update({'year': season_year})
				except: pass
				if upcoming_prependDate and i.get('traktUpcomingProgress') is True:
					try:
						if premiered and meta.get('airtime'): combined='%sT%s' % (premiered, meta.get('airtime', ''))
						else: raise Exception()
						air_datetime = tools.convert_time(stringTime=combined, zoneFrom=meta.get('airzone', ''), zoneTo='local', formatInput='%Y-%m-%dT%H:%M', formatOutput='%b %d %I:%M %p', remove_zeroes=True)
						new_title = '[COLOR %s][%s]  [/COLOR]' % (self.highlight_color, air_datetime) + title
						meta.update({'title': new_title})
					except: pass
				control.infoTagger(item, meta)
				item.addContextMenuItems(cm)
				if playlist: append((url, item, isFolder))
				else: control.addItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		if next:
			try:
				if not items: raise Exception()
				url = items[0]['next']
				if not url: raise Exception()
				nextMenu = getLS(32053)
				url_params = dict(parse_qsl(url))
				if 'imdb.com' in url:
					start = int(url_params.get('start'))
					page = '  [I](%s)[/I]' % str(((start - 1) / int(self.count)) + 1)
				else:
					page = url_params.get('page')
					page = '  [I](%s)[/I]' % page
#				nextMenu = '[COLOR skyblue]' + nextMenu + page + '[/COLOR]'
				nextMenu = f"[COLOR {self.highlight_color}]{nextMenu}{page}[/COLOR]"
				if '/users/me/history/' in url: url = '%s?action=calendar&url=%s' % (sysaddon, quote_plus(url))
				item = control.item(label=nextMenu, offscreen=True)
				icon = control.addonNext()
				item.setArt({'icon': icon, 'thumb': icon, 'poster': icon, 'banner': icon})
				item.setProperty ('SpecialSort', 'bottom')
				if playlist: append((url, item, True))
				else: control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except: pass
		if playlist: return listitems
		if isMultiList and multi_unwatchedEnabled: # Show multi episodes as show, in order to display unwatched count if enabled.
			control.content(syshandle, 'tvshows')
			control.directory(syshandle, cacheToDisc=False) # disable cacheToDisc so unwatched counts loads fresh data counts if changes made
			views.setView('tvshows', {'skin.estuary': 55, 'skin.confluence': 500})
		else:
			control.content(syshandle, 'episodes')
			control.directory(syshandle, cacheToDisc=False) # disable cacheToDisc so unwatched counts loads fresh data counts if changes made
			views.setView('episodes', {'skin.estuary': 55, 'skin.confluence': 504})

	def addDirectory(self, items, queue=False):
		from sys import argv # some functions like ActivateWindow() throw invalid handle less this is imported here.
		if not items: # with reuselanguageinvoker on an empty directory must be loaded, do not use sys.exit()
			control.hide() ; control.notification(title=32326, message=33049)
		syshandle = int(argv[1])
		addonThumb = control.addonThumb()
		artPath = control.artPath()
		queueMenu = getLS(32065)
		for i in items:
			try:
				name = i['name']
				if i['image'].startswith('http'): poster = i['image']
				elif artPath: poster = control.joinPath(artPath, i['image'])
				else: poster = addonThumb
				icon = i.get('icon', '') or 'DefaultFolder.png'
				if not icon.startswith('Default'): icon = control.joinPath(self.artPath, icon)
				url = 'plugin://plugin.video.dradis/?action=%s' % i['action']
				try: url += '&url=%s' % quote_plus(i['url'])
				except: pass
				cm = []
				if queue: cm.append((queueMenu, 'RunPlugin(plugin://plugin.video.dradis/?action=playlist_QueueItem)'))
				cm.append(('[COLOR red]Dradis Settings[/COLOR]', 'RunPlugin(plugin://plugin.video.dradis/?action=tools_openSettings)'))
				item = control.item(label=name, offscreen=True)
				item.setArt({'icon': icon, 'poster': poster, 'thumb': poster, 'fanart': control.addonFanart(), 'banner': poster})
				item.setInfo(type='video', infoLabels={'plot': name}) if KODI_VERSION < 20 else item.getVideoInfoTag().setPlot(name)
				item.addContextMenuItems(cm)
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		content = 'addons' if control.skin == 'skin.auramod' else ''
		control.content(syshandle, content) # some skins use their own thumb for things like "genres" when content type is set here
		control.directory(syshandle, cacheToDisc=True)
