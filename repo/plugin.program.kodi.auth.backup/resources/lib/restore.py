import zipfile, json
from pathlib import Path, PurePosixPath
import shutil
import xml.etree.ElementTree as ET
import sqlite3
import tempfile
import os
import re
from .config import KODI
from .logger import logger
from .accounts import KEYWORDS

AUTH_WORDS = set(KEYWORDS + ["apikey", "api_key", "clientsecret", "client_secret"])
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
TRAKT_WATCHED_INDICATOR_VALUES = {
    "watched_indicators": "1",
    "trakt_indicators_active": "true"
}

def _safe_member_parts(member):
    path = PurePosixPath(member)
    if path.is_absolute() or any(part in ("", "..") for part in path.parts):
        return None
    return path.parts

def list_backup_addons(zip_file):
    addons = set()

    with zipfile.ZipFile(zip_file, 'r') as z:
        for member in z.namelist():
            parts = _safe_member_parts(member)
            if parts and len(parts) >= 3 and parts[0] == "addon_data":
                addons.add(parts[1])

    return sorted(addons)

def _is_auth_setting(setting_id):
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

def _is_sqlite_auth_setting(setting_id):
    setting_id = (setting_id or "").lower()
    return any(keyword in setting_id for keyword in SQLITE_AUTH_KEYWORDS)

def _auth_prefix(setting_id):
    setting_id = (setting_id or "").lower()
    if "." in setting_id:
        return setting_id.split(".", 1)[0]

    for keyword in KEYWORDS:
        if keyword in setting_id:
            prefix = setting_id.split(keyword, 1)[0].strip("._-")
            if prefix:
                return prefix

    return ""

def _is_related_auth_state(setting_id, auth_prefixes):
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

def _useful_auth_value(value, default=None):
    value = "" if value is None else str(value)
    default = "" if default is None else str(default)
    if value.lower() in ("", "0", "false", "none", "empty_setting"):
        return False
    return value != default or default.lower() in ("", "0", "false", "none", "empty_setting")

def _decode_xml(raw):
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", errors="ignore")

def _setting_value(setting):
    if "value" in setting.attrib:
        return setting.attrib.get("value"), "value"
    return setting.text or "", "text"

def _extract_auth_settings(xml_text):
    values = {}
    root = ET.fromstring(xml_text)
    all_settings = []
    auth_prefixes = set()

    for setting in root.findall("setting"):
        setting_id = setting.get("id")
        all_settings.append((setting_id, setting))
        value, _storage = _setting_value(setting)
        if _is_auth_setting(setting_id) and _useful_auth_value(value):
            prefix = _auth_prefix(setting_id)
            if prefix:
                auth_prefixes.add(prefix)

    for setting_id, setting in all_settings:
        if not _is_auth_setting(setting_id) and not _is_related_auth_state(setting_id, auth_prefixes):
            continue

        value, storage = _setting_value(setting)
        if value:
            values[setting_id.lower()] = {
                "id": setting_id,
                "value": value,
                "storage": storage
            }

    if "trakt" in auth_prefixes:
        existing_keys = {(setting_id or "").lower() for setting_id, _setting in all_settings}
        for setting_id, setting in all_settings:
            setting_key = (setting_id or "").lower()
            if setting_key == "trakt.authed.clientid":
                value, storage = _setting_value(setting)
                if value:
                    values[setting_key] = {
                        "id": setting_id,
                        "value": value,
                        "storage": storage
                    }
                continue

            if setting_key not in TRAKT_WATCHED_INDICATOR_VALUES:
                continue
            if setting_key not in existing_keys:
                continue
            value, storage = _setting_value(setting)
            values[setting_key] = {
                "id": setting_id,
                "value": value or TRAKT_WATCHED_INDICATOR_VALUES[setting_key],
                "storage": storage
            }

    external_values = {}
    for setting_id, setting in all_settings:
        setting_key = (setting_id or "").lower()
        if setting_key not in ("provider.external.enabled", "external_provider.module", "external_provider.name"):
            continue

        value, storage = _setting_value(setting)
        if value:
            external_values[setting_key] = {
                "id": setting_id,
                "value": value,
                "storage": storage
            }

    if external_values.get("external_provider.module") or external_values.get("external_provider.name"):
        values.update(external_values)
        values["provider.external.enabled"] = {
            "id": "provider.external.enabled",
            "value": "true",
            "storage": "text"
        }

    return values

def _accounts_fallback(z):
    try:
        raw = z.read("accounts.json")
    except KeyError:
        return {}

    try:
        return json.loads(_decode_xml(raw))
    except Exception:
        return {}

def _backup_auth_settings(z, addon, fallback_accounts):
    member = "addon_data/{}/settings.xml".format(addon)

    try:
        return _extract_auth_settings(_decode_xml(z.read(member)))
    except Exception:
        pass

    values = {}
    fallback = fallback_accounts.get(addon, {})
    if "settings.xml" in fallback:
        fallback = fallback.get("settings.xml", {})
    elif "databases/settings.db" in fallback:
        fallback = {}

    for setting_id, value in fallback.items():
        values[setting_id.lower()] = {
            "id": setting_id,
            "value": value,
            "storage": "text"
        }
    return values

def _backup_settings_root_attrib(z, addon):
    member = "addon_data/{}/settings.xml".format(addon)

    try:
        root = ET.fromstring(_decode_xml(z.read(member)))
        return dict(root.attrib)
    except Exception:
        return {"version": "2"}

def _restore_full_settings_xml(z, addon, target):
    member = "addon_data/{}/settings.xml".format(addon)

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with z.open(member) as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)
        return ET.parse(str(target))
    except Exception:
        root = ET.Element("settings", _backup_settings_root_attrib(z, addon))
        return ET.ElementTree(root)

def _read_zip_member_to_temp(z, member):
    fd, temp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    with z.open(member) as src, open(temp_path, "wb") as dst:
        shutil.copyfileobj(src, dst)

    return temp_path

def _sqlite_auth_rows(db_path):
    rows = {}

    try:
        con = sqlite3.connect(str(db_path))
        cur = con.cursor()
        raw_rows = cur.execute(
            "SELECT setting_id, setting_type, setting_default, setting_value FROM settings"
        ).fetchall()
        con.close()
    except Exception:
        return rows

    auth_prefixes = set()
    for setting_id, _setting_type, default, value in raw_rows:
        if _is_sqlite_auth_setting(setting_id) and _useful_auth_value(value, default):
            prefix = _auth_prefix(setting_id)
            if prefix:
                auth_prefixes.add(prefix)

    for setting_id, setting_type, default, value in raw_rows:
        setting_key = (setting_id or "").lower()
        if not _useful_auth_value(value, default):
            continue

        if _is_sqlite_auth_setting(setting_key) or _is_related_auth_state(setting_key, auth_prefixes):
            rows[setting_key] = {
                "id": setting_id,
                "type": setting_type,
                "default": default,
                "value": value
            }

    return rows

def _fallback_sqlite_rows(addon, fallback_accounts):
    rows = {}
    fallback = fallback_accounts.get(addon, {})
    db_values = fallback.get("databases/settings.db", {})

    for setting_id, row in db_values.items():
        if isinstance(row, dict):
            rows[setting_id.lower()] = {
                "id": setting_id,
                "type": row.get("type", "string"),
                "default": row.get("default", "empty_setting"),
                "value": row.get("value", "")
            }
        else:
            rows[setting_id.lower()] = {
                "id": setting_id,
                "type": "string",
                "default": "empty_setting",
                "value": row
            }

    return rows

def _backup_sqlite_auth_rows(z, addon, fallback_accounts):
    member = "addon_data/{}/databases/settings.db".format(addon)
    temp_path = None

    try:
        temp_path = _read_zip_member_to_temp(z, member)
        rows = _sqlite_auth_rows(temp_path)
        if rows:
            return rows
    except Exception:
        pass
    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    return _fallback_sqlite_rows(addon, fallback_accounts)

def _merge_sqlite_auth_settings(z, addon, fallback_accounts):
    auth_rows = _backup_sqlite_auth_rows(z, addon, fallback_accounts)
    if not auth_rows:
        return False

    target = KODI / "addon_data" / addon / "databases" / "settings.db"
    source_member = "addon_data/{}/databases/settings.db".format(addon)

    if not target.exists():
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(source_member) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            return True
        except Exception:
            return False

    try:
        con = sqlite3.connect(str(target))
        cur = con.cursor()
        existing = cur.execute("SELECT setting_id FROM settings").fetchall()
        existing_keys = {row[0].lower() for row in existing if row and row[0]}

        changed = False
        for setting_key, row in auth_rows.items():
            if setting_key in existing_keys:
                cur.execute(
                    "UPDATE settings SET setting_value=? WHERE lower(setting_id)=?",
                    (row["value"], setting_key)
                )
            else:
                cur.execute(
                    "INSERT INTO settings (setting_id, setting_type, setting_default, setting_value) VALUES (?, ?, ?, ?)",
                    (row["id"], row["type"], row["default"], row["value"])
                )
            changed = True

        con.commit()
        con.close()
        return changed
    except Exception:
        try:
            con.close()
        except Exception:
            pass
        return False

def _merge_auth_settings(z, addon, fallback_accounts):
    auth_values = _backup_auth_settings(z, addon, fallback_accounts)
    if not auth_values:
        return False

    target = KODI / "addon_data" / addon / "settings.xml"
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        try:
            tree = ET.parse(str(target))
            root = tree.getroot()
        except Exception:
            tree = _restore_full_settings_xml(z, addon, target)
            root = tree.getroot()
    else:
        tree = _restore_full_settings_xml(z, addon, target)
        root = tree.getroot()

    current = {}
    for setting in root.findall("setting"):
        setting_id = setting.get("id")
        if setting_id:
            current[setting_id.lower()] = setting

    auth_prefixes = set()
    for backup_setting in auth_values.values():
        prefix = _auth_prefix(backup_setting["id"])
        if prefix:
            auth_prefixes.add(prefix)

    for setting_id in current:
        if setting_id not in auth_values and _is_related_auth_state(setting_id, auth_prefixes):
            auth_values[setting_id] = {
                "id": current[setting_id].get("id"),
                "value": "true",
                "storage": "text"
            }

    changed = False
    for setting_key, backup_setting in auth_values.items():
        setting = current.get(setting_key)
        if setting is None:
            setting = ET.SubElement(root, "setting", {"id": backup_setting["id"]})
            current[setting_key] = setting

        if "value" in setting.attrib or backup_setting["storage"] == "value":
            if setting.attrib.get("value") != backup_setting["value"]:
                setting.set("value", backup_setting["value"])
                changed = True
        elif setting.text != backup_setting["value"]:
            setting.text = backup_setting["value"]
            changed = True

    if any(key.startswith("trakt.") for key in auth_values):
        for setting_key, value in TRAKT_WATCHED_INDICATOR_VALUES.items():
            setting = current.get(setting_key)
            if setting is None:
                continue

            if "value" in setting.attrib:
                if setting.attrib.get("value") != value:
                    setting.set("value", value)
                    changed = True
            elif setting.text != value:
                setting.text = value
                changed = True

    if "external_provider.module" in auth_values or "external_provider.name" in auth_values:
        setting = current.get("provider.external.enabled")
        if setting is None:
            setting = ET.SubElement(root, "setting", {"id": "provider.external.enabled"})
            current["provider.external.enabled"] = setting

        if "value" in setting.attrib:
            if setting.attrib.get("value") != "true":
                setting.set("value", "true")
                changed = True
        elif setting.text != "true":
            setting.text = "true"
            changed = True

    if changed:
        tree.write(str(target), encoding="utf-8", xml_declaration=False)

    return changed

def run_restore(zip_file, mode="full", selected=None, auth_only=False, settings_only=False):
    logger.info(f"Restore start: {zip_file}")
    selected = set(selected or [])

    with zipfile.ZipFile(zip_file,'r') as z:
        if auth_only:
            addons = selected or set(list_backup_addons(zip_file))
            fallback_accounts = _accounts_fallback(z)
            for addon in addons:
                _merge_auth_settings(z, addon, fallback_accounts)
                _merge_sqlite_auth_settings(z, addon, fallback_accounts)

            logger.info("Auth-only restore done")
            return

        for member in z.namelist():
            if member == "accounts.json" or member.endswith("/"):
                continue

            parts = _safe_member_parts(member)
            if not parts:
                continue

            if mode == "partial":
                if len(parts) < 3 or parts[0] != "addon_data" or parts[1] not in selected:
                    continue

            if settings_only:
                if len(parts) < 3 or parts[0] != "addon_data":
                    continue
                if parts[2] != "settings.xml" and parts[-2:] != ("databases", "settings.db"):
                    continue

            target = KODI.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(member) as src, open(target,'wb') as dst:
                shutil.copyfileobj(src,dst)

    logger.info("Restore done")
