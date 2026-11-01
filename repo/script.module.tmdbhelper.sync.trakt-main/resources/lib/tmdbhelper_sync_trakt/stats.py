from tmdbhelper.lib.sync.providers.stats import StatsSupplier


class TraktStatsSupplier(StatsSupplier):
    url = 'users/me/stats'

    def get_items(self):
        from json import JSONDecodeError
        response = self.provider.api.get_response(self.url)
        if response is None or not response.ok:
            return
        try:
            data = response.json()
        except JSONDecodeError:
            return
        return self.get_mapped_items(data) if data is not None else None

    def get_mapped_items(self, stat, name=None, base=None):
        if isinstance(stat, int):
            return [{'name': name, 'type': base or 'user', 'stat': stat}]
        return [
            item
            for item_name, item_stat in stat.items()
            for item in self.get_mapped_items(
                item_stat, name=item_name, base=name if base is None else f'{base}_{name}')
        ] if isinstance(stat, dict) else []
