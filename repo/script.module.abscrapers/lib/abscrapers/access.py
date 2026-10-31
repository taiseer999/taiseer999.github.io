# -*- coding: utf-8 -*-
"""
	AB Scrapers - provider access check ("is this provider banned/blocked for me?").

	The health check only shows that a provider returned nothing. This probes every
	host a provider talks to and says WHY it is unreachable:

	  OK               reachable (any HTTP answer from the real site, 404 included)
	  DNS_BLOCK        your DNS gives no / a sinkhole address, public DNS (DoH) resolves it
	  DNS_FAIL         no DNS anywhere - domain dead
	  CONN_RESET       DNS fine, connection cut during connect/TLS - typical ISP SNI/DPI block
	  BLOCK_PAGE       an answer, but it is an ISP / regulator "site blocked" page
	  CLOUDFLARE       Cloudflare browser challenge - scraper can't pass it
	  BANNED           HTTP 403 - your IP / country is refused
	  RATE_LIMIT       HTTP 429 - too many requests, wait and retry
	  LEGAL            HTTP 451 - blocked for legal reasons
	  TIMEOUT          no answer in time - site down, overloaded or silently dropped
	  SERVER_ERROR     HTTP 5xx - site is up but broken
	  ERROR            anything else (shown with the exception)
"""

import ipaddress
import os
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor

from abscrapers import registry
from abscrapers.common import setting, log

OK, DNS_BLOCK, DNS_FAIL, CONN_RESET, BLOCK_PAGE, CLOUDFLARE, BANNED, RATE_LIMIT, LEGAL, TIMEOUT, SERVER_ERROR, ERROR = (
	'OK', 'DNS_BLOCK', 'DNS_FAIL', 'CONN_RESET', 'BLOCK_PAGE', 'CLOUDFLARE', 'BANNED', 'RATE_LIMIT', 'LEGAL',
	'TIMEOUT', 'SERVER_ERROR', 'ERROR')
BAD_FOR_YOU = (DNS_BLOCK, CONN_RESET, BLOCK_PAGE, BANNED, LEGAL)   # site works, you are blocked
SEVERITY = {OK: 0, RATE_LIMIT: 1, SERVER_ERROR: 2, TIMEOUT: 3, CLOUDFLARE: 4, ERROR: 5, DNS_FAIL: 6,
			BANNED: 7, LEGAL: 7, BLOCK_PAGE: 8, CONN_RESET: 8, DNS_BLOCK: 8}

_URL_RE = re.compile(r'https?://([a-z0-9][a-z0-9.-]*\.[a-z]{2,})', re.I)
_QUOTED_DOMAIN_RE = re.compile(r"""['"]((?:[a-z0-9-]+\.)+[a-z]{2,})['"]""", re.I)
_DOMAINS_BLOCK_RE = re.compile(r'(?:domains|base_links|mirrors)\s*=\s*[\[(](.*?)[\])]', re.I | re.S)
_IGNORE_HOSTS = ('torznab.com', 'www.w3.org', 'xmlns.com', 'schemas.xmlsoap.org', 'image.tmdb.org',
				 'api.themoviedb.org', 'v2.sg.media-imdb.com', 'github.com', 'raw.githubusercontent.com')
_EXTRA_HOSTS = {'telegrambot': ['web.telegram.org']}
_SETTING_HOSTS = {'prowlarr': ['prowlarr.url'], 'aiostreams': ['aiostreams.custom_url'],
				  'mediafusion': ['mediafusion.customurl']}
_BLOCK_MARKERS = ('this site is blocked', 'this website is blocked', 'site has been blocked', 'access to this site',
				  'blocked by order', 'blocked as per', 'telecommunications regulatory', 'trc.gov.jo', 'unauthorized website',
				  'تم حجب', 'محجوب', 'الموقع محظور', 'هذا الموقع غير متاح', 'هيئة تنظيم قطاع الاتصالات')
_CF_MARKERS = ('just a moment', 'cf-chl', 'challenge-platform', 'attention required! | cloudflare')
_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'


STATUS_TEXT = {
	OK: 'Reachable', DNS_BLOCK: 'Blocked (DNS)', DNS_FAIL: 'Domain dead', CONN_RESET: 'Blocked (connection cut)',
	BLOCK_PAGE: 'Blocked (block page)', CLOUDFLARE: 'Cloudflare challenge', BANNED: 'Banned (HTTP 403)',
	RATE_LIMIT: 'Rate-limited', LEGAL: 'Blocked (legal, HTTP 451)', TIMEOUT: 'No response', SERVER_ERROR: 'Site error',
	ERROR: 'Error'}
HINT_TEXT = {
	OK: 'Reachable from your connection. If it still returns nothing, the site changed or has no release for this title.',
	DNS_BLOCK: 'Your DNS (usually the ISP) hides this site while public DNS knows it. Fix: set the box DNS to 1.1.1.1 / 8.8.8.8 (CoreELEC: Settings > Network) or use DNS-over-HTTPS on the router.',
	CONN_RESET: 'DNS is fine but the connection is cut while connecting - the typical ISP filter on the site name (SNI). Changing DNS does not help; a VPN or proxy does.',
	BLOCK_PAGE: 'Your ISP or regulator answers with a "site blocked" page instead of the site. Use a VPN or another mirror.',
	CLOUDFLARE: 'The site sits behind a Cloudflare browser check that scrapers cannot pass. Not a ban on you: disable the provider or switch its engine/mirror.',
	BANNED: 'The site refuses your IP or country (HTTP 403). A VPN in another country usually works.',
	RATE_LIMIT: 'Too many requests from your IP. Wait a few minutes; avoid running the same provider from several engines (set its Engine to one).',
	LEGAL: 'Blocked for legal reasons in your region (HTTP 451). Use a VPN or another mirror.',
	TIMEOUT: 'No answer in time: the site is down or overloaded, or your network silently drops it. If it never answers but works over a VPN, it is blocked.',
	SERVER_ERROR: 'The site answers but is broken right now (HTTP 5xx). Usually temporary.',
	DNS_FAIL: 'The domain does not exist anywhere any more. The provider needs a new address - disable it until an update.',
	ERROR: 'Unexpected error - see the detail line.'}


def status_text(s):
	from abscrapers.strings import ls
	return ls(STATUS_TEXT.get(s, s))


# ---------------------------------------------------------------- endpoints
def _hosts_in_file(path):
	try:
		with open(path, encoding='utf-8', errors='ignore') as f: src = f.read()
	except Exception: return []
	hosts = [h.lower() for h in _URL_RE.findall(src)]
	for block in _DOMAINS_BLOCK_RE.findall(src):
		hosts += [d.lower() for d in _QUOTED_DOMAIN_RE.findall(block)]
	out = []
	for h in hosts:
		h = h.strip('.')
		if any(h == i or h.endswith('.' + i) for i in _IGNORE_HOSTS): continue
		if h not in out: out.append(h)
	return out


def _host_of(url):
	m = _URL_RE.match((url or '').strip())
	if m: return m.group(1).lower()
	m = re.match(r'^([a-z0-9.-]+\.[a-z]{2,})(?::\d+)?', (url or '').strip(), re.I)
	return m.group(1).lower() if m else ''


def provider_hosts(name, engines=None):
	"""Hosts the provider contacts with the engines that actually run for it."""
	engines = engines or registry.selected_engines(name, setting)
	hosts = []
	for engine in engines:
		for h in _hosts_in_file(os.path.join(registry.ENGINE_DIRS[engine], name + '.py')):
			if h not in hosts: hosts.append(h)
	for sid in _SETTING_HOSTS.get(name, ()):
		h = _host_of(setting(sid))
		if h and h not in hosts: hosts.insert(0, h)
	for h in _EXTRA_HOSTS.get(name, ()):
		if h not in hosts: hosts.append(h)
	return hosts


# ---------------------------------------------------------------- probes
def _is_sinkhole(ip):
	try:
		a = ipaddress.ip_address(ip)
		return a.is_private or a.is_loopback or a.is_unspecified or a.is_reserved or a.is_link_local
	except Exception: return False


def system_dns(host):
	try: return sorted({i[4][0] for i in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)})
	except Exception: return []


def public_dns(host, session=None):
	"""DNS-over-HTTPS (Cloudflare, then Google). None = DoH itself unreachable."""
	import requests
	s = session or requests
	for url in ('https://cloudflare-dns.com/dns-query', 'https://dns.google/resolve'):
		try:
			r = s.get(url, params={'name': host, 'type': 'A'}, headers={'accept': 'application/dns-json'}, timeout=5)
			js = r.json()
			return sorted({a['data'] for a in js.get('Answer', []) if a.get('type') == 1})
		except Exception: continue
	return None


def classify_http(status, headers, body):
	low = (body or '')[:20000].lower()
	hdr = {k.lower(): str(v).lower() for k, v in (headers or {}).items()}
	if any(m in low for m in _BLOCK_MARKERS): return BLOCK_PAGE
	if status in (403, 503) and (hdr.get('cf-mitigated') == 'challenge' or ('cloudflare' in hdr.get('server', '') and any(m in low for m in _CF_MARKERS))):
		return CLOUDFLARE
	if status == 403: return BANNED
	if status == 429: return RATE_LIMIT
	if status == 451: return LEGAL
	if status >= 500: return SERVER_ERROR
	return OK


def classify_exception(e):
	name, text = type(e).__name__, str(e).lower()
	if 'timeout' in name.lower() or 'timed out' in text: return TIMEOUT
	if any(k in text for k in ('connection reset', 'connectionreseterror', 'remotedisconnected', 'connection aborted',
							   'eof occurred in violation', 'unexpected_eof', 'wrong version number', 'tlsv1 alert', 'econnreset')):
		return CONN_RESET
	if any(k in text for k in ('name or service not known', 'nodename nor servname', 'getaddrinfo failed', 'failed to resolve',
							   'name resolution', 'no address associated')):
		return DNS_FAIL
	if 'connection refused' in text: return CONN_RESET
	return ERROR


def probe_host(host, session=None):
	"""Probe one host. Returns dict(host, status, code, ips, doh, detail, ms)."""
	import requests
	s = session or requests
	res = {'host': host, 'status': ERROR, 'code': 0, 'ips': [], 'doh': None, 'detail': '', 'ms': 0}
	start = time.monotonic()
	res['ips'] = sys_ips = system_dns(host)
	if not sys_ips or all(_is_sinkhole(i) for i in sys_ips):
		res['doh'] = doh = public_dns(host, s)
		if doh: res.update(status=DNS_BLOCK, detail='your DNS: %s | public DNS: %s' % (', '.join(sys_ips) or 'no answer', ', '.join(doh[:3])))
		elif doh is None: res.update(status=DNS_FAIL, detail='no DNS answer (public DNS unreachable to compare)')
		else: res.update(status=DNS_FAIL, detail='domain does not resolve anywhere')
		res['ms'] = int((time.monotonic() - start) * 1000)
		return res
	try:
		r = s.get('https://%s/' % host, headers={'User-Agent': _UA}, timeout=(6, 10), allow_redirects=True, stream=True)
		body = ''
		try: body = next(r.iter_content(20000, decode_unicode=False), b'').decode('utf-8', 'ignore')
		except Exception: pass
		res['code'] = r.status_code
		res['status'] = classify_http(r.status_code, r.headers, body)
		final = _host_of(getattr(r, 'url', '') or '')
		if final and final != host and res['status'] == OK: res['detail'] = 'redirects to %s' % final
		if res['status'] != OK: res['detail'] = 'HTTP %d%s' % (r.status_code, (' via %s' % final) if final and final != host else '')
		try: r.close()
		except Exception: pass
	except Exception as e:
		res['status'] = classify_exception(e)
		res['detail'] = ('%s: %s' % (type(e).__name__, e))[:160]
	if res['status'] in (CONN_RESET, TIMEOUT, ERROR):
		doh = public_dns(host, s)
		res['doh'] = doh
		if doh and not set(doh) & set(sys_ips):
			res['detail'] += ' | your DNS %s differs from public DNS %s' % (', '.join(sys_ips[:2]), ', '.join(doh[:2]))
	res['ms'] = int((time.monotonic() - start) * 1000)
	return res


def worst(results):
	if not results: return ERROR
	if any(r['status'] == OK for r in results): return OK  # a working mirror is enough
	return max((r['status'] for r in results), key=lambda s: SEVERITY.get(s, 5))


def check(names, progress=None, workers=16):
	"""names -> [(name, overall_status, [host results])]; progress(done, total, host)."""
	import requests
	plan = {n: provider_hosts(n) for n in names}
	hosts = sorted({h for hs in plan.values() for h in hs})
	session = requests.Session()
	out, done = {}, [0]
	def run(h):
		r = probe_host(h, session)
		done[0] += 1
		if progress:
			try: progress(done[0], len(hosts), h)
			except Exception: pass
		return r
	with ThreadPoolExecutor(max(1, min(workers, len(hosts) or 1))) as pool:
		for r in pool.map(run, hosts): out[r['host']] = r
	report = []
	for n in names:
		hr = [out[h] for h in plan[n] if h in out]
		report.append((n, worst(hr) if hr else ERROR, hr))
		log('[Access] %s: %s | %s' % (n, report[-1][1], '; '.join('%s=%s%s' % (r['host'], r['status'], (' (' + r['detail'] + ')') if r['detail'] else '') for r in hr) or 'no hosts found'))
	return report


# ---------------------------------------------------------------- UI
def run_dialog():
	import xbmcgui, xbmcaddon
	from abscrapers.strings import ls
	from abscrapers.common import ADDON_ID
	import abscrapers
	dialog = xbmcgui.Dialog()
	mode = dialog.select(ls('Check provider access (blocked / banned)'), [ls('Enabled providers only'), ls('Every provider')])
	if mode < 0: return
	names = abscrapers.provider_names() if mode == 1 else [n for n in abscrapers.provider_names() if abscrapers.enabledCheck(n)]
	if not names: return dialog.notification('AB Scrapers', ls('No providers enabled'))
	pd = xbmcgui.DialogProgress()
	pd.create('AB Scrapers', ls('Checking provider access...'))
	report = check(names, progress=lambda d, t, h: pd.update(int(d * 100 / max(t, 1)), '%s[CR]%d / %d' % (h, d, t)))
	pd.close()
	color = {OK: 'lime', RATE_LIMIT: 'yellow', SERVER_ERROR: 'orange', TIMEOUT: 'orange', CLOUDFLARE: 'orange',
			 DNS_FAIL: 'grey', ERROR: 'grey'}
	report.sort(key=lambda x: (-SEVERITY.get(x[1], 5), x[0]))
	icon = xbmcaddon.Addon(ADDON_ID).getAddonInfo('icon')
	items = []
	for name, status, hr in report:
		c = color.get(status, 'red')
		li = xbmcgui.ListItem('[COLOR %s][B]%s[/B][/COLOR]  %s' % (c, status_text(status), name.upper()),
							  '  |  '.join('%s: %s%s' % (r['host'], status_text(r['status']), (' - ' + r['detail']) if r['detail'] else '') for r in hr) or ls('No hosts found'),
							  offscreen=True)
		li.setArt({'icon': icon})
		items.append(li)
	blocked = sum(1 for _, s, _ in report if s in BAD_FOR_YOU)
	heading = '%s - %s: %d' % (ls('Provider access'), ls('Blocked for you'), blocked)
	while True:
		i = dialog.select(heading, items, useDetails=True)
		if i < 0: break
		name, status, hr = report[i]
		lines = ['[B]%s[/B]: %s' % (name.upper(), status_text(status)), '', ls(HINT_TEXT.get(status, '')), '']
		for r in hr:
			lines.append('%s  ->  %s  %s' % (r['host'], status_text(r['status']), ('HTTP %d' % r['code']) if r['code'] else ''))
			if r['ips']: lines.append('    IP: %s' % ', '.join(r['ips'][:3]))
			if r['detail']: lines.append('    %s' % r['detail'])
		dialog.textviewer('AB Scrapers - %s' % name.upper(), '[CR]'.join(lines))
