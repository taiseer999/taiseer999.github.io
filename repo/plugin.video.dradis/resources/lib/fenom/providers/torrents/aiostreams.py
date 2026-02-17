# created by kodifitzwell for Fenomscrapers
"""
	Fenomscrapers Project
"""

from json import loads as jsloads
import queue
from resources.lib.fenom import client
from resources.lib.fenom import source_utils
from resources.lib.fenom.control import setting as getSetting


class source:
	timeout = 7
	priority = 1
	pack_capable = True
	hasMovies = True
	hasEpisodes = True
	_queue = queue.SimpleQueue()
	def __init__(self):
		self.language = ['en']
		self.base_link = (
			"https://aiostreams.stremio.ru",
			"https://aiostreamsfortheweebs.midnightignite.me"
		)[int(getSetting('aiostreams.url', '0'))]
		self.movieSearch_link = '/api/v1/search?type=movie&id=%s'
		self.tvSearch_link = '/api/v1/search?type=series&id=%s:%s:%s'
		self.min_seeders = 0

	def sources(self, data, hostDict):
		sources = []
		if not data: return sources
		sources_append = sources.append
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
				hdlr = year
				url = '%s%s' % (self.base_link, self.movieSearch_link % imdb)
			# log_utils.log('url = %s' % url)
			try:
				results = client.request(url, headers=self._headers(), timeout=self.timeout)
				files = jsloads(results)['data']['results']
			except:
				files = []
				raise
			finally:
				self._queue.put_nowait(files) # if seasons
				self._queue.put_nowait(files) # if shows
			undesirables = source_utils.get_undesirables()
			check_foreign_audio = source_utils.check_foreign_audio()
		except:
			source_utils.scraper_error('AIOSTREAMS')
			return sources

		for file in files:
			try:
				hash = file['infoHash']
				file_title = (file['folderName'] or file['filename']).replace('┈➤', '\n').split('\n')

				name = source_utils.clean_name(file_title[0])

				if not source_utils.check_title(title, aliases, name.replace('.(Archie.Bunker', ''), hdlr, year): continue
				name_info = source_utils.info_from_name(name, title, year, hdlr, episode_title)
				if source_utils.remove_lang(name_info, check_foreign_audio): continue
				if undesirables and source_utils.remove_undesirables(name_info, undesirables): continue

				url = 'magnet:?xt=urn:btih:%s&dn=%s' % (hash, name)

				try:
					seeders = file['seeders']
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					size = f"{float(file['size']) / 1073741824:.2f} GB"
					dsize, isize = source_utils._size(size)
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				sources_append({
					'source': 'torrent', 'language': 'en', 'direct': False, 'debridonly': True,
					'provider': 'aiostreams', 'hash': hash, 'url': url, 'name': name, 'name_info': name_info,
					'quality': quality, 'info': info, 'size': dsize, 'seeders': seeders
				})
			except:
				source_utils.scraper_error('AIOSTREAMS')
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
			files = self._queue.get(timeout=self.timeout + 1)
			undesirables = source_utils.get_undesirables()
			check_foreign_audio = source_utils.check_foreign_audio()
		except:
			source_utils.scraper_error('AIOSTREAMS')
			return sources

		for file in files:
			try:
				hash = file['infoHash']
				file_title = (file['folderName'] or file['filename']).replace('┈➤', '\n').split('\n')

				name = source_utils.clean_name(file_title[0])

				episode_start, episode_end = 0, 0
				if not search_series:
					if not bypass_filter:
						valid, episode_start, episode_end = source_utils.filter_season_pack(title, aliases, year, season, name.replace('.(Archie.Bunker', ''))
						if not valid: continue
					package = 'season'

				elif search_series:
					if not bypass_filter:
						valid, last_season = source_utils.filter_show_pack(title, aliases, imdb, year, season, name.replace('.(Archie.Bunker', ''), total_seasons)
						if not valid: continue
					else: last_season = total_seasons
					package = 'show'

				name_info = source_utils.info_from_name(name, title, year, season=season, pack=package)
				if source_utils.remove_lang(name_info, check_foreign_audio): continue
				if undesirables and source_utils.remove_undesirables(name_info, undesirables): continue

				url = 'magnet:?xt=urn:btih:%s&dn=%s' % (hash, name)
				try:
					seeders = file['seeders']
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					size = f"{float(file['size']) / 1073741824:.2f} GB"
					dsize, isize = source_utils._size(size)
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				item = {
					'source': 'torrent', 'language': 'en', 'direct': False, 'debridonly': True,
					'provider': 'aiostreams', 'hash': hash, 'url': url, 'name': name, 'name_info': name_info,
					'quality': quality, 'info': info, 'size': dsize, 'seeders': seeders, 'package': package
				}
				if search_series: item.update({'last_season': last_season})
				elif episode_start: item.update({'episode_start': episode_start, 'episode_end': episode_end}) # for partial season packs
				sources_append(item)
			except:
				source_utils.scraper_error('AIOSTREAMS')
		return sources

	def _headers(self):
		return {'x-aiostreams-user-data': (
			'ewogICJwcmVzZXRzIjogWwogICAgewogICAgICAidHlwZSI6ICJjb21ldCIsCiAgICAgICJpbnN0YW5j'
			'ZUlkIjogImY3YiIsCiAgICAgICJlbmFibGVkIjogdHJ1ZSwKICAgICAgIm9wdGlvbnMiOiB7CiAgICAg'
			'ICAgIm5hbWUiOiAiQ29tZXQiLAogICAgICAgICJ0aW1lb3V0IjogNjUwMCwKICAgICAgICAicmVzb3Vy'
			'Y2VzIjogWyJzdHJlYW0iXSwKICAgICAgICAiaW5jbHVkZVAyUCI6IHRydWUsCiAgICAgICAgInJlbW92'
			'ZVRyYXNoIjogZmFsc2UKICAgICAgfQogICAgfSwKICAgIHsKICAgICAgInR5cGUiOiAibWVkaWFmdXNp'
			'b24iLAogICAgICAiaW5zdGFuY2VJZCI6ICI0NTAiLAogICAgICAiZW5hYmxlZCI6IHRydWUsCiAgICAg'
			'ICJvcHRpb25zIjogewogICAgICAgICJuYW1lIjogIk1lZGlhRnVzaW9uIiwKICAgICAgICAidGltZW91'
			'dCI6IDY1MDAsCiAgICAgICAgInJlc291cmNlcyI6IFsic3RyZWFtIl0sCiAgICAgICAgInVzZUNhY2hl'
			'ZFJlc3VsdHNPbmx5IjogdHJ1ZSwKICAgICAgICAiZW5hYmxlV2F0Y2hsaXN0Q2F0YWxvZ3MiOiBmYWxz'
			'ZSwKICAgICAgICAiZG93bmxvYWRWaWFCcm93c2VyIjogZmFsc2UsCiAgICAgICAgImNvbnRyaWJ1dG9y'
			'U3RyZWFtcyI6IGZhbHNlLAogICAgICAgICJjZXJ0aWZpY2F0aW9uTGV2ZWxzRmlsdGVyIjogW10sCiAg'
			'ICAgICAgIm51ZGl0eUZpbHRlciI6IFtdCiAgICAgIH0KICAgIH0KICBdLAogICJmb3JtYXR0ZXIiOiB7'
			'CiAgICAiaWQiOiAidG9ycmVudGlvIiwKICAgICJkZWZpbml0aW9uIjogeyJuYW1lIjogIiIsICJkZXNj'
			'cmlwdGlvbiI6ICIifQogIH0sCiAgInNvcnRDcml0ZXJpYSI6IHsiZ2xvYmFsIjogW119LAogICJkZWR1'
			'cGxpY2F0b3IiOiB7CiAgICAiZW5hYmxlZCI6IGZhbHNlLAogICAgImtleXMiOiBbImZpbGVuYW1lIiwg'
			'ImluZm9IYXNoIl0sCiAgICAibXVsdGlHcm91cEJlaGF2aW91ciI6ICJhZ2dyZXNzaXZlIiwKICAgICJj'
			'YWNoZWQiOiAic2luZ2xlX3Jlc3VsdCIsCiAgICAidW5jYWNoZWQiOiAicGVyX3NlcnZpY2UiLAogICAg'
			'InAycCI6ICJzaW5nbGVfcmVzdWx0IiwKICAgICJleGNsdWRlQWRkb25zIjogW10KICB9Cn0='
		)}

