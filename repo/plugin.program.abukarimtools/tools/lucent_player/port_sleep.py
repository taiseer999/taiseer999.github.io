import sys
s = open(sys.argv[1], encoding='utf-8').read()
R = [
 ('NL = xbmc.getLanguage(xbmc.ISO_639_1) == "nl"', 'AR = xbmc.getLanguage(xbmc.ISO_639_1) == "ar"'),
 ('def t(en, nl):\n    return nl if NL else en', 'def t(en, ar):\n    return ar if AR else en'),
 ('t("after this one", "na deze")', 't("after this one", "بعد هذا العرض")'),
 ('t(f"{left} min left", f"nog {left} min")', 't(f"{left} min left", f"متبقٍّ {left} دقيقة")'),
 ('t("Sleep timer", "Slaaptimer")', 't("Sleep timer", "مؤقت النوم")'),
 ('t("Goodnight", "Welterusten")', 't("Goodnight", "تصبح على خير")'),
 ('t("After this episode", "Na deze aflevering")', 't("After this episode", "بعد هذه الحلقة")'),
 ('t("After this film", "Na deze film")', 't("After this film", "بعد هذا الفيلم")'),
 ('t(f"In {m} minutes", f"Over {m} minuten")', 't(f"In {m} minutes", f"بعد {m} دقيقة")'),
 ('t("Switch the sleep timer off", "Slaaptimer uitzetten")', 't("Switch the sleep timer off", "إيقاف مؤقت النوم")'),
 ('t("Off", "Uit")', 't("Off", "متوقف")'),
 ('"special://skin/media/buttons/sleep_nf.png"', 'ICON'),
 ('[skin.lucent] sleep', '[AbukarimTools LucentPlayer] sleep'),
]
for a, b in R:
    n = s.count(a)
    if not n: raise SystemExit('not found: ' + a)
    s = s.replace(a, b)
s = s.replace('MINUTES = (15, 30, 45, 60, 90)', 'MINUTES = (15, 30, 45, 60, 90)\nICON = "special://skin/media/abk_lp/buttons/sleep_nf.png"', 1)
s = s.replace('"""Lucent: sleep timer from the player menu (the moon button).',
  '"""AB Tools "AF3: Lucent Player" - the sleep timer of the player menu (the moon button).\nPort of scripts/sleep.py from the Lucent skin by djdirty60 (github.com/djdirty60/Lucent, GPL-2.0-or-later),\nEnglish / Arabic (Fusha) instead of English / Dutch.\n\n    RunScript(special://home/addons/plugin.program.abukarimtools/resources/lib/lucent_sleep.py)\n\nLucent: sleep timer from the player menu (the moon button).', 1)
s = s.replace('    RunScript(special://skin/scripts/sleep.py)\n', '', 1)
import re
assert not re.search(r'\bNL\b|Slaap|Welter|minuten|aflevering', s), 'dutch left'
open(sys.argv[2], 'w', encoding='utf-8').write(s)
