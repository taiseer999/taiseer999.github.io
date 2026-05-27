import xbmc
import sys

COLOR1 = 'white'
COLOR2 = 'white'

try:
    _ver_str = xbmc.getInfoLabel("System.BuildVersion").split()[0]
    KODIV = float(_ver_str[:4])
except (ValueError, IndexError):
    KODIV = 20.0
if KODIV > 17:
	from . import zfile as zipfile
else:
	import zipfile

def all(_in, _out, dp=None, ignore=None, title=None):
	if dp: return allWithProgress(_in, _out, dp, ignore, title)
	else: return allNoProgress(_in, _out, ignore)

def allNoProgress(_in, _out, ignore):
	try:
		zin = zipfile.ZipFile(_in, 'r')
		zin.extractall(_out)
	except Exception as e:
		xbmc.log(str(e), xbmc.LOGINFO)
		return False
	return True

def allWithProgress(_in, _out, dp, ignore, title):
	count = 0; errors = 0; error = ''; update = 0; size = 0
	try:
		zin = zipfile.ZipFile(_in,  'r')
	except Exception as e:
		errors += 1; error += '%s\n' % e
		return update, errors, error
	nFiles = float(len(zin.namelist()))
	zipsize = convertSize(sum([item.file_size for item in zin.infolist()]))

	zipit = str(_in).replace('\\', '/').split('/')
	title = title if not title == None else zipit[-1].replace('.zip', '')

	for item in zin.infolist():
		try:
			str(item.filename).encode('ascii')
		except UnicodeDecodeError:
			continue
		count += 1; prog = int(count / nFiles * 100); size += item.file_size
		try:
			zin.extract(item, _out)
		except Exception as e:
			pass
		msg = '%s [B][Errors:%s][/B] | [B]File:[/B]%s/%s [B]Size:[/B] %s/%s | %s' % (title, errors, count, int(nFiles), convertSize(size), zipsize, item.filename)
		dp.update(prog, msg)
		if dp.iscanceled(): break
	if dp.iscanceled():
		dp.close()
		sys.exit()
	return prog, errors, error

def convertSize(num, suffix='B'):
	for unit in ['', 'K', 'M', 'G']:
		if abs(num) < 1024.0:
			return "%3.02f %s%s" % (num, unit, suffix)
		num /= 1024.0
	return "%.02f %s%s" % (num, 'G', suffix)