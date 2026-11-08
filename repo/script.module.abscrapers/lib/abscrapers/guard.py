# -*- coding: utf-8 -*-
"""
	AB Scrapers - provider guard (v1.1.6).

	Two protections around every provider call (single-engine and composite):

	1. Hard deadline. The real call runs in its own thread; the caller gets an
	   answer (the results, or [] on timeout) after at most provider.timeout
	   seconds. Before 1.1.6 only multi-engine providers had a deadline, so one
	   single-engine provider stuck on a dead site (BTDig, LimeTorrents, MagnetDL
	   in kodi.log 2026-11-08) held Fen Light / Umbrella / Red Light open forever
	   and AB Search All froze Kodi.

	2. Shared results (single-flight). AB Search All asks Fen Light, Umbrella
	   and Red Light for the same title at the same moment, and each of them ran
	   all 28 providers again (~84 scraper threads). Now the first add-on to ask
	   a provider does the network work; the others wait for its answer and get
	   a copy. Results live in a Kodi window property for share.ttl seconds, so
	   they are visible to every add-on (each runs in its own Python interpreter).
	   Each caller still applies its own repeated-results filter afterwards.
"""

import json
import threading
import time
from hashlib import md5

import xbmc
import xbmcgui

from abscrapers.common import setting, log

_WIN = None
_PREFIX = 'abscrapers.sf.'
_INDEX = 'abscrapers.sf.index'
_LOCAL_LOCK = threading.Lock()
_POLL = 0.25


def _win():
	global _WIN
	if _WIN is None: _WIN = xbmcgui.Window(10000)
	return _WIN


def provider_timeout():
	try: return max(5, int(float(setting('provider.timeout') or 15)))
	except Exception: return 15


def share_enabled():
	return setting('share.results') != 'false'


def _ttl():
	try: return max(30, int(float(setting('share.ttl') or 180)))
	except Exception: return 180


# ---------- key ----------

def _key(provider, method, data, kwargs):
	"""Same title + same provider + same call = same key, whichever add-on asks."""
	if not isinstance(data, dict): return None
	ident = data.get('imdb') or data.get('tmdb') or ''
	title = data.get('tvshowtitle') or data.get('title') or ''
	if not (ident or title): return None
	parts = [provider, method, str(ident).lower(), str(title).lower(), str(data.get('year') or ''),
			 str(data.get('season') or ''), str(data.get('episode') or '')]
	if kwargs:
		parts.append(json.dumps(kwargs, sort_keys=True, default=str))
	return md5('|'.join(parts).encode('utf-8')).hexdigest()


# ---------- window-property store ----------

def _read(key):
	try:
		raw = _win().getProperty(_PREFIX + key)
		return json.loads(raw) if raw else None
	except Exception:
		return None


def _write(key, value):
	try: _win().setProperty(_PREFIX + key, json.dumps(value, default=str))
	except Exception: pass


def _clear(key):
	try: _win().clearProperty(_PREFIX + key)
	except Exception: pass


def _index_add(key):
	"""Remember stored keys with their time so stale entries get dropped."""
	now = time.time()
	ttl = _ttl()
	try:
		idx = json.loads(_win().getProperty(_INDEX) or '{}')
	except Exception:
		idx = {}
	for k, ts in list(idx.items()):
		if now - ts > ttl * 2:
			_clear(k); idx.pop(k, None)
	idx[key] = now
	try: _win().setProperty(_INDEX, json.dumps(idx))
	except Exception: pass


# ---------- bounded call ----------

def _bounded(run, timeout, label):
	"""Run run() in a daemon thread; return (finished, result)."""
	box = {}

	def worker():
		try: box['res'] = run()
		except Exception as e: box['err'] = e

	t = threading.Thread(target=worker, name='abscrapers.guard.%s' % label)
	t.daemon = True
	t.start()
	t.join(timeout)
	if t.is_alive():
		log('%s gave no answer within %.0fs - returned 0 results, the caller is not kept waiting' % (label, timeout), xbmc.LOGWARNING)
		return False, []
	if 'err' in box: raise box['err']
	return True, box.get('res') or []


def call(provider, method, data, kwargs, run):
	"""Guarded provider call. run() performs the real search and returns a list."""
	timeout = provider_timeout()
	label = '%s.%s' % (provider, method)
	key = _key(provider, method, data, kwargs) if share_enabled() else None
	if not key:
		return _bounded(run, timeout, label)[1]

	deadline = time.monotonic() + timeout
	ttl = _ttl()
	while True:
		with _LOCAL_LOCK:
			entry = _read(key)
			now = time.time()
			if entry and entry.get('state') == 'done' and now - entry.get('ts', 0) <= ttl:
				res = entry.get('res') or []
				log('%s: %d shared results (searched %.0fs ago by %s)' % (label, len(res), now - entry.get('ts', 0), entry.get('by', '?')))
				return res
			running = entry and entry.get('state') == 'running' and now - entry.get('ts', 0) <= timeout + 2
			if not running:
				from abscrapers.common import caller_id
				me = caller_id()
				_write(key, {'state': 'running', 'ts': now, 'by': me})
				break
		if time.monotonic() >= deadline:
			log('%s: other add-on still searching after %ds - returned 0 results' % (label, timeout), xbmc.LOGWARNING)
			return []
		xbmc.sleep(int(_POLL * 1000))

	try:
		finished, res = _bounded(run, max(1.0, deadline - time.monotonic()), label)
	except Exception:
		_clear(key)
		raise
	if finished:
		try:
			json.dumps(res, default=str)
			_write(key, {'state': 'done', 'ts': time.time(), 'by': me, 'res': res})
			_index_add(key)
		except Exception:
			_clear(key)
	else:
		_clear(key)
	return res
