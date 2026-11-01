import json
from jurialmunkey.ftools import cached_property
from jurialmunkey.parser import try_int
from tmdbhelper.lib.addon.plugin import get_localized
from tmdbhelper.lib.items.directories.mapper_basic import ItemMapper
from tmdbhelper.lib.sync.providers.monitor_lists import MonitorListsSupplier, is_provider_user_slug
from tmdbhelper.lib.addon.consts import TRAKT_MAX_ITEMS_PER_PAGE


class TraktMonitorListMapper(ItemMapper):
    @cached_property
    def label(self):
        return self.meta['name']

    def get_params(self):
        return {'user_slug': '__api_trakt__', 'list_slug': self.meta['reference']}


class TraktMonitorLists(MonitorListsSupplier):
    item_mapper_class = TraktMonitorListMapper

    @staticmethod
    def get_reference(user_slug, list_slug):
        return json.dumps([user_slug, list_slug], separators=(',', ':'))

    def get_legacy_list_slug(self, user_slug, list_slug):
        if user_slug and list_slug and not is_provider_user_slug(user_slug):
            return self.get_reference(user_slug, list_slug)

    def get_entries(self, route):
        entries = []
        page = 1
        while True:
            response = self.provider.api.get_response(route, page=page, limit=TRAKT_MAX_ITEMS_PER_PAGE)
            if response is None or response.status_code != 200:
                return []
            entries.extend(response.json())
            if page >= try_int(response.headers.get('x-pagination-page-count'), fallback=1):
                return entries
            page += 1

    def get_mapped_item(self, item, add_infoproperties=None):
        return self.item_mapper_class(item, add_infoproperties).item

    def get_watchlists(self):
        return [self.get_mapped_item({
            'name': f'{get_localized(32193)} {get_localized(label)}',
            'reference': self.get_reference('me', f'watchlist/{item_type}'),
        }) for item_type, label in (('movies', 20342), ('shows', 20343))]

    def get_mapped_list(self, item):
        return self.get_mapped_item({
            'name': item['name'],
            'reference': self.get_reference(item['user']['ids']['slug'], item['ids']['slug']),
        })

    def get_lists(self):
        if not self.provider.is_authorized():
            return []
        owned = self.get_entries('users/me/lists')
        liked = [item['list'] for item in self.get_entries('users/likes/lists')]
        return self.get_watchlists() + [self.get_mapped_list(item) for item in owned + liked]

    def get_list_items(self, list_slug):
        if not self.provider.is_authorized():
            return
        user_slug, slug = json.loads(list_slug)
        route = (f'users/{user_slug}/{slug}' if slug.startswith('watchlist/') else
                 f'users/{user_slug}/lists/{slug}/items')
        return self.get_entries(route)
