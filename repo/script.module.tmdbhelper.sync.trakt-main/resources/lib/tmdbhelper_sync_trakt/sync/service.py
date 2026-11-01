from jurialmunkey.parser import try_int
from tmdbhelper.lib.addon.consts import TRAKT_MAX_ITEMS_PER_PAGE
from tmdbhelper.lib.sync.providers.services import ServiceDataType
from tmdbhelper_sync_trakt.sync.datatype import TraktDataType
from tmdbhelper_sync_trakt.sync.service_itemdata import TraktSyncItem


class TraktServiceDataType(TraktDataType, ServiceDataType):
    def get_syncitem(self, meta):
        return TraktSyncItem(self.item_type, meta, self.keys, key_prefix=self.key_prefix)

    def get_response_sync(self, *args, **kwargs):
        items = []
        page = 1
        while True:
            response = self.trakt_api.get_response(*args, page=page, limit=TRAKT_MAX_ITEMS_PER_PAGE, **kwargs)
            if response is None or response.status_code != 200:
                return
            try:
                data = response.json()
            except ValueError:
                return
            items.extend(data)
            if page >= try_int(response.headers.get('x-pagination-page-count'), fallback=1):
                return items
            page += 1
