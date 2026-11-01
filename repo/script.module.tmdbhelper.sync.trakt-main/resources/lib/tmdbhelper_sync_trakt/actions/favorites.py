from jurialmunkey.ftools import cached_property
from tmdbhelper_sync_trakt.actions.item import ItemSync
from tmdbhelper.lib.sync.datasync import SyncDataFactory


class ItemFavorites(ItemSync):
    sync_types = ('SyncFavorites',)
    localized_name_add = 32490
    localized_name_rem = 32491
    sync_key = 'favorites_listed_at'
    sync_url = 'favorites'

    @cached_property
    def syncdata(self):
        return self.get_syncdata()

    def get_syncdata(self):
        return SyncDataFactory()

    def get_sync_value(self):
        return self.syncdata.get_value(self.tmdb_type, self.tmdb_id, key=self.sync_key)
