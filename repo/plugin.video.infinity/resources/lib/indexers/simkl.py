# -*- coding: utf-8 -*-
"""
	OneMoar Add-on (added by OneMoar Dev 12/23/22)
"""

import requests
from requests.adapters import HTTPAdapter
from threading import Thread
from urllib3.util.retry import Retry
from resources.lib.database import cache
from resources.lib.modules import control

getLS = control.lang
getSetting = control.setting
simkl_icon = control.joinPath(control.artPath(), 'simkl.png')
session = requests.Session()
retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
session.mount('https://api.simkl.com', HTTPAdapter(max_retries=retries, pool_maxsize=100))


class SIMKL:
	def __init__(self):
		self.simkl_hours = int(getSetting('cache.simkl'))
		self.API_key = getSetting('simkl.apikey')

	def get_request(self, url):
		params = {'client_id': self.API_key} if self.API_key else None
		try:
			response = session.get(url, params=params, timeout=20)
			response.raise_for_status()
		except requests.exceptions.RequestException:
			control.notification(message=40349)
			from resources.lib.modules import log_utils
			log_utils.error()
		if response.status_code in (200, 201): return response.json()
		elif response.status_code == 404:
			from resources.lib.modules import log_utils
			log_utils.log('Simkl get_request() failed: (404:NOT FOUND) - URL: %s' % url, level=log_utils.LOGDEBUG)
			return '404:NOT FOUND'
		elif 'Retry-After' in response.headers:
			throttleTime = response.headers['Retry-After']
			control.notification(message='SIMKL Throttling Applied, Sleeping for %s seconds' % throttleTime)
			control.sleep((int(throttleTime) + 1) * 1000)
			return self.get_request(url)
		else:
			from resources.lib.modules import log_utils
			log_utils.log('SIMKL get_request() failed: URL: %s\n                       msg : SIMKL Response: %s' % (url, response.text), __name__, log_utils.LOGDEBUG)
			return None

	def simkl_list(self, url):
		try:
			result = self.get_request(url)
			if result is None: return
			items = result
		except: return
		collector = {}
		self.list = [] ; sortList = []
		threads = [] ; threads_append = threads.append
		for i in items:
			sortList.append(i['ids']['simkl_id'])
			threads_append(Thread(target=self.summary, args=(i['ids']['simkl_id'], collector)))

		[i.start() for i in threads]
		[i.join() for i in threads]
		for i in sortList:
			item = collector.get(i)
			if item: self.list.append(item)
		return self.list

	def summary(self, sid, collector):
		try:
			url = 'https://api.simkl.com/anime/%s?extended=full' % sid
			result = cache.get(self.get_request, self.simkl_hours, url)
			if result is None: return
			values = {}
			values['tmdb'] = str(result.get('ids').get('tmdb')) if result.get('ids').get('tmdb') else ''
			values['imdb'] = str(result.get('ids').get('imdb')) if result.get('ids').get('imdb') else ''
			values['title'] = result.get('en_title') if result.get('en_title') else result.get('title')
			values['year'] = result.get('year') or ''
			if values['imdb'] or values['tmdb']: collector[sid] = values
		except: return

	def auth(self):
		pass

	def revoke(self):
		pass
