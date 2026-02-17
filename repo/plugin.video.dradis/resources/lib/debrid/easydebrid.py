import requests
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules.source_utils import supported_video_extensions

getLS = control.lang
getSetting = control.setting
ip_url = 'https://api.ipify.org'
base_url = 'https://easydebrid.com/api/v1/'
download_url = 'link/generate'
stats_url = 'user/details'
cache_url = 'link/lookup'
ed_icon = control.joinPath(control.artPath(), 'easydebrid.png')
addonFanart = control.addonFanart()

session = requests.Session()
session.mount('https://easydebrid.com', requests.adapters.HTTPAdapter(max_retries=1))


class EasyDebrid:
	name = "EasyDebrid"
	sort_priority = getSetting('easydebrid.priority')
	def __init__(self):
		self.store_to_cloud = getSetting('easydebrid.saveToCloud') == 'true'
		self.token = getSetting('easydebrid.token')
		session.headers['Authorization'] = 'Bearer %s' % self.token

	def _request(self, method, path, params=None, json=None, data=None):
		if not self.token: return
		full_path = '%s%s' % (base_url, path)
		response = session.request(method, full_path, params=params, json=json, data=data, timeout=20)
		try: response.raise_for_status()
		except Exception as e: log_utils.log('easydebrid error %s' % str(e))
		try: result = response.json()
		except: result = {}
		return result

	def _get(self, url, params=None):
		return self._request('get', url, params=params)

	def _post(self, url, params=None, json=None, data=None):
		return self._request('post', url, params=params, json=json, data=data)

	def days_remaining(self):
		import datetime
		try:
			account_info = self.account_info()
			expires = datetime.datetime.fromtimestamp(account_info['paid_until'])
			days = (expires - datetime.datetime.today()).days
		except: days = None
		return days

	def account_info(self):
		return self._get(stats_url)

	def unrestrict_link(self, link):
		return link

	def check_cache(self, hashlist):
		data = {'urls': hashlist}
		result = self._post(cache_url, json=data)
		return [h for h, cached in zip(hashlist, result['cached']) if cached]

	def instant_transfer(self, magnet):
		try: user_ip = requests.get(ip_url, timeout=2.0).text
		except: user_ip = ''
		if user_ip: session.headers['X-Forwarded-For'] = user_ip
		data = {'url': magnet}
		return self._post(download_url, json=data)

	def create_transfer(self, magnet_url):
		data = {'url': magnet_url}
		result = self._post('link/request', json=data)
		return result.get('success', '')

	def display_magnet_pack(self, magnet_url, info_hash):
		try:
			extensions = supported_video_extensions()
			torrent = self.instant_transfer(magnet_url)
			torrent_files = torrent['files']
			torrent_files = [
				{'link': item['url'],
				 'size': item['size'] / 1073741824,
				 'filename': item['filename']}
				for item in torrent['files']
				if item['filename'].lower().endswith(tuple(extensions))
			]
			return torrent_files
		except Exception:
			return None

	def add_uncached_torrent(self, magnet_url, pack=False):
		control.busy()
		result = self.create_transfer(magnet_url)
		control.hide()
		if result: control.okDialog(title='default', message=getLS(40017) % 'EasyDebrid')
		else: control.okDialog(title=getLS(40018), message=getLS(33586))
		return None

	def account_info_to_dialog(self):
		import datetime
		try:
			control.busy()
			account_info = self.account_info()
			if account_info['paid_until']:
				expires = datetime.datetime.fromtimestamp(account_info['paid_until'])
				days_remaining = (expires - datetime.datetime.today()).days
				expires = expires.strftime("%A, %B %d, %Y")
			else: days_remaining, expires = '0', 'Expired'
			items = []
			items += ['[B]Customer[/B]: %s' % account_info['id']]
			items += ['[B]Expires[/B]: %s' % expires]
			items += ['[B]Days Remaining[/B]: %s' % days_remaining]
			control.hide()
			return control.selectDialog(items, 'EasyDebrid')
		except: log_utils.error()
