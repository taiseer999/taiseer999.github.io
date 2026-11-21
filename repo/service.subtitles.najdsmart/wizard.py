# -*- coding: utf-8 -*-
"""Setup wizard — everything is done from inside Kodi.
Run from: Add-ons → Program add-ons → ترجمة نجد الذكية  (also opens on first start)."""
import json
import os
import sys

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.common import ADDON_ID, ADDON_NAME, log
from resources.lib import checks, audiosync

ADDON = xbmcaddon.Addon(ADDON_ID)
DLG = xbmcgui.Dialog()

KEYS = [
    # id, title, where to get it, url
    ('subdl_key', 'SubDL', 'سجّل في subdl.com ثم افتح صفحة API وانسخ المفتاح', 'https://subdl.com/panel/api'),
    ('subsource_key', 'SubSource', 'سجّل في subsource.net ثم افتح تبويب API وأنشئ مفتاحاً', 'https://subsource.net/api-docs'),
    ('os_key', 'OpenSubtitles', 'سجّل في opensubtitles.com ثم Consumers ← New consumer وانسخ API key', 'https://www.opensubtitles.com/consumers'),
    ('gemini_key', 'Gemini (الذكاء الاصطناعي)', 'سجّل بحساب Google في aistudio.google.com ثم Create API key', 'https://aistudio.google.com/apikey'),
]

AI_EXTRA = [
    ('deepseek_key', 'DeepSeek', 'رخيص جداً — platform.deepseek.com ثم API keys', 'https://platform.deepseek.com/api_keys'),
    ('openai_key', 'ChatGPT', 'platform.openai.com ثم API keys (مدفوع)', 'https://platform.openai.com/api-keys'),
    ('claude_key', 'Claude', 'console.anthropic.com ثم API keys (مدفوع)', 'https://console.anthropic.com/settings/keys'),
    ('grok_key', 'Grok', 'console.x.ai ثم API keys', 'https://console.x.ai'),
    ('openrouter_key', 'OpenRouter', 'مفتاح واحد لعشرات النماذج، ومنها نماذج مجانية', 'https://openrouter.ai/keys'),
    ('groq_key', 'Groq', 'سريع جداً ويوفر خطة مجانية', 'https://console.groq.com/keys'),
    ('mistral_key', 'Mistral', 'يوفر خطة مجانية', 'https://console.mistral.ai/api-keys'),
]


def rpc(method, params):
    q = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
    return json.loads(xbmc.executeJSONRPC(q))


def set_defaults():
    """Make this add-on Kodi's default subtitle service and add Arabic to search languages."""
    ok = True
    for sid in ('subtitles.movie', 'subtitles.tv'):
        r = rpc('Settings.SetSettingValue', {'setting': sid, 'value': ADDON_ID})
        ok = ok and 'error' not in r
    langs = rpc('Settings.GetSettingValue', {'setting': 'subtitles.languages'}).get('result', {}).get('value') or []
    if 'Arabic' not in langs:
        rpc('Settings.SetSettingValue', {'setting': 'subtitles.languages', 'value': ['Arabic'] + list(langs)})
    return ok


def open_url(url):
    try:
        if sys.platform.startswith('win'):
            os.startfile(url)
            return True
        if sys.platform == 'darwin':
            os.system('open "%s"' % url)
            return True
        if not xbmc.getCondVisibility('System.Platform.Android'):
            os.system('xdg-open "%s" >/dev/null 2>&1 &' % url)
            return True
        xbmc.executebuiltin('StartAndroidActivity("","android.intent.action.VIEW","","%s")' % url)
        return True
    except Exception as e:
        log('open url failed: %s' % e)
        return False


def ask_key(kid, title, how, url):
    cur = ADDON.getSetting(kid)
    while True:
        opts = ['اكتب المفتاح أو الصقه', 'افتح موقع المفتاح في المتصفح', 'تخطي']
        if cur:
            opts = ['أبقِ المفتاح الحالي (••••%s)' % cur[-4:]] + opts
        head = '%s — %s' % (title, how)
        sel = DLG.select(head, opts)
        if sel < 0 or opts[sel] == 'تخطي':
            return cur
        if opts[sel].startswith('أبقِ'):
            return cur
        if opts[sel].startswith('افتح'):
            if open_url(url):
                DLG.ok(ADDON_NAME, 'تم فتح الموقع في المتصفح.\nانسخ المفتاح ثم عد إلى كودي والصقه (Ctrl+V).')
            else:
                DLG.ok(ADDON_NAME, 'افتح هذا الرابط من هاتفك أو حاسوبك:\n[B]%s[/B]' % url)
            continue
        val = DLG.input('الصق مفتاح %s' % title, cur).strip()
        if val:
            ADDON.setSetting(kid, val)
            return val


def test_all(show=True):
    a = xbmcaddon.Addon(ADDON_ID)
    rows = []
    prog = xbmcgui.DialogProgress()
    prog.create(ADDON_NAME, 'جارٍ الفحص...')
    tests = []
    if a.getSetting('subdl_key'):
        tests.append(('SubDL', lambda: checks.check_subdl(a.getSetting('subdl_key'))))
    if a.getSetting('subsource_key'):
        tests.append(('SubSource', lambda: checks.check_subsource(a.getSetting('subsource_key'))))
    if a.getSetting('os_key'):
        tests.append(('OpenSubtitles', lambda: checks.check_opensubtitles(
            a.getSetting('os_key'), a.getSetting('os_user'), a.getSetting('os_pass'))))
    from resources.lib import llm
    for pid in llm.configured():
        tests.append((llm.name(pid), (lambda p: (lambda: llm.check(p)))(pid)))
    try:
        from resources.lib.providers import kodiaddons
        names = [n for _i, n in kodiaddons.installed()]
    except Exception:
        names = []
    if names and a.getSetting('use_kodi_addons') != 'false':
        rows.append('[COLOR lime]●[/COLOR]  إضافات ترجمة مثبتة تُستخدم دون مفاتيح: %s' % '، '.join(names))
    tests.append(('قراءة الصوت', lambda: checks.check_audio(a.getSetting('ffmpeg_path'))))
    for n, (name, fn) in enumerate(tests):
        prog.update(int(n * 100 / len(tests)), 'فحص %s...' % name)
        ok, msg = fn()
        rows.append('[COLOR %s]%s[/COLOR]  %s: %s' % ('lime' if ok else 'red', '●', name, msg))
    prog.close()
    if not names and not any(a.getSetting(k) for k in ('subdl_key', 'subsource_key', 'os_key')):
        rows.insert(0, '[COLOR red]●[/COLOR]  لا يوجد أي مصدر للترجمة، يلزم مفتاح واحد على الأقل')
    if show:
        DLG.textviewer(ADDON_NAME + ' — نتيجة الفحص', '\n'.join(rows))
    return rows


def wizard():
    DLG.ok(ADDON_NAME, 'مرحباً! هذا معالج الإعداد، وسيجهّز كل شيء من داخل كودي:\n'
                       '١) يجعل الإضافة خدمة الترجمة الأساسية\n٢) تُدخل مفاتيح المواقع (اختياري — إذا كانت لديك إضافات ترجمة أخرى فسيستخدمها)\n٣) يتحقق من أن كل شيء يعمل')
    if set_defaults():
        xbmcgui.Dialog().notification(ADDON_NAME, 'أصبحت خدمة الترجمة الأساسية ✓', time=3000)
    for kid, title, how, url in KEYS:
        ask_key(kid, title, how, url)
        if kid == 'os_key' and ADDON.getSetting('os_key'):
            if DLG.yesno(ADDON_NAME, 'هل لديك حساب في OpenSubtitles وتريد إدخاله؟ (يزيد عدد التنزيلات اليومية)'):
                u = DLG.input('اسم المستخدم', ADDON.getSetting('os_user')).strip()
                p = DLG.input('كلمة المرور', option=xbmcgui.ALPHANUM_HIDE_INPUT).strip()
                if u and p:
                    ADDON.setSetting('os_user', u)
                    ADDON.setSetting('os_pass', p)
    from resources.lib import connect
    choice = DLG.select('ذكاء اصطناعي احتياطي (يعمل عند انتهاء حد Gemini)', [
        'تسجيل الدخول إلى OpenRouter بضغطة (مجاني، دون نسخ مفاتيح)',
        'لصق المفاتيح من الهاتف أو المتصفح (ChatGPT، Claude، DeepSeek، Grok...)',
        'كتابة المفاتيح هنا بجهاز التحكم',
        'تخطي'])
    if choice == 0:
        connect.openrouter_login()
    elif choice == 1:
        connect.key_form()
    elif choice == 2:
        sel = DLG.multiselect('اختر الخدمات التي لديك مفاتيحها', ['%s — %s' % (t, h) for _k, t, h, _u in AI_EXTRA])
        for i in (sel or []):
            ask_key(*AI_EXTRA[i])
    ADDON.setSetting('wizard_done', 'true')
    test_all()
    DLG.ok(ADDON_NAME, 'انتهى الإعداد ✓\nشغّل أي فيلم أو حلقة وستصلك الترجمة تلقائياً.\n'
                       'يمكنك العودة إلى هذا المعالج من: الإضافات ← إضافات البرامج ← %s' % ADDON_NAME)


def _subtitle_files_summary():
    """For each subtitle made recently: line count and where it has long empty stretches,
    so 'no subtitles at minute 7' can be seen in the report."""
    out = []
    try:
        from resources.lib.common import TEMP_DIR
        from resources.lib import subtitle, arabic
        names = sorted((n for n in os.listdir(TEMP_DIR) if n.endswith('.srt')),
                       key=lambda n: os.path.getmtime(os.path.join(TEMP_DIR, n)))[-8:]
        for n in names:
            with open(os.path.join(TEMP_DIR, n), 'rb') as f:
                cues = subtitle.parse(arabic.decode(f.read()))
            gaps = ['%d:%02d+%ds' % (cues[i].end // 60000, cues[i].end // 1000 % 60,
                                     (cues[i + 1].start - cues[i].end) // 1000)
                    for i in range(len(cues) - 1) if cues[i + 1].start - cues[i].end > 60000]
            first = cues[0].start // 1000 if cues else 0
            out.append('file %s: %d lines, first %d:%02d, empty >60s at %s' % (
                n[-40:], len(cues), first // 60, first % 60, ', '.join(gaps[:12]) or '-'))
    except Exception as e:
        out.append('files: %s' % e)
    return out + ([''] if out else [])


def report():
    """Collect this add-on's log lines (keys/links hidden) into a file on the Desktop."""
    import re
    import time
    import xbmcvfs
    from resources.lib.common import redact
    logdir = xbmcvfs.translatePath('special://logpath')
    lines = []
    for name in ('kodi.old.log', 'kodi.log'):
        p = os.path.join(logdir, name)
        if not os.path.exists(p):
            continue
        with open(p, encoding='utf-8', errors='replace') as f:
            keep = 0
            for line in f:
                hit = ADDON_ID in line
                if hit or (keep and (line.startswith((' ', '\t', 'Traceback')) or 'Error' in line)):
                    lines.append(redact(line.rstrip()))
                    keep = 25 if ('Traceback' in line or 'ERROR' in line) else max(0, keep - 1)
                    if hit and ('ERROR' in line or 'failed' in line):
                        keep = 25
                elif keep:
                    keep -= 1
        lines.append('---- end of %s ----' % name)
    a = xbmcaddon.Addon(ADDON_ID)
    head = ['Najd Smart Subs %s | Kodi %s | %s' % (a.getAddonInfo('version'),
            xbmc.getInfoLabel('System.BuildVersion'), sys.platform),
            'settings: sync=%s ai=%s | subtitle keys: subdl=%s subsource=%s os=%s' % (
                a.getSetting('sync_method'), a.getSetting('ai_fix'),
                bool(a.getSetting('subdl_key')), bool(a.getSetting('subsource_key')),
                bool(a.getSetting('os_key'))),
            'AI keys: %s | order: %s' % (
                ', '.join(p for p in ('gemini', 'deepseek', 'openai', 'claude', 'grok', 'openrouter',
                                      'groq', 'mistral') if a.getSetting(p + '_key')) or 'none',
                a.getSetting('ai_order') or 'default'), '']
    head += _subtitle_files_summary()
    text = '\n'.join(head + lines[-1500:])
    desk = os.path.join(os.environ.get('USERPROFILE', os.path.expanduser('~')), 'Desktop')
    if not os.path.isdir(desk):
        desk = xbmcvfs.translatePath('special://profile')   # CoreELEC/LibreELEC: \\<box>\Userdata
    out = os.path.join(desk, 'najd-report.txt')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(text)
    try:
        from resources.lib import sharereport
        if sharereport.share(text, out):
            return
    except Exception as e:
        log('report QR failed: %s' % e)
    DLG.ok(ADDON_NAME, 'تم إنشاء التقرير ✓ (دون مفاتيح أو روابط)\n[B]%s[/B]\n'
                       'أرسل هذا الملف في المحادثة.' % out)


def menu():
    opts = ['معالج الإعداد (المفاتيح والخدمة الأساسية)',
            'تسجيل الدخول إلى OpenRouter بضغطة (ذكاء اصطناعي مجاني)',
            'إدخال المفاتيح من الهاتف أو المتصفح', 'فحص المفاتيح والاتصال',
            'فتح الإعدادات', 'مسح الذاكرة المؤقتة (الترجمات والأصوات المحفوظة)',
            'إنشاء تقرير مشكلة (ملف على سطح المكتب)']
    sel = DLG.select(ADDON_NAME, opts)
    from resources.lib import connect
    if sel == 1:
        connect.openrouter_login()
        return
    if sel == 2:
        connect.key_form()
        return
    if sel > 2:
        sel -= 2
    if sel == 0:
        wizard()
    elif sel == 1:
        test_all()
    elif sel == 2:
        ADDON.openSettings()
    elif sel == 3:
        from resources.lib.common import CACHE_DIR
        for f in os.listdir(CACHE_DIR):
            try:
                os.remove(os.path.join(CACHE_DIR, f))
            except OSError:
                pass
        DLG.notification(ADDON_NAME, 'تم المسح ✓', time=2500)
    elif sel == 4:
        report()


if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else ''
    if arg == 'guide':
        from resources.lib import guide
        guide.show()
    elif arg == 'wizard':
        wizard()
    elif arg == 'clearcache':
        from resources.lib.common import CACHE_DIR
        for f in os.listdir(CACHE_DIR):
            try:
                os.remove(os.path.join(CACHE_DIR, f))
            except OSError:
                pass
        DLG.notification(ADDON_NAME, 'تم المسح ✓', time=2500)
    elif arg == 'test':
        test_all()
    elif arg == 'report':
        report()
    elif arg == 'openrouter':
        from resources.lib import connect
        connect.openrouter_login()
    elif arg == 'keyform':
        from resources.lib import connect
        connect.key_form()
    elif arg == 'defaults':
        if set_defaults():
            DLG.notification(ADDON_NAME, 'أصبحت خدمة الترجمة الأساسية ✓', time=3000)
    else:
        menu()
