"""Managing the .jar files in an instance's mods folder."""
import shutil
from pathlib import Path

from . import config


def mods_dir(instance_name: str) -> Path:
    return config.instance_dir(instance_name) / "mods"


def list_mods(instance_name: str) -> list:
    """Returns [(file name, enabled)] sorted by name."""
    items = []
    for f in sorted(mods_dir(instance_name).iterdir(), key=lambda p: p.name.lower()):
        if f.name.endswith(".jar"):
            items.append((f.name, True))
        elif f.name.endswith(".jar.disabled"):
            items.append((f.name[: -len(".disabled")], False))
    return items


def add_mod(instance_name: str, source: str) -> str:
    """Copy a .jar into the mods folder. Never overwrites an existing mod silently."""
    src = Path(source)
    if src.suffix.lower() != ".jar":
        raise ValueError("Only .jar files can be added.")
    dest = mods_dir(instance_name) / src.name
    if dest.exists() or Path(str(dest) + ".disabled").exists():
        raise FileExistsError("%s is already in this profile. Remove it first to replace it." % src.name)
    shutil.copy2(src, dest)
    return src.name


def toggle_mod(instance_name: str, jar_name: str) -> None:
    on = mods_dir(instance_name) / jar_name
    off = mods_dir(instance_name) / (jar_name + ".disabled")
    if on.exists():
        on.rename(off)
    elif off.exists():
        off.rename(on)


def remove_mod(instance_name: str, jar_name: str) -> None:
    for candidate in (jar_name, jar_name + ".disabled"):
        p = mods_dir(instance_name) / candidate
        if p.exists():
            p.unlink()
