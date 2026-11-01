from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.addon.plugin import get_localized
from tmdbhelper.lib.items.directories.mapper_basic import ItemMapper


class TraktDirectoryItemMapper(ItemMapper):
    type_art = False
    directory_route = 'trakt_directory'

    @cached_property
    def builder(self):
        return self.get_builder()

    def get_builder(self):
        entry = self.meta['entry']
        return entry.item.item_builder(
            entry.item, entry.type, mixed_dir=True, type_art=self.type_art and not self.is_group)

    @property
    def is_group(self):
        return self.meta['count'] > 1

    @cached_property
    def label(self):
        return self.get_label()

    def get_label(self):
        return get_localized(self.meta['entry'].item.group) if self.is_group else self.builder.label

    def get_params(self):
        if self.is_group:
            return {'info': self.directory_route, 'group': str(self.meta['entry'].item.group)}
        return self.builder.params

    def get_art(self):
        return self.builder.art

    def get_infoproperties(self):
        return self.builder.infoproperties.copy()

    def get_context_menu(self):
        return [] if self.is_group else self.builder.context_menu
