# -*- coding: utf-8 -*-
"""4.7.33: the DV2 test of the Lucent Player (4.7.35: the OSD info part is gone -
the OSD shows AF3's own expanded info, window 1153, see patcher.py).

Run after port.py / af3_layout.py / af3_furniture.py / af3_volume.py:
    python3 tools/lucent_player/af3_osdinfo.py resources/lucent_player/Includes_ABK_LucentPlayer.xml

ABK_LP_LucentDV2Named (Lucent 1.34.1) tests String.Contains(...,[dv2]):
   Kodi reads the "[" as a group bracket, logs "Misplaced [" / "Error parsing
   boolean expression" and the whole expression never parses, so the DV2
   badge never showed. Those two [dv2] clauses go; ".dv2." etc. still match.
Idempotent.
"""
import re
import sys

def main(path):
    txt = open(path, encoding='utf-8').read()
    done = []
    n = 0
    for il in ('Player.Filename', 'Player.FilenameAndPath'):
        txt, k = re.subn(r' \| String\.Contains\(%s,\[dv2\]\)' % re.escape(il), '', txt)
        n += k
    if n:
        done.append('dv2 test (%d clauses)' % n)
    if '[dv2]' in txt:
        sys.exit('[dv2] still present')
    open(path, 'w', encoding='utf-8').write(txt)
    print(', '.join(done) or 'already there')


if __name__ == '__main__':
    main(sys.argv[1])
