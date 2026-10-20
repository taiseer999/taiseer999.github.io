# -*- coding: utf-8 -*-
"""Shim: control API that external players expect from a scraper module."""
from abscrapers.engines.gears.modules.control import *  # noqa: F401,F403
from abscrapers.common import setting, setSetting, getProviderDefaults, make_settings_dict, settings_fallback  # noqa: F401
