# -*- coding: utf-8 -*-
"""
settings_flush.py - make GUI-setting changes survive an ABUKARIM restart.

3.4.31: Settings.SetSettingValue (JSON-RPC) only changes the value in memory.
Kodi writes guisettings.xml on a CLEAN shutdown, but every ABUKARIM restart
is a force close (origin_fix.force_restart -> os._exit), so the change was
thrown away and Kodi came back with the old value. That is why Device Tuning
"did not change the values" and why the readfactor stayed "adaptive".

There is no "SaveSettings" builtin in Kodi. What does exist: every
Skin.SetBool(name,value) call ends with CSettings::Save() (SkinBuiltins.cpp),
which writes the whole in-memory settings to guisettings.xml. We trigger that
with a private flag, then verify the file and, as a last resort, write the
values into guisettings.xml ourselves (Kodi would write the same values on a
clean exit, so the two never disagree).
"""

import os
import re

import xbmc
import xbmcvfs

_FLAG = 'abukarimtools.settings_flush'


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools SettingsFlush] %s' % msg, level)


def _path():
    return xbmcvfs.translatePath('special://profile/guisettings.xml')


def _read(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except OSError:
        return ''


def _rx(sid):
    return re.compile(r'<setting\s+id="%s"(?:\s[^>]*)?(?:/>|>(.*?)</setting>)'
                      % re.escape(sid), re.S)


def _on_disk(text, sid):
    m = _rx(sid).search(text)
    if not m:
        return None
    return (m.group(1) or '').strip()


def _missing(text, values):
    return {sid: v for sid, v in values.items() if _on_disk(text, sid) != str(v)}


def _write_file(path, text, values):
    for sid, v in values.items():
        new = '<setting id="%s">%s</setting>' % (sid, v)
        rx = _rx(sid)
        if rx.search(text):
            text = rx.sub(lambda _m: new, text, count=1)
        elif '</settings>' in text:
            text = text.replace('</settings>', '    %s\n</settings>' % new, 1)
        else:
            return False
    tmp = path + '.abk.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(text)
        os.replace(tmp, path)
        return True
    except OSError as e:
        _log('direct write failed: %s' % e, xbmc.LOGERROR)
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def flush(values=None):
    """Save Kodi's settings to disk now. `values` = {setting_id: value} that
    must end up in guisettings.xml. Returns True when they are on disk (or
    nothing to verify). Never raises."""
    try:
        xbmc.executebuiltin('Skin.SetBool(%s,true)' % _FLAG, True)
        xbmc.sleep(500)
    except Exception as e:
        _log('Skin.SetBool save trigger failed: %s' % e, xbmc.LOGWARNING)
    if not values:
        return True
    path = _path()
    text = _read(path)
    if not text:
        _log('guisettings.xml not readable at %s' % path, xbmc.LOGWARNING)
        return False
    miss = _missing(text, values)
    if not miss:
        _log('saved to guisettings.xml: %s' % values)
        return True
    _log('Kodi did not save %s - writing guisettings.xml directly' % miss,
         xbmc.LOGWARNING)
    if _write_file(path, text, miss) and not _missing(_read(path), values):
        _log('written to guisettings.xml: %s' % miss)
        return True
    _log('could not persist %s' % miss, xbmc.LOGERROR)
    return False
