# -*- coding: utf-8 -*-

from providerModules.a4kScrapers import core

class sources(core.DefaultSources):
    def __init__(self, *args, **kwargs):
        super(sources, self).__init__(__name__, *args, single_query=False, **kwargs)
        self._filter = core.Filter(fn=self._filter_fn, type='single')
        self._seen_hashes = set()

    def _filter_fn(self, title, clean_title):
        if self.is_movie_query():
            return False

        if self.scraper.filter_single_episode.fn(title, clean_title):
            self._filter.type = self.scraper.filter_single_episode.type
            return True

        if self.scraper.filter_show_pack.fn(title, clean_title):
            self._filter.type = self.scraper.filter_show_pack.type
            return True

        if self.scraper.filter_season_pack.fn(title, clean_title):
            self._filter.type = self.scraper.filter_season_pack.type
            return True

        return False

    def _get_scraper(self, title):
        return super(sources, self)._get_scraper(title, custom_filter=self._filter)

    def _do_search(self, url, query_text):
        """Execute a single PirateBay API search and return results list."""
        try:
            response = self._request.get(url.base + (url.search % core.quote_plus(query_text)))
            if response.status_code != 200:
                return []
            results = core.json.loads(response.text)
            if len(results) == 0 or results[0].get('id') == '0':
                return []
            return results
        except:
            return []

    def _search_request(self, url, query):
        """Search PirateBay using IMDB ID first, then title text, combined and deduped.

        PirateBay's IMDB index is incomplete -- many torrents lack IMDB tags.
        By doing both searches, we catch torrents that only one method finds.
        """
        all_results = []

        # Pass 1: IMDB search (fast, precise when indexed)
        if self._imdb:
            imdb_results = self._do_search(url, self._imdb)
            for r in imdb_results:
                h = r.get('info_hash', '').lower()
                if h and h not in self._seen_hashes:
                    self._seen_hashes.add(h)
                    all_results.append(r)

        # Pass 2: Title text search (catches non-IMDB-tagged torrents)
        if query:
            title_results = self._do_search(url, query)
            for r in title_results:
                h = r.get('info_hash', '').lower()
                if h and h not in self._seen_hashes:
                    self._seen_hashes.add(h)
                    all_results.append(r)

        return all_results

    def _soup_filter(self, response):
        return response

    def _title_filter(self, el):
        return el['name']

    def _info(self, el, url, torrent):
        torrent['hash'] = el['info_hash']
        torrent['size'] = int(el['size']) / 1024 / 1024
        torrent['seeds'] = el['seeders']

        return torrent

    def movie(self, title, year, imdb=None, **kwargs):
        self._imdb = imdb
        self._seen_hashes = set()
        return super(sources, self).movie(title, year, imdb)

    def episode(self, simple_info, all_info, **kwargs):
        self._imdb = all_info.get('info', {}).get('tvshow.imdb_id', None)
        if self._imdb is None:
            self._imdb = all_info.get('info', {}).get('imdb_id', None)
        if self._imdb is None:
            self._imdb = all_info.get('showInfo', {}).get('ids', {}).get('imdb', None)
        self._seen_hashes = set()
        return super(sources, self).episode(simple_info, all_info)
