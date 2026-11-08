# -*- coding: utf-8 -*-
"""
	AB Scrapers - ISO filter (v1.1.7).

	Blu-ray ISO releases keep the disc menus (HDMV / Java) that the AF3 Disc
	Menu button opens; everything else is a plain video file. This filter works
	on the release NAME every provider returns, for every calling add-on
	(Fen Light, Umbrella, Red Light, POV...):

	  filter.iso           0 = Show all (default)
	                       1 = Hide ISO releases
	                       2 = ISO releases only
	  filter.iso.fulldisc  also count full-disc releases (COMPLETE BLURAY,
	                       BDMV, BD25/50/66/100, FULL DISC) as ISO (default off)

	ISO       : "iso" as its own word (Movie.2019.UHD.BluRay.ISO, [ISO], .iso)
	            or BDISO / UHDISO.
	Full disc : a whole-disc copy that may be an ISO OR a BDMV folder - only the
	            playing add-on sees the files inside, so it is optional.
	Never raises; returns the input unchanged on error.
"""

import re

from abscrapers.common import setting, log, trace_enabled

_ISO = re.compile(r'(?:^|[^a-z0-9])(?:bd|uhd)?iso(?:$|[^a-z0-9])')
_FULLDISC = re.compile(
	r'complete[ ._\-\[\]()]*(?:uhd[ ._\-]*)?blu[ ._\-]*ray'
	r'|(?:^|[^a-z0-9])bdmv(?:$|[^a-z0-9])'
	r'|(?:^|[^a-z0-9])bd[ ._\-]?(?:25|50|66|100)(?:$|[^a-z0-9])'
	r'|full[ ._\-]*disc')


def mode():
	try: return int(setting('filter.iso') or 0)
	except Exception: return 0


def _name(item):
	for k in ('name', 'name_info', 'title'):
		v = item.get(k)
		if v: return str(v).lower()
	return ''


def is_iso(name, fulldisc=False):
	if not name: return False
	if _ISO.search(name): return True
	return bool(fulldisc and _FULLDISC.search(name))


def apply(results, provider=''):
	try:
		m = mode()
		if not m or not results: return results
		fulldisc = setting('filter.iso.fulldisc') == 'true'
		keep_iso = (m == 2)
		out = [i for i in results
			   if not isinstance(i, dict) or is_iso(_name(i), fulldisc) == keep_iso]
		dropped = len(results) - len(out)
		if dropped and trace_enabled():
			log('%s: ISO filter (%s) dropped %d, kept %d'
				% (provider, 'ISO only' if keep_iso else 'hide ISO', dropped, len(out)))
		return out
	except Exception as e:
		log('ISO filter error (%s): %s' % (provider, e))
		return results
