# -*- coding: utf-8 -*-
"""Generate the Arctic Fuse 3 "Lucent Glass" colour themes (AB Tools 4.6.8).

Dev tool (not used at runtime). Output: resources/af3_lucent/colors/*.xml,
installed into skin.arctic.fuse.3/colors/ by the always-on patcher entries and
picked by Toggles > "AF3: Lucent Look" (lookandfeel.skincolors).

Every token AF3 50.11.x defines in colors/defaults.xml is redefined, so the
theme is complete on its own. Palette after the Lucent skin by djdirty60
(github.com/djdirty60/Lucent): navy-black background, glass panels, cool
white text (bg 0B1119, panel 162532, text DCE2E7..FFFFFF, hairline white 18 %).

Run:  python3 tools/gen_af3_lucent.py
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'resources', 'af3_lucent', 'colors')

# AF3 alpha steps per family (same as defaults.xml)
FG = (('100', 'ff'), ('90', 'e7'), ('70', 'b3'), ('50', '80'), ('30', '4d'), ('12', '1f'), ('06', '0f'))
BG = (('100', 'ff'), ('90', 'e7'), ('70', 'b3'), ('50', '80'), ('30', '4d'), ('12', '1f'))
PANEL_BG = (('100', 'ff'),) + BG[1:]          # panel_bg_100 is used by AF3 but not defined there
PANEL_FG = FG[:-1]

THEMES = {
    'Lucent Glass': {
        'text': 'e8eef2', 'bg': '0b1119', 'dialog_bg': '162532', 'panel_bg': '0b1119',
        'soft': '3c4a56', 'logo': 'bdc8d1', 'nib': '2c3e4c',
        'overlay': 'e0162532',                 # glass body (Lucent "panel")
        'shadow_back': 'b30b1119',
    },
    'Lucent Glass AMOLED': {
        'text': 'eeeeee', 'bg': '000000', 'dialog_bg': '101010', 'panel_bg': '000000',
        'soft': '2a2a2a', 'logo': 'bdbdbd', 'nib': '222222',
        'overlay': 'e0101010',
        'shadow_back': 'cc000000',
    },
}


def theme_xml(name, t):
    rows = []

    def fam(prefix, steps, rgb):
        for step, a in steps:
            rows.append('    <color name="%s_%s">%s%s</color>' % (prefix, step, a, rgb))

    rows.append('    <!-- Main -->')
    fam('main_fg', FG, t['text'])
    fam('main_bg', BG, t['bg'])
    rows += ['    <color name="main_soft">4d%s</color>' % t['soft'],
             '    <color name="main_hard">b3%s</color>' % t['soft'],
             '    <color name="main_back">ff%s</color>' % t['soft'],
             '    <color name="main_logo">ff%s</color>' % t['logo'],
             '', '    <!-- Dialogs (glass) -->',
             '    <color name="dialog_nib">ff%s</color>' % t['nib'],
             '    <color name="dialog_overlay">%s</color>' % t['overlay']]
    fam('dialog_fg', FG, t['text'])
    fam('dialog_bg', BG, t['dialog_bg'])
    rows.append('    <!-- Panels -->')
    fam('panel_bg', PANEL_BG, t['panel_bg'])
    fam('panel_fg', PANEL_FG, t['text'])
    rows += ['', '    <!-- Overlay / glass -->',
             '    <color name="overlay_soft">14ffffff</color>',
             '    <color name="overlay_hard">2effffff</color>',
             '', '    <!-- Shadow -->',
             '    <color name="shadow_soft">1a000000</color>',
             '    <color name="shadow_hard">99000000</color>',
             '    <color name="shadow_full">c0000000</color>',
             '    <color name="shadow_back">%s</color>' % t['shadow_back'],
             '', '    <!-- Misc -->',
             '    <color name="yellow_star">d7f2b84b</color>',
             '    <color name="rating_9">ff32a0ee</color>',
             '    <color name="rating_8">ff4cc38a</color>',
             '    <color name="rating_7">ffa4c05b</color>',
             '    <color name="rating_6">ffb8b252</color>',
             '    <color name="rating_5">ffc39c4d</color>',
             '    <color name="rating_4">ffce8748</color>',
             '    <color name="rating_3">ffe5534b</color>']
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!-- %s - AF3 colour theme by ABUKARIM TOOLS (tools/gen_af3_lucent.py).\n'
            '     Palette after the Lucent skin by djdirty60. -->\n'
            '<colors>\n%s\n</colors>\n' % (name, '\n'.join(rows)))


def build():
    os.makedirs(OUT, exist_ok=True)
    out = []
    for name, t in THEMES.items():
        path = os.path.join(OUT, name + '.xml')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(theme_xml(name, t))
        out.append(path)
    return out


if __name__ == '__main__':
    for p in build():
        print(p)
