from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.addon.tmdate import get_datetime_today
from tmdbhelper.lib.items.directories.lists_default import ListDefault, ListProperties
from tmdbhelper.lib.items.directories.mapper_basic import ItemMapper


class YearItemMapper(ItemMapper):
    tmdb_type = None

    @cached_property
    def label(self):
        return str(self.meta)

    def get_params(self):
        return {'info': 'trakt_popular', 'tmdb_type': self.tmdb_type, 'years': str(self.meta)}


class ListTraktYearsProperties(ListProperties):
    container_content = ''
    item_mapper_class = YearItemMapper

    @cached_property
    def items(self):
        return self.get_items()

    def get_items(self):
        return [self.get_mapped_item(year)
                for year in reversed(range(1900, get_datetime_today().year + 1))]

    def get_mapped_item(self, item, add_infoproperties=None):
        mapper = self.item_mapper_class(item, add_infoproperties)
        mapper.tmdb_type = self.tmdb_type
        return mapper.item


class ListTraktYears(ListDefault):
    list_properties_class = ListTraktYearsProperties

    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.localize = 652
        list_properties.pagination = False
        return list_properties
