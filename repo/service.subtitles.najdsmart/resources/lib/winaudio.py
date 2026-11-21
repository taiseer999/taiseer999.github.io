# -*- coding: utf-8 -*-
"""Read a video's audio with Windows' own Media Foundation (signed system component,
so Smart App Control / App Control policies don't block it) — no ffmpeg needed.

Uses IMFSourceReader through ctypes COM calls and returns 8 kHz mono 16-bit PCM,
the same format the ffmpeg path produces."""
import array
import ctypes
import sys
import threading

try:
    import audioop
except ImportError:  # pragma: no cover
    audioop = None

IS_WIN = sys.platform.startswith('win')
RATE = 8000


class WinAudioError(Exception):
    pass


if IS_WIN:
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [('Data1', ctypes.c_uint32), ('Data2', ctypes.c_uint16),
                    ('Data3', ctypes.c_uint16), ('Data4', ctypes.c_ubyte * 8)]

        def __init__(self, s):
            ctypes.Structure.__init__(self)
            h = s.replace('-', '')
            self.Data1 = int(h[0:8], 16)
            self.Data2 = int(h[8:12], 16)
            self.Data3 = int(h[12:16], 16)
            for i in range(8):
                self.Data4[i] = int(h[16 + 2 * i:18 + 2 * i], 16)

    class PROPVARIANT(ctypes.Structure):
        _fields_ = [('vt', ctypes.c_ushort), ('r1', ctypes.c_ushort), ('r2', ctypes.c_ushort),
                    ('r3', ctypes.c_ushort), ('hVal', ctypes.c_longlong), ('pad', ctypes.c_longlong)]

    MF_MT_MAJOR_TYPE = GUID('48eba18e-f8c9-4687-bf11-0a74c9f96a8f')
    MF_MT_SUBTYPE = GUID('f7e34c9a-42e8-4714-b74b-cb29d72c35e5')
    MFMediaType_Audio = GUID('73647561-0000-0010-8000-00aa00389b71')
    MFAudioFormat_PCM = GUID('00000001-0000-0010-8000-00aa00389b71')
    MF_MT_AUDIO_NUM_CHANNELS = GUID('37e48bf5-645e-4c5b-89de-ada9e29b696a')
    MF_MT_AUDIO_SAMPLES_PER_SECOND = GUID('5faeeae7-0290-4c31-9e8a-c534f68d9dba')
    MF_MT_AUDIO_BITS_PER_SAMPLE = GUID('f2deb57f-40fa-4764-aa33-ed4f2d1ff669')
    GUID_NULL = GUID('00000000-0000-0000-0000-000000000000')

    FIRST_AUDIO = 0xFFFFFFFD
    ALL_STREAMS = 0xFFFFFFFE
    F_ENDOFSTREAM = 0x2
    F_ERROR = 0x1
    F_TYPECHANGED = 0x20

    _HR = ctypes.HRESULT

    def _m(ptr, index, *argtypes):
        """Bind COM vtable method #index of interface pointer ptr."""
        vtbl = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        proto = ctypes.WINFUNCTYPE(_HR, ctypes.c_void_p, *argtypes)
        fn = proto(vtbl[index])
        return lambda *a: fn(ptr, *a)

    def _release(ptr):
        if ptr:
            try:
                vtbl = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
                ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtbl[2])(ptr)
            except Exception:
                pass

    # IMFAttributes indices (after IUnknown 0..2)
    A_GETUINT32, A_SETUINT32, A_SETGUID = 7, 21, 24
    # IMFSourceReader
    R_SETSEL, R_GETCUR, R_SETCUR, R_SETPOS, R_READ = 4, 6, 7, 8, 9
    # IMFSample
    S_TOCONTIG = 41
    # IMFMediaBuffer
    B_LOCK, B_UNLOCK = 3, 4

    _lock = threading.Lock()
    _started = [False]

    def _startup():
        with _lock:
            if _started[0]:
                return
            ole32 = ctypes.windll.ole32
            hr = ole32.CoInitializeEx(None, 0)  # MTA; S_FALSE / RPC_E_CHANGED_MODE are fine
            mfplat = ctypes.windll.mfplat
            hr = mfplat.MFStartup(ctypes.c_ulong(0x00020070), ctypes.c_ulong(0))
            if hr < 0:
                raise WinAudioError('MFStartup failed 0x%08x' % (hr & 0xFFFFFFFF))
            _started[0] = True

    def _coinit_thread():
        try:
            ctypes.windll.ole32.CoInitializeEx(None, 0)
        except Exception:
            pass


def available():
    if not IS_WIN:
        return False
    try:
        ctypes.windll.mfplat
        ctypes.windll.mfreadwrite
        return True
    except Exception:
        return False


def _get_u32(mt, guid):
    v = ctypes.c_uint32(0)
    try:
        _m(mt, A_GETUINT32, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_uint32))(
            ctypes.byref(guid), ctypes.byref(v))
        return v.value
    except OSError:
        return 0


def _open(path):
    _startup()
    _coinit_thread()
    reader = ctypes.c_void_p()
    fn = ctypes.windll.mfreadwrite.MFCreateSourceReaderFromURL
    fn.restype = _HR
    fn.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    try:
        fn(path, None, ctypes.byref(reader))
    except OSError as e:
        raise WinAudioError('cannot open (%s)' % e)
    try:
        _m(reader, R_SETSEL, ctypes.c_uint32, ctypes.c_int)(ALL_STREAMS, 0)
        _m(reader, R_SETSEL, ctypes.c_uint32, ctypes.c_int)(FIRST_AUDIO, 1)
    except OSError as e:
        _release(reader)
        raise WinAudioError('no audio stream (%s)' % e)
    # ask the decoder for 16-bit PCM; prefer stereo 48k downmix (safe for AC3/E-AC3 5.1)
    mtp = ctypes.c_void_p()
    ctypes.windll.mfplat.MFCreateMediaType(ctypes.byref(mtp))
    setg = _m(mtp, A_SETGUID, ctypes.POINTER(GUID), ctypes.POINTER(GUID))
    setu = _m(mtp, A_SETUINT32, ctypes.POINTER(GUID), ctypes.c_uint32)
    setg(ctypes.byref(MF_MT_MAJOR_TYPE), ctypes.byref(MFMediaType_Audio))
    setg(ctypes.byref(MF_MT_SUBTYPE), ctypes.byref(MFAudioFormat_PCM))
    setu(ctypes.byref(MF_MT_AUDIO_BITS_PER_SAMPLE), 16)
    setcur = _m(reader, R_SETCUR, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_void_p)
    ok = False
    for attempt in ('stereo', 'native'):
        try:
            if attempt == 'stereo':
                setu(ctypes.byref(MF_MT_AUDIO_NUM_CHANNELS), 2)
            setcur(FIRST_AUDIO, None, mtp)
            ok = True
            break
        except OSError:
            # retry with only "PCM 16-bit" (decoder keeps its native layout)
            _release(mtp)
            mtp = ctypes.c_void_p()
            ctypes.windll.mfplat.MFCreateMediaType(ctypes.byref(mtp))
            setg = _m(mtp, A_SETGUID, ctypes.POINTER(GUID), ctypes.POINTER(GUID))
            setu = _m(mtp, A_SETUINT32, ctypes.POINTER(GUID), ctypes.c_uint32)
            setg(ctypes.byref(MF_MT_MAJOR_TYPE), ctypes.byref(MFMediaType_Audio))
            setg(ctypes.byref(MF_MT_SUBTYPE), ctypes.byref(MFAudioFormat_PCM))
            setu(ctypes.byref(MF_MT_AUDIO_BITS_PER_SAMPLE), 16)
    _release(mtp)
    if not ok:
        _release(reader)
        raise WinAudioError('Windows has no decoder for this audio format')
    return reader


def _format(reader):
    cur = ctypes.c_void_p()
    _m(reader, R_GETCUR, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p))(FIRST_AUDIO, ctypes.byref(cur))
    ch = _get_u32(cur, MF_MT_AUDIO_NUM_CHANNELS) or 2
    rate = _get_u32(cur, MF_MT_AUDIO_SAMPLES_PER_SECOND) or 48000
    bits = _get_u32(cur, MF_MT_AUDIO_BITS_PER_SAMPLE) or 16
    _release(cur)
    if bits != 16:
        raise WinAudioError('unexpected sample format (%d bit)' % bits)
    return ch, rate


def _to_mono8k(buf, ch, rate, state):
    """Native PCM16 (any channel count) → 8 kHz mono PCM16."""
    if ch == 1:
        mono = buf
    elif ch == 2 and audioop:
        mono = audioop.tomono(buf, 2, 0.5, 0.5)
    else:
        a = array.array('h')
        a.frombytes(buf[:len(buf) // (2 * ch) * 2 * ch])
        # 5.1/7.1: dialogue lives in the centre channel (index 2)
        mono = a[2::ch].tobytes() if ch >= 3 else a[0::ch].tobytes()
    if audioop:
        out, state[0] = audioop.ratecv(mono, 2, 1, rate, RATE, state[0])
        return out
    a = array.array('h')
    a.frombytes(mono)
    step = rate / float(RATE)
    return array.array('h', (a[int(i * step)] for i in range(int(len(a) / step)))).tobytes()


def read_pcm(path, start=0.0, dur=None, abort=None, max_seconds=4 * 3600):
    """Decode audio from `start` seconds for `dur` seconds (None = to the end).
    Returns 8 kHz mono PCM16 bytes aligned so byte 0 == `start`."""
    if not available():
        raise WinAudioError('not windows')
    reader = _open(path)
    try:
        ch, rate = _format(reader)
        if start > 0:
            pv = PROPVARIANT()
            pv.vt = 20  # VT_I8, 100-ns units
            pv.hVal = int(start * 10000000)
            _m(reader, R_SETPOS, ctypes.POINTER(GUID), ctypes.POINTER(PROPVARIANT))(
                ctypes.byref(GUID_NULL), ctypes.byref(pv))
        read = _m(reader, R_READ, ctypes.c_uint32, ctypes.c_uint32,
                  ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
                  ctypes.POINTER(ctypes.c_longlong), ctypes.POINTER(ctypes.c_void_p))
        out = bytearray()
        state = [None]
        end_ms = (start + dur) * 1000 if dur else (start + max_seconds) * 1000
        written_ms = start * 1000.0
        idx, flags, ts = ctypes.c_uint32(), ctypes.c_uint32(), ctypes.c_longlong()
        n = 0
        while True:
            n += 1
            if abort and n % 50 == 0 and abort():
                raise WinAudioError('aborted')
            sample = ctypes.c_void_p()
            read(FIRST_AUDIO, 0, ctypes.byref(idx), ctypes.byref(flags), ctypes.byref(ts),
                 ctypes.byref(sample))
            if flags.value & F_TYPECHANGED:
                ch, rate = _format(reader)
                state = [None]
            if sample:
                t_ms = ts.value / 10000.0
                try:
                    if t_ms < start * 1000 - 50:      # seek landed early: skip
                        continue
                    if t_ms > written_ms + 40:        # gap → silence keeps the clock right
                        gap = int((t_ms - written_ms) * RATE / 1000)
                        out += b'\x00\x00' * gap
                        written_ms += gap * 1000.0 / RATE
                    buf = ctypes.c_void_p()
                    _m(sample, S_TOCONTIG, ctypes.POINTER(ctypes.c_void_p))(ctypes.byref(buf))
                    try:
                        data = ctypes.POINTER(ctypes.c_ubyte)()
                        mx, cur = ctypes.c_uint32(), ctypes.c_uint32()
                        _m(buf, B_LOCK, ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),
                           ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32))(
                            ctypes.byref(data), ctypes.byref(mx), ctypes.byref(cur))
                        raw = ctypes.string_at(data, cur.value)
                        _m(buf, B_UNLOCK)()
                    finally:
                        _release(buf)
                    pcm = _to_mono8k(raw, ch, rate, state)
                    out += pcm
                    written_ms += len(pcm) * 1000.0 / (2 * RATE)
                finally:
                    _release(sample)
                if written_ms >= end_ms:
                    break
            if flags.value & (F_ENDOFSTREAM | F_ERROR):
                break
        if dur:
            want = int(dur * RATE) * 2
            out = out[:want]
        return bytes(out)
    finally:
        _release(reader)


def self_test(tmp_dir):
    """Decode a tiny generated WAV to prove the Windows path works on this PC."""
    import math
    import os
    import struct
    import wave
    p = os.path.join(tmp_dir, 'selftest.wav')
    w = wave.open(p, 'wb')
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(44100)
    frames = b''.join(struct.pack('<hh', int(8000 * math.sin(i / 10.0)), 0) for i in range(44100))
    w.writeframes(frames)
    w.close()
    pcm = read_pcm(p)
    os.remove(p)
    return 7000 < len(pcm) // 2 < 9000   # ~1 s at 8 kHz
