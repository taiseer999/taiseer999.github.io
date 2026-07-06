# -*- coding: utf-8 -*-
import time
import requests
import xbmc
import xbmcgui
from requests.adapters import HTTPAdapter

from acctmgr.modules import control
from acctmgr.modules import log_utils
from acctmgr.modules.qr_utils import make_qr, remove_qr


# Variables
OFFCLOUD_ICON = control.joinPath(control.artPath(), "offcloud.png")
OFFCLOUD_BDR = control.joinPath(control.addonPath(), "resources", "images", "white.png")
OFFCLOUD_BG = control.joinPath(control.addonPath(), "resources", "images", "dialog_background.png")
OFFCLOUD_QR = control.joinPath(control.addonPath(), "resources", "images", "offcloud_qr.png")


class OffcloudAuthDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.user_code = kwargs.get("user_code")
        self.verify_url = kwargs.get("verify_url")
        self.bg_image = kwargs.get("bg_image")
        self.qr_image = kwargs.get("qr_image")
        self.bdr_image = kwargs.get("bdr_image")
        self.is_active = True
        super(OffcloudAuthDialog, self).__init__()

    def onInit(self):
        self.setProperty("user_code", self.user_code)
        self.setProperty("verify_url", self.verify_url)
        self.setProperty("bg_image", self.bg_image)
        self.setProperty("qr_image", self.qr_image)
        self.setProperty("bdr_image", self.bdr_image)

    def onClick(self, controlId):
        self.is_active = False
        self.close()

    def onAction(self, action):
        if action.getId() in [10, 13, 92]:
            self.is_active = False
            self.close()

BASE_HOST = "https://offcloud.com"
API_BASE = f"{BASE_HOST}/api"
OAUTH_DEVICE_CODE_URL = f"{BASE_HOST}/oauth/device/code"
OAUTH_TOKEN_URL = f"{BASE_HOST}/oauth/token"
ACTIVATE_URL = "https://offcloud.com/activate"

TIMEOUT = 10.0

session = requests.Session()
session.mount("https://offcloud.com", HTTPAdapter(max_retries=1, pool_maxsize=20))


class Offcloud:
    def auth(self):
        # Already authorizedcheck
        if control.setting("offcloud.token"):
            control.notification(message="Offcloud is already authorized!",icon=OFFCLOUD_ICON)
            return False

        # Request device code
        try:
            resp = session.post(OAUTH_DEVICE_CODE_URL, timeout=TIMEOUT)
            resp.raise_for_status()
            result = resp.json()

            device_code = result.get("device_code")
            user_code = result.get("user_code")
            verification_uri = result.get("verification_uri") or ACTIVATE_URL
            interval = int(result.get("interval", 5))
            expires_in = int(result.get("expires_in", 600))

            if not device_code or not user_code:
                raise Exception(f"Unexpected response: {result}")

        except Exception as e:
            log_utils.error(f"Offcloud device code request failed: {e}")
            control.notification(message="Offcloud authorization failed!",icon=OFFCLOUD_ICON)
            return False

        # QR auth dialog: try dynamic QR, fall back to the bundled static QR
        # (points at the fixed activate page) when qrcode/PIL are unavailable
        qr_path = make_qr(verification_uri)
        qr_image = qr_path if qr_path else OFFCLOUD_QR
        dialog = OffcloudAuthDialog(
            "offcloud_auth.xml",
            str(control.addonPath()),
            "Default",
            user_code=user_code,
            verify_url=verification_uri,
            bg_image=OFFCLOUD_BG,
            qr_image=qr_image,
            bdr_image=OFFCLOUD_BDR
        )
        dialog.show()

        # Poll for access token
        data = {"device_code": device_code,"grant_type": "urn:ietf:params:oauth:grant-type:device_code",}

        token = None
        start = time.monotonic()
        end = start + expires_in

        try:
            while time.monotonic() < end:

                if not dialog.is_active or xbmc.Monitor().abortRequested():
                    control.notification(message="Offcloud authorization cancelled!",icon=OFFCLOUD_ICON)
                    return False

                try:
                    r = session.post(OAUTH_TOKEN_URL, json=data, timeout=TIMEOUT)
                    if r.ok:
                        j = r.json()
                        token = j.get("access_token")
                        if token:
                            break
                except Exception:
                    pass

                control.sleep(interval * 1000)

        finally:
            try:
                if dialog.is_active:
                    dialog.close()
                del dialog
            except Exception:
                pass
            remove_qr(qr_path)

        if not token:
            control.notification(message="Offcloud authorization timed out!",icon=OFFCLOUD_ICON)
            return False

        # Validate token
        try:
            r = session.get(f"{API_BASE}/account/info",params={"key": token},timeout=TIMEOUT)
            r.raise_for_status()
            info = r.json()

            username = (info.get("username") or info.get("email") or str(info.get("user_id", "Offcloud")))

        except Exception as e:
            log_utils.error(f"Offcloud token validation failed: {e}")
            control.notification(message="Offcloud authorization failed (token invalid).",icon=OFFCLOUD_ICON)
            return False

        # Save token & userid
        control.setSetting("offcloud.token", token)
        control.setSetting("offcloud.userid", str(username))

        control.notification(title="AM Lite",message="Successfully Authorized!",icon=OFFCLOUD_ICON)
        return True
