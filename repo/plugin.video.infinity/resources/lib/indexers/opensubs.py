# -*- coding: utf-8 -*-
"""
	Infinity Addon
"""

import requests
from resources.lib.modules import control


getLS = control.lang
timeout = 3.05
base_url = 'https://api.opensubtitles.com/api/v1'


langDict = {'Abkhazian': 'ab', 'Afrikaans': 'af', 'Albanian': 'sq', 'Amharic': 'am',
'Arabic': 'ar', 'Aragonese': 'an', 'Armenian': 'hy', 'Assamese': 'as', 'Asturian': 'at',
'Azerbaijani': 'az-az', 'Basque': 'eu', 'Belarusian': 'be', 'Bengali': 'bn',
'Bosnian': 'bs', 'Breton': 'br', 'Bulgarian': 'bg', 'Burmese': 'my', 'Catalan': 'ca',
'Chinese (Cantonese)': 'zh-ca', 'Chinese (simplified)': 'zh-cn', 'Chinese (traditional)': 'zh-tw',
'Chinese bilingual': 'ze', 'Croatian': 'hr', 'Czech': 'cs', 'Danish': 'da',
'Dari': 'pr', 'Dutch': 'nl', 'English': 'en', 'Esperanto': 'eo', 'Estonian': 'et',
'Extremaduran': 'ex', 'Finnish': 'fi', 'French': 'fr', 'Gaelic': 'gd', 'Galician': 'gl',
'Georgian': 'ka', 'German': 'de', 'Greek': 'el', 'Hebrew': 'he', 'Hindi': 'hi',
'Hungarian': 'hu', 'Icelandic': 'is', 'Igbo': 'ig', 'Indonesian': 'id', 'Interlingua': 'ia',
'Irish': 'ga', 'Italian': 'it', 'Japanese': 'ja', 'Kannada': 'kn', 'Kazakh': 'kk',
'Khmer': 'km', 'Korean': 'ko', 'Kurdish': 'ku', 'Latvian': 'lv', 'Lithuanian': 'lt',
'Luxembourgish': 'lb', 'Macedonian': 'mk',  'Malay': 'ms',  'Malayalam': 'ml',
'Manipuri': 'ma', 'Marathi': 'mr', 'Mongolian': 'mn', 'Montenegrin': 'me', 'Navajo': 'nv',
'Nepali': 'ne', 'Northern Sami': 'se', 'Norwegian': 'no', 'Occitan': 'oc', 'Odia': 'or',
'Persian': 'fa', 'Polish': 'pl', 'Portuguese': 'pt-pt', 'Portuguese (BR)': 'pt-br',
'Portuguese (MZ)': 'pm',  'Pushto': 'ps', 'Romanian': 'ro', 'Russian': 'ru',
'Santali': 'sx', 'Serbian': 'sr', 'Sindhi': 'sd', 'Sinhalese': 'si', 'Slovak': 'sk',
'Slovenian': 'sl', 'Somali': 'so', 'South Azerbaijani': 'az-zb', 'Spanish': 'es',
'Spanish (EU)': 'sp', 'Spanish (LA)': 'ea', 'Swahili': 'sw', 'Swedish': 'sv',
'Syriac': 'sy', 'Tagalog': 'tl', 'Tamil': 'ta', 'Tatar': 'tt', 'Telugu': 'te',
'Tetum': 'tm-td', 'Thai': 'th', 'Toki Pona': 'tp', 'Turkish': 'tr',  'Turkmen': 'tk',
'Ukrainian': 'uk', 'Urdu': 'ur', 'Uzbek': 'uz', 'Vietnamese': 'vi', 'Welsh': 'cy'}

class OpenSubtitles():
	def __init__(self):
		self.user_agent = 'Infinity v' + control.getInfinityVersion()
		self.apikey = control.setting('opensubs.apikey')
		self.jwt_token = control.setting('opensubstoken')
		self.is_auth = True if all((self.jwt_token, self.apikey)) else False

	def auth(self):
		try:
			username = control.dialog.input(getLS(40504))
			password = control.dialog.input(getLS(40505), option=2)
			if not all((username, password)): return
			url = base_url + '/login'
			headers = {
				'Content-Type': 'application/json',
				'User-Agent': self.user_agent,
				'Api-Key': self.apikey
			}
			data = {'username': username, 'password': password}
			response = requests.post(url, headers=headers, json=data, timeout=timeout)
			response = response.json()
			token = str(response['token'])
			control.setSetting('opensubstoken', token)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def revoke(self):
		try:
			control.setSetting('opensubstoken', '')
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def getAccountStatus(self):
		try:
			if not self.is_auth: return control.notification(title=40503, message=40507)
			url = base_url + '/infos/user'
			headers = {
				'Content-Type': 'application/json',
				'User-Agent': self.user_agent,
				'Api-Key': self.apikey,
				'Authorization': 'Bearer ' + self.jwt_token
			}
			response = requests.get(url, headers=headers, timeout=timeout)
			result = response.json()['data']
			items = []
			append = items.append
			append('[B]Username:[/B] %s' % result['username'])
			append('[B]Level:[/B] %s' % result['level'])
			append('[B]VIP:[/B] %s' % result['vip'])
			append('[B]Allowed Downloads:[/B] %s' % result['allowed_downloads'])
			append('[B]Remaining Downloads:[/B] %s' % result['remaining_downloads'])
			return control.selectDialog(items, getLS(40503))
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
