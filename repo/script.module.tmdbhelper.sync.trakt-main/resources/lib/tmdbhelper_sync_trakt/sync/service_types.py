from tmdbhelper_sync_trakt.sync.service import TraktServiceDataType
from tmdbhelper_sync_trakt.user_ratings import TraktUserRatings


class SyncRatings(TraktServiceDataType):
    keys = ('rating', 'rated_at')
    last_activities_key = 'rated_at'
    method = 'ratings'

    @classmethod
    def invalidate_cache(cls, provider):
        for item_type in TraktUserRatings.item_types:
            TraktUserRatings(provider.api, item_type).invalidate()


class SyncFavorites(TraktServiceDataType):
    keys = ('rank', 'listed_at', 'notes')
    last_activities_key = 'favorited_at'
    sync_kwgs = {'extended': 'full'}
    method = 'favorites'
    key_prefix = 'favorites'
