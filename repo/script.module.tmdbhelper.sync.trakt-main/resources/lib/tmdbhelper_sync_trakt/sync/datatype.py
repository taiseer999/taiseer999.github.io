from tmdbhelper.lib.addon.consts import TRAKT_MAX_ITEMS_PER_PAGE
from tmdbhelper.lib.addon.thread import ParallelThread
from tmdbhelper.lib.sync.datatype import DataType, DataTypeEpisodesInShows, DataTypeShowsToEpisodes


class TraktDataType(DataType):
    @property
    def trakt_api(self):
        return self.provider.api

    @property
    def sync_args(self):
        return ('sync', self.method, f'{self.item_type}s',)

    def get_syncitem(self, meta):
        from tmdbhelper_sync_trakt.sync.itemdata import TraktSyncItem
        return TraktSyncItem(self.item_type, meta, self.keys, key_prefix=self.key_prefix)

    def get_response_sync_data(self, *args, **kwargs):
        kwargs['limit'] = TRAKT_MAX_ITEMS_PER_PAGE
        path = self.trakt_api.get_request_url(*args, **kwargs)
        data = self.trakt_api.get_api_request(path, headers=self.trakt_api.headers)
        return data

    @staticmethod
    def get_response_json(response):
        if response is None or response.status_code != 200:
            return
        try:
            return response.json()
        except ValueError:
            return

    def get_response_sync(self, *args, **kwargs):
        response = self.get_response_sync_data(*args, **kwargs)
        this_data = self.get_response_json(response)
        if this_data is None:
            return

        try:
            page_count = int(response.headers.get('x-pagination-page-count', 1)) + 1
            page_start = int(response.headers.get('x-pagination-page', 1)) + 1
        except ValueError:
            return

        def get_next_item(x):
            data = self.get_response_json(self.get_response_sync_data(*args, **kwargs, page=x))
            return data if isinstance(data, list) else None

        with ParallelThread(range(page_start, page_count), get_next_item) as pt:
            next_data = pt.queue

        # Cached columns can only be replaced with a complete snapshot.
        if any(i is None for i in next_data):
            return
        for i in next_data:
            this_data.extend(i)

        return this_data


class TraktDataTypeEpisodesInShows(DataTypeEpisodesInShows, TraktDataType):
    pass


class TraktDataTypeShowsToEpisodes(DataTypeShowsToEpisodes, TraktDataType):
    pass
