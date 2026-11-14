"""Last step after port.py / af3_layout.py / af3_furniture.py (4.8.69):
route every Lucent pill texture (abk_lp/flags/X.png) through ABK_LP_FlagDir so
"AF3: OSD Flags Style" can swap the Lucent Player's pills for another badge set
(resource.images.af3.frbadges/<style>/lucent_player/X.png, same file names).
Skin.String(abk.flagstyle) empty = the Lucent pills (Automatic / Lucent).
Idempotent.  Usage: python3 af3_flagstyle.py .../Includes_ABK_LucentPlayer.xml
"""
import sys

VAR = '''<!-- 4.8.69: AF3 OSD Flags Style (af3_flagstyle.py) -->
    <variable name="ABK_LP_FlagDir">
        <value condition="!String.IsEmpty(Skin.String(abk.flagstyle)) + System.AddonIsEnabled(resource.images.af3.frbadges)">resource://resource.images.af3.frbadges/$INFO[Skin.String(abk.flagstyle)]/lucent_player</value>
        <value>abk_lp/flags</value>
    </variable>
'''


def main(path):
    s = open(path, encoding='utf-8').read()
    s = s.replace('abk_lp/flags/', '$VAR[ABK_LP_FlagDir]/')
    if 'name="ABK_LP_FlagDir"' not in s:
        i = s.index('<includes>') + len('<includes>')
        s = s[:i] + '\n    ' + VAR + s[i:]
    open(path, 'w', encoding='utf-8').write(s)


if __name__ == '__main__':
    main(sys.argv[1])
