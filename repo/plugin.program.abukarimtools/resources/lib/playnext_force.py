# -*- coding: utf-8 -*-
"""
playnext_force.py - ABUKARIM TOOLS 4.7.18

Turns "play next episode" on in the video add-ons on every patch run, so an
episode always leads to the next one (and, for an episode Search All played,
to Search All for the next one through the same add-on):

  Fen Light / Red Light  autoplay_next_episode + autoscrape_next_episode in
                         addon_data/<id>/databases/settings.db (their own
                         settings store) and the "<prefix>.<id>" Home
                         properties they read first. Which of the two runs
                         follows the add-on's own "autoplay" choice for
                         episodes, so both are on.
  POV                    autoplay_next_episode + autoscrape_next_episode in
                         its settings (and the pov_settings Home property).
  Umbrella               enable.playnext

Only writes what is not already on. Add-ons that are not installed, or never
opened yet (no settings.db), are skipped.
"""
import json
import os

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

_FEN_KEYS = ('autoplay_next_episode', 'autoscrape_next_episode')
_DB_ADDONS = (('plugin.video.fenlight', 'fenlight'), ('plugin.video.redlight', 'redlight'))
_POV = 'plugin.video.pov'
_UMB = 'plugin.video.umbrella'
ADDON_IDS = tuple(a for a, _p in _DB_ADDONS) + (_POV, _UMB)


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools PlayNext] %s' % msg, level)


def _installed(aid):
    return xbmc.getCondVisibility('System.HasAddon(%s)' % aid)


def _fen_family(aid, prefix):
    db = xbmcvfs.translatePath('special://profile/addon_data/%s/databases/settings.db' % aid)
    if not os.path.isfile(db):
        return 'no settings.db yet'
    import sqlite3
    con = sqlite3.connect(db, timeout=10)
    try:
        changed = []
        for key in _FEN_KEYS:
            row = con.execute('SELECT setting_value FROM settings WHERE setting_id = ?', (key,)).fetchone()
            if row and row[0] == 'true':
                continue
            con.execute('INSERT OR REPLACE INTO settings VALUES (?, ?, ?, ?)', (key, 'boolean', 'false', 'true'))
            changed.append(key)
        con.commit()
    finally:
        con.close()
    win = xbmcgui.Window(10000)
    for key in _FEN_KEYS:                       # the add-on reads its Home property first
        win.setProperty('%s.%s' % (prefix, key), 'true')
    return ', '.join(changed) + ' on' if changed else ''


def _pov():
    addon = xbmcaddon.Addon(_POV)
    changed = [k for k in _FEN_KEYS if addon.getSetting(k) != 'true']
    for key in changed:
        addon.setSetting(key, 'true')
    win = xbmcgui.Window(10000)
    raw = win.getProperty('pov_settings')
    if raw:
        try:
            cache = json.loads(raw)
            if any(cache.get(k) != 'true' for k in _FEN_KEYS):
                cache.update({k: 'true' for k in _FEN_KEYS})
                win.setProperty('pov_settings', json.dumps(cache))
        except Exception:
            pass
    return ', '.join(changed) + ' on' if changed else ''


def _umbrella():
    addon = xbmcaddon.Addon(_UMB)
    if addon.getSetting('enable.playnext') == 'true':
        return ''
    addon.setSetting('enable.playnext', 'true')
    return 'enable.playnext on'


def ensure(addon_ids=None):
    """[(ok, message)] in patcher style; 'Patched OK' only when something was switched on."""
    scope = set(addon_ids or ADDON_IDS)
    out = []
    jobs = [(aid, (lambda a=aid, p=prefix: _fen_family(a, p))) for aid, prefix in _DB_ADDONS]
    jobs += [(_POV, _pov), (_UMB, _umbrella)]
    for aid, job in jobs:
        if aid not in scope or not _installed(aid):
            continue
        try:
            what = job()
        except Exception as e:
            out.append((False, '[%s] Play next: %s' % (aid, e)))
            continue
        if what == 'no settings.db yet':
            out.append((True, '[%s] Play next: add-on not opened yet - skipping.' % aid))
        elif what:
            out.append((True, '[%s] Patched OK: play next episode - %s' % (aid, what)))
        else:
            out.append((True, '[%s] Play next already on - skipping.' % aid))
    return out
