"""Installing Minecraft and launching it."""
import logging
import subprocess
import sys
from pathlib import Path

import minecraft_launcher_lib as mll

from . import config

log = logging.getLogger("rihu.game")


class GameError(Exception):
    """An error whose message is safe and helpful to show to the user."""


def release_versions() -> list:
    """All official release versions, newest first. Needs internet."""
    versions = mll.utils.get_version_list()
    return [v["id"] for v in versions if v.get("type") == "release"]


def is_installed(version: str) -> bool:
    folder = config.MINECRAFT_DIR / "versions" / version
    return (folder / (version + ".json")).is_file() and (folder / (version + ".jar")).is_file()


def install(version: str, on_status, on_progress) -> None:
    """Download Minecraft from Mojang's official servers.
    on_status(text) and on_progress(fraction 0..1) are called while downloading."""
    state = {"max": 0}

    callback = {
        "setStatus": lambda text: on_status(text),
        "setMax": lambda value: state.__setitem__("max", max(int(value), 1)),
        "setProgress": lambda value: on_progress(min(int(value) / state["max"], 1.0) if state["max"] else None),
    }
    try:
        mll.install.install_minecraft_version(version, str(config.MINECRAFT_DIR), callback=callback)
    except Exception as err:
        log.exception("Install failed")
        raise GameError("Installing Minecraft %s failed: %s\nCheck your internet connection and press "
                        "Play again. Interrupted downloads are repaired automatically." % (version, err))
    if not is_installed(version):
        raise GameError("Minecraft %s still looks incomplete after installing. Press Play to retry." % version)


def validate(version: str, java_path: str, ram_mb: int) -> None:
    """Check everything that can be checked before starting the game."""
    if not is_installed(version):
        raise GameError("Minecraft %s is not installed correctly." % version)
    if java_path and not Path(java_path).is_file():
        raise GameError("The Java file you chose does not exist:\n%s\nFix it in Settings or clear it." % java_path)
    if ram_mb > config.total_ram_mb() - 1024:
        raise GameError("%d MB of RAM is too much for this PC (it has %d MB). Lower it in Settings."
                        % (ram_mb, config.total_ram_mb()))


def launch(version: str, instance_name: str, account, ram_mb: int, java_path: str):
    """Start Minecraft. Returns (process, log_file_path)."""
    game_dir = config.instance_dir(instance_name)
    options = {
        "username": account.name,
        "uuid": account.uuid,
        "token": account.access_token,
        "gameDirectory": str(game_dir),
        "launcherName": "RihuClient",
        "launcherVersion": config.APP_VERSION,
        "jvmArguments": ["-Xmx%dM" % ram_mb, "-Xms%dM" % min(ram_mb, 512)],
    }
    if java_path:
        options["executablePath"] = java_path
    try:
        command = mll.command.get_minecraft_command(version, str(config.MINECRAFT_DIR), options)
    except Exception as err:
        log.exception("Could not build launch command")
        raise GameError("Could not prepare the launch command: %s" % err)

    log_path = config.LOG_DIR / ("game-%s.log" % instance_name.replace(" ", "_"))
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        # NOTE: the command contains your access token, so it is never written to any log.
        log_file = open(log_path, "w", encoding="utf-8", errors="replace")
        proc = subprocess.Popen(command, cwd=str(game_dir), stdout=log_file, stderr=subprocess.STDOUT,
                                creationflags=flags)
    except FileNotFoundError:
        raise GameError("Java could not be found. In Settings, choose a Java executable (javaw.exe or java.exe).")
    except OSError as err:
        raise GameError("Could not start Java: %s" % err)

    try:  # if the game dies within a few seconds, report why
        code = proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        return proc, log_path
    raise GameError("Minecraft closed right after starting (exit code %s).\n%s" % (code, tail(log_path)))


def tail(path: Path, lines: int = 12) -> str:
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace").strip().splitlines()
        return "Last log lines:\n" + "\n".join(text[-lines:]) if text else "(the log is empty)"
    except OSError:
        return "(could not read the log)"
