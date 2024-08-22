# -*- coding: utf-8 -*-
"""
	OneMoar Add-on
"""

from datetime import datetime, timedelta
import time, calendar
import _strptime # import _strptime to workaround python 2 bug with threads
from resources.lib.modules import cleandate
from resources.lib.externals import pytz
from resources.lib.modules import control
from resources.lib.modules.control import lang as getLS

ZoneUtc = 'utc'
ZoneLocal = 'local'
FormatDateTime = '%Y-%m-%d %H:%M:%S'
FormatDate = '%Y-%m-%d'
FormatTime = '%H:%M:%S'
FormatTimeShort = '%H:%M'

# def datetime_from_string(self, string, format=FormatDateTime):
	# try:
		# return datetime.strptime(string, format)
	# except:
		# # Older Kodi Python versions do not have the strptime function.
		# # http://forum.kodi.tv/showthread.php?tid=112916
		# return datetime.fromtimestamp(time.mktime(time.strptime(string, format)))

def localZone():
	try:
		if time.daylight: # 1 if defined as DST zone
			local_time = time.localtime()
			if local_time.tm_isdst: offsetHour = time.altzone / 3600
			else: offsetHour = time.timezone / 3600
		else: offsetHour = time.timezone / 3600
		return 'Etc/GMT%+d' % offsetHour
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def convert_time(stringTime, stringDay=None, abbreviate=False, formatInput=FormatTimeShort, formatOutput=None, zoneFrom=ZoneUtc, zoneTo=ZoneLocal, remove_zeroes=False):
	result = ''
	try:
		# If only time is given, the date will be set to 1900-01-01 and there are conversion problems if this goes down to 1899.
		if formatInput == '%H:%M':
			stringTime = '%s %s' % (datetime.now().strftime('%Y-%m-%d'), stringTime) # Use current datetime.now() to accomodate for daylight saving time.
			formatNew = '%Y-%m-%d %H:%M'
		else: formatNew = formatInput

		if zoneFrom == ZoneUtc: zoneFrom = pytz.timezone('UTC')
		elif zoneFrom == ZoneLocal: zoneFrom = pytz.timezone(localZone())
		else: zoneFrom = pytz.timezone(zoneFrom)

		if zoneTo == ZoneUtc: zoneTo = pytz.timezone('UTC')
		elif zoneTo == ZoneLocal: zoneTo = pytz.timezone(localZone())
		else: zoneTo = pytz.timezone(zoneTo)

		timeobject = cleandate.datetime_from_string(string_date=stringTime, format=formatNew, date_only=False)

		if stringDay:
			stringDay = stringDay.lower()
			if stringDay.startswith('mon'): weekday = 0
			elif stringDay.startswith('tue'): weekday = 1
			elif stringDay.startswith('wed'): weekday = 2
			elif stringDay.startswith('thu'): weekday = 3
			elif stringDay.startswith('fri'): weekday = 4
			elif stringDay.startswith('sat'): weekday = 5
			else: weekday = 6
			weekdayCurrent = datetime.now().weekday()
			timeobject += timedelta(days=weekday) - timedelta(days=weekdayCurrent)

		timeobject = zoneFrom.localize(timeobject)
		timeobject = timeobject.astimezone(zoneTo)

		if not formatOutput: formatOutput = formatInput

		stringTime = timeobject.strftime(formatOutput)
		if remove_zeroes: stringTime = stringTime.replace(' 0', ' ').replace(':00 ', '')

		if stringDay:
			if abbreviate: stringDay = calendar.day_abbr[timeobject.weekday()]
			else: stringDay = calendar.day_name[timeobject.weekday()]
			return (stringTime, stringDay)
		else: return stringTime
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return stringTime

def external_providers():
	try:
		results = control.jsonrpc_get_addons()
		results.sort(key=lambda k: k.get('name'))
		chosen = control.selectDialog([i.get('name') for i in results], 'Select external provider module:')
		if chosen < 0:
#			control.homeWindow.setProperty('infinity.updateSettings', 'false')
#			control.setSetting('provider.external.enabled', 'false')
#			control.setSetting('external_provider.name', '')
#			control.homeWindow.setProperty('infinity.updateSettings', 'true')
#			control.setSetting('external_provider.module', '')
			control.setSettingsDict({
				'provider.external.enabled': 'false',
				'external_provider.name': '',
				'external_provider.module': ''
			})
			return
		try:
			module = results[chosen].get('addonid')
			name = module.split('.')[-1]
			from sys import path
			path.append(control.transPath('special://home/addons/%s/lib' % module))
			from importlib import import_module
			getattr(import_module(name), 'sources')
			success = True
		except:
			success = False
		if success:
#			control.homeWindow.setProperty('infinity.updateSettings', 'false')
#			control.setSetting('external_provider.name' , results[chosen].get('addonid').split('.')[-1])
#			control.homeWindow.setProperty('infinity.updateSettings', 'true')
#			control.setSetting('external_provider.module', results[chosen].get('addonid'))
			control.setSettingsDict({
				'provider.external.enabled': 'true',
				'external_provider.name': name,
				'external_provider.module': module
			})
			control.notification(title=results[chosen].get('name'), message=getLS(40449))
		else:
			control.okDialog(title=33586, message=getLS(40446) % results[chosen].get('name'))
			return external_providers()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
