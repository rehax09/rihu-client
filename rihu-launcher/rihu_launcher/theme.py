"""Colour themes. The accent colour can be changed in Settings."""

PRESETS = {
    "Purple": dict(bg="#0F0B1A", panel="#181230", panel2="#241C45", text="#EEEAFB", muted="#9189B5", accent="#8B5CF6"),
    "Dark": dict(bg="#0C0C0E", panel="#151518", panel2="#1F1F25", text="#ECECEF", muted="#8A8A93", accent="#6EA8FE"),
    "Minimal": dict(bg="#121212", panel="#1A1A1A", panel2="#262626", text="#E8E8E8", muted="#8C8C8C", accent="#D4D4D4"),
    "Neon": dict(bg="#07060D", panel="#0F0D1C", panel2="#1A1536", text="#F2F0FF", muted="#7D7AA6", accent="#22F5C7"),
}
ERROR = "#FF6B7A"
OK = "#5BE3A0"


def _rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def blend(a: str, b: str, t: float) -> str:
    """Mix colour a into colour b. t=0 gives a, t=1 gives b."""
    ra, ga, ba = _rgb(a)
    rb, gb, bb = _rgb(b)
    return "#%02x%02x%02x" % (round(ra + (rb - ra) * t), round(ga + (gb - ga) * t), round(ba + (bb - ba) * t))


def on_color(bg: str) -> str:
    """Pick readable text colour (dark or light) for a given background."""
    r, g, b = _rgb(bg)
    return "#0B0B10" if (0.299 * r + 0.587 * g + 0.114 * b) > 150 else "#FFFFFF"


def get_theme(settings: dict) -> dict:
    theme = dict(PRESETS.get(settings.get("theme"), PRESETS["Purple"]))
    accent = settings.get("accent", "")
    if isinstance(accent, str) and len(accent) == 7 and accent.startswith("#"):
        theme["accent"] = accent
    theme["on_accent"] = on_color(theme["accent"])
    return theme
