#!/usr/bin/python
# coding: utf-8

from __future__ import division
import xbmc, xbmcvfs
import os
from PIL import ImageFilter, Image, ImageOps, ImageEnhance, ImageStat
import math
import colorsys
import json
from .helper import *
from .config import BLUR_CONTAINER, LOGO_CONTAINER, BLUR_RADIUS, BLUR_SATURATION

OLD_IMAGE = ""
OLD_LOGO = ""

try:
    if not os.path.exists(ADDON_DATA_IMG_PATH):
        os.makedirs(ADDON_DATA_IMG_PATH)
        os.makedirs(ADDON_DATA_IMG_TEMP_PATH)

except OSError as e:
    # fix for race condition
    if e.errno != os.errno.EEXIST:
        raise
    pass


class ImageColorAnalyzer:
    def __init__(self, prop="listitem", file=None, radius=None, saturation=None):
        global OLD_IMAGE, OLD_LOGO
        if not hasattr(ImageColorAnalyzer, "_last_setting"):
            ImageColorAnalyzer._last_setting = None
        self.image = xbmc.getInfoLabel("Control.GetLabel(%s)" % BLUR_CONTAINER)
        self.logo = (
            file
            if file is not None
            else xbmc.getInfoLabel("Control.GetLabel(%s)" % LOGO_CONTAINER)
        )
        self.radius = int(radius) if radius is not None else int(BLUR_RADIUS)
        self.saturation = (
            float(saturation) if saturation is not None else float(BLUR_SATURATION)
        )
        self.is_video_context = xbmc.getCondVisibility(
            "Window.IsVisible(fullscreenvideo) | Window.IsVisible(videoosd)"
        )
        self.prop_suffix = "_video" if self.is_video_context else ""
        self._process_logo(prop)
        self._process_background(prop)

    def _process_logo(self, prop):
        if self.logo:
            global OLD_LOGO
            if self.logo != OLD_LOGO:
                OLD_LOGO = self.logo
                saved_logo = self.save_cropped_logo()
                if saved_logo:
                    winprop(f"{prop}_clearlogo_cropped{self.prop_suffix}", saved_logo)
                    if xbmc.getCondVisibility("Player.HasVideo"):
                        self.logo_color, self.logo_text_color = (
                            self.process_image_for_colors(self.logo)
                        )
                        winprop(f"{prop}_logo_color{self.prop_suffix}", self.logo_color)
                        winprop(
                            f"{prop}_logo_text_color{self.prop_suffix}",
                            self.logo_text_color,
                        )
                        r = int(self.logo_color[2:4], 16)
                        g = int(self.logo_color[4:6], 16)
                        b = int(self.logo_color[6:8], 16)
                        if (r + g + b) / 3 > 240:  # Very light color check
                            darken = int(255 * 0.5)  # 50% darker
                            dark_color = f"FF{darken:02x}{darken:02x}{darken:02x}"
                            winprop(
                                f"{prop}_logo_color_alt{self.prop_suffix}", dark_color
                            )
                        else:
                            winprop(f"{prop}_logo_color_alt{self.prop_suffix}", "")
                        if not self.logo_color or not self.logo_text_color:
                            winprop(f"{prop}_logo_color{self.prop_suffix}", "FFCCCCCC")
                            winprop(
                                f"{prop}_logo_text_color{self.prop_suffix}", "FF141515"
                            )
                            winprop(
                                f"{prop}_logo_color_alt{self.prop_suffix}", "FFCCCCCC"
                            )
        else:
            if xbmc.getCondVisibility("!Player.HasVideo + ControlGroup(2000).HasFocus"):
                OLD_LOGO = ""
                for suffix in ["", "_video"]:
                    for prop_type in [
                        "clearlogo_cropped",
                        "logo_color",
                        "logo_text_color",
                        "logo_color_alt",
                    ]:
                        winprop(f"{prop}_{prop_type}{suffix}", "")
            elif not xbmc.getCondVisibility("Player.HasVideo"):
                OLD_LOGO = ""

    def _process_background(self, prop):
        global OLD_IMAGE
        background_setting = xbmc.getInfoLabel("Skin.String(BackgroundSetting)")
        if not self.image or background_setting not in ["1", "2"]:
            return
        if self.image == OLD_IMAGE and hasattr(self, "avgcolor"):
            return
        OLD_IMAGE = self.image
        cache_key = self.get_cache_key(self.image)
        processed_img = None
        colors = self.get_cached_colors(cache_key)
        if background_setting == "2":
            filename = (
                md5hash(self.image) + str(self.radius) + str(self.saturation) + ".png"
            )
            targetfile = os.path.join(BLUR_PATH, filename)
            if xbmcvfs.exists(targetfile):
                touch_file(targetfile)
            else:
                processed_img = self.process_image()
                if processed_img:
                    try:
                        if not os.path.exists(BLUR_PATH):
                            os.makedirs(BLUR_PATH)
                        with open(targetfile, "wb") as f:
                            processed_img.save(f, "PNG")
                    except Exception as e:
                        xbmc.log(f"Error saving processed image: {str(e)}", 2)
            winprop(f"{prop}_blurred", targetfile)
        if colors:
            self.avgcolor = colors["avgcolor"]
            self.textcolor = colors["textcolor"]
        else:
            if not processed_img:
                processed_img = self.process_image()
            if processed_img:
                self.avgcolor, self.textcolor = self.color(processed_img)
                self.cache_colors(cache_key)
            else:
                self.avgcolor = "FFCCCCCC"
                self.textcolor = "FF141515"
        if hasattr(self, "avgcolor"):
            winprop(f"{prop}_color_noalpha", self.avgcolor[2:])
            winprop(f"{prop}_color", self.avgcolor)
            winprop(f"{prop}_textcolor", self.textcolor)

    def save_cropped_logo(self):
        try:
            cleaned_path = url_unquote(self.logo.replace("image://", "").rstrip("/"))
            filename = f"logo_{md5hash(cleaned_path)}.png"
            targetfile = os.path.join(ADDON_DATA_IMG_PATH, filename)
            if xbmcvfs.exists(targetfile):
                return targetfile
            img = _openimage(self.logo, ADDON_DATA_IMG_PATH, filename)
            if not img:
                return None
            try:
                img = img.convert("RGBA")
                bbox = img.getbbox()
                if not bbox:
                    return None
                img = img.crop(bbox)
                width, height = img.size
                if width > 400:
                    ratio = 400 / width
                    new_height = int(height * ratio)
                    img = img.resize((400, new_height), Image.LANCZOS)
                img = img.quantize(colors=256, method=2, kmeans=1).convert("RGBA")
                img.save(targetfile, "PNG", optimize=True, compression_level=6)
                return targetfile
            finally:
                if img:
                    img.close()
        except Exception as e:
            xbmc.log(f"Error processing clearlogo: {str(e)}", 2)
            if "targetfile" in locals() and xbmcvfs.exists(targetfile):
                xbmcvfs.delete(targetfile)
            return None

    def get_cache_key(self, image_path):
        current_radius = xbmc.getInfoLabel("Skin.String(BlurRadius)") or "20"
        current_saturation = xbmc.getInfoLabel("Skin.String(BlurSaturation)") or "1.5"
        param_string = f"{image_path}_{current_radius}_{current_saturation}"
        return md5hash(param_string)

    def get_cached_colors(self, image_path):
        try:
            if os.path.exists(COLOR_CACHE_FILE):
                cache_key = self.get_cache_key(image_path)
                with open(COLOR_CACHE_FILE, "r") as f:
                    cache = json.load(f)
                    return cache.get(cache_key)
        except Exception as e:
            xbmc.log(f"Error reading color cache: {str(e)}", 2)
        return None

    def cache_colors(self, image_path):
        try:
            cache = {}
            if os.path.exists(COLOR_CACHE_FILE):
                with open(COLOR_CACHE_FILE, "r") as f:
                    try:
                        cache = json.load(f)
                    except json.JSONDecodeError:
                        pass
            current_radius = xbmc.getInfoLabel("Skin.String(BlurRadius)") or "20"
            current_saturation = (
                xbmc.getInfoLabel("Skin.String(BlurSaturation)") or "1.5"
            )
            cache_key = self.get_cache_key(image_path)
            cache[cache_key] = {
                "avgcolor": self.avgcolor,
                "textcolor": self.textcolor,
                "parameters": {
                    "radius": current_radius,
                    "saturation": current_saturation,
                },
            }
            cache_dir = os.path.dirname(COLOR_CACHE_FILE)
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
            with open(COLOR_CACHE_FILE, "w") as f:
                json.dump(cache, f, indent=2)
        except Exception as e:
            xbmc.log(f"Error saving to color cache: {str(e)}", 2)

    def process_image(self):
        try:
            filename = (
                md5hash(self.image) + str(self.radius) + str(self.saturation) + ".png"
            )
            img = _openimage(self.image, ADDON_DATA_IMG_PATH, filename)
            if img:
                img.thumbnail((200, 200), Image.LANCZOS)
                img = img.convert("RGB")
                blur_radius = self.radius * 1.5
                img = img.filter(ImageFilter.GaussianBlur(blur_radius))
                contrast_level, brightness_level = self.analyze_image(img)
                if contrast_level > 0.7:
                    edge_preserve = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
                    img = Image.blend(img, edge_preserve, 0.15 * contrast_level)
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(self.saturation * 1.2)
                return img
        except Exception as e:
            xbmc.log(f"Error processing image: {str(e)}", 2)
            return None

    def process_image_for_colors(self, source_image):
        try:
            filename = md5hash(source_image) + "_colors.png"
            img = _openimage(source_image, ADDON_DATA_IMG_PATH, filename)
            if img:
                width, height = img.size
                max_width = 570
                if width > max_width:
                    ratio = max_width / width
                    new_height = int(height * ratio)
                    img = img.resize((max_width, new_height), Image.LANCZOS)
                img = img.convert("RGB")
                contrast_level = self.analyze_image(img)[0]

                def is_white_or_grey(color):
                    r, g, b = color
                    if all(c > 200 for c in color):
                        return True
                    max_diff = max(abs(r - g), abs(r - b), abs(g - b))
                    return max_diff < 30

                color_bins = {}
                for pixel in list(img.getdata()):
                    simple_color = (pixel[0] // 10, pixel[1] // 10, pixel[2] // 10)
                    if simple_color in color_bins:
                        color_bins[simple_color] += 1
                    else:
                        color_bins[simple_color] = 1
                sorted_colors = sorted(
                    color_bins.items(), key=lambda x: x[1], reverse=True
                )
                chosen_color = None
                for color, _ in sorted_colors:
                    scaled_color = tuple(x * 10 for x in color)
                    if not is_white_or_grey(scaled_color):
                        chosen_color = color
                        break
                if chosen_color is None:
                    chosen_color = sorted_colors[0][0]
                r, g, b = [x * 10 for x in chosen_color]
                color_enhance_factor = 1.2 + (0.08 * (1 - contrast_level))
                r = min(int(r * color_enhance_factor), 255)
                g = min(int(g * color_enhance_factor), 255)
                b = min(int(b * color_enhance_factor), 255)
                contrast_factor = 1.04 + (0.04 * (1 - contrast_level))
                r = min(int(r * contrast_factor), 255)
                g = min(int(g * contrast_factor), 255)
                b = min(int(b * contrast_factor), 255)
                h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                min_brightness = 0.65
                brightness_boost = 0.55
                if v < min_brightness:
                    v = min(v + brightness_boost, 1.0)
                    r, g, b = [int(x * 255) for x in colorsys.hsv_to_rgb(h, s, v)]
                imagecolor = f"FF{r:02x}{g:02x}{b:02x}"
                bg_luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
                textcolor = "FFFFFFFF" if bg_luminance < 0.6 else "FF141515"
                return imagecolor, textcolor
        except Exception as e:
            xbmc.log(f"Error processing image colors: {str(e)}", 2)
            return "FFCCCCCC", "FF141515"

    # def process_image_for_colors(self, source_image):
    #     try:
    #         filename = md5hash(source_image) + "_colors.png"
    #         img = _openimage(source_image, ADDON_DATA_IMG_PATH, filename)
    #         if img:
    #             width, height = img.size
    #             max_width = 570
    #             if width > max_width:
    #                 ratio = max_width / width
    #                 new_height = int(height * ratio)
    #                 img = img.resize((max_width, new_height), Image.LANCZOS)
    #             img = img.convert("RGB")
    #             contrast_level = self.analyze_image(img)[0]
    #             enhancer = ImageEnhance.Color(img)
    #             color_enhance_factor = 1.2 + (0.08 * (1 - contrast_level))
    #             img = enhancer.enhance(color_enhance_factor)
    #             contrast = ImageEnhance.Contrast(img)
    #             contrast_factor = 1.04 + (0.04 * (1 - contrast_level))
    #             img = contrast.enhance(contrast_factor)
    #             return img
    #     except Exception as e:
    #         xbmc.log(f"Error processing image for colors: {str(e)}", 2)
    #         return None

    def analyze_image(self, img):
        stat = ImageStat.Stat(img)
        r, g, b = stat.mean
        rm, gm, bm = stat.stddev
        contrast_level = (
            math.sqrt(0.241 * (rm**2) + 0.691 * (gm**2) + 0.068 * (bm**2)) / 100
        )
        contrast_level = min(contrast_level, 1.0)
        brightness_level = (r + g + b) / (3 * 255)
        return contrast_level, brightness_level

    def color(self, img):
        default_color = "FFCCCCCC"
        default_text_color = "FF141515"
        min_brightness = 0.75  # Minimum brightness value
        brightness_boost = 0.65  # Amount to boost brightness for dark colors

        def get_luminance(r, g, b):
            r = r / 255 if r <= 10 else ((r / 255 + 0.055) / 1.055) ** 2.4
            g = g / 255 if g <= 10 else ((g / 255 + 0.055) / 1.055) ** 2.4
            b = b / 255 if b <= 10 else ((b / 255 + 0.055) / 1.055) ** 2.4
            return 0.2126 * r + 0.7152 * g + 0.0722 * b

        def get_contrast_ratio(l1, l2):
            lighter = max(l1, l2)
            darker = min(l1, l2)
            return (lighter + 0.05) / (darker + 0.05)

        def get_best_text_color(bg_color):
            bg_luminance = get_luminance(bg_color[0], bg_color[1], bg_color[2])
            white = (255, 255, 255)
            dark = (20, 21, 21)  # FF141515
            white_contrast = get_contrast_ratio(get_luminance(*white), bg_luminance)
            dark_contrast = get_contrast_ratio(get_luminance(*dark), bg_luminance)
            if white_contrast >= dark_contrast * 0.52:  # Bias towards white text
                return "FFFFFFFF"
            return "FF141515"

        try:
            if img:
                img_resize = img.resize((25, 25))
                pixels = list(img_resize.convert("RGB").getdata())
                r_sum = g_sum = b_sum = 0
                for r, g, b in pixels:
                    r_sum += r
                    g_sum += g
                    b_sum += b
                pixel_count = len(pixels)
                r = r_sum // pixel_count
                g = g_sum // pixel_count
                b = b_sum // pixel_count

                # Apply brightness adjustment
                h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                if v < min_brightness:
                    v = min(v + brightness_boost, 1.0)
                    r, g, b = [int(x * 255) for x in colorsys.hsv_to_rgb(h, s, v)]

                imagecolor = f"FF{r:02x}{g:02x}{b:02x}"
                textcolor = get_best_text_color((r, g, b))
                return imagecolor, textcolor

        except Exception as e:
            xbmc.log(f"Error processing image colors: {str(e)}", 2)
        return default_color, default_text_color


""" get cached images or copy to temp if file has not been cached yet"""


def _openimage(image, targetpath, filename):
    cached_image_path = url_unquote(image.replace("image://", "")).rstrip("/")
    thumb_name = xbmc.getCacheThumbName(cached_image_path)
    cached_files = [
        os.path.join(
            "special://profile/Thumbnails/", thumb_name[0], f"{thumb_name[:-4]}.jpg"
        ),
        os.path.join(
            "special://profile/Thumbnails/", thumb_name[0], f"{thumb_name[:-4]}.png"
        ),
        os.path.join("special://profile/Thumbnails/Video/", thumb_name[0], thumb_name),
    ]

    def safe_open_image(path):
        try:
            with Image.open(xbmcvfs.translatePath(path)) as img:
                return img.copy()
        except Exception as error:
            xbmc.log(f"Could not open image: {error}", 2)
            return None

    for cache in cached_files:
        if xbmcvfs.exists(cache):
            img = safe_open_image(cache)
            if img:
                return img
    if xbmc.skinHasImage(image):
        skin_path = (
            image
            if image.startswith("special://skin")
            else os.path.join("special://skin/media/", image)
        )
        img = safe_open_image(skin_path)
        if img:
            return img
    temp_file = os.path.join(targetpath, f"temp_{filename}")
    try:
        if xbmcvfs.copy(image, temp_file):
            img = safe_open_image(temp_file)
            xbmcvfs.delete(temp_file)
            return img if img else ""
    except Exception as error:
        xbmc.log(f"Error processing file: {error}", 2)
        if xbmcvfs.exists(temp_file):
            xbmcvfs.delete(temp_file)
    return ""
