from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.items.directories.base.basedir_item import BaseDirItem
from tmdbhelper.lib.items.directories.base.item_builder import BaseDirItemBuilder
from tmdbhelper_sync_trakt.directories.artwork import ADDONPATH, get_icon


class TraktDirItemBuilder(BaseDirItemBuilder):
    def get_art(self):
        art = self.base_item.art.copy()
        art['icon'] = get_icon(self.base_item.art_icon, self.item_type if self.type_art else None)
        return art


class TraktDirItem(BaseDirItem):
    item_builder = TraktDirItemBuilder
    art_icon = 'resources/icons/trakt/trakt.png'

    @cached_property
    def art(self):
        return self.get_art()

    def get_art(self):
        return {'landscape': f'{ADDONPATH}/resources/fanart.jpg', 'icon': get_icon(self.art_icon)}


class TraktDirectoryItem(TraktDirItem):
    priority = 180
    label = 'Trakt'
    params = {'info': 'trakt_directory'}
    types = ('both',)
