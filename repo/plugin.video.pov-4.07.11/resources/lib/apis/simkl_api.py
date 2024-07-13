import requests
from threading import Thread
from caches.main_cache import cache_object
from caches.meta_cache import cache_function
from modules import kodi_utils

get_setting, logger = kodi_utils.get_setting, kodi_utils.logger
EXPIRES_2_DAYS, EXPIRES_1_WEEK, EXPIRES_1_MONTH = 48, 168, 672
API_KEY = get_setting('simkl_api')
base_url = 'https://api.simkl.com'
timeout = 3.05
session = requests.Session()
session.mount(base_url, requests.adapters.HTTPAdapter(pool_maxsize=100))

def call_simkl(url):
	params = {'client_id': API_KEY} if API_KEY else None
	try:
		response = session.get(url, params=params, timeout=timeout)
		response.raise_for_status()
	except requests.exceptions.RequestException as e:
		logger('simkl error', f"{e}\n{e.request.headers}\n{e.response.text}")
	if response.ok: return response.json()
	elif 'Retry-After' in response.headers:
		throttle_time = response.headers['Retry-After']
		kodi_utils.sleep((int(throttle_time) + 1) * 1000)
		return call_simkl(url)
	else: return None

def simkl_list(url):
	try:
		result = call_simkl(url)
		if result is None: return
	except: return
	collector = {}
	sort_list = []
	threads = []
	for i in result:
		sort_list.append(i['ids']['simkl_id'])
		t = Thread(target=summary, args=(i['ids']['simkl_id'], collector))
		threads.append(t)
		t.start()

	[i.join() for i in threads]
	items = [item for i in sort_list if (item := collector.get(i))]
	return items

def summary(sid, collector, media='anime'):
	try:
		string = 'simkl_anime_id_%s' % sid
		url = '%s/%s/%s?extended=full' % (base_url, media, sid)
		result = cache_function(call_simkl, string, url, EXPIRES_1_WEEK, json=False)
		if result is None: return
		imdb = result.get('ids').get('imdb') if result.get('ids').get('imdb') else ''
		tmdb = result.get('ids').get('tmdb') if result.get('ids').get('tmdb') else ''
		title = result.get('en_title') if result.get('en_title') else result.get('title')
		if tmdb or imdb: collector[sid] = {'imdb': str(imdb), 'tmdb': str(tmdb), 'title': title}
	except: pass

def simkl_movies_most_watched(page_no, media='anime'):
	string = 'simkl_movies_most_watched'
	url = '%s/%s/best/watched?type=movies' % (base_url, media)
	return cache_object(simkl_list, string, url, json=False, expiration=EXPIRES_2_DAYS)

def simkl_movies_most_voted(page_no, media='anime'):
	string = 'simkl_movies_most_voted'
	url = '%s/%s/best/voted?type=movies' % (base_url, media)
	return cache_object(simkl_list, string, url, json=False, expiration=EXPIRES_2_DAYS)

def simkl_movies_popular(page_no, media='anime'):
	string = 'simkl_movies_popular'
	url = '%s/%s/genres/all/movies/all-years/popular-this-week' % (base_url, media)
	return cache_object(simkl_list, string, url, json=False, expiration=EXPIRES_2_DAYS)

def simkl_movies_ranked(page_no, media='anime'):
	string = 'simkl_movies_ranked'
	url = '%s/%s/genres/all/movies/all-years/rank' % (base_url, media)
	return cache_object(simkl_list, string, url, json=False, expiration=EXPIRES_2_DAYS)

def simkl_movies_recent_release(page_no, media='anime'):
	string = 'simkl_movies_recent_release'
	url = '%s/%s/genres/all/movies/all-years/release-date' % (base_url, media)
	return cache_object(simkl_list, string, url, json=False, expiration=EXPIRES_2_DAYS)

def simkl_movies_genres(genre_id, media='anime'):
	string = 'simkl_movies_genres_%s' % genre_id
	url = '%s/%s/genres/%s/movies/all-years' % (base_url, media, genre_id)
	return cache_object(simkl_list, string, url, json=False, expiration=EXPIRES_2_DAYS)

def simkl_movies_year(year, media='anime'):
	string = 'simkl_movies_year_%s' % year
	url = '%s/%s/genres/all/movies/%s' % (base_url, media, year)
	return cache_object(simkl_list, string, url, json=False, expiration=EXPIRES_2_DAYS)

def simkl_tv_most_watched(page_no, media='anime'):
	string = 'simkl_tv_most_watched'
	url = '%s/%s/best/watched?type=tv' % (base_url, media)
	return cache_object(simkl_list, string, url, json=False, expiration=EXPIRES_2_DAYS)

def simkl_tv_most_voted(page_no, media='anime'):
	string = 'simkl_tv_most_voted'
	url = '%s/%s/best/voted?type=tv' % (base_url, media)
	return cache_object(simkl_list, string, url, json=False, expiration=EXPIRES_2_DAYS)

def simkl_tv_popular(page_no, media='anime'):
	string = 'simkl_tv_popular'
	url = '%s/%s/genres/all/series/all-years/popular-this-week' % (base_url, media)
	return cache_object(simkl_list, string, url, json=False, expiration=EXPIRES_2_DAYS)

def simkl_tv_ranked(page_no, media='anime'):
	string = 'simkl_tv_ranked'
	url = '%s/%s/genres/all/series/all-years/rank' % (base_url, media)
	return cache_object(simkl_list, string, url, json=False, expiration=EXPIRES_2_DAYS)

def simkl_tv_recent_release(page_no, media='anime'):
	string = 'simkl_tv_recent_release'
	url = '%s/%s/genres/all/series/all-years/release-date' % (base_url, media)
	return cache_object(simkl_list, string, url, json=False, expiration=EXPIRES_2_DAYS)

def simkl_tv_genres(genre_id, media='anime'):
	string = 'simkl_tv_genres_%s' % genre_id
	url = '%s/%s/genres/%s/series/all-years' % (base_url, media, genre_id)
	return cache_object(simkl_list, string, url, json=False, expiration=EXPIRES_2_DAYS)

def simkl_tv_year(year, media='anime'):
	string = 'simkl_tv_year_%s' % year
	url = '%s/%s/genres/all/series/%s' % (base_url, media, year)
	return cache_object(simkl_list, string, url, json=False, expiration=EXPIRES_2_DAYS)

def simkl_onas_most_watched(page_no, media='anime'):
	string = 'simkl_onas_most_watched'
	url = '%s/%s/best/watched?type=onas' % (base_url, media)
	return cache_object(simkl_list, string, url, json=False, expiration=EXPIRES_2_DAYS)

def simkl_onas_most_voted(page_no, media='anime'):
	string = 'simkl_onas_most_voted'
	url = '%s/%s/best/voted?type=onas' % (base_url, media)
	return cache_object(simkl_list, string, url, json=False, expiration=EXPIRES_2_DAYS)

def simkl_onas_popular(page_no, media='anime'):
	string = 'simkl_onas_popular'
	url = '%s/%s/genres/all/onas/all-years/popular-this-week' % (base_url, media)
	return cache_object(simkl_list, string, url, json=False, expiration=EXPIRES_2_DAYS)

def simkl_onas_ranked(page_no, media='anime'):
	string = 'simkl_onas_ranked'
	url = '%s/%s/genres/all/onas/all-years/rank' % (base_url, media)
	return cache_object(simkl_list, string, url, json=False, expiration=EXPIRES_2_DAYS)

def simkl_onas_recent_release(page_no, media='anime'):
	string = 'simkl_onas_recent_release'
	url = '%s/%s/genres/all/onas/all-years/release-date' % (base_url, media)
	return cache_object(simkl_list, string, url, json=False, expiration=EXPIRES_2_DAYS)

