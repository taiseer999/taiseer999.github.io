# -*- coding: utf-8 -*-
"""Najd's health record, so one report explains a crash or a power-off:
  - at start: did Kodi end normally last time? If not, keep Kodi's last lines (every
    add-on, not only Najd) and Kodi's crash log;
  - every 5 minutes: free memory, CPU heat and load, and what is playing — running out
    of memory or overheating shows in the last pulses before a crash.
All of it goes to Najd's own 3-day history (never kodi.log)."""
import glob
import os
import threading
import time

import xbmc
import xbmcvfs

from .common import PROFILE, history_note, history_block, log

STATE = os.path.join(PROFILE, 'health_state.txt')


def _read():
    try:
        with open(STATE, encoding='utf-8') as f:
            parts = f.read().split('|')
        return parts[0], parts[1] if len(parts) > 1 else ''
    except OSError:
        return '', ''


def _write(flag):
    try:
        with open(STATE, 'w', encoding='utf-8') as f:
            f.write('%s|%s' % (flag, time.strftime('%Y-%m-%d %H:%M:%S')))
    except OSError:
        pass


def _before_crash():
    logdir = xbmcvfs.translatePath('special://logpath')
    try:
        with open(os.path.join(logdir, 'kodi.old.log'), encoding='utf-8', errors='replace') as f:
            tail = f.readlines()[-300:]
        history_block("Kodi's last 300 lines before it went off (all add-ons)", tail)
    except OSError:
        pass
    seen = set()
    for d in (xbmcvfs.translatePath('special://temp'), xbmcvfs.translatePath('special://home'),
              logdir, os.path.expanduser('~'), '/storage/.kodi/temp', '/storage'):
        for f in glob.glob(os.path.join(d, '*crash*')):
            try:
                real = os.path.realpath(f)
                if real in seen or f.endswith('.dmp') or time.time() - os.path.getmtime(f) > 3 * 86400:
                    continue
                seen.add(real)
                with open(f, encoding='utf-8', errors='replace') as fh:
                    lines = fh.readlines()[-200:]
                history_block('Kodi crash log %s (%s)' % (os.path.basename(f), time.strftime(
                    '%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(f)))), lines)
            except OSError:
                continue


def _pulse():
    il = xbmc.getInfoLabel
    parts = ['free memory %s' % (il('System.FreeMemory') or '?'),
             'cpu temp %s' % (il('System.CPUTemperature') or '?'),
             'cpu %s' % (il('System.CpuUsage') or '?').replace('\n', ' ')]
    try:
        if xbmc.Player().isPlayingVideo():
            parts.append('playing %s at %s' % (il('Player.Filename')[:80], il('Player.Time')))
    except Exception:
        pass
    history_note('pulse: ' + ' | '.join(parts))


def start(monitor):
    flag, last = _read()
    if flag == 'running':
        history_note('KODI DID NOT CLOSE NORMALLY (power off or crash). Last seen running: %s' % (last or '?'))
        log('the last session did not end normally (last seen %s)' % (last or '?'))
        try:
            _before_crash()
        except Exception as e:
            history_note('could not keep the moments before: %s' % e)
    elif flag == 'stopped':
        history_note('Kodi closed normally at %s' % last)
    history_note('Kodi started')
    _write('running')

    def loop():
        n = 0
        while not monitor.waitForAbort(60):
            n += 1
            _write('running')
            if n % 5 == 1:
                try:
                    _pulse()
                except Exception:
                    pass
    threading.Thread(target=loop, daemon=True).start()


def stop():
    _write('stopped')
    history_note('Kodi closing')
