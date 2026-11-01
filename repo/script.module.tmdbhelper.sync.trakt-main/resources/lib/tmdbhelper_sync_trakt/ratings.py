from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.sync.providers.ratings import RatingsSupplier
from tmdbhelper_sync_trakt.ratings_mapping import map_trakt_ratings


class TraktRatingsSupplier(RatingsSupplier):
    @cached_property
    def ratings_uri(self):
        return self.get_ratings_uri()

    def get_ratings_uri(self):
        item_type = 'movie' if self.tmdb_type == 'movie' else 'show'
        return f'{item_type}s/{self.imdb_id}/ratings'

    def get_ratings(self):
        if not self.provider.is_authorized() or not self.imdb_id:
            return {}
        data = self.provider.api.get_response_json(self.ratings_uri, extended='all')
        return map_trakt_ratings(data) if data else {}


class TraktSeasonRatingsSupplier(TraktRatingsSupplier):
    def get_ratings_uri(self):
        return f'shows/{self.imdb_id}/seasons/{self.season}/ratings'


class TraktEpisodeRatingsSupplier(TraktSeasonRatingsSupplier):
    def get_ratings_uri(self):
        return f'shows/{self.imdb_id}/seasons/{self.season}/episodes/{self.episode}/ratings'
