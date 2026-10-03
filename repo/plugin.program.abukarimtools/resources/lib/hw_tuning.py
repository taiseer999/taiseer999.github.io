# -*- coding: utf-8 -*-
"""
hw_tuning.py - size Kodi's video cache to the box it is running on.

The build ships one advancedsettings.xml (200 MB cache, readfactor 20). That
is right for a 4 GB Ugoos AM9 Pro but too much for a 2 GB box, where it
pushes Kodi into low-memory kills during long 4K remuxes. This picks the
values from the detected RAM and edits only the <cache> block, keeping every
other line and comment of advancedsettings.xml untouched.

    RAM >= 3.5 GB  -> 200 MB, readfactor 20
    RAM >= 1.8 GB  -> 100 MB, readfactor 10
    otherwise      ->  50 MB, readfactor 4
"""

import os
import re

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

ADV = xbmcvfs.translatePath('special://profile/advancedsettings.xml')
TITLE = 'ABUKARIM – Device Tuning'

TIERS = [
    (3500, 200, 20, 'high'),
    (1800, 100, 10, 'mid'),
    (0,     50,  4, 'low'),
]


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools HwTuning] %s' % msg, level)


def _read(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except OSError:
        return ''


def ram_mb():
    m = re.search(r'MemTotal:\s+(\d+)\s*kB', _read('/proc/meminfo'))
    if m:
        return int(m.group(1)) // 1024
    lab = xbmc.getInfoLabel('System.Memory(total)') or ''
    m = re.search(r'([\d.]+)\s*([GM])B', lab, re.I)
    if m:
        v = float(m.group(1))
        return int(v * 1024) if m.group(2).upper() == 'G' else int(v)
    return 0


def soc():
    """Human readable SoC / board string (best effort)."""
    dt = _read('/proc/device-tree/model').strip('\x00 \n')
    if dt:
        return dt
    m = re.search(r'^Hardware\s*:\s*(.+)$', _read('/proc/cpuinfo'), re.M)
    if m:
        return m.group(1).strip()
    comp = _read('/proc/device-tree/compatible').replace('\x00', ' ').strip()
    return comp or xbmc.getInfoLabel('System.CpuInfo') or '?'


def recommend(mb=None):
    mb = ram_mb() if mb is None else mb
    for floor, size, rf, name in TIERS:
        if mb >= floor:
            return {'ram_mb': mb, 'memorysize': size * 1024 * 1024,
                    'readfactor': rf, 'tier': name}
    return None


def current():
    txt = _read(ADV)
    ms = re.search(r'<memorysize>\s*(\d+)\s*</memorysize>', txt)
    rf = re.search(r'<readfactor>\s*(\d+)\s*</readfactor>', txt)
    return (int(ms.group(1)) if ms else None, int(rf.group(1)) if rf else None)


def _set_tag(block, tag, value):
    rx = re.compile(r'<%s>\s*[^<]*\s*</%s>' % (tag, tag))
    if rx.search(block):
        return rx.sub('<%s>%s</%s>' % (tag, value, tag), block, count=1)
    return block.replace('</cache>', '    <%s>%s</%s>\n  </cache>' % (tag, value, tag), 1)


def apply(rec=None):
    """Write the recommendation. Returns True when the file changed."""
    rec = rec or recommend()
    if not rec:
        return False
    txt = _read(ADV)
    if not txt.strip():
        txt = '<?xml version="1.0" ?>\n<advancedsettings version="1.0">\n</advancedsettings>\n'
    if '<cache>' not in txt:
        txt = txt.replace('</advancedsettings>',
                          '  <cache>\n  </cache>\n</advancedsettings>', 1)
    head, rest = txt.split('<cache>', 1)
    block, tail = rest.split('</cache>', 1)
    block = '<cache>' + block + '</cache>'
    new = _set_tag(block, 'buffermode', 1)
    new = _set_tag(new, 'memorysize', rec['memorysize'])
    new = _set_tag(new, 'readfactor', rec['readfactor'])
    # keep the human note next to memorysize truthful ("<!-- 200MB -->")
    new = re.sub(r'(</memorysize>\s*<!--\s*)\d+\s*MB(\s*-->)',
                 r'\g<1>%dMB\g<2>' % (rec['memorysize'] // 1048576), new)
    if new == block:
        return False
    out = head + new + tail
    try:
        tmp = ADV + '.abk.part'
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(out)
        os.replace(tmp, ADV)
    except OSError as e:
        _log('write failed: %s' % e, xbmc.LOGERROR)
        return False
    _log('cache set to %d MB / readfactor %d (RAM %d MB, %s tier)'
         % (rec['memorysize'] // 1048576, rec['readfactor'], rec['ram_mb'], rec['tier']))
    return True


def auto():
    """Silent first-run step."""
    try:
        if apply():
            rec = recommend()
            xbmcgui.Dialog().notification(
                TITLE, T(30540) % (rec['memorysize'] // 1048576), xbmcgui.NOTIFICATION_INFO, 4000)
            return True
    except Exception as e:
        _log('auto tuning failed: %s' % e, xbmc.LOGWARNING)
    return False


def run():
    """Menu entry: show what was detected, apply on confirm."""
    rec = recommend()
    cur_ms, cur_rf = current()
    msg = T(30541) % (
        soc(), rec['ram_mb'],
        (cur_ms or 0) // 1048576, cur_rf or 0,
        rec['memorysize'] // 1048576, rec['readfactor'])
    if (cur_ms, cur_rf) == (rec['memorysize'], rec['readfactor']):
        xbmcgui.Dialog().ok(TITLE, msg + '[CR][CR]' + T(30542))
        return
    if xbmcgui.Dialog().yesno(TITLE, msg):
        if apply(rec):
            try:
                from resources.lib import origin_fix
                origin_fix.recommend_restart(message=T(30543))
            except Exception:
                xbmcgui.Dialog().ok(TITLE, T(30543))
