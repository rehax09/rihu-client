"""Custom-drawn widgets: rounded buttons with a glow, a progress bar and the logo."""
import tkinter as tk

from .theme import blend


def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    """Draw a rounded rectangle on a canvas."""
    r = max(0, min(r, (x2 - x1) // 2, (y2 - y1) // 2))
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


class RoundButton(tk.Canvas):
    """A rounded button. 'primary' buttons use the accent colour and a soft glow."""

    def __init__(self, parent, text, command, theme, width=150, height=40, primary=False, bg=None, size=11):
        self._bg = bg or theme["bg"]
        super().__init__(parent, width=width, height=height, bg=self._bg, highlightthickness=0, bd=0,
                         cursor="hand2")
        self.theme, self._text, self._cmd, self._primary = theme, text, command, primary
        self._bw, self._bh, self._enabled = width, height, True
        self._font = ("Segoe UI Semibold", size)
        self._t, self._target, self._job = 0.0, 0.0, None
        self.bind("<Enter>", lambda e: self._go(1.0))
        self.bind("<Leave>", lambda e: self._go(0.0))
        self.bind("<ButtonRelease-1>", self._click)
        self._draw()

    def set_text(self, text):
        self._text = text
        self._draw()

    def set_enabled(self, enabled):
        self._enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw()

    def _click(self, event):
        if self._enabled and 0 <= event.x <= self._bw and 0 <= event.y <= self._bh:
            self._cmd()

    def _go(self, target):
        self._target = target
        if self._job is None:
            self._step()

    def _step(self):
        diff = self._target - self._t
        if abs(diff) < 0.05:
            self._t, self._job = self._target, None
            self._draw()
            return
        self._t += diff * 0.45
        self._draw()
        self._job = self.after(16, self._step)

    def _draw(self):
        if not self.winfo_exists():
            return
        self.delete("all")
        t, h = self.theme, self._bh
        hover = self._t if self._enabled else 0.0
        if self._primary and self._enabled:
            glow = blend(self._bg, t["accent"], 0.20 + 0.20 * hover)
            round_rect(self, 0, 0, self._bw, h, h // 2, fill=glow, outline="")
            fill = blend(t["accent"], "#FFFFFF", 0.16 * hover)
            round_rect(self, 3, 3, self._bw - 3, h - 3, (h - 6) // 2, fill=fill, outline="")
            fg = t["on_accent"]
        else:
            fill = blend(t["panel2"], "#FFFFFF", 0.09 * hover)
            round_rect(self, 0, 0, self._bw, h, 10, fill=fill, outline="")
            fg = t["text"] if self._enabled else t["muted"]
        self.create_text(self._bw // 2, h // 2, text=self._text, fill=fg, font=self._font)


class ProgressBar(tk.Canvas):
    """A rounded progress bar. set(None) shows a moving 'working...' animation."""

    def __init__(self, parent, theme, width=560, height=8, bg=None):
        super().__init__(parent, width=width, height=height, bg=bg or theme["panel"], highlightthickness=0, bd=0)
        self.theme, self._bw, self._bh = theme, width, height
        self._frac, self._phase, self._job = 0.0, 0.0, None
        self._draw()

    def set(self, frac):
        if frac is None:
            if self._job is None:
                self._spin()
            return
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        self._frac = max(0.0, min(1.0, frac))
        self._draw()

    def _spin(self):
        if not self.winfo_exists():
            return
        self._phase = (self._phase + 0.03) % 1.0
        self._draw(spin=True)
        self._job = self.after(30, self._spin)

    def _draw(self, spin=False):
        if not self.winfo_exists():
            return
        self.delete("all")
        t, h = self.theme, self._bh
        round_rect(self, 0, 0, self._bw, h, h // 2, fill=t["panel2"], outline="")
        if spin:
            width = self._bw * 0.25
            start = (self._bw + width) * self._phase - width
            x1, x2 = max(0, start), min(self._bw, start + width)
        else:
            x1, x2 = 0, self._bw * self._frac
        if x2 - x1 > h:
            round_rect(self, int(x1), 0, int(x2), h, h // 2, fill=t["accent"], outline="")


def draw_logo(canvas, cx, cy, size, theme, bg):
    """The Rihu Client mark: a glowing rounded tile holding an 'R' with a spark."""
    half = size // 2
    for i in range(6, 0, -1):  # soft glow rings
        grow = i * 4
        round_rect(canvas, cx - half - grow, cy - half - grow, cx + half + grow, cy + half + grow,
                   size // 3 + grow, fill=blend(bg, theme["accent"], 0.035 * (7 - i)), outline="")
    round_rect(canvas, cx - half, cy - half, cx + half, cy + half, size // 3, fill=theme["accent"], outline="")
    round_rect(canvas, cx - half + 5, cy - half + 5, cx + half - 5, cy + half - 5, size // 3 - 4,
               fill=blend(theme["accent"], "#000000", 0.38), outline="")
    canvas.create_text(cx - 1, cy + 1, text="R", fill="#FFFFFF", font=("Segoe UI Black", int(size * 0.46)))
    s = size // 9  # the spark in the corner
    sx, sy = cx + half - 8, cy - half + 9
    canvas.create_polygon(sx, sy - s, sx + s // 2, sy, sx, sy + s, sx - s // 2, sy, fill=theme["accent"], outline="")


class RoundSlider(tk.Canvas):
    """A slider with a visible glowing handle. Click or drag anywhere on it."""

    def __init__(self, parent, theme, minimum, maximum, step, value, on_change, on_release, width=290, bg=None):
        super().__init__(parent, width=width, height=28, bg=bg or theme["panel"], highlightthickness=0, bd=0,
                         cursor="hand2")
        self.theme, self._min, self._max, self._step = theme, minimum, maximum, step
        self._bw, self._on_change, self._on_release = width, on_change, on_release
        self.value = self._snap(value)
        self.bind("<Button-1>", self._drag)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", lambda e: self._on_release(self.value))
        self._draw()

    def _snap(self, v):
        v = max(self._min, min(self._max, v))
        return min(self._max, int(round((v - self._min) / self._step)) * self._step + self._min)

    def _drag(self, event):
        pad = 12
        frac = (event.x - pad) / float(self._bw - 2 * pad)
        v = self._snap(self._min + frac * (self._max - self._min))
        if v != self.value:
            self.value = v
            self._draw()
            self._on_change(v)

    def _draw(self):
        self.delete("all")
        t, pad, mid = self.theme, 12, 14
        frac = (self.value - self._min) / float(max(1, self._max - self._min))
        x = pad + frac * (self._bw - 2 * pad)
        round_rect(self, pad, mid - 3, self._bw - pad, mid + 3, 3, fill=t["panel2"], outline="")
        if x - pad > 6:
            round_rect(self, pad, mid - 3, int(x), mid + 3, 3, fill=t["accent"], outline="")
        self.create_oval(x - 12, mid - 12, x + 12, mid + 12, fill=blend(t["panel"], t["accent"], 0.3), outline="")
        self.create_oval(x - 8, mid - 8, x + 8, mid + 8, fill=t["accent"], outline="")
