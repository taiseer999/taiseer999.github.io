import json
import xml.etree.ElementTree as ET
from pathlib import Path
from .config import KODI

KEYWORDS = ["token", "api", "key", "auth", "secret", "username", "password"]
AUTH_STATE_SUFFIXES = ("enabled", "enable", "isauthed", "authorized", "authenticated")

def auth_prefix(setting_id):
    setting_id = (setting_id or "").lower()
    if "." in setting_id:
        return setting_id.split(".", 1)[0]

    for keyword in KEYWORDS:
        if keyword in setting_id:
            prefix = setting_id.split(keyword, 1)[0].strip("._-")
            if prefix:
                return prefix

    return ""

def is_auth_setting(setting_id):
    setting_id = (setting_id or "").lower()
    return any(keyword in setting_id for keyword in KEYWORDS)

def is_related_auth_state(setting_id, auth_prefixes):
    setting_id = (setting_id or "").lower()
    if not setting_id or not auth_prefixes:
        return False

    separator = "." if "." in setting_id else "_"
    parts = setting_id.split(separator)
    if len(parts) < 2:
        return False

    prefix = parts[0]
    suffix = parts[-1]
    return prefix in auth_prefixes and suffix in AUTH_STATE_SUFFIXES

def extract_tokens(xml_text):
    result = {}

    try:
        root = ET.fromstring(xml_text)
        all_settings = []
        auth_prefixes = set()

        for setting in root.findall("setting"):
            sid = setting.get("id", "")
            all_settings.append((sid, setting))
            if is_auth_setting(sid):
                prefix = auth_prefix(sid)
                if prefix:
                    auth_prefixes.add(prefix)

        for sid, setting in all_settings:
            sid = (sid or "").lower()
            value = setting.get("value") if "value" in setting.attrib else setting.text

            if not value:
                continue

            if is_auth_setting(sid) or is_related_auth_state(sid, auth_prefixes):
                result[sid] = value

    except Exception as e:
        pass

    return result


def export_accounts(addons):
    data = {}

    for addon in addons:
        f = KODI / "addon_data" / addon / "settings.xml"

        if not f.exists():
            continue

        try:
            text = f.read_text(encoding="utf-8")
        except:
            text = f.read_text(encoding="latin-1", errors="ignore")

        tokens = extract_tokens(text)

        if tokens:
            data[addon] = tokens

    return data


def save_accounts(data, dest):
    path = Path(dest) / "accounts.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return path
