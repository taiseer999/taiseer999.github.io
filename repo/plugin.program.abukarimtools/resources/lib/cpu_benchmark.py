# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""
cpu_benchmark.py - AB Tools CPU Benchmark (rewritten for AB Tools in 4.12.0).

Runs the classic Pystone benchmark (resources/lib/modules/pystone.py, the
CPython version, PSF License) once per logical CPU core and shows the result
in the active skin's text viewer (control 1 = heading, 5 = text):

  * the device: Kodi build, system, processor, architecture, cores, Python;
  * one row per pass with a coloured meter, then the average;
  * the report is uploaded to paste.kodi.tv (log_share) and its link shown.

The passes run on their own thread, so Back closes the window at once (the
pass in progress finishes on its own). Kodi's CPU/RAM overlay
(debug.showloginfo) is on during the run and set back afterwards.
"""
import json
import os
import platform
import re
import subprocess
import threading

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib import paths
from resources.lib.i18n import T
from resources.lib.modules import pystone

TITLE = 'ABUKARIM TOOLS'
TAG = '[AbukarimTools CPUBench]'
PASS_LOOPS = 50000
METER = 40                      # meter width in characters
TOP_SCORE = 200000              # pystones/s that fill the meter
RULE = '[COLOR=dimgrey]%s[/COLOR]' % ('-' * 60)
# meter colour by how full it is: weak .. strong
SHADES = ((0.25, 'red'), (0.5, 'orange'), (0.75, 'yellow'), (1.01, 'limegreen'))


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('%s %s' % (TAG, msg), level)


def _cores():
    try:
        return max(1, os.cpu_count() or 1)
    except Exception:
        return 1


# ---------------------------------------------------------------------- the device
def _read(path):
    try:
        with open(path, 'r', errors='replace') as fh:
            return fh.read()
    except Exception:
        return ''


def processor_name():
    parts = []
    info = _read('/proc/cpuinfo')
    for key in ('model name', 'Hardware'):
        m = re.search(r'^%s\s*:\s*(.+)$' % key, info, re.M)
        if m:
            parts.append(m.group(1).strip())
            break
    board = _read('/proc/device-tree/model').replace('\x00', '').strip()
    if board:
        parts.append(board)
    if not parts and platform.system() == 'Darwin':
        try:
            parts.append(subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string'],
                                                 timeout=5).decode().strip())
        except Exception:
            pass
    return ' '.join(parts) or platform.processor() or platform.machine() or '?'


def device_lines():
    return [
        'Kodi: [B]%s[/B]' % xbmc.getInfoLabel('System.BuildVersion'),
        'System: [B]%s %s[/B]' % (platform.system(), platform.release()),
        'Processor: [B]%s[/B]' % processor_name(),
        'Architecture: [B]%s (%s)[/B]' % (platform.machine(), platform.architecture()[0]),
        'Cores: [B]%d[/B]' % _cores(),
        'Python: [B]%s %s[/B]   Pystone [B]%s[/B], %d loops a pass' % (
            platform.python_implementation(), platform.python_version(),
            getattr(pystone, '__version__', '?'), PASS_LOOPS),
    ]


# ---------------------------------------------------------------------- the meter
def meter(score):
    """A coloured bar for a pystones/s score."""
    share = max(0.0, min(1.0, float(score) / TOP_SCORE))
    filled = int(round(share * METER))
    colour = next(c for limit, c in SHADES if share < limit)
    return '[COLOR=%s]%s[/COLOR][COLOR=dimgrey]%s[/COLOR]' % (colour, '#' * filled, '.' * (METER - filled))


def result_row(label, score, seconds):
    return '%s  %s  [B]%s[/B] pystones/s  (%.2f s)' % (label, meter(score), '{:,}'.format(int(score)), seconds)


def waiting_row(done, total):
    return '[COLOR=dimgrey]%s %d / %d ...[/COLOR]' % (T(30624), done + 1, total)


def plain(text):
    text = text.replace('[CR]', '\n')
    return re.sub(r'\[/?(?:COLOR[^\]]*|B|I)\]', '', text)


# ---------------------------------------------------------------------- the window
class BenchWindow(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        self.heading = kwargs.pop('heading', TITLE)
        self.lines = device_lines() + [RULE]
        self.box = None
        self.cancel = threading.Event()
        self.thread = None

    def onInit(self):
        try:
            self.getControl(1).setLabel(self.heading)
        except Exception:
            pass
        self.box = self.getControl(5)
        self.refresh()
        if self.thread is None:
            self.thread = threading.Thread(target=self.bench, name='abk_cpubench')
            self.thread.daemon = True
            self.thread.start()

    def onAction(self, action):
        if action.getId() in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK,
                              xbmcgui.ACTION_SELECT_ITEM):
            self.cancel.set()
            self.close()

    def refresh(self, extra=None):
        if self.box is None:
            return
        rows = self.lines + ([extra] if extra else [])
        try:
            self.box.setText('[CR]'.join(rows))
            xbmc.sleep(150)
            self.box.scroll(10000)          # newest rows in view
        except Exception:
            pass

    def bench(self):
        total = _cores()
        results = []
        for n in range(total):
            if self.cancel.is_set():
                return
            self.refresh(waiting_row(n, total))
            seconds, score = pystone.pystones(PASS_LOOPS)
            results.append((seconds, score))
            if total > 1:
                self.lines.append(result_row('%s %d' % (T(30624), n + 1), score, seconds))
                self.refresh()
        if self.cancel.is_set() or not results:
            return
        avg_seconds = sum(r[0] for r in results) / len(results)
        avg_score = sum(r[1] for r in results) / len(results)
        _log('score %d pystones/s (%d passes, %.2f s each)' % (avg_score, len(results), avg_seconds))
        self.lines += [RULE, result_row('[B]%s[/B]' % T(30621), avg_score, avg_seconds), RULE]
        self.refresh('[COLOR=dimgrey]%s[/COLOR]' % T(30623))
        try:
            from resources.lib import log_share
            head = 'AB Tools %s - CPU Benchmark\n\n' % paths.version()
            link = log_share.upload(head + plain('[CR]'.join(self.lines)))
            _log('uploaded: %s' % link)
            self.lines.append('%s: [B]%s[/B]' % (T(30622), link))
        except Exception as e:
            _log('upload failed: %s' % e, xbmc.LOGWARNING)
        if not self.cancel.is_set():
            self.refresh('[COLOR=dimgrey]%s[/COLOR]' % T(30625))


# ---------------------------------------------------------------------- entry
def _setting(method, **params):
    call = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(call))).get('result')
    except Exception:
        return None


def run():
    shown = bool((_setting('Settings.GetSettingValue', setting='debug.showloginfo') or {}).get('value'))
    if not shown:
        _setting('Settings.SetSettingValue', setting='debug.showloginfo', value=True)
    try:
        win = BenchWindow('DialogTextViewer.xml', xbmcvfs.translatePath(paths.ADDON_PATH), 'Default', '1080i',
                          heading='%s - %s' % (TITLE, T(30620)))
        win.doModal()
        win.cancel.set()
        del win
    except Exception as e:
        _log('failed: %s' % e, xbmc.LOGERROR)
        xbmcgui.Dialog().ok(TITLE, T(30626) % e)
    finally:
        if not shown:
            _setting('Settings.SetSettingValue', setting='debug.showloginfo', value=False)
