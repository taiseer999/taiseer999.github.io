from tmdbhelper.lib.items.directories.lists_trakt import ListTraktFiltered


class ListTraktTrending(ListTraktFiltered):
    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.request_url = '{trakt_type}s/trending'
        list_properties.localize = 32204
        list_properties.sub_type = True
        return list_properties


class ListTraktPopular(ListTraktFiltered):
    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.request_url = '{trakt_type}s/popular'
        list_properties.localize = 32175
        list_properties.sub_type = False
        return list_properties


class ListTraktMostPlayed(ListTraktFiltered):
    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.request_url = '{trakt_type}s/played/weekly'
        list_properties.localize = 32205
        list_properties.sub_type = True
        return list_properties


class ListTraktMostWatched(ListTraktFiltered):
    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.request_url = '{trakt_type}s/watched/weekly'
        list_properties.localize = 32414
        list_properties.sub_type = True
        return list_properties


class ListTraktAnticipated(ListTraktFiltered):
    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.request_url = '{trakt_type}s/anticipated'
        list_properties.localize = 32206
        list_properties.sub_type = True
        return list_properties
