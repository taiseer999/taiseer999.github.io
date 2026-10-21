"""Rebuild the small, vertically seamless rain tile (requires Pillow)."""

from pathlib import Path
from random import Random

from PIL import Image


def make_rain():
    # Half-resolution art is drawn at 480 x 1080 by the skin. Keep a single
    # shared texture; stagger the speed and mirroring of its four screen strips.
    width, height = 240, 540
    alpha = Image.new("L", (width, height))
    pixels = alpha.load()
    random = Random(1191)
    for _ in range(48):
        x = random.randrange(3, width - 3)
        y = random.randrange(height)
        length = random.randrange(10, 35)
        peak = random.randrange(110, 235)
        for step in range(length):
            # A tapered trail with a bright lower tip; wrap at the vertical seam.
            strength = int(peak * (step / length) ** 0.7 * min(1, (length - step) / 3))
            row = (y + step) % height
            for dx, scale in ((-1, 0.15), (0, 1), (1, 0.15)):
                pixels[x + dx, row] = max(pixels[x + dx, row], int(strength * scale))

    # White with 16 alpha levels compresses to a tiny indexed PNG and tints in Kodi.
    tile = Image.new("P", alpha.size)
    tile.putpalette([255, 255, 255] * 256)
    tile.putdata([round(value / 17) for value in alpha.getdata()])
    tile.info["transparency"] = bytes(min(255, value * 17) for value in range(256))
    destination = Path(__file__).resolve().parents[1] / "resources/effects/rain.png"
    destination.parent.mkdir(parents=True, exist_ok=True)
    tile.save(destination, optimize=True)
    print(f"{destination}: {destination.stat().st_size:,} bytes")


if __name__ == "__main__":
    make_rain()
