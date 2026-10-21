# -*- coding: utf-8 -*-
"""
	AB Scrapers - provider registry.
	Maps every provider name to the engine implementations that ship it and to
	the engine(s) used by default ("Auto").
"""

import os

ENGINE_ORDER = ('coco', 'gears', 'magneto')
ENGINE_LABELS = {'coco': 'CocoScrapers', 'gears': 'Gears', 'magneto': 'Magneto'}
ENGINE_PACKAGES = {
	'coco': 'abscrapers.engines.coco.sources_cocoscrapers.torrents',
	'gears': 'abscrapers.engines.gears.providers.torrents',
	'magneto': 'abscrapers.engines.magneto.providers.torrents',
}
_BASE = os.path.join(os.path.dirname(__file__), 'engines')
ENGINE_DIRS = {
	'coco': os.path.join(_BASE, 'coco', 'sources_cocoscrapers', 'torrents'),
	'gears': os.path.join(_BASE, 'gears', 'providers', 'torrents'),
	'magneto': os.path.join(_BASE, 'magneto', 'providers', 'torrents'),
}

# Auto = curated choice per overlapping provider.
#  - same endpoint in several engines   -> run only the strongest implementation
#  - different instances/mirrors/APIs   -> run them together and merge by info-hash
AUTO = {
	# CocoScrapers 1.0.43 ships kodifitzwell's POV 6.10.16 provider code - the newest
	# upstream of what Magneto 6.10.04 had (Magneto 6.10.16+ dropped its own providers).
	# So Coco replaces Magneto wherever the two were the same code.
	'1337x': ('gears',),                     # gears probes 8 mirrors, coco hard-codes one
	'aiostreams': ('gears', 'coco'),         # gears multi-instance + coco instance/login (AIOStreams v2 auth)
	'bitmagnet': ('gears',),
	'bitsearch': ('coco', 'gears'),          # coco: new bitsearch.eu domain/format; gears: bitsearch.to
	'comet': ('gears', 'coco'),              # feels.legal + selectable instance (latest format fix)
	'dmm': ('coco',),                        # upstream fix: one page, avoids DMM rate-limiting
	'eztv': ('gears',),
	'kickass2': ('gears', 'coco'),           # gears mirror probing + coco new search/result parsing
	'knaben': ('gears', 'coco'),             # html site + JSON API
	'limetorrents': ('gears', 'coco'),       # different mirror sets
	'mediafusion': ('gears', 'coco'),        # midnightignite + stremio.ru/custom (with user data)
	'meteor': ('coco',),                     # upstream format fix
	'nyaa': ('coco',),                       # RSS feed parser (newest)
	'piratebay': ('gears',),
	'prowlarr': ('gears',),                  # same user instance in every engine
	'rutor': ('gears',),
	'torlock': ('gears', 'coco'),            # html + torznab api (newest)
	'torrentdownload': ('gears',),
	'torrentgalaxy': ('coco', 'gears'),      # json api (3 mirrors, packs) + html detail scrape
	'torrentio': ('gears',),
	'torrentproject2': ('coco', 'gears'),    # .com + .org
	'torrentsdb': ('gears',),
	'torz': ('gears', 'coco'),               # fixed instance + selectable instance
	'ytsmx': ('gears', 'coco'),              # yts mirrors + new YTS API endpoint
	'zilean': ('gears', 'coco'),             # fixed instance + selectable instance
}
PREFERENCE = ('gears', 'coco', 'magneto')


def _scan(engine):
	try: files = os.listdir(ENGINE_DIRS[engine])
	except Exception: return []
	return sorted(f[:-3] for f in files if f.endswith('.py') and not f.startswith('__'))


_PROVIDERS = None

def providers():
	"""{provider_name: [engines that implement it, in ENGINE_ORDER]}"""
	global _PROVIDERS
	if _PROVIDERS is None:
		found = {}
		for engine in ENGINE_ORDER:
			for name in _scan(engine): found.setdefault(name, []).append(engine)
		_PROVIDERS = dict(sorted(found.items()))
	return _PROVIDERS


def engines_for(name):
	return providers().get(name, [])


def engine_choices(name):
	"""Values of the per-provider engine selector; index stored as engine.<name>."""
	return ['auto', 'all'] + list(engines_for(name))


def auto_engines(name):
	available = engines_for(name)
	picked = [e for e in AUTO.get(name, ()) if e in available]
	if picked: return picked
	for e in PREFERENCE:
		if e in available: return [e]
	return []


def selected_engines(name, getSetting):
	available = engines_for(name)
	if len(available) <= 1: return list(available)
	choices = engine_choices(name)
	try: choice = choices[int(getSetting('engine.%s' % name) or 0)]
	except Exception: choice = 'auto'
	if choice == 'all': return list(available)
	if choice in available: return [choice]
	return auto_engines(name)
