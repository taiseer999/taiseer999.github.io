# created by Venom for Fenomscrapers (updated 3-02-2022)
"""
	Fenomscrapers Project
"""

from json import loads as jsloads, dumps as jsdumps
import base64, re, requests, queue
#from fenom import client
from resources.lib.modules import scrape_utils, source_utils
from resources.lib.modules.control import setting as getSetting


class source:
	priority = 1
	pack_capable = True
	hasMovies = True
	hasEpisodes = True
	_queue = queue.SimpleQueue()
	def __init__(self):
		services = {
			'0': ('realdebrid', 'realdebridtoken'), '1': ('premiumize', 'premiumizetoken'), '2': ('alldebrid', 'alldebridtoken')
		}
		url = getSetting('comet.url')
		debrid = getSetting('comet.debrid', '0')
		debrid, token = services[debrid]
		token = getSetting(token, '')
		indexers = getSetting('comet.indexers')
		indexers = [i.strip() for i in indexers.split(',') if i.strip()]
		languages = getSetting('comet.langs')
		languages = [i.strip() for i in languages.split(',') if i.strip()]
		params = {"indexers":[],"maxResults":0,"maxSize":0,"resultFormat":["All"],"resolutions":["All"],"languages":["All"],"debridService":"","debridApiKey":"","debridStreamProxyPassword":""}
		params.update({'indexers': indexers, 'languages': languages, 'debridService': debrid, 'debridApiKey': token})
		params = base64.b64encode(jsdumps(params, separators=(',', ':')).encode('utf-8')).decode('utf-8')
		self.language = ['en']
		self.base_link = url or 'https://comet.elfhosted.com'
		self.movieSearch_link = f"/{params}/stream/movie/%s.json"
		self.tvSearch_link = f"/{params}/stream/series/%s:%s:%s.json"
		self.min_seeders = 0
# Currently supports BITSEARCH(+), EZTV(+), ThePirateBay(+), TheRARBG(+), YTS(+)

	def sources(self, data, hostDict):
		sources = []
		if not data: return sources
		append = sources.append
		try:
			title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
			title = title.replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
			aliases = data['aliases']
			episode_title = data['title'] if 'tvshowtitle' in data else None
			year = data['year']
			imdb = data['imdb']
			if 'tvshowtitle' in data:
				season = data['season']
				episode = data['episode']
				hdlr = 'S%02dE%02d' % (int(season), int(episode))
				url = '%s%s' % (self.base_link, self.tvSearch_link % (imdb, season, episode))
			else:
				url = '%s%s' % (self.base_link, self.movieSearch_link % imdb)
				hdlr = year
			# log_utils.log('url = %s' % url)
			try:
				results = requests.get(url, timeout=7) # client.request(url, timeout=7)
				files = results.json()['streams'] # jsloads(results)['streams']
			except: files = []
			self._queue.put_nowait(files) # if seasons
			self._queue.put_nowait(files) # if shows
			_INFO = re.compile(r'💾.*') # _INFO = re.compile(r'👤.*')
		except:
			source_utils.scraper_error('COMET')
			return sources

		for file in files:
			try:
				try: hash = file['infoHash']
				except: hash = file['behaviorHints']['bingeGroup'].replace('comet|', '')
				file_title = file['description'].split('\n')
				file_info = [x for x in file_title if _INFO.match(x)][0]
				# try:
					# index = file_title.index(file_info)
					# if index == 1: combo = file_title[0].replace(' ', '.')
					# else: combo = ''.join(file_title[0:2]).replace(' ', '.')
					# if '🇷🇺' in file_title[index+1] and not any(value in combo for value in ('.en.', '.eng.', 'english')): continue
				# except: pass

				name = scrape_utils.clean_name(file_title[0])

				if not scrape_utils.check_title(title, aliases, name.replace('.(Archie.Bunker', ''), hdlr, year): continue
				name_info = scrape_utils.info_from_name(name, title, year, hdlr, episode_title)

				url = 'magnet:?xt=urn:btih:%s&dn=%s' % (hash, name) 
				# if not episode_title: #filter for eps returned in movie query (rare but movie and show exists for Run in 2020)
					# ep_strings = [r'(?:\.|\-)s\d{2}e\d{2}(?:\.|\-|$)', r'(?:\.|\-)s\d{2}(?:\.|\-|$)', r'(?:\.|\-)season(?:\.|\-)\d{1,2}(?:\.|\-|$)']
					# name_lower = name.lower()
					# if any(re.search(item, name_lower) for item in ep_strings): continue

#				try:
#					seeders = int(re.search(r'(\d+)', file_info).group(1))
#					if self.min_seeders > seeders: continue
#				except: seeders = 0

				quality, info = scrape_utils.get_release_quality(name_info, url)
				try:
					size = re.search(r'((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|Gb|MB|MiB|Mb))', file_info).group(0)
					dsize, isize = scrape_utils._size(size)
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				append({'provider': 'comet', 'source': 'torrent', 'seeders': 0, 'hash': hash, 'name': name, 'name_info': name_info, 'quality': quality,
							'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize})
			except:
				source_utils.scraper_error('COMET')
		return sources

	def sources_packs(self, data, hostDict, search_series=False, total_seasons=None, bypass_filter=False):
		sources = []
		if not data: return sources
		sources_append = sources.append
		try:
			title = data['tvshowtitle'].replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
			aliases = data['aliases']
			imdb = data['imdb']
			year = data['year']
			season = data['season']
			url = '%s%s' % (self.base_link, self.tvSearch_link % (imdb, season, data['episode']))
#			results = requests.get(url, timeout=7) # client.request(url, timeout=7)
			files = self._queue.get(timeout=8) # jsloads(results)['streams']
			_INFO = re.compile(r'💾.*') # _INFO = re.compile(r'👤.*')
		except:
			source_utils.scraper_error('COMET')
			return sources

		for file in files:
			try:
				try: hash = file['infoHash']
				except: hash = file['behaviorHints']['bingeGroup'].replace('comet|', '')
				file_title = file['description'].split('\n')
				file_info = [x for x in file_title if _INFO.match(x)][0]
				# try:
					# index = file_title.index(file_info)
					# if index == 1: combo = file_title[0].replace(' ', '.')
					# else: combo = ''.join(file_title[0:2]).replace(' ', '.')
					# if '🇷🇺' in file_title[index+1] and not any(value in combo for value in ('.en.', '.eng.', 'english')): continue
				# except: pass

				name = scrape_utils.clean_name(file['torrentTitle'].split('\n')[0])

				episode_start, episode_end = 0, 0
				if not search_series:
					if not bypass_filter:
						valid, episode_start, episode_end = scrape_utils.filter_season_pack(title, aliases, year, season, name.replace('.(Archie.Bunker', ''))
						if not valid: continue
					package = 'season'

				elif search_series:
					if not bypass_filter:
						valid, last_season = scrape_utils.filter_show_pack(title, aliases, imdb, year, season, name.replace('.(Archie.Bunker', ''), total_seasons)
						if not valid: continue
					else: last_season = total_seasons
					package = 'show'

				name_info = scrape_utils.info_from_name(name, title, year, season=season, pack=package)

				url = 'magnet:?xt=urn:btih:%s&dn=%s' % (hash, name)
#				try:
#					seeders = int(re.search(r'(\d+)', file_info).group(1))
#					if self.min_seeders > seeders: continue
#				except: seeders = 0

				quality, info = scrape_utils.get_release_quality(name_info, url)
				try:
					size = re.search(r'((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|Gb|MB|MiB|Mb))', file_info).group(0)
					dsize, isize = scrape_utils._size(size)
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				item = {'provider': 'comet', 'source': 'torrent', 'seeders': 0, 'hash': hash, 'name': name, 'name_info': name_info, 'quality': quality,
							'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'package': package}
				if search_series: item.update({'last_season': last_season})
				elif episode_start: item.update({'episode_start': episode_start, 'episode_end': episode_end}) # for partial season packs
				sources_append(item)
			except:
				source_utils.scraper_error('COMET')
		return sources
