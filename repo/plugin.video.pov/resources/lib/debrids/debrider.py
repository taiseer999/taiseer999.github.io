import sys
from debrids.debrider_api import DebriderAPI as Debrid
from modules import kodi_utils
from modules.source_utils import supported_video_extensions
from modules.utils import clean_file_name, normalize
# from modules.kodi_utils import logger

get_setting, set_setting = kodi_utils.get_setting, kodi_utils.set_setting
ls, build_url, make_listitem = kodi_utils.local_string, kodi_utils.build_url, kodi_utils.make_listitem
folder_str, file_str, delete_str, down_str = ls(32742).upper(), ls(32743).upper(), ls(32785), ls(32747)
fanart = kodi_utils.get_addoninfo('fanart')
default_icon = kodi_utils.media_path(Debrid.icon)
default_art = {'icon': default_icon, 'poster': default_icon, 'thumb': default_icon, 'fanart': fanart, 'banner': default_icon}
extensions = supported_video_extensions()

class Indexer(Debrid):
	def run(self, params):
		if   '_delete' in params['mode']:
			return self.cloud_delete(params['folder_id'])
		elif '_browse_cloud' in params['mode']:
			items = self.user_cloud(params['folder_id'])['files']
			_builder = self.browse_cloud
		elif '_torrent_cloud' in params['mode']:
			items = self.user_cloud()
			_builder = self.torrent_cloud
		else: return getattr(self, params['mode'].split('.')[-1])()
		__handle__ = int(sys.argv[1])
		kodi_utils.add_items(__handle__, list(_builder(items)))
		kodi_utils.set_content(__handle__, 'files')
		kodi_utils.end_directory(__handle__)
		kodi_utils.set_view_mode('view.premium')

	def torrent_cloud(self, items):
		for count, item in enumerate(items, 1):
			try:
				if not item['status'] == 'completed' and not item['type'] == 'torrent': continue
				cm = []
				cm_append = cm.append
				request_id, folder_name = item['id'], item['name']
				delete_params = {'mode': 'debrider.db_delete', 'folder_id': request_id}
				display = '%02d | [B]%s[/B] | [I]%s [/I]' % (count, folder_str, clean_file_name(normalize(folder_name)).upper())
				url_params = {'mode': 'debrider.db_browse_cloud', 'folder_id': request_id}
				cm_append(('[B]%s %s[/B]' % (delete_str, folder_str.capitalize()), 'RunPlugin(%s)' % build_url(delete_params)))
				url = build_url(url_params)
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt(default_art)
				yield (url, listitem, True)
			except: pass

	def browse_cloud(self, items):
		for count, item in enumerate(items, 1):
			try:
				if not item['name'].lower().endswith(tuple(extensions)): continue
				cm = []
				cm_append = cm.append
				name = item['name'].split('/')[-1]
				name = clean_file_name(name).upper()
				size = float(int(item['size']))/1073741824
				link = item['download_link']
				display = '%02d | [B]%s[/B] | %.2f GB | [I]%s [/I]' % (count, file_str, size, name)
				url_params = {'mode': 'media_play', 'url': link, 'media_type': 'video'}
				down_file_params = {'mode': 'downloader', 'action': 'cloud.debrider_direct', 'name': name, 'url': link, 'image': default_icon}
				cm_append((down_str,'RunPlugin(%s)' % build_url(down_file_params)))
				url = build_url(url_params)
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt(default_art)
				listitem.setInfo('video', {})
				yield (url, listitem, False)
			except: pass

	def cloud_delete(self, folder_id):
		if not kodi_utils.confirm_dialog(): return
		result = self.delete_torrent(folder_id)
		if 'success' not in result: return kodi_utils.notification(32574)
		self.clear_cache()
		kodi_utils.container_refresh()

	def show_account_info(self):
		try:
			kodi_utils.show_busy_dialog()
			account_info = self.account_info()
			plan, desc = account_info['subscription']['plan']['name'], account_info['subscription']['plan']['description']
			body = []
			append = body.append
			append(ls(32758) % account_info['id'])
			append(ls(32755) % account_info['email'])
			append('[B]Plan:[/B] %s (%s)' % (desc, plan))
			append(ls(32757) % account_info['subscription']['status'].capitalize())
			kodi_utils.hide_busy_dialog()
			return kodi_utils.show_text('Debrider'.upper(), '\n\n'.join(body), font_size='large')
		except: kodi_utils.hide_busy_dialog()

