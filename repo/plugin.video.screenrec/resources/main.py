# -*- coding: utf-8 -*-
# ============================================================
# Author: Meshal (Telegram: @i_Meshal)
# حفظ الحقوق: @i_Meshal
# Screen Rec. Plugin
# Developed by Meshal © 2025
# Licensed under MIT
# https://github.com/i-Meshal/Screen-Rec./
# 
# ============================================================
import os, sys, time, errno, signal, shutil, subprocess, json, logging, urllib.parse, zipfile, re
from logging.handlers import RotatingFileHandler
import xbmc, xbmcgui, xbmcaddon, xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
ADDON_PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))

PID_FILE = os.path.join(ADDON_PROFILE, 'recording.pid')
STATUS_FILE = os.path.join(ADDON_PROFILE, 'recording_status.txt')
FFMPEG_LOG = os.path.join(ADDON_PROFILE, 'ffmpeg.log')
ERROR_LOG = os.path.join(ADDON_PROFILE, 'errors.log')
MAX_RECORD_SECONDS = 30 * 60

if not os.path.exists(ADDON_PROFILE):
    os.makedirs(ADDON_PROFILE, exist_ok=True)

_get_bool = lambda s, d=False: (s or '').strip().lower() in ('1','true','yes','on') if (s or '').strip() != '' else d
DEBUG_ON = _get_bool(ADDON.getSetting('debug_log'), False)

LOGGER = logging.getLogger(ADDON_ID)
LOGGER.setLevel(logging.DEBUG if DEBUG_ON else logging.INFO)
if not LOGGER.handlers:
    h = RotatingFileHandler(ERROR_LOG, maxBytes=512*1024, backupCount=3, encoding='utf-8')
    h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(funcName)s:%(lineno)d %(message)s'))
    LOGGER.addHandler(h)

# ---------- Helpers ----------
def _pid_is_running(pid):
    if not pid: return False
    try:
        os.kill(pid, 0)
    except OSError as e:
        return e.errno != errno.ESRCH
    else:
        return True

def _get_save_path():
    p = xbmcvfs.translatePath(ADDON.getSetting('save_path') or '')
    return p or os.path.join(ADDON_PROFILE, 'recordings')

def save_status(is_recording, recording_file, pid=None):
    try:
        with open(STATUS_FILE,'w',encoding='utf-8') as f:
            f.write('1' if is_recording else '0')
            if recording_file:
                f.write('\n' + (recording_file or ''))
        if pid:
            with open(PID_FILE,'w',encoding='utf-8') as pf:
                pf.write(str(pid))
        else:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
    except Exception as e:
        LOGGER.error('save_status error: %s', e)

def load_status():
    is_rec=False; rec_file=None
    pid_running=False
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE,'r',encoding='utf-8') as pf:
                pid=int(pf.read().strip() or 0)
            if pid and _pid_is_running(pid):
                pid_running=True
                is_rec=True
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE,'r',encoding='utf-8') as f:
                lines=f.readlines()
                if lines:
                    is_rec = ((lines[0].strip()=='1') and pid_running) or is_rec
                    if len(lines)>1:
                        rec_file=lines[1].strip()
        if not is_rec and os.path.exists(PID_FILE):
            try: os.remove(PID_FILE)
            except Exception: pass
    except Exception as e:
        LOGGER.error('load_status error: %s', e)
    return is_rec, rec_file

FFMPEG_CANDIDATES = ['/storage/.kodi/addons/tools.ffmpeg-tools/bin/ffmpeg','/usr/bin/ffmpeg','ffmpeg']

def get_ffmpeg_path():
    try:
        tools = xbmcaddon.Addon('tools.ffmpeg-tools')
        p = os.path.join(tools.getAddonInfo('path'),'bin','ffmpeg')
        if os.path.exists(p): return p
    except Exception:
        pass
    which = shutil.which('ffmpeg')
    if which: return which
    for p in FFMPEG_CANDIDATES:
        try:
            r = subprocess.run([p,'-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
            if r.returncode==0: return p
        except Exception:
            continue
    return None

# ---------- Build FFmpeg cmd ----------
def get_resolution(key):
    return {'0':'1280x720','1':'1920x1080','2':'3840x2160'}.get(key,'1280x720')

def get_auto_fps():
    for path in ('/sys/class/display/mode', '/sys/class/graphics/fb0/modes'):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                data = f.read()
            match = re.search(r'(?:p|i|smpte)([0-9]{2,3})hz', data, re.IGNORECASE)
            if match:
                fps = int(match.group(1))
                return str(max(10, min(60, fps)))
        except Exception:
            pass
    labels = []
    try:
        labels.append(xbmc.getInfoLabel('System.ScreenMode'))
    except Exception:
        pass
    try:
        labels.append(xbmc.getInfoLabel('System.CurrentWindow'))
    except Exception:
        pass
    for label in labels:
        if not label:
            continue
        match = re.search(r'@\s*([0-9]+(?:\.[0-9]+)?)', label)
        if match:
            try:
                fps = int(round(float(match.group(1))))
                return str(max(10, min(60, fps)))
            except Exception:
                pass
    return '30'

def get_capture_device():
    for dev in ('/dev/fb0', '/dev/graphics/fb0'):
        if os.path.exists(dev):
            return dev
    return '/dev/fb0'

def ffmpeg_has_device(ffmpeg, name):
    try:
        r = subprocess.run([ffmpeg, '-hide_banner', '-devices'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=4)
        data = (r.stdout or '') + '\n' + (r.stderr or '')
        return r.returncode == 0 and re.search(r'\b%s\b' % re.escape(name), data) is not None
    except Exception:
        return False

def read_capture_mode():
    try:
        return int(ADDON.getSetting('capture_mode') or '0')
    except Exception:
        return 0

def get_capture_backend(ffmpeg):
    mode = read_capture_mode()
    dev = get_capture_device()

    if mode in (0, 1) and os.path.exists('/dev/dri') and ffmpeg_has_device(ffmpeg, 'kmsgrab'):
        return 'kmsgrab', None
    if mode in (0, 2) and os.path.exists(dev):
        return 'fbdev', dev
    if mode == 1 and os.path.exists(dev):
        return 'fbdev', dev
    if mode == 2 and os.path.exists('/dev/dri') and ffmpeg_has_device(ffmpeg, 'kmsgrab'):
        return 'kmsgrab', None
    return None, None

def kmsgrab_filter_works(ffmpeg, fps, vf):
    if not (os.path.exists('/dev/dri') and ffmpeg_has_device(ffmpeg, 'kmsgrab')):
        return False
    cmd = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-f', 'kmsgrab', '-framerate', fps]
    if os.path.exists('/dev/dri/card0'):
        cmd += ['-device', '/dev/dri/card0']
    cmd += ['-i', '-', '-vf', vf, '-frames:v', '1', '-f', 'null', '-']
    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=6)
        if r.returncode == 0:
            return True
        LOGGER.info("KMS preflight failed: %s", (r.stderr or b'')[:500].decode('utf-8', 'ignore'))
    except Exception:
        LOGGER.exception("KMS preflight exception")
    return False

def get_framebuffer_size():
    paths = (
        '/sys/class/graphics/fb0/virtual_size',
        '/sys/class/graphics/fb0/modes'
    )
    for path in paths:
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                data = f.read().strip()
            match = re.search(r'([0-9]{3,5})\D+([0-9]{3,5})', data)
            if match:
                return match.group(1), match.group(2)
        except Exception:
            continue
    try:
        w = int(xbmcgui.getScreenWidth())
        h = int(xbmcgui.getScreenHeight())
        if w > 0 and h > 0:
            return str(w), str(h)
    except Exception:
        pass
    return None, None

def get_quality(key, enc):
    if enc == 'vp9':
        return {'0':'38','1':'28','2':'18'}.get(key,'28')
    if enc == 'x264':
        return {'0':'24','1':'20','2':'16'}.get(key,'20')
    if enc == 'x265':
        return {'0':'24','1':'20','2':'16'}.get(key,'20')
    return {'0':'2M','1':'4M','2':'8M'}.get(key,'4M')

def read_encoder():
    try:
        idx=int(ADDON.getSetting('encoder') or '0')
    except:
        idx=0
    return ['x264','x265','vp9'][idx if 0<=idx<=2 else 0]

def build_cmd(output_path):
    ffmpeg=get_ffmpeg_path()
    if not ffmpeg: return None, output_path
    res=get_resolution(ADDON.getSetting('resolution') or '1')
    fps=get_auto_fps()
    enc=read_encoder()
    q=get_quality(ADDON.getSetting('quality') or '1', enc)
    if enc in ('x264','x265') and not output_path.endswith('.mp4'):
        output_path=os.path.splitext(output_path)[0]+'.mp4'
    elif enc == 'vp9' and not output_path.endswith('.webm'):
        output_path=os.path.splitext(output_path)[0]+'.webm'
    try:
        w,h = (res.split('x')+['720'])[:2]
    except Exception:
        w,h='1280','720'

    vf=f"scale={w}:{h}:flags=bicubic,format=yuv420p"
    kms_vf='hwdownload,format=rgba,' + vf
    backend, capture_dev = get_capture_backend(ffmpeg)
    if backend == 'kmsgrab' and read_capture_mode() == 0 and not kmsgrab_filter_works(ffmpeg, fps, kms_vf):
        dev = get_capture_device()
        if os.path.exists(dev):
            backend, capture_dev = 'fbdev', dev
    if not backend:
        return None, output_path
    LOGGER.info("Capture backend: %s, device: %s, auto_fps: %s, output_resolution: %s, encoder: %s, quality: %s", backend, capture_dev or 'auto', fps, res, enc, q)
    cmd=[ffmpeg]
    cmd += ['-loglevel','info','-stats'] if DEBUG_ON else ['-loglevel','warning']
    cmd += ['-fflags','+genpts','-thread_queue_size','512']
    if backend == 'kmsgrab':
        drm_device = '/dev/dri/card0' if os.path.exists('/dev/dri/card0') else None
        cmd += ['-f','kmsgrab','-framerate', fps]
        if drm_device:
            cmd += ['-device', drm_device]
        cmd += ['-i','-','-vf', kms_vf,'-y']
    else:
        cmd += ['-f','fbdev','-framerate', fps, '-i', capture_dev, '-vf', vf,'-y']
    cmd += ['-t', str(MAX_RECORD_SECONDS)]
    mp4_flags = '+frag_keyframe+empty_moov+default_base_moof'
    try:
        gop = str(max(25, min(120, int(float(fps)) * 2)))
    except Exception:
        gop = '60'
    if enc=='x264':
        cmd += ['-c:v','libx264','-preset','ultrafast','-tune','zerolatency','-crf', q, '-g', gop, '-x264-params', 'repeat-headers=1', '-movflags', mp4_flags]
    elif enc=='x265':
        cmd += ['-c:v','libx265','-preset','ultrafast','-x265-params', 'log-level=error', '-crf', q, '-tag:v','hvc1','-movflags', mp4_flags]
    else:
        cmd += ['-c:v','libvpx-vp9','-crf', q,'-b:v','0','-deadline','realtime','-cpu-used','5']
    cmd.append(output_path)
    return cmd, output_path

# ---------- Recording ----------
def start_recording():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE,'r',encoding='utf-8') as pf:
                pid=int(pf.read().strip() or 0)
            if pid and _pid_is_running(pid):
                xbmcgui.Dialog().ok(ADDON_NAME,'يوجد تسجيل نشط بالفعل. أوقفه أولًا.')
                return False
            else:
                os.remove(PID_FILE)
        except Exception:
            pass
    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path:
        xbmcgui.Dialog().ok(ADDON_NAME,'لم يتم العثور على FFmpeg. ثبّت إضافة FFmpeg Tools.')
        return False
    backend, _ = get_capture_backend(ffmpeg_path)
    if not backend:
        xbmcgui.Dialog().ok(ADDON_NAME,'لم أجد مصدر التقاط مناسب. تأكد من توفر /dev/dri أو /dev/fb0 ثم صدّر السجلات للفحص.')
        return False
    save_path=_get_save_path()
    try:
        os.makedirs(save_path, exist_ok=True)
    except Exception as e:
        xbmcgui.Dialog().ok(ADDON_NAME, f'خطأ في إنشاء مجلد الحفظ: {e}')
        LOGGER.exception("mkdir save_path failed")
        return False
    ts=time.strftime('%Y%m%d_%H%M%S')
    outfile=os.path.join(save_path, f'recording_{ts}.webm')
    cmd,outfile=build_cmd(outfile)
    if not cmd:
        xbmcgui.Dialog().ok(ADDON_NAME,'تعذّر بناء أمر FFmpeg أو تحديد مصدر الالتقاط.')
        return False
    LOGGER.info("FFmpeg command: %s", ' '.join(cmd))
    try:
        log_handle=open(FFMPEG_LOG,'ab',buffering=0)
        proc=subprocess.Popen(cmd, stdout=log_handle, stderr=log_handle, stdin=subprocess.PIPE, start_new_session=True)
        save_status(True, cmd[-1], proc.pid)
        xbmcgui.Dialog().notification(ADDON_NAME,'بدأ التسجيل', xbmcgui.NOTIFICATION_INFO, 3000)
        return True
    except Exception as e:
        xbmcgui.Dialog().ok(ADDON_NAME, f'فشل بدء التسجيل: {e}')
        LOGGER.exception("start_recording failed")
        save_status(False, None)
        return False

def _signal_process(pid, sig):
    try:
        os.killpg(pid, sig)
        return
    except Exception:
        pass
    try:
        os.kill(pid, sig)
    except Exception:
        pass

def _wait_process_exit(pid, seconds):
    end = time.time() + seconds
    while time.time() < end:
        if not _pid_is_running(pid):
            return True
        time.sleep(0.25)
    return not _pid_is_running(pid)

def _send_ffmpeg_quit(pid):
    try:
        fd_path = f'/proc/{pid}/fd/0'
        if os.path.exists(fd_path):
            with open(fd_path, 'wb', buffering=0) as fd:
                fd.write(b'q\n')
            return True
    except Exception:
        LOGGER.exception("send ffmpeg quit failed")
    return False

def _graceful_stop(pid):
    if _send_ffmpeg_quit(pid) and _wait_process_exit(pid, 8):
        return
    _signal_process(pid, signal.SIGINT)
    if _wait_process_exit(pid, 15):
        return
    _signal_process(pid, signal.SIGTERM)
    if _wait_process_exit(pid, 5):
        return
    _signal_process(pid, signal.SIGKILL)

def stop_recording():
    is_rec, rec_file = load_status()
    if not is_rec:
        xbmcgui.Dialog().notification(ADDON_NAME,'لا يوجد تسجيل نشط', xbmcgui.NOTIFICATION_INFO,1200)
        return None
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE,'r',encoding='utf-8') as pf:
                pid=int(pf.read().strip() or 0)
            if pid and _pid_is_running(pid):
                LOGGER.info("Stopping recording ... pid=%s", pid)
                xbmcgui.Dialog().notification(ADDON_NAME,'جارٍ حفظ ملف التسجيل ...', xbmcgui.NOTIFICATION_INFO,2000)
                _graceful_stop(pid)
                xbmcgui.Dialog().notification(ADDON_NAME,'توقف التسجيل', xbmcgui.NOTIFICATION_INFO,2000)
    except Exception:
        LOGGER.exception("stop_recording failed")
    finally:
        try:
            if os.path.exists(PID_FILE): os.remove(PID_FILE)
        except Exception: pass
        save_status(False, None)
    return rec_file

# ---------- Open save folder (no return) ----------
def _open_save_folder():
    p = _get_save_path().replace('\\', '/')
    if p and not p.endswith('/'):
        p += '/'
    xbmc.executebuiltin('Dialog.Close(all,true)')
    xbmc.sleep(80)
    quoted = '"' + p.replace('"', '\\"') + '"'
    xbmc.executebuiltin(f'ActivateWindow(Videos,{quoted})')

# ---------- Logs & tools ----------
def _zip_logs():
    ts=time.strftime('%Y%m%d_%H%M%S')
    outzip=os.path.join(ADDON_PROFILE, f'logs_{ts}.zip')
    with zipfile.ZipFile(outzip, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in (ERROR_LOG, FFMPEG_LOG, STATUS_FILE, PID_FILE):
            if p and os.path.exists(p):
                z.write(p, arcname=os.path.basename(p))
        settings_res=os.path.join(ADDON_PATH,'resources','settings.xml')
        if os.path.exists(settings_res):
            z.write(settings_res, arcname='settings_schema.xml')
    return outzip

def _open_logs_folder():
    xbmc.executebuiltin(f'ActivateWindow(videos,{ADDON_PROFILE})')

# ---------- Toggle with dialog ----------
def toggle_with_dialog():
    is_rec, rec_file = load_status()
    if is_rec:
        recorded = stop_recording()
        if recorded and (os.path.exists(recorded) or True):
            enable_share = _get_bool(ADDON.getSetting('enable_share'), True)
            options = ['مشاركة','فتح مجلد الفديو','إغلاق'] if enable_share else ['فتح مجلد الفديو','إغلاق']
            sel = xbmcgui.Dialog().select('خيارات التسجيل', options)
            if enable_share and sel == 0:
                share_video(recorded)
                return 'shared'
            elif (enable_share and sel == 1) or (not enable_share and sel == 0):
                return 'open_folder'
            else:
                return 'stopped'
        return 'stopped'
    else:
        ok = start_recording()
        return 'started' if ok else 'error'

# ---------- Share (Litterbox/Catbox) ----------
def _run_curl_cancellable(args, title, msg, max_time=120):
    base = ['curl','-4','-sS','--http1.1','--connect-timeout','6','--max-time',str(max_time)]
    cmd = base + args
    dp = xbmcgui.DialogProgress()
    dp.create(title, msg)
    rc = -1; out=''; err=''; cancelled=False
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        start = time.time()
        while True:
            try:
                o, e = proc.communicate(timeout=0.5)
                out += o or ''
                err += e or ''
                rc = proc.returncode
                break
            except subprocess.TimeoutExpired:
                elapsed = time.time()-start
                pct = min(5 + int((elapsed/max(1.0,float(max_time)))*90), 99)
                try: dp.update(pct)
                except Exception: pass
                if dp.iscanceled():
                    cancelled=True
                    try:
                        proc.terminate()
                        try:
                            proc.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                    except Exception:
                        pass
                    rc = -15
                    err += '\nCancelled by user.'
                    break
        return rc, (out or '').strip(), (err or '').strip(), cancelled
    finally:
        try: dp.close()
        except Exception: pass

def _build_upload_cmd(video_file, backend):
    if backend == 'catbox':
        return ['-F','reqtype=fileupload','-F', f'fileToUpload=@{video_file}', 'https://catbox.moe/user/api.php']
    return ['-F','reqtype=fileupload','-F','time=72h','-F', f'fileToUpload=@{video_file}', 'https://litterbox.catbox.moe/resources/internals/api.php']

def _download_qr(qr_path, url):
    providers = [
        'https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={}',
        'https://quickchart.io/qr?size=300&text={}',
        'https://chart.googleapis.com/chart?cht=qr&chs=300x300&chl={}'
    ]
    enc = urllib.parse.quote(url, safe='')
    for p in providers:
        api = p.format(enc)
        rc, _, _, cancelled = _run_curl_cancellable(['-L','-o',qr_path, api], ADDON_NAME, 'جارٍ توليد QR ...', max_time=20)
        if cancelled:
            return False
        if rc==0 and os.path.exists(qr_path) and os.path.getsize(qr_path)>0:
            return True
    return False

def share_video(video_file):
    enable_share = _get_bool(ADDON.getSetting('enable_share'), True)
    if not enable_share:
        xbmcgui.Dialog().ok(ADDON_NAME,'المشاركة معطّلة من الإعدادات.')
        return
    try:
        idx = int(ADDON.getSetting('upload_backend') or '1')
    except Exception:
        idx = 0
    backend = 'litterbox' if idx == 0 else 'catbox'
    args = _build_upload_cmd(video_file, backend)
    label = 'Litterbox (72h)' if backend=='litterbox' else 'Catbox'
    rc, out, err, cancelled = _run_curl_cancellable(args, ADDON_NAME, f'جارٍ الرفع عبر {label} ...', max_time=120)
    if cancelled:
        xbmcgui.Dialog().notification(ADDON_NAME,'تم إلغاء الرفع', xbmcgui.NOTIFICATION_INFO, 1200)
        return
    if rc == 0 and out.startswith('http'):
        url = out
        qr_path = os.path.join(ADDON_PROFILE, 'qr.png')
        if _download_qr(qr_path, url):
            class QRDialog(xbmcgui.WindowDialog):
                def __init__(self, u, q):
                    super().__init__()
                    w=xbmcgui.getScreenWidth(); h=xbmcgui.getScreenHeight()
                    bg = xbmcgui.ControlImage(0,0,w,h,'',colorDiffuse='0x80000080')
                    self.addControl(bg)
                    img = xbmcgui.ControlImage((w-225)//2,(h-225)//2,225,225,q)
                    self.addControl(img)
                    btn = xbmcgui.ControlButton((w-200)//2, min(h-80,(h+225)//2+16),200,50,'إغلاق')
                    self.addControl(btn)
                    self.setFocus(btn)
                def onAction(self, a):
                    if a in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK): self.close()
                def onControl(self, c):
                    try:
                        if c.getLabel()=='إغلاق': self.close()
                    except Exception: pass
            d=QRDialog(url, qr_path); d.doModal(); del d
            try: os.remove(qr_path)
            except Exception: pass
        else:
            xbmcgui.Dialog().textviewer('رابط المشاركة', url)
        return
    xbmcgui.Dialog().ok(ADDON_NAME, 'فشل في رفع الفيديو.\n' + f'rc={rc}\nout[:120]={out[:120]}\nerr[:120]={err[:120]}')

# ---------- Entry ----------
def main():
    handle = int(sys.argv[1]) if len(sys.argv)>1 else -1
    succeeded = True
    state = None
    try:
        if len(sys.argv)>2 and sys.argv[2].startswith('?'):
            params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
            action = (params.get('action') or '').lower()
            if action == 'about':
                xbmcgui.Dialog().ok(ADDON_NAME, 'المطوّر: Meshal A. Alsaedi\nTelegram: @i_Meshal')
                state = 'about'
            elif action == 'export_logs':
                p=_zip_logs()
                xbmcgui.Dialog().ok(ADDON_NAME, f'تم إنشاء الحزمة:\n{p}')
                state='export_logs'
            elif action == 'open_logs':
                _open_logs_folder(); state='open_logs'
            else:
                state = toggle_with_dialog()
                succeeded = (state!='error')
        else:
            state = toggle_with_dialog()
            succeeded = (state!='error')
    finally:
        try:
            import xbmcplugin
            xbmcplugin.endOfDirectory(handle, succeeded=succeeded)
        except Exception:
            pass
        if state == 'started':
            xbmc.executebuiltin('Action(Back)')
        elif state == 'open_folder':
            _open_save_folder()

if __name__ == '__main__':
    main()
