# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""
clock_fix.py - correct time from the first seconds on boxes without an RTC.

4.12.13: a user's AM9 Pro (CoreELEC, no /dev/rtc*) booted with the clock on
2026-11-05 while the real date was 2026-11-21. Until connman synced the time
(its time servers were empty, so it first had to resolve pool names through a
slow router DNS) HTTPS to any server whose certificate was issued after the
stale date failed, and every add-on looked "offline" for a minute or two. The
same build on an Intel box (CMOS clock) was fine.

Two parts, both only on CoreELEC / LibreELEC with no RTC device:

1. Boot unit /storage/.config/system.d/abk-clock.service runs a tiny helper
   (/storage/.config/abk_clock.py) before connman and Kodi. It moves the clock
   FORWARD to the last time saved on this box (never backwards), so the clock
   is at most the shutdown gap behind instead of weeks. On shutdown it saves.

2. From Kodi, a thread asks NTP servers by IP address (no DNS needed) with a
   plain SNTP query, steps the clock when it is off by more than 2 s, and then
   saves the time every 10 minutes so a power cut loses little.

Off switch: create /storage/.config/abk_clock.off (both parts then do nothing).
"""

import glob
import os
import socket
import struct
import subprocess
import threading
import time

import xbmc

STAMP = '/storage/.cache/abk_clock'
OFF_FLAG = '/storage/.config/abk_clock.off'
HELPER = '/storage/.config/abk_clock.py'
UNIT_DIR = '/storage/.config/system.d'
UNIT_NAME = 'abk-clock.service'
UNIT = os.path.join(UNIT_DIR, UNIT_NAME)
WANTS = os.path.join(UNIT_DIR, 'sysinit.target.wants', UNIT_NAME)

# Cloudflare (time.cloudflare.com) and Google (time.google.com), by address.
NTP_SERVERS = ('162.159.200.1', '162.159.200.123', '216.239.35.0', '216.239.35.4')
NTP_EPOCH = 2208988800          # 1900-01-01 -> 1970-01-01
MIN_VALID = 1767225600          # 2026-01-01: anything earlier is a stale clock
MAX_VALID = 4102444800          # 2100-01-01: anything later is garbage
STEP_IF_OFF = 2.0               # seconds
SAVE_EVERY = 600                # seconds
SYNC_BUDGET = 180               # keep trying NTP this long after Kodi starts

HELPER_SRC = r'''#!/usr/bin/python3
# AB Tools clock helper (plugin.program.abukarimtools, clock_fix.py).
# restore: move the clock FORWARD to the last saved time (box has no RTC).
# save:    store the current time if it is newer than the saved one.
import os, sys, time
STAMP = '%(stamp)s'
OFF = '%(off)s'
MIN_VALID, MAX_VALID = %(min)d, %(max)d
def read():
    try:
        with open(STAMP) as f:
            return int(f.read().strip())
    except Exception:
        return 0
def main():
    if os.path.exists(OFF) or len(sys.argv) < 2:
        return
    now = int(time.time())
    saved = read()
    if sys.argv[1] == 'restore':
        if MIN_VALID < saved < MAX_VALID and now < saved:
            time.clock_settime(time.CLOCK_REALTIME, saved)
            print('abk-clock: clock moved from %%d to saved %%d' %% (now, saved))
    elif sys.argv[1] == 'save':
        if MIN_VALID < now < MAX_VALID and now > saved:
            tmp = STAMP + '.tmp'
            with open(tmp, 'w') as f:
                f.write(str(now))
            os.replace(tmp, STAMP)
main()
''' % {'stamp': STAMP, 'off': OFF_FLAG, 'min': MIN_VALID, 'max': MAX_VALID}

UNIT_SRC = '''[Unit]
Description=AB Tools: restore the last saved time (no RTC on this box)
DefaultDependencies=no
After=local-fs.target
Before=sysinit.target time-set.target connman.service kodi.service shutdown.target
Conflicts=shutdown.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/python3 %(helper)s restore
ExecStop=/usr/bin/python3 %(helper)s save
TimeoutSec=10

[Install]
WantedBy=sysinit.target
''' % {'helper': HELPER}


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools Clock] %s' % msg, level)


def applies():
    """CoreELEC / LibreELEC, no RTC device, not switched off."""
    if os.path.exists(OFF_FLAG):
        return False
    try:
        with open('/etc/os-release', encoding='utf-8') as f:
            text = f.read().lower()
    except Exception:
        return False
    if 'coreelec' not in text and 'libreelec' not in text:
        return False
    return not glob.glob('/dev/rtc*')


def _write_if_changed(path, text, mode=None):
    try:
        with open(path, encoding='utf-8') as f:
            if f.read() == text:
                return False
    except Exception:
        pass
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(text)
    if mode is not None:
        os.chmod(tmp, mode)
    os.replace(tmp, path)
    return True


def install_unit():
    """Write the helper and the boot unit; enable it. Idempotent."""
    changed = _write_if_changed(HELPER, HELPER_SRC, 0o755)
    changed = _write_if_changed(UNIT, UNIT_SRC) or changed
    if not os.path.lexists(WANTS):
        os.makedirs(os.path.dirname(WANTS), exist_ok=True)
        os.symlink(UNIT, WANTS)
        changed = True
    if changed:
        try:
            subprocess.call(['systemctl', 'daemon-reload'], timeout=20)
            # start it now so its ExecStop saves the time at this shutdown
            subprocess.call(['systemctl', 'start', UNIT_NAME], timeout=20)
        except Exception as e:
            _log('systemctl: %s' % e, xbmc.LOGWARNING)
        _log('boot unit installed: %s' % UNIT)


def _saved():
    try:
        with open(STAMP) as f:
            return int(f.read().strip())
    except Exception:
        return 0


def save(force=False):
    """Store the clock; normally only forward (force = right after an NTP sync)."""
    now = int(time.time())
    if not (MIN_VALID < now < MAX_VALID):
        return
    if not force and now <= _saved():
        return
    try:
        os.makedirs(os.path.dirname(STAMP), exist_ok=True)
        tmp = STAMP + '.tmp'
        with open(tmp, 'w') as f:
            f.write(str(now))
        os.replace(tmp, STAMP)
    except OSError as e:
        _log('could not save the time: %s' % e, xbmc.LOGWARNING)


def sntp(server, timeout=2.0):
    """One SNTP query; returns the server's Unix time (RTT-corrected) or None."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        t0 = time.monotonic()
        s.sendto(b'\x1b' + 47 * b'\0', (server, 123))
        data, _ = s.recvfrom(512)
        rtt = time.monotonic() - t0
    except OSError:
        return None
    finally:
        s.close()
    if len(data) < 48 or (data[0] & 0x07) not in (4, 5) or data[1] == 0:
        return None                     # not a server reply / kiss-o'-death
    secs, frac = struct.unpack('!II', data[40:48])
    t = secs - NTP_EPOCH + frac / 4294967296.0 + rtt / 2.0
    return t if MIN_VALID < t < MAX_VALID else None


def sync_once():
    """Ask the servers in turn; step the clock when needed. True on success."""
    for server in NTP_SERVERS:
        t = sntp(server)
        if t is None:
            continue
        off = t - time.time()
        if abs(off) > STEP_IF_OFF:
            try:
                time.clock_settime(time.CLOCK_REALTIME, t)
                _log('clock was off by %.1f s - set from %s' % (off, server))
            except (OSError, AttributeError) as e:
                _log('could not set the clock (%s)' % e, xbmc.LOGWARNING)
                return False
        else:
            _log('clock OK (%.2f s off, %s)' % (off, server))
        save(force=True)
        return True
    return False


def _loop(monitor):
    try:
        install_unit()
    except Exception as e:
        _log('boot unit not installed: %s' % e, xbmc.LOGWARNING)
    deadline = time.monotonic() + SYNC_BUDGET
    synced = False
    while not synced and time.monotonic() < deadline:
        synced = sync_once()
        if not synced and monitor.waitForAbort(5):
            return
    if not synced:
        _log('no NTP answer in %d s - keeping the system clock' % SYNC_BUDGET)
    while not monitor.waitForAbort(SAVE_EVERY):
        save()


def start(monitor):
    if not applies():
        return False
    t = threading.Thread(target=_loop, args=(monitor,), name='abk-clock')
    t.daemon = True
    t.start()
    return True
