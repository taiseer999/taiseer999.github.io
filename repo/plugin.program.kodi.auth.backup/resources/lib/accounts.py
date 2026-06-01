import json
import xml.etree.ElementTree as ET
import sqlite3
import re
from pathlib import Path
from .config import KODI

KEYWORDS = ["token", "auth", "secret", "username", "password", "apikey", "api_key", "clientsecret", "client_secret"]
AUTH_WORDS = set(KEYWORDS)
COMPOUND_AUTH_SUFFIXES = ("token", "refresh", "secret", "username", "password", "apikey", "api")
COMPOUND_AUTH_PREFIXES = (
    "alldebrid",
    "easydebrid",
    "easynews",
    "filepursuit",
    "gdrive",
    "mdblist",
    "offcloud",
    "opensubs",
    "plexshare",
    "premiumize",
    "realdebrid",
    "simkl",
    "tmdb",
    "torbox",
    "trakt"
)
AUTH_STATE_SUFFIXES = (
    "enabled",
    "enable",
    "isauthed",
    "authorized",
    "authenticated",
    "refresh",
    "expires",
    "expiry",
    "user",
    "account_id"
)
SQLITE_AUTH_KEYWORDS = ("token", "auth", "secret", "username", "password", "account_id", "apikey", "api_key")

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
    if setting_id.endswith("alternateapi"):
        return False

    parts = [part for part in re.split(r"[._-]+", setting_id) if part]
    if any(part in AUTH_WORDS for part in parts):
        return True

    return any(
        setting_id.startswith(prefix) and setting_id.endswith(suffix)
        for prefix in COMPOUND_AUTH_PREFIXES
        for suffix in COMPOUND_AUTH_SUFFIXES
    )

def is_sqlite_auth_setting(setting_id):
    setting_id = (setting_id or "").lower()
    return any(keyword in setting_id for keyword in SQLITE_AUTH_KEYWORDS)

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

def useful_auth_value(value, default=None):
    value = "" if value is None else str(value)
    default = "" if default is None else str(default)
    if value.lower() in ("", "0", "false", "none", "empty_setting"):
        return False
    return value != default or default.lower() in ("", "0", "false", "none", "empty_setting")

def extract_tokens(xml_text):
    result = {}

    try:
        root = ET.fromstring(xml_text)
        all_settings = []
        auth_prefixes = set()

        for setting in root.findall("setting"):
            sid = setting.get("id", "")
            all_settings.append((sid, setting))
            value = setting.get("value") if "value" in setting.attrib else setting.text
            if is_auth_setting(sid) and useful_auth_value(value):
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

        if "trakt" in auth_prefixes:
            for sid, setting in all_settings:
                sid_l = (sid or "").lower()
                if sid_l not in ("watched_indicators", "trakt_indicators_active", "trakt.authed.clientid"):
                    continue
                value = setting.get("value") if "value" in setting.attrib else setting.text
                if value:
                    result[sid_l] = value

        external_values = {}
        for sid, setting in all_settings:
            sid_l = (sid or "").lower()
            if sid_l not in ("provider.external.enabled", "external_provider.module", "external_provider.name"):
                continue

            value = setting.get("value") if "value" in setting.attrib else setting.text
            if value:
                external_values[sid_l] = value

        if external_values.get("external_provider.module") or external_values.get("external_provider.name"):
            result.update(external_values)
            result["provider.external.enabled"] = "true"

    except Exception as e:
        pass

    return result

def extract_sqlite_tokens(db_path):
    result = {}

    try:
        con = sqlite3.connect(str(db_path))
        cur = con.cursor()
        rows = cur.execute(
            "SELECT setting_id, setting_type, setting_default, setting_value FROM settings"
        ).fetchall()
        con.close()
    except Exception:
        return result

    auth_prefixes = set()
    for sid, _stype, default, value in rows:
        if is_sqlite_auth_setting(sid) and useful_auth_value(value, default):
            prefix = auth_prefix(sid)
            if prefix:
                auth_prefixes.add(prefix)

    for sid, stype, default, value in rows:
        sid_l = (sid or "").lower()
        if not useful_auth_value(value, default):
            continue

        if is_sqlite_auth_setting(sid_l) or is_related_auth_state(sid_l, auth_prefixes):
            result[sid_l] = {
                "type": stype,
                "default": default,
                "value": value
            }

    return result


def export_accounts(addons):
    data = {}

    for addon in addons:
        addon_data = {}
        f = KODI / "addon_data" / addon / "settings.xml"

        if f.exists():
            try:
                text = f.read_text(encoding="utf-8")
            except:
                text = f.read_text(encoding="latin-1", errors="ignore")

            tokens = extract_tokens(text)
            if tokens:
                addon_data["settings.xml"] = tokens

        db = KODI / "addon_data" / addon / "databases" / "settings.db"
        if db.exists():
            sqlite_tokens = extract_sqlite_tokens(db)
            if sqlite_tokens:
                addon_data["databases/settings.db"] = sqlite_tokens

        if addon_data:
            data[addon] = addon_data

    return data


def save_accounts(data, dest):
    path = Path(dest) / "accounts.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return path
