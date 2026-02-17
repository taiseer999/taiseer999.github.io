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
FormatDateTime = '%Y-%m-%dT%H:%M:%S.%fZ'
rest_base_url = 'https://app.real-debrid.com/rest/1.0/'
oauth_base_url = 'https://app.real-debrid.com/oauth/v2/'
unrestrict_link_url = 'unrestrict/link'
device_code_url = 'device/code?%s'
credentials_url = 'device/credentials?%s'
downloads_delete_url = 'downloads/delete'
add_magnet_url = 'torrents/addMagnet'
select_files_url = 'torrents/selectFiles'
torrents_info_url = 'torrents/info'
torrents_delete_url = 'torrents/delete'
torrents_active_url = 'torrents/activeCount'
hosts_domains_url = 'hosts/domains'
# hosts_status_url = 'hosts/status'
hosts_regex_url = 'hosts/regex'
rd_icon = control.joinPath(control.artPath(), 'realdebrid.png')
addonFanart = control.addonFanart()

session = requests.Session()
retries = Retry(total=1, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount('https://app.real-debrid.com', HTTPAdapter(max_retries=retries, pool_maxsize=100))


class RealDebrid:
	name = "Real-Debrid"
	sort_priority = getSetting('realdebrid.priority')
	def __init__(self):
		self.hosters = None
		self.hosts = None
		self.server_notifications = getSetting('realdebrid.server.notifications')
		self.external_cache = getSetting('realdebrid.check_cache') == 'true'
		self.store_to_cloud = getSetting('realdebrid.saveToCloud') == 'true'
		self.token = getSetting('realdebrid.token')
		self.client_id = getSetting('realdebrid.client_id') or 'X245A4XAIBGVM'
		self.secret = getSetting('realdebrid.secret')
		self.device_code = ''

	def _get(self, url, token_ck=False):
		if self.token == '': return None
		original_url = url
		url = rest_base_url + url

		try:
			session.headers['Authorization'] = f"Bearer {self.token}"
			response = session.get(url, timeout=40) # cache checking of show packs results in random timeout at 30
			if response.status_code in (401,):
				if self.refresh_token() and not token_ck: return self._get(original_url)
			if not response.ok: response.raise_for_status()
		except requests.exceptions.RequestException as e:
			if e.response is None: response, message = None, 'Failed to connect to Real-Debrid'
			else: response, message = e.response, f"{e.response.status_code}: {e.response.reason}"
			if self.server_notifications: control.notification(message=message, icon=rd_icon)
			log_utils.log('Real-Debrid: %s' % message, level=log_utils.LOGWARNING)
		try: return response.json()
		except: return response

	def _post(self, url, data):
		if self.token == '': return None
		original_url = url
		url = rest_base_url + url

		try:
			session.headers['Authorization'] = f"Bearer {self.token}"
			response = session.post(url, data=data, timeout=20)
			if response.status_code in (401,):
				if self.refresh_token(): return self._post(original_url, data)
			if not response.ok: response.raise_for_status()
		except requests.exceptions.RequestException as e:
			if e.response is None: response, message = None, 'Failed to connect to Real-Debrid'
			else: response, message = e.response, f"{e.response.status_code}: {e.response.reason}"
			if self.server_notifications: control.notification(message=message, icon=rd_icon)
			log_utils.log('Real-Debrid: %s' % message, level=log_utils.LOGWARNING)
		try: return response.json()
		except: return response

	def refresh_token(self):
		try:
			self.client_id = getSetting('realdebrid.client_id')
			self.secret = getSetting('realdebrid.secret')
			self.device_code = getSetting('realdebrid.refresh')
			if not self.client_id or not self.secret or not self.device_code: return False # avoid if previous refresh attempt revoked accnt, loops twice.
			log_utils.log('Real-Debrid: Refreshing Expired Token: | %s | %s |' % (self.client_id, self.device_code), level=log_utils.LOGDEBUG)
			success, error = self.get_token()
			if not success:
				if not 'Temporarily Down For Maintenance' in error:
					if any(value == error.get('error_code') for value in (9, 12, 13, 14)):
						self.reset_authorization() # empty all auth settings to force a re-auth on next use
						if self.server_notifications: control.notification(message='Real-Debrid revoked due to:  %s' % error.get('error'), icon=rd_icon)
				log_utils.log('Real-Debrid: Unable to Refresh Token: %s' % error.get('error'), level=log_utils.LOGWARNING)
				return False
			else:
				log_utils.log('Real Debrid: Token Successfully Refreshed', level=log_utils.LOGDEBUG)
				return True
		except:
			log_utils.error()
			return False

	def get_token(self):
		try:
			post_data = {'client_id': self.client_id, 'client_secret': self.secret, 'code': self.device_code, 'grant_type': 'http://oauth.net/grant_type/device/1.0'}
			response = session.post(oauth_base_url + 'token', data=post_data)
			# log_utils.log('Real-Debrid: Authorize Result: | %s |' % response, level=log_utils.LOGDEBUG)
			if '[204]' in str(response): return False, str(response)
			if 'Temporarily Down For Maintenance' in response.text:
				if self.server_notifications: control.notification(message='Real-Debrid Temporarily Down For Maintenance', icon=rd_icon)
				log_utils.log('Real-Debrid: Temporarily Down For Maintenance', level=log_utils.LOGWARNING)
				return False, response.text
			else: response = response.json()

			if 'error' in response:
				message = response.get('error')
				if self.server_notifications: control.notification(message=message, icon=rd_icon)
				log_utils.log('Real-Debrid: Error: %s' % message, level=log_utils.LOGWARNING)
				return False, response

			self.token, refresh = response['access_token'], response['refresh_token']
			control.sleep(500)
			account_info = self.account_info()
			username = account_info['username']
			control.setSetting('realdebrid.username', username)
			control.setSetting('realdebrid.client_id', self.client_id)
			control.setSetting('realdebrid.secret', self.secret)
			control.setSetting('realdebrid.token', self.token)
			control.setSetting('realdebrid.refresh', refresh)
			return True, None
		except:
			log_utils.error('Real Debrid Authorization Failed : ')
			return False, None

	def reset_authorization(self):
		try:
			control.setSetting('realdebrid.client_id', '')
			control.setSetting('realdebrid.secret', '')
			control.setSetting('realdebrid.token', '')
			control.setSetting('realdebrid.refresh', '')
			control.setSetting('realdebrid.username', '')
			control.dialog.ok(getLS(40058), getLS(32320))
		except: log_utils.error()

	def days_remaining(self):
		import datetime
		try:
			account_info = self.account_info()
#			try: expires = datetime.datetime.strptime(account_info['expiration'], FormatDateTime)
#			except: expires = datetime.datetime(*(time.strptime(account_info['expiration'], FormatDateTime)[0:6]))
#			days = (expires - datetime.datetime.today()).days
			days = int(account_info['premium']/86400)
		except: days = None
		return days

	def account_info(self):
		return self._get('user')

	def torrent_info(self, torrent_id):
		try:
			url = torrents_info_url + '/%s' % torrent_id
			return self._get(url)
		except: log_utils.error()

	def delete_torrent(self, torrent_id):
		try:
			ck_token = self._get('user', token_ck=True) # check token, and refresh if needed
			url = torrents_delete_url + '/%s&auth_token=%s' % (torrent_id, self.token)
			response = session.delete(rest_base_url + url)
			if not response.ok: response.raise_for_status()
		except: log_utils.error()

	def unrestrict_link(self, link):
		post_data = {'link': link}
		response = self._post(unrestrict_link_url, post_data)
		try: return response['download']
		except: return None

	def check_cache(self, hashList):
		if isinstance(hashList, list): hashString = '/' + '/'.join(hashList)
		else: hashString = '/' + hashList
		response = self._get('torrents/instantAvailability' + hashString)
		return response

	def add_torrent_select(self, torrent_id, file_ids):
		try:
			url = '%s/%s' % (select_files_url, torrent_id)
			data = {'files': file_ids}
			return self._post(url, data)
		except: log_utils.error()

	def add_magnet(self, magnet):
		try:
			data = {'magnet': magnet}
			response = self._post(add_magnet_url, data)
			return response.get('id', '')
		except: log_utils.error()

	def create_transfer(self, magnet_url):
		try:
			extensions = supported_video_extensions()
			torrent_id = self.add_magnet(magnet_url)
#			info = self.torrent_info(torrent_id)
#			files = info['files']
#			torrent_keys = [str(item['id']) for item in files if item['path'].lower().endswith(tuple(extensions))]
#			torrent_keys = ','.join(torrent_keys)
#			self.add_torrent_select(torrent_id, torrent_keys)
			self.add_torrent_select(torrent_id, 'all')
			return torrent_id
		except:
			log_utils.error()
			self.delete_torrent(torrent_id)
			return ''

	def display_magnet_pack(self, magnet_url, info_hash):
		try:
			extensions = supported_video_extensions()
			torrent_id = self.create_transfer(magnet_url)
			for key in ['ended'] * 3:
				control.sleep(500)
				torrent_info = self.torrent_info(torrent_id)
				if key in torrent_info: break
			else: raise Exception('uncached')
			torrent_files = (i for i in torrent_info['files'] if i['selected'])
			torrent_files = [
				{'link': link,
				 'size': float(item['bytes'] / 1073741824),
				 'torrent_id': torrent_id,
				 'filename': item['path'].replace('/', '')}
				for item, link in zip(torrent_files, torrent_info['links'])
				if item['path'].lower().endswith(tuple(extensions))
			]
			return torrent_files
		except Exception:
			log_utils.error()
			if torrent_id: self.delete_torrent(torrent_id)

	def add_uncached_torrent(self, magnet_url, pack=False):
		def _return_failed(message=getLS(33586)):
			try: control.progressDialog.close()
			except: pass
			self.delete_torrent(torrent_id)
			control.hide()
			control.sleep(500)
			control.okDialog(title=getLS(40018), message=message)
			return False
		control.busy()
		try:
			active_count = self.torrents_activeCount()
			if active_count['nb'] >= active_count['limit']: return _return_failed()
		except: pass
		interval = 5
		stalled = ['magnet_error', 'error', 'virus', 'dead']
		extensions = supported_video_extensions()
		torrent_id = self.add_magnet(magnet_url)
		if not torrent_id: return _return_failed()
		torrent_info = self.torrent_info(torrent_id)
		if 'error_code' in torrent_info: return _return_failed()
		status = torrent_info['status']
		line = '%s\n%s\n%s'
		if status == 'magnet_conversion':
			line1 = getLS(40013)
			line2 = torrent_info['filename']
			line3 = getLS(40012) % str(torrent_info['seeders'])
			timeout = 100
			control.progressDialog.create(getLS(40018), line % (line1, line2, line3))
			while status == 'magnet_conversion' and timeout > 0:
				control.progressDialog.update(timeout, line % (line1, line2, line3))
				if control.monitor.abortRequested(): return sysexit()
				try:
					if control.progressDialog.iscanceled(): return _return_failed(getLS(40014))
				except: pass
				timeout -= interval
				control.sleep(1000 * interval)
				torrent_info = self.torrent_info(torrent_id)
				status = torrent_info['status']
				if any(x in status for x in stalled): return _return_failed()
				line3 = getLS(40012) % str(torrent_info['seeders'])
			try: control.progressDialog.close()
			except: pass
		if status == 'downloaded':
			control.busy()
			return True
		if status == 'magnet_conversion': return _return_failed()
		if any(x in status for x in stalled): return _return_failed(status)
		if status == 'waiting_files_selection': 
			video_files = []
			append = video_files.append
			all_files = torrent_info['files']
			for item in all_files:
				if any(item['path'].lower().endswith(x) for x in extensions): append(item)
			if pack:
				try:
					if len(video_files) == 0: return _return_failed()
					video_files.sort(key=lambda x: x['path'])
					torrent_keys = [str(i['id']) for i in video_files]
					if not torrent_keys: return _return_failed(getLS(40014))
					torrent_keys = ','.join(torrent_keys)
					self.add_torrent_select(torrent_id, torrent_keys)
					control.okDialog(title='default', message=getLS(40017) % getLS(40058))
					control.hide()
					return True # returning true here causes "success" to be returned and resolve runs on  non valid link
				except: return _return_failed()
			else:
				try:
					video = max(video_files, key=lambda x: x['bytes'])
					file_id = video['id']
				except ValueError: return _return_failed()
				self.add_torrent_select(torrent_id, str(file_id))
			control.sleep(2000)
			torrent_info = self.torrent_info(torrent_id)
			status = torrent_info['status']
			if status == 'downloaded':
				control.hide()
				control.notification(message=getLS(32057), icon=rd_icon)
				return True
			file_size = round(float(video['bytes']) / (1000 ** 3), 2)
			line1 = '%s...' % (getLS(40017) % getLS(40058))
			line2 = torrent_info['filename']
			line3 = status
			control.progressDialog.create(getLS(40018), line % (line1, line2, line3))
			while not status == 'downloaded':
				control.sleep(1000 * interval)
				torrent_info = self.torrent_info(torrent_id)
				status = torrent_info['status']
				if status == 'downloading':
					line3 = getLS(40011) % (file_size, round(float(torrent_info['speed']) / (1000**2), 2), torrent_info['seeders'], torrent_info['progress'])
				else:
					line3 = status
				control.progressDialog.update(int(float(torrent_info['progress'])), line % (line1, line2, line3))
				if control.monitor.abortRequested(): return sysexit()
				try:
					if control.progressDialog.iscanceled():
						if control.yesnoDialog('Delete RD download also?', 'No will continue the download', 'but close dialog'):
							return _return_failed(getLS(40014))
						else:
							control.progressDialog.close()
							control.hide()
							return False
				except: pass
				if any(x in status for x in stalled): return _return_failed()
			try: control.progressDialog.close()
			except: pass
			control.hide()
			return True
		control.hide()
		return False

	def torrents_activeCount(self):
		return self._get(torrents_active_url)

	def get_link(self, link):
		if 'download' in link:
			if 'quality' in link: label = '[%s] %s' % (link['quality'], link['download'])
			else: label = link['download']
			return label, link['download']

	def sort_cache_list(self, unsorted_list):
		sorted_list = sorted(unsorted_list, key=lambda x: x[1], reverse=True)
		return [i[0] for i in sorted_list]

	def get_aliases(self, title): # no longer used atm
		from sqlite3 import dbapi2 as database
		aliases = []
		try:
			dbcon = database.connect(control.providercacheFile, timeout=60)
			dbcur = dbcon.cursor()
			fetch = dbcur.execute('''SELECT * FROM rel_aliases WHERE title=?''', (title,)).fetchone()
			aliases = eval(fetch[1])
		except: log_utils.error()
		return aliases

	def valid_url(self, host):
		try:
			self.hosts = self.get_hosts()
			if not self.hosts['Real-Debrid']: return False
			if any(host in item for item in self.hosts['Real-Debrid']): return True
			return False
		except: log_utils.error()

	def get_hosts(self):
		hosts_dict = {'Real-Debrid': []}
		try:
			result = cache.get(self._get, 168, hosts_domains_url)
			hosts_dict['Real-Debrid'] = result
		except: log_utils.error()
		return hosts_dict

	def get_hosts_regex(self):
		hosts_regexDict = {'Real-Debrid': []}
		try:
			result = cache.get(self._get, 168, hosts_regex_url)
			hosts_regexDict['Real-Debrid'] = result
		except: log_utils.error()
		return hosts_regexDict

	def user_cloud(self):
		try:
			url = 'torrents?limit=500'
			return self._get(url)
		except: log_utils.error()

	def user_torrents(self):
		try:
			url = 'downloads?limit=500'
			return self._get(url)
		except: log_utils.error()

	def delete_user_torrent(self, media_id, name):
		try:
			if not control.yesnoDialog(getLS(40050) % '?[CR]' + name, '', ''): return
			ck_token = self._get('user', token_ck=True) # check token, and refresh if needed
			url = torrents_delete_url + '/%s&auth_token=%s' % (media_id, self.token)
			response = session.delete(rest_base_url + url)
			if not response.ok: response.raise_for_status()
			if self.server_notifications: control.notification(message='Real-Debrid: %s was removed from your Cloud Storage' % name, icon=rd_icon)
			control.refresh()
		except: log_utils.error()

	def delete_download(self, media_id, name):
		try:
			if not control.yesnoDialog(getLS(40050) % '?[CR]' + name, '', ''): return
			ck_token = self._get('user', token_ck=True) # check token, and refresh if needed
			url = downloads_delete_url + '/%s&auth_token=%s' % (media_id, self.token)
			response = session.delete(rest_base_url + url)
			if not response.ok: response.raise_for_status()
			if self.server_notifications: control.notification(message='Real-Debrid: %s was removed from your Transfers' % name, icon=rd_icon)
			control.refresh()
		except: log_utils.error()

	def user_cloud_to_listItem(self):
		sysaddon, syshandle = 'plugin://plugin.video.dradis/', int(argv[1])
		folder_str, deleteMenu = getLS(40046).upper(), getLS(40050)
		folders = []
		try: folders += self.user_cloud()
		except: pass
		for count, item in enumerate(folders, 1):
			try:
				if not item.get('ended'): continue
				cm = []
				status = '[COLOR %s]%s[/COLOR]' % (control.getHighlightColor(), item['status'].capitalize())
				folder_name = string_tools.strip_non_ascii_and_unprintable(item['filename'])
				label = '%02d | [B]%s[/B] - %s | [B]%s[/B] | [I]%s [/I]' % (count, status, str(item['progress']) + '%', folder_str, folder_name)
				url = '%s?action=rd_BrowseUserCloud&id=%s' % (sysaddon, item['id'])
				cm.append((deleteMenu % 'Torrent', 'RunPlugin(%s?action=rd_DeleteUserTorrent&id=%s&name=%s)' %
						(sysaddon, item['id'], quote_plus(folder_name))))
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': rd_icon, 'poster': rd_icon, 'thumb': rd_icon, 'fanart': addonFanart, 'banner': rd_icon})
				item.setInfo(type='video', infoLabels='')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def browse_user_cloud(self, folder_id):
		sysaddon, syshandle = 'plugin://plugin.video.dradis/', int(argv[1])
		extensions = supported_video_extensions()
		file_str, downloadMenu = getLS(40047).upper(), getLS(40048)
		files = self.torrent_info(folder_id)
		file_info = (i for i in files['files'] if i['selected'])
		file_urls = files['links']
		video_files = [{**i, 'url_link': url} for i, url in zip(file_info, file_urls) if i['path'].lower().endswith(tuple(extensions))]
		for count, item in enumerate(video_files, 1):
			try:
				cm = []
				name = string_tools.strip_non_ascii_and_unprintable(item['path'])
				if name.startswith('/'): name = name.split('/')[-1]
				size = float(int(item['bytes'])) / 1073741824
				url_link = item['url_link']
				label = '%02d | [B]%s[/B] | %.2f GB | [I]%s [/I]' % (count, file_str, size, name)
				url = '%s?action=play_URL&url=%s&caller=realdebrid&type=unrestrict' % (sysaddon, url_link)
				cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&url=%s&caller=realdebrid&type=unrestrict)' %
							(sysaddon, quote_plus(name), quote_plus(rd_icon), url_link)))
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': rd_icon, 'poster': rd_icon, 'thumb': rd_icon, 'fanart': addonFanart, 'banner': rd_icon})
				item.setInfo(type='video', infoLabels='')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def user_torrents_to_listItem(self):
		from resources.lib.modules import cleandate
		sysaddon, syshandle = 'plugin://plugin.video.dradis/', int(argv[1])
		extensions = supported_video_extensions()
		downloadMenu, deleteMenu = getLS(40048), getLS(40050)
		files = self.user_torrents()
		video_files = [i for i in files if i['download'].lower().endswith(tuple(extensions))]
		for count, item in enumerate(video_files, 1):
			try:
				cm = []
				name = string_tools.strip_non_ascii_and_unprintable(item['filename'])
				size = float(int(item['filesize'])) / 1073741824
				datetime_object = cleandate.datetime_from_string(item['generated'], FormatDateTime)
				label = '%02d | %.2f GB | %s | [I]%s [/I]' % (count, size, datetime_object, name)
				url_link = item['download']
				url = '%s?action=play_URL&url=%s' % (sysaddon, url_link)
				cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&url=%s&caller=realdebrid)' %
								(sysaddon, quote_plus(name), quote_plus(rd_icon), url_link)))
				cm.append((deleteMenu % 'File', 'RunPlugin(%s?action=rd_DeleteDownload&id=%s&name=%s)' %
								(sysaddon, item['id'], name)))
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': rd_icon, 'poster': rd_icon, 'thumb': rd_icon, 'fanart': addonFanart, 'banner': rd_icon})
				item.setInfo(type='video', infoLabels='')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def account_info_to_dialog(self):
		from datetime import datetime
		from resources.lib.modules import cleandate
		try:
			account_info = self.account_info()
			expires = cleandate.datetime_from_string(account_info['expiration'], FormatDateTime, date_only=False)
			days_remaining = (expires - datetime.today()).days
			expires = expires.strftime('%A, %B %d, %Y')
			items = []
			items += [getLS(40035) % account_info['email']]
			items += [getLS(40036) % account_info['username']]
			items += [getLS(40037) % account_info['type'].capitalize()]
			items += [getLS(40041) % expires]
			items += [getLS(40042) % days_remaining]
			items += [getLS(40038) % account_info['points']]
			return control.selectDialog(items, 'Real-Debrid')
		except: log_utils.error()
