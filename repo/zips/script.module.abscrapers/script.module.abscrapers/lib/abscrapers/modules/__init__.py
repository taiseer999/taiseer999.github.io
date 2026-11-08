# -*- coding: utf-8 -*-
"""
	Compatibility namespace for add-ons written against cocoscrapers/fenomscrapers:
	  <module>.modules.control.getProviderDefaults()   (Fen Light)
	  <module>.modules.cfscrape.CloudScraper            (Umbrella cloudflare fallback)
	Anything not defined here resolves to the Gears engine's modules package.
"""
import os
__path__.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'engines', 'gears', 'modules'))
