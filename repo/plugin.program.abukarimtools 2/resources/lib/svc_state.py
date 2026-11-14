# -*- coding: utf-8 -*-
"""Which ABUKARIM TOOLS service copy is the live one (3.2.18).

Window(Home).Property(abukarimtools.service.alive) holds '<version>/<origin>/<token>'.
A newer copy started after an in-place update takes the property over; the
older copy's loops see a foreign token and stop, so the new code takes effect
without a duplicate watchdog. (Copies started by the guardian via RunScript are
not managed by Kodi, so Kodi never stops them on an update - this does.)
"""
import xbmcgui

PROP = 'abukarimtools.service.alive'
_token = None


def claim(value):
    global _token
    _token = value
    xbmcgui.Window(10000).setProperty(PROP, value)


def current():
    try:
        return xbmcgui.Window(10000).getProperty(PROP)
    except Exception:
        return ''


def still_mine():
    """True when this process is (still) the live service, or never claimed."""
    if _token is None:
        return True
    return current() == _token


def release():
    if _token is not None and current() == _token:
        xbmcgui.Window(10000).clearProperty(PROP)
