# Arctic Splash

Kodi image resource add-on `resource.images.arctic.splash`, version 1.0.0.

The 616 registered 1920 x 1080 image layers are in `resources/layers/`. The
manifest defines four seasons, five weather patterns and 24 hourly states.
Composite each state's nine images in manifest order using normal alpha-over.
All lighting, reflections and weather effects are authored in the image assets.

Large layers use quality 95 WebP with lossless alpha. Celestial, glow and
conditions overlays retain lossless PNG; sky plates retain JPG. Images total
approximately 101 MiB. `compile="false"` preserves these compressed files.

The skin declares this add-on as a required dependency and reads images from:

`special://home/addons/resource.images.arctic.splash/resources/layers/`

Kodi's image resource `resource://` handler only publishes PNG/JPG, including
in Kodi 21 and current source. Reading the add-on's files through `special://`
allows WebP decoding without expanding the artwork back to PNG. Install this
add-on normally in Kodi's user add-ons directory. No executable code is needed.

The skin selects season, hour and weather. Custom user image paths continue to
use the existing slideshow and do not use these layers.
