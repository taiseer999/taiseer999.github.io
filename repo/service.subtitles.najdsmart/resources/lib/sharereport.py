# -*- coding: utf-8 -*-
"""Send the problem report from the phone: a QR on the TV opens a page where you
write the problem in your own words, then copy / WhatsApp / download it.
Works on boxes with no desktop (CoreELEC/LibreELEC). Same Wi-Fi only; the page
lives only while the QR card is on screen, behind a random token."""
import html
import json
import os
import secrets
import struct
import threading
import urllib.parse
import zlib
from http.server import BaseHTTPRequestHandler

import xbmcgui
import xbmcvfs

from .common import ADDON, ADDON_NAME, TEMP_DIR, log
from .connect import _free_server, _lan_ip

MEDIA = os.path.join(ADDON.getAddonInfo('path'), 'resources', 'media')


def _png(matrix, scale=10, border=4):
    n = len(matrix)
    size = (n + 2 * border) * scale
    rows = []
    for y in range(size):
        my = y // scale - border
        row = bytearray([0])
        for x in range(size):
            mx = x // scale - border
            row.append(0 if (0 <= mx < n and 0 <= my < n and matrix[my][mx]) else 255)
        rows.append(bytes(row))

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 0, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b''.join(rows), 9)) + chunk(b'IEND', b''))


def qr_png(text):
    from .qrcodegen import QrCode
    q = QrCode.encode_text(text, QrCode.Ecc.MEDIUM)
    m = [[q.get_module(x, y) for x in range(q.get_size())] for y in range(q.get_size())]
    path = os.path.join(TEMP_DIR, 'qr_%08x.png' % (zlib.crc32(text.encode('utf-8')) & 0xffffffff))
    with open(path, 'wb') as f:
        f.write(_png(m))
    return path


PAGE = '''<!doctype html><html dir="rtl" lang="ar"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>تقرير ترجمة نجد</title>
<style>
body{font-family:system-ui,sans-serif;background:#0f1724;color:#eef;margin:0;padding:18px;line-height:1.6}
h1{color:#ecbe5c;font-size:21px;margin:0 0 6px}
p{margin:6px 0;color:#b8c2d6;font-size:14px}
textarea{width:100%%;box-sizing:border-box;border-radius:12px;border:1px solid #345;background:#16233a;
color:#fff;font-size:17px;padding:12px;font-family:inherit}
#note{height:140px}
button,a.b{display:block;width:100%%;box-sizing:border-box;padding:14px;border:0;border-radius:12px;
font-size:18px;font-weight:bold;margin-top:10px;text-align:center;text-decoration:none;font-family:inherit}
.g{background:#ecbe5c;color:#111}.w{background:#25d366;color:#08210f}.s{background:#24324d;color:#eef}
.ok{background:#173d27;padding:10px;border-radius:10px;display:none;margin-top:10px}
details{margin-top:14px;color:#9aa6bd}pre{white-space:pre-wrap;font-size:11px;direction:ltr;text-align:left;
background:#0a111c;padding:10px;border-radius:10px;max-height:300px;overflow:auto}
</style>
<h1>تقرير مشكلة — ترجمة نجد</h1>
<p>صف ما حدث بأسلوبك (اسم الفيلم، وما ضغطت عليه، وما ظهر لك). لا يحتوي التقرير على مفاتيح أو روابط.</p>
<textarea id="note" placeholder="مثال: ضغطت على ترجمة الترجمة المدمجة، فتوقفت عند ٥٠٪ وظهر خطأ..."></textarea>
<button class="g" onclick="copyAll()">نسخ التقرير كامل</button>
<a class="b w" id="wa" href="#" onclick="return wa()">إرسال بالواتساب</a>
<button class="s" onclick="dl()">تنزيل ملف التقرير</button>
<div class="ok" id="ok"></div>
<details><summary>عرض التقرير (%(n)d سطراً)</summary><pre id="rep"></pre></details>
<textarea id="tmp" style="position:fixed;top:-1000px;height:10px"></textarea>
<script>
var REP=%(rep)s, TOKEN=%(tok)s;
document.getElementById('rep').textContent=REP;
function full(){var n=document.getElementById('note').value.trim();
 return 'وصف المشكلة:\\n'+(n||'(لم يُكتب وصف)')+'\\n\\n==== التقرير ====\\n'+REP;}
function sendNote(){var n=document.getElementById('note').value.trim(); if(!n)return;
 var x=new XMLHttpRequest();x.open('POST','/'+TOKEN+'/note');x.send(n);}
function ok(t){var o=document.getElementById('ok');o.textContent=t;o.style.display='block';}
function copyAll(){sendNote();var t=document.getElementById('tmp');t.value=full();t.select();
 t.setSelectionRange(0,t.value.length);var done=false;try{done=document.execCommand('copy');}catch(e){}
 ok(done?'✓ تم النسخ — الصقه في المحادثة':'تعذر النسخ التلقائي: افتح «عرض التقرير» وانسخه يدوياً');}
function wa(){sendNote();var t=full();if(t.length>6000)t=t.slice(0,1200)+'\\n...\\n'+t.slice(-4600);
 location.href='https://wa.me/?text='+encodeURIComponent(t);return false;}
function dl(){sendNote();var b=new Blob([full()],{type:'text/plain;charset=utf-8'});
 var a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='najd-report.txt';
 document.body.appendChild(a);a.click();ok('✓ تم تنزيل الملف — تجده في مجلد التنزيلات، أرسله في المحادثة');}
</script></html>'''


class QRCard(xbmcgui.WindowDialog):
    def __init__(self, link, extra):
        super().__init__()
        white = os.path.join(MEDIA, 'white.png')
        self.addControl(xbmcgui.ControlImage(0, 0, 1280, 720, white, colorDiffuse='E60B111B'))
        self.addControl(xbmcgui.ControlImage(370, 50, 540, 620, white, colorDiffuse='FF141C2A'))
        self.addControl(xbmcgui.ControlLabel(370, 70, 540, 40, '[B]تقرير مشكلة — ترجمة نجد[/B]',
                                             textColor='FFECBE5C', alignment=0x00000002))
        self.addControl(xbmcgui.ControlImage(490, 120, 300, 300, qr_png(link)))
        self.addControl(xbmcgui.ControlLabel(370, 435, 540, 30, 'امسح الرمز بكاميرا الهاتف',
                                             textColor='FFF4F1EA', alignment=0x00000002))
        self.addControl(xbmcgui.ControlLabel(370, 470, 540, 30, 'صف المشكلة ثم اضغط نسخ أو واتساب',
                                             textColor='FFB8C2D6', alignment=0x00000002))
        self.addControl(xbmcgui.ControlLabel(370, 510, 540, 30, link,
                                             textColor='FFECBE5C', alignment=0x00000002))
        self.addControl(xbmcgui.ControlLabel(380, 550, 520, 60, extra, textColor='FF98A2B3',
                                             alignment=0x00000002))
        self.addControl(xbmcgui.ControlLabel(370, 625, 540, 30, 'يجب أن يكون الهاتف على الشبكة نفسها — رجوع للإغلاق',
                                             textColor='FF98A2B3', alignment=0x00000002))

    def onAction(self, action):
        if action.getId() in (9, 10, 13, 92, 110, 7, 100, 101):
            self.close()


def share(text, saved_path):
    token = secrets.token_urlsafe(6)
    page = (PAGE % {'rep': json.dumps(text, ensure_ascii=False).replace('</', '<\\/'),
                    'tok': json.dumps(token), 'n': text.count('\n') + 1}).encode('utf-8')
    notes = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, body, code=200, ctype='text/html; charset=utf-8'):
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.strip('/') != token:
                return self._send(b'404', 404, 'text/plain')
            self._send(page)

        def do_POST(self):
            if self.path.strip('/') != token + '/note':
                return self._send(b'404', 404, 'text/plain')
            n = int(self.headers.get('Content-Length') or 0)
            if 0 < n < 20000:
                note = self.rfile.read(n).decode('utf-8', 'replace').strip()
                if note and note not in notes:
                    notes.append(note)
                    try:
                        with open(saved_path, 'w', encoding='utf-8') as f:
                            f.write('وصف المشكلة:\n%s\n\n==== التقرير ====\n%s' % (note, text))
                    except OSError:
                        pass
            self._send(b'ok', 200, 'text/plain')

    try:
        srv, port = _free_server(H, '0.0.0.0', range(8790, 8820))
    except OSError:
        return False
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    link = 'http://%s:%d/%s' % (_lan_ip(), port, token)
    log('report page ready on port %d' % port)
    try:
        w = QRCard(link, 'وتوجد نسخة محفوظة على الجهاز: ' + os.path.basename(saved_path))
        w.doModal()
        del w
    finally:
        srv.shutdown()
        srv.server_close()
    if notes:
        xbmcgui.Dialog().notification(ADDON_NAME, 'تم استلام وصف المشكلة ✓', time=3000)
    return True
