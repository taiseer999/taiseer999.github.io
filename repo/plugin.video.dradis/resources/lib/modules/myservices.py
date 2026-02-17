import requests, time
from threading import Thread, Timer
from resources.lib.indexers.trakt import force_traktSync
from resources.lib.modules import control
from resources.lib.windows.source_progress import SourceProgressXML


quote = requests.utils.quote
getLS = control.lang
getSetting = control.setting
user_agent = 'Dradis/%s' % control.getDradisVersion()
qr_str = 'https://api.qrserver.com/v1/create-qr-code/?size=256x256&qzone=1%s'
meta_keys = 'title year poster fanart clearlogo tmdblogo'
code_str, nav2_str = 'PIN CODE: [B]%s[/B]', 'LOCATION: [B]%s[/B]'
await_str = 'REMAINING: [B]%02d:%02d[/B]'
timeout = 10.05

def _make_progress_dialog(**kwargs):
	progressDialog = SourceProgressXML('source_progress.xml', control.addonPath(control.addonId()), **kwargs)
	Thread(target=progressDialog.run).start()
	return progressDialog

def authorize(service):
	return {
		'realdebrid': RealDebrid, 'premiumize': Premiumize, 'alldebrid': AllDebrid,
		'easydebrid': EasyDebrid, 'torbox': TorBox, 'offcloud': Offcloud,
		'trakt': Trakt, 'mdblist': MDBList, 'tmdblist': TMDbList
	}[service]().set_auth()

class RepeatTimer(Timer):
	def run(self):
		while not self.finished.wait(self.interval):
			self.function(*self.args, **self.kwargs)

class RealDebrid:
	def __init__(self):
		self.token = getSetting('realdebrid.token')
		self.client_id = getSetting('realdebrid.client_id') or 'X245A4XAIBGVM'
		self.secret = getSetting('realdebrid.secret')

	def base_url(self, path):
		return 'https://app.real-debrid.com/%s' % path

	def poll_auth(self, data):
		params = {'client_id': self.client_id, 'code': data['code']}
		response = requests.get(self.base_url('oauth/v2/device/credentials'), params=params, timeout=timeout)
		if not response.ok: return
		data.update(response.json())
		self.secret = data['client_secret']

	def set_auth(self):
		cls_name = 'Real-Debrid'
		if self.token:
			if not control.yesnoDialog(getLS(32056), '', ''): return
			control.setSetting('realdebrid.username', '')
			control.setSetting('realdebrid.client_id', '')
			control.setSetting('realdebrid.token', '')
			control.setSetting('realdebrid.refresh', '')
			control.setSetting('realdebrid.secret', '')
			return control.notification(message='Removed %s Authorization' % cls_name)

		params = {'client_id': self.client_id, 'new_credentials': 'yes'}
		response = requests.get(self.base_url('oauth/v2/device/code'), params=params, timeout=timeout)
		result = response.json()
		data = {'code': result['device_code'], 'grant_type': 'http://oauth.net/grant_type/device/1.0'}
		expires_in, expires_at = result['expires_in'], result['expires_in'] + time.monotonic()
		try: qr_icon = qr_str % '&data=%s' % quote(result['direct_verification_url'])
		except: qr_icon = ''
		meta = {**dict.fromkeys(meta_keys.split(), ''), 'poster': qr_icon, 'fanart': control.addonFanart()}
		detail = code_str % result['user_code'], nav2_str % result['verification_url']
		progressDialog = _make_progress_dialog(heading=cls_name, meta=meta)
		timer = RepeatTimer(result['interval'], self.poll_auth, args=(data,))
		timer.start()
		for i in range(1, expires_in + 1):
			if self.secret or progressDialog.iscanceled(): break
			lines = await_str % divmod(expires_at - time.monotonic(), 60), *detail
			progress = 100 - int(100 * i / expires_in)
			progressDialog.update(progress, '[CR]'.join(lines))
			control.sleep(1000)
		timer.cancel()
		progressDialog.close()
		if progressDialog.iscanceled(): return False
		if not self.secret: return control.notification(message=32574)
		response = requests.post(self.base_url('oauth/v2/token'), data=data, timeout=timeout)
		data.update(response.json())
		control.sleep(500)
		headers = {'Authorization': 'Bearer %s' % data['access_token']}
		response = requests.get(self.base_url('rest/1.0/user'), headers=headers, timeout=timeout)
		username = response.json()['username']
		client_id, secret = data['client_id'], data['client_secret']
		token, refresh = data['access_token'], data['refresh_token']
		control.setSetting('realdebrid.username', str(username))
		control.setSetting('realdebrid.client_id', client_id)
		control.setSetting('realdebrid.token', token)
		control.setSetting('realdebrid.refresh', refresh)
		control.setSetting('realdebrid.secret', secret)
		control.notification(message='Set %s Authorization' % cls_name)
		return True

class Premiumize:
	def __init__(self):
		self.token = getSetting('premiumize.token')
		self.client_id = '663882072'

	def base_url(self, path):
		return 'https://www.premiumize.me/%s' % path

	def poll_auth(self, data):
		response = requests.post(self.base_url('token'), json=data, timeout=timeout)
		if not response.ok: return
		data.update(response.json())
		self.token = data['access_token']

	def set_auth(self):
		cls_name = 'Premiumize.me'
		if self.token:
			if not control.yesnoDialog(getLS(32056), '', ''): return
			control.setSetting('premiumize.username', '')
			control.setSetting('premiumize.token', '')
			return control.notification(message='Removed %s Authorization' % cls_name)

		data = {'client_id': self.client_id, 'response_type': 'device_code'}
		response = requests.post(self.base_url('token'), json=data, timeout=timeout)
		result = response.json()
		data = {'client_id': self.client_id, 'code': result['device_code'], 'grant_type': 'device_code'}
		expires_in, expires_at = result['expires_in'], result['expires_in'] + time.monotonic()
		try: qr_icon = qr_str % '&data=%s' % quote(result['verification_uri'])
		except: qr_icon = ''
		meta = {**dict.fromkeys(meta_keys.split(), ''), 'poster': qr_icon, 'fanart': control.addonFanart()}
		detail = code_str % result['user_code'], nav2_str % result['verification_uri']
		progressDialog = _make_progress_dialog(heading=cls_name, meta=meta)
		timer = RepeatTimer(result['interval'], self.poll_auth, args=(data,))
		timer.start()
		for i in range(1, expires_in + 1):
			if self.token or progressDialog.iscanceled(): break
			lines = await_str % divmod(expires_at - time.monotonic(), 60), *detail
			progress = 100 - int(100 * i / expires_in)
			progressDialog.update(progress, '[CR]'.join(lines))
			control.sleep(1000)
		timer.cancel()
		progressDialog.close()
		if progressDialog.iscanceled(): return False
		if not self.token: return control.notification(message=32574)
		control.sleep(500)
		headers = {'User-Agent': user_agent, 'Authorization': 'Bearer %s' % self.token}
		response = requests.get(self.base_url('api/account/info'), headers=headers, timeout=timeout)
		username = response.json()['customer_id']
		token = str(data['access_token'])
		control.setSetting('premiumize.username', str(username))
		control.setSetting('premiumize.token', token)
		control.notification(message='Set %s Authorization' % cls_name)
		return True

class AllDebrid:
	def __init__(self):
		self.token = getSetting('alldebrid.token')

	def base_url(self, path):
		return 'https://api.alldebrid.com/%s' % path

	def poll_auth(self, url):
		response = requests.get(url, timeout=timeout)
		result = response.json()['data']
		self.token = result.get('apikey', '')

	def set_auth(self):
		cls_name = self.__class__.__name__
		if self.token:
			if not control.yesnoDialog(getLS(32056), '', ''): return
			control.setSetting('alldebrid.username', '')
			control.setSetting('alldebrid.token', '')
			return control.notification(message='Removed %s Authorization' % cls_name)

		response = requests.get(self.base_url('v4/pin/get'), timeout=timeout)
		result = response.json()['data']
		expires_in, expires_at = result['expires_in'], result['expires_in'] + time.monotonic()
		try: qr_icon = qr_str % '&bgcolor=ffd700&data=%s' % quote(result['user_url'])
		except: qr_icon = ''
		meta = {**dict.fromkeys(meta_keys.split(), ''), 'poster': qr_icon, 'fanart': control.addonFanart()}
		detail = code_str % result['pin'], nav2_str % result['base_url']
		progressDialog = _make_progress_dialog(heading=cls_name, meta=meta)
		timer = RepeatTimer(5, self.poll_auth, args=(result['check_url'],))
		timer.start()
		for i in range(1, expires_in + 1):
			if self.token or progressDialog.iscanceled(): break
			lines = await_str % divmod(expires_at - time.monotonic(), 60), *detail
			progress = 100 - int(100 * i / expires_in)
			progressDialog.update(progress, '[CR]'.join(lines))
			control.sleep(1000)
		timer.cancel()
		progressDialog.close()
		if progressDialog.iscanceled(): return False
		if not self.token: return control.notification(message=32574)
		control.sleep(500)
		headers = {'Authorization': 'Bearer %s' % self.token}
		response = requests.get(self.base_url('v4/user'), headers=headers, timeout=timeout)
		result = response.json()['data']
		username = result['user']['username']
		control.setSetting('alldebrid.username', str(username))
		control.setSetting('alldebrid.token', self.token)
		control.notification(message='Set %s Authorization' % cls_name)
		return True

class EasyDebrid:
	def base_url(self, path):
		return 'https://easydebrid.com/api/v1/%s' % path

	def set_auth(self):
		cls_name = self.__class__.__name__
		if getSetting('easydebrid.token'):
			if not control.yesnoDialog(getLS(32056), '', ''): return
			control.setSetting('easydebrid.token', '')
			control.setSetting('easydebrid.username', '')
			return control.notification(message='Removed %s Authorization' % cls_name)

		api_key = control.dialog.input('EasyDebrid API Key:')
		if not api_key: return
		headers = {'Authorization': 'Bearer %s' % api_key}
		response = requests.get(self.base_url('user/details'), headers=headers, timeout=timeout)
		result = response.json()
		customer = result['id']
		control.setSetting('easydebrid.username', str(customer))
		control.setSetting('easydebrid.token', api_key)
		control.notification(message='Set %s Authorization' % cls_name)
		return True

class TorBox:
	def base_url(self, path):
		return 'https://api.torbox.app/v1/api/%s' % path

	def set_auth(self):
		cls_name = self.__class__.__name__
		if getSetting('torbox.token'):
			if not control.yesnoDialog(getLS(32056), '', ''): return
			control.setSetting('torbox.token', '')
			control.setSetting('torbox.username', '')
			return control.notification(message='Removed %s Authorization' % cls_name)

		api_key = control.dialog.input('TorBox API Key:')
		if not api_key: return
		headers = {'Authorization': 'Bearer %s' % api_key}
		response = requests.get(self.base_url('user/me'), headers=headers, timeout=timeout)
		result = response.json()
		customer = result['data']['customer']
		control.setSetting('torbox.username', str(customer))
		control.setSetting('torbox.token', api_key)
		control.notification(message='Set %s Authorization' % cls_name)
		return True

class Offcloud:
	def base_url(self, path):
		return 'https://offcloud.com/api/%s' % path

	def set_auth(self):
		cls_name = self.__class__.__name__
		if getSetting('offcloud.token'):
			if not control.yesnoDialog(getLS(32056), '', ''): return
			control.setSetting('offcloud.token', '')
			control.setSetting('offcloud.username', '')
			return control.notification(message='Removed %s Authorization' % cls_name)

		username = control.dialog.input('Offcloud Email:')
		password = control.dialog.input('Offcloud Password:', option=2)
		if not all((username, password)): return
		data = {'username': username, 'password': password}
		response = requests.post(self.base_url('login'), json=data, timeout=timeout)
		result = response.json()
		user_id = result.get('userId')
		if not user_id: return control.notification(message=32574)
		result = requests.post(self.base_url('key'), cookies=response.cookies, timeout=timeout).json()
		api_key = result.get('apiKey')
		if not api_key: return control.notification(message=32574)
		control.setSetting('offcloud.username', str(user_id))
		control.setSetting('offcloud.token', api_key)
		control.notification(message='Set %s Authorization' % cls_name)
		return True

class Trakt:
	def __init__(self):
		self.token = getSetting('trakt.token')
		self.client_id = getSetting('trakt.client_id')
		self.secret = getSetting('trakt.client_secret')

	def base_url(self, path):
		return 'https://api.trakt.tv/%s' % path

	def poll_auth(self, data):
		response = requests.post(self.base_url('oauth/device/token'), json=data, timeout=timeout)
		if not response.ok: return
		data.update(response.json())
		self.token = data['access_token']

	def set_auth(self):
		cls_name = self.__class__.__name__
		if self.token:
			if not control.yesnoDialog(getLS(32056), '', ''): return
			data = {'token': self.token, 'client_id': self.client_id, 'client_secret': self.secret}
			response = requests.post(self.base_url('oauth/revoke'), json=data, timeout=timeout)
			control.setSetting('trakt.username', '')
			control.setSetting('trakt.token', '')
			control.setSetting('trakt.refresh', '')
			control.setSetting('trakt.expires', '')
			control.setSetting('trakt.isauthed', '')
			control.sleep(500)
			return control.notification(message='Removed %s Authorization' % cls_name)

		data = {'client_id': self.client_id, 'client_secret': self.secret, 'code': ''}
		response = requests.post(self.base_url('oauth/device/code'), json=data, timeout=timeout)
		result = response.json()
		data['code'] = result['device_code']
		expires_in, expires_at = result['expires_in'], result['expires_in'] + time.monotonic()
		try: qr_icon = qr_str % '&color=f00&data=%s' % quote('%s/%s' % (result['verification_url'], result['user_code']))
		except: qr_icon = ''
		meta = {**dict.fromkeys(meta_keys.split(), ''), 'poster': qr_icon, 'fanart': control.addonFanart()}
		detail = code_str % result['user_code'], nav2_str % result['verification_url']
		progressDialog = _make_progress_dialog(heading=cls_name, meta=meta)
		timer = RepeatTimer(result['interval'], self.poll_auth, args=(data,))
		timer.start()
		for i in range(1, expires_in + 1):
			if self.token or progressDialog.iscanceled(): break
			lines = await_str % divmod(expires_at - time.monotonic(), 60), *detail
			progress = 100 - int(100 * i / expires_in)
			progressDialog.update(progress, '[CR]'.join(lines))
			control.sleep(1000)
		timer.cancel()
		progressDialog.close()
		if progressDialog.iscanceled(): return False
		if not self.token: return control.notification(message=32574)
		control.sleep(500)
		headers = {'trakt-api-key': self.client_id, 'trakt-api-version': '2', 'Content-Type': 'application/json'}
		headers.update({'Authorization': 'Bearer %s' % self.token})
		response = requests.get(self.base_url('users/me'), headers=headers, timeout=timeout)
		username = response.json()['username']
		expires = int(data['created_at']) + int(data['expires_in'])
		refresh, token = data['refresh_token'], data['access_token']
		control.setSetting('trakt.username', str(username))
		control.setSetting('trakt.token', token)
		control.setSetting('trakt.refresh', refresh)
		control.setSetting('trakt.expires', str(expires))
		control.setSetting('trakt.isauthed', 'true')
		control.setSetting('indicators.alt', '1')
		control.notification(message='Set %s Authorization' % cls_name)
		control.sleep(500)
		force_traktSync()
		return True

class MDBList:
	def base_url(self, path):
		return 'https://api.mdblist.com/%s' % path

	def set_auth(self):
		cls_name = self.__class__.__name__
		if getSetting('mdblist.token'):
			if not control.yesnoDialog(getLS(32056), '', ''): return
			control.setSetting('mdblist.username', '')
			control.setSetting('mdblist.token', '')
			return control.notification(message='Removed %s Authorization' % cls_name)

		api_key = control.dialog.input('MDBList API Key:')
		if not api_key: return
		params = {'apikey': api_key}
		response = requests.get(self.base_url('user'), params=params, timeout=timeout)
		result = response.json()
		user_id, username = result['user_id'], result['username']
		control.setSetting('mdblist.username', str(username))
		control.setSetting('mdblist.token', api_key)
		control.notification(message='Set %s Authorization' % cls_name)
		return True

class TMDbList:
	pass
