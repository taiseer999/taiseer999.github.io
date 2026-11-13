# -*- coding: utf-8 -*-
"""
af3_lucent_schemes.py - ABUKARIM TOOLS (4.8.48)

Data of the AF3 Lucent Look "Colours" window. Plain data, no Kodi imports:
also read by the dev tools tools/gen_af3_colours.py (cards) and
tools/gen_af3_lucent.py (AF3 colour themes).

A scheme = an AF3 colour theme (background, panels, dialogs) + the highlight
colour it comes with. A highlight = focus colour + the text colour on it.
"""

# id, AF3 colour theme (colors/<theme>.xml), label id, highlight, text on the
# highlight, card corners (top-left, top-right, bottom-left, bottom-right).
SCHEMES = [
    dict(id='glass', theme='Lucent Glass', label=30852, focus='ffffffff', onfocus='ff0b1119',
         corners=('0f1a26', '1a2a38', '1c2e3e', '0b1119')),
    dict(id='amoled', theme='Lucent Glass AMOLED', label=32223, focus='ffffffff', onfocus='ff0b1119',
         corners=('0a0a0a', '161616', '101010', '000000')),
    dict(id='bright', theme='Lucent Vaporwave', label=32224, focus='ffffffff', onfocus='ff100e24',
         corners=('1f0c33', '28253e', '511260', '171832')),
    dict(id='miami', theme='Lucent Vaporwave', label=32225, focus='ffe91e63', onfocus='ffffffff',
         corners=('1f0c33', '28253e', '511260', '171832')),
    dict(id='aqua', theme='Lucent Aqua', label=32226, focus='ff00b8d4', onfocus='ff06141a',
         corners=('0c2134', '253b3e', '12205f', '183231')),
    dict(id='sunset', theme='Lucent Sunset', label=32227, focus='fff4511e', onfocus='ffffffff',
         corners=('330d2a', '3b243e', '5f1234', '2a1732')),
    dict(id='slate', theme='Lucent Slate', label=32228, focus='ff0091ea', onfocus='ffffffff',
         corners=('202022', '333534', '292629', '212323')),
    dict(id='midnight', theme='Lucent Midnight', label=32229, focus='ff5528a8', onfocus='ffffffff',
         corners=('101010', '1a1c1b', '161416', '101212')),
]

# AF3 colour themes added in 4.8.48 (Lucent Glass / Glass AMOLED are older and
# generated from their own table in tools/gen_af3_lucent.py).
THEMES = {
    'Lucent Vaporwave': dict(text='f2eff8', bg='100e24', dialog_bg='1f1a3c', panel_bg='100e24',
                             soft='3e3760', logo='d2cde2', nib='3b2f63', overlay='f51f1a3c',
                             shadow_back='b3100e24'),
    'Lucent Aqua': dict(text='eaf4f5', bg='0b1b24', dialog_bg='13303a', panel_bg='0b1b24',
                        soft='2f5059', logo='c6d8db', nib='1f4a52', overlay='f513303a',
                        shadow_back='b30b1b24'),
    'Lucent Sunset': dict(text='f6eef2', bg='1c0c1e', dialog_bg='33182e', panel_bg='1c0c1e',
                          soft='5a3550', logo='dccbd5', nib='4e2443', overlay='f533182e',
                          shadow_back='b31c0c1e'),
    'Lucent Slate': dict(text='eeeeef', bg='141516', dialog_bg='26282a', panel_bg='141516',
                         soft='45484b', logo='cfd1d3', nib='383b3e', overlay='f526282a',
                         shadow_back='b3141516'),
    'Lucent Midnight': dict(text='ececec', bg='0a0a0b', dialog_bg='171718', panel_bg='0a0a0b',
                            soft='333335', logo='c8c8ca', nib='2a2a2c', overlay='f5171718',
                            shadow_back='cc0a0a0b'),
}

# The swatch row: (highlight, text on it)
SWATCHES = [
    ('ff00b8d4', 'ff06141a'),     # cyan
    ('fff4511e', 'ffffffff'),     # orange
    ('ffe91e63', 'ffffffff'),     # pink
    ('ff0091ea', 'ffffffff'),     # blue
    ('ff5528a8', 'ffffffff'),     # purple
    ('ffffffff', 'ff0b1119'),     # white
]

# The palette button: the 14 colour themes of the Lucent skin 2.1.0
# (colors/<id>.xml focus / on_focus), label ids 32230-32243.
LUCENT_ACCENTS = [
    ('glass', 32230, 'ffffffff', 'ff0b1119'), ('white', 32231, 'fff5f7fa', 'ff0b1119'),
    ('crimson', 32232, 'ffe5364f', 'ffffffff'), ('emerald', 32233, 'ff22b07d', 'ffffffff'),
    ('ocean', 32234, 'ff1e88e5', 'ffffffff'), ('violet', 32235, 'ff8b5cf6', 'ffffffff'),
    ('amber', 32236, 'fff5a524', 'ff0b1119'), ('gold', 32237, 'ffe8c35a', 'ff0b1119'),
    ('rose', 32238, 'fff0648c', 'ffffffff'), ('rosegold', 32239, 'ffe8a598', 'ff0b1119'),
    ('copper', 32240, 'ffc8743e', 'ffffffff'), ('jade', 32241, 'ff00a88f', 'ffffffff'),
    ('arcticblue', 32242, 'ff7fd1ff', 'ff0b1119'), ('graphite', 32243, 'ff5b6673', 'ffffffff'),
]


def text_on(hexcolour):
    """Dark or white text for a custom highlight colour (perceived luminance)."""
    h = hexcolour[-6:]
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 'ff0b1119' if (0.299 * r + 0.587 * g + 0.114 * b) > 150 else 'ffffffff'
