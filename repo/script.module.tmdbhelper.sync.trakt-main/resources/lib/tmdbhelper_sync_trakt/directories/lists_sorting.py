from tmdbhelper.lib.addon.plugin import get_localized
from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.items.directories.lists_default import ListDefault, ListProperties
from tmdbhelper.lib.items.directories.mapper_basic import ItemMapper


class TraktPersonalSortMethods:
    @staticmethod
    def get_sort_methods(info=None):
        return [
            {
                'name': f'{get_localized(32287)}: {get_localized(571)}',
                'params': {},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(32451)} {get_localized(32286)}',
                'params': {'sort_by': 'rank', 'sort_how': 'asc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(32452)} {get_localized(32286)}',
                'params': {'sort_by': 'rank', 'sort_how': 'desc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(32063)} {get_localized(584)}',
                'params': {'sort_by': 'added', 'sort_how': 'asc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(32063)} {get_localized(585)}',
                'params': {'sort_by': 'added', 'sort_how': 'desc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(32473)} {get_localized(584)}',
                'params': {'sort_by': 'collected', 'sort_how': 'asc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(32473)} {get_localized(585)}',
                'params': {'sort_by': 'collected', 'sort_how': 'desc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(369)} (A-Z)',
                'params': {'sort_by': 'title', 'sort_how': 'asc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(369)} (Z-A)',
                'params': {'sort_by': 'title', 'sort_how': 'desc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(563)} {get_localized(584)}',
                'params': {'sort_by': 'percentage', 'sort_how': 'asc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(563)} {get_localized(585)}',
                'params': {'sort_by': 'percentage', 'sort_how': 'desc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(32242)} {get_localized(584)}',
                'params': {'sort_by': 'released', 'sort_how': 'asc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(32242)} {get_localized(585)}',
                'params': {'sort_by': 'released', 'sort_how': 'desc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(2050)} {get_localized(584)}',
                'params': {'sort_by': 'runtime', 'sort_how': 'asc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(2050)} {get_localized(585)}',
                'params': {'sort_by': 'runtime', 'sort_how': 'desc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(205)} {get_localized(584)}',
                'params': {'sort_by': 'votes', 'sort_how': 'asc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(205)} {get_localized(585)}',
                'params': {'sort_by': 'votes', 'sort_how': 'desc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(32175)} {get_localized(584)}',
                'params': {'sort_by': 'popularity', 'sort_how': 'asc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(32175)} {get_localized(585)}',
                'params': {'sort_by': 'popularity', 'sort_how': 'desc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(16102)} {get_localized(584)}',
                'params': {'sort_by': 'watched', 'sort_how': 'asc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(16102)} {get_localized(585)}',
                'params': {'sort_by': 'watched', 'sort_how': 'desc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(590)}',
                'params': {'sort_by': 'random'},
            }]


class TraktDefaultSortMethods:
    @staticmethod
    def get_sort_methods(info=None):
        return [
            {
                'name': f'{get_localized(32287)}: {get_localized(571)}',
                'params': {},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(369)} (A-Z)',
                'params': {'sort_by': 'title', 'sort_how': 'asc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(369)} (Z-A)',
                'params': {'sort_by': 'title', 'sort_how': 'desc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(345)} {get_localized(584)}',
                'params': {'sort_by': 'year', 'sort_how': 'asc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(345)} {get_localized(585)}',
                'params': {'sort_by': 'year', 'sort_how': 'desc'},
            },
            {
                'name': f'{get_localized(32287)}: {get_localized(590)}',
                'params': {'sort_by': 'random'},
            }]


class TraktSortMethods:
    @staticmethod
    def get_sort_methods(info=None):
        methods = TraktPersonalSortMethods if info == 'trakt_userlist' else TraktDefaultSortMethods
        return methods.get_sort_methods(info)


class TraktSortItemMapper(ItemMapper):
    parent_params = {}

    @cached_property
    def label(self):
        return f'{self.parent_params.get("list_name")} - {self.meta["name"]}'

    def get_params(self):
        return {**self.parent_params, **self.meta['params']}


class TraktSortProperties(ListProperties):
    container_content = ''
    item_mapper_class = TraktSortItemMapper

    @cached_property
    def items(self):
        return self.get_items()

    def get_items(self):
        return [self.get_mapped_item(item) for item in TraktSortMethods.get_sort_methods(self.parent_params['info'])]

    def get_mapped_item(self, item, add_infoproperties=None):
        mapper = self.item_mapper_class(item, add_infoproperties)
        mapper.parent_params = self.parent_params
        return mapper.item


class ListTraktSortBy(ListDefault, TraktSortMethods):
    list_properties_class = TraktSortProperties
    kodi_db = None

    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.pagination = False
        return list_properties

    def get_items(self, parent_info=None, **kwargs):
        kwargs.pop('info', None)
        self.list_properties.parent_params = dict(kwargs, info=parent_info)
        return self.get_items_finalised()
