from tmdbhelper.lib.script.actions.trakt.item import ItemAction as BasicItemAction


class ItemAction(BasicItemAction):
    def get_trakt_api(self):
        return self.sync_provider.api
