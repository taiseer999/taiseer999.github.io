from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.addon.plugin import executebuiltin, get_localized
from tmdbhelper.lib.items.directories.base.lists_base import BaseDirList
from tmdbhelper.lib.items.directories.base.basedir_calendar import get_all_calendar_class_instances
from tmdbhelper.lib.items.directories.lists_default import ListDefault, ListProperties
from tmdbhelper_sync_trakt.directories.basedir_trakt import get_all_trakt_class_instances
from tmdbhelper_sync_trakt.directories.basedir_random import get_all_random_class_instances
from tmdbhelper_sync_trakt.directories.basedir_trakt_genre import get_all_trakt_genre_class_instances
from tmdbhelper_sync_trakt.directories.mapper_directory import TraktDirectoryItemMapper


class TraktBaseDirList(BaseDirList):
    def __init__(self, items):
        self.items = items

    @property
    def basedir(self):
        return self.items


class TraktDirectoryProperties(ListProperties):
    plugin_name = 'Trakt'
    container_content = ''
    directory_route = 'trakt_directory'
    item_mapper_class = TraktDirectoryItemMapper
    grouped = True
    group = None
    tmdb_type = None

    def get_menu_items(self):
        return get_all_trakt_class_instances() + get_all_random_class_instances()

    @cached_property
    def entries(self):
        return self.get_entries()

    def get_entries(self):
        entries = TraktBaseDirList(self.get_menu_items()).get_basedir(self.tmdb_type)
        if self.group:
            return [{'entry': entry, 'count': 1} for entry in entries if entry.item.group == int(self.group)]
        if not self.grouped:
            return [{'entry': entry, 'count': 1} for entry in entries]
        groups = {}
        for entry in entries:
            group = groups.setdefault(entry.item.group, {'entry': entry, 'count': 0})
            group['count'] += 1
        return list(groups.values())

    @cached_property
    def type_art(self):
        return len({item['entry'].type for item in self.entries}) > 1

    @cached_property
    def items(self):
        return self.get_items()

    def get_items(self):
        return [self.get_mapped_item(entry) for entry in self.entries]

    def get_mapped_item(self, item, add_infoproperties=None):
        mapper = self.item_mapper_class(item, add_infoproperties)
        mapper.type_art = self.type_art
        mapper.directory_route = self.directory_route
        return mapper.item


class TraktRandomDirectoryProperties(TraktDirectoryProperties):
    grouped = False

    def get_menu_items(self):
        return get_all_random_class_instances()


class TraktGenreDirectoryProperties(TraktDirectoryProperties):
    grouped = False

    def get_menu_items(self):
        return get_all_trakt_genre_class_instances(self.genre)


class TraktCalendarDirectoryProperties(TraktDirectoryProperties):
    grouped = False

    def get_menu_items(self):
        return get_all_calendar_class_instances(**self.calendar_params)


class ListTraktDirectory(ListDefault):
    list_properties_class = TraktDirectoryProperties
    kodi_details = False

    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.plugin_name = 'Trakt'
        list_properties.pagination = False
        return list_properties

    def get_items(self, group=None, tmdb_type=None, **kwargs):
        self.list_properties.group = group
        self.list_properties.tmdb_type = tmdb_type if tmdb_type not in ('both', 'None') else None
        return self.get_items_finalised()


class ListTraktRandomDirectory(ListTraktDirectory):
    list_properties_class = TraktRandomDirectoryProperties

    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.plugin_name = f'Trakt {get_localized(590)}'
        return list_properties


class ListTraktGenreDirectory(ListTraktDirectory):
    list_properties_class = TraktGenreDirectoryProperties

    def get_items(self, genre, **kwargs):
        self.list_properties.genre = genre
        return super().get_items(**kwargs)


class ListTraktCalendarDirectory(ListTraktDirectory):
    list_properties_class = TraktCalendarDirectoryProperties
    calendar_info = 'trakt_calendar'
    calendar_type = 'tv'

    def get_items(self, endpoint=None, user=None, **kwargs):
        self.list_properties.calendar_params = {
            key: value for key, value in (
                ('info', self.calendar_info), ('endpoint', endpoint), ('user', user)) if value is not None
        }
        kwargs['tmdb_type'] = self.calendar_type
        return super().get_items(**kwargs)


class ListTraktMovieCalendarDirectory(ListTraktCalendarDirectory):
    calendar_info = 'trakt_moviecalendar'
    calendar_type = 'movie'


class ListTraktDVDCalendarDirectory(ListTraktMovieCalendarDirectory):
    calendar_info = 'trakt_dvdcalendar'


class ListTraktAuthenticate(ListTraktDirectory):
    def get_items(self, **kwargs):
        executebuiltin('RunScript(plugin.video.themoviedb.helper,authenticate_trakt)')
        return []
