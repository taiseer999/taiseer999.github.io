from jurialmunkey.parser import boolean, try_int
from tmdbhelper_sync_trakt.directories.mapper_calendar import FactoryCalendarMovieItemMapper
from tmdbhelper.lib.addon.plugin import get_localized
from tmdbhelper.lib.items.directories.lists_trakt import ListTraktFiltered
from tmdbhelper.lib.items.directories.lists_calendar import (
    ListCalendar, ListCalendarProperties,
)


class ListTraktMyAiring(ListTraktFiltered):
    """
    For tv/movie type calendars
    """

    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.trakt_authorization = True
        list_properties.request_url = 'calendars/my/{trakt_type}s'
        list_properties.plugin_name = f'{get_localized(32201)} {{plural}} {{localized}}'
        list_properties.localize = 32202
        list_properties.sub_type = True
        return list_properties


class ListTraktCalendarProperties(ListCalendarProperties):
    pass


class ListTraktCalendar(ListCalendar):
    list_properties_class = ListTraktCalendarProperties


class ListTraktCalendarMovieProperties(ListCalendarProperties):
    def get_mapped_item(self, item, add_infoproperties=None):
        item_mapper = FactoryCalendarMovieItemMapper(item, add_infoproperties)
        if not self.get_mapped_item_air_date_is_in_range(item_mapper):
            return
        return item_mapper.item


class ListTraktMoviesCalendar(ListTraktFiltered):

    list_properties_class = ListTraktCalendarMovieProperties

    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.trakt_authorization = True
        list_properties.request_url = 'calendars/{trakt_user}/movies/{start_date}/{total_days}'
        list_properties.container_content = 'movies'
        list_properties.trakt_type = 'movie'
        return list_properties

    def get_items(self, *args, startdate, days, user=True, tmdb_type='movie', **kwargs):
        self.list_properties.trakt_user = 'my' if boolean(user) else 'all'
        self.list_properties.trakt_date = try_int(startdate)
        self.list_properties.trakt_days = try_int(days)
        return super().get_items(*args, tmdb_type=tmdb_type, **kwargs)


class ListTraktDVDsCalendar(ListTraktMoviesCalendar):
    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.request_url = 'calendars/{trakt_user}/dvd/{start_date}/{total_days}'
        return list_properties
