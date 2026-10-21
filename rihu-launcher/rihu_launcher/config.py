"""Settings, folder locations and small system helpers.

Everything the launcher saves lives in  %APPDATA%\\RihuClient  on Windows:
    settings.json   your launcher settings
    minecraft/      shared game files (libraries, assets, versions)
    instances/      one folder per profile (saves, mods, configs)
    logs/           launcher and game logs
"""
import copy
import ctypes
import json
import logging
import os
import re
import sys
from pathlib import Path

APP_NAME = "RihuClient"
APP_VERSION = "0.1.0"

log = logging.getLogger("rihu.config")


def _data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


DATA_DIR = _data_dir()
MINECRAFT_DIR = DATA_DIR / "minecraft"
INSTANCES_DIR = DATA_DIR / "instances"
LOG_DIR = DATA_DIR / "logs"
SETTINGS_FILE = DATA_DIR / "settings.json"
for _p in (MINECRAFT_DIR, INSTANCES_DIR, LOG_DIR):
    _p.mkdir(parents=True, exist_ok=True)

DEFAULT_SETTINGS = {
    # Azure application (client) ID. Required for Microsoft sign-in. See README.
    "client_id": "",
    "redirect_uri": "http://localhost:53682",
    "ram_mb": 2048,
    "java_path": "",  # empty = use the Java that Minecraft needs (downloaded automatically)
    "theme": "Purple",
    "accent": "",  # empty = use the theme's own accent colour
    "selected_instance": "Default",
    "instances": {"Default": {"version": "1.8.9"}},
}


def load_settings() -> dict:
    """Read settings.json. A broken file is renamed, never silently overwritten."""
    settings = copy.deepcopy(DEFAULT_SETTINGS)
    if SETTINGS_FILE.exists():
        try:
            loaded = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("settings.json is not a JSON object")
            settings.update(loaded)
        except (OSError, ValueError) as err:
            backup = SETTINGS_FILE.with_suffix(".json.broken")
            log.error("Could not read settings (%s). Moving it to %s", err, backup)
            try:
                SETTINGS_FILE.replace(backup)
            except OSError:
                pass
            settings = copy.deepcopy(DEFAULT_SETTINGS)
    if not settings.get("instances"):
        settings["instances"] = copy.deepcopy(DEFAULT_SETTINGS["instances"])
    if settings["selected_instance"] not in settings["instances"]:
        settings["selected_instance"] = next(iter(settings["instances"]))
    return settings


def save_settings(settings: dict) -> None:
    """Write settings safely: write a temp file first, then swap it in."""
    tmp = SETTINGS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    tmp.replace(SETTINGS_FILE)


def instance_dir(name: str) -> Path:
    path = INSTANCES_DIR / name
    (path / "mods").mkdir(parents=True, exist_ok=True)
    return path


def clean_instance_name(raw: str) -> str:
    """Keep only characters that are safe in a Windows folder name."""
    name = re.sub(r"[^A-Za-z0-9 _.\-]", "", raw).strip(" .")
    return name[:40]


def total_ram_mb() -> int:
    """Total installed RAM in MB (used to limit the RAM slider)."""
    if sys.platform != "win32":
        return 8192

    class MemStatus(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    try:
        status = MemStatus()
        status.dwLength = ctypes.sizeof(MemStatus)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
        return int(status.ullTotalPhys // (1024 * 1024))
    except Exception:  # pragma: no cover - fall back safely
        return 8192
