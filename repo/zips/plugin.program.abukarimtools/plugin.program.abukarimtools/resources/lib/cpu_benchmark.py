# -*- coding: utf-8 -*-
"""
cpu_benchmark.py - CPU Benchmark (pystone) inside ABUKARIM TOOLS.

Port of script.pystone.benchmark 1.1.8 by Lunatixz (GPLv3,
https://github.com/Lunatixz/Kodi_Addons/tree/master/script.pystone.benchmark).
The pystone benchmark itself is vendored unchanged at
resources/lib/modules/pystone.py.

Changes from the original:
  * no kodi_six / requests - plain xbmc* and the paste.kodi.tv uploader
    from log_share;
  * the passes run on a worker thread, so Back closes the window (and stops
    after the current pass) instead of being ignored until the end;
  * Kodi's debug overlay (CPU/RAM, debug.showloginfo) is switched on during
    the run and always restored afterwards;
  * texts go through i18n (English / Arabic).
"""
import os
import re
import json
import platform
import textwrap
import threading

import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.i18n import T
from resources.lib.modules import pystone

TITLE = 'ABUKARIM TOOLS'
LIMIT = 45
LINE  = 64
LOOP  = 50000
MAXSEED = 200000
TAG   = '[AbukarimTools CPUBench]'

try:
    CPU_COUNT = os.cpu_count() or 1
except Exception:
    CPU_COUNT = 1


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('%s %s' % (TAG, msg), level)


def _repeat(length=LIMIT, fill=u'█'):
    length = int(round(length))
    return (fill * (int(length / len(fill)) + 1))[:length]


def _k(n):
    n = int(n)
    return '%dk' % (n // 1000) if n >= 1000 else str(n)


def _color(col, txt):
    return '[COLOR=%s]%s[/COLOR]' % (col, txt)


def progress_bar(iteration, total, length=LIMIT, fill=u'█'):
    percent = '%.1f' % (100 * (iteration / float(total)))
    filled = int(length * iteration // total)
    bar = fill * filled + '-' * (length - filled)
    if filled > 10:
        mid = length // 2 - len(percent) // 2
        bar = bar[:mid] + percent + '%' + bar[mid + len(percent):]
    return '|%s|' % bar


def score_bar(stones, seed, dur, length=LIMIT):
    value = (stones * 100) // MAXSEED
    if value >= 100:
        value = 90
    value = 100 - value
    score = '| %s |' % stones
    fill = _repeat(length - 4)
    sindex = int(length * ((length / 100.0) * value / length))
    colors = ['green', 'yellow', 'orange', 'red', 'dimgrey', 'dimgrey']
    chunks = textwrap.wrap(fill[:sindex - len(score) // 2] + score
                           + fill[sindex + len(score) // 2:], length // 4)
    bars = ''.join(_color(colors.pop(0), c) for c in chunks if colors)
    return '| %s | %s in %.2fs' % (bars, _k(seed), dur)


def _cpu_name():
    try:
        with open('/proc/cpuinfo', 'r') as f:
            info = f.read()
        m = (re.search(r'model name\s*:\s*(.+)', info)
             or re.search(r'Hardware\s*:\s*(.+)', info))
        name = m.group(1).strip() if m else ''
    except Exception:
        name = ''
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read().strip().strip('\x00')
        if model:
            name = ('%s %s' % (name, model)).strip()
    except Exception:
        pass
    if not name and platform.system() == 'Darwin':
        try:
            import subprocess
            name = subprocess.check_output(
                ['sysctl', '-n', 'machdep.cpu.brand_string']).decode().strip()
        except Exception:
            pass
    return name or platform.processor() or platform.machine()


def system_info():
    sep = _repeat(LINE, '_')
    return '[CR]'.join([
        'Kodi Build: [B]%s[/B]' % xbmc.getInfoLabel('System.BuildVersion'),
        'Operating System: [B]%s v.%s (%s)[/B]' % (platform.system(), platform.release(),
                                                  platform.platform()),
        sep,
        'Processor: [B]%s[/B]' % _cpu_name(),
        'Machine Architecture: [B]%s %s[/B]' % (platform.machine(),
                                               ' '.join(platform.architecture())),
        'Logical CPU Cores: [B]%d[/B]' % CPU_COUNT,
        sep,
        'Python: [B]%s v.%s[/B][CR]Benchmark: [B]pystone v.%s[/B] n=%d' % (
            platform.python_implementation(), platform.python_version(),
            pystone.__version__, LOOP),
        sep,
    ])


def _plain(text):
    text = text.replace('[CR]', '\n')
    text = re.sub(r'\[/?COLOR[^\]]*\]', '', text)
    return re.sub(r'\[/?[BI]\]', '', text)


class BenchWindow(xbmcgui.WindowXMLDialog):
    """Runs inside the active skin's DialogTextViewer (1 = heading, 5 = text)."""

    def __init__(self, *args, **kwargs):
        self.head = kwargs.pop('head', TITLE)
        self.text = system_info()
        self.textbox = None
        self.stop = threading.Event()
        self.worker = None

    def onInit(self):
        try:
            self.getControl(1).setLabel(self.head)
        except Exception:
            pass
        self.textbox = self.getControl(5)
        self._show(self.text)
        if self.worker is None:      # onInit can fire again after a re-init
            self.worker = threading.Thread(target=self._run, name='abk_cpubench')
            self.worker.daemon = True
            self.worker.start()

    def onAction(self, action):
        if action.getId() in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK,
                              xbmcgui.ACTION_SELECT_ITEM):
            self.stop.set()
            self.close()

    def _show(self, txt):
        try:
            self.textbox.setText(txt)
            # keep the newest lines in view (any skin: Kodi clamps the offset
            # to the last page once the new text is laid out)
            xbmc.sleep(150)
            self.textbox.scroll(10000)
        except Exception:
            pass

    def _run(self):
        ranks = []
        seeds = [LOOP] * CPU_COUNT
        for i, seed in enumerate(seeds):
            if self.stop.is_set():
                return
            self._show('%s[CR]%s' % (self.text, progress_bar(i, len(seeds))))
            dur, stones = pystone.pystones(seed)
            ranks.append((seed, dur, stones))
            if len(seeds) > 1:
                self.text = '%s[CR]%s %d%s' % (self.text, T(30624), i + 1,
                                              score_bar(int(stones), seed, dur))
                self._show(self.text)
        if self.stop.is_set() or not ranks:
            return
        n = float(len(ranks))
        avg_seed = int(sum(r[0] for r in ranks) / n)
        avg_dur = sum(r[1] for r in ranks) / n
        avg_stones = int(sum(r[2] for r in ranks) / n)
        _log('score %d pystones/s (%d passes, %.2fs avg)' % (avg_stones, len(ranks), avg_dur))
        self.text = '%s[CR]%s %s[CR]%s' % (self.text, T(30621),
                                           score_bar(avg_stones, avg_seed, avg_dur),
                                           _repeat(LINE, '_'))
        self._show('%s[CR]%s' % (self.text, _color('dimgrey', T(30623))))
        try:
            from resources.lib import log_share
            build = 'ABUKARIM TOOLS %s | CPU Benchmark\n\n' % (
                xbmcaddon.Addon('plugin.program.abukarimtools').getAddonInfo('version'))
            url = log_share.upload(build + _plain(self.text))
            _log('uploaded: %s' % url)
            self.text = '%s[CR]%s: [B]%s[/B]' % (self.text, T(30622), url)
        except Exception as e:
            _log('upload failed: %s' % e, xbmc.LOGWARNING)
        if not self.stop.is_set():
            self._show('%s[CR]%s' % (self.text, _color('dimgrey', T(30625))))


def _rpc(method, params):
    req = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(req))).get('result')
    except Exception:
        return None


def run():
    import xbmcvfs
    path = xbmcvfs.translatePath(
        xbmcaddon.Addon('plugin.program.abukarimtools').getAddonInfo('path'))
    res = _rpc('Settings.GetSettingValue', {'setting': 'debug.showloginfo'}) or {}
    overlay_was_on = bool(res.get('value', False))
    if not overlay_was_on:
        _rpc('Settings.SetSettingValue', {'setting': 'debug.showloginfo', 'value': True})
    try:
        win = BenchWindow('DialogTextViewer.xml', path, 'Default', '1080i',
                          head='%s - %s' % (TITLE, T(30620)))
        win.doModal()
        win.stop.set()
        del win
    except Exception as e:
        _log('failed: %s' % e, xbmc.LOGERROR)
        xbmcgui.Dialog().ok(TITLE, T(30626) % e)
    finally:
        if not overlay_was_on:
            _rpc('Settings.SetSettingValue', {'setting': 'debug.showloginfo', 'value': False})
