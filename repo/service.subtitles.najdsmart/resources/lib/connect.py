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
                msg = 'تم ✓ عد إلى كودي — Done, return to Kodi'
            else:
                msg = 'لم يصل أي رمز — No code received'
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
        DLG.ok(ADDON_NAME, 'تعذر تشغيل خادم الاستقبال على هذا الجهاز.')
        return None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    cb = 'http://localhost:%d/callback' % port
    url = 'https://openrouter.ai/auth?' + urllib.parse.urlencode(
        {'callback_url': cb, 'code_challenge': challenge, 'code_challenge_method': 'S256'})
    if not _open_browser(url):
        srv.shutdown()
        DLG.ok(ADDON_NAME, 'تعذر فتح المتصفح على هذا الجهاز.\nاستخدم «إدخال المفاتيح من الهاتف» بدلاً من ذلك.')
        return None
    prog = xbmcgui.DialogProgress()
    prog.create(ADDON_NAME, 'تم فتح OpenRouter في المتصفح:\nسجّل الدخول (أو أنشئ حساباً) واضغط Authorize، ثم عد إلى هنا.')
    key = None
    try:
        t0 = time.time()
        while time.time() - t0 < 600:
            if prog.iscanceled():
                break
            if 'code' in box:
                prog.update(90, 'جارٍ استلام المفتاح...')
                r = http('https://openrouter.ai/api/v1/auth/keys',
                         json_body={'code': box['code'], 'code_verifier': verifier,
                                    'code_challenge_method': 'S256'}, timeout=30)
                key = r.get('key')
                break
            prog.update(int((time.time() - t0) * 100 / 600), 'في انتظار تسجيل الدخول في المتصفح...')
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
        DLG.ok(ADDON_NAME, 'لم يكتمل تسجيل الدخول. حاول مرة أخرى.')
        return None
    a = xbmcaddon.Addon(ADDON_ID)
    a.setSetting('openrouter_key', key)
    order = [p for p in (a.getSetting('ai_order') or '').split(',') if p and p != 'openrouter']
    pos = 1 if order and order[0] == 'gemini' else 0
    order.insert(pos, 'openrouter')
    a.setSetting('ai_order', ','.join(order))
    DLG.ok(ADDON_NAME, 'تم ربط OpenRouter ✓\nوأصبح احتياطياً تلقائياً عند انتهاء حد Gemini.')
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
        hint = ('موجود (••••%s) — اتركه فارغاً للإبقاء عليه' % html.escape(cur[-4:])) if cur else 'الصق المفتاح هنا'
        rows.append('<label><b>%s</b> <a href="%s" target="_blank">احصل على مفتاح ↗</a>'
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
            '<p style="opacity:.6;font-size:12px">تعمل هذه الصفحة فقط ما دام كودي مفتوحاً على نافذة الاستقبال.</p>'
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
        DLG.ok(ADDON_NAME, 'تعذر تشغيل صفحة المفاتيح على هذا الجهاز.')
        return
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = 'http://%s:%d/%s' % (_lan_ip(), port, token)
    if sys.platform.startswith('win') or sys.platform == 'darwin':
        _open_browser('http://localhost:%d/%s' % (port, token))   # also open it right here
    DLG.ok(ADDON_NAME, 'افتح هذا الرابط من هاتفك أو أي جهاز متصل بالشبكة نفسها:\n'
                       '[B]%s[/B]\nالصق المفاتيح واضغط حفظ، ثم عد واضغط موافق.\n'
                       '(إذا سألك ويندوز عن جدار الحماية، فاختر «السماح»)' % url)
    srv.shutdown()
    if saved_all:
        DLG.notification(ADDON_NAME, 'تم الحفظ: %s ✓' % '، '.join(sorted(set(saved_all))), time=5000)
