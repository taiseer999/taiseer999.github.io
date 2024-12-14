import requests
from sys import argv, exit as sysexit
from threading import Thread
from urllib.parse import urlencode
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules import string_tools
from resources.lib.modules.source_utils import supported_video_extensions

getLS = control.lang
getSetting = control.setting
base_url = 'https://api.torbox.app/v1/api'
tb_icon = control.joinPath(control.artPath(), 'torbox.png')
addonFanart = control.addonFanart()

session = requests.Session()
session.mount(base_url, requests.adapters.HTTPAdapter(max_retries=1))

class TorBox:
	download = '/torrents/requestdl'
	remove = '/torrents/controltorrent'
	stats = '/user/me'
	history = '/torrents/mylist'
	explore = '/torrents/mylist?id=%s'
	cache = '/torrents/checkcached'
	cloud = '/torrents/createtorrent'

	def __init__(self):
		self.name = 'TorBox'
		self.user_agent = 'Mozilla/5.0'
		self.api_key = getSetting('torboxtoken')
		self.sort_priority = getSetting('torbox.priority')
		self.store_to_cloud = getSetting('torbox.saveToCloud') == 'true'
		self.timeout = 28.0

	def _request(self, method, path, params=None, json=None, data=None):
		if not self.api_key: return
		session.headers['Authorization'] = 'Bearer %s' % self.api_key
		full_path = '%s%s' % (base_url, path)
		response = session.request(method, full_path, params=params, json=json, data=data, timeout=self.timeout)
		try: response.raise_for_status()
		except Exception as e: log_utils.log('torbox error', f"{e}\n{response.text}")
		try: result = response.json()
		except: result = {}
		return result

	def _GET(self, url, params=None):
		return self._request('get', url, params=params)

	def _POST(self, url, params=None, json=None, data=None):
		return self._request('post', url, params=params, json=json, data=data)

	def add_headers_to_url(self, url):
		return url + '|' + urlencode(self.headers())

	def headers(self):
		return {'User-Agent': self.user_agent}

	def account_info(self):
		return self._GET(self.stats)

	def torrent_info(self, request_id=''):
		url = self.explore % request_id
		return self._GET(url)

	def delete_torrent(self, request_id=''):
		data = {'torrent_id': request_id, 'operation': 'delete'}
		return self._POST(self.remove, json=data)

	def unrestrict_link(self, file_id):
		torrent_id, file_id = file_id.split(',')
		params = {'token': self.api_key, 'torrent_id': torrent_id, 'file_id': file_id, 'user_ip': True}
		try: return self._GET(self.download, params=params)['data']
		except: return None

	def check_cache_single(self, hash):
		return self._GET(self.cache, params={'hash': hash, 'format': 'list'})

	def check_cache(self, hashlist):
		data = {'hashes': hashlist}
		return self._POST(self.cache, params={'format': 'list'}, json=data)

	def add_magnet(self, magnet):
		data = {'magnet': magnet, 'seed': 3, 'allow_zip': False}
		return self._POST(self.cloud, data=data)

	def create_transfer(self, magnet_url):
		result = self.add_magnet(magnet_url)
		if not result['success']: return ''
		return result['data'].get('torrent_id', '')

	def resolve_magnet(self, magnet_url, info_hash, season, episode, title):
		from resources.lib.modules.source_utils import seas_ep_filter, extras_filter
		try:
			file_url, match = None, False
			extensions = supported_video_extensions()
			extras_filtering_list = tuple(i for i in extras_filter() if not i in title.lower())
			check = self.check_cache_single(info_hash)
			match = info_hash in [i['hash'] for i in check['data']]
			if not match: return None
			torrent = self.add_magnet(magnet_url)
			if not torrent['success']: return None
			torrent_id = torrent['data']['torrent_id']
			torrent_files = self.torrent_info(torrent_id)
			selected_files = [
				{'link': '%d,%d' % (torrent_id, i['id']), 'filename': i['short_name'], 'size': i['size']}
				for i in torrent_files['data']['files'] if i['short_name'].lower().endswith(tuple(extensions))
			]
			if not selected_files: return None
			if season:
				selected_files = [i for i in selected_files if seas_ep_filter(season, episode, i['filename'])]
			else:
				if self._m2ts_check(selected_files): raise Exception('_m2ts_check failed')
				selected_files = [i for i in selected_files if not any(x in i['filename'] for x in extras_filtering_list)]
				selected_files.sort(key=lambda k: k['size'], reverse=True)
			if not selected_files: return None
			file_key = selected_files[0]['link']
			file_url = self.unrestrict_link(file_key)
			if not self.store_to_cloud: Thread(target=self.delete_torrent, args=(torrent_id,)).start()
			return file_url
		except Exception as e:
			log_utils.error('TorBox: Error RESOLVE MAGNET "%s" ' % magnet_url)
			if torrent_id: Thread(target=self.delete_torrent, args=(torrent_id,)).start()
			return None

	def display_magnet_pack(self, magnet_url, info_hash):
		try:
			extensions = supported_video_extensions()
			torrent = self.add_magnet(magnet_url)
			if not torrent['success']: return None
			torrent_id = torrent['data']['torrent_id']
			torrent_files = self.torrent_info(torrent_id)
			torrent_files = [
				{'link': '%d,%d' % (torrent_id, item['id']), 'filename': item['short_name'], 'size': item['size'] / 1073741824}
				for item in torrent_files['data']['files'] if item['short_name'].lower().endswith(tuple(extensions))
			]
			self.delete_torrent(torrent_id)
			return torrent_files
		except Exception:
			if torrent_id: self.delete_torrent(torrent_id)
			return None

	def add_uncached_torrent(self, magnet_url, pack=False):
		control.busy()
		result = self.create_transfer(magnet_url)
		control.hide()
		if result: control.okDialog(title='default', message=getLS(40017) % 'TorBox')
		else: return control.okDialog(title=getLS(40018), message=getLS(33586))
		return True

	def _m2ts_check(self, folder_items):
		for item in folder_items:
			if item['filename'].endswith('.m2ts'): return True
		return False

	def auth(self):
		api_key = control.dialog.input('TorBox API Key:')
		if not api_key: return
		self.api_key = api_key
		r = self.account_info()
		customer = r['data']['customer']
		control.setSetting('torboxtoken', api_key)
		control.setSetting('torbox.username', customer)
		control.notification(message='TorBox succesfully authorized', icon=tb_icon)
		return True

	def remove_auth(self):
		try:
			self.api_key = ''
			control.setSetting('torboxtoken', '')
			control.setSetting('torbox.username', '')
			control.notification(title='TorBox', message=40009)
		except: log_utils.error()

	def account_info_to_dialog(self):
		try:
			control.busy()
			plans = {0: 'Free plan', 1: 'Essential plan', 2: 'Pro plan', 3: 'Standard plan'}
			account_info = self.account_info()
			account_info = account_info['data']
			items = []
			items += ['[B]Email[/B]: %s' % account_info['email']]
			items += ['[B]Customer[/B]: %s' % account_info['customer']]
			items += ['[B]Plan[/B]: %s' % plans[account_info['plan']]]
			items += ['[B]Expires[/B]: %s' % account_info['premium_expires_at']]
			items += ['[B]Downloaded[/B]: %s' % account_info['total_downloaded']]
			control.hide()
			return control.selectDialog(items, 'TorBox')
		except: log_utils.error()

	def user_cloud(self):
		url = self.history
		return self._GET(url)

	def user_cloud_clear(self):
		if not control.yesnoDialog(getLS(32056), '', ''): return
		data = {'all': True, 'operation': 'delete'}
		self._POST(self.remove, json=data)
		self._POST(self.remove_usenet, json=data)

	def user_cloud_to_listItem(self, folder_id=None):
		sysaddon, syshandle = 'plugin://plugin.video.infinity/', int(argv[1])
		quote_plus = requests.utils.quote
		highlight_color = getSetting('highlight.color')
		folder_str, deleteMenu = getLS(40046).upper(), getLS(40050)
		file_str, downloadMenu = getLS(40047).upper(), getLS(40048)
		cloud_dict = self.user_cloud()
		cloud_dict = [i for i in cloud_dict['data'] if i['download_finished']]
		for count, item in enumerate(cloud_dict, 1):
			try:
				cm = []
				folder_name = string_tools.strip_non_ascii_and_unprintable(item['name'])
				status_str = '[COLOR %s]%s[/COLOR]' % (highlight_color, item['download_state'].capitalize())
				cm.append((deleteMenu % 'Torrent', 'RunPlugin(%s?action=tb_DeleteUserTorrent&id=%s&name=%s)' %
					(sysaddon, item['id'], quote_plus(folder_name))))
				label = '%02d | [B]%s[/B] | [B]%s[/B] | [I]%s [/I]' % (count, status_str, folder_str, folder_name)
				url = '%s?action=tb_BrowseUserTorrents&id=%s' % (sysaddon, item['id'])
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': tb_icon, 'poster': tb_icon, 'thumb': tb_icon, 'fanart': addonFanart, 'banner': tb_icon})
				item.setInfo(type='video', infoLabels='')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def browse_user_torrents(self, folder_id):
		sysaddon, syshandle = 'plugin://plugin.video.infinity/', int(argv[1])
		quote_plus = requests.utils.quote
		extensions = supported_video_extensions()
		file_str, downloadMenu = getLS(40047).upper(), getLS(40048)
		torrent_files = self.torrent_info(folder_id)
		video_files = [i for i in torrent_files['data']['files'] if i['short_name'].lower().endswith(tuple(extensions))]
		for count, item in enumerate(video_files, 1):
			try:
				cm = []
				name = string_tools.strip_non_ascii_and_unprintable(item['short_name'])
				size = item['size']
				display_size = float(int(size)) / 1073741824
				label = '%02d | [B]%s[/B] | %.2f GB | [I]%s [/I]' % (count, file_str, display_size, name)
				item = '%d,%d' % (int(folder_id), item['id'])
				url = '%s?action=play_URL&url=%s&caller=torbox&type=unrestrict' % (sysaddon, item)
				cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&url=%s&caller=torbox&type=unrestrict)' %
					(sysaddon, quote_plus(name), quote_plus(tb_icon), item)))
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': tb_icon, 'poster': tb_icon, 'thumb': tb_icon, 'fanart': addonFanart, 'banner': tb_icon})
				item.setInfo(type='video', infoLabels='')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def delete_user_torrent(self, request_id, name):
		if not control.yesnoDialog(getLS(40050) % '?\n' + name, '', ''): return
		result = self.delete_torrent(request_id)
		if result['success']:
			control.notification(message='TorBox: %s was removed' % name, icon=tb_icon)
			control.refresh()
