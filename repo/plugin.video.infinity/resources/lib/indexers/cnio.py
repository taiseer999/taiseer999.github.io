# -*- coding: utf-8 -*-
"""
	OneMoar Addon
"""

import requests
from resources.lib.modules.control import getProgressWindow, sleep


base_url = 'https://api.chucknorris.io/jokes/random'

def news():
	try:
		response = requests.get(base_url, timeout=3)
		result = response.json()
		icon, message = result['icon_url'], result['value']
	except: return

	try:
		progressDialog = getProgressWindow('chucknorris.io', icon=icon)
		progressDialog.update(100, message)
		for i in range(1, 16):
			sleep(1000)
			progressDialog.update(100 - int(100 * i / 15), message)
	except: pass
	finally:
		progressDialog.close()
