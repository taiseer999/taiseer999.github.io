import sys
from queue import SimpleQueue
from threading import Thread
from apis.tmdb_api import TMDBList
from indexers.movies import Movies
from indexers.tvshows import TVShows
from modules import kodi_utils, settings
from modules.utils import TaskPool
# logger = kodi_utils.logger

KODI_VERSION, ls = kodi_utils.get_kodi_version(), kodi_utils.local_string
build_url, make_listitem = kodi_utils.build_url, kodi_utils.make_listitem
default_icon = kodi_utils.translate_path('special://home/addons/plugin.video.pov/resources/media/tmdb.png')
default_fanart = kodi_utils.translate_path('special://home/addons/plugin.video.pov/fanart.png')
item_jump = kodi_utils.translate_path('special://home/addons/plugin.video.pov/resources/media/item_jump.png')
add2menu_str, add2folder_str = ls(32730), ls(32731)
newlist_str, deletelist_str, nextpage_str, jump2_str = ls(32780), ls(32781), ls(32799), ls(32964)

def get_tmdb_lists(params):
	def _process():
		for item in lists:
			try:
				cm = []
				cm_append = cm.append
				poster_path, fanart_path = item['poster_path'], item['backdrop_path']
				poster = tmdb_image_base % (image_resolution['poster'], poster_path) if poster_path else default_icon
				fanart = tmdb_image_base % (image_resolution['fanart'], fanart_path) if fanart_path else default_fanart
				name, user = item['name'], item['account_object_id']
				item_count, list_id = item['number_of_items'], item['id']
				display = '%s (x%s)' % (name, item_count) if item_count else name
				if not item['public']: display = '[COLOR cyan][I]%s[/I][/COLOR]' % display
				plot = '[B]Updated[/B]: %s[CR]%s' % (item['updated_at'], item['description'])
				url = build_url({'mode': 'build_tmdb_list', 'user': user, 'list_id': list_id, 'name': name})
				cm_append((add2menu_str, 'RunPlugin(%s)' % build_url({'mode': 'menu_editor.add_external', 'name': display, 'iconImage': 'tmdb.png'})))
				cm_append((add2folder_str, 'RunPlugin(%s)' % build_url({'mode': 'menu_editor.shortcut_folder_add_item', 'name': display, 'iconImage': 'tmdb.png'})))
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.setArt({'icon': poster, 'poster': poster, 'thumb': poster, 'fanart': fanart, 'banner': poster})
				listitem.setInfo('video', {'plot': plot}) if KODI_VERSION < 20 else listitem.getVideoInfoTag().setPlot(plot)
				listitem.addContextMenuItems(cm, replaceItems=False)
				yield (url, listitem, True)
			except: pass
	image_resolution = settings.get_resolution()
	tmdb_image_base = 'https://image.tmdb.org/t/p/%s%s'
	lists = TMDBList().user_lists()
	page, total_pages = lists['page'], lists['total_pages']
	lists = lists['results']
	__handle__ = int(sys.argv[1])
	kodi_utils.add_items(__handle__, list(_process()))
	kodi_utils.set_category(__handle__, params.get('name'))
	kodi_utils.set_sort_method(__handle__, 'label')
	kodi_utils.set_content(__handle__, 'files')
	kodi_utils.end_directory(__handle__)
	kodi_utils.set_view_mode('view.main')

def build_tmdb_list(params):
	def _thread_target(q):
		while not q.empty():
			try: target, *args = q.get() ; target(*args)
			except: pass
	__handle__, _queue, is_widget = int(sys.argv[1]), SimpleQueue(), kodi_utils.external_browse()
	user, name = params.get('user'), params.get('name')
	list_id, page = params.get('list_id'), params.get('new_page', '1')
	results = TMDBList().details(list_id, page)
	page, total_pages = results['page'], results['total_pages']
	movies, tvshows = Movies({'id_type': 'tmdb_id'}), TVShows({'id_type': 'tmdb_id'})
	for idx, tag in enumerate(results['results'], 1):
		mtype = tag['media_type']
		if   mtype == 'movie':
			_queue.put((movies.build_movie_content, idx, tag['id']))
		elif mtype == 'tv':
			_queue.put((tvshows.build_tvshow_content, idx, tag['id']))
	maxsize = min(_queue.qsize(), int(kodi_utils.get_setting('pov.max_threads', '100')))
	threads = (Thread(target=_thread_target, args=(_queue,)) for i in range(maxsize))
	threads = list(TaskPool.process(threads))
	[i.join() for i in threads]
	items = movies.items + tvshows.items
	items.sort(key=lambda k: int(k[1].getProperty('pov_sort_order')))
	content, total = max(
		('movies', movies), ('tvshows', tvshows), key=lambda k: len(k[1].items)
	)
	if total_pages > 2 and not is_widget and settings.nav_jump_use_alphabet():
		url = {'mode': 'build_navigate_to_page', 'transfer_mode': 'build_tmdb_list', 'media_type': 'Media', 'name': name,
				'user': user, 'list_id': list_id, 'current_page': page, 'total_pages': total_pages}
		kodi_utils.add_dir(__handle__, url, jump2_str, iconImage=item_jump, isFolder=False)
	kodi_utils.add_items(__handle__, items)
	if total_pages > page:
		url = {'mode': 'build_tmdb_list', 'user': user, 'name': name, 'list_id': list_id, 'new_page': page + 1}
		kodi_utils.add_dir(__handle__, url, nextpage_str)
	kodi_utils.set_category(__handle__, name)
	kodi_utils.set_content(__handle__, content)
	kodi_utils.end_directory(__handle__, False if is_widget else None)
	kodi_utils.set_view_mode('view.%s' % content, content)

