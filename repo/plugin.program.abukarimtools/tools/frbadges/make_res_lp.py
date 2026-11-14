from PIL import Image
def lucent_pill(im):
    # Lucent glass: white text on a see-through white pill (AF3 Lucent: 38FFFFFF)
    from PIL import ImageDraw
    a = im.split()[3]; bb = a.point(lambda v: 255 if v > 20 else 0).getbbox() or (0, 0) + im.size
    im = im.crop(bb); w, h = im.size
    px, py = int(h * .32), int(h * .26)
    W, Hh = w + 2 * px, h + 2 * py
    S = 4; big = Image.new('RGBA', (W * S, Hh * S)); d = ImageDraw.Draw(big)
    r = int(Hh * .30) * S
    d.rounded_rectangle((0, 0, W * S - 1, Hh * S - 1), radius=r, fill=(255, 255, 255, 56), outline=(255, 255, 255, 96), width=3 * S)
    out = big.resize((W, Hh), Image.LANCZOS); out.alpha_composite(im, (px, py))
    return out
