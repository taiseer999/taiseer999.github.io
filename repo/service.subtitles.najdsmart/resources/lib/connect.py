# -*- coding: utf-8 -*-
"""Sign in to AI services from inside the add-on.

1) OpenRouter one-click sign-in (OAuth PKCE): the add-on opens openrouter.ai in the
   browser, you log in and press Authorize, OpenRouter sends a code back to a tiny
   server on this PC (localhost) and the add-on swaps it for your own API key.
2) Key form for every other service: the add-on serves a small page on your home
   network — open it on your phone or PC browser and paste keys there instead of
   typing them with the remote. Protected by a one-time random link."""
import base64
import hashlib
import html
import json
import os
import secrets
import socket
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

import xbmc
import xbmcaddon
import xbmcgui

from .common import ADDON_ID, ADDON_NAME, http, log

DLG = xbmcgui.Dialog()


def _open_browser(url):
    try:
        if sys.platform.startswith('win'):
            os.startfile(url)
        elif sys.platform == 'darwin':
            os.system('open "%s"' % url)
        elif xbmc.getCondVisibility('System.Platform.Android'):
            xbmc.executebuiltin('StartAndroidActivity("","android.intent.action.VIEW","","%s")' % url)
        else:
            os.system('xdg-open "%s" >/dev/null 2>&1 &' % url)
        return True
    except Exception as e:
        log('open browser failed: %s' % e)
        return False


def _free_server(handler, host, ports):
    for p in ports:
        try:
            srv = HTTPServer((host, p), handler)
            return srv, p
        except OSError:
            continue
    raise OSError('no free port')


# ------------------------------------------------------------------ OpenRouter
def openrouter_login():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    box = {}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if 'code' in q:
                box['code'] = q['code'][0]
                msg = 'تم ✓ ارجع لكودي — Done, return to Kodi'
            else:
                msg = 'ما وصل رمز — No code received'
            body = ('<html dir="rtl"><meta charset="utf-8"><body style="font-family:sans-serif;'
                    'background:#101826;color:#fff;text-align:center;padding-top:15vh">'
                    '<h1>%s</h1></body></html>' % msg).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(body)

    try:
        srv, port = _free_server(H, '127.0.0.1', [3000] + list(range(51400, 51440)))
    except OSError:
        DLG.ok(ADDON_NAME, 'ما قدرت أشغل خادم الاستقبال على هذا الجهاز.')
        return None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    cb = 'http://localhost:%d/callback' % port
    url = 'https://openrouter.ai/auth?' + urllib.parse.urlencode(
        {'callback_url': cb, 'code_challenge': challenge, 'code_challenge_method': 'S256'})
    if not _open_browser(url):
        srv.shutdown()
        DLG.ok(ADDON_NAME, 'ما قدرت أفتح المتصفح على هذا الجهاز.\nاستخدم «إدخال المفاتيح من الجوال» بدلها.')
        return None
    prog = xbmcgui.DialogProgress()
    prog.create(ADDON_NAME, 'فتحت لك OpenRouter في المتصفح:\nسجّل دخول (أو أنشئ حساب) واضغط Authorize، وارجع هنا.')
    key = None
    try:
        t0 = time.time()
        while time.time() - t0 < 600:
            if prog.iscanceled():
                break
            if 'code' in box:
                prog.update(90, 'جاري استلام المفتاح...')
                r = http('https://openrouter.ai/api/v1/auth/keys',
                         json_body={'code': box['code'], 'code_verifier': verifier,
                                    'code_challenge_method': 'S256'}, timeout=30)
                key = r.get('key')
                break
            prog.update(int((time.time() - t0) * 100 / 600), 'بانتظار تسجيل الدخول في المتصفح...')
            xbmc.sleep(500)
    except Exception as e:
        log('openrouter login failed: %s' % e)
    finally:
        prog.close()
        try:
            srv.shutdown()
        except Exception:
            pass
    if not key:
        DLG.ok(ADDON_NAME, 'ما اكتمل تسجيل الدخول. جرّب مرة ثانية.')
        return None
    a = xbmcaddon.Addon(ADDON_ID)
    a.setSetting('openrouter_key', key)
    order = [p for p in (a.getSetting('ai_order') or '').split(',') if p and p != 'openrouter']
    pos = 1 if order and order[0] == 'gemini' else 0
    order.insert(pos, 'openrouter')
    a.setSetting('ai_order', ','.join(order))
    DLG.ok(ADDON_NAME, 'تم ربط OpenRouter ✓\nصار احتياط تلقائي إذا خلص Gemini.')
    return key


# ------------------------------------------------------------------ key form
FIELDS = [
    ('gemini_key', 'Gemini', 'https://aistudio.google.com/apikey'),
    ('deepseek_key', 'DeepSeek', 'https://platform.deepseek.com/api_keys'),
    ('openai_key', 'ChatGPT (OpenAI)', 'https://platform.openai.com/api-keys'),
    ('claude_key', 'Claude', 'https://console.anthropic.com/settings/keys'),
    ('grok_key', 'Grok (xAI)', 'https://console.x.ai'),
    ('openrouter_key', 'OpenRouter', 'https://openrouter.ai/keys'),
    ('groq_key', 'Groq', 'https://console.groq.com/keys'),
    ('mistral_key', 'Mistral', 'https://console.mistral.ai/api-keys'),
    ('subdl_key', 'SubDL', 'https://subdl.com/panel/api'),
    ('subsource_key', 'SubSource', 'https://subsource.net'),
    ('os_key', 'OpenSubtitles', 'https://www.opensubtitles.com/consumers'),
]


def _lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()


def _page(token, saved=None):
    a = xbmcaddon.Addon(ADDON_ID)
    rows = []
    for sid, title, link in FIELDS:
        cur = a.getSetting(sid)
        hint = ('موجود (••••%s) — اتركه فاضي للإبقاء' % html.escape(cur[-4:])) if cur else 'الصق المفتاح هنا'
        rows.append('<label><b>%s</b> <a href="%s" target="_blank">طلّع مفتاح ↗</a>'
                    '<input name="%s" placeholder="%s" autocomplete="off"></label>'
                    % (html.escape(title), link, sid, hint))
    note = '<p class="ok">✓ تم الحفظ: %s</p>' % html.escape('، '.join(saved)) if saved else ''
    return ('<!doctype html><html dir="rtl" lang="ar"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>ترجمة نجد — المفاتيح</title><style>'
            'body{font-family:system-ui,sans-serif;background:#0f1724;color:#eef;margin:0;padding:18px}'
            'h1{color:#ecbe5c;font-size:22px}label{display:block;margin:12px 0}'
            'input{width:100%%;box-sizing:border-box;padding:12px;border-radius:10px;border:1px solid #345;'
            'background:#16233a;color:#fff;font-size:16px;direction:ltr;margin-top:6px}'
            'a{color:#7fb5ff;font-size:13px}button{width:100%%;padding:14px;border:0;border-radius:12px;'
            'background:#ecbe5c;color:#111;font-size:18px;font-weight:bold;margin-top:12px}'
            '.ok{background:#173d27;padding:10px;border-radius:10px}</style>'
            '<h1>ترجمة نجد الذكية — المفاتيح</h1>%s'
            '<form method="post" action="/%s">%s<button>حفظ</button></form>'
            '<p style="opacity:.6;font-size:12px">الصفحة تشتغل بس وكودي مفتوح على نافذة الاستقبال.</p>'
            '</html>' % (note, token, ''.join(rows)))


def key_form():
    token = secrets.token_urlsafe(8)
    saved_all = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, body, code=200):
            b = body.encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            if self.path.strip('/') != token:
                return self._send('<h1>404</h1>', 404)
            self._send(_page(token))

        def do_POST(self):
            if self.path.strip('/') != token:
                return self._send('<h1>404</h1>', 404)
            n = int(self.headers.get('Content-Length') or 0)
            if n > 20000:
                return self._send('<h1>413</h1>', 413)
            form = urllib.parse.parse_qs(self.rfile.read(n).decode('utf-8', 'replace'))
            a = xbmcaddon.Addon(ADDON_ID)
            saved = []
            for sid, title, _l in FIELDS:
                v = (form.get(sid) or [''])[0].strip()
                if v and len(v) < 400:
                    a.setSetting(sid, v)
                    saved.append(title)
            saved_all.extend(saved)
            self._send(_page(token, saved))

    try:
        srv, port = _free_server(H, '0.0.0.0', range(8765, 8790))
    except OSError:
        DLG.ok(ADDON_NAME, 'ما قدرت أشغل صفحة المفاتيح على هذا الجهاز.')
        return
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = 'http://%s:%d/%s' % (_lan_ip(), port, token)
    if sys.platform.startswith('win') or sys.platform == 'darwin':
        _open_browser('http://localhost:%d/%s' % (port, token))   # also open it right here
    DLG.ok(ADDON_NAME, 'افتح هذا الرابط من جوالك أو أي جهاز على نفس الواي فاي:\n'
                       '[B]%s[/B]\nالصق المفاتيح واضغط حفظ، بعدين ارجع واضغط موافق.\n'
                       '(لو ويندوز سأل عن جدار الحماية، اختر «السماح»)' % url)
    srv.shutdown()
    srv.server_close()
    if saved_all:
        DLG.notification(ADDON_NAME, 'انحفظت: %s ✓' % '، '.join(sorted(set(saved_all))), time=5000)


# ------------------------------------------------------------------ Groq (Whisper) by QR code
GROQ_PAGE = '''<!doctype html><html dir="rtl" lang="ar"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>ترجمة نجد - Whisper</title>
<style>body{font-family:system-ui,sans-serif;background:#0f1724;color:#eef;margin:0;padding:18px;line-height:1.6}
h1{color:#ecbe5c;font-size:21px;margin:0 0 6px}.st{background:#16233a;border-radius:14px;padding:12px 14px;margin:12px 0}
.n{display:inline-block;width:26px;height:26px;border-radius:13px;background:#ecbe5c;color:#111;text-align:center;font-weight:bold;margin-left:6px}
a.b,button{display:block;width:100%%;box-sizing:border-box;text-align:center;padding:14px;border:0;border-radius:12px;font-size:17px;font-weight:bold;text-decoration:none;margin-top:8px}
a.b{background:#2b6cdf;color:#fff}button{background:#ecbe5c;color:#111}button.g{background:#2a3a55;color:#dde}
input{width:100%%;box-sizing:border-box;padding:12px;border-radius:10px;border:1px solid #345;background:#0f1a2c;color:#fff;font-size:16px;direction:ltr;margin-top:8px}
.msg{padding:12px;border-radius:10px;margin-top:10px;display:none}.ok{background:#173d27;display:block}.bad{background:#4a1c1c;display:block}
small{opacity:.65}</style>
<h1>ربط Whisper (مجاني)</h1><small>يخلي الإضافة تسمع كلام الفيلم وتضبط الترجمة عليه. %(cur)s</small>
<div class="st"><span class="n">١</span>سجّل دخول في Groq (يقبل حساب قوقل، بدون بطاقة)
<a class="b" href="https://console.groq.com/keys" target="_blank">افتح Groq ↗</a></div>
<div class="st"><span class="n">٢</span>اضغط <b>Create API Key</b>، اكتب أي اسم، بعدين <b>Copy</b></div>
<div class="st"><span class="n">٣</span>ارجع هنا والصقه
<button class="g" type="button" onclick="pasteKey()">📋 لصق</button>
<input id="k" placeholder="gsk_..." autocomplete="off" autocapitalize="off" spellcheck="false">
<button type="button" onclick="save()">حفظ وتجربة</button><div id="m" class="msg"></div></div>
<script>
function say(t,ok){var m=document.getElementById('m');m.textContent=t;m.className='msg '+(ok?'ok':'bad');}
function pasteKey(){if(navigator.clipboard&&navigator.clipboard.readText){navigator.clipboard.readText().then(function(t){document.getElementById('k').value=t.trim();save();},function(){say('اضغط مطوّل على الخانة واختر لصق',false);});}else{say('اضغط مطوّل على الخانة واختر لصق',false);}}
function save(){var k=document.getElementById('k').value.replace(/\\s+/g,'');
 if(!/^gsk_[A-Za-z0-9]{20,}$/.test(k)){say('المفتاح يبدأ بـ gsk_ — تأكد إنك نسخته كامل',false);return;}
 say('جاري التجربة...',true);
 fetch(location.pathname,{method:'POST',body:k}).then(function(r){return r.json();}).then(function(j){say(j.msg,j.ok);})
 .catch(function(){say('انقطع الاتصال بكودي — تأكد إنك على نفس الواي فاي',false);});}
</script></html>'''


def check_groq(key):
    """'ok' | 'bad' | 'net' - a tiny call that costs nothing."""
    try:
        http('https://api.groq.com/openai/v1/models', headers={'Authorization': 'Bearer ' + key}, timeout=15)
        return 'ok'
    except Exception as e:
        t = str(e)
        return 'bad' if ('401' in t or '403' in t) else 'net'


class _KeyQR(xbmcgui.WindowDialog):
    def __init__(self, link, title, lines):
        super().__init__()
        from .sharereport import qr_png, MEDIA
        white = os.path.join(MEDIA, 'white.png')
        self.addControl(xbmcgui.ControlImage(0, 0, 1280, 720, white, colorDiffuse='E60B111B'))
        self.addControl(xbmcgui.ControlImage(370, 40, 540, 640, white, colorDiffuse='FF141C2A'))
        self.addControl(xbmcgui.ControlLabel(370, 60, 540, 40, '[B]%s[/B]' % title,
                                             textColor='FFECBE5C', alignment=0x00000002))
        self.addControl(xbmcgui.ControlImage(490, 110, 300, 300, qr_png(link)))
        y = 425
        for ln, col in lines:
            self.addControl(xbmcgui.ControlLabel(380, y, 520, 30, ln, textColor=col, alignment=0x00000002))
            y += 34
        self.status = xbmcgui.ControlLabel(380, y + 4, 520, 30, '', textColor='FF7BE495', alignment=0x00000002)
        self.addControl(self.status)
        self.addControl(xbmcgui.ControlLabel(370, 640, 540, 30, 'رجوع للإغلاق', textColor='FF98A2B3',
                                             alignment=0x00000002))

    def onAction(self, action):
        if action.getId() in (9, 10, 13, 92, 110, 7, 100, 101):
            self.close()


def groq_qr():
    """Show a QR code; the phone opens a small page that walks through getting a free Groq
    key and sends it back here. The window closes by itself once a working key arrives."""
    token = secrets.token_urlsafe(8)
    cur = xbmcaddon.Addon(ADDON_ID).getSetting('groq_key')
    state = {'ok': False}
    holder = {}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, body, ctype='text/html; charset=utf-8', code=200):
            b = body.encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(b)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(b)

        def _json(self, ok, msg):
            self._send(json.dumps({'ok': ok, 'msg': msg}, ensure_ascii=False), 'application/json; charset=utf-8')

        def do_GET(self):
            if self.path.strip('/') != token:
                return self._send('404', 'text/plain', 404)
            note = ('عندك مفتاح محفوظ (••••%s)، تقدر تبدّله.' % html.escape(cur[-4:])) if cur else ''
            self._send(GROQ_PAGE % {'cur': note})

        def do_POST(self):
            if self.path.strip('/') != token:
                return self._send('404', 'text/plain', 404)
            n = int(self.headers.get('Content-Length') or 0)
            key = self.rfile.read(n).decode('utf-8', 'replace').strip() if 0 < n < 400 else ''
            if not key.startswith('gsk_'):
                return self._json(False, 'هذا مو مفتاح Groq')
            res = check_groq(key)
            if res == 'bad':
                return self._json(False, 'Groq رفض المفتاح — انسخه مرة ثانية')
            a = xbmcaddon.Addon(ADDON_ID)
            a.setSetting('groq_key', key)
            a.setSetting('whisper_sync', 'true')
            state['ok'] = True
            self._json(True, '✓ تم! المفتاح شغّال وانحفظ في كودي. تقدر تسكّر الصفحة.' if res == 'ok' else
                       '✓ انحفظ في كودي (ما قدرت أجرّبه الحين، بيتجرّب أول ما يشتغل فيلم).')
            w = holder.get('w')
            if w:
                try:
                    w.status.setLabel('✓ وصل المفتاح وانحفظ')
                except Exception:
                    pass
                threading.Timer(2.0, w.close).start()

    try:
        srv, port = _free_server(H, '0.0.0.0', range(8765, 8790))
    except OSError:
        DLG.ok(ADDON_NAME, 'ما قدرت أشغل صفحة الربط على هذا الجهاز.')
        return False
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    link = 'http://%s:%d/%s' % (_lan_ip(), port, token)
    try:
        w = _KeyQR(link, 'ربط Whisper — مجاني', [
            ('صوّر الرمز بكاميرا الجوال', 'FFF4F1EA'),
            ('سجّل في Groq ← انسخ المفتاح ← الصق ← حفظ', 'FFB8C2D6'),
            (link, 'FFECBE5C'),
            ('الجوال لازم يكون على نفس الواي فاي', 'FF98A2B3')])
        holder['w'] = w
        w.doModal()
        del w
    finally:
        srv.shutdown()
        srv.server_close()
    if state['ok']:
        DLG.notification(ADDON_NAME, 'Whisper جاهز ✓ — بيضبط الترجمة على كلام الفيلم', time=5000)
    return state['ok']
