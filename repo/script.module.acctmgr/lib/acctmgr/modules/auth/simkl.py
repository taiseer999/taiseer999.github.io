# -*- coding: utf-8 -*-
"""Simkl authorization (PIN / device flow) for AM Lite.

Uses Simkl's PIN flow (GET /oauth/pin, poll GET /oauth/pin/{user_code}),
which is what the supported add-ons (Otaku, Umbrella) use themselves: one
long-lived access token, no refresh token.  The token is then synced to every
supported add-on by acctmgr.modules.sync.simkl_sync.
"""
import requests
from requests.adapters import HTTPAdapter

from acctmgr.modules import control
from acctmgr.modules import log_utils
from acctmgr.modules.auth.base_auth import BaseDeviceAuth

# Variables
sk_icon = control.joinPath(control.iconsPath(), 'simkl.png')

API_BASE = 'https://api.simkl.com'
PIN_URL = API_BASE + '/oauth/pin'
SETTINGS_URL = API_BASE + '/users/settings'
VERIFY_URL = 'https://simkl.com/pin'

# Simkl PIN-flow client id (the same app Otaku authorizes with, so the token
# works there unchanged).  Can be overridden with the hidden setting
# 'simkl.client_id'.
DEFAULT_CLIENT_ID = '59dfdc579d244e1edf6f89874d521d37a69a95a1abd349910cb056a1872ba2c8'

TIMEOUT = 15

session = requests.Session()
session.mount('https://api.simkl.com', HTTPAdapter(max_retries=1, pool_maxsize=10))


def client_id():
	return control.setting('simkl.client_id') or DEFAULT_CLIENT_ID


def _params():
	return {'client_id': client_id(), 'app-name': 'acctmgr', 'app-version': control.addonInfo('version') or '1'}


def _headers(token=None):
	headers = {
		'Content-Type': 'application/json',
		'User-Agent': 'acctmgr/%s' % (control.addonInfo('version') or '1'),
		'simkl-api-key': client_id(),
	}
	if token:
		headers['Authorization'] = 'Bearer %s' % token
	return headers


class Simkl(BaseDeviceAuth):
	provider_name = 'Simkl'
	icon = sk_icon

	def auth(self):
		if control.setting('simkl.token'):
			control.notification(title='Simkl', message='Simkl is already authorized!', icon=sk_icon)
			return False
		return self.authenticate()

	def get_device_code(self):
		resp = session.get(PIN_URL, params=_params(), headers=_headers(), timeout=TIMEOUT)
		resp.raise_for_status()
		result = resp.json()
		user_code = result.get('user_code')
		if not user_code:
			raise ValueError('Simkl PIN response missing user_code: %s' % str(result)[:200])
		verification_url = result.get('verification_uri') or result.get('verification_url') or VERIFY_URL
		return {
			# Simkl's device_code is a placeholder; polling is keyed on user_code.
			'device_code': result.get('device_code') or user_code,
			'user_code': user_code,
			'verification_url': verification_url,
			'qr_data': '%s?user_code=%s' % (verification_url, user_code),
			'interval': result.get('interval', 5),
			'expires_in': result.get('expires_in', 900),
		}

	def poll_token(self, device_data):
		try:
			resp = session.get('%s/%s' % (PIN_URL, device_data['user_code']),
							   params=_params(), headers=_headers(), timeout=TIMEOUT)
			if resp.status_code == 429:
				self.increase_poll_interval()
				return
			if resp.status_code in (400, 401, 403):
				self.abort_auth('Simkl authorization failed: HTTP %s' % resp.status_code)
				return
			result = resp.json()
		except (requests.RequestException, ValueError) as e:
			log_utils.log('Simkl PIN poll failed: %s' % e, __name__, log_utils.LOGDEBUG)
			return

		if not isinstance(result, dict):
			return
		token = result.get('access_token')
		if result.get('result') == 'OK' and token:
			self.token_data = {'access_token': token}
			return
		# An unknown/expired code makes Simkl issue a brand-new code (with device_code): stop.
		if result.get('result') == 'OK' and result.get('user_code') and result.get('user_code') != device_data['user_code']:
			self.abort_auth('Authorization timed out')
		# result == 'KO' -> "Authorization pending": keep polling

	def account_info(self, token=None):
		token = token or control.setting('simkl.token')
		if not token:
			return None
		try:
			resp = session.post(SETTINGS_URL, params=_params(), headers=_headers(token), json={}, timeout=TIMEOUT)
			resp.raise_for_status()
			return resp.json()
		except Exception as e:
			log_utils.error('Simkl account info failed: %s' % e)
			return None

	def save_account(self):
		token = (self.token_data or {}).get('access_token')
		if not token:
			return False
		info = self.account_info(token) or {}
		user = info.get('user') or {}
		account = info.get('account') or {}
		username = user.get('name') or 'Simkl'
		control.setSetting('simkl.token', token)
		control.setSetting('simkl.username', str(username))
		control.setSetting('simkl.userid', str(account.get('id') or ''))
		control.setSetting('simkl.joindate', str(user.get('joined_at') or ''))
		return True

	def account_info_to_dialog(self):
		try:
			info = self.account_info()
			if not info:
				control.notification(title='Simkl', message='Simkl authorization failed!', icon=sk_icon)
				return -1
			user = info.get('user') or {}
			account = info.get('account') or {}
			items = []
			items += ['Username: %s' % (user.get('name') or '')]
			if account.get('id'):
				items += ['Account ID: %s' % account.get('id')]
			if account.get('type'):
				items += ['Account Type: %s' % str(account.get('type')).capitalize()]
			if user.get('joined_at'):
				items += ['Joined: %s' % str(user.get('joined_at'))[:10]]
			if account.get('timezone'):
				items += ['Timezone: %s' % account.get('timezone')]
			return control.selectDialog(items, 'Simkl')
		except Exception as e:
			log_utils.error('Simkl account dialog failed: %s' % e)
		return

	def revoke(self):
		for k in ('simkl.token', 'simkl.username', 'simkl.userid', 'simkl.joindate'):
			control.setSetting(k, '')
