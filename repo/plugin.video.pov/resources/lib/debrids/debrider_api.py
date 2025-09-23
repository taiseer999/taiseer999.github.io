import requests
from threading import Thread
from caches.main_cache import cache_object
from modules import kodi_utils
# logger = kodi_utils.logger

ls, get_setting = kodi_utils.local_string, kodi_utils.get_setting
base_url = 'https://debrider.app/api/v1'
timeout = 10.0
session = requests.Session()
session.mount(base_url, requests.adapters.HTTPAdapter(max_retries=1))

class DebriderAPI:
	icon = 'debrider.png'

	def __init__(self):
		self.token = get_setting('db.token')

	def _request(self, method, path, params=None, json=None, data=None):
		session.headers['Authorization'] = 'Bearer %s' % self.token
		url = '%s/%s' % (base_url, path)
		try:
			response = session.request(method, url, params=params, json=json, data=data, timeout=timeout)
			result = response.json() if 'json' in response.headers.get('Content-Type', '') else response.text
			if not response.ok: response.raise_for_status()
			return result
		except requests.exceptions.RequestException as e:
			kodi_utils.logger('debrider error', str(e))

	def _get(self, url, params=None):
		return self._request('get', url, params=params)

	def _post(self, url, params=None, json=None, data=None):
		return self._request('post', url, params=params, json=json, data=data)

	def days_remaining(self):
		pass

	def account_info(self):
		url = 'account'
		return self._get(url)

	def torrent_info(self, request_id):
		url = '%s/%s' % ('tasks', request_id)
		return self._get(url)

	def delete_torrent(self, request_id):
		session.headers['Authorization'] = 'Bearer %s' % self.token
		url = '%s/%s/%s' % (base_url, 'tasks', request_id)
		result = session.delete(url, timeout=timeout)
		return 'success' if result.ok else ''

	def unrestrict_link(self, link):
		return link

	def check_single_magnet(self, hash_string):
		data = {'data': [hash_string]}
		url = 'link/lookup'
		result = self._post(url, json=data)
		return [{h: i['files']} for h, i in zip([hash_string], result['result']) if i['cached']]

	def check_cache(self, hashes):
		data = {'data': hashes}
		url = 'link/lookup'
		result = self._post(url, json=data)
		return [h for h, i in zip(hashes, result['result']) if i['cached']]

	def add_magnet(self, magnet):
		data = {'type': 'magnet', 'data': magnet}
		url = 'tasks'
		return self._post(url, json=data)

	def instant_transfer(self, hash):
		data = {'data': hash}
		url = 'link/generate'
		return self._post(url, json=data)

	def create_transfer(self, magnet):
		result = self.add_magnet(magnet)
		return result.get('data', {}).get('id', '')

	def parse_magnet_pack(self, magnet_url, info_hash):
		from modules.source_utils import supported_video_extensions
		try:
			extensions = supported_video_extensions()
			cached = self.check_single_magnet(info_hash)
			torrent_files = cached[0][info_hash]
			torrent_files = [
				{'link': item['download_link'],
				 'size': item['size'],
				 'filename': item['name'].split('/')[-1]}
				for item in torrent_files
				if item['name'].lower().endswith(tuple(extensions))
			]
			return torrent_files
		except Exception:
			return None

	def user_cloud(self, request_id=None, check_cache=True):
		string = 'pov_db_user_cloud_info_%s' % request_id if request_id else 'pov_db_user_cloud'
		url = '%s/%s' % ('tasks', request_id) if request_id else 'tasks'
		if check_cache: result = cache_object(self._get, string, url, False, 0.5)
		else: result = self._get(url)
		return result

	def clear_cache(*args):
		try:
			if not kodi_utils.path_exists(kodi_utils.maincache_db): return True
			from caches.debrid_cache import DebridCache
			user_cloud_success = False
			dbcon = kodi_utils.database_connect(kodi_utils.maincache_db)
			dbcur = dbcon.cursor()
			# USER CLOUD
			try:
				dbcur.execute("""SELECT id FROM maincache WHERE id LIKE ?""", ('pov_db_user_cloud%',))
				try:
					user_cloud_cache = dbcur.fetchall()
					user_cloud_cache = [i[0] for i in user_cloud_cache]
				except:
					user_cloud_success = True
				if not user_cloud_success:
					for i in user_cloud_cache:
						dbcur.execute("""DELETE FROM maincache WHERE id = ?""", (i,))
						kodi_utils.clear_property(str(i))
					dbcon.commit()
					user_cloud_success = True
			except: user_cloud_success = False
			# HASH CACHED STATUS
			try:
				DebridCache().clear_debrid_results('db')
				hash_cache_status_success = True
			except: hash_cache_status_success = False
		except: return False
		if False in (user_cloud_success, hash_cache_status_success): return False
		return True

