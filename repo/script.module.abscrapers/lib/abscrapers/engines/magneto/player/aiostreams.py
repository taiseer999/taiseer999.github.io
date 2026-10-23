import json
import base64
import requests
from . import kore
from .kore import logger, get_setting, set_property, int_window_prop

public_instance = (
	'https://aiostreams.stremio.ru',
	'https://',
	'https://aiostreams.viren070.me',
	'https://aiostreams.fortheweak.cloud',
	'https://aiostreamsfortheweebsstable.midnightignite.me'
)

# AIOStreams service id -> Account Manager (script.module.acctmgr) setting ids, first non-empty wins
DEBRID_KEYS = (
	('realdebrid', ('realdebrid.token', 'rd.token')),
	('alldebrid', ('alldebrid.token', 'ad.token')),
	('premiumize', ('premiumize.token', 'pm.token')),
	('torbox', ('torbox.token', 'tb.token')),
	('offcloud', ('offcloud.token', 'oc.token')),
	('easydebrid', ('easydebrid.token', 'ed.token')),
)

def debrid_services():
	"""Debrid keys authorized in Account Manager, as AIOStreams 'services' entries."""
	try:
		import xbmcaddon
		am = xbmcaddon.Addon('script.module.acctmgr')
	except Exception:
		return []
	services = []
	for service_id, setting_ids in DEBRID_KEYS:
		for setting_id in setting_ids:
			try: value = (am.getSetting(setting_id) or '').strip()
			except Exception: value = ''
			if value:
				services.append({'id': service_id, 'enabled': True, 'credentials': {'apiKey': value}})
				break
	return services

def internal_results(provider, sources):
	set_property(int_window_prop % provider, json.dumps(sources))

class source:
	timeout = 30
	scrape_provider = 'aiostreams'
	def results(self, info):
		try:
			self.sources = []
			sources_append = self.sources.append
			title, season, episode = info.get('title'), info.get('season'), info.get('episode')
			if 'timeout' in info: self.timeout = info['timeout'] + 1
			media_id = info['imdb_id'] or ('tmdb:%s' % info['tmdb_id'])
			self.scrape_results = self.search(media_id, season, episode)
			if not self.scrape_results:
				logger(self.scrape_provider, f"{title} : 0 results")
				return internal_results(self.scrape_provider, self.sources)
			p2p = 0
			for item in self.scrape_results:
				if 'p2p' in str(item.get('type', '')):
					p2p += 1
					continue
				item.pop('sources', None)
				file = {'scrape_provider': self.scrape_provider, **item.pop('parsedFile', {})}
				try: file.update(item)
				except: pass
				else: sources_append(file)
			if p2p: logger(self.scrape_provider, f"{p2p} P2P results skipped (not debrid-cached, this player cannot play them)")
			if p2p and not self.sources: kore.notification('AIOStreams: %d P2P results only - add a debrid in Account Manager or an AIOStreams login' % p2p, 6000)
		except Exception as e: logger(f"Magneto {self.scrape_provider} Exception", f"{e}")
		if self.errors: logger(self.scrape_provider, f"{self.errors}")
		logger(self.scrape_provider, f"{title} : {self.elapsed}s, {len(self.sources)}, {len(getattr(self, 'scrape_results', []) or [])}")
		internal_results(self.scrape_provider, self.sources)
		return self.sources

	def search(self, media_id, season, episode):
		scrape_results = []
		if episode: params = {'type': 'series', 'id': '%s:%s:%s' % (media_id, season, episode)}
		else: params = {'type': 'movie', 'id': '%s' % media_id}
		params['requiredFields'] = 'parsedFile'
		try:
			base_url, auth, headers = self.connection()
			if not base_url:
				logger(self.scrape_provider, 'no instance URL set (Custom instance with empty URL)')
				return scrape_results
			search_link = '%s/api/v1/search' % base_url
			response = requests.get(search_link, params=params, auth=auth, headers=headers, timeout=self.timeout)
			if response.status_code in (401, 403):
				logger(self.scrape_provider, f"HTTP {response.status_code} from {base_url}: wrong UUID/password for this instance (UUIDs are per instance)")
			if not response.ok: response.raise_for_status()
			results = response.json()['data']
			self.elapsed = round(response.elapsed.total_seconds(), 3)
			self.errors = [': '.join(str(v) for v in i.values()) for i in results.get('errors') or []]
			scrape_results.extend(results.get('results') or [])
		except requests.exceptions.RequestException as e:
			url = getattr(getattr(e, 'request', None), 'url', '')
			logger(self.scrape_provider, f"{e}\n{url}")
		except Exception as e:
			logger(self.scrape_provider, f"bad response: {e}")
		return scrape_results

	def connection(self):
		"""(base_url, auth, headers).
		1. Player login (AIOStreams Player > Username/Password) on the player instance.
		2. else the scraper login (Instances > AIOStreams) on the scraper instance.
		3. else anonymous on the player instance with the built-in AIOStreams config
		   (same as the AIOStreams scraper) - before 1.1.2 this case returned nothing silently."""
		user, password = get_setting('aio.username').strip(), get_setting('aio.password').strip()
		if user and password:
			return self._player_url(), (user, password), None
		user, password = get_setting('aiostreams.username').strip(), get_setting('aiostreams.password').strip()
		if user and password:
			logger(self.scrape_provider, 'player login empty - using the AIOStreams scraper login and instance')
			return self._scraper_url(), (user, password), None
		from abscrapers.engines.coco.sources_cocoscrapers.torrents.aiostreams import source as coco_aio
		headers = coco_aio._headers(None)
		services = debrid_services()
		if services:
			try:
				config = json.loads(base64.b64decode(headers['x-aiostreams-user-data']))
				config['services'] = services
				headers = {'x-aiostreams-user-data': base64.b64encode(json.dumps(config).encode()).decode()}
				logger(self.scrape_provider, 'no AIOStreams login set - anonymous search with your debrid from Account Manager: %s' % ', '.join(i['id'] for i in services))
			except Exception as e:
				logger(self.scrape_provider, 'could not add debrid to the built-in config: %s' % e)
		else:
			logger(self.scrape_provider, 'no AIOStreams login and no debrid in Account Manager - results will be P2P only, which this player cannot play')
		return self._player_url(), None, headers

	def _player_url(self):
		try: instance_id = int(get_setting('aiostreams_instance', '0'))
		except ValueError: instance_id = 0
		if instance_id == 1: base_url = get_setting('aio.custom_url')
		else: base_url = public_instance[instance_id] if instance_id < len(public_instance) else public_instance[0]
		return (base_url or '').strip().rstrip('/')

	def _scraper_url(self):
		instances = (public_instance[0], public_instance[2], public_instance[3], public_instance[4])
		try: instance_id = int(get_setting('aiostreams.instance', '0'))
		except ValueError: instance_id = 0
		if instance_id >= len(instances): return get_setting('aiostreams.custom_url').strip().rstrip('/')
		return instances[instance_id]

	def __init__(self):
		self.elapsed = None
		self.errors = []
