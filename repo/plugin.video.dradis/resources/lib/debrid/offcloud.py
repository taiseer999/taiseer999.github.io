import re
import requests
from sys import argv, exit as sysexit
from threading import Thread
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules import string_tools
from resources.lib.modules.source_utils import supported_video_extensions

getLS = control.lang
getSetting = control.setting
base_url = 'https://offcloud.com/api/'
download_url = 'https://%s.offcloud.com/cloud/download/%s/%s'
zip_url = 'https://%s.offcloud.com/cloud/zip/%s/%s.zip'
remove_url = 'https://offcloud.com/cloud/remove/%s' # undocumented
stats_url = 'account/stats' # undocumented
history_url = 'cloud/history' # undocumented
explore_url = 'cloud/explore/%s'
files_url = 'cloud/list/%s'
status_url = 'cloud/status'
cache_url = 'cache'
cloud_url = 'cloud'
oc_icon = control.joinPath(control.artPath(), 'offcloud.png')
addonFanart = control.addonFanart()

session = requests.Session()
session.mount('https://offcloud.com', requests.adapters.HTTPAdapter(max_retries=1))


class Offcloud:
	name = "Offcloud"
	sort_priority = getSetting('offcloud.priority')
	def __init__(self):
		self.token = getSetting('offcloud.token')

	def _request(self, method, path, params=None, data=None):
		if not self.token: return
		params = params or {}
		params['key'] = self.token
		full_path = '%s%s' % (base_url, path)
		response = session.request(method, full_path, params=params, json=data, timeout=20)
		try: response.raise_for_status()
		except Exception as e: log_utils.log('offcloud error %s' % str(e))
		try: result = response.json()
		except: result = {}
		return result

	def _get(self, url):
		return self._request('get', url)

	def _post(self, url, data=None):
		return self._request('post', url, data=data)

	@staticmethod
	def requote_uri(url):
		return requests.utils.requote_uri(url)

	def build_url(self, server, request_id, file_name):
		return download_url % (server, request_id, file_name)

	def build_zip(self, server, request_id, file_name):
		return zip_url % (server, request_id, file_name)

	def requestid_from_url(self, url):
		match = re.search(r'download/[A-Za-z0-9]+/', url)
		if not match: return None
		request_id = match.group(0).split('/')[-2]
		return request_id

	def account_info(self):
		return self._get(stats_url)

	def torrent_info(self, request_id=''):
		url = explore_url % request_id
		return self._get(url)

	def delete_torrent(self, request_id=''):
		params = {'key': self.token}
		url = remove_url % request_id
		r = session.get(url, params=params, timeout=20)
		try: r = r.json()
		except: r = {}
		return r

	def unrestrict_link(self, link):
		return link

	def check_cache(self, hashlist):
		data = {'hashes': hashlist}
		result = self._post(cache_url, data=data)
		return result['cachedItems']

	def add_magnet(self, magnet):
		data = {'url': magnet}
		return self._post(cloud_url, data=data)

	def create_transfer(self, magnet_url):
		result = self.add_magnet(magnet_url)
		if result.get('status') not in ('created', 'downloaded'): return None
		return result.get('requestId', '')

	def display_magnet_pack(self, magnet_url, info_hash):
		try:
			extensions = supported_video_extensions()
			torrent = self.add_magnet(magnet_url)
			torrent_id = torrent['requestId']
			torrent_files = self.torrent_info(torrent_id)
			if isinstance(torrent_files, list): pass
			else: torrent_files = ['%s/%s' % (torrent['url'], torrent['fileName'])]
			torrent_files = [
				{'link': self.requote_uri(item),
				 'size': 0,
				 'torrent_id': torrent_id,
				 'filename': item.split('/')[-1]}
				for item in torrent_files
				if item.lower().endswith(tuple(extensions))
			]
			return torrent_files
		except Exception:
			if torrent_id: self.delete_torrent(torrent_id)
			return None

	def add_uncached_torrent(self, magnet_url, pack=False):
		control.busy()
		result = self.create_transfer(magnet_url)
		control.hide()
		if result: control.okDialog(title='default', message=getLS(40017) % 'Offcloud')
		else: control.okDialog(title=getLS(40018), message=getLS(33586))
		return None

	def user_cloud(self):
		return self._get(history_url)

	def user_cloud_clear(self):
		if not control.yesnoDialog(getLS(32056), '', ''): return
		files = self.user_cloud()
		if not files: return
		threads = []
		append = threads.append
		len_files = len(files)
		progressBG = control.progressDialogBG
		progressBG.create('Offcloud', 'Clearing cloud files')
		for count, i in enumerate(files, 1):
			try:
				req = Thread(target=self.delete_torrent, args=(i['requestId'],), name=i['fileName'])
				req.start()
				progressBG.update(int(count / len_files * 100), 'Deleting %s...' % req.name)
				req.join(1)
			except: pass
		try: progressBG.close()
		except: pass

	def delete_user_torrent(self, request_id, name):
		if not control.yesnoDialog(getLS(40050) % '?[CR]' + name, '', ''): return
		result = self.delete_torrent(request_id)
		if 'success' in result:
			control.notification(message='Offcloud: %s was removed' % name, icon=oc_icon)
			control.refresh()

	def user_cloud_to_listItem(self):
		sysaddon, syshandle = 'plugin://plugin.video.dradis/', int(argv[1])
		quote_plus = requests.utils.quote
		folder_str, deleteMenu = getLS(40046).upper(), getLS(40050)
		file_str, downloadMenu = getLS(40047).upper(), getLS(40048)
		folders = self.user_cloud()
		try: folders += [i for i in self.user_cloud()]
		except: pass
		for count, item in enumerate(folders, 1):
			try:
				if not item['status'] == 'downloaded': continue
				cm = []
				is_folder = item['isDirectory']
				folder_name = string_tools.strip_non_ascii_and_unprintable(item['fileName'])
				request_id, server = item['requestId'], item['server']
				status_str = '[COLOR %s]%s[/COLOR]' % (control.getHighlightColor(), item['status'].capitalize())
				cm.append((deleteMenu % 'Torrent', 'RunPlugin(%s?action=oc_DeleteUserTorrent&id=%s&name=%s)' %
					(sysaddon, request_id, quote_plus(folder_name))))
				if is_folder:
					label = '%02d | [B]%s[/B] | [B]%s[/B] | [I]%s [/I]' % (count, status_str, folder_str, folder_name)
					url = '%s?action=oc_BrowseUserTorrents&id=%s' % (sysaddon, request_id)
				else:
					label = '%02d | [B]%s[/B] | [B]%s[/B] | [I]%s [/I]' % (count, status_str, file_str, folder_name)
					link = self.requote_uri(self.build_url(server, request_id, folder_name))
					url = '%s?action=play_URL&url=%s&caller=offcloud&type=direct' % (sysaddon, link)
					cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&url=%s&caller=offcloud&type=direct)' %
						(sysaddon, quote_plus(name), quote_plus(oc_icon), link)))
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': oc_icon, 'poster': oc_icon, 'thumb': oc_icon, 'fanart': addonFanart, 'banner': oc_icon})
				item.setInfo(type='video', infoLabels='')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=is_folder)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def browse_user_torrents(self, folder_id):
		sysaddon, syshandle = 'plugin://plugin.video.dradis/', int(argv[1])
		quote_plus = requests.utils.quote
		extensions = supported_video_extensions()
		file_str, downloadMenu = getLS(40047).upper(), getLS(40048)
		files = self.torrent_info(folder_id)
		video_files = [i for i in files if i.lower().endswith(tuple(extensions))]
		for count, item in enumerate(video_files, 1):
			try:
				cm = []
				name = string_tools.strip_non_ascii_and_unprintable(item.split('/')[-1])
				label = '%02d | [B]%s[/B] | %.2f GB | [I]%s [/I]' % (count, file_str, 0, name)
				item = self.requote_uri(item)
				url = '%s?action=play_URL&url=%s&caller=offcloud&type=direct' % (sysaddon, item)
				cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&url=%s&caller=offcloud&type=direct)' %
					(sysaddon, quote_plus(name), quote_plus(oc_icon), item)))
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': oc_icon, 'poster': oc_icon, 'thumb': oc_icon, 'fanart': addonFanart, 'banner': oc_icon})
				item.setInfo(type='video', infoLabels='')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def account_info_to_dialog(self):
		try:
			account_info = self.account_info()
			items = []
			append = items.append
			append('[B]Email[/B]: %s' % account_info['email'])
			append('[B]userId[/B]: %s' % account_info['userId'])
			append('[B]Premium[/B]: %s' % account_info['isPremium'])
			append('[B]Expires[/B]: %s' % account_info['expirationDate'])
			append('[B]Cloud Limit[/B]: {:,}'.format(account_info['limits']['cloud']))
			return control.selectDialog(items, 'Offcloud')
		except: log_utils.error()
