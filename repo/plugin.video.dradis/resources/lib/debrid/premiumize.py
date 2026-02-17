"""
	Venom Add-on
"""

import requests
from requests.adapters import HTTPAdapter
from sys import argv, exit as sysexit
from urllib3.util.retry import Retry
from urllib.parse import quote_plus, urlencode
from resources.lib.database import cache
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules import string_tools
from resources.lib.modules.source_utils import supported_video_extensions

getLS = control.lang
getSetting = control.setting
user_agent = 'Dradis/%s' % control.getDradisVersion()
CLIENT_ID = '522962560' # used to auth
base_url = 'https://www.premiumize.me/api/'
folder_list_url = 'folder/list'
folder_rename_url = 'folder/rename'
folder_delete_url = 'folder/delete'
item_listall_url = 'item/listall'
item_details_url = 'item/details'
item_delete_url = 'item/delete'
item_rename_url = 'item/rename'
transfer_create_url = 'transfer/create'
transfer_directdl_url = 'transfer/directdl'
transfer_list_url = 'transfer/list'
transfer_clearfinished_url = 'transfer/clearfinished'
transfer_delete_url = 'transfer/delete'
account_info_url = 'account/info'
cache_check_url = 'cache/check'
list_services_path_url = 'services/list'
pm_icon = control.joinPath(control.artPath(), 'premiumize.png')
addonFanart = control.addonFanart()

session = requests.Session()
retries = Retry(total=1, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount('https://www.premiumize.me', HTTPAdapter(max_retries=retries, pool_maxsize=100))


class Premiumize:
	name = "Premiumize.me"
	sort_priority = getSetting('premiumize.priority')
	def __init__(self):
		self.hosts = []
		self.patterns = []
		self.server_notifications = getSetting('premiumize.server.notifications')
		self.store_to_cloud = getSetting('premiumize.saveToCloud') == 'true'
		self.token = getSetting('premiumize.token')
		self.headers = {'User-Agent': user_agent , 'Authorization': 'Bearer %s' % self.token}
		session.headers.update(self.headers)

	def _get(self, url):
		if self.token == '': return None
		response = None
		url = base_url + url

		try:
			response = session.get(url, timeout=20).json()
			# if response.status_code in (200, 201): response = response.json() # need status code checking for server maintenance
			if 'status' in response and response.get('status') == 'error':
				if self.server_notifications: control.notification(message=response.get('message'), icon=pm_icon)
				log_utils.log('Premiumize.me: %s' % response.get('message'), level=log_utils.LOGWARNING)
		except: log_utils.error()
		return response

	def _post(self, url, data=None):
		if self.token == '': return None
		response = None
		url = base_url + url

		try:
			response = session.post(url, data=data, timeout=20).json()
			# if response.status_code in (200, 201): response = response.json() # need status code checking for server maintenance
			if 'status' in response and response.get('status') == 'error':
				if 'You already have this job added' in response.get('message'): return None
				if self.server_notifications: control.notification(message=response.get('message'), icon=pm_icon)
				log_utils.log('Premiumize.me: %s' % response.get('message'), level=log_utils.LOGWARNING)
		except: log_utils.error()
		return response

	def add_headers_to_url(self, url):
		return url + '|' + urlencode(self.headers)

	def days_remaining(self):
		import datetime
		try:
			account_info = self.account_info()
			expires = datetime.datetime.fromtimestamp(account_info['premium_until'])
			days = (expires - datetime.datetime.today()).days
		except: days = None
		return days

	def account_info(self):
		try:
			return self._get(account_info_url)
		except: log_utils.error()
		return None

	def list_transfer(self):
		return self._get(transfer_list_url)

	def unrestrict_link(self, link):
		try:
			data = {'src': link}
			response = self._post(transfer_directdl_url, data)
			try: return self.add_headers_to_url(response['content'][0]['link'])
			except: return None
		except: log_utils.error()

	def check_cache(self, hashList):
		try:
			data = {'items[]': hashList}
			response = self._post(cache_check_url, data)
			try: return [h for h, cached in zip(hashList, response['response']) if cached]
			except: return False
		except: log_utils.error()

	def create_transfer(self, src,  folder_id=0):
		try:
			data = {'src': src, 'folder_id': folder_id}
			return self._post(transfer_create_url, data)
		except: log_utils.error()

	def display_magnet_pack(self, magnet_url, info_hash):
		try:
			extensions = supported_video_extensions()
			transfer = self._post(transfer_directdl_url, {'src': magnet_url})
			transfer_files = transfer['content']
			transfer_files = [
				{'link': item['link'],
				 'size': float(item['size']) / 1073741824,
				 'filename': item['path'].split('/')[-1]}
				for item in transfer_files
				if item['path'].lower().endswith(tuple(extensions))
			]
			return transfer_files
		except Exception:
			return None

	def add_uncached_torrent(self, magnet_url, pack=False):
		def _transfer_info(transfer_id):
			info = self.list_transfer()
			if 'status' in info and info['status'] == 'success':
				for item in info['transfers']:
					if item['id'] == transfer_id: return item
			return {}
		def _return_failed(message=getLS(33586)):
			try: control.progressDialog.close()
			except: pass
			self.delete_transfer(transfer_id)
			control.hide()
			control.sleep(500)
			control.okDialog(title=getLS(40018), message=message)
			return False
		control.busy()
		extensions = supported_video_extensions()
		transfer_id = self.create_transfer(magnet_url)
		if not transfer_id: return control.hide()
		if not transfer_id['status'] == 'success': return _return_failed()
		transfer_id = transfer_id['id']
		transfer_info = _transfer_info(transfer_id)
		if not transfer_info: return _return_failed()
		# if pack:
			# control.hide()
			# control.okDialog(title='default', message=getLS(40017) % getLS(40057))
			# return True
		interval = 5
		line = '%s\n%s\n%s'
		line1 = '%s...' % (getLS(40017) % getLS(40057))
		line2 = transfer_info['name']
		line3 = transfer_info['message']
		control.progressDialog.create(getLS(40018), line % (line1, line2, line3))
		while not transfer_info['status'] == 'seeding':
			control.sleep(1000 * interval)
			transfer_info = _transfer_info(transfer_id)
			line3 = transfer_info['message']
			control.progressDialog.update(int(float(transfer_info['progress']) * 100), line % (line1, line2, line3))
			if control.monitor.abortRequested(): return sysexit()
			try:
				if control.progressDialog.iscanceled():
					if control.yesnoDialog('Delete PM download also?', 'No will continue the download', 'but close dialog'):
						return _return_failed(getLS(40014))
					else:
						control.progressDialog.close()
						control.hide()
						return False
			except: pass
			if transfer_info.get('status') == 'stalled':
				return _return_failed()
		control.sleep(1000 * interval)
		try:
			control.progressDialog.close()
		except: log_utils.error()
		control.hide()
		return True

	def valid_url(self, host):
		try:
			self.hosts = self.get_hosts()
			if not self.hosts['Premiumize.me']: return False
			if any(host in item for item in self.hosts['Premiumize.me']): return True
			return False
		except: log_utils.error()

	def get_hosts(self):
		hosts_dict = {'Premiumize.me': []}
		hosts = []
		append = hosts.append
		try:
			result = cache.get(self._get, 168, list_services_path_url)
			for x in result['directdl']:
				for alias in result['aliases'][x]: append(alias)
			hosts_dict['Premiumize.me'] = list(set(hosts))
		except: log_utils.error()
		return hosts_dict

	def user_transfers(self):
		try:
			response = self._get(transfer_list_url)
			if response: return response.get('transfers')
		except: log_utils.error()

	def my_files(self, folder_id=None):
		try:
			if folder_id: url = folder_list_url + '?id=%s' % folder_id
			else: url = folder_list_url
			response = self._get(url)
			if response: return response.get('content')
		except: log_utils.error()

	def my_files_all(self):
		try:
			response = self._get(item_listall_url)
			if response: return response.get('files')
		except: log_utils.error()

	def item_details(self, item_id):
		try:
			data = {'id': item_id}
			response = self._post(item_details_url, data)
			return response
		except: log_utils.error()
		return None

	def rename(self, type, folder_id=None, folder_name=''):
		try:
			if type == 'folder':
				url = folder_rename_url
				heading = getLS(40049) % type
			else:
				if not control.yesnoDialog(getLS(40049) % folder_name + ': [B](YOU MUST ENTER MATCHING FILE EXT.)[/B]', '', ''): return
				url = item_rename_url
				heading = getLS(40049) % type + ': [B](YOU MUST ENTER MATCHING FILE EXT.)[/B]'
			name = control.dialog.input(heading, defaultt=folder_name)
			if not name: return
			data = {'id': folder_id, 'name': name}
			response = self._post(url, data)
			if not response: return
			if 'status' in response and response.get('status') == 'success':
				control.refresh()
		except: log_utils.error()

	def delete(self, type, folder_id=None, folder_name=None):
		try:
			if not control.yesnoDialog(getLS(40050) % folder_name, '', ''): return
			if type == 'folder': url = folder_delete_url
			else: url = item_delete_url
			data = {'id': folder_id}
			response = self._post(url, data)
			if not response: return
			if 'status' in response:
				if response.get('status') == 'success': control.refresh()
		except: log_utils.error()

	def delete_transfer(self, media_id, folder_name=None, silent=True):
		try:
			if not silent and not control.yesnoDialog(getLS(40050) % '?[CR]' + folder_name, '', ''): return
			data = {'id': media_id}
			response = self._post(transfer_delete_url, data)
			if not silent and response and response.get('status') == 'success':
				if self.server_notifications: control.notification(message='%s successfully deleted from the Premiumize.me cloud' % folder_name, icon=pm_icon)
				control.refresh()
		except: log_utils.error()

	def clear_finished_transfers(self):
		try:
			response = self._post(transfer_clearfinished_url)
			if not response: return
			if 'status' in response and response.get('status') == 'success':
				control.refresh()
		except: log_utils.error()
		return

	def user_transfers_to_listItem(self):
		sysaddon, syshandle = 'plugin://plugin.video.dradis/', int(argv[1])
		extensions = supported_video_extensions()
		downloadMenu, renameMenu, deleteMenu, clearFinishedMenu = getLS(40048), getLS(40049), getLS(40050), getLS(40051)
		folder_str, file_str = getLS(40046).upper(), getLS(40047).upper()
		transfer_files = []
		try: transfer_files += self.user_transfers()
		except: pass
		for count, item in enumerate(transfer_files, 1):
			try:
				cm = []
				content_type = 'folder' if item['file_id'] is None else 'file'
				name = string_tools.strip_non_ascii_and_unprintable(item['name'])
				status = item['status']
				progress = 100 if status == 'finished' else item['progress'] or 0
				if content_type == 'folder':
					isFolder = True if status == 'finished' else False
					status_str = '[COLOR %s]%s[/COLOR]' % (control.getHighlightColor(), status.capitalize())
					label = '%02d | [B]%s[/B] - %s | [B]%s[/B] | [I]%s [/I]' % (count, status_str, str(progress) + '%', folder_str, name)
					url = '%s?action=pm_MyFiles&id=%s&name=%s' % (sysaddon, item['folder_id'], quote_plus(name))

					# Till PM addresses issue with item also being removed from public acess if item not accessed for 60 days this option is disabled.
					# cm.append((clearFinishedMenu, 'RunPlugin(%s?action=pm_ClearFinishedTransfers)' % sysaddon))
				else:
					isFolder = False
					details = self.item_details(item['file_id'])
					if not details: continue
					url_link = details['link']
					if url_link.startswith('/'):
						url_link = 'https' + url_link
					size = details['size']
					display_size = float(int(size)) / 1073741824
					label = '%02d | %s%% | [B]%s[/B] | %.2f GB | [I]%s [/I]' % (count, str(progress), file_str, display_size, name)
					url = '%s?action=play_URL&url=%s' % (sysaddon, url_link)
					cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&url=%s&caller=premiumize)' %
								(sysaddon, quote_plus(name), quote_plus(pm_icon), url_link)))

				cm.append((deleteMenu % 'Transfer', 'RunPlugin(%s?action=pm_DeleteTransfer&id=%s&name=%s)' %
							(sysaddon, item['id'], quote_plus(name))))
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': pm_icon, 'poster': pm_icon, 'thumb': pm_icon, 'fanart': addonFanart, 'banner': pm_icon})
				item.setInfo(type='video', infoLabels='')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def my_files_to_listItem(self, folder_id=None, folder_name=None):
		sysaddon, syshandle = 'plugin://plugin.video.dradis/', int(argv[1])
		extensions = supported_video_extensions()
		downloadMenu, renameMenu, deleteMenu = getLS(40048), getLS(40049), getLS(40050)
		folder_str, file_str = getLS(40046).upper(), getLS(40047).upper()
		cloud_files = []
		try: cloud_files += self.my_files(folder_id)
		except: pass
		cloud_files.sort(key=lambda k: k['name'])
		cloud_files.sort(key=lambda k: k['type'], reverse=True)
		for count, item in enumerate(cloud_files, 1):
			try:
				if not ('link' in item and item['link'].lower().endswith(tuple(extensions))) and not item['type'] == 'folder': continue
				cm = []
				content_type = item['type']
				name = string_tools.strip_non_ascii_and_unprintable(item['name'])
				if content_type == 'folder':
					isFolder = True
					label = '%02d | [B]%s[/B] | [I]%s [/I]' % (count, folder_str, name)
					url = '%s?action=pm_MyFiles&id=%s&name=%s' % (sysaddon, item['id'], quote_plus(name))
				else:
					isFolder = False
					url_link = item['link']
					if url_link.startswith('/'):
						url_link = 'https' + url_link
					size = item['size']
					display_size = float(int(size)) / 1073741824
					label = '%02d | [B]%s[/B] | %.2f GB | [I]%s [/I]' % (count, file_str, display_size, name)
					url = '%s?action=play_URL&url=%s' % (sysaddon, url_link)
					cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&url=%s&caller=premiumize)' %
								(sysaddon, quote_plus(name), quote_plus(pm_icon), url_link)))
				cm.append((renameMenu % content_type.capitalize(), 'RunPlugin(%s?action=pm_Rename&type=%s&id=%s&name=%s)' %
								(sysaddon, content_type, item['id'], quote_plus(name))))
				cm.append((deleteMenu % content_type.capitalize(), 'RunPlugin(%s?action=pm_Delete&type=%s&id=%s&name=%s)' %
								(sysaddon, content_type, item['id'], quote_plus(name))))
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': pm_icon, 'poster': pm_icon, 'thumb': pm_icon, 'fanart': addonFanart, 'banner': pm_icon})
				item.setInfo(type='video', infoLabels='')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def account_info_to_dialog(self):
		from datetime import datetime
		import math
		try:
			account_info = self.account_info()
			expires = datetime.fromtimestamp(account_info['premium_until'])
			days_remaining = (expires - datetime.today()).days
			expires = expires.strftime("%A, %B %d, %Y")
			points_used = int(math.floor(float(account_info['space_used']) / 1073741824.0))
			space_used = float(int(account_info['space_used'])) / 1073741824
			percentage_used = str(round(float(account_info['limit_used']) * 100.0, 1))
			items = []
			items += [getLS(40040) % account_info['customer_id']]
			items += [getLS(40041) % expires]
			items += [getLS(40042) % days_remaining]
			items += [getLS(40043) % points_used]
			items += [getLS(40044) % space_used]
			items += [getLS(40045) % percentage_used]
			return control.selectDialog(items, 'Premiumize')
		except: log_utils.error()
