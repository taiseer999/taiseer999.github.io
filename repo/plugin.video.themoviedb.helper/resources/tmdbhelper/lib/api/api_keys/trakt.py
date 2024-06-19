from tmdbhelper.lib.addon.permissions import __access__
from tmdbhelper.lib.api.api_keys.tokenhandler import TokenHandler

if __access__.has_access('internal'):
    CLIENT_ID = '20fdc5f7364aad2c6d0491652bffc16e2eb7be35b9572478049d54d9824cc4d0'
    CLIENT_SECRET = '3bd196ae0ce16d553d17cf5e3535ba3e65215cf8b5975a8dd9f2969ff0cd4592'
    USER_TOKEN = TokenHandler('trakt_token', store_as='setting')

elif __access__.has_access('trakt'):
    CLIENT_ID = ''
    CLIENT_SECRET = ''
    USER_TOKEN = TokenHandler('trakt_token', store_as='setting')

else:
    CLIENT_ID = ''
    CLIENT_SECRET = ''
    USER_TOKEN = TokenHandler()
