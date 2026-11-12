# -*- coding: utf-8 -*-
"""Generate the AB Tools settings window (4.8.23).

Dev tool (not used at runtime). One template, two outputs:

  resources/skins/Default/1080i/abk_settings.xml
      every skin: fixed Lucent palette (navy glass, cool white text)
  resources/af3_settings/abk_settings.xml
      copied into skin.arctic.fuse.3/1080i/ by the always-on patcher entry;
      Kodi takes a window file from the active skin first, so AF3 shows this
      one - same layout in AF3's theme colours (main_* / overlay_* names
      that every AF3 colour theme defines, Lucent Glass included)

No <defaultcontrol>: in Arabic list 9000 is hidden and Kodi logged "Control
9000 ... asked to focus, but it can't" (4.8.27); settings_engine focuses the
shown list itself.

Each file holds the layout twice: left-to-right (lists 9000 / 9001) and the
mirror for Arabic (9100 / 9101: categories on the right, text aligned
right). settings_window.py sets Window.Property(dir) and focuses the pair
that is shown. Fonts abk_set_* are registered in every fontset of the active
skin by the patcher (like Search All's abk_srch_*).

Run:  python3 tools/gen_settings_window.py
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_GENERIC = os.path.join(ROOT, 'resources', 'skins', 'Default', '1080i', 'abk_settings.xml')
OUT_AF3 = os.path.join(ROOT, 'resources', 'af3_settings', 'abk_settings.xml')

ADDON = 'special://home/addons/plugin.program.abukarimtools/'
LUC = ADDON + 'resources/lucent/media/lucent/'
TEX = {
    'white': LUC + 'white.png',
    'panel': LUC + 'panel.png',
    'panel_edge': LUC + 'panel_edge.png',
    'card': LUC + 'card.png',
    'pill': LUC + 'pill48.png',
    'knob': LUC + 'knob.png',
    'grad_bottom': LUC + 'grad_bottom.png',
    'vignette': LUC + 'vignette.png',
    'chevron': ADDON + 'resources/skins/Default/media/abk_sq_chevron.png',
}

PALETTES = {
    'generic': {
        'BG': 'FF0B1119', 'FG100': 'FFE8EEF2', 'FG70': 'B3E8EEF2', 'FG50': '80E8EEF2',
        'FG30': '4DE8EEF2', 'FG12': '1FE8EEF2', 'FG06': '0FE8EEF2',
        'GLASS': '14FFFFFF', 'EDGE': '1FFFFFFF',
        
    },
    'af3': {
        'BG': 'main_bg_100', 'FG100': 'main_fg_100', 'FG70': 'main_fg_70', 'FG50': 'main_fg_50',
        'FG30': 'main_fg_30', 'FG12': 'main_fg_12', 'FG06': 'main_fg_06',
        'GLASS': 'overlay_soft', 'EDGE': 'main_fg_12',
        
    },
}

W, H = 1560, 1080

# 4.8.23: all content sits in ONE group, 1560 wide, centred on the screen
# (<centerleft>50%</centerleft>). The window's coordinate width is not
# always 1920: on a 16:10 MacBook (3024x1964 screenshot, 2026-11-11) Kodi
# gave it ~1620-1730, and a layout drawn for 1920 lost its right side
# (title and the Arabic categories column). 1560 fits there with a margin; on 16:9 it
# is centred with even margins. Backgrounds use 100% sizes.
# geometry inside the group (left-to-right; the Arabic copy mirrors every x)
CAT = dict(x=0, y=196, w=440, h=736)        # categories column
PAN = dict(x=480, y=180, w=1080, h=692)     # entries glass panel
LST = dict(x=500, y=200, w=1040, h=652)     # entries list inside it
DSC = dict(x=480, y=892, w=1080, h=132)     # description strip
CAT_ROW = 92
ROW = 92


def mx(x, w, pw, rtl):
    """x of a box of width w inside a parent of width pw."""
    return pw - x - w if rtl else x


def al(align, rtl):
    if not rtl:
        return align
    return {'left': 'right', 'right': 'left'}.get(align, align)


def image(x, y, w, h, tex, color, pw, rtl, extra='', visible=None, border=None, flip=False):
    b = ' border="%d"' % border if border else ''
    f = ' flipx="true"' if flip else ''
    vis = '<visible>%s</visible>' % visible if visible else ''
    return ('<control type="image"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
            '<texture%s%s colordiffuse="%s">%s</texture>%s%s</control>'
            % (mx(x, w, pw, rtl), y, w, h, b, f, color, tex, extra, vis))


def label(x, y, w, h, text, font, color, align, pw, rtl, visible=None, scroll=False):
    vis = '<visible>%s</visible>' % visible if visible else ''
    sc = '<scroll>true</scroll>' if scroll else ''
    return ('<control type="label"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
            '<font>%s</font><textcolor>%s</textcolor><align>%s</align><aligny>center</aligny>'
            '%s<label>%s</label>%s</control>'
            % (mx(x, w, pw, rtl), y, w, h, font, color, al(align, rtl), sc, text, vis))


def cat_layout(p, rtl, focused, list_id):
    w = CAT['w']
    out = []
    has = 'Control.HasFocus(%d)' % list_id
    if focused:
        out.append(image(0, 4, w, CAT_ROW - 8, TEX['card'], p['FG100'], w, rtl, border=24, visible=has))
        out.append(image(0, 4, w, CAT_ROW - 8, TEX['card'], p['FG12'], w, rtl, border=24, visible='!' + has))
    out.append(image(22, 20, 52, 52, '$INFO[ListItem.Icon]', 'FFFFFFFF', w, rtl,
                     extra='<aspectratio>keep</aspectratio>'))
    if focused:
        out.append(label(96, 0, w - 120, CAT_ROW, '[B]$INFO[ListItem.Label][/B]', 'abk_set_m',
                         p['BG'], 'left', w, rtl, visible=has, scroll=True))
        out.append(label(96, 0, w - 120, CAT_ROW, '[B]$INFO[ListItem.Label][/B]', 'abk_set_m',
                         p['FG100'], 'left', w, rtl, visible='!' + has))
    else:
        out.append(label(96, 0, w - 120, CAT_ROW, '$INFO[ListItem.Label]', 'abk_set_m',
                         p['FG70'], 'left', w, rtl))
    return '\n'.join(out)


def row_layout(p, rtl, focused, list_id):
    w = LST['w']
    out = []
    has = 'Control.HasFocus(%d)' % list_id
    on_dark = has if focused else 'false'
    if focused:
        out.append(image(0, 4, w, ROW - 8, TEX['card'], p['FG100'], w, rtl, border=24, visible=has))
    fg_main, fg_dim = (p['FG100'], p['FG70'])
    dk_main, dk_dim = (p['BG'], p['BG'])
    # icon
    out.append(image(22, 20, 52, 52, '$INFO[ListItem.Icon]', 'FFFFFFFF', w, rtl,
                     extra='<aspectratio>keep</aspectratio>'))
    is_sw = '!String.IsEmpty(ListItem.Property(switch))'
    no_sw = 'String.IsEmpty(ListItem.Property(switch))'
    has_val = '!String.IsEmpty(ListItem.Label2)'
    # main label (shorter when a value is shown)
    for vis_extra, lw in (('[%s + %s]' % (no_sw, has_val), w - 98 - 460), ('![%s + %s]' % (no_sw, has_val), w - 98 - 150)):
        if focused:
            out.append(label(98, 0, lw, ROW, '$INFO[ListItem.Label]', 'abk_set_m', dk_main, 'left', w, rtl,
                             visible='%s + %s' % (vis_extra, on_dark), scroll=True))
            out.append(label(98, 0, lw, ROW, '$INFO[ListItem.Label]', 'abk_set_m', fg_main, 'left', w, rtl,
                             visible='%s + !%s' % (vis_extra, on_dark)))
        else:
            out.append(label(98, 0, lw, ROW, '$INFO[ListItem.Label]', 'abk_set_m', fg_main, 'left', w, rtl,
                             visible=vis_extra))
    # value (label2) on the far side
    val_vis = '%s + %s' % (no_sw, has_val)
    if focused:
        out.append(label(w - 460, 0, 400, ROW, '$INFO[ListItem.Label2]', 'abk_set_s', dk_dim, 'right', w, rtl,
                         visible='%s + %s' % (val_vis, on_dark)))
        out.append(label(w - 460, 0, 400, ROW, '$INFO[ListItem.Label2]', 'abk_set_s', fg_dim, 'right', w, rtl,
                         visible='%s + !%s' % (val_vis, on_dark)))
    else:
        out.append(label(w - 460, 0, 400, ROW, '$INFO[ListItem.Label2]', 'abk_set_s', fg_dim, 'right', w, rtl,
                         visible=val_vis))
    # chevron: plain actions (no switch, no value)
    chev_vis = '%s + !%s' % (no_sw, has_val)
    if focused:
        out.append(image(w - 64, 28, 36, 36, TEX['chevron'], dk_dim, w, rtl, flip=rtl,
                         visible='%s + %s' % (chev_vis, on_dark)))
        out.append(image(w - 64, 28, 36, 36, TEX['chevron'], p['FG50'], w, rtl, flip=rtl,
                         visible='%s + !%s' % (chev_vis, on_dark)))
    else:
        out.append(image(w - 64, 28, 36, 36, TEX['chevron'], p['FG50'], w, rtl, flip=rtl, visible=chev_vis))
    # switch: track + knob
    on = 'String.IsEqual(ListItem.Property(switch),on)'
    off = 'String.IsEqual(ListItem.Property(switch),off)'
    tx, ty, tw, th = w - 120, 24, 88, 44
    knob = 36
    k_on_x = tx + tw - knob - 4
    k_off_x = tx + 4
    if focused:
        # on a white row: track dark when on, dim dark when off
        out.append(image(tx, ty, tw, th, TEX['pill'], p['BG'], w, rtl, border=22, visible='%s + %s' % (on, on_dark)))
        out.append(image(k_on_x, ty + 4, knob, knob, TEX['knob'], p['FG100'], w, rtl, visible='%s + %s' % (on, on_dark)))
        out.append(image(tx, ty, tw, th, TEX['pill'], '4D000000', w, rtl, border=22, visible='%s + %s' % (off, on_dark)))
        out.append(image(k_off_x, ty + 4, knob, knob, TEX['knob'], p['FG100'], w, rtl, visible='%s + %s' % (off, on_dark)))
    nd = ('!%s' % on_dark) if focused else None

    def v(c):
        return '%s + %s' % (c, nd) if nd else c
    out.append(image(tx, ty, tw, th, TEX['pill'], p['FG100'], w, rtl, border=22, visible=v(on)))
    out.append(image(k_on_x, ty + 4, knob, knob, TEX['knob'], p['BG'], w, rtl, visible=v(on)))
    out.append(image(tx, ty, tw, th, TEX['pill'], p['FG30'], w, rtl, border=22, visible=v(off)))
    out.append(image(k_off_x, ty + 4, knob, knob, TEX['knob'], p['FG100'], w, rtl, visible=v(off)))
    return '\n'.join(out)


def side(p, rtl):
    cat_id, item_id = (9100, 9101) if rtl else (9000, 9001)
    to_items, to_cats = ('onleft', 'onright') if rtl else ('onright', 'onleft')
    vis = 'String.IsEqual(Window.Property(dir),rtl)' if rtl else '!String.IsEqual(Window.Property(dir),rtl)'
    c = []
    c.append('<control type="group">')
    c.append('<centerleft>50%%</centerleft><top>0</top><width>%d</width><height>%d</height>' % (W, H))
    c.append('<visible>%s</visible>' % vis)
    # header
    c.append(label(16, 52, 1100, 64, '[B]$INFO[Window.Property(title)][/B]', 'abk_set_xl', p['FG100'], 'left', W, rtl))
    c.append(label(16, 112, 1100, 44, '$INFO[Window.Property(cat.title)]', 'abk_set_m', p['FG70'], 'left', W, rtl))
    c.append(label(W - 16 - 400, 60, 400, 50, '$INFO[Window.Property(version),v]', 'abk_set_s', p['FG50'], 'right', W, rtl))
    # position in a long category: "6 / 16" while the entries have focus
    c.append(label(W - 16 - 400, 112, 400, 44,
                   '$INFO[Container(%d).CurrentItem]$INFO[Container(%d).NumItems, / ]' % (item_id, item_id),
                   'abk_set_s', p['FG50'], 'right', W, rtl, visible='Control.HasFocus(%d)' % item_id))
    # glass panel behind the entries + its edge
    c.append(image(PAN['x'], PAN['y'], PAN['w'], PAN['h'], TEX['panel'], p['GLASS'], W, rtl, border=40))
    c.append(image(PAN['x'], PAN['y'], PAN['w'], PAN['h'], TEX['panel_edge'], p['EDGE'], W, rtl, border=40))
    # description strip
    c.append(image(DSC['x'], DSC['y'], DSC['w'], DSC['h'], TEX['panel'], p['GLASS'], W, rtl, border=40))
    for has, src in (('Control.HasFocus(%d)' % item_id, item_id), ('!Control.HasFocus(%d)' % item_id, cat_id)):
        c.append('<control type="textbox"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
                 '<font>abk_set_s</font><textcolor>%s</textcolor><align>%s</align>'
                 '<autoscroll delay="4000" time="2000" repeat="6000">true</autoscroll>'
                 '<label>$INFO[Container(%d).ListItem.Property(desc)]</label><visible>%s</visible></control>'
                 % (mx(DSC['x'] + 36, DSC['w'] - 72, W, rtl), DSC['y'] + 20, DSC['w'] - 72, DSC['h'] - 40,
                    p['FG70'], al('left', rtl), src, has))
    # categories list
    c.append('<control type="list" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
             '<%s>%d</%s><onup>%d</onup><ondown>%d</ondown><scrolltime tween="cubic" easing="out">220</scrolltime>'
             '<orientation>vertical</orientation>'
             '<itemlayout height="%d" width="%d">%s</itemlayout>'
             '<focusedlayout height="%d" width="%d">%s</focusedlayout></control>'
             % (cat_id, mx(CAT['x'], CAT['w'], W, rtl), CAT['y'], CAT['w'], CAT['h'],
                to_items, item_id, to_items, cat_id, cat_id,
                CAT_ROW, CAT['w'], cat_layout(p, rtl, False, cat_id),
                CAT_ROW, CAT['w'], cat_layout(p, rtl, True, cat_id)))
    # entries list
    c.append('<control type="list" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
             '<%s>%d</%s><onup>%d</onup><ondown>%d</ondown><scrolltime tween="cubic" easing="out">220</scrolltime>'
             '<orientation>vertical</orientation>'
             '<itemlayout height="%d" width="%d">%s</itemlayout>'
             '<focusedlayout height="%d" width="%d">%s</focusedlayout></control>'
             % (item_id, mx(LST['x'], LST['w'], W, rtl), LST['y'], LST['w'], LST['h'],
                to_cats, cat_id, to_cats, item_id, item_id,
                ROW, LST['w'], row_layout(p, rtl, False, item_id),
                ROW, LST['w'], row_layout(p, rtl, True, item_id)))
    c.append('</control>')
    return '\n'.join(c)


def build(p, header):
    full = ('<control type="image"><left>0</left><top>%s</top><width>100%%</width><height>%s</height>'
            '<texture colordiffuse="%s">%s</texture></control>')
    bg = [
        full % (0, '100%', p['BG'], TEX['white']),
        full % ('40%', '60%', p['BG'], TEX['grad_bottom']),
        full % (0, '100%', '99000000', TEX['vignette']),
    ]
    body = '\n'.join(bg) + '\n' + side(p, False) + '\n' + side(p, True)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<!-- %s -->\n'
           '<window>\n'
           '<animation effect="fade" start="0" end="100" time="250">WindowOpen</animation>\n'
           '<animation effect="fade" start="100" end="0" time="200">WindowClose</animation>\n'
           '<controls>\n%s\n</controls>\n</window>\n' % (header, body))
    return xml


def outputs():
    """{path: xml} of both window files (tools/selftest.py compares them)."""
    hdr = ('AB Tools settings window (4.8.23). Generated by tools/gen_settings_window.py - '
           'edit the generator, not this file. Look after the Lucent skin by djdirty60.')
    return {OUT_GENERIC: build(PALETTES['generic'], hdr + ' Copy for every skin.'),
            OUT_AF3: build(PALETTES['af3'], hdr + ' Arctic Fuse 3 copy (theme colours).')}


def main():
    os.makedirs(os.path.dirname(OUT_AF3), exist_ok=True)
    for path, xml in outputs().items():
        with open(path, 'w', encoding='utf-8') as f:
            f.write(xml)
    # switch knob: white circle, antialiased (tinted in the XML)
    try:
        from PIL import Image, ImageDraw
        s, n = 8, 64
        im = Image.new('RGBA', (n * s, n * s), (0, 0, 0, 0))
        ImageDraw.Draw(im).ellipse((2 * s, 2 * s, (n - 2) * s, (n - 2) * s), fill=(255, 255, 255, 255))
        im = im.resize((n, n), Image.LANCZOS)
        im.save(os.path.join(ROOT, 'resources', 'lucent', 'media', 'lucent', 'knob.png'), optimize=True)
    except ImportError:
        print('PIL missing: knob.png not redrawn')
    print('wrote', OUT_GENERIC)
    print('wrote', OUT_AF3)


if __name__ == '__main__':
    main()
