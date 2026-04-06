"""ArtDraw Extreme — Legendary Edition v4  ·  Full-featured drawing studio."""

import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox, simpledialog
import math, random, json, os, time


class Layer:
    def __init__(self, name, tag):
        self.name = name
        self.tag = tag
        self.visible = True
        self.locked = False


class ArtCanvas:
    # ── Theme ──────────────────────────────────────────────────────
    BG_DARK     = "#050505"
    BG_CANVAS   = "#141414"
    ACCENT1     = "#FF4E7E"
    ACCENT2     = "#1E1E2E"
    ACCENT_GLOW = "#705BFF"
    TXT         = "#F0F0F0"
    TXT_DIM     = "#707070"
    TB_BG       = "#0A0A0A"
    DIVIDER     = "#252525"
    VP_COLOR    = "#FF6B35"
    VP_RADIUS   = 8
    PARAM_BG    = "#0E0E14"   # Shape parameter bar

    COPIC = [
        "#FFCDD2", "#F8BBD0", "#E1BEE7", "#D1C4E9", "#C5CAE9", "#BBDEFB",
        "#B3E5FC", "#B2EBF2", "#B2DFDB", "#C8E6C9", "#DCEDC8", "#F0F4C3",
        "#FFF9C4", "#FFECB3", "#FFE0B2", "#FFCCBC", "#D7CCC8", "#F5F5F5",
    ]

    def __init__(self, root):
        self.root = root
        self.root.title("ArtDraw Extreme — Legendary Edition v4")
        self.root.configure(bg=self.BG_DARK)
        self.root.geometry("1500x950")

        # ── Drawing State ──────────────────────────────────────────
        self.current_tool   = "Brush"
        self.brush_type     = "Marker"
        self.brush_color    = self.ACCENT1
        self.canvas_bg      = self.BG_CANVAS
        self.brush_size     = 15
        self.brush_opacity  = 0.6
        self.zoom_level     = 1.0

        # Mirror
        self.mirror_mode    = "OFF"
        self.mirror_modes   = ["OFF", "H", "V", "4-WAY", "6-WAY", "8-WAY"]

        # Perspective
        self.persp_mode     = "OFF"
        self.persp_modes    = ["OFF", "1-PT", "2-PT", "3-PT"]
        self.vanishing_pts  = []
        self.dragging_vp    = None

        # Shape parameters
        self.shape_sides    = 6
        self.star_points    = 5
        self.star_inner     = 40
        self.shape_rotation = 0
        self.shape_filled   = False

        self.grid_on        = False
        self.undo_stack     = []
        self.redo_stack     = []
        self.drawing_active = False
        self.preview_ids    = []

        # ── NEW v4 State ───────────────────────────────────────────
        # Layers
        self.layers = [Layer(f"Layer {i+1}", f"L{i}") for i in range(5)]
        self.active_layer_idx = 0
        # Recent colors
        self.recent_colors = []
        # Selection
        self.selection_ids  = []
        self.sel_rect_id    = None
        self.sel_drag_start = None
        # Text tool
        self.text_font_size = 24
        # Tooltip
        self._tooltip_win   = None
        # Cursor circle
        self.cursor_id      = None
        # Fullscreen
        self.is_fullscreen  = False
        # Auto-save
        self._autosave_path = os.path.join(os.path.expanduser("~"),
                                           ".artdraw_autosave.artdraw")

        self._build_ui()
        self._update_preview()
        self._bind_global_keys()
        self._schedule_autosave()

    # ══════════════════════════════════════════════════════════════
    #  UI CONSTRUCTION
    # ══════════════════════════════════════════════════════════════

    def _build_ui(self):
        # ── Top Toolbar ────────────────────────────────────────────
        tb = tk.Frame(self.root, bg=self.TB_BG, height=80)
        tb.pack(fill=tk.X, side=tk.TOP)
        tb.pack_propagate(False)

        # Brand
        brand = tk.Frame(tb, bg=self.TB_BG)
        brand.pack(side=tk.LEFT, padx=20)
        tk.Label(brand, text="✦ ArtDraw",
                 font=("Segoe UI", 18, "bold"),
                 fg=self.ACCENT1, bg=self.TB_BG).pack(side=tk.LEFT)
        tk.Label(brand, text="v4 LEGENDARY",
                 font=("Segoe UI", 7, "bold"),
                 fg="#FFF", bg=self.ACCENT_GLOW, padx=8).pack(side=tk.LEFT, padx=10)

        # HUD Center
        hud = tk.Frame(tb, bg=self.TB_BG)
        hud.pack(side=tk.LEFT, expand=True)

        # Brush preview
        self.prev_cv = tk.Canvas(hud, width=45, height=45,
                                 bg=self.TB_BG, highlightthickness=0)
        self.prev_cv.pack(side=tk.LEFT, padx=12)

        # Undo / Redo
        hist = tk.Frame(hud, bg=self.TB_BG)
        hist.pack(side=tk.LEFT, padx=8)
        for icon, cmd in [("⟲", self._undo), ("⟳", self._redo)]:
            b = tk.Label(hist, text=icon, font=("Segoe UI", 13),
                         fg=self.TXT, bg=self.ACCENT2, width=3, cursor="hand2")
            b.pack(side=tk.LEFT, padx=2)
            b.bind("<Button-1>", lambda e, c=cmd: c())

        # SIZE slider
        self._make_slider(hud, "SIZE", 1, 300, self.brush_size, self._on_size)
        # FLOW slider
        self._make_slider(hud, "FLOW", 1, 100,
                          int(self.brush_opacity * 100), self._on_flow)

        # ── Right Toolbar ──────────────────────────────────────────
        rt = tk.Frame(tb, bg=self.TB_BG)
        rt.pack(side=tk.RIGHT, padx=15)

        toolbar_btns = [
            ("Mirror: OFF", self._cycle_mirror, self.ACCENT2, "mir_btn"),
            ("Persp: OFF",  self._cycle_persp,  self.ACCENT2, "persp_btn"),
        ]
        for text, cmd, bg, attr in toolbar_btns:
            b = tk.Label(rt, text=text, font=("Segoe UI", 8, "bold"),
                         fg="#FFF", bg=bg, padx=10, pady=6, cursor="hand2")
            b.pack(side=tk.LEFT, padx=3)
            b.bind("<Button-1>", lambda e, c=cmd: c())
            setattr(self, attr, b)

        for text, cmd, bg in [("GRID", self._toggle_grid, self.TB_BG),
                               ("BG",   self._change_bg,   self.TB_BG),
                               ("Flip H", lambda: self._flip_view('H'), self.TB_BG),
                               ("Flip V", lambda: self._flip_view('V'), self.TB_BG),
                               ("⛶ Full", self._toggle_fullscreen, self.TB_BG),
                               ("💾 PNG", self._save_png,  "#2E7D32"),
                               ("📁 Save", self._save_project, "#1565C0"),
                               ("📂 Load", self._load_project, "#4527A0"),
                               ("Clear", self._clear_canvas, "#8B0000")]:
            b = tk.Label(rt, text=text, font=("Segoe UI", 8, "bold"),
                         fg="#FFF" if bg != self.TB_BG else self.TXT_DIM,
                         bg=bg, padx=10, pady=6, cursor="hand2",
                         highlightthickness=1 if bg == self.TB_BG else 0,
                         highlightbackground=self.ACCENT2)
            b.pack(side=tk.LEFT, padx=3)
            b.bind("<Button-1>", lambda e, c=cmd: c())
            if text == "GRID":
                self.grid_btn = b

        # ── Shape Parameter Bar (hidden by default) ────────────────
        self.param_bar = tk.Frame(self.root, bg=self.PARAM_BG, height=36)
        # Don't pack yet — shown only when a shape tool is selected
        self.param_bar.pack_propagate(False)
        self._build_param_bar()

        # ── Left Sidebar (Tools) — scrollable ─────────────────────
        sb_l_wrap = tk.Frame(self.root, bg=self.TB_BG, width=68)
        sb_l_wrap.pack(fill=tk.Y, side=tk.LEFT)
        sb_l_wrap.pack_propagate(False)
        sb_l_cv = tk.Canvas(sb_l_wrap, bg=self.TB_BG, highlightthickness=0, width=68)
        sb_l_cv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_l_scroll = tk.Scrollbar(sb_l_wrap, orient=tk.VERTICAL, command=sb_l_cv.yview)
        sb_l_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        sb_l_cv.configure(yscrollcommand=sb_l_scroll.set)
        sb_l = tk.Frame(sb_l_cv, bg=self.TB_BG, width=68)
        sb_l_id = sb_l_cv.create_window((0, 0), window=sb_l, anchor="nw")

        def _sb_l_configure(_e=None):
            sb_l_cv.configure(scrollregion=sb_l_cv.bbox("all"))
            try:
                sb_l_cv.itemconfigure(sb_l_id, width=sb_l_cv.winfo_width())
            except Exception:
                pass
        sb_l.bind("<Configure>", _sb_l_configure)
        sb_l_cv.bind("<Configure>", _sb_l_configure)

        def _sb_l_mousewheel(e):
            delta = -1 if e.delta > 0 else 1
            sb_l_cv.yview_scroll(delta, "units")
        sb_l_cv.bind("<MouseWheel>", _sb_l_mousewheel)
        self.tls = {}

        # --- BRUSHES ---
        self._section_label(sb_l, "BRUSHES")
        for ic, nm in [("🖌","Marker"),  ("🖊","Felt Pen"), ("☁️","Cloud"),
                        ("🎨","Oil"),     ("💧","Watercolor"),
                        ("✨","Glow"),    ("🖋","Calligraphy"),
                        ("✏️","Charcoal"), ("💦","Splatter"),
                        ("🌀","Swirl"),   ("🔥","Ember")]:
            self._add_tool_btn(sb_l, ic, nm)

        # --- SHAPES ---
        self._section_divider(sb_l)
        self._section_label(sb_l, "SHAPES")
        for ic, nm in [("⭕","Oval"),    ("🔲","Rect"),
                        ("⬡","Polygon"), ("⭐","Star"),
                        ("❤️","Heart"),  ("📏","Line"),
                        ("〰️","Dashed"), ("➡️","Arrow")]:
            self._add_tool_btn(sb_l, ic, nm)

        # --- UTILITY ---
        self._section_divider(sb_l)
        self._section_label(sb_l, "UTILITY")
        er = tk.Label(sb_l, text="🧽 Eraser",
                      font=("Segoe UI", 10, "bold"),
                      bg="#5D1A1A", fg="#FFF", pady=6, cursor="hand2")
        er.pack(fill=tk.X, pady=2)
        er.bind("<Button-1>", lambda e: self._select_tool("Eraser"))
        self._attach_tooltip(er, "Eraser")
        self.tls["Eraser"] = er
        self._add_tool_btn(sb_l, "🔍", "Color Pick")

        self.tls["Marker"].configure(bg=self.ACCENT_GLOW)

        # ── Right Sidebar (Colors) ─────────────────────────────────
        sb_r = tk.Frame(self.root, bg=self.TB_BG, width=64)
        sb_r.pack(fill=tk.Y, side=tk.RIGHT)
        sb_r.pack_propagate(False)
        self._section_label(sb_r, "COLORS")
        for hx in self.COPIC:
            lb = tk.Label(sb_r, bg=hx, height=1, width=3, cursor="hand2")
            lb.pack(pady=2, padx=15)
            lb.bind("<Button-1>", lambda e, c=hx: self._set_color(c))
        cp = tk.Label(sb_r, text="+ Custom", font=("Segoe UI", 7, "bold"),
                      fg=self.TXT_DIM, bg=self.TB_BG, cursor="hand2", pady=6)
        cp.pack(fill=tk.X, pady=4)
        cp.bind("<Button-1>", lambda e: self._pick_color())

        # Recent colors row
        self._section_label(sb_r, "RECENT")
        self.recent_frame = tk.Frame(sb_r, bg=self.TB_BG)
        self.recent_frame.pack(fill=tk.X)
        self._recent_labels = []
        for _ in range(8):
            lb = tk.Label(self.recent_frame, bg=self.TB_BG, height=1, width=3, cursor="hand2")
            lb.pack(pady=2, padx=15)
            lb.bind("<Button-1>", lambda e, w=lb: self._recent_click(w))
            self._recent_labels.append(lb)

        # ── Bottom Status ──────────────────────────────────────────
        bb = tk.Frame(self.root, bg="#020202", height=24)
        bb.pack(fill=tk.X, side=tk.BOTTOM)
        self.info_lbl = tk.Label(bb, text="Ready", font=("Segoe UI", 8),
                                 fg=self.TXT_DIM, bg="#020202", padx=20)
        self.info_lbl.pack(side=tk.LEFT)
        self.coord_lbl = tk.Label(bb, text="0, 0", font=("Consolas", 8),
                                  fg=self.TXT_DIM, bg="#020202", padx=20)
        self.coord_lbl.pack(side=tk.RIGHT)
        self.zoom_lbl = tk.Label(bb, text="100%", font=("Consolas", 8),
                                 fg=self.ACCENT_GLOW, bg="#020202", padx=10)
        self.zoom_lbl.pack(side=tk.RIGHT)
        self.layer_lbl = tk.Label(bb, text="Layer 1", font=("Segoe UI", 8),
                                  fg=self.ACCENT1, bg="#020202", padx=10)
        self.layer_lbl.pack(side=tk.LEFT)

        # ── Canvas ─────────────────────────────────────────────────
        self.canvas = tk.Canvas(self.root, bg=self.BG_CANVAS,
                                highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<Button-1>",        self._start_draw)
        self.canvas.bind("<B1-Motion>",       self._on_draw)
        self.canvas.bind("<ButtonRelease-1>", self._stop_draw)
        self.canvas.bind("<Button-3>",        self._start_drag_vp)
        self.canvas.bind("<B3-Motion>",       self._drag_vp)
        self.canvas.bind("<ButtonRelease-3>", self._stop_drag_vp)
        self.canvas.bind("<Motion>",          self._on_move)
        self.canvas.bind("<MouseWheel>",      self._on_zoom)
        self.canvas.bind("<Button-2>",
                         lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B2-Motion>",
                         lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))
        self.root.bind("<Control-z>", lambda e: self._undo())
        self.root.bind("<Control-y>", lambda e: self._redo())
        self.root.bind("<Control-s>", lambda e: self._save_png())

    # ── Shape Parameter Bar ────────────────────────────────────────

    def _build_param_bar(self):
        """Build the configurable shape parameter controls."""
        f = self.param_bar
        tk.Label(f, text="⚙ SHAPE PARAMS",
                 font=("Segoe UI", 7, "bold"),
                 fg=self.ACCENT1, bg=self.PARAM_BG).pack(side=tk.LEFT, padx=12)

        # Sides / Points
        self.sides_frame = tk.Frame(f, bg=self.PARAM_BG)
        self.sides_frame.pack(side=tk.LEFT, padx=8)
        self.sides_label = tk.Label(self.sides_frame, text="SIDES: 6",
                                    font=("Segoe UI", 7, "bold"),
                                    fg=self.TXT_DIM, bg=self.PARAM_BG)
        self.sides_label.pack()
        self.sides_scale = tk.Scale(
            self.sides_frame, from_=3, to=20, orient=tk.HORIZONTAL,
            bg=self.PARAM_BG, highlightthickness=0, showvalue=False,
            width=6, length=100, command=self._on_sides)
        self.sides_scale.set(self.shape_sides)
        self.sides_scale.pack()

        # Inner Radius (for stars)
        self.inner_frame = tk.Frame(f, bg=self.PARAM_BG)
        self.inner_frame.pack(side=tk.LEFT, padx=8)
        self.inner_label = tk.Label(self.inner_frame, text="INNER: 40%",
                                    font=("Segoe UI", 7, "bold"),
                                    fg=self.TXT_DIM, bg=self.PARAM_BG)
        self.inner_label.pack()
        self.inner_scale = tk.Scale(
            self.inner_frame, from_=10, to=90, orient=tk.HORIZONTAL,
            bg=self.PARAM_BG, highlightthickness=0, showvalue=False,
            width=6, length=100, command=self._on_inner)
        self.inner_scale.set(self.star_inner)
        self.inner_scale.pack()

        # Rotation
        rot_frame = tk.Frame(f, bg=self.PARAM_BG)
        rot_frame.pack(side=tk.LEFT, padx=8)
        self.rot_label = tk.Label(rot_frame, text="ROTATE: 0°",
                                  font=("Segoe UI", 7, "bold"),
                                  fg=self.TXT_DIM, bg=self.PARAM_BG)
        self.rot_label.pack()
        self.rot_scale = tk.Scale(
            rot_frame, from_=0, to=360, orient=tk.HORIZONTAL,
            bg=self.PARAM_BG, highlightthickness=0, showvalue=False,
            width=6, length=100, command=self._on_rotation)
        self.rot_scale.set(0)
        self.rot_scale.pack()

        # Fill toggle
        self.fill_btn = tk.Label(
            f, text="OUTLINE", font=("Segoe UI", 8, "bold"),
            fg=self.TXT_DIM, bg=self.PARAM_BG, padx=12, pady=4,
            cursor="hand2", highlightthickness=1,
            highlightbackground=self.ACCENT2)
        self.fill_btn.pack(side=tk.LEFT, padx=12)
        self.fill_btn.bind("<Button-1>", lambda e: self._toggle_fill())

    def _show_param_bar(self, tool):
        """Show/hide param bar and configure it for the active shape tool."""
        shape_tools = ["Polygon", "Star", "Oval", "Rect", "Heart",
                       "Line", "Dashed", "Arrow"]
        if tool in shape_tools:
            self.param_bar.pack(fill=tk.X, side=tk.TOP, before=self.canvas)
            # Show/hide relevant controls
            if tool == "Polygon":
                self.sides_frame.pack(side=tk.LEFT, padx=8)
                self.sides_label.configure(text=f"SIDES: {self.shape_sides}")
                self.inner_frame.pack_forget()
            elif tool == "Star":
                self.sides_frame.pack(side=tk.LEFT, padx=8)
                self.sides_label.configure(text=f"POINTS: {self.star_points}")
                self.sides_scale.set(self.star_points)
                self.inner_frame.pack(side=tk.LEFT, padx=8)
            else:
                self.sides_frame.pack_forget()
                self.inner_frame.pack_forget()
        else:
            self.param_bar.pack_forget()

    def _on_sides(self, v):
        v = int(v)
        if self.current_tool == "Star":
            self.star_points = v
            self.sides_label.configure(text=f"POINTS: {v}")
        else:
            self.shape_sides = v
            self.sides_label.configure(text=f"SIDES: {v}")

    def _on_inner(self, v):
        self.star_inner = int(v)
        self.inner_label.configure(text=f"INNER: {v}%")

    def _on_rotation(self, v):
        self.shape_rotation = int(v)
        self.rot_label.configure(text=f"ROTATE: {v}°")

    def _toggle_fill(self):
        self.shape_filled = not self.shape_filled
        self.fill_btn.configure(
            text="FILLED" if self.shape_filled else "OUTLINE",
            fg="#FFF" if self.shape_filled else self.TXT_DIM,
            highlightbackground=self.ACCENT1 if self.shape_filled else self.ACCENT2)

    # ── Sidebar Helpers ────────────────────────────────────────────

    def _section_label(self, parent, text):
        tk.Label(parent, text=text, font=("Segoe UI", 6, "bold"),
                 fg=self.TXT_DIM, bg=self.TB_BG, pady=5).pack(fill=tk.X)

    def _section_divider(self, parent):
        tk.Frame(parent, bg=self.DIVIDER, height=2).pack(fill=tk.X, pady=3)

    def _add_tool_btn(self, parent, icon, name):
        b = tk.Label(parent, text=icon, font=("Segoe UI Emoji", 13),
                     bg=self.TB_BG, fg=self.TXT, pady=4, cursor="hand2")
        b.pack(fill=tk.X)
        b.bind("<Button-1>", lambda e, n=name: self._select_tool(n))
        # Tooltip with tool name for clarity
        self._attach_tooltip(b, name)
        self.tls[name] = b

    def _make_slider(self, parent, label, lo, hi, init, cmd):
        box = tk.Frame(parent, bg=self.TB_BG, padx=8)
        box.pack(side=tk.LEFT)
        tk.Label(box, text=label, font=("Segoe UI", 7, "bold"),
                 fg=self.TXT_DIM, bg=self.TB_BG).pack()
        s = tk.Scale(box, from_=lo, to=hi, orient=tk.HORIZONTAL,
                     bg=self.TB_BG, highlightthickness=0, showvalue=False,
                     width=8, length=90, command=cmd)
        s.set(init)
        s.pack()

    # ══════════════════════════════════════════════════════════════
    #  TOOL & STATE LOGIC
    # ══════════════════════════════════════════════════════════════

    def _update_preview(self):
        self.prev_cv.delete("all")
        c = self.brush_color if self.current_tool != "Eraser" else "#FFF"
        r = max(3, min(16, self.brush_size / 8))
        self.prev_cv.create_oval(22-r, 22-r, 22+r, 22+r,
                                 fill=c, outline=self.TXT_DIM)

    def _select_tool(self, name):
        # Reset highlights
        for bname, b in self.tls.items():
            if bname == "Eraser":
                b.configure(bg="#5D1A1A")
            else:
                b.configure(bg=self.TB_BG)

        if name == "Color Pick":
            self.current_tool = "Eyedropper"
            if name in self.tls:
                self.tls[name].configure(bg=self.ACCENT_GLOW)
            self.info_lbl.configure(text="Tool: Eyedropper — click canvas to pick color")
            self._update_preview()
            return

        # Highlight selected
        if name == "Eraser":
            self.tls["Eraser"].configure(bg="#B71C1C")
        elif name in self.tls:
            self.tls[name].configure(bg=self.ACCENT_GLOW)

        brush_names = ["Marker", "Felt Pen", "Cloud", "Oil", "Watercolor",
                       "Glow", "Calligraphy", "Charcoal", "Splatter",
                       "Swirl", "Ember"]
        if name in brush_names:
            self.current_tool = "Brush"
            self.brush_type = name
        elif name == "Eraser":
            self.current_tool = "Eraser"
        else:
            self.current_tool = name

        self._show_param_bar(name)
        self.info_lbl.configure(text=f"Tool: {name}")
        self._update_preview()

    def _pick_color(self):
        res = colorchooser.askcolor(initialcolor=self.brush_color)[1]
        if res:
            self.brush_color = res
            self._remember_recent_color(res)
            self._update_preview()

    def _set_color(self, c):
        self.brush_color = c
        self._remember_recent_color(c)
        self._update_preview()

    def _remember_recent_color(self, color):
        try:
            if color in self.recent_colors:
                self.recent_colors.remove(color)
            self.recent_colors.insert(0, color)
            self.recent_colors = self.recent_colors[:8]
            self._update_recent_colors_ui()
        except Exception:
            pass

    def _update_recent_colors_ui(self):
        if not hasattr(self, "_recent_labels"):
            return
        for i, lb in enumerate(self._recent_labels):
            if i < len(self.recent_colors):
                c = self.recent_colors[i]
                lb.configure(bg=c)
                # Rebind with the correct color (avoid late binding)
                lb.bind("<Button-1>", lambda e, col=c: self._set_color(col))
            else:
                lb.configure(bg=self.TB_BG)
                lb.bind("<Button-1>", lambda e: None)

    def _recent_click(self, widget):
        c = widget.cget("bg")
        if c and c != self.TB_BG:
            self._set_color(c)

    def _on_size(self, v):
        self.brush_size = int(v)
        self._update_preview()
        try:
            if hasattr(self, "_last_mouse"):
                self._update_cursor_visual(*self._last_mouse)
        except Exception:
            pass

    def _on_flow(self, v):
        self.brush_opacity = int(v) / 100
        self._update_preview()
        try:
            if hasattr(self, "_last_mouse"):
                self._update_cursor_visual(*self._last_mouse)
        except Exception:
            pass

    def _update_cursor_visual(self, x, y):
        try:
            if self.cursor_id is not None:
                self.canvas.delete(self.cursor_id)
        except Exception:
            pass
        try:
            if self.current_tool in ("Brush", "Eraser"):
                r = max(2, (self.brush_size * self.zoom_level) / 2)
                color = self.ACCENT1
            else:
                r = 6
                color = self.TXT_DIM
            self.cursor_id = self.canvas.create_oval(
                x - r, y - r, x + r, y + r,
                outline=color, width=1, tags=("cursor",))
        except Exception:
            self.cursor_id = None

    def _on_move(self, e):
        x = int(self.canvas.canvasx(e.x))
        y = int(self.canvas.canvasy(e.y))
        self.coord_lbl.configure(text=f"{x}, {y}")
        # Track and draw dynamic cursor
        self._last_mouse = (x, y)
        self._update_cursor_visual(x, y)

    def _on_zoom(self, e):
        s = 1.1 if e.delta > 0 else 0.9
        # Use canvas coordinates for the scale pivot to keep zoom centered under cursor
        cx = self.canvas.canvasx(e.x)
        cy = self.canvas.canvasy(e.y)
        self.canvas.scale("all", cx, cy, s, s)
        self.zoom_level *= s
        # Update zoom indicator
        try:
            pct = max(1, int(self.zoom_level * 100))
            self.zoom_lbl.configure(text=f"{pct}%")
        except Exception:
            pass

    def _change_bg(self):
        res = colorchooser.askcolor(initialcolor=self.canvas_bg)[1]
        if res:
            self.canvas_bg = res
            self.canvas.configure(bg=res)
            self.info_lbl.configure(text=f"Background: {res}")

    def _bind_global_keys(self):
        """Bind global keyboard shortcuts and toggles."""
        # Help overlay (F1 or '?')
        self.root.bind("<F1>", lambda e: self._toggle_help_overlay())
        # '?' key can be unreliable across layouts; also bind Shift+/ which produces '?'
        self.root.bind("<Shift-/>", lambda e: self._toggle_help_overlay())
        # Keyboard zoom at center
        self.root.bind("<Control-=>", lambda e: self._zoom_at_center(1.1))
        self.root.bind("<Control-minus>", lambda e: self._zoom_at_center(0.9))
        # Fullscreen toggle
        self.root.bind("<F11>", lambda e: self._toggle_fullscreen())

    def _zoom_at_center(self, s):
        """Zoom relative to canvas center (for keyboard shortcuts)."""
        cx = self.canvas.canvasx(self.canvas.winfo_width() // 2)
        cy = self.canvas.canvasy(self.canvas.winfo_height() // 2)
        self.canvas.scale("all", cx, cy, s, s)
        self.zoom_level *= s
        try:
            pct = max(1, int(self.zoom_level * 100))
            self.zoom_lbl.configure(text=f"{pct}%")
        except Exception:
            pass

    def _toggle_help_overlay(self):
        if hasattr(self, "_help_win") and self._help_win and tk.Toplevel.winfo_exists(self._help_win):
            self._help_win.destroy()
            self._help_win = None
            return
        self._help_win = tk.Toplevel(self.root)
        self._help_win.title("ArtDraw Shortcuts")
        self._help_win.configure(bg=self.TB_BG)
        self._help_win.attributes("-topmost", True)
        self._help_win.resizable(False, False)
        frm = tk.Frame(self._help_win, bg=self.TB_BG, padx=16, pady=12)
        frm.pack(fill=tk.BOTH, expand=True)
        tk.Label(frm, text="Keyboard Shortcuts", font=("Segoe UI", 12, "bold"),
                 fg=self.ACCENT1, bg=self.TB_BG).pack(anchor="w", pady=(0,8))
        lines = [
            ("Ctrl+S", "Save PNG"),
            ("Ctrl+Z / Ctrl+Y", "Undo / Redo"),
            ("Mouse Wheel", "Zoom at cursor"),
            ("Middle-drag", "Pan canvas"),
            ("Ctrl+= / Ctrl-", "Zoom in / out"),
            ("F1 / ?", "Toggle this help"),
        ]
        for k, d in lines:
            row = tk.Frame(frm, bg=self.TB_BG)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=k, font=("Consolas", 10), fg=self.TXT, bg=self.TB_BG, width=16, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=d, font=("Segoe UI", 9), fg=self.TXT_DIM, bg=self.TB_BG).pack(side=tk.LEFT)
        tk.Button(frm, text="Close", command=self._toggle_help_overlay, relief=tk.FLAT,
                  bg=self.ACCENT2, fg=self.TXT).pack(anchor="e", pady=(10,0))

    def _attach_tooltip(self, widget, text):
        """Lightweight tooltip for a widget (shows on hover)."""
        tip = {"win": None}

        def show(_e):
            if tip["win"] is not None:
                return
            x = widget.winfo_rootx() + widget.winfo_width() + 8
            y = widget.winfo_rooty() + 4
            win = tk.Toplevel(widget)
            win.wm_overrideredirect(True)
            win.attributes("-topmost", True)
            tk.Label(win, text=text, font=("Segoe UI", 8),
                     bg="#111", fg="#EEE", padx=8, pady=4,
                     relief=tk.SOLID, bd=1).pack()
            win.wm_geometry(f"+{x}+{y}")
            tip["win"] = win

        def hide(_e):
            if tip["win"] is not None:
                try:
                    tip["win"].destroy()
                except Exception:
                    pass
                tip["win"] = None

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)

    def _toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        try:
            self.root.attributes("-fullscreen", self.is_fullscreen)
        except Exception:
            try:
                self.root.state("zoomed" if self.is_fullscreen else "normal")
            except Exception:
                pass
        self.info_lbl.configure(text=f"Fullscreen {'On' if self.is_fullscreen else 'Off'}")

    def _flip_view(self, axis):
        cx = self.canvas.winfo_width() / 2
        cy = self.canvas.winfo_height() / 2
        try:
            if axis == 'H':
                self.canvas.scale("all", cx, cy, -1, 1)
            else:
                self.canvas.scale("all", cx, cy, 1, -1)
            self.info_lbl.configure(text=f"View Flip {axis}")
        except Exception as _:
            pass

    # ══════════════════════════════════════════════════════════════
    #  MIRROR SYSTEM
    # ══════════════════════════════════════════════════════════════

    def _cycle_mirror(self):
        idx = self.mirror_modes.index(self.mirror_mode)
        self.mirror_mode = self.mirror_modes[(idx + 1) % len(self.mirror_modes)]
        active = self.mirror_mode != "OFF"
        self.mir_btn.configure(
            text=f"Mirror: {self.mirror_mode}",
            bg=self.ACCENT_GLOW if active else self.ACCENT2)
        self._draw_all_guides()

    def _mirror_points(self, x1, y1, x2, y2):
        cx = self.canvas.winfo_width() / 2
        cy = self.canvas.winfo_height() / 2
        m = self.mirror_mode
        pairs = [((x1, y1), (x2, y2))]
        if m == "H":
            pairs.append(((2*cx-x1, y1), (2*cx-x2, y2)))
        elif m == "V":
            pairs.append(((x1, 2*cy-y1), (x2, 2*cy-y2)))
        elif m == "4-WAY":
            pairs.append(((2*cx-x1, y1), (2*cx-x2, y2)))
            pairs.append(((x1, 2*cy-y1), (x2, 2*cy-y2)))
            pairs.append(((2*cx-x1, 2*cy-y1), (2*cx-x2, 2*cy-y2)))
        elif m in ("6-WAY", "8-WAY"):
            n = 6 if m == "6-WAY" else 8
            for k in range(1, n):
                angle = 2 * math.pi * k / n
                pairs.append(self._rotate_seg(x1, y1, x2, y2, cx, cy, angle))
        return pairs

    def _rotate_seg(self, x1, y1, x2, y2, cx, cy, angle):
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        def rot(px, py):
            dx, dy = px - cx, py - cy
            return (cx + dx*cos_a - dy*sin_a, cy + dx*sin_a + dy*cos_a)
        return (rot(x1, y1), rot(x2, y2))

    # ══════════════════════════════════════════════════════════════
    #  PERSPECTIVE SYSTEM
    # ══════════════════════════════════════════════════════════════

    def _cycle_persp(self):
        idx = self.persp_modes.index(self.persp_mode)
        self.persp_mode = self.persp_modes[(idx + 1) % len(self.persp_modes)]
        active = self.persp_mode != "OFF"
        self.persp_btn.configure(
            text=f"Persp: {self.persp_mode}",
            bg=self.ACCENT_GLOW if active else self.ACCENT2)
        self._init_vanishing_pts()
        self._draw_all_guides()
        if active:
            self.info_lbl.configure(
                text=f"Perspective: {self.persp_mode} — Right-click to drag VPs")

    def _init_vanishing_pts(self):
        w = self.canvas.winfo_width() or 1300
        h = self.canvas.winfo_height() or 800
        cx, cy = w // 2, h // 2
        if self.persp_mode == "1-PT":
            self.vanishing_pts = [[cx, cy]]
        elif self.persp_mode == "2-PT":
            self.vanishing_pts = [[50, cy], [w - 50, cy]]
        elif self.persp_mode == "3-PT":
            self.vanishing_pts = [[50, cy], [w - 50, cy], [cx, 30]]
        else:
            self.vanishing_pts = []

    def _persp_adjust(self, x1, y1, x2, y2):
        if self.persp_mode == "OFF" or not self.vanishing_pts:
            return x2, y2
        best_vp = min(self.vanishing_pts,
                      key=lambda vp: (vp[0]-x1)**2 + (vp[1]-y1)**2)
        dvx, dvy = best_vp[0] - x1, best_vp[1] - y1
        d_len = math.sqrt(dvx*dvx + dvy*dvy)
        if d_len < 5:
            return x2, y2
        dvx, dvy = dvx / d_len, dvy / d_len
        dmx, dmy = x2 - x1, y2 - y1
        move_len = math.sqrt(dmx*dmx + dmy*dmy)
        if move_len < 0.5:
            return x2, y2
        proj = dmx * dvx + dmy * dvy
        blend = 0.75
        return (x1 + proj*dvx*blend + dmx*(1-blend),
                y1 + proj*dvy*blend + dmy*(1-blend))

    # ── VP Dragging ────────────────────────────────────────────────

    def _start_drag_vp(self, e):
        if not self.vanishing_pts:
            return
        ox, oy = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
        best_idx, best_dist = -1, float("inf")
        for i, vp in enumerate(self.vanishing_pts):
            d = math.sqrt((vp[0]-ox)**2 + (vp[1]-oy)**2)
            if d < best_dist:
                best_dist, best_idx = d, i
        if best_dist < 60:
            self.dragging_vp = best_idx

    def _drag_vp(self, e):
        if self.dragging_vp is None:
            return
        ox, oy = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
        self.vanishing_pts[self.dragging_vp] = [ox, oy]
        self._draw_all_guides()

    def _stop_drag_vp(self, e):
        self.dragging_vp = None

    # ══════════════════════════════════════════════════════════════
    #  GUIDE RENDERING
    # ══════════════════════════════════════════════════════════════

    def _draw_all_guides(self):
        self.canvas.delete("guide")
        self._draw_mirror_guides()
        self._draw_persp_guides()
        self._draw_vp_markers()

    def _draw_mirror_guides(self):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        cx, cy = w // 2, h // 2
        gc = "#2A2A2A"
        m = self.mirror_mode
        if m in ("H", "4-WAY", "6-WAY", "8-WAY"):
            self.canvas.create_line(cx, 0, cx, h*2, fill=gc,
                                    dash=(4,4), tags="guide")
        if m in ("V", "4-WAY", "6-WAY", "8-WAY"):
            self.canvas.create_line(0, cy, w*2, cy, fill=gc,
                                    dash=(4,4), tags="guide")
        if m in ("6-WAY", "8-WAY"):
            d = max(w, h)
            self.canvas.create_line(cx-d, cy-d, cx+d, cy+d,
                                    fill=gc, dash=(4,4), tags="guide")
            self.canvas.create_line(cx+d, cy-d, cx-d, cy+d,
                                    fill=gc, dash=(4,4), tags="guide")
        if m == "8-WAY":
            d = max(w, h)
            for ang in [22.5, 67.5]:
                a = math.radians(ang)
                self.canvas.create_line(
                    cx-d*math.cos(a), cy-d*math.sin(a),
                    cx+d*math.cos(a), cy+d*math.sin(a),
                    fill="#1F1F1F", dash=(2,6), tags="guide")
                self.canvas.create_line(
                    cx-d*math.cos(a), cy+d*math.sin(a),
                    cx+d*math.cos(a), cy-d*math.sin(a),
                    fill="#1F1F1F", dash=(2,6), tags="guide")

    def _draw_persp_guides(self):
        if self.persp_mode == "OFF" or not self.vanishing_pts:
            return
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        pc = "#3A2525"
        for vp in self.vanishing_pts:
            vx, vy = vp
            for ty in [0, h]:
                for frac in [0, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1.0]:
                    self.canvas.create_line(vx, vy, int(w*frac), ty,
                                            fill=pc, dash=(6,8), tags="guide")
            for tx in [0, w]:
                for frac in [0.2, 0.4, 0.6, 0.8]:
                    self.canvas.create_line(vx, vy, tx, int(h*frac),
                                            fill=pc, dash=(6,8), tags="guide")

    def _draw_vp_markers(self):
        for i, vp in enumerate(self.vanishing_pts):
            x, y = vp
            r = self.VP_RADIUS
            self.canvas.create_oval(x-r-2, y-r-2, x+r+2, y+r+2,
                                    outline=self.VP_COLOR, width=2, tags="guide")
            self.canvas.create_oval(x-3, y-3, x+3, y+3,
                                    fill=self.VP_COLOR, outline="", tags="guide")
            self.canvas.create_text(x, y-r-8, text=f"VP{i+1}",
                                    fill=self.VP_COLOR,
                                    font=("Segoe UI", 8, "bold"), tags="guide")

    # ── Grid ───────────────────────────────────────────────────────

    def _toggle_grid(self):
        self.grid_on = not self.grid_on
        self.grid_btn.configure(fg="#FFF" if self.grid_on else self.TXT_DIM)
        if self.grid_on:
            for x in range(0, 2500, 40):
                for y in range(0, 1800, 40):
                    self.canvas.create_oval(x-1, y-1, x+1, y+1,
                                            fill="#1F1F1F", outline="",
                                            tags="grid")
        else:
            self.canvas.delete("grid")

    # ── History ────────────────────────────────────────────────────

    def _undo(self):
        if self.undo_stack:
            g = self.undo_stack.pop()
            for i in g:
                self.canvas.itemconfigure(i, state="hidden")
            self.redo_stack.append(g)
            self.info_lbl.configure(text="Undo")

    def _redo(self):
        if self.redo_stack:
            g = self.redo_stack.pop()
            for i in g:
                self.canvas.itemconfigure(i, state="normal")
            self.undo_stack.append(g)
            self.info_lbl.configure(text="Redo")

    def _clear_canvas(self):
        if not messagebox.askyesno(
            "Clear Canvas",
            "This will remove all strokes and cannot be undone.\nAre you sure you want to clear the canvas?",
        ):
            return
        self.canvas.delete("user")
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.info_lbl.configure(text="Canvas Cleared")

    # ══════════════════════════════════════════════════════════════
    #  AUTOSAVE (minimal)
    # ══════════════════════════════════════════════════════════════

    def _schedule_autosave(self, delay_ms: int = 180000):  # default 3 minutes
        try:
            if hasattr(self, "_autosave_job") and self._autosave_job:
                self.root.after_cancel(self._autosave_job)
        except Exception:
            pass
        try:
            self._autosave_job = self.root.after(delay_ms, self._do_autosave)
        except Exception:
            # If scheduling fails, silently ignore to avoid startup crashes
            self._autosave_job = None

    def _do_autosave(self):
        try:
            items = []
            for item_id in self.canvas.find_withtag("user"):
                itype = self.canvas.type(item_id)
                coords = list(self.canvas.coords(item_id))
                cfg = {}
                for prop in [
                    "fill", "outline", "width", "dash",
                    "stipple", "capstyle", "smooth",
                ]:
                    try:
                        val = self.canvas.itemcget(item_id, prop)
                        if val not in ("", None):
                            # convert width to float if possible
                            if prop == "width":
                                try:
                                    val = float(val)
                                except (ValueError, TypeError):
                                    pass
                            cfg[prop] = val
                    except Exception:
                        pass
                items.append({
                    "type": itype,
                    "coords": coords,
                    "config": cfg,
                    "state": self.canvas.itemcget(item_id, "state") or "normal",
                })
            project = {
                "version": 3,
                "canvas_bg": self.canvas_bg,
                "items": items,
                "vanishing_pts": self.vanishing_pts,
                "persp_mode": self.persp_mode,
                "mirror_mode": self.mirror_mode,
                "shape_sides": self.shape_sides,
                "star_points": self.star_points,
                "star_inner": self.star_inner,
            }
            # Ensure directory exists
            try:
                os.makedirs(os.path.dirname(self._autosave_path), exist_ok=True)
            except Exception:
                pass
            with open(self._autosave_path, "w") as f:
                json.dump(project, f)
        except Exception:
            # Avoid crashing on autosave errors
            pass
        finally:
            # Reschedule next autosave
            try:
                self._schedule_autosave()
            except Exception:
                pass

    # ══════════════════════════════════════════════════════════════
    #  SAVE / LOAD
    # ══════════════════════════════════════════════════════════════

    def _save_png(self):
        try:
            from PIL import ImageGrab
            path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG Image", "*.png"), ("JPEG", "*.jpg"),
                           ("All", "*.*")])
            if not path:
                return
            self.canvas.update()
            x = self.canvas.winfo_rootx()
            y = self.canvas.winfo_rooty()
            w = x + self.canvas.winfo_width()
            h = y + self.canvas.winfo_height()
            img = ImageGrab.grab(bbox=(x, y, w, h))
            img.save(path)
            self.info_lbl.configure(text=f"Saved: {os.path.basename(path)}")
        except ImportError:
            path = filedialog.asksaveasfilename(
                defaultextension=".ps",
                filetypes=[("PostScript", "*.ps")])
            if path:
                self.canvas.postscript(file=path, colormode="color")
                self.info_lbl.configure(text=f"Saved PS: {os.path.basename(path)}")
        except Exception as ex:
            messagebox.showerror("Save Error", str(ex))

    def _save_project(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".artdraw",
            filetypes=[("ArtDraw Project", "*.artdraw")])
        if not path:
            return
        items = []
        for item_id in self.canvas.find_withtag("user"):
            itype = self.canvas.type(item_id)
            coords = list(self.canvas.coords(item_id))
            cfg = {}
            try:
                for prop in ["fill", "outline", "width", "dash",
                              "stipple", "capstyle", "smooth"]:
                    try:
                        val = self.canvas.itemcget(item_id, prop)
                        if val:
                            cfg[prop] = val
                    except Exception:
                        pass
            except Exception:
                pass
            items.append({
                "type": itype, "coords": coords, "config": cfg,
                "state": self.canvas.itemcget(item_id, "state") or "normal"
            })
        project = {
            "version": 3, "canvas_bg": self.canvas_bg, "items": items,
            "vanishing_pts": self.vanishing_pts,
            "persp_mode": self.persp_mode,
            "mirror_mode": self.mirror_mode,
            "shape_sides": self.shape_sides,
            "star_points": self.star_points,
            "star_inner": self.star_inner,
        }
        with open(path, "w") as f:
            json.dump(project, f)
        self.info_lbl.configure(text=f"Project saved: {os.path.basename(path)}")

    def _load_project(self):
        path = filedialog.askopenfilename(
            filetypes=[("ArtDraw Project", "*.artdraw"), ("All", "*.*")])
        if not path:
            return
        try:
            with open(path, "r") as f:
                proj = json.load(f)
        except Exception as ex:
            messagebox.showerror("Load Error", str(ex))
            return
        self.canvas.delete("user")
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.canvas_bg = proj.get("canvas_bg", self.BG_CANVAS)
        self.canvas.configure(bg=self.canvas_bg)
        new_group = []
        for item in proj.get("items", []):
            itype = item["type"]
            coords = item["coords"]
            cfg = {k: v for k, v in item.get("config", {}).items()
                   if v not in ("", None)}
            cfg["tags"] = "user"
            # Convert width to float
            if "width" in cfg:
                try:
                    cfg["width"] = float(cfg["width"])
                except (ValueError, TypeError):
                    del cfg["width"]
            try:
                if itype == "line":
                    tid = self.canvas.create_line(*coords, **cfg)
                elif itype == "oval":
                    tid = self.canvas.create_oval(*coords, **cfg)
                elif itype == "rectangle":
                    tid = self.canvas.create_rectangle(*coords, **cfg)
                elif itype == "polygon":
                    tid = self.canvas.create_polygon(*coords, **cfg)
                else:
                    continue
                if item.get("state") == "hidden":
                    self.canvas.itemconfigure(tid, state="hidden")
                new_group.append(tid)
            except Exception:
                pass
        if new_group:
            self.undo_stack.append(new_group)
        # Restore settings
        self.vanishing_pts = proj.get("vanishing_pts", [])
        self.persp_mode = proj.get("persp_mode", "OFF")
        self.persp_btn.configure(
            text=f"Persp: {self.persp_mode}",
            bg=self.ACCENT_GLOW if self.persp_mode != "OFF" else self.ACCENT2)
        self.mirror_mode = proj.get("mirror_mode", "OFF")
        self.mir_btn.configure(
            text=f"Mirror: {self.mirror_mode}",
            bg=self.ACCENT_GLOW if self.mirror_mode != "OFF" else self.ACCENT2)
        self.shape_sides = proj.get("shape_sides", 6)
        self.star_points = proj.get("star_points", 5)
        self.star_inner = proj.get("star_inner", 40)
        self._draw_all_guides()
        self.info_lbl.configure(text=f"Loaded: {os.path.basename(path)}")

    # ══════════════════════════════════════════════════════════════
    #  DRAWING ENGINE
    # ══════════════════════════════════════════════════════════════

    def _start_draw(self, e):
        # Eyedropper: sample color under cursor and exit
        if getattr(self, "current_tool", "") == "Eyedropper":
            try:
                try:
                    from PIL import ImageGrab
                except ImportError:
                    # Fallback to system picker if PIL not available
                    return self._pick_color()
                xg = e.x_root if hasattr(e, "x_root") else self.root.winfo_pointerx()
                yg = e.y_root if hasattr(e, "y_root") else self.root.winfo_pointery()
                img = ImageGrab.grab(bbox=(xg, yg, xg+1, yg+1))
                rgb = img.getpixel((0, 0))
                hexc = "#%02x%02x%02x" % rgb
                self._set_color(hexc)
                self.info_lbl.configure(text=f"Picked: {hexc}")
                self._update_preview()
            except Exception:
                # As a last resort
                self._pick_color()
            return
        self.drawing_active = True
        ox, oy = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
        self.start_x, self.start_y = ox, oy
        self.last_x, self.last_y = ox, oy
        self.cur_g = []
        self.redo_stack.clear()

    def _on_draw(self, e):
        if not self.drawing_active:
            return
        ox, oy = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)

        if self.current_tool in ("Brush", "Eraser"):
            ax, ay = self._persp_adjust(self.last_x, self.last_y, ox, oy)
            for (p1, p2) in self._mirror_points(
                    self.last_x, self.last_y, ax, ay):
                self._paint(p1[0], p1[1], p2[0], p2[1])
            self.last_x, self.last_y = ax, ay
        else:
            # Shape live preview
            for pid in self.preview_ids:
                self.canvas.delete(pid)
            self.preview_ids = []
            for (s, en) in self._mirror_points(
                    self.start_x, self.start_y, ox, oy):
                tid = self._make_shape(s[0], s[1], en[0], en[1],
                                       self.current_tool, preview=True)
                if tid:
                    self.preview_ids.append(tid)

    def _stop_draw(self, e):
        if not self.drawing_active:
            return
        for pid in self.preview_ids:
            self.canvas.delete(pid)
        self.preview_ids = []
        if self.current_tool not in ("Brush", "Eraser"):
            ox, oy = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
            for (s, en) in self._mirror_points(
                    self.start_x, self.start_y, ox, oy):
                self._make_shape(s[0], s[1], en[0], en[1],
                                 self.current_tool)
        if self.cur_g:
            self.undo_stack.append(self.cur_g)
        self.drawing_active = False

    # ── Brush Stroke Rendering ─────────────────────────────────────

    def _paint(self, x1, y1, x2, y2):
        c = self.brush_color if self.current_tool != "Eraser" else self.canvas_bg
        sz = self.brush_size * self.zoom_level
        op = self.brush_opacity
        st = "gray50" if op < 0.5 else ("gray25" if op < 0.25 else "")
        tag = ("user",)
        bt = self.brush_type if self.current_tool != "Eraser" else "Eraser"

        if bt == "Glow":
            self.cur_g.append(self.canvas.create_line(
                x1, y1, x2, y2, fill=self.ACCENT_GLOW,
                width=sz*2, stipple="gray25", tags=tag))
            self.cur_g.append(self.canvas.create_line(
                x1, y1, x2, y2, fill="#FFFFFF",
                width=max(1, sz/3), capstyle=tk.ROUND, tags=tag))
        elif bt == "Cloud":
            for _ in range(3):
                oxx = random.randint(int(-sz), int(sz))
                oyy = random.randint(int(-sz), int(sz))
                self.cur_g.append(self.canvas.create_oval(
                    x2+oxx, y2+oyy, x2+oxx+sz, y2+oyy+sz,
                    fill=c, outline="", stipple="gray25", tags=tag))
        elif bt == "Oil":
            self.cur_g.append(self.canvas.create_line(
                x1, y1, x2, y2, fill=c, width=sz,
                capstyle=tk.BUTT, tags=tag))
            self.cur_g.append(self.canvas.create_line(
                x1+2, y1+2, x2+2, y2+2, fill="#000",
                width=max(1, sz/4), stipple="gray25", tags=tag))
        elif bt == "Watercolor":
            self.cur_g.append(self.canvas.create_oval(
                x2-sz*2, y2-sz*2, x2+sz*2, y2+sz*2,
                fill=c, outline="", stipple="gray12", tags=tag))
        elif bt == "Splatter":
            for _ in range(5):
                oxx = random.randint(-30, 30)
                oyy = random.randint(-30, 30)
                r = random.randint(1, 5)
                self.cur_g.append(self.canvas.create_oval(
                    x2+oxx, y2+oyy, x2+oxx+r, y2+oyy+r,
                    fill=c, outline="", tags=tag))
        elif bt == "Charcoal":
            self.cur_g.append(self.canvas.create_line(
                x1, y1, x2, y2, fill=c, width=sz,
                stipple="gray12", dash=(1, 3), tags=tag))
        elif bt == "Calligraphy":
            self.cur_g.append(self.canvas.create_line(
                x1, y1, x2, y2, fill=c, width=sz,
                capstyle=tk.BUTT, tags=tag))
        elif bt == "Swirl":
            # Swirl: offset stroke that curves around the cursor
            a = math.atan2(y2 - y1, x2 - x1) + math.pi / 4
            oxx = sz * 0.4 * math.cos(a)
            oyy = sz * 0.4 * math.sin(a)
            self.cur_g.append(self.canvas.create_line(
                x1, y1, x2, y2, fill=c, width=sz,
                capstyle=tk.ROUND, stipple=st, tags=tag))
            self.cur_g.append(self.canvas.create_line(
                x1+oxx, y1+oyy, x2+oxx, y2+oyy,
                fill=c, width=max(1, sz/3),
                stipple="gray50", tags=tag))
        elif bt == "Ember":
            # Ember: hot-particle scatter
            for _ in range(3):
                oxx = random.gauss(0, sz * 0.6)
                oyy = random.gauss(0, sz * 0.6)
                rsz = random.randint(1, max(2, int(sz / 4)))
                fc = random.choice(["#FF6600", "#FF3300", "#FFCC00", c])
                self.cur_g.append(self.canvas.create_oval(
                    x2+oxx, y2+oyy, x2+oxx+rsz, y2+oyy+rsz,
                    fill=fc, outline="", tags=tag))
        else:
            # Marker, Felt Pen, Eraser
            self.cur_g.append(self.canvas.create_line(
                x1, y1, x2, y2, fill=c, width=sz,
                capstyle=tk.ROUND, stipple=st, tags=tag))

    # ── Shape Rendering (Parametric) ───────────────────────────────

    def _make_shape(self, x1, y1, x2, y2, tool, preview=False):
        c    = self.brush_color
        sz   = self.brush_size * self.zoom_level
        tag  = "preview" if preview else "user"
        dash = (4, 4) if preview else None
        fill = c if self.shape_filled else ""
        rot  = math.radians(self.shape_rotation)
        tid  = None

        mx, my = (x1+x2)/2, (y1+y2)/2
        rx, ry = abs(x2-x1)/2, abs(y2-y1)/2

        if tool == "Oval":
            tid = self.canvas.create_oval(
                x1, y1, x2, y2, outline=c, fill=fill,
                width=sz, dash=dash, tags=tag)

        elif tool == "Rect":
            tid = self.canvas.create_rectangle(
                x1, y1, x2, y2, outline=c, fill=fill,
                width=sz, dash=dash, tags=tag)

        elif tool == "Polygon":
            n = self.shape_sides
            pts = self._regular_polygon(mx, my, rx, ry, n, rot)
            if pts:
                tid = self.canvas.create_polygon(
                    pts, outline=c, fill=fill,
                    width=sz, dash=dash, tags=tag)

        elif tool == "Star":
            n = self.star_points
            inner_ratio = self.star_inner / 100.0
            pts = self._star_polygon(mx, my, rx, ry, n, inner_ratio, rot)
            if pts:
                tid = self.canvas.create_polygon(
                    pts, outline=c, fill=fill,
                    width=sz, dash=dash, tags=tag)

        elif tool == "Heart":
            w, h = x2 - x1, y2 - y1
            if abs(w) > 2 and abs(h) > 2:
                tid = self.canvas.create_polygon(
                    x1+w/2, y1+h/4, x1+w/4, y1, x1, y1+h/4,
                    x1+w/2, y2, x2, y1+h/4, x2-w/4, y1,
                    x1+w/2, y1+h/4,
                    outline=c, fill=fill, width=sz, dash=dash,
                    smooth=True, tags=tag)

        elif tool == "Arrow":
            # Arrow shape pointing from start to end
            pts = self._arrow_polygon(x1, y1, x2, y2, sz * 3)
            if pts:
                tid = self.canvas.create_polygon(
                    pts, outline=c, fill=fill if fill else c,
                    width=max(1, sz/3), dash=dash, tags=tag)

        elif tool == "Line":
            tid = self.canvas.create_line(
                x1, y1, x2, y2, fill=c, width=sz,
                dash=dash, tags=tag)

        elif tool == "Dashed":
            tid = self.canvas.create_line(
                x1, y1, x2, y2, fill=c, width=sz,
                dash=(10, 10), tags=tag)

        if tid and not preview:
            self.cur_g.append(tid)
        return tid

    def _regular_polygon(self, cx, cy, rx, ry, sides, rot_offset=0):
        """Generate points for a regular polygon with N sides."""
        pts = []
        for i in range(sides):
            angle = 2 * math.pi * i / sides - math.pi / 2 + rot_offset
            pts.extend([cx + rx * math.cos(angle),
                        cy + ry * math.sin(angle)])
        return pts

    def _star_polygon(self, cx, cy, rx, ry, points, inner_ratio, rot_offset=0):
        """Generate points for a star with N points and configurable inner radius."""
        pts = []
        inner_rx = rx * inner_ratio
        inner_ry = ry * inner_ratio
        for i in range(points * 2):
            angle = math.pi * i / points - math.pi / 2 + rot_offset
            if i % 2 == 0:
                pts.extend([cx + rx * math.cos(angle),
                            cy + ry * math.sin(angle)])
            else:
                pts.extend([cx + inner_rx * math.cos(angle),
                            cy + inner_ry * math.sin(angle)])
        return pts

    def _arrow_polygon(self, x1, y1, x2, y2, head_size):
        """Generate an arrow polygon from (x1,y1) to (x2,y2)."""
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length < 5:
            return None
        # Normalize
        ux, uy = dx / length, dy / length
        # Perpendicular
        px, py = -uy, ux
        shaft_w = head_size * 0.3
        head_w = head_size
        neck = max(0, length - head_size)

        pts = [
            x1 + px * shaft_w,  y1 + py * shaft_w,    # shaft left start
            x1 + ux * neck + px * shaft_w,             # shaft left end
            y1 + uy * neck + py * shaft_w,
            x1 + ux * neck + px * head_w,              # head left
            y1 + uy * neck + py * head_w,
            x2, y2,                                     # tip
            x1 + ux * neck - px * head_w,              # head right
            y1 + uy * neck - py * head_w,
            x1 + ux * neck - px * shaft_w,             # shaft right end
            y1 + uy * neck - py * shaft_w,
            x1 - px * shaft_w,  y1 - py * shaft_w,    # shaft right start
        ]
        return pts


# ═══════════════════════════════════════════════════════════════════
#  LAUNCH
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll, c_int, byref
        hwnd = windll.user32.GetParent(root.winfo_id())
        windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(c_int(1)), 4)
    except Exception:
        pass
    app = ArtCanvas(root)
    root.mainloop()
