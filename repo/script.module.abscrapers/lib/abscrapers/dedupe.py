# -*- coding: utf-8 -*-
"""
	AB Scrapers - repeated-results filter.

	Indexers such as Comet often return the SAME release several times under
	different info-hashes (re-uploads / tracker variants: identical name, identical
	size). The calling add-on only de-duplicates by hash, so all of them reach the
	results list. This filter removes them.

	Settings (Filters):
	  filter.duplicates        0 = Off, 1 = same hash, 2 = same release name + size (default)
	  filter.duplicates.cross  also drop repeats already returned by another provider
	                           in the same search (default on)

	Within one provider call the copy with the most seeders is kept. Across
	providers the first provider to return a release keeps it (earlier results are
	already in the add-on's hands). A "search" is the data dict the add-on passes
	to every provider (Fen Light / Umbrella movies pass one shared dict); if an
	add-on copies the dict per provider, only the per-provider filter applies.
"""

import re
import threading
import time
from abscrapers.common import setting, log, trace_enabled

_SESSIONS = {}   # id(data) -> [data, set(keys), last_used]
_LOCK = threading.Lock()
_TTL = 600       # seconds a search session is remembered
_NON_ALNUM = re.compile(r'[^a-z0-9]+')


def mode():
	try: return int(setting('filter.duplicates') or 2)
	except Exception: return 2


def _seeders(item):
	try: return int(item.get('seeders') or 0)
	except Exception: return 0


def _size(item):
	try: return round(float(item.get('size') or 0), 2)
	except Exception: return 0.0


def keys_for(item, m):
	"""All identity keys of one result for mode m (a result is a repeat if ANY key was seen)."""
	scope = (str(item.get('package', '')), str(item.get('episode_start', '')), str(item.get('last_season', '')))
	keys = []
	h = (item.get('hash') or '').lower().strip()
	if h: keys.append(('h', h) + scope)
	elif item.get('url'): keys.append(('u', str(item['url']).lower()) + scope)
	if m >= 2:
		name = _NON_ALNUM.sub('', str(item.get('name') or '').lower())
		if name: keys.append(('n', name, _size(item)) + scope)
	return keys


def _filter_list(results, m):
	"""Drop repeats inside one result list; keep the copy with the most seeders."""
	best, order, index = {}, [], {}
	for item in results:
		if not isinstance(item, dict):
			order.append(('_raw', len(order))); best[order[-1]] = item; continue
		ks = keys_for(item, m)
		slot = next((index[k] for k in ks if k in index), None)
		if slot is None:
			slot = ('_slot', len(order)); order.append(slot); best[slot] = item
		elif _seeders(item) > _seeders(best[slot]):
			best[slot] = item
		for k in ks + keys_for(best[slot], m): index[k] = slot
	return [best[s] for s in order]


def _session(data):
	now = time.monotonic()
	with _LOCK:
		for k in [k for k, v in _SESSIONS.items() if now - v[2] > _TTL]: _SESSIONS.pop(k, None)
		entry = _SESSIONS.get(id(data))
		if entry is None or entry[0] is not data:
			entry = [data, set(), now]
			_SESSIONS[id(data)] = entry
		entry[2] = now
		return entry


def apply(results, data, provider=''):
	"""Filter one provider's results. Never raises; returns the input unchanged on error."""
	try:
		m = mode()
		if not m or not results: return results
		before = len(results)
		out = _filter_list(list(results), m)
		if isinstance(data, dict) and setting('filter.duplicates.cross') != 'false':
			entry = _session(data)
			with _LOCK:
				seen, kept = entry[1], []
				for item in out:
					ks = keys_for(item, m) if isinstance(item, dict) else []
					if ks and any(k in seen for k in ks): continue
					seen.update(ks); kept.append(item)
			out = kept
		dropped = before - len(out)
		if dropped and trace_enabled():
			log('%s: %d repeated results filtered (%d kept)' % (provider, dropped, len(out)))
		return out
	except Exception as e:
		log('repeat filter error (%s): %s' % (provider, e))
		return results
