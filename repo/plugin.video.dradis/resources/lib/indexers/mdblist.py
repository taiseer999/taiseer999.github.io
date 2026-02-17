"""
	Dradis Add-on
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from resources.lib.modules import control

getLS = control.lang
getSetting = control.setting
base_url = 'https://api.mdblist.com'
session = requests.Session()
retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
session.mount('https://api.mdblist.com', HTTPAdapter(max_retries=retries, pool_maxsize=100))
highlight_color = control.getHighlightColor()


def call_mdblist(url, params=None, json=None, method=None):
	params = params or {}
	params['apikey'] = getSetting('mdblist.token')
	try:
		response = session.request(
			method or 'get',
			url,
			params=params,
			json=json,
			timeout=20
		)
		response.raise_for_status()
	except requests.exceptions.RequestException as e:
		from resources.lib.modules import log_utils
		log_utils.error()
	try: result = response.json()
	except: result = []
	return result

def mdb_modify_list(list_id, data, action='add'):
	if list_id: url = '%s/lists/%s/items/%s' % (base_url, list_id, action)
	else: url = '%s/watchlist/items/%s' % (base_url, action)
	results = call_mdblist(url, json=data, method='post')
	if 'detail' in results: control.notification(message=results['detail'])
	key = 'added' if action == 'add' else 'removed'
	success = key in results and any(results[key][i] for i in ('movies', 'shows'))
	return success

def manager(name, imdb=None, media_type=None):
	items = [
		(getLS(33580) % (highlight_color, 'Watchlist'), '', 'add'),
		(getLS(33581) % (highlight_color, 'Watchlist'), '', 'remove')
	]
	try:
		lists = call_mdblist('%s/lists/user' % base_url)
		for i in lists:
			if i['dynamic']: continue
			items += [(getLS(33580) % (highlight_color, i['name']), str(i['id']), 'add')]
			items += [(getLS(33581) % (highlight_color, i['name']), str(i['id']), 'remove')]
		if not items: return

		select = control.selectDialog([i[0] for i in items], heading=control.addonInfo('name') + ' - ' + 'MDBList Manager')

		if select == -1: return
		if select >= 0:
			list_id, action = items[select][1], items[select][2]
			data = {media_type: [{'imdb': imdb}]}
			message = 'Item Removed From MDBList' if action == 'remove' else 'Item Added To MDBList'
			if mdb_modify_list(list_id, data, action): control.notification(title=name, message=message)
			else: control.notification(title=name, message='MDBList Addition Failed')
			if action == 'remove': control.refresh()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
