# -*- coding: utf-8 -*-
"""
	AB Scrapers Module
	One module, three engines: CocoScrapers + Gears Scrapers + Magneto.

	Drop-in API (same shape as cocoscrapers / fenomscrapers):
		import abscrapers
		abscrapers.sources(ret_all=False)   -> [(provider_name, source_class), ...]
		abscrapers.pack_sources()           -> [provider_name, ...]
"""

from importlib import import_module
from abscrapers.common import setting as getSetting, log, debug_enabled, trace, caller_id
from abscrapers import registry

debug = debug_enabled()
sourceFolder = 'torrents'


def enabledCheck(module_name):
	try: return getSetting('provider.' + module_name) == 'true'
	except Exception: return True


def _load(engine, name):
	module = import_module('%s.%s' % (registry.ENGINE_PACKAGES[engine], name))
	cls = module.source
	if hasattr(cls, 'clear_all'): # magneto SourceRegistry: drop futures left from the previous search
		try: cls.clear_all()
		except Exception: pass
	return cls


def _traced(name, engine, cls):
	"""Thin subclass of a single-engine provider: same attributes, every call is traced."""
	class source(cls):
		ab_provider, ab_engines = name, (engine,)
		def sources(self, data, hostDict):
			from abscrapers import dedupe
			return dedupe.apply(trace(name, engine, 'sources', lambda: cls.sources(self, data, hostDict)), data, name)
		if hasattr(cls, 'sources_packs'):
			def sources_packs(self, data, hostDict, search_series=False, total_seasons=None, bypass_filter=False):
				from abscrapers import dedupe
				return dedupe.apply(trace(name, engine, 'sources_packs', lambda: cls.sources_packs(self, data, hostDict,
					search_series=search_series, total_seasons=total_seasons, bypass_filter=bypass_filter)), data, name)
	source.__module__ = cls.__module__
	return source


def load_provider(name, engines=None):
	from abscrapers.composite import make_composite
	engines = engines or registry.selected_engines(name, getSetting)
	impls = []
	for engine in engines:
		try: impls.append((engine, _load(engine, name)))
		except Exception as e:
			log('Error: loading provider "%s" from %s engine: %s' % (name, engine, e))
	if not impls: return None
	if len(impls) == 1: return _traced(name, impls[0][0], impls[0][1])
	return make_composite(name, impls)


def sources(specified_folders=None, ret_all=False):
	sourceDict = []
	try:
		if specified_folders and sourceFolder not in specified_folders: return sourceDict
		for name in registry.providers():
			if not (ret_all or enabledCheck(name)): continue
			cls = load_provider(name)
			if cls is not None: sourceDict.append((name, cls))
	except Exception as e:
		log('sources() failure: %s' % e)
	log('sources() for %s: %d providers (ret_all=%s): %s' % (caller_id(), len(sourceDict), ret_all, ', '.join(n for n, _ in sourceDict)))
	return sourceDict


def pack_sources(sourceSubFolder='torrents'):
	try: return [name for name, cls in sources(ret_all=True) if getattr(cls, 'pack_capable', False)]
	except Exception: return []


def provider_names():
	return list(registry.providers())
