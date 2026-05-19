# -*- coding: utf-8 -*-

import re
from providerModules.a4kScrapers import core

class sources(core.DefaultExtraQuerySources):
    def __init__(self, *args, **kwargs):
        super(sources, self).__init__(__name__, *args, request_timeout=5, **kwargs)

    def _find_title(self, el):
        try:
            links = el.find_all('a')
            for link in links:
                href = link.get('href', '')
                if 'torrent.html' in href:
                    return link.text.strip()
        except:
            pass
        return el.text.split('\n')[1] if len(el.text.split('\n')) > 1 else ''

    def _find_url(self, el):
        try:
            links = el.find_all('a')
            for link in links:
                href = link.get('href', '')
                if 'torrent.html' in href:
                    return href
        except:
            pass
        return ''

    def _find_seeds(self, el):
        try:
            text = el.text
            match = re.search(r'(\d+)\s*$', text.strip())
            if match:
                return match.group(1)
        except:
            pass
        return '0'
