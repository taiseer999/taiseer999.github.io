import os
import sys
from urllib.request import Request, urlopen
import xbmc
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')
ICON = ADDON.getAddonInfo('icon')

class Downloader:
    # 3.9.43: every network call has a timeout. For the build download it is
    # per socket read, so a stalled server ends the download instead of
    # freezing the progress dialog forever.
    TIMEOUT = 60

    def __init__(self, url):
        if url.startswith('https://www.dropbox.com'):
            url = url.replace('dl=0', 'dl=1')   # dl=0 serves an HTML page
        self.url = url
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        self.headers = {"User-Agent": self.user_agent}
        
    def get_urllib(self, decoding=True):
        req = Request(self.url, headers = self.headers)
        if decoding:
            return urlopen(req, timeout=self.TIMEOUT).read().decode('utf-8')
        return urlopen(req, timeout=self.TIMEOUT)
    
    def get_length(self, response):
        try:
            return response.getheader('content-length')
        except KeyError:
            return None
    
    def download_build(self, name, zippath):
        """Download to zippath. Returns True when the whole file arrived.

        False = network error / timeout / short read (the partial file is
        deleted and the error logged). Cancel still exits as before.
        """
        dp = xbmcgui.DialogProgress()
        try:
            return self._download(dp, name, zippath)
        except Exception as e:
            xbmc.log('AB Wizard: download failed (%s): %s' % (self.url, e), xbmc.LOGERROR)
            try:
                dp.close()
            except Exception:
                pass
            try:
                if os.path.exists(zippath):
                    os.unlink(zippath)
            except Exception:
                pass
            return False

    def _download(self, dp, name, zippath):
        response = self.get_urllib(decoding=False)
        length = self.get_length(response)
        if length is not None:
            length2 = int(int(length)/1000000)
            dp.create(f'{name} - {length2}MB', 'Downloading your build...')
        else:
            length2 = 'Unknown Size'
            dp.create(f'{name} - {length2}', 'Downloading your build...')
        
        dp.update(0, 'Downloading your build...')
        cancelled = False
        chunksize = 1000000
        size = 0
        with open(zippath, 'wb') as f:
            if length is not None:
                while True:
                    chunk = response.read(chunksize)
                    if not chunk:
                        break
                    size += len(chunk)
                    size2 = int(size/1000000)
                    perc = int(int(size)/int(length)*100)
                    f.write(chunk)
                    dp.update(perc, f'Downloading your build...\n{size2}/{length2} MB')
                    if dp.iscanceled():
                        cancelled = True
                        break
                    
            else:
                while True:
                    chunk = response.read(chunksize)
                    if not chunk:
                        break
                    size += len(chunk)
                    size2 = int(size/1000000)
                    f.write(chunk)
                    dp.update(50, f'Downloading your build...\n{size2} MB')
                    if dp.iscanceled():
                        cancelled = True
                        break
                        
        if cancelled is True:
            dp.close()
            os.unlink(zippath)
            dialog = xbmcgui.Dialog()
            dialog.notification(ADDON_NAME, 'Download Cancelled', icon=ICON)
            sys.exit()
        
        if length is not None:
            dp.update(100,
                f'Downloading your build...Done!\n{size2}/{length2} MB'
            )
        else:
            dp.update(100, f'Downloading your build...Done!\n{size2} MB')
        
        xbmc.sleep(500)
        dp.close()
        if length is not None and size != int(length):
            # The server closed the connection early: a clean EOF, no error.
            xbmc.log('AB Wizard: short download %d of %s bytes' % (size, length),
                     xbmc.LOGERROR)
            os.unlink(zippath)
            return False
        return True
    