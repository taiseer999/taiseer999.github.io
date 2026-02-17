"""
	Venom Add-on
"""

import requests
from requests.adapters import HTTPAdapter
from sys import argv, exit as sysexit
from urllib3.util.retry import Retry
from urllib.parse import quote_plus
from resources.lib.database import cache
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules import string_tools
from resources.lib.modules.source_utils import supported_video_extensions

getLS = control.lang
getSetting = control.setting
base_url = 'https://api.alldebrid.com/'
unrestrict_link_url = 'v4/link/unlock'
transfer_create_url = 'v4/magnet/upload'
transfer_info_url = 'v4.1/magnet/status'
transfer_delete_url = 'v4/magnet/delete'
transfer_restart_url = 'v4/magnet/restart'
ad_icon = control.joinPath(control.artPath(), 'alldebrid.png')
addonFanart = control.addonFanart()
invalid_extensions = ('.bmp', '.gif', '.jpg', '.nfo', '.part', '.png', '.rar', '.sample.', '.srt', '.txt', '.zip')

session = requests.Session()
retries = Retry(total=1, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount('https://api.alldebrid.com', HTTPAdapter(max_retries=retries, pool_maxsize=100))


class AllDebrid:
	name = "AllDebrid"
	sort_priority = getSetting('alldebrid.priority')
	@staticmethod
	def flatten_magnet_files(files_list):
		def flatten(items):
			for i in items:
				if not isinstance(i, dict): continue
				if 'e' in i: flatten(i['e'])
				else: files_append(i)
		files = []
		files_append = files.append
		flatten(files_list)
		return files

	def __init__(self):
		self.server_notifications = getSetting('alldebrid.server.notifications')
		self.external_cache = getSetting('alldebrid.check_cache') == 'true'
		self.store_to_cloud = getSetting('alldebrid.saveToCloud') == 'true'
		self.token = getSetting('alldebrid.token')
		session.headers['Authorization'] = f"Bearer {self.token}"

	def _get(self, url, params=None):
		if self.token == '': return None
		response = None
		url = base_url + url

		try:
			response = session.get(url, params=params, timeout=20).json()
			if 'status' in response and response.get('status') == 'error':
				if self.server_notifications: control.notification(message=response.get('error').get('message'), icon=ad_icon)
				log_utils.log('AllDebrid: %s' % response.get('error').get('message'), level=log_utils.LOGWARNING)
			if response.get('status') == 'success' and 'data' in response: response = response['data']
		except: log_utils.error()
		return response

	def _post(self, url, data=None):
		if self.token == '': return None
		response = None
		url = base_url + url

		try:
			response = session.post(url, data=data, timeout=20).json()
			if 'status' in response and response.get('status') == 'error':
				if self.server_notifications: control.notification(message=response.get('error').get('message'), icon=ad_icon)
				log_utils.log('AllDebrid: %s' % response.get('error').get('message'), level=log_utils.LOGWARNING)
			if response.get('status') == 'success' and 'data' in response: response = response['data']
		except: log_utils.error()
		return response

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

	def transfer_info(self, transfer_id):
		try:
			params = {'id': transfer_id}
			result = self._get(transfer_info_url, params)
			return result['magnets']
		except: log_utils.error()

	def delete_torrent(self, transfer_id):
		return self.delete_transfer(transfer_id)

	def unrestrict_link(self, link, return_all=False):
		try:
			params = {'link': link}
			response = self._get(unrestrict_link_url, params)
			if return_all: return response
			else: return response['link']
		except: log_utils.error()

	def check_cache(self, hashes):
		try:
			data = {'magnets[]': hashes}
			response = self._post('v4/magnet/instant', data)
			return response
		except: log_utils.error()

	def create_transfer(self, magnet):
		try:
			params = {'magnets[]': magnet}
			result = self._get(transfer_create_url, params)
			result = result['magnets'][0]
			return result.get('id', '')
		except: log_utils.error()

	def display_magnet_pack(self, magnet_url, info_hash):
		try:
			extensions = supported_video_extensions()
			transfer_id = self.create_transfer(magnet_url)
			for key in ['completionDate'] * 3:
				control.sleep(500)
				transfer_info = self.transfer_info(transfer_id)
				if transfer_info[key]: break
			else: raise Exception('uncached')
			transfer_info['links'] = self.flatten_magnet_files(transfer_info['files'])
			transfer_files = [
				{'link': item['l'],
				 'size': float(item['s']) / 1073741824,
				 'torrent_id': transfer_id,
				 'filename': item['n']}
				for item in transfer_info['links']
				if item['n'].lower().endswith(tuple(extensions))
			]
			return transfer_files
		except Exception:
			log_utils.error()
			if transfer_id: self.delete_torrent(transfer_id)

	def add_uncached_torrent(self, magnet_url, pack=False):
		def _return_failed(message=getLS(33586)):
			try: control.progressDialog.close()
			except: pass
			self.delete_transfer(transfer_id)
			control.hide()
			control.sleep(500)
			control.okDialog(title=getLS(40018), message=message)
			return False
		control.busy()
		transfer_id = self.create_transfer(magnet_url)
		if not transfer_id: return _return_failed()
		transfer_info = self.transfer_info(transfer_id)
		if not transfer_info: return _return_failed()
		# if pack:
			# control.hide()
			# control.okDialog(title='default', message=getLS(40017) % getLS(40059))
			# return True
		interval = 5
		line = '%s\n%s\n%s'
		line1 = '%s...' % (getLS(40017) % getLS(40059))
		line2 = transfer_info['filename']
		line3 = transfer_info['status']
		control.progressDialog.create(getLS(40018), line % (line1, line2, line3))
		while not transfer_info['statusCode'] == 4:
			control.sleep(1000 * interval)
			transfer_info = self.transfer_info(transfer_id)
			file_size = transfer_info['size']
			line2 = transfer_info['filename']
			if transfer_info['statusCode'] == 1:
				download_speed = round(float(transfer_info['downloadSpeed']) / (1000**2), 2)
				progress = int(float(transfer_info['downloaded']) / file_size * 100) if file_size > 0 else 0
				line3 = getLS(40016) % (download_speed, transfer_info['seeders'], progress, round(float(file_size) / (1000 ** 3), 2))
			elif transfer_info['statusCode'] == 3:
				upload_speed = round(float(transfer_info['uploadSpeed']) / (1000 ** 2), 2)
				progress = int(float(transfer_info['uploaded']) / file_size * 100) if file_size > 0 else 0
				line3 = getLS(40015) % (upload_speed, progress, round(float(file_size) / (1000 ** 3), 2))
			else:
				line3 = transfer_info['status']
				progress = 0
			control.progressDialog.update(progress, line % (line1, line2, line3))
			if control.monitor.abortRequested(): return sysexit()
			try:
				if control.progressDialog.iscanceled():
					if control.yesnoDialog('Delete AD download also?', 'No will continue the download', 'but close dialog'):
						return _return_failed(getLS(40014))
					else:
						control.progressDialog.close()
						control.hide()
						return False
			except: pass
			if 5 <= transfer_info['statusCode'] <= 10: return _return_failed()
		control.sleep(1000 * interval)
		try: control.progressDialog.close()
		except: pass
		control.hide()
		return True

	def valid_url(self, host):
		try:
			self.hosts = self.get_hosts()
			if not self.hosts['AllDebrid']: return False
			if any(host in item for item in self.hosts['AllDebrid']): return True
			return False
		except: log_utils.error()

	def get_hosts(self):
		url = 'v4/hosts'
		hosts_dict = {'AllDebrid': []}
		hosts = []
		extend = hosts.extend
		try:
			result = cache.get(self._get, 168, url)
			result = result['hosts']
			for k, v in result.items():
				try: extend(v['domains'])
				except: pass
			hosts_dict['AllDebrid'] = list(set(hosts))
		except: log_utils.error()
		return hosts_dict

	def user_cloud(self):
		try:
			url = 'v4.1/magnet/status'
			return self._get(url)
		except: log_utils.error()

	def user_transfers(self):
		try:
			url = 'v4/user/history'
			return self._get(url)
		except: log_utils.error()

	def delete_transfer(self, transfer_id, folder_name=None, silent=True):
		try:
			if not silent and not control.yesnoDialog(getLS(40050) % '?[CR]' + folder_name, '', ''): return
			params = {'id': transfer_id}
			response = self._get(transfer_delete_url, params)
			if not silent and response and 'message' in response:
				if self.server_notifications: control.notification(message=response.get('message'), icon=ad_icon)
				control.refresh()
		except: log_utils.error()

	def restart_transfer(self, transfer_id, folder_name=None, silent=True):
		try:
			if not silent and not control.yesnoDialog(getLS(40007) % '[CR]' + folder_name, '', ''): return
			params = {'id': transfer_id}
			response = self._get(transfer_restart_url, params)
			if not silent and response and 'message' in response:
				if self.server_notifications: control.notification(message=response.get('message'), icon=ad_icon)
				control.refresh()
		except: log_utils.error()

	def user_cloud_to_listItem(self):
		sysaddon, syshandle = 'plugin://plugin.video.dradis/', int(argv[1])
		folder_str, deleteMenu = getLS(40046).upper(), getLS(40050)
		folders = self.user_cloud()['magnets']
		for count, item in enumerate(folders, 1):
			try:
				if not item['statusCode'] == 4: continue
				cm = []
				folder_name = string_tools.strip_non_ascii_and_unprintable(item['filename'])
				status_str = '[COLOR %s]%s[/COLOR]' % (control.getHighlightColor(), item['status'].capitalize())
				label = '%02d | [B]%s[/B] | [B]%s[/B] | [I]%s [/I]' % (count, status_str, folder_str, folder_name)
				url = '%s?action=ad_BrowseUserCloud&source=%s' % (sysaddon, item['id'])
				cm.append((deleteMenu % 'Transfer', 'RunPlugin(%s?action=ad_DeleteTransfer&id=%s&name=%s)' %
					(sysaddon, item['id'], folder_name)))
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': ad_icon, 'poster': ad_icon, 'thumb': ad_icon, 'fanart': addonFanart, 'banner': ad_icon})
				item.setInfo(type='video', infoLabels='')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def browse_user_cloud(self, folder):
		sysaddon, syshandle = 'plugin://plugin.video.dradis/', int(argv[1])
		extensions = supported_video_extensions()
		file_str, downloadMenu, deleteMenu = getLS(40047).upper(), getLS(40048), getLS(40050)
		torrent_folder = self.transfer_info(folder)
		links = self.flatten_magnet_files(torrent_folder['files'])
		for count, item in enumerate(links, 1):
			try:
				cm = []
				name = string_tools.strip_non_ascii_and_unprintable(item['n'])
				if name.lower().endswith(invalid_extensions): continue
				if not name.lower().endswith(tuple(extensions)): continue
				url_link = item['l']
				size = item['s']
				display_size = float(int(size)) / 1073741824
				label = '%02d | [B]%s[/B] | %.2f GB | [I]%s [/I]' % (count, file_str, display_size, name)
				url = '%s?action=play_URL&url=%s&caller=alldebrid&type=unrestrict' % (sysaddon, url_link)
				cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&url=%s&caller=alldebrid)' %
								(sysaddon, quote_plus(name), quote_plus(ad_icon), url_link)))
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': ad_icon, 'poster': ad_icon, 'thumb': ad_icon, 'fanart': addonFanart, 'banner': ad_icon})
				item.setInfo(type='video', infoLabels='')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def user_transfers_to_listItem(self):
		from datetime import datetime
		sysaddon, syshandle = 'plugin://plugin.video.dradis/', int(argv[1])
		extensions = supported_video_extensions()
		file_str, downloadMenu, deleteMenu = getLS(40047).upper(), getLS(40048), getLS(40050)
		files = self.user_transfers()['links']
		video_files = [i for i in files if i['filename'].lower().endswith(tuple(extensions))]
		video_files.sort(key=lambda k: k['date'], reverse=True)
		for count, item in enumerate(video_files, 1):
			try:
				cm = []
				name = string_tools.strip_non_ascii_and_unprintable(item['filename'])
				size = float(int(item['size'])) / 1073741824
				datetime_object = datetime.fromtimestamp(item['date']).strftime('%Y-%m-%d')
				label = '%02d | %.2f GB | %s | [I]%s [/I]' % (count, size, datetime_object, name)
				url_link = item['link_dl']
				url = '%s?action=play_URL&url=%s' % (sysaddon, url_link)
				cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&url=%s&caller=alldebrid)' %
								(sysaddon, quote_plus(name), quote_plus(ad_icon), url_link)))
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': ad_icon, 'poster': ad_icon, 'thumb': ad_icon, 'fanart': addonFanart, 'banner': ad_icon})
				item.setInfo(type='video', infoLabels='')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def account_info_to_dialog(self):
		from datetime import datetime
		try:
			account_info = self.account_info()['user']
			username = account_info['username']
			email = account_info['email']
			status = 'Premium' if account_info['isPremium'] else 'Not Active'
			expires = datetime.fromtimestamp(account_info['premiumUntil'])
			days_remaining = (expires - datetime.today()).days
			heading = getLS(40059).upper()
			items = []
			items += [getLS(40036) % username]
			items += [getLS(40035) % email]
			items += [getLS(40037) % status]
			items += [getLS(40041) % expires]
			items += [getLS(40042) % days_remaining]
			return control.selectDialog(items, 'AllDebrid')
		except: log_utils.error()
