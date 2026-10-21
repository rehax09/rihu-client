"""The launcher window, built with tkinter (it ships with Python, nothing extra to install)."""
import logging
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from . import auth, config, game, mods
from . import theme as themes
from .widgets import ProgressBar, RoundButton, RoundSlider, draw_logo

log = logging.getLogger("rihu.ui")
FONT = "Segoe UI"

HELP_TEXT = """Sign-in says 'not approved' or 'AzureAppNotPermitted'
  Mojang must approve your Azure application once. Follow README.md, step 3, then try again in a few days.

Sign-in window never comes back
  Make sure the redirect address in Settings (default http://localhost:53682) is exactly the one registered
  in Azure, and that no other program uses that port.

Minecraft closes right after starting
  Press 'Open logs' on the Home page and read the end of the game log. Common causes: too little RAM,
  a broken mod (turn mods off on the Mods page), or a wrong Java file chosen in Settings.

Download failed or was interrupted
  Press Play again. Missing or damaged files are downloaded again automatically.

'Java could not be found'
  Leave the Java setting empty so Minecraft's own Java is used, or pick javaw.exe in Settings.

Where is everything stored?
  %APPDATA%\\RihuClient  (settings, game files, profiles, logs). Use 'Open data folder' below.
"""


class App(tk.Tk):
    NAV = ["Home", "Profiles", "Mods", "Settings", "Help"]

    def __init__(self):
        super().__init__()
        self.settings = config.load_settings()
        self.t = themes.get_theme(self.settings)
        self.title("Rihu Client Launcher")
        self.geometry("1000x660")
        self.minsize(940, 620)
        self.account = None
        self.busy = False
        self.page = "Home"
        self.versions = ["1.8.9"]
        self.queue = queue.Queue()
        self.status = tk.StringVar(value="Ready")
        self.error = tk.StringVar(value="")
        self.account_var = tk.StringVar(value="Not signed in")
        self.progress = 0.0
        self.play_btn = self.bar = self.acct_btn = None
        self._build()
        self.after(100, self._poll)
        threading.Thread(target=self._startup_tasks, daemon=True).start()

    # ------------------------------------------------------------------ plumbing
    def post(self, fn):
        """Run fn on the UI thread (safe to call from worker threads)."""
        self.queue.put(fn)

    def _poll(self):
        try:
            while True:
                self.queue.get_nowait()()
        except queue.Empty:
            pass
        except Exception:
            log.exception("UI task failed")
        self.after(100, self._poll)

    def _save(self):
        try:
            config.save_settings(self.settings)
        except OSError as err:
            messagebox.showerror("Rihu Client", "Could not save settings:\n%s" % err)

    def _startup_tasks(self):
        try:
            versions = game.release_versions()
            if versions:
                self.post(lambda: self._set_versions(versions))
        except Exception as err:
            log.warning("Could not load the version list (offline?): %s", err)
        s = self.settings
        account = auth.silent_sign_in(s["client_id"], s["redirect_uri"])
        if account:
            self.account = account
            self.post(self._update_account_ui)

    def _set_versions(self, versions):
        self.versions = versions
        if self.page in ("Home", "Profiles"):
            self.show_page(self.page)

    def _update_account_ui(self):
        self.account_var.set(self.account.name if self.account else "Not signed in")
        if self.acct_btn is not None and self.acct_btn.winfo_exists():
            self.acct_btn.set_text("Sign out" if self.account else "Sign in")

    def _open(self, path):
        try:
            if sys.platform == "win32":
                os.startfile(str(path))
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as err:
            messagebox.showerror("Rihu Client", "Could not open %s:\n%s" % (path, err))

    # ------------------------------------------------------------------ layout
    def _style(self):
        t = self.t
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Rihu.TCombobox", fieldbackground=t["panel2"], background=t["panel2"],
                        foreground=t["text"], arrowcolor=t["text"], bordercolor=t["panel2"],
                        lightcolor=t["panel2"], darkcolor=t["panel2"], selectbackground=t["panel2"],
                        selectforeground=t["text"], padding=6)
        style.map("Rihu.TCombobox", fieldbackground=[("readonly", t["panel2"])],
                  foreground=[("readonly", t["text"])], selectbackground=[("readonly", t["panel2"])],
                  selectforeground=[("readonly", t["text"])])
        self.option_add("*TCombobox*Listbox.background", t["panel2"])
        self.option_add("*TCombobox*Listbox.foreground", t["text"])
        self.option_add("*TCombobox*Listbox.selectBackground", t["accent"])
        self.option_add("*TCombobox*Listbox.selectForeground", t["on_accent"])

    def _build(self):
        t = self.t
        for child in self.winfo_children():
            child.destroy()
        self.configure(bg=t["bg"])
        self._style()

        side = tk.Frame(self, bg=t["panel"], width=230)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        logo = tk.Canvas(side, width=230, height=130, bg=t["panel"], highlightthickness=0)
        logo.pack()
        draw_logo(logo, 115, 62, 56, t, t["panel"])
        logo.create_text(115, 112, text="Rihu Client", fill=t["text"], font=(FONT, 13, "bold"))

        self.nav_labels = {}
        for name in self.NAV:
            lbl = tk.Label(side, text="   " + name, anchor="w", font=(FONT, 12), bg=t["panel"], fg=t["muted"],
                           padx=14, pady=10, cursor="hand2")
            lbl.pack(fill="x", padx=12, pady=1)
            lbl.bind("<Button-1>", lambda e, n=name: self.show_page(n))
            lbl.bind("<Enter>", lambda e, w=lbl: w.configure(bg=t["panel2"]))
            lbl.bind("<Leave>", lambda e, w=lbl, n=name: w.configure(
                bg=t["panel2"] if n == self.page else t["panel"]))
            self.nav_labels[name] = lbl

        bottom = tk.Frame(side, bg=t["panel"])
        bottom.pack(side="bottom", fill="x", padx=16, pady=18)
        tk.Label(bottom, textvariable=self.account_var, bg=t["panel"], fg=t["text"], font=(FONT, 11, "bold"),
                 anchor="w").pack(fill="x", pady=(0, 8))
        self.acct_btn = RoundButton(bottom, "Sign out" if self.account else "Sign in", self._account_clicked, t,
                                    width=198, height=36, bg=t["panel"])
        self.acct_btn.pack()

        self.content = tk.Frame(self, bg=t["bg"])
        self.content.pack(side="left", fill="both", expand=True, padx=34, pady=28)
        self.show_page(self.page)

    def show_page(self, name):
        self.page = name
        t = self.t
        for n, lbl in self.nav_labels.items():
            lbl.configure(fg=t["accent"] if n == name else t["muted"], bg=t["panel2"] if n == name else t["panel"],
                          font=(FONT, 12, "bold" if n == name else "normal"))
        for child in self.content.winfo_children():
            child.destroy()
        self.play_btn = self.bar = None
        getattr(self, "_page_" + name.lower())()

    # ------------------------------------------------------------------ small helpers
    def _heading(self, text, sub):
        t = self.t
        tk.Label(self.content, text=text, bg=t["bg"], fg=t["text"], font=(FONT, 24, "bold"), anchor="w").pack(fill="x")
        tk.Label(self.content, text=sub, bg=t["bg"], fg=t["muted"], font=(FONT, 11), anchor="w").pack(fill="x", pady=(2, 0))

    def _card(self, parent=None, **pack):
        card = tk.Frame(parent or self.content, bg=self.t["panel"], padx=22, pady=18)
        return card

    def _label(self, parent, text, muted=False, size=11, bold=False, **kw):
        t = self.t
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=t["muted"] if muted else t["text"],
                        font=(FONT, size, "bold" if bold else "normal"), **kw)

    def _entry(self, parent, var, width=28):
        t = self.t
        return tk.Entry(parent, textvariable=var, width=width, bg=t["panel2"], fg=t["text"], insertbackground=t["text"],
                        relief="flat", font=(FONT, 11), highlightthickness=1, highlightbackground=t["panel2"],
                        highlightcolor=t["accent"])

    def _combo(self, parent, var, values, width=18):
        return ttk.Combobox(parent, textvariable=var, values=values, state="readonly", width=width,
                            style="Rihu.TCombobox", font=(FONT, 11))

    def _listbox(self, parent, height=9):
        t = self.t
        return tk.Listbox(parent, bg=t["panel2"], fg=t["text"], selectbackground=t["accent"],
                          selectforeground=t["on_accent"], highlightthickness=0, bd=0, activestyle="none",
                          font=(FONT, 11), height=height)

    def _btn(self, parent, text, cmd, width=140, **kw):
        return RoundButton(parent, text, cmd, self.t, width=width, height=38, bg=parent.cget("bg"), **kw)

    # ------------------------------------------------------------------ Home
    def _current(self):
        name = self.settings["selected_instance"]
        return name, self.settings["instances"][name]["version"]

    def _page_home(self):
        t = self.t
        name, version = self._current()
        self._heading("Play", "Pick a profile and version, then press Play.")

        card = self._card()
        card.pack(fill="x", pady=(18, 0))
        row = tk.Frame(card, bg=t["panel"])
        row.pack(fill="x")

        col = tk.Frame(row, bg=t["panel"])
        col.pack(side="left", padx=(0, 28))
        self._label(col, "Profile", muted=True, size=10).pack(anchor="w")
        prof_var = tk.StringVar(value=name)
        box = self._combo(col, prof_var, list(self.settings["instances"].keys()))
        box.pack(pady=(4, 0))
        box.bind("<<ComboboxSelected>>", lambda e: self._select_instance(prof_var.get()))

        col = tk.Frame(row, bg=t["panel"])
        col.pack(side="left", padx=(0, 28))
        self._label(col, "Minecraft version", muted=True, size=10).pack(anchor="w")
        ver_var = tk.StringVar(value=version)
        values = self.versions if version in self.versions else [version] + self.versions
        box = self._combo(col, ver_var, values, width=14)
        box.pack(pady=(4, 0))
        box.bind("<<ComboboxSelected>>", lambda e: self._set_version(ver_var.get()))

        col = tk.Frame(row, bg=t["panel"])
        col.pack(side="left")
        self._label(col, "Launch settings", muted=True, size=10).pack(anchor="w")
        java = os.path.basename(self.settings["java_path"]) or "automatic"
        self._label(col, "%.1f GB RAM  |  Java: %s" % (self.settings["ram_mb"] / 1024, java), size=11).pack(
            anchor="w", pady=(8, 0))

        play_row = tk.Frame(card, bg=t["panel"])
        play_row.pack(fill="x", pady=(22, 0))
        self.play_btn = RoundButton(play_row, "Play", self._on_play, t, width=240, height=56, primary=True,
                                    bg=t["panel"], size=17)
        self.play_btn.pack(side="left")
        self.play_btn.set_enabled(not self.busy)
        mod_count = len([m for m in mods.list_mods(name) if m[1]])
        self._label(play_row, "%d mod%s enabled in this profile" % (mod_count, "" if mod_count == 1 else "s"),
                    muted=True).pack(side="left", padx=20)

        status = self._card()
        status.pack(fill="x", pady=(16, 0))
        tk.Label(status, textvariable=self.status, bg=t["panel"], fg=t["text"], font=(FONT, 11), anchor="w").pack(fill="x")
        self.bar = ProgressBar(status, t, width=600)
        self.bar.pack(anchor="w", pady=(10, 0))
        self.bar.set(None if self.busy and self.progress is None else self.progress or 0.0)
        tk.Label(status, textvariable=self.error, bg=t["panel"], fg=themes.ERROR, font=(FONT, 10), anchor="w",
                 justify="left", wraplength=620).pack(fill="x", pady=(10, 0))

        tools = tk.Frame(self.content, bg=t["bg"])
        tools.pack(fill="x", pady=(14, 0))
        self._btn(tools, "Open game folder", lambda: self._open(config.instance_dir(name)), 160).pack(side="left")
        self._btn(tools, "Open logs", lambda: self._open(config.LOG_DIR), 120).pack(side="left", padx=10)
        self._label(self.content, "Mod loader: none yet. Minecraft runs as vanilla until the Rihu Client mod and "
                    "Legacy Fabric are added in the next stage.", muted=True, size=10, wraplength=700,
                    justify="left").pack(anchor="w", pady=(16, 0))

    def _select_instance(self, name):
        if name in self.settings["instances"]:
            self.settings["selected_instance"] = name
            self._save()
            self.show_page("Home")

    def _set_version(self, version):
        name, _ = self._current()
        self.settings["instances"][name]["version"] = version
        self._save()

    # ------------------------------------------------------------------ Play flow
    def set_status(self, text):
        self.post(lambda: self.status.set(text))

    def set_progress(self, frac):
        def apply():
            self.progress = frac
            if self.bar is not None and self.bar.winfo_exists():
                self.bar.set(frac)
        self.post(apply)

    def _set_busy(self, busy):
        def apply():
            self.busy = busy
            if self.play_btn is not None and self.play_btn.winfo_exists():
                self.play_btn.set_enabled(not busy)
        self.post(apply)

    def _on_play(self):
        if self.busy:
            return
        name, version = self._current()
        self.busy = True
        self.play_btn.set_enabled(False)
        self.error.set("")
        threading.Thread(target=self._play_worker, args=(name, version), daemon=True).start()

    def _play_worker(self, name, version):
        s = self.settings
        try:
            self.set_progress(None)
            self.set_status("Signing in...")
            account = auth.silent_sign_in(s["client_id"], s["redirect_uri"])
            if account is None:
                self.set_status("Finish signing in with Microsoft in your browser...")
                account = auth.sign_in(s["client_id"], s["redirect_uri"])
            self.account = account
            self.post(self._update_account_ui)

            if not game.is_installed(version):
                self.set_status("Downloading Minecraft %s..." % version)
            else:
                self.set_status("Checking Minecraft %s files..." % version)
            game.install(version, self.set_status, self.set_progress)

            self.set_progress(None)
            game.validate(version, s["java_path"], s["ram_mb"])
            self.set_status("Starting Minecraft %s..." % version)
            proc, log_path = game.launch(version, name, account, s["ram_mb"], s["java_path"])
            self.set_progress(1.0)
            self.set_status("Minecraft is running (profile %s, %s). Have fun, %s!" % (name, version, account.name))
            code = proc.wait()
            self.set_progress(0.0)
            if code == 0:
                self.set_status("Minecraft closed. Ready.")
            else:
                self.set_status("Minecraft stopped unexpectedly.")
                self.post(lambda: self.error.set("Exit code %s.\n%s" % (code, game.tail(log_path))))
        except (auth.AuthError, game.GameError) as err:
            self.set_progress(0.0)
            self.set_status("Could not start.")
            msg = str(err)
            self.post(lambda: self.error.set(msg))
        except Exception as err:
            log.exception("Unexpected launch error")
            self.set_progress(0.0)
            self.set_status("Something unexpected went wrong.")
            msg = "%s: %s\nDetails are in %s" % (type(err).__name__, err, config.LOG_DIR / "launcher.log")
            self.post(lambda: self.error.set(msg))
        finally:
            self._set_busy(False)

    def _account_clicked(self):
        if self.account:
            auth.sign_out()
            self.account = None
            self._update_account_ui()
            return
        if self.busy:
            return
        s = self.settings

        def work():
            try:
                self.set_status("Finish signing in with Microsoft in your browser...")
                self.account = auth.sign_in(s["client_id"], s["redirect_uri"])
                self.set_status("Signed in.")
                self.post(self._update_account_ui)
            except auth.AuthError as err:
                self.set_status("Sign-in failed.")
                self.post(lambda: self.error.set(str(err)))

        self.error.set("")
        threading.Thread(target=work, daemon=True).start()

    # ------------------------------------------------------------------ Profiles
    def _page_profiles(self):
        t = self.t
        self._heading("Profiles", "Each profile has its own worlds, mods and Minecraft version.")
        card = self._card()
        card.pack(fill="x", pady=(18, 0))
        names = list(self.settings["instances"].keys())
        lb = self._listbox(card, height=7)
        lb.pack(fill="x")
        for n in names:
            marker = "  (selected)" if n == self.settings["selected_instance"] else ""
            lb.insert("end", "%s    -    Minecraft %s%s" % (n, self.settings["instances"][n]["version"], marker))

        def chosen():
            sel = lb.curselection()
            return names[sel[0]] if sel else None

        def use():
            n = chosen()
            if n:
                self._select_instance(n)
                self.show_page("Profiles")

        def delete():
            n = chosen()
            if not n:
                return
            if len(names) == 1:
                messagebox.showinfo("Rihu Client", "You need at least one profile.")
                return
            if not messagebox.askyesno("Delete profile", "Delete '%s' and everything inside it (worlds, mods, "
                                       "settings)?\nThis cannot be undone." % n):
                return
            try:
                shutil.rmtree(config.INSTANCES_DIR / n)
            except OSError as err:
                messagebox.showerror("Rihu Client", "Could not delete the folder:\n%s" % err)
                return
            del self.settings["instances"][n]
            if self.settings["selected_instance"] == n:
                self.settings["selected_instance"] = next(iter(self.settings["instances"]))
            self._save()
            self.show_page("Profiles")

        bar = tk.Frame(card, bg=t["panel"])
        bar.pack(fill="x", pady=(14, 0))
        self._btn(bar, "Use selected", use, 130, primary=True).pack(side="left")
        self._btn(bar, "Open folder", lambda: chosen() and self._open(config.instance_dir(chosen())), 120).pack(
            side="left", padx=10)
        self._btn(bar, "Delete", delete, 100).pack(side="left")

        new = self._card()
        new.pack(fill="x", pady=(16, 0))
        self._label(new, "New profile", bold=True).pack(anchor="w")
        row = tk.Frame(new, bg=t["panel"])
        row.pack(fill="x", pady=(10, 0))
        name_var, ver_var = tk.StringVar(), tk.StringVar(value="1.8.9")
        self._entry(row, name_var, 24).pack(side="left", ipady=5)
        self._combo(row, ver_var, self.versions, width=12).pack(side="left", padx=12)

        def create():
            n = config.clean_instance_name(name_var.get())
            if not n:
                messagebox.showinfo("Rihu Client", "Type a name using letters, numbers, spaces, - or _.")
            elif n in self.settings["instances"]:
                messagebox.showinfo("Rihu Client", "A profile named '%s' already exists." % n)
            else:
                self.settings["instances"][n] = {"version": ver_var.get()}
                config.instance_dir(n)
                self._save()
                self.show_page("Profiles")

        self._btn(row, "Create", create, 100, primary=True).pack(side="left")

    # ------------------------------------------------------------------ Mods
    def _page_mods(self):
        t = self.t
        name, _ = self._current()
        self._heading("Mods", "Mods for profile '%s'. Disabled mods stay in the folder but are not loaded." % name)
        card = self._card()
        card.pack(fill="x", pady=(18, 0))
        lb = self._listbox(card, height=10)
        lb.pack(fill="x")
        items = mods.list_mods(name)
        for jar, enabled in items:
            lb.insert("end", ("ON    " if enabled else "OFF   ") + jar)
        if not items:
            lb.insert("end", "No mods yet. Press 'Add mod' and choose a .jar file.")

        def chosen():
            sel = lb.curselection()
            return items[sel[0]][0] if sel and items else None

        def add():
            path = filedialog.askopenfilename(title="Choose a mod", filetypes=[("Mod files", "*.jar")])
            if not path:
                return
            try:
                mods.add_mod(name, path)
            except (ValueError, FileExistsError, OSError) as err:
                messagebox.showerror("Rihu Client", str(err))
                return
            self.show_page("Mods")

        def toggle():
            jar = chosen()
            if jar:
                mods.toggle_mod(name, jar)
                self.show_page("Mods")

        def remove():
            jar = chosen()
            if jar and messagebox.askyesno("Remove mod", "Delete %s from this profile?" % jar):
                mods.remove_mod(name, jar)
                self.show_page("Mods")

        bar = tk.Frame(card, bg=t["panel"])
        bar.pack(fill="x", pady=(14, 0))
        self._btn(bar, "Add mod", add, 110, primary=True).pack(side="left")
        self._btn(bar, "Turn on / off", toggle, 130).pack(side="left", padx=10)
        self._btn(bar, "Remove", remove, 100).pack(side="left")
        self._btn(bar, "Open folder", lambda: self._open(mods.mods_dir(name)), 120).pack(side="left", padx=10)
        self._label(self.content, "Mods only load once a mod loader (Legacy Fabric for 1.8.9) is installed in the "
                    "profile. That comes with the Rihu Client mod stage.", muted=True, size=10, wraplength=700,
                    justify="left").pack(anchor="w", pady=(16, 0))

    # ------------------------------------------------------------------ Settings
    def _page_settings(self):
        t = self.t
        s = self.settings
        self._heading("Settings", "Changes are saved automatically.")
        grid = tk.Frame(self.content, bg=t["bg"])
        grid.pack(fill="both", expand=True, pady=(16, 0))
        grid.columnconfigure(0, weight=1, uniform="c")
        grid.columnconfigure(1, weight=1, uniform="c")

        # --- memory + java
        left = tk.Frame(grid, bg=t["bg"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ram = self._card(left)
        ram.pack(fill="x")
        self._label(ram, "Memory (RAM)", bold=True).pack(anchor="w")
        top = max(2048, min(config.total_ram_mb() - 1024, 16384))
        ram_text = tk.StringVar(value="%.2f GB" % (s["ram_mb"] / 1024))
        tk.Label(ram, textvariable=ram_text, bg=t["panel"], fg=t["accent"], font=(FONT, 14, "bold")).pack(anchor="w", pady=(6, 0))
        def ram_changed(value):
            ram_text.set("%.2f GB" % (value / 1024))

        def ram_done(value):
            s["ram_mb"] = int(value)
            self._save()

        RoundSlider(ram, t, 1024, top, 256, min(s["ram_mb"], top), ram_changed, ram_done, width=290,
                    bg=t["panel"]).pack(anchor="w", pady=(8, 0))
        self._label(ram, "1.8.9 runs well with 2 to 4 GB.", muted=True, size=10).pack(anchor="w", pady=(6, 0))

        java = self._card(left)
        java.pack(fill="x", pady=(14, 0))
        self._label(java, "Java file", bold=True).pack(anchor="w")
        self._label(java, "Leave empty to use Minecraft's own Java.", muted=True, size=10).pack(anchor="w", pady=(2, 8))
        java_var = tk.StringVar(value=s["java_path"])
        self._entry(java, java_var, 32).pack(fill="x", ipady=5)

        def java_save(_e=None):
            s["java_path"] = java_var.get().strip()
            self._save()

        def java_browse():
            path = filedialog.askopenfilename(title="Choose javaw.exe or java.exe",
                                              filetypes=[("Java", "java.exe javaw.exe"), ("All files", "*.*")])
            if path:
                java_var.set(path)
                java_save()

        jb = tk.Frame(java, bg=t["panel"])
        jb.pack(fill="x", pady=(10, 0))
        self._btn(jb, "Browse", java_browse, 100).pack(side="left")
        self._btn(jb, "Clear", lambda: (java_var.set(""), java_save()), 90).pack(side="left", padx=8)
        java_var.trace_add("write", lambda *a: java_save())

        # --- sign-in + appearance
        right = tk.Frame(grid, bg=t["bg"])
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        acct = self._card(right)
        acct.pack(fill="x")
        self._label(acct, "Microsoft sign-in", bold=True).pack(anchor="w")
        self._label(acct, "Azure client ID (README step 3)", muted=True, size=10).pack(
            anchor="w", pady=(2, 8))
        cid = tk.StringVar(value=s["client_id"])
        self._entry(acct, cid, 32).pack(fill="x", ipady=5)
        self._label(acct, "Redirect address", muted=True, size=10).pack(anchor="w", pady=(10, 4))
        redirect = tk.StringVar(value=s["redirect_uri"])
        self._entry(acct, redirect, 32).pack(fill="x", ipady=5)

        def save_login():
            s["client_id"] = cid.get().strip()
            s["redirect_uri"] = redirect.get().strip() or config.DEFAULT_SETTINGS["redirect_uri"]
            self._save()
            self.status.set("Sign-in settings saved.")

        self._btn(acct, "Save sign-in settings", save_login, 200).pack(anchor="w", pady=(12, 0))

        look = self._card(right)
        look.pack(fill="x", pady=(14, 0))
        self._label(look, "Appearance", bold=True).pack(anchor="w")
        chips = tk.Frame(look, bg=t["panel"])
        chips.pack(fill="x", pady=(10, 0))
        for preset in themes.PRESETS:
            self._btn(chips, preset, lambda p=preset: self._set_theme(p), 64, primary=(preset == s["theme"]), size=10).pack(
                side="left", padx=(0, 5))
        row2 = tk.Frame(look, bg=t["panel"])
        row2.pack(fill="x", pady=(10, 0))
        self._btn(row2, "Pick accent colour", self._pick_accent, 170).pack(side="left")
        self._btn(row2, "Reset", lambda: self._set_accent(""), 80).pack(side="left", padx=8)

    def _set_theme(self, preset):
        self.settings["theme"] = preset
        self.settings["accent"] = ""
        self._save()
        self.t = themes.get_theme(self.settings)
        self._build()

    def _set_accent(self, color):
        self.settings["accent"] = color
        self._save()
        self.t = themes.get_theme(self.settings)
        self._build()

    def _pick_accent(self):
        _rgb, hex_color = colorchooser.askcolor(color=self.t["accent"], title="Accent colour")
        if hex_color:
            self._set_accent(hex_color)

    # ------------------------------------------------------------------ Help
    def _page_help(self):
        t = self.t
        self._heading("Help", "Fixes for the most common problems.")
        card = self._card()
        card.pack(fill="both", expand=True, pady=(18, 0))
        text = tk.Text(card, bg=t["panel"], fg=t["text"], relief="flat", wrap="word", font=(FONT, 10), height=16,
                       highlightthickness=0, padx=4, pady=4)
        text.insert("1.0", HELP_TEXT)
        text.configure(state="disabled")
        text.pack(fill="both", expand=True)
        bar = tk.Frame(self.content, bg=t["bg"])
        bar.pack(fill="x", pady=(14, 0))
        self._btn(bar, "Open logs", lambda: self._open(config.LOG_DIR), 120).pack(side="left")
        self._btn(bar, "Open data folder", lambda: self._open(config.DATA_DIR), 160).pack(side="left", padx=10)
