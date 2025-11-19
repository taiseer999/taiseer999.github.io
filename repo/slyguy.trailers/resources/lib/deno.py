import os
import zipfile

from slyguy import dialog
from slyguy.log import log
from slyguy.constants import ADDON_PROFILE
from slyguy.util import get_system_arch
from slyguy.session import Session

from .language import _


VERSION = '2.5.6'

SOURCES = {
    'Windows64bit': 'https://github.com/denoland/deno/releases/download/v{}/deno-x86_64-pc-windows-msvc.zip'.format(VERSION),
}

DEST_DIR = os.path.join(ADDON_PROFILE, 'deno')
if not os.path.exists(DEST_DIR):
    os.makedirs(DEST_DIR)


def install_deno(reinstall=False):
    system, arch = get_system_arch()
    url = SOURCES.get(system + arch)
    if not url:
        log.info("Deno for {} {} not yet supported. Fallback to legacy built-in js extractor".format(system, arch))
        return None

    if system == "Windows":
        extension = '.exe'
    else:
        extension = ''

    dst_file = os.path.join(DEST_DIR, VERSION + extension)
    if os.path.exists(dst_file) and not reinstall:
        log.debug("Found deno: {}".format(dst_file))
        return dst_file

    with dialog.progress(_(_.IA_DOWNLOADING_FILE, url=url), percent=50):
        # clear out old
        for file in os.listdir(DEST_DIR):
            os.remove(os.path.join(DEST_DIR, file))

        # download and extract
        Session().chunked_dl(url, dst_file+'.zip')
        with zipfile.ZipFile(dst_file+'.zip', "r") as z:
            z.extractall(DEST_DIR)

        os.remove(dst_file+'.zip')
        os.rename(os.path.join(DEST_DIR, os.listdir(DEST_DIR)[0]), dst_file)

    log.debug("Deno installed: {}".format(dst_file))
    return dst_file
