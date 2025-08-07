# created by kodifitzwell for Fenomscrapers
"""
	Fenomscrapers Project
"""

from json import loads as jsloads, dumps as jsdumps
import base64, re, requests
#from fenom import client
from fenom import source_utils
from fenom.control import setting as getSetting


class source:
	timeout = 7
	priority = 1
	pack_capable = False # packs parsed in sources function
	hasMovies = True
	hasEpisodes = True
	def __init__(self):
		self.language = ['en']
		self.base_link = "https://mediafusion.elfhosted.com"
		self.movieSearch_link = '/stream/movie/%s.json'
		self.tvSearch_link = '/stream/series/%s:%s:%s.json'
		self.min_seeders = 0

	def _headers(self):
		debrid = getSetting('mfdebrid.debrid')
		params = {"enable_catalogs":False,"max_streams_per_resolution":99,"torrent_sorting_priority":[],"certification_filter":["Disable"],"nudity_filter":["Disable"]}
		headers = {'encoded_user_data': 'eyJlbmFibGVfY2F0YWxvZ3MiOiBmYWxzZSwgIm1heF9zdHJlYW1zX3Blcl9yZXNvbHV0aW9uIjogOTksICJ0b3JyZW50X3NvcnRpbmdfcHJpb3JpdHkiOiBbXSwgImNlcnRpZmljYXRpb25fZmlsdGVyIjogWyJEaXNhYmxlIl0sICJudWRpdHlfZmlsdGVyIjogWyJEaXNhYmxlIl19'}
		if not debrid in ('0', '1'): return headers
		service, token = {'0': ('realdebrid', 'rd.token'), '1': ('alldebrid', 'ad.token')}[debrid]
		params['streaming_provider'] = {'token': getSetting(token), 'service': service, 'only_show_cached_streams': True}
		headers['encoded_user_data'] = base64.b64encode(jsdumps(params).encode('utf-8')).decode('utf-8')
		return headers

	def sources(self, data, hostDict):
		sources = []
		if not data: return sources
		append = sources.append
		try:
			title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
			title = title.replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
			aliases = data['aliases']
			episode_title = data['title'] if 'tvshowtitle' in data else None
			total_seasons = data['total_seasons'] if 'tvshowtitle' in data else None
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
			results = requests.get(url, headers=self._headers(), timeout=self.timeout) # client.request(url, timeout=7)
			files = results.json()['streams'] # jsloads(results)['streams']
			_INFO = re.compile(r'💾.*')
			undesirables = source_utils.get_undesirables()
			check_foreign_audio = source_utils.check_foreign_audio()
		except:
			source_utils.scraper_error('MFDEBRID')
			return sources

		for file in files:
			try:
				package, episode_start = None, 0
				if 'url' in file: hash = re.search(r'\b\w{40}\b', file['url']).group()
				else: hash = file['infoHash']
				file_title = file['description'].replace('┈➤', '\n').split('\n')
				file_info = [x for x in file_title if _INFO.search(x)][0]
				cached = 'MF+' if '⚡' in file['name'] else False

				name = source_utils.clean_name(file_title[0])

				if not source_utils.check_title(title, aliases, name, hdlr, year):
					if total_seasons is None: continue
					valid, last_season = source_utils.filter_show_pack(title, aliases, imdb, year, season, name, total_seasons)
					if not valid:
						valid, episode_start, episode_end = source_utils.filter_season_pack(title, aliases, year, season, name)
						if not valid: continue
						else: package = 'season'
					else: package = 'show'
				name_info = source_utils.info_from_name(name, title, year, hdlr, episode_title)
				if source_utils.remove_lang(name_info, check_foreign_audio): continue
				if undesirables and source_utils.remove_undesirables(name_info, undesirables): continue

				url = 'magnet:?xt=urn:btih:%s&dn=%s' % (hash, name) 

				try:
					seeders = int(re.search(r'👤\s*(\d+)', file_info).group(1))
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					size = re.findall(r'((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|Gb|MB|MiB|Mb))', file_info)[-1]
					dsize, isize = source_utils._size(size)
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				item = {
					'source': 'torrent', 'language': 'en', 'direct': False, 'debridonly': True,
					'provider': cached or 'mfdebrid', 'url': url, 'hash': hash, 'name': name, 'name_info': name_info,
					'quality': quality, 'info': info, 'size': dsize, 'seeders': seeders
				}
				if package: item['package'] = package
				if package == 'show': item.update({'last_season': last_season})
				if episode_start: item.update({'episode_start': episode_start, 'episode_end': episode_end}) # for partial season packs
				append(item)
			except:
				source_utils.scraper_error('MFDEBRID')
		return sources

