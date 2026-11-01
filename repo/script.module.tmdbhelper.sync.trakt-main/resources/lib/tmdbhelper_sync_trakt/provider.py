from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.sync.providers.base import SyncProvider
from tmdbhelper_sync_trakt.sync import synctype, datasync
from tmdbhelper_sync_trakt.actions import basic
from tmdbhelper_sync_trakt.actions.progress import ItemProgress
from tmdbhelper_sync_trakt.scrobbler import ProviderScrobbler
from tmdbhelper_sync_trakt.sync.service_types import SyncRatings, SyncFavorites
from tmdbhelper_sync_trakt.actions.rating import ItemRating
from tmdbhelper_sync_trakt.actions.favorites import ItemFavorites
from tmdbhelper_sync_trakt.directories.item import TraktDirectoryItem
from tmdbhelper_sync_trakt.directories.routes import LIST_ROUTES
from tmdbhelper_sync_trakt.monitor_lists import TraktMonitorLists
from tmdbhelper_sync_trakt.stats import TraktStatsSupplier
from tmdbhelper_sync_trakt.ratings import (
    TraktRatingsSupplier, TraktSeasonRatingsSupplier, TraktEpisodeRatingsSupplier,
)
from tmdbhelper_sync_trakt.imdb_top250 import (
    TraktIMDbTop250MoviesSupplier, TraktIMDbTop250TVShowsSupplier,
)


class Provider(SyncProvider):
    interface_version = 3
    provider_id = 'trakt'
    display_name = 'Trakt'
    sync_classes = {
        'SyncWatched': synctype.SyncWatched,
        'SyncPlayback': synctype.SyncPlayback,
        'SyncNextEpisodes': synctype.SyncNextEpisodes,
        'SyncAllNextEpisodes': synctype.SyncAllNextEpisodes,
        'SyncWatchlist': synctype.SyncWatchlist,
        'SyncCollection': synctype.SyncCollection,
        'SyncHiddenDropped': synctype.SyncHiddenDropped,
        'SyncHiddenCalendar': synctype.SyncHiddenCalendar,
        'SyncHiddenProgressWatched': synctype.SyncHiddenProgressWatched,
        'SyncHiddenProgressCollected': synctype.SyncHiddenProgressCollected,
        'SyncAiredEpisodes': synctype.SyncWatched,
    }
    action_classes = {
        'watched': basic.ItemWatched,
        'unwatched': basic.ItemUnwatched,
        'watchlist': basic.ItemWatchlist,
        'collection': basic.ItemCollection,
        'dropped': basic.ItemDropped,
        'progress': ItemProgress,
    }
    getter_classes = {
        'movies_to_watch': datasync.TraktSyncDataGetterAllUnHiddenMoviesToWatch,
        'shows_to_watch': datasync.TraktSyncDataGetterAllUnHiddenShowsToWatch,
        'shows_in_progress': datasync.TraktSyncDataGetterAllUnHiddenShowsInProgress,
    }
    service_sync_classes = {'SyncRatings': SyncRatings, 'SyncFavorites': SyncFavorites}
    service_action_classes = {'traktrating': ItemRating, 'traktfavorites': ItemFavorites}
    ratings_classes = {
        'movie': TraktRatingsSupplier,
        'tvshow': TraktRatingsSupplier,
        'season': TraktSeasonRatingsSupplier,
        'episode': TraktEpisodeRatingsSupplier,
    }
    directory_item_class = TraktDirectoryItem
    imdb_top250_classes = {
        'movie': TraktIMDbTop250MoviesSupplier,
        'tvshow': TraktIMDbTop250TVShowsSupplier,
    }
    list_routes = LIST_ROUTES
    monitor_lists_class = TraktMonitorLists
    stats_class = TraktStatsSupplier
    scrobbler_class = ProviderScrobbler

    @cached_property
    def api(self):
        return self.get_api()

    def get_api(self):
        from tmdbhelper.lib.api.trakt.api import TraktAPI
        return TraktAPI()

    def is_authorized(self):
        return self.api is not None and self.api.authenticator.is_authorized

    def get_last_activities(self):
        return self.api.get_response_json('sync/last_activities')
