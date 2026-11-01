from tmdbhelper_sync_trakt.directories.item import TraktDirItem as BaseDirItem
from tmdbhelper.lib.addon.plugin import get_localized
from jurialmunkey.ftools import cached_property


class BaseDirItemRandomTrending(BaseDirItem):
    priority = 170
    label_prefix = 32204
    label_append = 590
    params = {'info': 'trakt_random_trending'}
    types = ('movie', 'tv', 'both', )
    art_icon = 'resources/icons/trakt/trend.png'
    group = 32204

    @cached_property
    def label(self):
        return '{label_append} {label_prefix}{{space}}{{item_type}}'.format(
            label_prefix=get_localized(self.label_prefix),
            label_append=get_localized(self.label_append)
        )


class BaseDirItemRandomPopular(BaseDirItemRandomTrending):
    priority = 180
    label_prefix = 32175
    params = {'info': 'trakt_random_popular'}
    art_icon = 'resources/icons/trakt/popular.png'
    group = 32175


class BaseDirItemRandomMostPlayed(BaseDirItemRandomTrending):
    priority = 190
    label_prefix = 32205
    params = {'info': 'trakt_random_mostplayed'}
    art_icon = 'resources/icons/trakt/mostplayed.png'
    group = 32414


class BaseDirItemRandomMostViewers(BaseDirItemRandomTrending):
    priority = 200
    label_prefix = 32414
    params = {'info': 'trakt_random_mostviewers'}
    art_icon = 'resources/icons/trakt/viewers.png'
    group = 32414


class BaseDirItemRandomAnticipated(BaseDirItemRandomTrending):
    priority = 210
    label_prefix = 32206
    params = {'info': 'trakt_random_anticipated'}
    art_icon = 'resources/icons/trakt/anticipated.png'
    group = 32206


class BaseDirItemRandomTrendingLists(BaseDirItemRandomTrending):
    priority = 220
    label_prefix = 32300
    params = {'info': 'trakt_random_trendinglists'}
    art_icon = 'resources/icons/trakt/trendinglist.png'
    types = ('both', )
    group = 32159


class BaseDirItemRandomPopularLists(BaseDirItemRandomTrending):
    priority = 230
    label_prefix = 32301
    params = {'info': 'trakt_random_popularlists'}
    art_icon = 'resources/icons/trakt/popularlist.png'
    types = ('both', )
    group = 32159


class BaseDirItemRandomLikedLists(BaseDirItemRandomTrending):
    priority = 240
    label_prefix = 32302
    params = {'info': 'trakt_random_likedlists'}
    art_icon = 'resources/icons/trakt/likedlist.png'
    types = ('both', )
    group = 32159


class BaseDirItemRandomMyLists(BaseDirItemRandomTrending):
    priority = 250
    label_prefix = 32303
    params = {'info': 'trakt_random_mylists'}
    art_icon = 'resources/icons/trakt/mylists.png'
    types = ('both', )
    group = 32159


def get_all_random_class_instances():
    from tmdbhelper.lib.addon.module import get_all_module_class_objects_by_priority
    return [clobj() for clobj in get_all_module_class_objects_by_priority(__name__)]
