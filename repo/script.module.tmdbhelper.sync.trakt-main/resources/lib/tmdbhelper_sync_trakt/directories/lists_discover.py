from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.addon.plugin import get_localized, PLUGINPATH
from tmdbhelper.lib.items.directories.lists_default import ListDefault, ListProperties
from tmdbhelper.lib.items.directories.mapper_basic import ItemMapper
from tmdbhelper_sync_trakt.directories.artwork import get_icon


class DiscoverItemMapper(ItemMapper):
    @cached_property
    def label(self):
        return f'{get_localized(35261)}...'

    def get_params(self):
        return {'info': 'trakt_discover'}

    def get_art(self):
        return {'icon': get_icon('resources/icons/trakt/trakt.png')}

    def get_item(self):
        item = super().get_item()
        item['path'] = PLUGINPATH
        return item


class ListDiscoverProperties(ListProperties):
    container_content = ''
    item_mapper_class = DiscoverItemMapper

    @cached_property
    def items(self):
        return self.get_items()

    def get_items(self):
        return [self.get_mapped_item(None)] + self.get_saved_items()

    def get_mapped_item(self, item, add_infoproperties=None):
        return self.item_mapper_class(item, add_infoproperties).item

    def get_saved_items(self):
        from urllib.parse import urlencode
        from tmdbhelper.lib.addon.consts import NODE_BASEDIR
        from tmdbhelper.lib.items.routes import get_container
        from tmdbhelper_sync_trakt.directories.discover import NODE_FILENAME
        params = {'filename': NODE_FILENAME, 'info': 'dir_custom_node', 'basedir': NODE_BASEDIR}
        container = get_container('dir_custom_node')(self.handle, urlencode(params), **params)
        return container.get_directory(items_only=True, build_items=False) or []


class ListDiscoverDir(ListDefault):
    list_properties_class = ListDiscoverProperties
    kodi_details = False

    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.handle = self.handle
        list_properties.plugin_name = f'Trakt {get_localized(32174)}'
        list_properties.pagination = False
        return list_properties

    def get_items(self, **kwargs):
        return self.get_items_finalised()


class ListDiscover(ListDiscoverDir):
    def get_items(self, **kwargs):
        from tmdbhelper_sync_trakt.directories.discover import TraktDiscover
        discover = TraktDiscover()
        discover.load_values(**kwargs)
        discover.doModal()
        return super().get_items(**kwargs)
