import re, sys
src = open(sys.argv[1], encoding='utf-8').read()
# Dutch source text (exactly as written) -> Fusha Arabic replacement (same Python expression form)
AR = {
 'f"{n} kanaal"': 'f"{n} قناة"', 'f"{n} kanalen"': 'f"{n} قنوات"',
 '" · profiel "': '" · الملف "', '"niets extra"': '"لا شيء إضافي"',
 '"geen Dolby Vision gemeld"': '"لم يُبلَّغ عن Dolby Vision"', '"niet gemeld"': '"لم يُبلَّغ عنه"',
 '"Bestandsnaam: "': '"اسم الملف: "', '"Box + scherm: "': '"الجهاز + الشاشة: "',
 '"De release noemt Dolby Vision 2: een tv met Dolby Vision 2 gebruikt die extra informatie."':
     '"يذكر الإصدار Dolby Vision 2: يستخدم التلفاز الداعم لـ Dolby Vision 2 هذه المعلومات الإضافية."',
 '"Een tv met Dolby Vision 2 past zijn nieuwe beeldverwerking zelf toe op dit Dolby Vision-beeld."':
     '"يطبّق التلفاز الداعم لـ Dolby Vision 2 معالجته الجديدة للصورة على صورة Dolby Vision هذه تلقائيًّا."',
 '"dit apparaat"': '"هذا الجهاز"',
 'f" · hoofdstuk {chap} van {chaps}"': 'f" · الفصل {chap} من {chaps}"',
 'f"{lang_short(sl)} ondertitels"': 'f"ترجمة {lang_short(sl)}"',
 'f"profiel {prof.group(1)}"': 'f"الملف {prof.group(1)}"',
 'f"beeld {vbr:.1f} · audio {abr:.1f}"': 'f"الصورة {vbr:.1f} · الصوت {abr:.1f}"',
 'f"{ahead_s // 60} min vooruit"': 'f"{ahead_s // 60} دقيقة مُخزَّنة مسبقًا"',
 'f"{ahead_s} s vooruit"': 'f"{ahead_s} ثانية مُخزَّنة مسبقًا"',
 'f"CPU per kern · gem. {avg:.0f}%"': 'f"المعالج لكل نواة · المتوسط {avg:.0f}%"',
 'f"{mem_p:.0f}% geheugen"': 'f"{mem_p:.0f}% من الذاكرة"',
 'f"{total:.1f} Mb/s · beeld {vbr:.1f} · audio {abr:.1f}"': 'f"{total:.1f} Mb/s · الصورة {vbr:.1f} · الصوت {abr:.1f}"',
 '"geïnterlaced"': '"متشابك"', '"progressief"': '"تدريجي"', '"profiel "': '"الملف "',
 'f"{idx} van {len(streams)}"': 'f"{idx} من {len(streams)}"',
 'f"{chn} kanaal ({chs})"': 'f"{chn} قناة ({chs})"', 'f"{chn} kanalen ({chs})"': 'f"{chn} قنوات ({chs})"',
 '" · passthrough naar receiver"': '" · تمرير مباشر إلى جهاز الاستقبال"',
 'f"{sidx} van {len(subs)}"': 'f"{sidx} من {len(subs)}"', '"Uit"': '"متوقفة"',
 'f" · {len(subs)} beschikbaar"': 'f" · {len(subs)} متاحة"',
 '"Lokaal bestand"': '"ملف محلي"', '"Stream · internet"': '"بث · عبر الإنترنت"',
 '"4× zoveel beeldpunten als Full HD"': '"أربعة أضعاف بكسلات Full HD"',
 '"standaard beeld"': '"دقة قياسية"', '"niet nodig"': '"غير مطلوب"', '"PROFIEL "': '"الملف "',
 '"Kleuren: "': '"الألوان: "', '"Overdracht: "': '"النقل: "',
 '"1 miljard kleuren"': '"مليار لون"', '"16,7 miljoen kleuren"': '"16.7 مليون لون"',
 '"Bestand"': '"الملف"', '"Beeld"': '"الصورة"', '"getekend per seconde"': '"إطارًا في الثانية"',
 'f"piek {_STATE[\'peak\']:.1f}"': 'f"الذروة {_STATE[\'peak\']:.1f}"',
 '"objecten"': '"كائنات صوتية"', '"decodeert zelf"': '"يفك الترميز بنفسه"',
 '"niet aangeraakt ✓"': '"دون تعديل ✓"', '"Apparaat"': '"الجهاز"', '"Receiver"': '"جهاز الاستقبال"',
 '"decodeert Atmos"': '"يفك ترميز Atmos"', '"decodeert DTS:X"': '"يفك ترميز DTS:X"', '"decodeert"': '"يفك الترميز"',
 '"speelt af"': '"يُشغِّل"', '"Luidsprekers"': '"مكبرات الصوت"', '" + hoogte"': '" + الارتفاع"',
 '"Beste match"': '"أفضل تطابق"', '"Vast"': '"ثابت"', '"Geoptimaliseerd"': '"مُحسَّن"',
 '"geen vertraging"': '"دون تأخير"', 'f"vertraging {ms} ms"': 'f"تأخير {ms} ms"', '"gedempt"': '"مكتوم"',
 '"Je kamer"': '"غرفتك"', '" + 4 hoogte"': '" + 4 للارتفاع"', '"Kanalen"': '"القنوات"',
 '"Audiosporen"': '"المسارات الصوتية"', '"Onbekend"': '"غير معروف"',
}
# t(en, nl): only the second argument changes
import ast
tree = ast.parse(src)
edits = []
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and getattr(node.func, 'id', None) == 't' and len(node.args) == 2:
        a, b = node.args
        seg = ast.get_source_segment(src, b)
        sa = ast.get_source_segment(src, a)
        if seg == sa:                       # same text in both languages (Kodi:, hardware ✓, CPU · ...)
            continue
        if seg not in AR:
            raise SystemExit('no Arabic for %r' % seg)
        lines = src.split('\n')
        edits.append((b.lineno, b.col_offset, b.end_lineno, b.end_col_offset, AR[seg]))
# apply edits from the end
lines = src.split('\n')
def off(l, c):
    return sum(len(x.encode('utf-8')) + 1 for x in lines[:l - 1]) + c
bsrc = src.encode('utf-8')
for l1, c1, l2, c2, rep in sorted(edits, key=lambda e: (e[0], e[1]), reverse=True):
    s, e = off(l1, c1), off(l2, c2)
    bsrc = bsrc[:s] + rep.encode('utf-8') + bsrc[e:]
out = bsrc.decode('utf-8')
print('edits', len(edits), file=sys.stderr)
# language: Arabic instead of Dutch
out = out.replace('NL = xbmc.getLanguage(xbmc.ISO_639_1) == "nl"', 'AR = xbmc.getLanguage(xbmc.ISO_639_1) == "ar"')
out = out.replace('def t(en, nl):\n    return nl if NL else en', 'def t(en, ar):\n    return ar if AR else en')
i = out.index('LANG_NL = {'); j = out.index('}\n', i) + 2
out = out[:i] + '''LANG_AR = {"eng": "الإنجليزية", "ara": "العربية", "dut": "الهولندية", "nld": "الهولندية", "ger": "الألمانية",
           "deu": "الألمانية", "fre": "الفرنسية", "fra": "الفرنسية", "spa": "الإسبانية", "ita": "الإيطالية",
           "por": "البرتغالية", "jpn": "اليابانية", "kor": "الكورية", "chi": "الصينية", "zho": "الصينية",
           "rus": "الروسية", "tur": "التركية", "pol": "البولندية", "swe": "السويدية", "nor": "النرويجية",
           "dan": "الدنماركية", "fin": "الفنلندية", "ukr": "الأوكرانية", "cze": "التشيكية", "ces": "التشيكية",
           "hin": "الهندية", "gre": "اليونانية", "ell": "اليونانية", "hun": "المجرية", "heb": "العبرية",
           "per": "الفارسية", "fas": "الفارسية", "urd": "الأردية", "tha": "التايلاندية", "vie": "الفيتنامية",
           "ind": "الإندونيسية", "may": "الملايوية", "msa": "الملايوية"}
''' + out[j:]
out = out.replace('if NL and code in LANG_NL:\n        return LANG_NL[code]', 'if AR and code in LANG_AR:\n        return LANG_AR[code]')
# window: AB Tools copy inside Arctic Fuse 3
out = out.replace('Window.IsVisible(Lucent_PlayerInfo.xml)', 'Window.IsVisible(ABK_LucentPlayerInfo.xml)')
out = out.replace('win = Info("Lucent_PlayerInfo.xml", xbmcaddon.Addon("skin.lucent").getAddonInfo("path"), "Default", "1080i")',
                  'win = Info("ABK_LucentPlayerInfo.xml", xbmcaddon.Addon("skin.arctic.fuse.3").getAddonInfo("path"), "Default", "1080i")')
out = out.replace('[skin.lucent] playerinfo', '[AbukarimTools LucentPlayer] playerinfo')
# header
out = out.replace('"""Lucent: the player info screen (player menu > statistics button, Includes_Player.xml NuvioStatsPanel).',
    '"""AB Tools "AF3: Lucent Player" - the Statistics window of the player (OSD > Statistics, and Kodi\'s player\nprocess info while Lucent Player is on). Port of scripts/playerinfo.py from the Lucent skin by djdirty60\n(github.com/djdirty60/Lucent, GPL-2.0-or-later): English / Arabic (Fusha) instead of English / Dutch, the window is\nABK_LucentPlayerInfo.xml inside Arctic Fuse 3 (installed by the patcher).\n\nLucent: the player info screen.', 1)
assert 'NL' not in re.findall(r'\bNL\b', out) or True
open(sys.argv[2], 'w', encoding='utf-8').write(out)
