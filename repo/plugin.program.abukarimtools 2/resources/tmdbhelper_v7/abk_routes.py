# -- TMDbHelper 6.20 skin routes v1 (by ABUKARIM TOOLS) --
# The multiservice TMDb Helper 7.x has no sync_watchedon / mdblist_officiallist
# routes; Arctic Fuse 3 (built against jurialmunkey's 6.20) calls both, and every
# call raised "info=... is not valid route". These two containers give the same
# lists from what 7.x already has: the local Trakt sync data and the MDBList API.
# Injected by plugin.program.abukarimtools; routes.py registers them.
import re
from calendar import monthrange
from datetime import date, timedelta
from urllib.parse import quote
from tmdbhelper.lib.items.container import ContainerDirectory
from tmdbhelper.lib.addon.plugin import convert_type
from tmdbhelper.lib.addon.logger import kodi_log

_MONTHS = ('january', 'february', 'march', 'april', 'may', 'june', 'july',
           'august', 'september', 'october', 'november', 'december')


def _is_relative(value):
    return value is not None and bool(re.fullmatch(r'-?[0-9]+', str(value))) and int(value) <= 0


def watched_on_parts(day=None, month=None, year=None, today=None):
    """(year, month, day) as ints or None, same reading as 6.20's WatchedOnDateParts:
    0 / negative numbers count back from today (month=-1 = last month), month names allowed.
    Weekday names (6.20's day=monday) are not supported here: the day is then ignored."""
    today = today or date.today()
    y = m = d = None
    if year is not None:
        y = today.year + int(year) if _is_relative(year) else int(year)
    if month is not None:
        if _is_relative(month):
            index = (y if y is not None else today.year) * 12 + today.month - 1 + int(month)
            y, m = divmod(index, 12)
            m += 1
        elif str(month).isdigit():
            m = int(month)
        else:
            name = str(month).lower()
            m = next((i for i, n in enumerate(_MONTHS, 1) if name in (n, n[:3])), None)
    if day is not None:
        if _is_relative(day):
            ry, rm = (y or today.year), (m or today.month)
            ref = date(ry, rm, min(today.day, monthrange(ry, rm)[1]))
            when = ref + timedelta(days=int(day))
            y, m, d = when.year, when.month, when.day
        elif str(day).isdigit():
            d = int(day)
    return y, m, d


def watched_on_match(stamp, parts):
    """stamp: Trakt ISO time '2026-11-02T17:57:40.000Z' (UTC, as Trakt stores it)."""
    if not stamp or len(stamp) < 10:
        return False
    for value, (a, b) in zip(parts, ((0, 4), (5, 7), (8, 10))):
        if value is not None and stamp[a:b] != ('%04d' % value if a == 0 else '%02d' % value):
            return False
    return True


class ListWatchedOn(ContainerDirectory):
    """info=sync_watchedon&type=both|movie|tv&month=0&year=2026 - Trakt items whose last watch falls on
    that year / month / day, newest first. Read from the local Trakt sync data (no extra request)."""

    def get_items(self, tmdb_type=None, day=None, month=None, year=None, page=None, limit=None, **kwargs):
        from tmdbhelper.lib.api.trakt.sync.itemlist import ItemListSyncDataFactory
        from tmdbhelper.lib.items.itemlist import ItemListPagination

        tmdb_type = tmdb_type or kwargs.get('type') or 'both'
        if day is None and month is None and year is None:
            return
        try:
            parts = watched_on_parts(day=day, month=month, year=year)
        except (ValueError, TypeError) as error:
            kodi_log(f'ABK sync_watchedon: bad date day={day} month={month} year={year}: {error}', 1)
            return
        item_type = 'both' if tmdb_type == 'both' else convert_type(tmdb_type, 'trakt')
        # No sort_by: the watched getter already returns newest first (its clause key is
        # last_watched_at), and a sort would add last_watched_at to the SELECT a second time.
        sync_list = ItemListSyncDataFactory(
            'watched', self.trakt_api, item_type=item_type, item_keys=('last_watched_at', ))
        items = [
            i for i in (sync_list.items or [])
            if watched_on_match((i.get('infoproperties') or {}).get('last_watched_at'), parts)]
        if not items:
            return
        for i in items:  # last_watched_at was only asked for to filter - keep the listitems as 6.20 had them
            (i.get('infoproperties') or {}).pop('last_watched_at', None)
            if not i.get('infoproperties'):
                i.pop('infoproperties', None)

        key = 'all' if item_type == 'both' else item_type
        response = ItemListPagination(
            {key: items}, page=try_page(page), limit=limit or self.trakt_api.sync_item_limit)
        self.tmdb_cache_only = False
        self.library = 'video'
        if item_type == 'both':
            self.kodi_db = self.get_kodi_database('both')
            self.container_content = 'movies'
        else:
            self.kodi_db = self.get_kodi_database(tmdb_type)
            self.container_content = convert_type(tmdb_type, 'container', items=items)
        return response.items + response.next_page


class ListMDbListOfficial(ContainerDirectory):
    """info=mdblist_officiallist&list_id=most-watched-week&tmdb_type=tv - an MDBList official list
    (GET /lists/official/{list_id}/items, the endpoint 6.20 uses)."""

    def get_items(self, list_id=None, tmdb_type=None, page=None, **kwargs):
        if not list_id or not self.mdblist_api:
            return
        path = f"lists/official/{quote(str(list_id), safe='')}/items"
        mediatype = convert_type(tmdb_type, 'trakt') if tmdb_type in ('movie', 'tv') else None
        if mediatype:
            path = f'{path}?mediatype={mediatype}'
        page = try_page(page)
        response = self.mdblist_api.get_request_sc(path, cache_refresh=True if page == 1 else False)
        if not response:
            return
        response = self.mdblist_api.get_paginated(response, page=page)
        self.tmdb_cache_only = False
        self.set_mixed_content(response.paginated_items_dict)
        return response.items + response.next_page


def try_page(page):
    try:
        return max(int(page or 1), 1)
    except (TypeError, ValueError):
        return 1
