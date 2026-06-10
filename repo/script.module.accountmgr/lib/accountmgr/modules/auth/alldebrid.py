# -*- coding: utf-8 -*-
"""
	Account Manager
"""

import requests
from accountmgr.modules import control
from accountmgr.modules import log_utils

base_url = 'https://api.alldebrid.com/v4/'
user_agent = 'Account%20Manager%20for%20Kodi'
ad_icon = control.joinPath(control.artPath(), 'alldebrid.png')

class AllDebrid:
	name = "AllDebrid"

	def __init__(self):
		self.token = control.setting('alldebrid.token')
		self.timeout = 15.0

	def _get(self, url, url_append=''):
		result = None
		try:
			if self.token == '': return None
			url = base_url + url + '?agent=%s&apikey=%s' % (user_agent, self.token) + url_append
			result = requests.get(url, timeout=self.timeout).json()
			if result.get('status') == 'success':
				if 'data' in result: result = result['data']
		except requests.exceptions.ConnectionError:
			control.notification(title='default', message=40073, icon=ad_icon)
		except BaseException:
			log_utils.error()
		return result

	def auth_loop(self):
		control.sleep(5000)
		response = requests.get(self.check_url, timeout=self.timeout).json()
		response = response['data']
		if 'error' in response:
			self.token = 'failed'
			return control.notification(title='default', message=40021, icon=ad_icon)
		if response['activated']:
			try:
				self.progress_dialog.close()
				self.token = str(response['apikey'])
				control.setSetting('alldebrid.token', self.token)
			except:
				self.token = 'failed'
				return control.notification(title='default', message=40021, icon=ad_icon)
		return

	def auth(self):
		from accountmgr.windows.qr_auth import QRProgressDialog
		self.token = ''
		url = base_url + 'pin/get?agent=%s' % user_agent
		response = requests.get(url, timeout=self.timeout).json()
		response = response['data']
		self.progress_dialog = QRProgressDialog()
		self.progress_dialog.create('AllDebrid Authorization', 'https://alldebrid.com/pin/', response['pin'], qr_url=response.get('user_url'))
		self.check_url = response.get('check_url')
		auth_timeout = int(response.get('expires_in', 600))
		time_passed = 0
		control.sleep(2000)
		while not self.token:
			if self.progress_dialog.iscanceled():
				self.progress_dialog.close()
				break
			self.auth_loop()
			time_passed += 5
			self.progress_dialog.update(int(100 * time_passed / max(auth_timeout, 1)))
			if time_passed >= auth_timeout:
				self.progress_dialog.close()
				break
		if self.token in (None, '', 'failed'): return
		control.sleep(2000)
		account_info = self.account_info()
		control.setSetting('alldebrid.username', str(account_info['user']['username']))
		control.notification_ad(title=40059, message=40081, icon=ad_icon) #Authorization complete. Start sync process

	def revoke(self):
		try:
			control.setSetting('alldebrid.username', '')
			control.setSetting('alldebrid.token', '')
			control.dialog.ok(control.lang(40059), control.lang(32314))
		except:
			log_utils.error()

	def account_info(self):
		response = self._get('user')
		return response

	def account_info_to_dialog(self):
		from datetime import datetime
		try:
			account_info = self.account_info()['user']
			username = account_info['username']
			email = account_info['email']
			status = 'Premium' if account_info['isPremium'] else 'Not Active'
			expires = datetime.fromtimestamp(account_info['premiumUntil'])
			days_remaining = (expires - datetime.today()).days
			heading = control.lang(40059).upper()
			items = []
			items += [control.lang(40036) % username]
			items += [control.lang(40035) % email]
			items += [control.lang(40037) % status]
			items += [control.lang(40041) % expires]
			items += [control.lang(40042) % days_remaining]
			return control.selectDialog(items, 'All Debrid')
		except:
			log_utils.error()
		return
