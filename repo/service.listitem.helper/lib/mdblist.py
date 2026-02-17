#!/usr/bin/python
# -*- coding: utf-8 -*-

'''Get metadata from mdblist'''
import sys
if sys.version_info.major == 3:# Python 3
    from .utils import get_json, KODI_LANGUAGE, try_parse_int, int_with_commas, ADDON_ID
else:# Python 2
    from utils import get_json, KODI_LANGUAGE, try_parse_int, int_with_commas, ADDON_ID
from simplecache import use_cache
from operator import itemgetter
import xbmc
import xbmcgui
import xbmcaddon
import datetime


class mdblist(object):
    '''get metadata from mdblist'''
    api_key = None  # public var to be set by the calling addon

    def __init__(self, simplecache=None):
        '''Initialize - optionaly provide simplecache object'''
        if not simplecache:
            from simplecache import SimpleCache
            self.cache = SimpleCache()
        else:
            self.cache = simplecache
        addon = xbmcaddon.Addon(id=ADDON_ID)
        # personal api key (preferred over provided api key)
        api_key = addon.getSetting("mdblist_api_key")
        if api_key:
            self.api_key = api_key
        del addon

    def get_details_by_externalid(self, extid, extid_type):
        params = {}
        params["i"] = extid
        results = self.get_data(params)
        if results:
            return results

    def get_data(self, params):
        '''helper method to get data from mdblist json API'''
        url = u'https://mdblist.com/api/'
        
        unique_cache_id = 'listitemhelpermdblist.' + url + params["i"]
        
        if self.api_key:
            # addon provided or personal api key
            params["apikey"] = self.api_key
            rate_limit = None
            expiration = datetime.timedelta(days=2)
        else:
            params["apikey"] = ""
            # without personal (or addon specific) api key = rate limiting and older info from cache
            rate_limit = ("mdblist.com", 5)
            expiration = datetime.timedelta(days=30)
        
        cache = self.cache.get(unique_cache_id)
        
        if cache:
            # data obtained from cache
            result = cache
        elif self.api_key:
            # no cache, grab data from API
            result = get_json(url, params, ratelimit=rate_limit, suppressException=True)
            if result and "title" in result and "type" in result and (result['type'] == 'movie' or result['type'] == 'show'):
                
                self.cache.set(unique_cache_id, result, expiration=expiration)
                
        if self.api_key and result:
            return result
