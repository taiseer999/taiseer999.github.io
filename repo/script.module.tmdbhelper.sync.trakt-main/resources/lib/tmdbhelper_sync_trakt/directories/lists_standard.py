from tmdbhelper.lib.items.directories.lists_trakt import (
    ListTraktStandard, ListTraktStandardProperties,
)


class ListTraktBoxOffice(ListTraktStandard):  # Box Office doesn't support filters or pagination
    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.request_url = '{trakt_type}s/boxoffice'
        list_properties.localize = 32207
        list_properties.sub_type = True
        return list_properties


class ListTraktRecommendations(ListTraktStandard):  # Box Office doesn't support filters or pagination
    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.trakt_authorization = True
        list_properties.trakt_filters = {
            'ignore_collected': 'true',
            'ignore_watchlisted': 'true'
        }
        list_properties.request_url = 'recommendations/{trakt_type}s'
        list_properties.localize = 32198
        list_properties.sub_type = True
        return list_properties
