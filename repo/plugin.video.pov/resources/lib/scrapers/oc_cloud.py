from threading import Thread
from debrids.offcloud_api import OffcloudAPI as Debrid
from modules import source_utils
from modules.utils import clean_file_name, normalize
from modules.settings import enabled_debrids_check, filter_by_name
# from modules.kodi_utils import logger

internal_results, check_title, clean_title = source_utils.internal_results, source_utils.check_title, source_utils.clean_title
get_file_info, release_info_format, seas_ep_filter = source_utils.get_file_info, source_utils.release_info_format, source_utils.seas_ep_filter
extensions = source_utils.supported_video_extensions()

class source(Debrid):
	scrape_provider = 'oc_cloud'
	def results(self, info):
		try:
			self.sources = []
			if not enabled_debrids_check('oc'): return internal_results(self.scrape_provider, self.sources)
			self.folder_results, self.scrape_results = [], []
			title_filter = filter_by_name(self.scrape_provider)
			self.media_type, title = info.get('media_type'), info.get('title')
			self.year, self.season, self.episode = int(info.get('year')), info.get('season'), info.get('episode')
			if self.media_type == 'episode': self.seas_ep_query_list = source_utils.seas_ep_query_list(self.season, self.episode)
			self.folder_query, self.year_query_list = clean_title(normalize(title)), tuple(map(str, range(self.year - 1, self.year + 2)))
			self._scrape_cloud()
			if not self.scrape_results: return internal_results(self.scrape_provider, self.sources)
			self.aliases = source_utils.get_aliases_titles(info.get('aliases', []))
			def _process():
				for item in self.scrape_results:
					try:
						file_name = item['filename']
						if title_filter and not check_title(title, file_name, self.aliases, self.year, self.season, self.episode): continue
						URLName = clean_file_name(file_name).replace('html', ' ').replace('+', ' ').replace('-', ' ')
						file_dl, size = item['url'], round(float(item['size'])/1073741824, 2)
						video_quality, details = get_file_info(name_info=release_info_format(file_name))
						source_item = {'name': file_name, 'title': file_name, 'URLName': URLName, 'quality': video_quality, 'size': size, 'size_label': '%.2f GB' % size,
									'extraInfo': details, 'url_dl': file_dl, 'id': file_dl, 'downloads': False, 'direct': True, 'source': self.scrape_provider,
									'scrape_provider': self.scrape_provider}
						yield source_item
					except: pass
			self.sources = list(_process())
		except Exception as e:
			from modules.kodi_utils import logger
			logger('POV offcloud scraper Exception', e)
		internal_results(self.scrape_provider, self.sources)
		return self.sources

	def _scrape_cloud(self):
		try:
			results_append = self.scrape_results.append
			threads = []
			append = threads.append
			my_cloud_files = self.user_cloud(check_cache=False)
			for item in my_cloud_files:
				if not item['status'] == 'downloaded': continue
				if not self.folder_query in clean_title(normalize(item['fileName'])): continue
				if item['isDirectory']:
					append(i := Thread(target=self._scrape_folders, args=(item,)))
					i.start()
				else:
					url = self.build_url(item['server'], item['requestId'], item['fileName'])
					self.folder_results.append({'filename': item['fileName'], 'url': url, 'folder_name': item['fileName']})
			[i.join() for i in threads]
			if not self.folder_results: return self.sources
			for item in self.folder_results:
				try:
					if not item['filename'].lower().endswith(tuple(extensions)): continue
					formalized = normalize(item['folder_name'])
					foldername = clean_title(formalized)
					normalized = normalize(item['filename'])
					filename = clean_title(normalized)
					if self.media_type == 'movie':
						if not any(x in filename for x in self.year_query_list): continue
					elif not seas_ep_filter(self.season, self.episode, normalized): continue
					if not (self.folder_query in filename or self.folder_query in foldername): continue
					results_append({'filename': normalized, 'url': self.requote_uri(item['url']), 'size': 0})
				except: pass
		except: pass

	def _scrape_folders(self, folder_info):
		try: self.folder_results += [
			{'filename': i.split('/')[-1], 'url': i, 'folder_name': folder_info['fileName']}
			for i in self.user_cloud(folder_info['requestId'], check_cache=False)
		]
		except: pass

