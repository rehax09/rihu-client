"""Starts Rihu Client Launcher:  python -m rihu_launcher"""
import ctypes
import logging
import sys
import traceback

from . import config


def main():
    logging.basicConfig(
        filename=str(config.LOG_DIR / "launcher.log"), level=logging.INFO, encoding="utf-8",
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("rihu").info("Rihu Client Launcher %s starting", config.APP_VERSION)
    if sys.platform == "win32":
        try:  # crisp text on high-DPI screens
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    try:
        from .ui import App
        App().mainloop()
    except Exception:
        logging.getLogger("rihu").exception("Fatal error")
        try:
            from tkinter import messagebox
            messagebox.showerror("Rihu Client Launcher",
                                 "The launcher crashed:\n\n%s\n\nDetails: %s" % (
                                     traceback.format_exc(limit=3), config.LOG_DIR / "launcher.log"))
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
