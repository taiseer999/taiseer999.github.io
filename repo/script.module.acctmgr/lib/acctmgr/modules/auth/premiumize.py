# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import requests
from acctmgr.modules import control
from acctmgr.modules import log_utils
from acctmgr.modules.qr_utils import make_qr, remove_qr

# Variables
CLIENT_ID = '671951559'  # used to auth
BaseUrl = 'https://www.premiumize.me/api'
account_info_url = '%s/account/info' % BaseUrl
pm_icon = control.joinPath(control.artPath(), 'premiumize.png')
pm_bdr = control.joinPath(control.addonPath(), 'resources', 'images', 'white.png')
pm_bg = control.joinPath(control.addonPath(), 'resources', 'images', 'dialog_background.png')

class PremiumizeAuthDialog(xbmcgui.WindowXMLDialog):
	def __init__(self, *args, **kwargs):
		self.user_code = kwargs.get('user_code')
		self.bg_image = kwargs.get('bg_image')
		self.qr_image = kwargs.get('qr_image')
		self.bdr_image = kwargs.get('bdr_image')
		self.is_active = True
		super(PremiumizeAuthDialog, self).__init__()

	def onInit(self):
		self.setProperty('user_code', str(self.user_code or ''))
		self.setProperty('bg_image', str(self.bg_image or ''))
		self.setProperty('qr_image', str(self.qr_image or ''))
		self.setProperty('bdr_image', str(self.bdr_image or ''))

	def onClick(self, controlId):
		self.is_active = False
		self.close()

	def onAction(self, action):
		if action.getId() in [10, 13, 92]:
			self.is_active = False
			self.close()

class Premiumize:
	name = "Premiumize.me"

	def __init__(self):
		self.token = control.setting('premiumize.token')
		self.headers = {
			'User-Agent': 'AM Lite for Kodi',
			'Authorization': 'Bearer %s' % self.token
		}
		self.server_notifications = False

	def _get(self, url):
		try:
			response = requests.get(
				url,
				headers=self.headers,
				timeout=15
			).json()

			if 'status' in response:
				if response.get('status') == 'success':
					return response
				if response.get('status') == 'error' and self.server_notifications:
					control.notification(
						title='default',
						message=response.get('message'),
						icon=pm_icon
					)
		except Exception as e:
			log_utils.error(f"Premiumize GET request failed: {e}")
		return response

	def _post(self, url, data={}):
		try:
			response = requests.post(
				url,
				data,
				headers=self.headers,
				timeout=15
			).json()

			if 'status' in response:
				if response.get('status') == 'success':
					return response
				if response.get('status') == 'error' and self.server_notifications:
					control.notification(
						title='default',
						message=response.get('message'),
						icon=pm_icon
					)
		except Exception as e:
			log_utils.error(f"Premiumize POST request failed: {e}")
		return response

	def auth(self):
		import time

		data = {'client_id': CLIENT_ID, 'response_type': 'device_code'}

		try:
			token = requests.post(
				'https://www.premiumize.me/token',
				data=data,
				timeout=15
			).json()

			expiry = float(token['expires_in'])
			token_ttl = int(token['expires_in'])
			interval = int(token['interval'])
			device_code = token['device_code']
			user_code = token['user_code']
			verify_url = token['verification_uri']
			# Prefer the complete URI (embeds the code) so the website prefills it
			verify_url_qr = token.get('verification_uri_complete') or verify_url

		except Exception as e:
			log_utils.error(f"Premiumize device code request failed: {e}")
			control.notification(
				title='default',
				message=control.lang(40020),
				icon=pm_icon
			)
			return False

		qr_path = make_qr(verify_url_qr)
		pm_static_qr = control.joinPath(control.addonPath(), 'resources', 'images', 'premiumize_qr.png')
		qr_image = qr_path if qr_path else pm_static_qr

		dialog = PremiumizeAuthDialog(
			'premiumize_auth.xml',
			str(control.addonPath()),
			'Default',
			user_code=user_code,
			bg_image=pm_bg,
			qr_image=qr_image,
			bdr_image=pm_bdr
		)
		dialog.show()

		start = time.time()
		timeout = expiry or 300
		success = False

		while dialog.is_active:
			if time.time() - start > timeout:
				break

			poll_again, success = self.poll_token(device_code)
			if success:
				break

			control.sleep(interval * 1000)
			token_ttl -= interval
			if token_ttl <= 0:
				break

		dialog.close()
		del dialog
		remove_qr(qr_path)

		if not success:
			control.notification(
				'Premiumize',
				'Authorization failed or timed out',
				icon=pm_icon
			)
			return False

		control.notification(title='AM Lite',message='Successfully Authorized!',icon=pm_icon)
		return True

	def poll_token(self, device_code):
		data = {
			'client_id': CLIENT_ID,
			'code': device_code,
			'grant_type': 'device_code'
		}

		try:
			token = requests.post(
				'https://www.premiumize.me/token',
				data=data,
				timeout=15
			).json()
		except Exception as e:
			log_utils.error(f"Premiumize poll token failed: {e}")
			return True, False

		if 'error' in token:
			if token['error'] == "access_denied":
				control.okDialog(
					title='default',
					message=control.lang(40020)
				)
				return False, False
			return True, False

		self.token = token['access_token']
		self.headers = {
			'User-Agent': 'AM Lite for Kodi',
			'Authorization': 'Bearer %s' % self.token
		}

		control.sleep(500)
		account_info = self.account_info()
		control.setSetting('premiumize.token', token['access_token'])
		control.setSetting(
			'premiumize.username',
			str(account_info['customer_id'])
		)
		return False, True

	def revoke(self):
		try:
			control.setSetting('premiumize.token', '')
			control.setSetting('premiumize.username', '')
			control.dialog.ok(
				control.lang(40057),
				control.lang(32314)
			)
		except Exception as e:
			log_utils.error(f"Premiumize revoke failed: {e}")

	def account_info(self):
		try:
			return self._get(account_info_url)
		except Exception as e:
			log_utils.error(f"Premiumize account info failed: {e}")
		return None

	def account_info_to_dialog(self):
		from datetime import datetime
		import math
		try:
			accountInfo = self.account_info()
			expires = datetime.fromtimestamp(accountInfo['premium_until'])
			days_remaining = (expires - datetime.today()).days
			expires = expires.strftime("%A, %B %d, %Y")
			points_used = int(
				math.floor(float(accountInfo['space_used']) / 1073741824.0)
			)
			space_used = float(int(accountInfo['space_used'])) / 1073741824
			percentage_used = str(
				round(float(accountInfo['limit_used']) * 100.0, 1)
			)

			items = []
			items += [control.lang(40040) % accountInfo['customer_id']]
			items += [control.lang(40041) % expires]
			items += [control.lang(40042) % days_remaining]
			items += [control.lang(40043) % points_used]
			items += [control.lang(40044) % space_used]
			items += [control.lang(40045) % percentage_used]

			return control.selectDialog(items, 'Premiumize')

		except Exception as e:
			log_utils.error(f"Premiumize account dialog failed: {e}")
		return
