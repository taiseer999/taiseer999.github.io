import requests
from caches.main_cache import cache_object
from modules import kodi_utils
# logger = kodi_utils.logger

ls, get_setting = kodi_utils.local_string, kodi_utils.get_setting
base_url = 'https://api.alldebrid.com/'
timeout = 10.0
session = requests.Session()
session.mount('https://api.alldebrid.com', requests.adapters.HTTPAdapter(max_retries=1))

class AllDebridAPI:
	icon = 'alldebrid.png'

	def __init__(self):
		self.token = get_setting('ad.token')
		session.headers['Authorization'] = 'Bearer %s' % self.token

	def _get(self, url, params=None):
		if self.token == '': return None
		result = None
		url = base_url + url
		try:
			result = session.get(url, params=params, timeout=timeout).json()
			if result.get('status') == 'success' and 'data' in result: result = result['data']
		except: pass
		return result

	def _post(self, url, data=None):
		if self.token == '': return None
		result = None
		url = base_url + url
		try:
			result = session.post(url, data=data, timeout=timeout).json()
			if result.get('status') == 'success' and 'data' in result: result = result['data']
		except: pass
		return result

	def days_remaining(self):
		import datetime
		try:
			account_info = self.account_info()['user']
			expires = datetime.datetime.fromtimestamp(account_info['premiumUntil'])
			days = (expires - datetime.datetime.today()).days
		except: days = None
		return days

	def account_info(self):
		response = self._get('v4/user')
		return response

	def list_transfer(self, transfer_id):
		url = 'v4/magnet/status'
		params = {'id': transfer_id}
		result = self._get(url, params)
		result = result['magnets']
		return result

	def delete_torrent(self, transfer_id):
		url = 'v4/magnet/delete'
		params = {'id': transfer_id}
		result = self._get(url, params)
		result = False if 'error' in result else True
		return result

	def unrestrict_link(self, link):
		url = 'v4/link/unlock'
		params = {'link': link}
		response = self._get(url, params)
		try: return response['link']
		except: return None

	def check_single_magnet(self, hash_string):
		cache_info = self.check_cache(hash_string)['magnets'][0]
		return cache_info['instant']

	def check_cache(self, hashes):
		data = {'v4/magnets[]': hashes}
		response = self._post('magnet/instant', data)
		return response

	def create_transfer(self, magnet):
		url = 'v4/magnet/upload'
		params = {'magnet': magnet}
		result = self._get(url, params)
		result = result['magnets'][0]
		return result.get('id', '')

	def parse_magnet_pack(self, magnet_url, info_hash):
		from modules.source_utils import supported_video_extensions
		try:
			extensions = supported_video_extensions()
			torrent_id = self.create_transfer(magnet_url)
			for key in ['completionDate'] * 3:
				kodi_utils.sleep(500)
				transfer_info = self.list_transfer(torrent_id)
				if transfer_info[key]: break
			else: raise Exception('uncached magnet:\n%s' % magnet_url)
			torrent_files = [
				{'link': item['link'],
				 'size': item['size'],
				 'torrent_id': torrent_id,
				 'filename': item['filename']}
				for item in transfer_info['links']
				if item['filename'].lower().endswith(tuple(extensions))
			]
			return torrent_files
		except Exception as e:
			kodi_utils.logger('alldebrid exception', str(e))
			if torrent_id: self.delete_torrent(torrent_id)
			return None

	def get_hosts(self):
		string = 'pov_ad_valid_hosts'
		url = 'v4/hosts'
		hosts_dict = {'AllDebrid': []}
		hosts = []
		try:
			result = cache_object(self._get, string, url, False, 168)
			result = result['hosts']
			for k, v in result.items():
				try: hosts.extend(v['domains'])
				except: pass
			hosts = list(set(hosts))
			hosts_dict['AllDebrid'] = hosts
		except: pass
		return hosts_dict

	def downloads(self):
		url = 'v4/user/history'
		string = 'pov_ad_downloads'
		return cache_object(self._get, string, url, False, 0.5)

	def user_cloud(self):
		url = 'v4/magnet/status'
		string = 'pov_ad_user_cloud'
		return cache_object(self._get, string, url, False, 0.5)

	def clear_cache(self):
		from modules.kodi_utils import clear_property, path_exists, database_connect, maincache_db
		try:
			if not path_exists(maincache_db): return True
			from caches.debrid_cache import DebridCache
			dbcon = database_connect(maincache_db)
			dbcur = dbcon.cursor()
			# USER CLOUD
			try:
				dbcur.execute("""DELETE FROM maincache WHERE id = ?""", ('pov_ad_user_cloud',))
				clear_property('pov_ad_user_cloud')
				dbcon.commit()
				user_cloud_success = True
			except: user_cloud_success = False
			# DOWNLOAD LINKS
			try:
				dbcur.execute("""DELETE FROM maincache WHERE id = ?""", ('pov_ad_downloads',))
				clear_property('pov_ad_downloads')
				dbcon.commit()
				download_links_success = True
			except: download_links_success = False
			# HOSTERS
			try:
				dbcur.execute("""DELETE FROM maincache WHERE id = ?""", ('pov_ad_valid_hosts',))
				clear_property('pov_ad_valid_hosts')
				dbcon.commit()
				dbcon.close()
				hoster_links_success = True
			except: hoster_links_success = False
			# HASH CACHED STATUS
			try:
				DebridCache().clear_debrid_results('ad')
				hash_cache_status_success = True
			except: hash_cache_status_success = False
		except: return False
		if False in (user_cloud_success, download_links_success, hoster_links_success, hash_cache_status_success): return False
		return True

