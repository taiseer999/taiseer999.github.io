# -*- coding: utf-8 -*-

#############################
# Light IMDb Ratings Update #
# by axlt2002               #
#############################

import socket, six
import xbmc, xbmcgui
from six.moves import urllib
from six.moves.urllib.request import Request, urlopen
from six.moves.urllib.error import HTTPError, URLError
from support.common import *
import io, gzip
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

User_Agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
Accept_Encoding = "gzip"

class download_tools():
	def downloader(self,url,dest,description,heading):
		dp = xbmcgui.DialogProgressBG()
		dp.create(heading,description)
		dp.update(0)
		urllib.request.urlretrieve(url,dest,lambda nb, bs, fs, url=url: self._pbhook(nb,bs,fs,dp))
		xbmc.sleep(2000)
		dp.close()
		
	def _pbhook(self,numblocks, blocksize, filesize,dp=None):
		try:
			percent = int((int(numblocks)*int(blocksize)*100)/int(filesize))
			dp.update(percent)
		except:
			percent = 100
			dp.update(percent)

def verify_and_download(url, filename, date):
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    try:
        response = session.get(url, stream=True, timeout=15)
        try:
            if response.status_code != 200:
                return {"status": "Response error: {0}".format(response.status_code), "last_modified": None,}

            raw_header = response.headers.get('Last-Modified') or response.headers.get('Date')
            last_modified = " ".join(raw_header.split()[:4])

            if not last_modified:
                return {"status": "Error: Last-Modified and Date not available", "last_modified": None,}

            if last_modified == date:
                return {"status": "No update available", "last_modified": last_modified,}

            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return {"status": "Verified and downloaded", "last_modified": last_modified,}
        finally:
            response.close()

    except Exception as e:
        return {"status": "Connection error: {0}".format(str(e)), "last_modified": None,}

def get_page(url):
	req = Request(url)
	req.add_header('User-Agent', User_Agent)
	req.add_header('Accept-encoding', Accept_Encoding)
	socket.setdefaulttimeout(30)
	html = ""
	try:
		response = urlopen(req)
		if response.info().get('Content-Encoding') == 'gzip':
			buf = io.BytesIO(response.read())
			f = gzip.GzipFile(fileobj=buf)
			html = f.read().decode("utf-8")
		else:
			html=response.read().decode("utf-8")
		response.close()
		return (html, "OK", "OK")
	except HTTPError as err:
		error = str(err.code) + " " + err.reason
		statusInfo = "Method get_page - " + url + " -> Error accessing IMDb site (" + error + ")"
		return (html, "HTTP", statusInfo)
	except socket.error as err:
		statusInfo = "Method get_page - " + url + " -> Error accessing IMDb site (" + str (err) + ")"
		return (html, "socket", statusInfo)
	except URLError as err:
		#handling as timeout
		if not isinstance(err, six.string_types):
			error = err.reason
		else:
			error = str(err)
		statusInfo = "Method get_page - " + url + " -> Error accessing IMDb site (" + error + ")"
		return (html, "socket", statusInfo)