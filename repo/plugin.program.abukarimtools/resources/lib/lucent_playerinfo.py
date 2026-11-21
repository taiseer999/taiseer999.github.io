# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""AB Tools "AF3: Lucent Player" - the player's Statistics window (rewritten for AB Tools in 4.12.0).

Opened from OSD > Statistics, and in place of Kodi's player process info while Lucent Player is on:

    RunScript(special://home/addons/plugin.program.abukarimtools/resources/lib/lucent_playerinfo.py,open)

The window (ABK_LucentPlayerInfo.xml, in the active skin) only draws; this script reads Kodi once a second
and writes what it shows into Window(Home) properties named lucent.pi.<key>:

  overview  title, time, badges (b.*), six tiles (t1..t6), the per-core CPU meter, system meters (m.*),
            the detail rows (r.*) and a bitrate graph (spark)
  video     resolution, frame, HDR / Dolby Vision, colour, decoder, screen, video bitrate graph (v.*)
  audio     the signal path (a.c1..c5), what is heard, output, speakers (sp.*) and the audio tracks (a.t1..t4)

Meters are steps (0..40, cores 1..27): a skin cannot size a picture from a number. For the location only a
server or add-on name is shown, never the address, which can carry a login or a key.
"""
import json
import os
import re
import struct
import threading
import time
import urllib.parse
import zlib

import xbmc
import xbmcgui
import xbmcvfs

HOME = xbmcgui.Window(10000)
PREFIX = 'lucent.pi.'
ARABIC = xbmc.getLanguage(xbmc.ISO_639_1) == 'ar'
GRAPH_DIR = 'special://temp/lucent_pi/'
GRAPH_RGB = (0x7C, 0xC4, 0xFF)
METER_STEPS = 40
CORE_STEPS = 27
MAX_CORES = 8
HISTORY = 40
_LOG = '[AbukarimTools LucentPlayer] playerinfo'


def say(en, ar):
    return ar if ARABIC else en


def _log(msg):
    xbmc.log('%s: %s' % (_LOG, msg), xbmc.LOGINFO)


# ============================================================================ reading Kodi
def label(name):
    """An info label; '' where Kodi answers with the label's own name (a label it does not know)."""
    value = xbmc.getInfoLabel(name)
    return '' if value == name else (value or '')


def flag(name):
    return bool(xbmc.getCondVisibility(name))


def number(text, fallback=0.0):
    m = re.search(r'-?\d+(?:[.,]\d+)?', text or '')
    return float(m.group(0).replace(',', '.')) if m else fallback


def digits(text):
    """'48,000' / '48.000' -> 48000.0 (thousands marks dropped)."""
    only = re.sub(r'\D', '', text or '')
    return float(only) if only else 0.0


def meter(percent, steps=METER_STEPS):
    try:
        return int(max(0, min(steps, round(float(percent) / 100.0 * steps))))
    except (TypeError, ValueError):
        return 0


def joined(*parts, sep=' · '):
    return sep.join(p for p in parts if p)


def rpc(method, **params):
    try:
        out = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method,
                                                           'params': params})))
        return out.get('result') or {}
    except Exception:
        return {}


class Every(object):
    """A value fetched again only after ``seconds``."""

    def __init__(self, seconds, fetch):
        self.seconds, self.fetch = seconds, fetch
        self.at, self.value = 0.0, None

    def get(self, now, fresh=False):
        if fresh or self.value is None or now - self.at >= self.seconds:
            self.at = now
            try:
                self.value = self.fetch()
            except Exception:
                self.value = {}
        return self.value


TRACKS = Every(5, lambda: rpc('Player.GetProperties', playerid=1,
                              properties=['currentaudiostream', 'audiostreams', 'currentsubtitle',
                                          'subtitles', 'subtitleenabled']))


def _audio_settings():
    keys = ('audiooutput.audiodevice', 'audiooutput.passthroughdevice', 'audiooutput.config',
            'audiooutput.channels')
    return dict((k, rpc('Settings.GetSettingValue', setting=k).get('value')) for k in keys)


AUDIO_SETTINGS = Every(10, _audio_settings)


# ============================================================================ names
AUDIO_LONG = {
    'truehd_atmos': 'TrueHD Atmos', 'truehd': 'TrueHD', 'eac3_ddp_atmos': 'Dolby Digital+ Atmos',
    'eac3': 'Dolby Digital+', 'ac3': 'Dolby Digital', 'dtshd_ma_x_imax': 'DTS:X IMAX', 'dtshd_ma_x': 'DTS:X',
    'dtshd_ma': 'DTS-HD MA', 'dtshd_hra': 'DTS-HD HRA', 'dts': 'DTS', 'aac': 'AAC', 'flac': 'FLAC',
    'opus': 'Opus', 'mp3': 'MP3', 'mp2': 'MP2', 'vorbis': 'Vorbis', 'pcm': 'PCM',
}
AUDIO_SHORT = {
    'truehd_atmos': 'TrueHD', 'truehd': 'TrueHD', 'eac3_ddp_atmos': 'DD+', 'eac3': 'DD+', 'ac3': 'DD',
    'dtshd_ma_x_imax': 'DTS-HD MA', 'dtshd_ma_x': 'DTS-HD MA', 'dtshd_ma': 'DTS-HD MA',
    'dtshd_hra': 'DTS-HD HRA', 'dts': 'DTS', 'aac': 'AAC', 'flac': 'FLAC', 'opus': 'OPUS', 'mp3': 'MP3',
}
AUDIO_FAMILY = {
    'truehd_atmos': 'Dolby TrueHD', 'truehd': 'Dolby TrueHD', 'eac3_ddp_atmos': 'Dolby Digital+',
    'eac3': 'Dolby Digital+', 'ac3': 'Dolby Digital', 'dtshd_ma_x_imax': 'DTS:X', 'dtshd_ma_x': 'DTS:X',
    'dtshd_ma': 'DTS-HD MA', 'dtshd_hra': 'DTS-HD HRA', 'dts': 'DTS',
}
VIDEO_CODECS = {'hevc': 'HEVC', 'h264': 'H.264', 'av1': 'AV1', 'vp9': 'VP9', 'mpeg2video': 'MPEG-2', 'vc1': 'VC-1'}
CONTAINERS = {
    'mkv': 'Matroska (MKV)', 'mp4': 'MPEG-4 (MP4)', 'm4v': 'MPEG-4 (M4V)', 'ts': 'MPEG-TS',
    'm2ts': 'Blu-ray (M2TS)', 'avi': 'AVI', 'webm': 'WebM', 'mov': 'QuickTime (MOV)', 'iso': 'ISO',
    'm3u8': 'HLS (M3U8)', 'mpd': 'DASH (MPD)', 'wmv': 'WMV', 'flv': 'FLV',
}
LAYOUTS = {1: '1.0', 2: '2.0', 3: '2.1', 6: '5.1', 7: '6.1', 8: '7.1'}
SPEAKERS = {
    1: ('c',), 2: ('l', 'r'), 3: ('l', 'r', 'lfe'), 4: ('l', 'r', 'sl', 'sr'), 5: ('l', 'r', 'c', 'sl', 'sr'),
    6: ('l', 'r', 'c', 'lfe', 'sl', 'sr'), 7: ('l', 'r', 'c', 'lfe', 'sl', 'sr', 'sbl'),
    8: ('l', 'r', 'c', 'lfe', 'sl', 'sr', 'sbl', 'sbr'),
}
SPEAKER_NAMES = ('l', 'c', 'r', 'sl', 'sr', 'sbl', 'sbr', 'lfe', 'tfl', 'tfr', 'trl', 'trr')
HEIGHT_SPEAKERS = ('tfl', 'tfr', 'trl', 'trr')
OUTPUT_LAYOUTS = {0: '2.0', 1: '2.1', 2: '3.0', 3: '3.1', 4: '4.0', 5: '4.1', 6: '5.0', 7: '5.1', 8: '7.0',
                  9: '7.1', 10: '7.1'}
HDR_NAMES = {'dolbyvision': 'Dolby Vision', 'hdr10': 'HDR10', 'hdr10plus': 'HDR10+', 'hlg': 'HLG'}
HDR_BADGES = {'hdr10': 'HDR10', 'hdr10plus': 'HDR10+', 'hlg': 'HLG'}
ARABIC_LANGUAGES = {
    'ara': 'العربية', 'eng': 'الإنجليزية', 'fre': 'الفرنسية', 'fra': 'الفرنسية', 'ger': 'الألمانية',
    'deu': 'الألمانية', 'spa': 'الإسبانية', 'ita': 'الإيطالية', 'por': 'البرتغالية', 'rus': 'الروسية',
    'tur': 'التركية', 'per': 'الفارسية', 'fas': 'الفارسية', 'urd': 'الأردية', 'hin': 'الهندية',
    'jpn': 'اليابانية', 'kor': 'الكورية', 'chi': 'الصينية', 'zho': 'الصينية', 'dut': 'الهولندية',
    'nld': 'الهولندية', 'swe': 'السويدية', 'nor': 'النرويجية', 'dan': 'الدنماركية', 'fin': 'الفنلندية',
    'pol': 'البولندية', 'ukr': 'الأوكرانية', 'cze': 'التشيكية', 'ces': 'التشيكية', 'gre': 'اليونانية',
    'ell': 'اليونانية', 'hun': 'المجرية', 'heb': 'العبرية', 'tha': 'التايلاندية', 'vie': 'الفيتنامية',
    'ind': 'الإندونيسية', 'may': 'الملايوية', 'msa': 'الملايوية',
}
_DV2 = re.compile(r'(?i)(?<![a-z0-9])(?:dv2|dovi[ ._-]?2|dolby[ ._-]?vision[ ._-]?2)(?![a-z0-9])')
_DV_PROFILE = re.compile(r'(?i)(?<![a-z0-9])(?:dv|dovi)?[ ._-]?p([578])(?:[ ._]\d)?(?![0-9a-z])')
_DV_LAYER = re.compile(r'(?i)(?<![a-z0-9])(fel|mel)(?![a-z0-9])')


def language(code):
    code = (code or '').strip().lower()
    if not code or code in ('und', 'unk', 'unknown'):
        return ''
    if ARABIC and code in ARABIC_LANGUAGES:
        return ARABIC_LANGUAGES[code]
    try:
        return xbmc.convertLanguage(code, xbmc.ENGLISH_NAME) or code.upper()
    except Exception:
        return code.upper()


def language_tag(code):
    try:
        short = xbmc.convertLanguage(code or '', xbmc.ISO_639_1)
    except Exception:
        short = ''
    return (short or code or '').upper()[:3]


def channel_count(n):
    if n == 1:
        return say('1 channel', 'قناة واحدة')
    return say('%d channels' % n, '%d قنوات' % n)


def shorten(name, room=64):
    """A long file name with its middle taken out."""
    if len(name) <= room:
        return name
    front = int(room * 0.55)
    back = room - front - 3
    return '%s … %s' % (name[:front].rstrip('.'), name[-back:].lstrip('.'))


def where_from(path):
    """The server, add-on or 'this device' a video comes from - never the address itself."""
    if not path:
        return ''
    if path.startswith('plugin://'):
        addon_id = urllib.parse.urlparse(path).netloc
        try:
            import xbmcaddon
            return xbmcaddon.Addon(addon_id).getAddonInfo('name')
        except Exception:
            return addon_id
    parts = urllib.parse.urlparse(path)
    if parts.scheme in ('http', 'https', 'rtmp', 'rtsp', 'udp', 'rtp', 'mms'):
        host = (parts.hostname or '').lower()
        return host[4:] if host.startswith('www.') else host
    if parts.scheme in ('smb', 'nfs', 'ftp', 'sftp', 'dav', 'davs'):
        return joined(parts.hostname or '', parts.scheme.upper())
    return say('this device', 'هذا الجهاز')


def file_size(path):
    if not path or ('://' in path and not path.startswith(('smb://', 'nfs://', 'special://'))):
        return ''
    try:
        size = xbmcvfs.Stat(path).st_size()
    except Exception:
        return ''
    if not size:
        return ''
    if size >= 1 << 30:
        return '%.1f GB' % (size / float(1 << 30))
    return '%d MB' % round(size / float(1 << 20))


def bit_depth(hdr='', detail='', layer=''):
    """Video bit depth (0 when unknown): Kodi 22's video.bitdepth, else the (Amlogic) pixel format.
    PQ / HLG / Dolby Vision pictures are 10-bit at least, and a Dolby Vision FEL stream is 12-bit."""
    depth = 0
    m = re.search(r'\d+', label('Player.Process(video.bitdepth)'))
    if m:
        depth = int(m.group(0))
    if not depth:
        for name in ('Player.Process(amlogic.pixformat)', 'Player.Process(pixformat)'):
            fmt = label(name).lower()
            m = (re.search(r'\b(8|10|12)\s*-?\s*bit', fmt) or re.search(r'p0?(10|12|16)(?:le|be)?\b', fmt)
                 or re.search(r'yuv\w*?(10|12)(?:le|be)?\b', fmt))
            if m:
                depth = min(int(m.group(1)), 12) if m.group(1) != '16' else 10
                break
            if re.search(r'\b(?:nv12|yuv420p|yuvj420p|rgb24|bgra|8bit)\b', fmt):
                depth = 8
                break
    kind = (hdr or '').lower()
    if kind in ('hdr10', 'hdr10plus', 'hlg', 'dolbyvision'):
        depth = max(depth, 10)
    if kind == 'dolbyvision' and 'FEL' in ('%s%s' % (layer or '', detail or '')).upper():
        depth = max(depth, 12)
    return depth


def dolby_vision_from_name(name):
    name = name or ''
    profile = _DV_PROFILE.search(name)
    layer = _DV_LAYER.search(name)
    return {'dv2': bool(_DV2.search(name)), 'profile': profile.group(1) if profile else '',
            'layer': layer.group(1).upper() if layer else ''}


def kodi_volume():
    got = rpc('Application.GetProperties', properties=['volume', 'muted'])
    if 'volume' in got:
        return got.get('volume'), bool(got.get('muted'))
    return None, flag('Player.Muted')


def device_name(raw):
    """'ALSA:hdmi:CARD=PCH,DEV=0|HDA Intel PCH, HDMI 0' -> 'HDA Intel PCH, HDMI 0'."""
    raw = str(raw or '')
    if '|' in raw:
        raw = raw.split('|', 1)[1]
    elif ':' in raw:
        raw = raw.split(':', 1)[1]
    return raw.strip()


# ============================================================================ the bitrate graphs
def _png(width, height, pixels):
    """RGBA rows -> PNG bytes."""
    data = b''.join(b'\x00' + bytes(row) for row in pixels)

    def block(kind, body):
        return (struct.pack('>I', len(body)) + kind + body
                + struct.pack('>I', zlib.crc32(kind + body) & 0xFFFFFFFF))
    return (b'\x89PNG\r\n\x1a\n'
            + block(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
            + block(b'IDAT', zlib.compress(data, 6)) + block(b'IEND', b''))


class Graph(object):
    """A line with a soft fill under it, of the last HISTORY values, saved as a fresh PNG each time
    (Kodi caches a picture by its name)."""
    _serial = [0]

    def __init__(self, tag, width, height):
        self.tag, self.width, self.height = tag, width, height

    def draw(self, values):
        values = list(values)[-HISTORY:]
        if len(values) < 2:
            return ''
        w, h = self.width, self.height
        low, high = min(values), max(values)
        spread = (high - low) or max(high, 1.0)
        flat = high == low
        line = []
        last = len(values) - 1
        for x in range(w):
            at = x * last / float(w - 1)
            i = min(int(at), last - 1)
            v = values[i] + (values[i + 1] - values[i]) * (at - i)
            y = (h - 4) - (v - low) / spread * (h - 12)
            line.append(y - (h * 0.1 if flat else 0))
        r, g, b = GRAPH_RGB
        solid, soft = bytes((r, g, b, 255)), bytes((r, g, b, 46))
        rows = [bytearray(w * 4) for _ in range(h)]
        for x in range(w):
            y_here = line[x]
            y_prev = line[x - 1] if x else y_here
            top = min(y_here, y_prev) - 2.5
            bottom = max(y_here, y_prev) + 2.5
            for y in range(max(0, int(top)), h):
                if y < top:
                    continue
                rows[y][x * 4:x * 4 + 4] = solid if y <= bottom else soft
        return self._save(_png(w, h, rows))

    def _save(self, data):
        folder = xbmcvfs.translatePath(GRAPH_DIR)
        os.makedirs(folder, exist_ok=True)
        Graph._serial[0] += 1
        name = '%s_%d_%d.png' % (self.tag, int(time.time()), Graph._serial[0])
        with open(os.path.join(folder, name), 'wb') as fh:
            fh.write(data)
        for old in os.listdir(folder):
            if old != name and old.startswith(self.tag + '_'):
                try:
                    if time.time() - os.path.getmtime(os.path.join(folder, old)) > 4:
                        os.remove(os.path.join(folder, old))
                except OSError:
                    pass
        return GRAPH_DIR + name


TOTAL_GRAPH = Graph('spark', 760, 60)
VIDEO_GRAPH = Graph('vspark', 940, 120)


# ============================================================================ state between ticks
class State(object):
    def __init__(self):
        self.reset(None)
        self.max_clock = 0.0
        self.shown = False

    def reset(self, path):
        self.path = path
        self.total_rates = []
        self.video_rates = []
        self.video_peak = 0.0
        self.size = file_size(path) if path else ''
        TRACKS.at = 0.0


STATE = State()


def write(values):
    for key, value in values.items():
        value = '' if value is None else str(value)
        if HOME.getProperty(PREFIX + key) != value:
            HOME.setProperty(PREFIX + key, value)


# ============================================================================ one reading
class Reading(object):
    """Everything the three pages need, read from Kodi once."""

    def __init__(self, now):
        self.now = now
        self.path = label('Player.Filenameandpath')
        self.filename = label('Player.Filename')
        # video
        self.width = re.sub(r'[,.]', '', label('Player.Process(videowidth)'))
        self.height = re.sub(r'[,.]', '', label('Player.Process(videoheight)'))
        self.fps = label('Player.Process(videofps)')
        res = label('VideoPlayer.VideoResolution')
        self.res = {'8K': '8K', '4K': '4K', '1080': '1080p', '720': '720p', '576': '576p', '540': '540p',
                    '480': '480p'}.get(res, res.upper())
        self.hdr = label('VideoPlayer.HdrType').lower()
        self.hdr_detail = label('VideoPlayer.HdrDetail')
        m = re.search(r'(\d+)', self.hdr_detail)
        self.dv_profile = m.group(1) if (m and self.hdr == 'dolbyvision') else ''
        up = self.hdr_detail.upper()
        self.dv_layer = 'FEL' if 'FEL' in up else ('MEL' if 'MEL' in up else '')
        self.pixfmt = label('Player.Process(pixformat)')
        self.bits = bit_depth(self.hdr, self.hdr_detail, self.dv_layer)
        codec = label('VideoPlayer.VideoCodec').lower()
        self.vcodec = VIDEO_CODECS.get(codec, codec.upper())
        self.dv_name = (dolby_vision_from_name('%s %s' % (self.filename, self.path))
                        if self.hdr == 'dolbyvision' else {})
        self.hdr_name = HDR_NAMES.get(self.hdr, '')
        scan = label('Player.Process(videoscantype)').lower()
        self.scan = (say('progressive', 'تدريجي') if scan.startswith('p')
                     else say('interlaced', 'متشابك') if scan.startswith('i') else '')
        self.dar = label('Player.Process(videodar)')
        self.vdecoder = label('Player.Process(videodecoder)')
        self.hw = flag('Player.Process(videohwdecoder)')
        self.screen = label('System.ScreenResolution')
        self.render_fps = number(label('System.FPS'))
        # audio
        self.acodec = label('VideoPlayer.AudioCodec').lower()
        try:
            self.channels = int(label('VideoPlayer.AudioChannels') or 0)
        except ValueError:
            self.channels = 0
        self.layout = LAYOUTS.get(self.channels, ('%d.0' % self.channels) if self.channels else '')
        self.aname = label('VideoPlayer.AudioName')
        low = self.aname.lower()
        self.atmos = 'atmos' in self.acodec or 'atmos' in low
        self.dtsx = self.acodec.startswith('dtshd_ma_x') or 'dts:x' in low or 'dts-x' in low
        self.immersive = self.atmos or self.dtsx
        self.alabel = AUDIO_LONG.get(self.acodec, self.acodec.upper())
        if self.atmos and 'Atmos' not in self.alabel:
            self.alabel += ' Atmos'
        self.ashort = AUDIO_SHORT.get(self.acodec, self.acodec.upper())
        self.rate = digits(label('Player.Process(audiosamplerate)'))
        self.khz = ('%g kHz' % (self.rate / 1000.0)) if self.rate else ''
        abits = label('Player.Process(audiobitspersample)')
        self.abits = abits if abits and abits != '0' else ''
        adec = label('Player.Process(audiodecoder)')
        self.adecoder = '' if adec.lower() in ('unknown', 'none') else adec
        self.passthrough = self.adecoder.lower().startswith('pt-')
        self.aqueue = number(label('Player.Process(audioqueuelevel)'))
        self.vqueue = number(label('Player.Process(videoqueuelevel)'))
        # rates and buffer
        self.vrate = number(label('Player.Process(videolivebitrate)'))
        self.arate = digits(label('Player.Process(audiolivebitrate)')) / 1024.0
        self.total_rate = self.vrate + self.arate
        self.cache = number(label('Player.CacheLevel'))
        self.ahead = self._ahead()
        self.stream = flag('Player.IsInternetStream')
        self.tracks = TRACKS.get(now) or {}

    @staticmethod
    def _ahead():
        try:
            total = xbmc.Player().getTotalTime()
        except Exception:
            return ''
        done, cached = number(label('Player.Progress')), number(label('Player.ProgressCache'))
        if not total or cached <= done:
            return ''
        secs = int((cached - done) / 100.0 * total)
        if secs < 600:
            return say('%d s buffered' % secs, '%d ثانية في المخزن المؤقت' % secs)
        return say('%d min buffered' % (secs // 60), '%d دقيقة في المخزن المؤقت' % (secs // 60))


def _rates_text(r):
    return say('%.1f Mb/s · video %.1f · audio %.1f' % (r.total_rate, r.vrate, r.arate),
               '%.1f Mb/s · الفيديو %.1f · الصوت %.1f' % (r.total_rate, r.vrate, r.arate))


def _dv_badge(r, upper=True):
    name = 'DOLBY VISION 2' if r.dv_name.get('dv2') else 'DOLBY VISION'
    return name if upper else name.title()


def _profile_text(r, key='profile'):
    if not r.dv_profile:
        return ''
    word = say('profile ', 'الملف ') if key == 'profile' else say('PROFILE ', 'الملف ')
    return word + r.dv_profile + ((' ' + r.dv_layer) if r.dv_layer else '')


# ---------------------------------------------------------------------------- page 1: overview
def overview(r):
    out = {}
    show = label('VideoPlayer.TVShowTitle')
    title = label('VideoPlayer.Title')
    if show:
        season, episode = label('VideoPlayer.Season'), label('VideoPlayer.Episode')
        out['title'] = joined(show, ('S%s E%s' % (season, episode)) if season and episode else '', title)
    else:
        year = label('VideoPlayer.Year')
        out['title'] = ('%s (%s)' % (title, year)) if (title and year) else (title or r.filename)
    clock = label('Player.Time')
    duration = label('Player.Duration')
    text = ('%s / %s' % (clock, duration)) if duration else clock
    try:
        chapter, chapters = int(label('Player.Chapter') or 0), int(label('Player.ChapterCount') or 0)
    except ValueError:
        chapter = chapters = 0
    if chapter and chapters > 1:
        text += say(' · chapter %d of %d' % (chapter, chapters), ' · الفصل %d من %d' % (chapter, chapters))
    out['time'] = text

    # badges
    out['b.res'] = r.res
    if r.hdr == 'dolbyvision':
        out['b.dv'] = joined(_dv_badge(r), ('P' + r.dv_profile) if r.dv_profile else '', r.dv_layer, sep=' ')
        out['b.hdr'] = ''
    else:
        out['b.dv'] = ''
        out['b.hdr'] = HDR_BADGES.get(r.hdr, '')
    out['b.vc'] = ('%s %d-bit' % (r.vcodec, r.bits)) if (r.vcodec and r.bits >= 10) else r.vcodec
    out['b.remux'] = 'REMUX' if re.search(r'remux', r.filename, re.I) else ''
    out['b.ac'] = r.ashort
    out['b.imm'] = (('ATMOS %s' % r.layout) if r.atmos else ('DTS:X %s' % r.layout) if r.dtsx else '').strip()
    out['b.ch'] = '' if r.immersive else r.layout
    sub_lang = label('VideoPlayer.SubtitlesLanguage')
    out['b.sub'] = (say('%s subtitles' % language_tag(sub_lang), 'ترجمة %s' % language_tag(sub_lang))
                    if (flag('VideoPlayer.SubtitlesEnabled') and sub_lang) else '')

    # tiles
    out['t1.big'] = ('%s HDR' % r.res) if r.hdr_name else r.res
    out['t1.sub'] = joined(('%s×%s' % (r.width, r.height)) if (r.width and r.height) else '', r.fps)
    out['t2.big'] = r.hdr_name or 'SDR'
    out['t2.sub'] = _profile_text(r)
    if r.atmos:
        big = 'Atmos %s' % r.layout
    elif r.dtsx:
        big = 'DTS:X %s' % r.layout
    else:
        big = r.layout or r.alabel
    out['t3.big'] = big.strip()
    out['t3.sub'] = joined(AUDIO_SHORT.get(r.acodec, r.alabel) if (r.immersive or r.layout) else '', r.khz)
    if r.total_rate:
        STATE.total_rates = (STATE.total_rates + [r.total_rate])[-HISTORY:]
    out['t4.big'] = ('%.1f Mb/s' % r.total_rate) if r.total_rate else '–'
    out['t4.sub'] = (say('video %.1f · audio %.1f' % (r.vrate, r.arate), 'الفيديو %.1f · الصوت %.1f' % (r.vrate, r.arate))
                     if r.total_rate else '')
    if len(STATE.total_rates) >= 2:
        try:
            out['spark'] = TOTAL_GRAPH.draw(STATE.total_rates)
        except Exception as e:
            _log('graph: %s' % e)
    out['t5.big'] = '%d%%' % round(r.cache)
    out['t5.sub'] = r.ahead
    out['t5.bar'] = meter(r.cache)

    # system
    cpu = label('System.CpuUsage').replace(',', '.')
    per_core = [float(v) for v in re.findall(r'#\d+:\s*([\d.]+)%', cpu)]
    average = (sum(per_core) / len(per_core)) if per_core else number(cpu)
    out['cores'] = min(len(per_core), MAX_CORES)
    for n in range(MAX_CORES):
        out['core%d' % n] = max(1, meter(per_core[n], CORE_STEPS)) if n < len(per_core) else ''
    out['cores.label'] = (say('CPU per core · average %d%%' % round(average), 'المعالج لكل نواة · المتوسط %d%%' % round(average))
                          if per_core else 'CPU · %d%%' % round(average))
    cpu_temp, gpu_temp = number(label('System.CPUTemperature'), -1), number(label('System.GPUTemperature'), -1)
    mem = number(label('System.Memory(used.percent)'))
    mem_used = re.sub(r'\s+', ' ', label('System.Memory(used)').replace('MB', ' MB').replace('GB', ' GB')).strip()
    out['t6.big'] = 'CPU %d%%' % round(average)
    out['t6.sub'] = joined(('%d °C' % round(cpu_temp)) if cpu_temp >= 0 else '',
                           say('%d%% memory' % round(mem), '%d%% من الذاكرة' % round(mem)))
    out['t6.bar'] = meter(mem)
    out['m.ct'] = ('%d °C' % round(cpu_temp)) if cpu_temp >= 0 else '–'
    out['m.ct.bar'] = meter(cpu_temp) if cpu_temp >= 0 else 0
    out['m.gt'] = ('%d °C' % round(gpu_temp)) if gpu_temp >= 0 else '–'
    out['m.gt.bar'] = meter(gpu_temp) if gpu_temp >= 0 else 0
    out['m.mem'] = joined('%d%%' % round(mem), mem_used)
    out['m.mem.bar'] = meter(mem)
    clock_mhz = number(label('System.CpuFrequency'))
    if not STATE.max_clock:
        try:
            with open('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq') as fh:
                STATE.max_clock = int(fh.read().strip()) / 1000.0
        except (OSError, ValueError):
            STATE.max_clock = 0.0
    STATE.max_clock = max(STATE.max_clock, clock_mhz)
    out['m.clk'] = ('%d MHz' % round(clock_mhz)) if clock_mhz else '–'
    out['m.clk.bar'] = meter(clock_mhz / STATE.max_clock * 100) if (clock_mhz and STATE.max_clock) else 0
    video_fps = number(r.fps)
    out['m.fps'] = ('%.2f fps' % r.render_fps) if r.render_fps else '–'
    out['m.fps.bar'] = meter(min(100.0, r.render_fps / video_fps * 100)) if (r.render_fps and video_fps) else 0
    out['m.vq'] = '%d%%' % round(r.vqueue)
    out['m.vq.bar'] = meter(r.vqueue)

    # rows: source
    out['r.file'] = shorten(r.filename)
    origin = where_from(r.path)
    out['r.loc'] = joined(origin, say('stream', 'بث')) if (r.stream and origin) else origin
    ext = os.path.splitext(urllib.parse.urlparse(r.filename).path)[1].lower().lstrip('.')
    out['r.cont'] = joined(CONTAINERS.get(ext, ext.upper()), STATE.size)
    out['r.rate'] = _rates_text(r) if r.total_rate else '–'
    # rows: video
    out['r.res'] = joined(('%s×%s' % (r.width, r.height)) if (r.width and r.height) else '',
                          ('%s fps' % r.fps) if r.fps else '', r.scan)
    if r.hdr == 'dolbyvision':
        out['r.hdr'] = joined('Dolby Vision', _profile_text(r), 'BT.2020')
    elif r.hdr_name:
        out['r.hdr'] = joined(r.hdr_name, 'BT.2020')
    else:
        out['r.hdr'] = 'SDR'
    out['r.fmt'] = joined(r.pixfmt, ('%s:1' % r.dar) if r.dar else '')
    out['r.vdec'] = joined(r.vdecoder, 'hardware' if r.hw else 'software')
    screen = re.sub(r'(\d)\s*x\s*(\d)', r'\1×\2', r.screen).replace(' - ', ' · ')
    out['r.disp'] = re.sub(r'(\d)Hz', r'\1 Hz', screen)
    out['r.vq'] = '%d%%' % round(r.vqueue)
    out['r.vq.dot'] = 'low' if r.vqueue <= 20 else 'ok'
    # rows: audio
    streams = r.tracks.get('audiostreams') or []
    current = r.tracks.get('currentaudiostream') or {}
    pos = next((n for n, s in enumerate(streams, 1) if s.get('index') == current.get('index')), 0)
    out['r.atrack'] = joined(say('%d of %d' % (pos, len(streams)), '%d من %d' % (pos, len(streams)))
                             if (pos and len(streams) > 1) else '',
                             language(current.get('language') or label('VideoPlayer.AudioLanguage')),
                             current.get('name') or r.aname)
    out['r.afmt'] = joined(r.alabel, ('%s (%s)' % (channel_count(r.channels), r.layout)) if r.channels else '')
    out['r.aq'] = joined(r.khz, ('%s bit' % r.abits) if r.abits else '')
    out['r.adec'] = (r.adecoder + say(' · passed through to the receiver', ' · يُمرَّر كما هو إلى جهاز الاستقبال')
                     if r.passthrough else r.adecoder)
    out['r.aqueue'] = '%d%%' % round(r.aqueue)
    out['r.aqueue.dot'] = 'low' if r.aqueue <= 20 else 'ok'
    # rows: subtitles
    subs = r.tracks.get('subtitles') or []
    sub = r.tracks.get('currentsubtitle') or {}
    if r.tracks.get('subtitleenabled') and sub:
        spos = next((n for n, s in enumerate(subs, 1) if s.get('index') == sub.get('index')), 0)
        out['r.sub'] = joined(language(sub.get('language')) or sub.get('name'),
                              (sub.get('codec') or '').upper().replace('SUBRIP', 'SRT'),
                              say('%d of %d' % (spos, len(subs)), '%d من %d' % (spos, len(subs))) if spos else '')
    else:
        out['r.sub'] = say('Off', 'متوقفة') + (say(' · %d available' % len(subs), ' · %d متاحة' % len(subs))
                                               if subs else '')
    # rows: network
    out['r.buf'] = joined('%d%%' % round(r.cache), r.ahead)
    out['r.buf.dot'] = 'low' if r.cache <= 20 else 'ok'
    out['r.type'] = say('Stream · internet', 'بث · عبر الإنترنت') if r.stream else say('Local file', 'ملف محلي')
    return out


# ---------------------------------------------------------------------------- page 2: video
def _white(text):
    return '[COLOR FFFFFFFF][B]%s[/B][/COLOR]' % text


def video_page(r):
    out = {}
    try:
        width = int(r.width or 0)
    except ValueError:
        width = 0
    box = '4k' if width >= 3000 else ('1080' if width >= 1200 else 'sd')
    out['v.resbox'] = box
    out['v.reslabel'] = joined(r.res, ('%s×%s' % (r.width, r.height)) if (r.width and r.height) else '')
    out['v.resshort'] = r.res
    out['v.resnote'] = {'4k': say('four times the pixels of Full HD', 'أربعة أضعاف بكسلات Full HD'),
                        '1080': 'Full HD' if width >= 1900 else 'HD',
                        'sd': say('standard definition', 'دقة قياسية')}[box]
    ratio_name = ''
    try:
        ratio = float(r.dar.replace(',', '.'))
        if abs(ratio - 1.78) < 0.02:
            ratio_name = '16:9'
        elif abs(ratio - 1.33) < 0.02:
            ratio_name = '4:3'
        elif 2.3 < ratio < 2.45:
            ratio_name = '21:9'
    except ValueError:
        pass
    out['v.dar'] = (('%s:1' % r.dar) + ((' (%s)' % ratio_name) if ratio_name else '')) if r.dar else '–'
    out['v.fps'] = ('%s fps' % r.fps) if r.fps else '–'
    out['v.scan'] = r.scan or '–'
    deint = label('Player.Process(deintmethod)')
    out['v.deint'] = deint if (deint and deint.lower() not in ('none', 'unknown')) else say('not needed', 'غير مطلوب')
    kind = 'dv' if r.hdr == 'dolbyvision' else ('hdr10' if r.hdr in ('hdr10', 'hdr10plus', 'hlg') else 'sdr')
    out['v.hdrbar'] = kind
    out['v.hb.dv'] = _dv_badge(r) if r.hdr == 'dolbyvision' else ''
    out['v.hb.hdr'] = HDR_BADGES.get(r.hdr, '')
    out['v.hb.sdr'] = 'SDR' if kind == 'sdr' else ''
    out['v.hb2'] = _profile_text(r, 'PROFILE')
    out.update(_dolby_vision_row(r))
    wide = kind != 'sdr'
    out['v.gamut'] = '2020' if wide else '709'
    out['v.c1'] = say('Colours: ', 'الألوان: ') + _white('BT.2020' if wide else 'BT.709')
    transfer = {'dolbyvision': 'PQ', 'hdr10': 'PQ', 'hdr10plus': 'PQ', 'hlg': 'HLG'}.get(r.hdr, 'SDR (gamma)')
    out['v.c2'] = say('Transfer: ', 'منحنى النقل: ') + _white(transfer)
    bits = r.bits or (10 if wide else 8)
    if bits >= 12:
        colours = say('68.7 billion colours', '68.7 مليار لون')
    elif bits == 10:
        colours = say('1.07 billion colours', '1.07 مليار لون')
    else:
        colours = say('16.7 million colours', '16.7 مليون لون')
    out['v.c3'] = '%s · %s' % (_white('%d-bit' % bits), colours)
    out['v.p1k'] = say('File', 'الملف')
    out['v.p1'] = ('%s %d-bit' % (r.vcodec, bits)) if (r.vcodec and r.bits >= 10) else (r.vcodec or '–')
    out['v.p1s'] = r.pixfmt
    out['v.p2k'] = say('Decoder', 'فك الترميز')
    out['v.p2'] = r.vdecoder or '–'
    out['v.p2s'] = 'hardware ✓' if r.hw else 'software'
    out['v.p3k'] = say('Picture', 'الصورة')
    out['v.p3'] = ('%.2f fps' % r.render_fps) if r.render_fps else '–'
    out['v.p3s'] = say('drawn each second', 'إطارًا يُرسم كل ثانية')
    size = re.search(r'(\d+)\s*x\s*(\d+)', r.screen)
    hz_m = re.search(r'@\s*([\d.,]+)', r.screen)
    hz = number(hz_m.group(1)) if hz_m else 0.0
    video_fps = number(r.fps)
    out['v.p4k'] = say('TV', 'الشاشة')
    out['v.p4'] = ('%s×%s' % size.groups()) if size else r.screen
    matched = bool(hz and video_fps and any(abs(hz - video_fps * k) < 0.05 for k in (1, 2)))
    out['v.p4s'] = (('@ %.2f Hz' % hz) + (' ✓' if matched else '')) if hz else ''
    if r.vrate:
        STATE.video_rates = (STATE.video_rates + [r.vrate])[-HISTORY:]
        STATE.video_peak = max(STATE.video_peak, r.vrate)
    out['v.br'] = ('%.1f Mb/s' % r.vrate) if r.vrate else '–'
    out['v.peak'] = (say('peak %.1f' % STATE.video_peak, 'الذروة %.1f' % STATE.video_peak)
                     if STATE.video_peak else '')
    if len(STATE.video_rates) >= 2:
        out['v.spark'] = VIDEO_GRAPH.draw(STATE.video_rates)
    return out


def _dolby_vision_row(r):
    if r.hdr != 'dolbyvision':
        return {'v.dv.on': ''}
    dvn = r.dv_name
    from_kodi = 'Dolby Vision' + ((' · ' + _profile_text(r)) if r.dv_profile else '')
    named = joined(('P%s' % dvn['profile'] + ((' ' + dvn['layer']) if dvn.get('layer') else '')) if dvn.get('profile')
                   else dvn.get('layer', ''), 'DV2' if dvn.get('dv2') else '') or say('nothing more', 'لا شيء إضافي')
    supported = label('System.SupportedHDRTypes').lower()
    if 'dolby' in supported:
        screen = 'Dolby Vision ✓'
    elif supported:
        screen = say('no Dolby Vision reported', 'لم يُبلَّغ عن Dolby Vision')
    else:
        screen = say('not reported', 'لم يُبلَّغ عنه')
    line = '   ·   '.join(('Kodi: ' + _white(from_kodi),
                           say('File name: ', 'اسم الملف: ') + _white(named),
                           say('Box + TV: ', 'الجهاز + الشاشة: ') + _white(screen)))
    if dvn.get('dv2'):
        note = say('The release is marked Dolby Vision 2: a Dolby Vision 2 TV uses the extra data it carries.',
                   'الإصدار موسوم بـ Dolby Vision 2: يستعمل التلفاز الداعم لـ Dolby Vision 2 البيانات الإضافية التي يحملها.')
    else:
        note = say('A Dolby Vision 2 TV applies its own newer picture processing to this Dolby Vision picture.',
                   'يطبّق التلفاز الداعم لـ Dolby Vision 2 معالجته الأحدث للصورة على صورة Dolby Vision هذه.')
    return {'v.dv.on': '1', 'v.dv.line': line, 'v.dv.note': note}


# ---------------------------------------------------------------------------- page 3: audio
def audio_page(r):
    out = {}
    cfg = AUDIO_SETTINGS.get(r.now) or {}
    family = AUDIO_FAMILY.get(r.acodec, r.alabel.replace(' Atmos', ''))
    lossless = r.acodec.startswith(('truehd', 'dtshd_ma', 'flac', 'pcm'))
    plus_height = say(' + height', ' + الارتفاع')
    # the path of the sound
    out['a.c1k'] = say('File', 'الملف')
    out['a.c1'] = r.ashort + (' Atmos' if r.atmos else '')
    if r.immersive and r.layout:
        out['a.c1s'] = '%s + %s' % (r.layout, say('objects', 'كائنات صوتية'))
    else:
        out['a.c1s'] = channel_count(r.channels) if r.channels else ''
    out['a.c2k'] = 'Kodi'
    out['a.c2'] = 'passthrough' if r.passthrough else say('decodes it', 'يفك ترميزه بنفسه')
    out['a.c2s'] = say('untouched ✓', 'دون تعديل ✓') if r.passthrough else r.adecoder
    out['a.c3k'] = 'HDMI' if r.passthrough else say('Out', 'الخرج')
    out['a.c3'] = say('bitstream', 'تمرير مباشر') if r.passthrough else 'PCM'
    out['a.c3s'] = joined(r.khz, ('%s bit' % r.abits) if r.abits else '')
    device = device_name(cfg.get('audiooutput.passthroughdevice') if r.passthrough else cfg.get('audiooutput.audiodevice'))
    out['a.c4k'] = say('Receiver', 'جهاز الاستقبال') if r.passthrough else say('Device', 'الجهاز')
    out['a.c4'] = device or '–'
    if r.passthrough:
        out['a.c4s'] = (say('decodes Atmos', 'يفك ترميز Atmos') if r.atmos
                        else say('decodes DTS:X', 'يفك ترميز DTS:X') if r.dtsx else say('decodes', 'يفك الترميز'))
    else:
        out['a.c4s'] = say('plays', 'يُشغِّل')
    chosen = cfg.get('audiooutput.channels')
    out_layout = OUTPUT_LAYOUTS.get(chosen if isinstance(chosen, int) else -1, '')
    extra = ' + Atmos' if r.atmos else (' + DTS:X' if r.dtsx else '')
    out['a.c5k'] = say('Speakers', 'مكبرات الصوت')
    out['a.c5'] = (r.layout or out_layout) + extra
    out['a.c5s'] = (channel_count(r.channels) + (plus_height if r.immersive else '')) if r.channels else ''
    # what is heard
    out['a.h1'] = family
    out['a.h2'] = 'Atmos' if r.atmos else ''
    out['a.hs'] = joined((r.layout + plus_height) if (r.immersive and r.layout) else r.layout, r.khz,
                         say('%s bit' % r.abits, '%s بت' % r.abits) if r.abits else '',
                         say('lossless', 'بلا فقد') if lossless else '')
    # output
    mode = {1: say('Fixed', 'ثابت'), 2: say('Best match', 'أفضل تطابق'),
            3: say('Optimised', 'مُحسَّن')}.get(cfg.get('audiooutput.config'), '')
    out['a.dev'] = (('HDMI · ' if (r.passthrough and device and 'hdmi' not in device.lower()) else '')
                    + (device or '–'))
    out['a.cfg'] = joined(mode, out_layout) or '–'
    volume, muted = kodi_volume()
    volume_text = ('%s%%' % volume) if volume is not None else label('Player.Volume')
    delay = ''
    try:
        ms = int(round(float(label('Player.AudioDelay').split()[0].replace(',', '.')) * 1000))
        delay = say('delay %d ms' % ms, 'تأخير %d ms' % ms) if ms else say('no delay', 'دون تأخير')
    except (ValueError, IndexError):
        pass
    out['a.vol'] = joined(say('muted', 'مكتوم') if muted else volume_text, delay) or '–'
    out['r.aqueue2'] = '%d%%' % round(r.aqueue)
    out['r.aqueue2.bar'] = meter(r.aqueue)
    # the speakers this track uses
    active = set(SPEAKERS.get(r.channels, SPEAKERS[8] if r.channels > 8 else ()))
    if r.immersive:
        active.update(HEIGHT_SPEAKERS)
    for name in SPEAKER_NAMES:
        out['sp.' + name] = '1' if name in active else ''
    out['a.roomlabel'] = say('Your room', 'غرفتك') + ((' · ' + r.layout + extra) if r.layout else '')
    out['a.chlabel'] = (say('Channels', 'القنوات') + ((' · ' + r.layout) if r.layout else '')
                        + (say(' + 4 height', ' + 4 للارتفاع') if r.immersive else ''))
    # the audio tracks (four shown)
    streams = r.tracks.get('audiostreams') or []
    current = (r.tracks.get('currentaudiostream') or {}).get('index')
    out['a.tlabel'] = '%s · %d' % (say('Audio tracks', 'المسارات الصوتية'), len(streams))
    for n in range(1, 5):
        s = streams[n - 1] if n <= len(streams) else None
        key = 'a.t%d.' % n
        if not s:
            for part in ('lang', 'codec', 'sub', 'on'):
                out[key + part] = ''
            continue
        codec = (s.get('codec') or '').lower()
        out[key + 'lang'] = language(s.get('language')) or say('Unknown', 'غير معروفة')
        out[key + 'codec'] = AUDIO_LONG.get(codec, codec.upper()) or '–'
        out[key + 'sub'] = joined(LAYOUTS.get(s.get('channels') or 0, ''), s.get('name') or '')
        out[key + 'on'] = '1' if s.get('index') == current else ''
    return out


# ============================================================================ the update
def is_open():
    return bool(HOME.getProperty(PREFIX + 'open')) and flag('Player.HasVideo')


def tick():
    if not is_open():
        if STATE.shown:
            STATE.shown = False
            STATE.reset(STATE.path)
        return
    STATE.shown = True
    now = time.time()
    path = label('Player.Filenameandpath')
    if path != STATE.path:
        STATE.reset(path)
    r = Reading(now)
    for page in (overview, video_page, audio_page):
        try:
            write(page(r))
        except Exception as e:
            _log('%s: %s' % (page.__name__, e))


# Back, close, Info, context and the remote's stop/menu keys close the window
CLOSE_ACTIONS = (9, 10, 11, 92, 216, 247, 257, 275, 61448, 61467)


class StatsWindow(xbmcgui.WindowXMLDialog):

    def onInit(self):
        self.done = False
        HOME.setProperty(PREFIX + 'tab', '1')
        try:
            self.setFocusId(101)
        except Exception:
            pass
        th = threading.Thread(target=self._update, name='abk-lucent-stats')
        th.daemon = True
        th.start()

    def _update(self):
        monitor = xbmc.Monitor()
        while not self.done and not monitor.abortRequested():
            try:
                tick()
            except Exception as e:
                _log(str(e))
            if not flag('Player.HasVideo'):
                self.close()
                return
            if monitor.waitForAbort(1):
                return

    def onAction(self, action):
        if action.getId() in CLOSE_ACTIONS:
            self.close()

    def close(self):
        self.done = True
        HOME.clearProperty(PREFIX + 'open')
        xbmcgui.WindowXMLDialog.close(self)


def _skin_path():
    import xbmcaddon
    for skin in (xbmc.getSkinDir(), 'skin.arctic.fuse.3'):
        try:
            return xbmcaddon.Addon(skin).getAddonInfo('path')
        except Exception:
            continue
    return ''


def open_window():
    # an 'open' mark left by a script Kodi stopped (skin reload, crash) only counts while the window shows
    if HOME.getProperty(PREFIX + 'open') and flag('Window.IsVisible(ABK_LucentPlayerInfo.xml)'):
        return
    HOME.setProperty(PREFIX + 'open', '1')
    try:
        win = StatsWindow('ABK_LucentPlayerInfo.xml', _skin_path(), 'Default', '1080i')
        tick()
        win.doModal()
        del win
    finally:
        HOME.clearProperty(PREFIX + 'open')


if __name__ == '__main__':
    import sys
    if sys.argv[1:2] == ['open']:
        xbmc.executebuiltin('Dialog.Close(videoosd,true)')
        open_window()
