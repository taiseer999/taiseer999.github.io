# -*- coding: utf-8 -*-
"""
4.8.11: Update TMDb Helper Players (Patching menu).

Downloads the players pack (a .zip of TMDbHelper player .json files) from
the ABUKARIM builds index (Cloudflare worker), falling back to Google Drive,
and writes every valid player into
addon_data/plugin.video.themoviedb.helper/players/.

- Players in the pack replace files of the same name; players that are not
  in the pack (e.g. the ones AB Tools injects itself) are left alone.
- The current players folder is copied to
  addon_data/plugin.program.abukarimtools/players_backup/ first.
- Every .json is parsed before anything is written; a pack with no valid
  player changes nothing.
- The pack URL and the Drive file id can be changed without a release
  through config.json on the remote config repo ("players_url" /
  "players_drive_id").

Drive: small files download straight from drive.usercontent.google.com with
confirm=t. If Drive still answers with its HTML "can't scan for viruses"
page, the form's hidden fields (id / export / confirm / uuid) are read and
the request is sent again. The file must be shared "Anyone with the link".
"""

import io
import json
import os
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request
import zipfile

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

# Primary source: the ABUKARIM builds index (Cloudflare worker download link).
PLAYERS_URL = ('https://abukarimbuilds.tashouri.workers.dev/download.aspx'
               '?file=fHLhwWQZ7FbVCddLy2zyIjtmFpqYuxDNpBNcdvFKwMtl9EgC4s4aylqnDGtjcS3V'
               '&expiry=y8s6eHazRVGOGaDTiHiE3A%3D%3D'
               '&mac=e65c3fead77a104f1c4f54f76f020df9975df9c738899b1e2d143361a31a29ec')
# Fallback: the same pack on Google Drive.
DRIVE_FILE_ID = '1k3f8oHkIaAaPbcgmyLhGLr2W4UOi_SD3'
TMDBH_ID = 'plugin.video.themoviedb.helper'

HOME = xbmcvfs.translatePath('special://home/')
ADDON_DATA = xbmcvfs.translatePath('special://profile/addon_data/')
PLAYERS_DIR = os.path.join(ADDON_DATA, TMDBH_ID, 'players')
BACKUP_DIR = os.path.join(ADDON_DATA, 'plugin.program.abukarimtools', 'players_backup')

MAX_BYTES = 20 * 1024 * 1024        # a players pack is a few hundred KB
TIMEOUT = 30
UA = ('Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/130.0 Safari/537.36')


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools Players] %s' % msg, level)


def _players_url():
    try:
        from resources.lib import remote_config
        url = remote_config.flag('players_url')
        if url and str(url).startswith('https://'):
            return str(url)
    except Exception:
        pass
    return PLAYERS_URL


def _drive_id():
    try:
        from resources.lib import remote_config
        fid = remote_config.flag('players_drive_id')
        if fid and re.match(r'^[\w-]{10,}$', str(fid)):
            return str(fid)
    except Exception:
        pass
    return DRIVE_FILE_ID


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------
def _get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = r.read(MAX_BYTES + 1)
        ctype = r.headers.get('Content-Type', '') or ''
    if len(data) > MAX_BYTES:
        raise ValueError('file larger than %d MB' % (MAX_BYTES // 1048576))
    return data, ctype


def _confirm_url(html):
    """URL from Drive's virus-scan warning form, or None."""
    m = re.search(r'<form[^>]+action="([^"]+)"', html)
    if not m:
        return None
    action = m.group(1).replace('&amp;', '&')
    fields = dict(re.findall(r'<input[^>]+type="hidden"[^>]+name="([^"]+)"[^>]+value="([^"]*)"', html))
    if not fields:
        return None
    return action + ('&' if '?' in action else '?') + urllib.parse.urlencode(fields)


def download(file_id, first_url=None):
    """Bytes of the players zip. Tries first_url (the builds index), then
    Google Drive. Raises with a short reason."""
    urls = ([first_url] if first_url else []) + [
        'https://drive.usercontent.google.com/download?id=%s&export=download&confirm=t' % file_id,
        'https://drive.google.com/uc?export=download&id=%s' % file_id,
    ]
    last = None
    for url in urls:
        try:
            data, ctype = _get(url)
            if data[:2] == b'PK':
                return data
            if b'<html' in data[:2048].lower() or 'text/html' in ctype:
                nxt = _confirm_url(data.decode('utf-8', 'replace'))
                if nxt:
                    data, ctype = _get(nxt)
                    if data[:2] == b'PK':
                        return data
                last = ('web page instead of a zip (link expired or file not public?)')
            else:
                last = 'not a zip file'
        except urllib.error.HTTPError as e:
            last = 'HTTP %s' % e.code
        except Exception as e:
            last = str(e)
        _log('%s -> %s' % (url.split('?')[0], last), xbmc.LOGWARNING)
    raise ValueError(last or 'download failed')


# ---------------------------------------------------------------------------
# Unpack / validate
# ---------------------------------------------------------------------------
def read_players(data):
    """{filename: bytes} for every valid player .json in the zip, and the
    list of skipped names."""
    players, skipped = {}, []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            name = info.filename.replace('\\', '/')
            base = name.rsplit('/', 1)[-1]
            if (info.is_dir() or '__MACOSX/' in name or base.startswith('.')
                    or not base.lower().endswith('.json')):
                continue
            if info.file_size > 1024 * 1024:
                skipped.append(base)
                continue
            raw = z.read(info)
            try:
                obj = json.loads(raw.decode('utf-8-sig'))
                if not isinstance(obj, dict) or not obj.get('plugin'):
                    raise ValueError('no "plugin" key')
            except Exception as e:
                _log('skipped %s: %s' % (name, e), xbmc.LOGWARNING)
                skipped.append(base)
                continue
            if base in players:
                _log('duplicate %s in pack - last copy kept' % base, xbmc.LOGWARNING)
            players[base] = raw
    return players, skipped


def _backup():
    if not os.path.isdir(PLAYERS_DIR):
        return
    if os.path.isdir(BACKUP_DIR):
        shutil.rmtree(BACKUP_DIR, ignore_errors=True)
    shutil.copytree(PLAYERS_DIR, BACKUP_DIR)


def install(players):
    """Write the players. Returns (new, updated, unchanged) name lists."""
    os.makedirs(PLAYERS_DIR, exist_ok=True)
    new, updated, same = [], [], []
    for base, raw in sorted(players.items()):
        dest = os.path.join(PLAYERS_DIR, base)
        if os.path.isfile(dest):
            with open(dest, 'rb') as f:
                if f.read() == raw:
                    same.append(base)
                    continue
            updated.append(base)
        else:
            new.append(base)
        tmp = dest + '.part'
        with open(tmp, 'wb') as f:
            f.write(raw)
        os.replace(tmp, dest)
    return new, updated, same


# ---------------------------------------------------------------------------
# Menu entry
# ---------------------------------------------------------------------------
def run():
    dlg = xbmcgui.Dialog()
    if not os.path.isdir(os.path.join(HOME, 'addons', TMDBH_ID)):
        dlg.ok(T(30023), T(30030))
        return
    if not dlg.yesno(T(30023), T(30031)):
        return

    prog = xbmcgui.DialogProgress()
    prog.create(T(30023), T(30032))
    try:
        file_id = _drive_id()
        url = _players_url()
        _log('downloading players pack (%s, drive id %s)' % (url.split('?')[0], file_id))
        try:
            data = download(file_id, url)
        except Exception as e:
            _log('download failed: %s' % e, xbmc.LOGERROR)
            prog.close()
            dlg.ok(T(30023), T(30033) + '[CR][CR]' + str(e))
            return
        prog.update(60, T(30034))
        try:
            players, skipped = read_players(data)
        except zipfile.BadZipFile as e:
            players, skipped = {}, []
            _log('bad zip: %s' % e, xbmc.LOGERROR)
        if not players:
            prog.close()
            dlg.ok(T(30023), T(30035))
            return
        prog.update(80, T(30034))
        try:
            _backup()
        except Exception as e:
            _log('backup failed: %s' % e, xbmc.LOGWARNING)
        new, updated, same = install(players)
        prog.update(100)
    finally:
        prog.close()

    _log('installed: %d new %s, %d updated %s, %d unchanged, %d skipped %s'
         % (len(new), new, len(updated), updated, len(same), len(skipped), skipped))
    msg = T(30036) % (len(new), len(updated), len(same))
    if skipped:
        msg += '[CR]' + T(30037) % (len(skipped), ', '.join(skipped[:6]))
    if new or updated:
        msg += '[CR][CR]' + T(30038)
    dlg.ok(T(30023), msg)
