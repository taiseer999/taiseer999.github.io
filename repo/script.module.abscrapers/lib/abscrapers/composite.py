# -*- coding: utf-8 -*-
"""
	AB Scrapers - composite provider.
	Wraps several engine implementations of one provider behind the standard
	Fenomscrapers "source" class interface, runs them in parallel and merges the
	results by info-hash so the calling addon never sees duplicates.
"""

import threading
import time
from abscrapers.common import setting, log, debug_enabled, trace


def _key(item):
	h = (item.get('hash') or '').lower()
	base = h or (item.get('url') or '').lower()
	return (base, item.get('package', ''), item.get('episode_start', 0), item.get('last_season', 0))


def _seeders(item):
	try: return int(item.get('seeders') or 0)
	except Exception: return 0


def merge(result_lists):
	"""Union of all lists; on duplicate hash keep the entry with more seeders."""
	merged, order = {}, []
	for results in result_lists:
		for item in results or []:
			if not isinstance(item, dict): continue
			k = _key(item)
			if not k[0]:
				k = ('_nokey_%d' % len(order),)
			if k not in merged:
				merged[k] = item; order.append(k)
			elif _seeders(item) > _seeders(merged[k]):
				merged[k] = item
	return [merged[k] for k in order]


def _timeout():
	try: return max(5, int(float(setting('composite.timeout') or 30)))
	except Exception: return 30


def make_composite(name, impls):
	"""impls: list of (engine, source_class). One implementation -> returned untouched (zero overhead)."""
	if len(impls) == 1: return impls[0][1]
	impls = list(impls)
	classes = [c for _, c in impls]

	class source(object):
		priority = min(getattr(c, 'priority', 1) for c in classes)
		pack_capable = any(getattr(c, 'pack_capable', False) for c in classes)
		hasMovies = any(getattr(c, 'hasMovies', True) for c in classes)
		hasEpisodes = any(getattr(c, 'hasEpisodes', True) for c in classes)
		ab_provider = name
		ab_engines = tuple(e for e, _ in impls)

		def __init__(self):
			self.language = ['en']
			self._instances = {}
			self._ilock = threading.Lock()

		def _instance(self, engine, cls):
			with self._ilock:
				inst = self._instances.get(engine)
				if inst is None:
					inst = cls()
					self._instances[engine] = inst
				return inst

		def _run(self, method, wants, *args, **kwargs):
			collected, lock = [], threading.Lock()

			def worker(engine, cls):
				try:
					res = trace(name, engine, method, lambda: getattr(self._instance(engine, cls), method)(*args, **kwargs)) or []
					with lock: collected.append(res)
				except Exception as e:
					log('%s[%s].%s failed: %s' % (name, engine, method, e))

			threads = []
			for engine, cls in impls:
				if not wants(cls) or not hasattr(cls, method): continue
				t = threading.Thread(target=worker, args=(engine, cls), name='abscrapers.%s.%s' % (name, engine))
				t.daemon = True
				t.start(); threads.append(t)
			deadline = time.monotonic() + _timeout()
			for t in threads: t.join(max(0.0, deadline - time.monotonic()))
			with lock: snapshot = list(collected)
			return merge(snapshot)

		def sources(self, data, hostDict):
			if not data: return []
			episode = 'tvshowtitle' in data
			wants = (lambda c: getattr(c, 'hasEpisodes', True)) if episode else (lambda c: getattr(c, 'hasMovies', True))
			return self._run('sources', wants, data, hostDict)

		def sources_packs(self, data, hostDict, search_series=False, total_seasons=None, bypass_filter=False):
			if not data: return []
			return self._run('sources_packs', lambda c: getattr(c, 'pack_capable', False), data, hostDict,
							search_series=search_series, total_seasons=total_seasons, bypass_filter=bypass_filter)

	return source
