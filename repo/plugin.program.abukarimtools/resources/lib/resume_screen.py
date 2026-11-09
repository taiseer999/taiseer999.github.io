# -*- coding: utf-8 -*-
"""
resume_screen.py - ABUKARIM TOOLS (4.8.2)

A Fen Light+ style resume screen for streams picked in Search All:
clearlogo (or title), "year | running time | ends at", "certificate |
genres | rating", plot, then Resume N% / Start Over / Cancel and a bar
showing how much has been watched.

Self-contained: it also runs inside other add-ons' interpreters (the
Umbrella Search All bridge loads it by file path), so it imports nothing
from AB Tools' packages and reads AB Tools' strings through xbmcaddon.

    show(meta, percent) -> 'resume' | 'start' | None (cancelled)

meta keys used (all optional): title, tvshowtitle, year, runtime (minutes),
mpaa, genre (text or list), rating, plot, clearlogo, fanart.
"""
import time

import xbmc
import xbmcaddon
import xbmcgui

ADDON_ID = 'plugin.program.abukarimtools'
XML = 'abk_resume.xml'
_BACK = (9, 10, 92, 216, 247, 257, 275, 61467, 61448)


def _s(sid, fallback):
    try:
        text = xbmcaddon.Addon(ADDON_ID).getLocalizedString(sid)
        return text or fallback
    except Exception:
        return fallback


def _num(v):
    try:
        return float(str(v).strip())
    except Exception:
        return 0.0


def _lines(meta):
    sep = '  |  '
    first, second = [], []
    year = str(meta.get('year') or '').strip()
    if year and year != '0':
        first.append(year)
    minutes = int(_num(meta.get('runtime')))
    if minutes > 0:
        first.append(_s(32118, '%dh %dm') % (minutes // 60, minutes % 60) if minutes >= 60
                     else _s(32124, '%dm') % minutes)
        ends = time.localtime(time.time() + minutes * 60)
        first.append(_s(32119, 'Ends at %s') % time.strftime('%H:%M', ends))
    mpaa = str(meta.get('mpaa') or '').replace('Rated ', '').strip()
    if mpaa:
        second.append(mpaa)
    genre = meta.get('genre')
    if isinstance(genre, (list, tuple)):
        genre = ', '.join(str(g) for g in genre[:3] if g)
    genre = str(genre or '').replace(' / ', ', ').strip()
    if genre:
        second.append(genre)
    rating = _num(meta.get('rating'))
    if rating > 0:
        second.append('%.1f' % rating)
    return sep.join(first), sep.join(second)


class ResumeScreen(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.meta = kwargs.get('meta') or {}
        self.percent = max(0.0, min(100.0, _num(kwargs.get('percent'))))
        self.choice = None

    def onInit(self):
        m = self.meta
        line1, line2 = _lines(m)
        props = {
            'abk.r.logo': m.get('clearlogo') or '',
            'abk.r.fanart': m.get('fanart') or '',
            'abk.r.title': m.get('tvshowtitle') or m.get('title') or '',
            'abk.r.line1': line1,
            'abk.r.line2': line2,
            'abk.r.plot': m.get('plot') or '',
            'abk.r.resume': _s(32120, 'Resume %d%%') % max(1, int(round(self.percent))),
            'abk.r.start': _s(32121, 'Start Over'),
            'abk.r.cancel': _s(32122, 'Cancel'),
        }
        for k, v in props.items():
            self.setProperty(k, str(v))
        try:
            self.getControl(30).setPercent(self.percent)
        except Exception:
            pass
        try:
            self.setFocusId(10)
        except Exception:
            pass

    def onClick(self, control_id):
        self.choice = {10: 'resume', 11: 'start'}.get(control_id)
        self.close()

    def onAction(self, action):
        if action.getId() in _BACK:
            self.choice = None
            self.close()


def show(meta, percent):
    """Returns 'resume', 'start' or None (cancelled)."""
    path = xbmcaddon.Addon(ADDON_ID).getAddonInfo('path')
    win = ResumeScreen(XML, path, 'Default', '1080i', meta=meta, percent=percent)
    try:
        win.doModal()
        choice = win.choice
    finally:
        del win
    xbmc.log('[AbukarimTools Resume] %.0f%% -> %s' % (_num(percent), choice or 'cancel'), xbmc.LOGINFO)
    return choice
