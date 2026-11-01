from tmdbhelper.lib.sync.providers.imdb_top250 import IMDbTop250Supplier


class TraktIMDbTop250MoviesSupplier(IMDbTop250Supplier):
    url = 'users/justin/lists/imdb-top-rated-movies/items'
    item_type = 'movie'

    def get_items(self):
        data = self.provider.api.get_response_json(self.url, limit=4095)
        return [self.get_mapped_item(item) for item in data] if data else []

    def get_mapped_item(self, item):
        meta = item[self.item_type]
        return {
            'rank': item['rank'],
            'tmdb_type': self.tmdb_type,
            'tmdb_id': meta['ids']['tmdb'],
            'title': meta['title'],
            'year': meta['year'],
            'slug': meta['ids']['slug'],
        }


class TraktIMDbTop250TVShowsSupplier(TraktIMDbTop250MoviesSupplier):
    url = 'users/justin/lists/imdb-top-rated-tv-shows/items'
    item_type = 'show'
