from xbmcaddon import Addon
from xbmcvfs import translatePath, exists


ADDONPATH = translatePath(Addon('script.module.tmdbhelper.sync.trakt').getAddonInfo('path'))


def get_icon(path, item_type=None):
    icon = f'{ADDONPATH}/{path}'
    variant = f'{icon[:-4]}-{item_type}.png'
    return variant if item_type and exists(variant) else icon
