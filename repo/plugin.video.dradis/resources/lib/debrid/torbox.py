import requests
from sys import argv, exit as sysexit
from threading import Thread
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules import string_tools
from resources.lib.modules.source_utils import supported_video_extensions

getLS = control.lang
getSetting = control.setting
FormatDateTime = "%Y-%m-%dT%H:%M:%SZ"
ip_url = 'https://api.ipify.org'
base_url = 'https://api.torbox.app/v1/api/'
download_url = 'torrents/requestdl'
download_usenet_url = 'usenet/requestdl'
remove_url = 'torrents/controltorrent'
remove_usenet_url = 'usenet/controlusenetdownload'
stats_url = 'user/me'
history_url = 'torrents/mylist'
history_usenet_url = 'usenet/mylist'
explore_url = 'torrents/mylist?id=%s'
explore_usenet_url = 'usenet/mylist?id=%s'
cache_url = 'torrents/checkcached'
cloud_url = 'torrents/createtorrent'
cloud_usenet_url = 'usenet/createusenetdownload'
tb_icon = control.joinPath(control.artPath(), 'torbox.png')
addonFanart = control.addonFanart()

session = requests.Session()
session.mount('https://api.torbox.app', requests.adapters.HTTPAdapter(max_retries=1))


class TorBox:
	name = "TorBox"
	sort_priority = getSetting('torbox.priority')
	def __init__(self):
		self.store_to_cloud = getSetting('torbox.saveToCloud') == 'true'
		self.token = getSetting('torbox.token')
		session.headers['Authorization'] = 'Bearer %s' % self.token

	def _request(self, method, path, params=None, json=None, data=None):
		if not self.token: return
		full_path = '%s%s' % (base_url, path)
		response = session.request(method, full_path, params=params, json=json, data=data, timeout=20)
		try: response.raise_for_status()
		except Exception as e: log_utils.log('torbox error %s' % str(e))
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
			date_string = account_info['data']['premium_expires_at']
			expires = datetime.datetime.strptime(date_string, FormatDateTime)
			days = (expires - datetime.datetime.today()).days
		except: days = None
		return days

	def account_info(self):
		return self._get(stats_url)

	def torrent_info(self, request_id=''):
		url = explore_url % request_id
		return self._get(url)

	def delete_torrent(self, request_id=''):
		data = {'torrent_id': request_id, 'operation': 'delete'}
		return self._post(remove_url, json=data)

	def delete_usenet(self, request_id=''):
		data = {'usenet_id': request_id, 'operation': 'delete'}
		return self._post(remove_usenet_url, json=data)

	def unrestrict_link(self, file_id):
		try: user_ip = requests.get(ip_url, timeout=2.0).text
		except: user_ip = ''
		params = {'user_ip': user_ip} if user_ip else {}
		torrent_id, file_id = file_id.split(',')
		params.update({'token': self.token, 'torrent_id': torrent_id, 'file_id': file_id})
		try: return self._get(download_url, params=params)['data']
		except: return None

	def unrestrict_usenet(self, file_id):
		try: user_ip = requests.get(ip_url, timeout=2.0).text
		except: user_ip = ''
		params = {'user_ip': user_ip} if user_ip else {}
		usenet_id, file_id = file_id.split(',')
		params.update({'token': self.token, 'usenet_id': usenet_id, 'file_id': file_id})
		try: return self._get(download_usenet_url, params=params)['data']
		except: return None

	def check_cache(self, hashlist):
		data = {'hashes': hashlist}
		result = self._post(cache_url, params={'format': 'list'}, json=data)
		return [i['hash'] for i in result['data']]

	def add_magnet(self, magnet):
		data = {'magnet': magnet, 'seed': 3, 'allow_zip': 'false'}
		return self._post(cloud_url, data=data)

	def add_nzb(self, nzb, name=''):
		data = {'link': nzb}
		if name: data['name'] = name
		return self._post(cloud_usenet_url, data=data)

	def create_transfer(self, link, name=''):
		if link.startswith('magnet'): key, result = 'torrent_id', self.add_magnet(link)
		else: key, result = 'usenetdownload_id', self.add_nzb(link, name)
		if not result['success']: return ''
		return result['data'].get(key, '')

	def display_magnet_pack(self, magnet_url, info_hash):
		try:
			extensions = supported_video_extensions()
			torrent_id = self.create_transfer(magnet_url)
			torrent_files = self.torrent_info(torrent_id)
			torrent_files = [
				{'link': '%d,%d' % (torrent_id, item['id']),
				 'size': item['size'] / 1073741824,
				 'torrent_id': torrent_id,
				 'filename': item['short_name']}
				for item in torrent_files['data']['files']
				if item['short_name'].lower().endswith(tuple(extensions))
			]
			return torrent_files
		except Exception:
			if torrent_id: self.delete_torrent(torrent_id)
			return None

	def add_uncached_torrent(self, magnet_url, pack=False):
		control.busy()
		result = self.create_transfer(magnet_url)
		control.hide()
		if result: control.okDialog(title='default', message=getLS(40017) % 'TorBox')
		else: control.okDialog(title=getLS(40018), message=getLS(33586))
		return False

	def add_uncached_nzb(self, nzb_url, name='', pack=False):
		control.busy()
		result = self.create_transfer(nzb_url, name)
		control.hide()
		if result: control.okDialog(title='default', message=getLS(40017) % 'TorBox')
		else: control.okDialog(title=getLS(40018), message=getLS(33586))
		return False

	def user_cloud(self, request_id=None):
		url = explore_url % request_id if request_id else history_url
		return self._get(url)

	def user_cloud_usenet(self, request_id=None):
		url = explore_usenet_url % request_id if request_id else history_usenet_url
		return self._get(url)

	def user_cloud_clear(self):
		if not control.yesnoDialog(getLS(32056), '', ''): return
		data = {'all': True, 'operation': 'delete'}
		self._post(remove_url, json=data)
		self._post(remove_usenet_url, json=data)

	def delete_user_torrent(self, request_id, mediatype, name):
		if not control.yesnoDialog(getLS(40050) % '?[CR]' + name, '', ''): return
		result = self.delete_usenet(request_id) if mediatype == 'usenet' else self.delete_torrent(request_id)
		if result['success']:
			control.notification(message='TorBox: %s was removed' % name, icon=tb_icon)
			control.refresh()

	def user_cloud_to_listItem(self, mediatype='torrent'):
		sysaddon, syshandle = 'plugin://plugin.video.dradis/', int(argv[1])
		quote_plus = requests.utils.quote
		folder_str, deleteMenu = getLS(40046).upper(), getLS(40050)
		file_str, downloadMenu = getLS(40047).upper(), getLS(40048)
		folders = []
		function = self.user_cloud_usenet if mediatype == 'usenet' else self.user_cloud
		try: folders += [{**i, 'mediatype': mediatype} for i in function()['data']]
		except: pass
		folders.sort(key=lambda k: k['updated_at'], reverse=True)
		for count, item in enumerate(folders, 1):
			try:
				if not item['download_finished']: continue
				cm = []
				folder_name = string_tools.strip_non_ascii_and_unprintable(item['name'])
				status_str = '[COLOR %s]%s[/COLOR]' % (control.getHighlightColor(), item['download_state'].capitalize())
				cm.append((deleteMenu % 'Torrent', 'RunPlugin(%s?action=tb_DeleteUserTorrent&id=%s&mediatype=%s&name=%s)' %
					(sysaddon, item['id'], item['mediatype'], quote_plus(folder_name))))
				label = '%02d | [B]%s[/B] | [B]%s[/B] | [I]%s [/I]' % (count, status_str, folder_str, folder_name)
				url = '%s?action=tb_BrowseUserTorrents&id=%s&mediatype=%s' % (sysaddon, item['id'], item['mediatype'])
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': tb_icon, 'poster': tb_icon, 'thumb': tb_icon, 'fanart': addonFanart, 'banner': tb_icon})
				item.setInfo(type='video', infoLabels='')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def browse_user_torrents(self, folder_id, mediatype):
		sysaddon, syshandle = 'plugin://plugin.video.dradis/', int(argv[1])
		quote_plus = requests.utils.quote
		extensions = supported_video_extensions()
		file_str, downloadMenu = getLS(40047).upper(), getLS(40048)
		files = self.user_cloud_usenet(folder_id) if mediatype == 'usenet' else self.user_cloud(folder_id)
		video_files = [i for i in files['data']['files'] if i['short_name'].lower().endswith(tuple(extensions))]
		for count, item in enumerate(video_files, 1):
			try:
				cm = []
				name = string_tools.strip_non_ascii_and_unprintable(item['short_name'])
				size = item['size']
				display_size = float(int(size)) / 1073741824
				label = '%02d | [B]%s[/B] | %.2f GB | [I]%s [/I]' % (count, file_str, display_size, name)
				item = '%d,%d' % (int(folder_id), item['id'])
				url = '%s?action=play_URL&url=%s&caller=torbox&mediatype=%s&type=unrestrict' % (sysaddon, item, mediatype)
				cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&url=%s&caller=torbox&mediatype=%s&type=unrestrict)' %
					(sysaddon, quote_plus(name), quote_plus(tb_icon), item, mediatype)))
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': tb_icon, 'poster': tb_icon, 'thumb': tb_icon, 'fanart': addonFanart, 'banner': tb_icon})
				item.setInfo(type='video', infoLabels='')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def account_info_to_dialog(self):
		from datetime import datetime
		from resources.lib.modules import cleandate
		try:
			control.busy()
			plans = {0: 'Free plan', 1: 'Essential plan', 2: 'Pro plan', 3: 'Standard plan'}
			account_info = self.account_info()
			account_info = account_info['data']
			expires = cleandate.datetime_from_string(account_info['premium_expires_at'], FormatDateTime, date_only=False)
			days_remaining = (expires - datetime.today()).days
			expires = expires.strftime("%A, %B %d, %Y")
			items = []
			items += ['[B]Email[/B]: %s' % account_info['email']]
			items += ['[B]Customer[/B]: %s' % account_info['customer']]
			items += ['[B]Plan[/B]: %s' % plans[account_info['plan']]]
			items += ['[B]Expires[/B]: %s' % expires]
			items += ['[B]Days Remaining[/B]: %s' % days_remaining]
			items += ['[B]Downloaded[/B]: %s' % account_info['total_downloaded']]
			control.hide()
			return control.selectDialog(items, 'TorBox')
		except: log_utils.error()
