# -*- coding: utf-8 -*-
"""Redraw the text of Najd's guide slides in Modern Standard Arabic (Piers edition).
python3 najd_guide_fusha.py <guide_dir_in> <guide_dir_out> <font_dir>"""
import os, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

SRC, DST, FD = sys.argv[1:4]
F = lambda w, s: ImageFont.truetype(os.path.join(FD, 'plex_%s.ttf' % w), s, layout_engine=ImageFont.Layout.RAQM)
WHITE, GOLD, GRAY, KGOLD = (244, 250, 252), (232, 190, 96), (150, 156, 160), (204, 187, 131)


def erase(img, box, thr=28, flat=False):
    a = np.asarray(img.convert('RGB')).copy()
    x0, y0, x1, y1 = box
    reg = a[y0:y1, x0:x1].astype(int)
    if flat:      # a mock-up panel: one flat colour, taken from the box's edges
        edge = np.concatenate([reg[0], reg[-1], reg[:, 0], reg[:, -1]])
        bg = np.median(edge, axis=0)[None, None, :]
    else:
        bg = np.dstack([cv2.medianBlur(np.ascontiguousarray(reg[:, :, c]).astype(np.uint8), 61)
                        for c in range(3)]).astype(int)
    m = (np.abs(reg - bg).max(axis=2) > thr).astype(np.uint8) * 255
    m = cv2.dilate(m, np.ones((7, 7), np.uint8))
    mask = np.zeros(a.shape[:2], np.uint8)
    mask[y0:y1, x0:x1] = m
    out = cv2.inpaint(cv2.cvtColor(a, cv2.COLOR_RGB2BGR), mask, 7, cv2.INPAINT_TELEA)
    return Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))


def runs(d, x_right, y, segs, font, anchor='rm'):
    """segs: [(text, colour)] in reading order; drawn right to left."""
    x = x_right
    for text, col in segs:
        w = d.textlength(text, font=font, direction='rtl')
        d.text((x, y), text, font=font, fill=col, anchor=anchor, direction='rtl')
        x -= w
    return x


def centre(d, xc, y, text, font, col, shadow=False):
    w = d.textlength(text, font=font, direction='rtl')
    if shadow:
        d.text((xc + w / 2 + 2, y + 2), text, font=font, fill=(0, 0, 0), anchor='rm', direction='rtl')
    d.text((xc + w / 2, y), text, font=font, fill=col, anchor='rm', direction='rtl')


def S(*parts):
    """'text', ('gold text',) -> segments"""
    return [(p[0], GOLD) if isinstance(p, tuple) else (p, WHITE) for p in parts]


BUL = F('400', 23)
TITLE = F('700', 40)
KICK = F('500', 18)
TXR = 1166                      # right edge of bullet text (circles at 1180-1215)

SLIDES = {
    1: dict(bullets=[(320, S('تبحث لك عن ', ('ترجمة عربية',), ' في أكثر من موقع')),
                     (378, S('تصحّح النص العربي: الحروف والترقيم والإعلانات')),
                     (436, S('تضبط التوقيت على ', ('صوت الفيلم',), ' تلقائياً')),
                     (496, S('وتترجم الترجمة المدمجة بالذكاء الاصطناعي'))],
            area=(600, 295, 1176, 525)),
    2: dict(bullets=[(325, S('شغّل الفيلم واضغط ', ('OK',), ' لتظهر الأزرار')),
                     (381, S('اختر أيقونة ', ('الترجمة',))),
                     (437, S('اختر ', ('تحميل',))),
                     (493, S('اختر ', ('ترجمة نجد الذكية',)))],
            area=(600, 290, 1176, 530)),
    3: dict(bullets=[(308, S('الخيارات ', ('الذهبية',), ' في الأعلى أدوات:')),
                     (343, S('الترجمة المدمجة وإعادة ضبط التوقيت')),
                     (399, S('تحتها الترجمات من المواقع')),
                     (455, S(('النجوم',), ' = مدى قرب الترجمة من نسخة فيلمك')),
                     (511, S('اختر واحدة، وتتولى الإضافة الباقي'))],
            area=(600, 285, 1176, 545),
            mock=[((380, 238, 575, 270), 'rm', 563, 253, 'أعد ضبط توقيت الترجمة الحالية', F('500', 17), GOLD)]),
    4: dict(title='بعد الاختيار',
            bullets=[(325, S('تعمل الترجمة ', ('فوراً',))),
                     (381, S('وفي الخلفية تستمع إلى الصوت وتضبط ', ('كل قسم',), ' على حدة')),
                     (437, S('عند الانتهاء تُستبدل الترجمة دون إيقاف الفيلم')),
                     (493, S('ويظهر لك تنبيه صغير بما حدث'))],
            area=(600, 290, 1176, 530),
            mock=[((295, 303, 545, 338), 'rm', 532, 317, 'جارٍ ضبط الترجمة مع الصوت...', F('400', 19), WHITE)]),
    5: dict(kicker='إذا لم يكن التوقيت مضبوطاً',
            bullets=[(325, S('افتح قائمة الترجمة مرة أخرى')),
                     (381, S('اختر ', ('أعد ضبط توقيت الترجمة الحالية',))),
                     (437, S('أو عدّل التأخير من ', ('إعدادات الترجمة',), ' في المشغّل')),
                     (493, S('لفرق ثابت في كل الترجمات: إعدادات نجد ثم «التوقيت»'))],
            area=(600, 290, 1176, 530),
            mock=[((150, 372, 520, 410), 'c', 333, 390, 'أين كنت طوال هذا الوقت؟', F('500', 22), WHITE),
                  ((150, 465, 520, 505), None, 0, 0, '', None, None)]),
    6: dict(bullets=[(325, S('في بعض الأفلام ترجمة إنجليزية ', ('داخل الملف',))),
                     (381, S('اضغط الخيار ', ('الذهبي',), ' في القائمة')),
                     (437, S('تُستخرج وتُترجم إلى العربية بالذكاء الاصطناعي')),
                     (493, S('توقيتها مضبوط 100٪، ولا تعمل إلا إذا طلبتها'))],
            area=(600, 290, 1176, 530),
            mock=[((240, 236, 430, 254), 'c', 333, 245, 'يحتوي على ترجمة إنجليزية مدمجة', F('400', 13), GRAY),
                  ((190, 472, 437, 500), 'rm', 436, 486, 'ترجمة عربية على التوقيت نفسه', F('500', 17), WHITE)]),
    7: dict(title='أمور مهمة مرة واحدة فقط',
            bullets=[(308, S(('معالج الإعداد',), ' في الإعدادات يجهّز كل شيء')),
                     (364, S('للذكاء الاصطناعي: مفتاح Gemini مجاني أو OpenRouter')),
                     (455, S('تحت كل خيار شرح من سطرين، قف عليه ليظهر')),
                     (511, S('أي مشكلة: قسم ', ('الدعم',), ' ثم «إرسال تقرير مشكلة»'))],
            area=(600, 285, 1176, 545)),
    8: dict(kicker='انتهينا',
            bullets=[(378, S('شغّل فيلمك واختر ترجمة نجد')),
                     (437, S('يمكنك العودة إلى هذا الشرح من إعدادات الإضافة'))],
            area=(600, 355, 1176, 465)),
}


def bands(img):
    a = np.asarray(img.convert('RGB')).astype(int)
    reg = a[:, 640:1260].mean(axis=2)
    on = (reg - np.median(reg, axis=1, keepdims=True)) > 60
    rows = on.sum(axis=1)
    out, s = [], None
    for y, v in enumerate(rows[:340]):
        if v and s is None:
            s = y
        if not v and s is not None:
            if y - s > 12:
                out.append((s, y))
            s = None
    merged = []
    for a0, a1 in out:
        if merged and a0 - merged[-1][1] < 8:
            merged[-1] = (merged[-1][0], a1)
        else:
            merged.append((a0, a1))
    return merged          # [kicker, title, ...]


for n, spec in SLIDES.items():
    img = Image.open(os.path.join(SRC, '%d.jpg' % n)).convert('RGB')
    b = bands(img)
    kick, title = b[0], b[1]
    if 'kicker' in spec:
        img = erase(img, (640, kick[0] - 6, 1230, kick[1] + 6))
    if 'title' in spec:
        img = erase(img, (620, title[0] - 6, 1235, title[1] + 6))
    img = erase(img, spec['area'])
    for box, *_ in spec.get('mock', []):
        img = erase(img, box, thr=22, flat=(n != 5))
    d = ImageDraw.Draw(img)
    if 'kicker' in spec:
        d.text((1214, (kick[0] + kick[1]) / 2), spec['kicker'], font=KICK, fill=KGOLD, anchor='rm', direction='rtl')
    if 'title' in spec:
        d.text((1216, (title[0] + title[1]) / 2), spec['title'], font=TITLE, fill=WHITE, anchor='rm', direction='rtl')
    for y, segs in spec['bullets']:
        runs(d, TXR, y, segs, BUL)
    for box, how, x, y, text, font, col in spec.get('mock', []):
        if not how:
            continue
        if how == 'c':
            centre(d, x, y, text, font, col, shadow=(n == 5))
        else:
            d.text((x, y), text, font=font, fill=col, anchor='rm', direction='rtl')
    img.save(os.path.join(DST, '%d.jpg' % n), quality=92)
    print('slide', n, 'kicker/title bands', kick, title)
