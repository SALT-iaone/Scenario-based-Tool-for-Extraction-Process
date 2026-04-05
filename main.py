"""
S.T.E.P. v2.2
Mac / Windows 両対応 · Python 3.8+
依存: pip install mysql-connector-python "sshtunnel>=0.4" "paramiko>=2.11,<3"
"""

import base64
import csv
import datetime
import json
import os
import re
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

try:
    import mysql.connector
except ImportError:
    mysql = None

try:
    from sshtunnel import SSHTunnelForwarder
    import paramiko
except ImportError:
    SSHTunnelForwarder = None
    paramiko = None

# ── 設定ファイル ───────────────────────────────────────────────
CONFIG_DIR      = os.path.join(os.path.expanduser("~"), ".step_tool")
CONFIG_FILE     = os.path.join(CONFIG_DIR, "connections.json")
SCENARIOS_FILE  = os.path.join(CONFIG_DIR, "scenarios.json")
VARIABLES_FILE  = os.path.join(CONFIG_DIR, "variables.json")

# ── パスワード簡易エンコード ───────────────────────────────────
def _enc(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("ascii")

def _dec(s: str) -> str:
    try:
        return base64.b64decode(s.encode("ascii")).decode("utf-8")
    except Exception:
        return ""

# ── 設定 I/O ──────────────────────────────────────────────────
def load_configs() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_configs(cfg: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def load_scenarios() -> list:
    if os.path.exists(SCENARIOS_FILE):
        with open(SCENARIOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return [{"name": "シナリオ 1", "sql": "SELECT * FROM your_table LIMIT 1000;"}]

def save_scenarios(scenarios: list):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(SCENARIOS_FILE, "w", encoding="utf-8") as f:
        json.dump(scenarios, f, ensure_ascii=False, indent=2)

def load_variables() -> list:
    """[{"key": "start_date", "val": "2024-01-01"}, ...] の形式"""
    if os.path.exists(VARIABLES_FILE):
        with open(VARIABLES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_variables(variables: list):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(VARIABLES_FILE, "w", encoding="utf-8") as f:
        json.dump(variables, f, ensure_ascii=False, indent=2)

def substitute_vars(sql: str, variables: dict) -> str:
    def replacer(m):
        key = m.group(1)
        return variables.get(key, m.group(0))
    return re.sub(r"\{(\w+)\}", replacer, sql)

# ── カラーパレット ────────────────────────────────────────────
C = {
    "bg":       "#0f1117",
    "surface":  "#1a1d27",
    "card":     "#1e2235",
    "card2":    "#181b2e",
    "card3":    "#141627",   # ジャンプサーバー用（一段深い）
    "border":   "#2c3050",
    "accent":   "#4f8ef7",
    "accent2":  "#7c5cfc",
    "success":  "#34d399",
    "warning":  "#fbbf24",
    "danger":   "#f87171",
    "ssh":      "#38bdf8",
    "jump":     "#a78bfa",   # ジャンプサーバー色
    "text":     "#e8eaf6",
    "muted":    "#6b7280",
    "input_bg": "#141726",
    "sel_bg":   "#2a3060",
}

FONT_FAMILY = "Courier New" if sys.platform == "win32" else "Menlo"
FONT_UI     = ("Segoe UI", 9)  if sys.platform == "win32" else ("SF Pro Display", 10)
FONT_MONO   = (FONT_FAMILY, 9) if sys.platform == "win32" else (FONT_FAMILY, 10)
FONT_TITLE  = ("Segoe UI", 12, "bold") if sys.platform == "win32" else ("SF Pro Display", 13, "bold")
FONT_SMALL  = ("Segoe UI", 8)  if sys.platform == "win32" else ("SF Pro Display", 9)


# ── カスタムウィジェット ──────────────────────────────────────
class StyledEntry(tk.Entry):
    def __init__(self, master, **kw):
        kw.setdefault("bg",                C["input_bg"])
        kw.setdefault("fg",                C["text"])
        kw.setdefault("insertbackground",  C["accent"])
        kw.setdefault("relief",            "flat")
        kw.setdefault("font",              FONT_MONO)
        kw.setdefault("highlightthickness", 1)
        kw.setdefault("highlightbackground", C["border"])
        kw.setdefault("highlightcolor",    C["accent"])
        super().__init__(master, **kw)

class StyledText(tk.Text):
    def __init__(self, master, **kw):
        kw.setdefault("bg",                C["input_bg"])
        kw.setdefault("fg",                C["text"])
        kw.setdefault("insertbackground",  C["accent"])
        kw.setdefault("relief",            "flat")
        kw.setdefault("font",              FONT_MONO)
        kw.setdefault("highlightthickness", 1)
        kw.setdefault("highlightbackground", C["border"])
        kw.setdefault("highlightcolor",    C["accent"])
        kw.setdefault("selectbackground",  C["accent2"])
        kw.setdefault("wrap",              "none")
        super().__init__(master, **kw)

class StyledButton(tk.Label):
    def __init__(self, master, text="", command=None, bg=None, fg=None, **kw):
        self._bg  = bg or C["accent"]
        self._fg  = fg or "#ffffff"
        self._cmd = command
        super().__init__(
            master, text=text, bg=self._bg, fg=self._fg,
            font=FONT_UI, cursor="hand2",
            padx=10, pady=5, relief="flat", **kw
        )
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>",    self._enter)
        self.bind("<Leave>",    self._leave)

    def _click(self, _=None):
        if self._cmd and str(self.cget("state")) != "disabled":
            self._cmd()

    def _enter(self, _=None):
        if str(self.cget("state")) != "disabled":
            self.config(bg=_brighten(self._bg))

    def _leave(self, _=None):
        self.config(bg=self._bg)

    def disable(self):
        self.config(state="disabled", bg=C["muted"], fg="#888", cursor="arrow")

    def enable(self):
        self.config(state="normal", bg=self._bg, fg=self._fg, cursor="hand2")

def _brighten(h: str) -> str:
    r, g, b = int(h[1:3],16), int(h[3:5],16), int(h[5:7],16)
    return f"#{min(255,r+25):02x}{min(255,g+25):02x}{min(255,b+25):02x}"

def _card(parent, title, fill="x", expand=False, pady_bottom=10):
    outer = tk.Frame(parent, bg=C["border"], pady=1, padx=1)
    outer.pack(fill=fill, expand=expand, pady=(0, 10))
    inner = tk.Frame(outer, bg=C["card"])
    inner.pack(fill="both", expand=True)
    tk.Label(inner, text=title, font=(FONT_UI[0], 8, "bold"),
             bg=C["card"], fg=C["muted"], anchor="w",
             padx=10, pady=6).pack(fill="x")
    body = tk.Frame(inner, bg=C["card"], padx=10, pady=0)
    body.pack(fill="both", expand=True, pady=(0, pady_bottom))
    return body

def _labeled_entry(parent, label, show=None):
    f = tk.Frame(parent, bg=C["card"])
    f.pack(fill="x", pady=2)
    tk.Label(f, text=label, font=FONT_SMALL, bg=C["card"],
             fg=C["muted"], width=9, anchor="w").pack(side="left")
    kw = {}
    if show:
        kw["show"] = show
    e = StyledEntry(f, **kw)
    e.pack(side="left", fill="x", expand=True)
    return e

def _file_row(parent, label, bg=None):
    bg = bg or C["card"]
    f = tk.Frame(parent, bg=bg)
    f.pack(fill="x", pady=2)
    tk.Label(f, text=label, font=FONT_SMALL, bg=bg,
             fg=C["muted"], width=9, anchor="w").pack(side="left")
    e = StyledEntry(f)
    e.pack(side="left", fill="x", expand=True)
    btn = tk.Label(f, text="…", bg=C["border"], fg=C["muted"],
                   font=FONT_SMALL, padx=5, pady=3, cursor="hand2")
    btn.pack(side="left", padx=(2, 0))
    btn.bind("<Button-1>", lambda _, e=e: _browse_file(e))
    return e

def _browse_file(entry):
    path = filedialog.askopenfilename(
        title="ファイルを選択",
        filetypes=[("証明書 / 鍵", "*.pem *.key *.crt *.cer *.pub *.ppk"),
                   ("全ファイル", "*.*")]
    )
    if path:
        entry.delete(0, "end")
        entry.insert(0, path)

def _icon_btn(parent, text, cmd, bg=None, fg=None, padx=6, pady=3):
    bg = bg or C["surface"]
    fg_orig = fg or C["muted"]
    b = tk.Label(parent, text=text, bg=bg, fg=fg_orig, font=FONT_SMALL,
                 padx=padx, pady=pady, cursor="hand2", relief="flat")
    b.bind("<Button-1>", lambda _: cmd())
    b.bind("<Enter>", lambda _: b.config(fg=C["text"]))
    b.bind("<Leave>", lambda _: b.config(fg=fg_orig))
    return b


# ── SSH サブパネルビルダー ────────────────────────────────────
def _build_ssh_subpanel(parent_frame, bg, accent_color):
    """
    SSHサーバー or ジャンプサーバー共通の入力フォームを作る。
    返す dict: host_e, port_e, user_e, auth_mode (StringVar),
               pkey_e, passphrase_e, password_e,
               key_frame, pass_frame, refresh_auth (callable)
    """
    W = {}

    def _row(lbl, show=None):
        f = tk.Frame(parent_frame, bg=bg)
        f.pack(fill="x", pady=2)
        tk.Label(f, text=lbl, font=FONT_SMALL, bg=bg,
                 fg=C["muted"], width=9, anchor="w").pack(side="left")
        kw = {}
        if show: kw["show"] = show
        e = StyledEntry(f, **kw)
        e.pack(side="left", fill="x", expand=True)
        return e

    def _frow(lbl):
        f = tk.Frame(parent_frame, bg=bg)
        f.pack(fill="x", pady=2)
        tk.Label(f, text=lbl, font=FONT_SMALL, bg=bg,
                 fg=C["muted"], width=9, anchor="w").pack(side="left")
        e = StyledEntry(f)
        e.pack(side="left", fill="x", expand=True)
        btn = tk.Label(f, text="…", bg=C["border"], fg=C["muted"],
                       font=FONT_SMALL, padx=5, pady=3, cursor="hand2")
        btn.pack(side="left", padx=(2, 0))
        btn.bind("<Button-1>", lambda _, e=e: _browse_file(e))
        return e

    W["host_e"] = _row("Host")
    W["port_e"] = _row("Port")
    W["user_e"] = _row("User")

    # 認証方式
    tk.Label(parent_frame, text="認証", font=(FONT_SMALL[0], 8, "bold"),
             bg=bg, fg=accent_color, anchor="w").pack(fill="x", pady=(6, 2))

    auth_bar = tk.Frame(parent_frame, bg=bg)
    auth_bar.pack(fill="x", pady=(0, 4))
    W["auth_mode"] = tk.StringVar(value="key")

    key_frame  = tk.Frame(parent_frame, bg=bg)
    pass_frame = tk.Frame(parent_frame, bg=bg)
    W["key_frame"]  = key_frame
    W["pass_frame"] = pass_frame

    # key フレーム内
    W["pkey_e"]       = _ssh_file_row_in(key_frame, "秘密鍵", bg)
    W["passphrase_e"] = _ssh_row_in(key_frame, "Passphrase", bg, show="●")

    # pass フレーム内
    W["password_e"] = _ssh_row_in(pass_frame, "Password", bg, show="●")

    btn_key  = tk.Label(auth_bar, text="🔑 秘密鍵",    font=FONT_SMALL,
                        padx=8, pady=3, cursor="hand2", relief="flat")
    btn_pass = tk.Label(auth_bar, text="🔒 パスワード", font=FONT_SMALL,
                        padx=8, pady=3, cursor="hand2", relief="flat")
    btn_key.pack(side="left", padx=(0, 2))
    btn_pass.pack(side="left")

    def refresh():
        mode = W["auth_mode"].get()
        if mode == "key":
            pass_frame.pack_forget()
            key_frame.pack(fill="x")
            btn_key.config(bg=accent_color, fg="#000")
            btn_pass.config(bg=C["border"], fg=C["muted"])
        else:
            key_frame.pack_forget()
            pass_frame.pack(fill="x")
            btn_key.config(bg=C["border"], fg=C["muted"])
            btn_pass.config(bg=accent_color, fg="#000")

    def _set_key():
        W["auth_mode"].set("key"); refresh()
    def _set_pass():
        W["auth_mode"].set("password"); refresh()

    btn_key.bind("<Button-1>",  lambda _: _set_key())
    btn_pass.bind("<Button-1>", lambda _: _set_pass())
    W["refresh_auth"] = refresh
    refresh()
    return W


def _ssh_row_in(parent, label, bg, show=None):
    f = tk.Frame(parent, bg=bg)
    f.pack(fill="x", pady=2)
    tk.Label(f, text=label, font=FONT_SMALL, bg=bg,
             fg=C["muted"], width=9, anchor="w").pack(side="left")
    kw = {}
    if show: kw["show"] = show
    e = StyledEntry(f, **kw)
    e.pack(side="left", fill="x", expand=True)
    return e

def _ssh_file_row_in(parent, label, bg):
    f = tk.Frame(parent, bg=bg)
    f.pack(fill="x", pady=2)
    tk.Label(f, text=label, font=FONT_SMALL, bg=bg,
             fg=C["muted"], width=9, anchor="w").pack(side="left")
    e = StyledEntry(f)
    e.pack(side="left", fill="x", expand=True)
    btn = tk.Label(f, text="…", bg=C["border"], fg=C["muted"],
                   font=FONT_SMALL, padx=5, pady=3, cursor="hand2")
    btn.pack(side="left", padx=(2, 0))
    btn.bind("<Button-1>", lambda _, e=e: _browse_file(e))
    return e


# ── paramiko ヘルパー ─────────────────────────────────────────
def _make_paramiko_client(host, port, user, auth_mode,
                           pkey_path=None, passphrase=None, password=None,
                           proxy_channel=None):
    """
    paramiko SSHClient を作って接続し返す。
    proxy_channel が渡された場合はそれをソケット代わりに使う（多段SSH用）。
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kw = dict(username=user, timeout=15)
    if proxy_channel:
        kw["sock"] = proxy_channel
    if auth_mode == "key":
        if pkey_path:
            kw["key_filename"] = pkey_path
        if passphrase:
            kw["passphrase"] = passphrase
    else:
        kw["password"] = password or ""
    client.connect(host, port=port, **kw)
    return client


# ══════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("S.T.E.P. v2.2")
        self.configure(bg=C["bg"])
        self.resizable(True, True)
        self.minsize(1100, 720)
        self.geometry("1260x840")

        if sys.platform == "win32":
            try:
                from ctypes import windll
                windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass

        self._conn              = None
        self._tunnel            = None     # SSHTunnelForwarder
        self._jump_client       = None     # ジャンプサーバー paramiko.SSHClient
        self._configs: dict     = load_configs()
        self._scenarios: list   = load_scenarios()
        self._sel_idx: int      = 0
        self._tables: list      = []
        self._var_rows: list    = []

        self._build_ui()
        self._refresh_profiles()
        self._render_scenarios()
        if self._scenarios:
            self._select_scenario(0)
        # 保存済み変数を復元
        for item in load_variables():
            self._add_var_row(item.get("key", ""), item.get("val", ""))

    # ══ UI ═══════════════════════════════════════════════════
    def _build_ui(self):
        hdr = tk.Frame(self, bg=C["surface"], pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⬡  S.T.E.P.  ─  Scenario-based Tool for Extraction Process",
                 font=FONT_TITLE, bg=C["surface"], fg=C["text"]).pack(side="left", padx=16)
        self._conn_badge = tk.Label(hdr, text="● 未接続", font=FONT_SMALL,
                                    bg=C["surface"], fg=C["muted"])
        self._conn_badge.pack(side="right", padx=16)

        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=14, pady=12)

        col_left = tk.Frame(body, bg=C["bg"], width=260)
        col_left.pack(side="left", fill="y", padx=(0, 10))
        col_left.pack_propagate(False)

        col_mid = tk.Frame(body, bg=C["bg"], width=275)
        col_mid.pack(side="left", fill="y", padx=(0, 10))
        col_mid.pack_propagate(False)

        col_right = tk.Frame(body, bg=C["bg"])
        col_right.pack(side="left", fill="both", expand=True)

        self._build_connection_panel(col_left)
        self._build_table_panel(col_left)
        self._build_scenario_panel(col_mid)
        self._build_variable_panel(col_mid)
        self._build_sql_panel(col_right)
        self._build_log_panel(col_right)
        self._build_export_bar()

    # ── 接続パネル ─────────────────────────────────────────────
    def _build_connection_panel(self, parent):
        outer = tk.Frame(parent, bg=C["border"], pady=1, padx=1)
        outer.pack(fill="both", expand=True, pady=(0, 10))
        card = tk.Frame(outer, bg=C["card"])
        card.pack(fill="both", expand=True)

        # ─ ヘッダー行（タイトル + フロー表示）
        hdr = tk.Frame(card, bg=C["card"])
        hdr.pack(fill="x", padx=10, pady=(6, 0))
        tk.Label(hdr, text="CONNECTION", font=(FONT_UI[0], 8, "bold"),
                 bg=C["card"], fg=C["muted"]).pack(side="left")
        self._flow_label = tk.Label(hdr, text="", font=FONT_SMALL,
                                    bg=C["card"], fg=C["muted"], anchor="e")
        self._flow_label.pack(side="right")

        # ─ プロファイル行
        pf = tk.Frame(card, bg=C["card"], padx=10)
        pf.pack(fill="x", pady=(4, 2))
        tk.Label(pf, text="Profile", font=FONT_SMALL, bg=C["card"],
                 fg=C["muted"], width=9, anchor="w").pack(side="left")
        self._profile_var = tk.StringVar()
        self._profile_cb  = ttk.Combobox(pf, textvariable=self._profile_var,
                                          state="readonly", font=FONT_MONO, width=14)
        self._profile_cb.pack(side="left", fill="x", expand=True)
        self._profile_cb.bind("<<ComboboxSelected>>", self._load_profile)

        # ─ タブバー
        tab_bar = tk.Frame(card, bg=C["card"], padx=10, pady=4)
        tab_bar.pack(fill="x")

        self._tab_frames: dict = {}
        self._tab_btns:   dict = {}
        tab_content = tk.Frame(card, bg=C["card"], padx=10, pady=4)
        tab_content.pack(fill="both", expand=True)

        TABS = [
            ("mysql", "MySQL",    C["accent"]),
            ("ssh",   "SSH",      C["ssh"]),
            ("jump",  "Jump",     C["jump"]),
        ]

        def _switch_tab(name):
            for n, f in self._tab_frames.items():
                f.pack_forget()
            self._tab_frames[name].pack(fill="both", expand=True)
            for n, b in self._tab_btns.items():
                _, _, accent = next(t for t in TABS if t[0] == n)
                if n == name:
                    b.config(bg=accent, fg="#000" if accent != C["muted"] else C["text"])
                else:
                    b.config(bg=C["border"], fg=C["muted"])

        for name, label, accent in TABS:
            frame = tk.Frame(tab_content, bg=C["card"])
            self._tab_frames[name] = frame
            btn = tk.Label(tab_bar, text=label, font=FONT_SMALL,
                           padx=12, pady=4, cursor="hand2", relief="flat",
                           bg=C["border"], fg=C["muted"])
            btn.pack(side="left", padx=(0, 3))
            btn.bind("<Button-1>", lambda _, n=name: _switch_tab(n))
            self._tab_btns[name] = btn

        self._switch_tab = _switch_tab

        # ════ MySQL タブ ══════════════════════════════════════
        mt = self._tab_frames["mysql"]

        self._host_e = _labeled_entry(mt, "Host")
        self._port_e = _labeled_entry(mt, "Port")
        self._user_e = _labeled_entry(mt, "User")
        self._pass_e = _labeled_entry(mt, "Password", show="●")
        self._db_e   = _labeled_entry(mt, "Database")
        self._host_e.insert(0, "127.0.0.1")
        self._port_e.insert(0, "3306")

        tk.Label(mt, text="SSL (任意)", font=(FONT_SMALL[0], 8, "bold"),
                 bg=C["card"], fg=C["muted"], anchor="w").pack(fill="x", pady=(8, 2))
        self._ssl_ca_e   = _file_row(mt, "CA Cert")
        self._ssl_cert_e = _file_row(mt, "Cert")
        self._ssl_key_e  = _file_row(mt, "Key File")

        # ════ SSH タブ ════════════════════════════════════════
        st = self._tab_frames["ssh"]

        self._ssh_enabled = tk.BooleanVar(value=False)
        ssh_chk_row = tk.Frame(st, bg=C["card"])
        ssh_chk_row.pack(fill="x", pady=(0, 6))
        tk.Checkbutton(
            ssh_chk_row, text="SSH トンネルを使用",
            variable=self._ssh_enabled, command=self._update_flow_label,
            bg=C["card"], fg=C["ssh"],
            selectcolor=C["input_bg"], activebackground=C["card"],
            activeforeground=C["ssh"],
            font=(FONT_SMALL[0], 8, "bold"), cursor="hand2",
        ).pack(side="left")

        tk.Label(st, text="SSHサーバー", font=(FONT_SMALL[0], 8, "bold"),
                 bg=C["card"], fg=C["ssh"], anchor="w").pack(fill="x", pady=(0, 2))

        self._ssh = _build_ssh_subpanel(st, C["card"], C["ssh"])
        self._ssh["host_e"].insert(0, "bastion.example.com")
        self._ssh["port_e"].insert(0, "22")

        # ════ ジャンプ タブ ═══════════════════════════════════
        jt = self._tab_frames["jump"]

        self._jump_enabled = tk.BooleanVar(value=False)
        jump_chk_row = tk.Frame(jt, bg=C["card"])
        jump_chk_row.pack(fill="x", pady=(0, 6))
        tk.Checkbutton(
            jump_chk_row, text="ジャンプサーバーを使用",
            variable=self._jump_enabled, command=self._update_flow_label,
            bg=C["card"], fg=C["jump"],
            selectcolor=C["input_bg"], activebackground=C["card"],
            activeforeground=C["jump"],
            font=(FONT_SMALL[0], 8, "bold"), cursor="hand2",
        ).pack(side="left")

        tk.Label(jt, text="ジャンプサーバー（踏み台）",
                 font=(FONT_SMALL[0], 8, "bold"),
                 bg=C["card"], fg=C["jump"], anchor="w").pack(fill="x", pady=(0, 2))

        self._jump = _build_ssh_subpanel(jt, C["card"], C["jump"])
        self._jump["host_e"].insert(0, "jump.example.com")
        self._jump["port_e"].insert(0, "22")

        # ─ 接続ボタン行
        bf = tk.Frame(card, bg=C["card"], padx=10)
        bf.pack(fill="x", pady=(6, 8))
        StyledButton(bf, "接続", self._connect, bg=C["accent"]).pack(side="left", fill="x", expand=True)
        tk.Frame(bf, bg=C["card"], width=3).pack(side="left")
        StyledButton(bf, "切断", self._disconnect, bg=C["muted"]).pack(side="left", fill="x", expand=True)
        tk.Frame(bf, bg=C["card"], width=3).pack(side="left")
        StyledButton(bf, "保存", self._save_profile, bg=C["accent2"]).pack(side="left", fill="x", expand=True)
        tk.Frame(bf, bg=C["card"], width=3).pack(side="left")
        StyledButton(bf, "削除", self._delete_profile, bg=C["danger"]).pack(side="left", fill="x", expand=True)

        # 初期表示
        _switch_tab("mysql")
        self._update_flow_label()

    def _update_flow_label(self):
        use_ssh  = self._ssh_enabled.get()
        use_jump = self._jump_enabled.get()
        if use_jump and use_ssh:
            txt = "PC → Jump → SSH → MySQL"
            fg  = C["jump"]
        elif use_ssh:
            txt = "PC → SSH → MySQL"
            fg  = C["ssh"]
        else:
            txt = "PC → MySQL"
            fg  = C["muted"]
        self._flow_label.config(text=txt, fg=fg)

    # ── テーブルパネル ─────────────────────────────────────────
    def _build_table_panel(self, parent):
        body = _card(parent, "TABLES", fill="both", expand=True, pady_bottom=4)

        sf = tk.Frame(body, bg=C["card"])
        sf.pack(fill="x", pady=(0, 4))
        tk.Label(sf, text="🔍", bg=C["card"], fg=C["muted"],
                 font=(FONT_UI[0], 10)).pack(side="left")
        self._table_search = StyledEntry(sf)
        self._table_search.pack(side="left", fill="x", expand=True, padx=4)
        self._table_search.bind("<KeyRelease>", self._filter_tables)

        lf = tk.Frame(body, bg=C["card"])
        lf.pack(fill="both", expand=True)
        sb = tk.Scrollbar(lf, bg=C["border"], troughcolor=C["card"],
                          relief="flat", width=6)
        sb.pack(side="right", fill="y")
        self._table_lb = tk.Listbox(
            lf, yscrollcommand=sb.set,
            bg=C["input_bg"], fg=C["text"],
            selectbackground=C["accent2"], selectforeground="#fff",
            font=FONT_MONO, relief="flat", highlightthickness=0,
            activestyle="none",
        )
        self._table_lb.pack(side="left", fill="both", expand=True)
        sb.config(command=self._table_lb.yview)
        self._table_lb.bind("<<ListboxSelect>>", self._on_table_select)

    # ── シナリオパネル ─────────────────────────────────────────
    def _build_scenario_panel(self, parent):
        body = _card(parent, "SCENARIOS", pady_bottom=4)

        tb = tk.Frame(body, bg=C["card"])
        tb.pack(fill="x", pady=(0, 4))
        for icon, cmd in [("＋", self._add_scenario),
                           ("✎", self._rename_scenario),
                           ("⊕", self._duplicate_scenario),
                           ("✕", self._delete_scenario)]:
            _icon_btn(tb, icon, cmd, bg=C["border"],
                      fg=C["muted"], padx=8, pady=4).pack(side="left", padx=(0, 3))

        # 書き出し・読み込みボタン（右寄せ）
        _icon_btn(tb, "↑ 書き出し", self._export_preset,
                  bg=C["accent2"], fg=C["text"], padx=8, pady=4).pack(side="right", padx=(3, 0))
        _icon_btn(tb, "↓ 読み込み", self._import_preset,
                  bg=C["surface"], fg=C["text"], padx=8, pady=4).pack(side="right", padx=(3, 0))

        lf = tk.Frame(body, bg=C["card"])
        lf.pack(fill="both", expand=True)
        sb = tk.Scrollbar(lf, bg=C["border"], troughcolor=C["card"],
                          relief="flat", width=6)
        sb.pack(side="right", fill="y")
        self._scenario_lb = tk.Listbox(
            lf, yscrollcommand=sb.set,
            bg=C["input_bg"], fg=C["text"],
            selectbackground=C["sel_bg"], selectforeground=C["accent"],
            font=FONT_MONO, relief="flat", highlightthickness=0,
            activestyle="none", height=8,
        )
        self._scenario_lb.pack(side="left", fill="both", expand=True)
        sb.config(command=self._scenario_lb.yview)
        self._scenario_lb.bind("<<ListboxSelect>>", self._on_scenario_click)

    # ── 変数パネル ─────────────────────────────────────────────
    def _build_variable_panel(self, parent):
        body = _card(parent, "VARIABLES  ─  {変数名} でSQL内に展開",
                     fill="both", expand=True, pady_bottom=6)

        tb = tk.Frame(body, bg=C["card"])
        tb.pack(fill="x", pady=(0, 4))
        _icon_btn(tb, "＋ 行を追加", self._add_var_row,
                  bg=C["border"], fg=C["muted"]).pack(side="left")

        canvas = tk.Canvas(body, bg=C["card"], highlightthickness=0)
        sb = tk.Scrollbar(body, orient="vertical", command=canvas.yview,
                          bg=C["border"], troughcolor=C["card"],
                          relief="flat", width=6)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._var_frame = tk.Frame(canvas, bg=C["card"])
        vid = canvas.create_window((0, 0), window=self._var_frame, anchor="nw")
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(vid, width=e.width))
        self._var_frame.bind("<Configure>",
                             lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    def _add_var_row(self, key="", val=""):
        f = tk.Frame(self._var_frame, bg=C["card"])
        f.pack(fill="x", pady=2)
        k_var = tk.StringVar(value=key)
        v_var = tk.StringVar(value=val)
        tk.Label(f, text="{", font=FONT_MONO, bg=C["card"],
                 fg=C["warning"], padx=2).pack(side="left")
        StyledEntry(f, textvariable=k_var, width=12).pack(side="left")
        tk.Label(f, text="}=", font=FONT_MONO, bg=C["card"],
                 fg=C["warning"], padx=2).pack(side="left")
        StyledEntry(f, textvariable=v_var).pack(side="left", fill="x", expand=True)
        row = (k_var, v_var, f)
        self._var_rows.append(row)
        dl = tk.Label(f, text=" ✕ ", bg=C["card"], fg=C["danger"],
                      font=FONT_SMALL, cursor="hand2")
        dl.pack(side="right")
        dl.bind("<Button-1>", lambda _, r=row: self._remove_var_row(r))
        # 編集のたびに自動保存
        k_var.trace_add("write", lambda *_: self._save_variables())
        v_var.trace_add("write", lambda *_: self._save_variables())

    def _remove_var_row(self, row):
        _, _, f = row
        f.destroy()
        self._var_rows = [r for r in self._var_rows if r is not row]
        self._save_variables()

    def _save_variables(self):
        save_variables([{"key": k.get(), "val": v.get()}
                        for k, v, _ in self._var_rows])

    def _get_variables(self) -> dict:
        return {k.get().strip(): v.get()
                for k, v, _ in self._var_rows if k.get().strip()}

    # ── SQL エディタ ────────────────────────────────────────────
    def _build_sql_panel(self, parent):
        body = _card(parent, "SQL EDITOR  ─  選択中シナリオ",
                     fill="both", expand=True, pady_bottom=6)
        self._sql_title = tk.Label(body, text="", font=(FONT_UI[0], 9, "bold"),
                                   bg=C["card"], fg=C["accent"], anchor="w")
        self._sql_title.pack(fill="x", pady=(0, 4))

        tf = tk.Frame(body, bg=C["card"])
        tf.pack(fill="both", expand=True)
        xsb = tk.Scrollbar(tf, orient="horizontal", bg=C["border"],
                           troughcolor=C["card"], relief="flat")
        ysb = tk.Scrollbar(tf, bg=C["border"], troughcolor=C["card"],
                           relief="flat", width=6)
        self._sql_text = StyledText(tf, xscrollcommand=xsb.set,
                                    yscrollcommand=ysb.set)
        xsb.config(command=self._sql_text.xview)
        ysb.config(command=self._sql_text.yview)
        ysb.pack(side="right", fill="y")
        xsb.pack(side="bottom", fill="x")
        self._sql_text.pack(side="left", fill="both", expand=True)
        self._sql_text.bind("<KeyRelease>", self._on_sql_edit)

    # ── ログ ────────────────────────────────────────────────────
    def _build_log_panel(self, parent):
        body = _card(parent, "LOG", fill="x", pady_bottom=4)
        lf = tk.Frame(body, bg=C["card"])
        lf.pack(fill="both", expand=True)
        sb = tk.Scrollbar(lf, bg=C["border"], troughcolor=C["card"],
                          relief="flat", width=6)
        sb.pack(side="right", fill="y")
        self._log_text = StyledText(lf, height=5, state="disabled",
                                    yscrollcommand=sb.set)
        self._log_text.pack(side="left", fill="both", expand=True)
        sb.config(command=self._log_text.yview)
        for tag, fg in [("ok",   C["success"]), ("err",  C["danger"]),
                         ("warn", C["warning"]), ("info", C["muted"]),
                         ("ssh",  C["ssh"]),     ("jump", C["jump"]),
                         ("hdr",  C["accent"])]:
            self._log_text.tag_config(tag, foreground=fg)

    # ── エクスポートバー ────────────────────────────────────────
    def _build_export_bar(self):
        bar = tk.Frame(self, bg=C["surface"], pady=8, padx=14)
        bar.pack(fill="x", side="bottom")

        tk.Label(bar, text="エンコーディング", font=FONT_SMALL,
                 bg=C["surface"], fg=C["muted"]).pack(side="left")
        self._enc_var = tk.StringVar(value="utf-8-sig")
        for lbl, val in [("UTF-8 BOM", "utf-8-sig"), ("UTF-8", "utf-8"), ("Shift-JIS", "shift_jis")]:
            tk.Radiobutton(bar, text=lbl, variable=self._enc_var, value=val,
                           bg=C["surface"], fg=C["text"],
                           selectcolor=C["accent2"], activebackground=C["surface"],
                           font=FONT_SMALL).pack(side="left", padx=5)

        tk.Frame(bar, bg=C["border"], width=1).pack(side="left", fill="y", padx=12)

        tk.Label(bar, text="区切り", font=FONT_SMALL,
                 bg=C["surface"], fg=C["muted"]).pack(side="left")
        self._delim_var = tk.StringVar(value=",")
        for lbl, val in [("カンマ", ","), ("タブ", "\t"), (";", ";")]:
            tk.Radiobutton(bar, text=lbl, variable=self._delim_var, value=val,
                           bg=C["surface"], fg=C["text"],
                           selectcolor=C["accent2"], activebackground=C["surface"],
                           font=FONT_SMALL).pack(side="left", padx=4)

        self._run_all_btn = StyledButton(bar, "▶▶  全シナリオ実行",
                                          self._run_all, bg=C["success"], fg="#111")
        self._run_all_btn.pack(side="right", padx=(6, 0))
        self._run_one_btn = StyledButton(bar, "▶  選択を実行",
                                          self._run_selected, bg=C["accent"])
        self._run_one_btn.pack(side="right", padx=(6, 0))

    # ══ 接続処理 ══════════════════════════════════════════════
    def _connect(self):
        if mysql is None:
            messagebox.showerror("依存パッケージ不足",
                'pip install mysql-connector-python "sshtunnel>=0.4" "paramiko>=2.11,<3"')
            return

        use_ssh  = self._ssh_enabled.get()
        use_jump = self._jump_enabled.get()

        if use_ssh and SSHTunnelForwarder is None:
            messagebox.showerror("sshtunnel 未インストール",
                'pip install "sshtunnel>=0.4" "paramiko>=2.11,<3"')
            return

        # 読み取り（UI スレッド）
        mysql_host = self._host_e.get().strip()
        mysql_port = int(self._port_e.get().strip() or "3306")
        mysql_user = self._user_e.get().strip()
        mysql_pwd  = self._pass_e.get()
        mysql_db   = self._db_e.get().strip()
        ssl_ca     = self._ssl_ca_e.get().strip()
        ssl_cert   = self._ssl_cert_e.get().strip()
        ssl_key    = self._ssl_key_e.get().strip()

        if not mysql_host or not mysql_user:
            self._log("MySQL Host と User は必須です", "err"); return

        ssh = {k: w.get() if hasattr(w, "get") else w
               for k, w in self._ssh.items()
               if k not in ("key_frame", "pass_frame", "refresh_auth")}

        jump = {k: w.get() if hasattr(w, "get") else w
                for k, w in self._jump.items()
                if k not in ("key_frame", "pass_frame", "refresh_auth")}

        if use_jump and use_ssh:
            self._log(f"接続フロー: PC → ジャンプ({jump['host_e']}) → SSH({ssh['host_e']}) → MySQL", "jump")
        elif use_ssh:
            self._log(f"接続フロー: PC → SSH({ssh['host_e']}) → MySQL", "ssh")
        else:
            self._log(f"接続中: {mysql_user}@{mysql_host}:{mysql_port}", "info")

        def _do():
            jump_client  = None
            local_port   = mysql_port

            try:
                # ── STEP 1: ジャンプサーバー経由で SSH サーバーへ ──
                proxy_chan = None
                if use_ssh and use_jump:
                    j_host = jump["host_e"].strip()
                    j_port = int(jump["port_e"].strip() or "22")
                    j_user = jump["user_e"].strip()
                    if not j_host or not j_user:
                        raise ValueError("ジャンプサーバーの Host / User は必須です")

                    self.after(0, self._log,
                               f"ジャンプサーバーに接続中: {j_user}@{j_host}:{j_port}", "jump")
                    jump_client = _make_paramiko_client(
                        j_host, j_port, j_user,
                        auth_mode   = jump["auth_mode"].strip(),
                        pkey_path   = jump["pkey_e"].strip() or None,
                        passphrase  = jump["passphrase_e"].strip() or None,
                        password    = jump["password_e"].strip() or None,
                    )
                    self._jump_client = jump_client
                    self.after(0, self._log, "ジャンプサーバー接続完了", "jump")

                    # ジャンプサーバー → SSH サーバーへのチャンネル
                    ssh_host = ssh["host_e"].strip()
                    ssh_port_n = int(ssh["port_e"].strip() or "22")
                    proxy_chan = jump_client.get_transport().open_channel(
                        "direct-tcpip",
                        (ssh_host, ssh_port_n),
                        ("", 0),
                    )

                # ── STEP 2: SSH トンネル開通（MySQL フォワード）──
                if use_ssh:
                    ssh_host   = ssh["host_e"].strip()
                    ssh_port_n = int(ssh["port_e"].strip() or "22")
                    ssh_user   = ssh["user_e"].strip()
                    if not ssh_host or not ssh_user:
                        raise ValueError("SSH サーバーの Host / User は必須です")

                    self.after(0, self._log,
                               f"SSH トンネル構築中: {ssh_user}@{ssh_host}:{ssh_port_n}", "ssh")

                    tunnel_kw = dict(
                        ssh_username=ssh_user,
                        remote_bind_address=(mysql_host, mysql_port),
                    )
                    if proxy_chan:
                        tunnel_kw["ssh_proxy"] = proxy_chan

                    if ssh["auth_mode"].strip() == "key":
                        pkey = ssh["pkey_e"].strip() or None
                        pp   = ssh["passphrase_e"].strip() or None
                        tunnel_kw["ssh_pkey"] = pkey
                        if pp:
                            tunnel_kw["ssh_private_key_password"] = pp
                    else:
                        tunnel_kw["ssh_password"] = ssh["password_e"].strip()

                    tunnel = SSHTunnelForwarder(
                        (ssh_host, ssh_port_n), **tunnel_kw
                    )
                    tunnel.start()
                    self._tunnel = tunnel
                    local_port   = tunnel.local_bind_port
                    self.after(0, self._log,
                               f"SSH トンネル確立 → localhost:{local_port}", "ssh")

                # ── STEP 3: MySQL 接続 ──────────────────────────
                kw = dict(
                    host="127.0.0.1" if use_ssh else mysql_host,
                    port=local_port,
                    user=mysql_user,
                    password=mysql_pwd,
                    database=mysql_db or None,
                    connection_timeout=10,
                )
                if ssl_ca or ssl_cert or ssl_key:
                    kw["ssl_ca"]          = ssl_ca   or None
                    kw["ssl_cert"]        = ssl_cert or None
                    kw["ssl_key"]         = ssl_key  or None
                    kw["ssl_verify_cert"] = bool(ssl_ca)

                self._conn = mysql.connector.connect(**kw)
                self.after(0, self._on_connected, mysql_host, mysql_db,
                           use_ssh, use_jump)

            except Exception as e:
                self._cleanup_connections()
                self.after(0, self._on_connect_error, str(e))

        threading.Thread(target=_do, daemon=True).start()

    def _cleanup_connections(self):
        if self._conn:
            try: self._conn.close()
            except Exception: pass
            self._conn = None
        if self._tunnel:
            try: self._tunnel.stop()
            except Exception: pass
            self._tunnel = None
        if self._jump_client:
            try: self._jump_client.close()
            except Exception: pass
            self._jump_client = None

    def _on_connected(self, host, db, via_ssh, via_jump):
        parts = [host, db or "─"]
        tags = []
        if via_jump: tags.append("Jump")
        if via_ssh:  tags.append("SSH")
        suffix = f"  [{'+'.join(tags)}]" if tags else ""
        self._conn_badge.config(
            text=f"● {host}/{db or '─'}{suffix}",
            fg=C["jump"] if via_jump else C["ssh"] if via_ssh else C["success"])
        self._log("MySQL 接続成功 ✓", "ok")
        self._load_tables()

    def _on_connect_error(self, msg):
        self._conn_badge.config(text="● 接続失敗", fg=C["danger"])
        self._log(f"接続エラー: {msg}", "err")

    def _disconnect(self):
        self._cleanup_connections()
        self._conn_badge.config(text="● 未接続", fg=C["muted"])
        self._table_lb.delete(0, "end")
        self._tables = []
        self._log("切断しました", "warn")

    # ══ テーブル ══════════════════════════════════════════════
    def _load_tables(self):
        if not self._conn: return
        try:
            cur = self._conn.cursor()
            cur.execute("SHOW TABLES")
            self._tables = [r[0] for r in cur.fetchall()]
            cur.close()
            self._render_tables(self._tables)
            self._log(f"{len(self._tables)} テーブル取得", "ok")
        except Exception as e:
            self._log(f"テーブル取得失敗: {e}", "err")

    def _render_tables(self, tables):
        self._table_lb.delete(0, "end")
        for t in tables:
            self._table_lb.insert("end", t)

    def _filter_tables(self, _=None):
        q = self._table_search.get().lower()
        self._render_tables([t for t in self._tables if q in t.lower()])

    def _on_table_select(self, _=None):
        sel = self._table_lb.curselection()
        if not sel: return
        table = self._table_lb.get(sel[0])
        self._sql_text.delete("1.0", "end")
        self._sql_text.insert("1.0", f"SELECT *\nFROM `{table}`\nLIMIT 1000;")
        self._save_current_sql()

    # ══ シナリオ管理 ══════════════════════════════════════════
    def _render_scenarios(self):
        self._scenario_lb.delete(0, "end")
        for i, s in enumerate(self._scenarios):
            self._scenario_lb.insert("end", f"  {i+1:02d}. {s['name']}")

    def _select_scenario(self, idx: int):
        self._sel_idx = idx
        self._scenario_lb.selection_clear(0, "end")
        self._scenario_lb.selection_set(idx)
        self._scenario_lb.see(idx)
        sc = self._scenarios[idx]
        self._sql_title.config(text=sc["name"])
        self._sql_text.delete("1.0", "end")
        self._sql_text.insert("1.0", sc.get("sql", ""))

    def _on_scenario_click(self, _=None):
        sel = self._scenario_lb.curselection()
        if not sel: return
        self._save_current_sql()
        self._select_scenario(sel[0])

    def _on_sql_edit(self, _=None):
        if 0 <= self._sel_idx < len(self._scenarios):
            self._scenarios[self._sel_idx]["sql"] = self._sql_text.get("1.0", "end-1c")

    def _save_current_sql(self):
        if 0 <= self._sel_idx < len(self._scenarios):
            self._scenarios[self._sel_idx]["sql"] = self._sql_text.get("1.0", "end-1c")
        save_scenarios(self._scenarios)

    def _add_scenario(self):
        name = simpledialog.askstring("シナリオ追加", "シナリオ名:")
        if not name: return
        self._scenarios.append({"name": name, "sql": "SELECT * FROM your_table LIMIT 1000;"})
        save_scenarios(self._scenarios)
        self._render_scenarios()
        self._select_scenario(len(self._scenarios) - 1)

    def _rename_scenario(self):
        if not self._scenarios: return
        name = simpledialog.askstring("名前変更", "新しい名前:",
                                       initialvalue=self._scenarios[self._sel_idx]["name"])
        if not name: return
        self._scenarios[self._sel_idx]["name"] = name
        save_scenarios(self._scenarios)
        self._render_scenarios()
        self._select_scenario(self._sel_idx)

    def _duplicate_scenario(self):
        if not self._scenarios: return
        import copy
        sc = copy.deepcopy(self._scenarios[self._sel_idx])
        sc["name"] += " (コピー)"
        self._scenarios.insert(self._sel_idx + 1, sc)
        save_scenarios(self._scenarios)
        self._render_scenarios()
        self._select_scenario(self._sel_idx + 1)

    def _delete_scenario(self):
        if len(self._scenarios) <= 1:
            messagebox.showwarning("削除不可", "最低1つのシナリオが必要です"); return
        name = self._scenarios[self._sel_idx]["name"]
        if not messagebox.askyesno("削除確認", f"「{name}」を削除しますか？"): return
        self._scenarios.pop(self._sel_idx)
        save_scenarios(self._scenarios)
        self._render_scenarios()
        self._select_scenario(max(0, self._sel_idx - 1))

    def _export_preset(self):
        """シナリオ＋変数を1つのJSONファイルに書き出す"""
        self._save_current_sql()
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile="preset.json",
            filetypes=[("プリセット JSON", "*.json"), ("全ファイル", "*.*")],
            title="プリセットの書き出し先を選択",
        )
        if not path: return
        preset = {
            "version": 1,
            "scenarios": self._scenarios,
            "variables": [{"key": k.get(), "val": v.get()}
                          for k, v, _ in self._var_rows],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(preset, f, ensure_ascii=False, indent=2)
        self._log(f"↑ プリセットを書き出しました → {os.path.basename(path)}", "ok")

    def _import_preset(self):
        """JSONファイルからシナリオ＋変数を読み込む"""
        path = filedialog.askopenfilename(
            filetypes=[("プリセット JSON", "*.json"), ("全ファイル", "*.*")],
            title="読み込むプリセットファイルを選択",
        )
        if not path: return

        try:
            with open(path, "r", encoding="utf-8") as f:
                preset = json.load(f)
        except Exception as e:
            messagebox.showerror("読み込みエラー", f"ファイルを読み込めませんでした:\n{e}")
            return

        scenarios = preset.get("scenarios", [])
        variables = preset.get("variables", [])

        if not isinstance(scenarios, list) or not scenarios:
            messagebox.showerror("フォーマットエラー", "有効なシナリオが含まれていません")
            return

        mode = messagebox.askyesnocancel(
            "読み込み方法",
            f"シナリオ {len(scenarios)} 件・変数 {len(variables)} 件を読み込みます。\n\n"
            "「はい」  → 現在の内容を置き換える\n"
            "「いいえ」→ 現在の内容に追加する\n"
            "「キャンセル」→ 中止",
        )
        if mode is None: return  # キャンセル

        if mode:  # 置き換え
            self._scenarios = scenarios
        else:  # 追加
            self._scenarios = self._scenarios + scenarios

        save_scenarios(self._scenarios)
        self._render_scenarios()
        self._select_scenario(0)

        # 変数の読み込み
        if variables:
            if mode:  # 置き換え：既存行を全削除
                for row in list(self._var_rows):
                    _, _, f = row
                    f.destroy()
                self._var_rows = []

            for item in variables:
                self._add_var_row(item.get("key", ""), item.get("val", ""))
            self._save_variables()

        n_sc  = len(scenarios)
        n_var = len(variables)
        verb  = "置き換え" if mode else "追加"
        self._log(f"↓ プリセット読み込み完了: シナリオ {n_sc} 件・変数 {n_var} 件を{verb}", "ok")

    # ══ プロファイル管理 ══════════════════════════════════════
    def _refresh_profiles(self):
        self._profile_cb["values"] = list(self._configs.keys())
        if self._configs:
            first = list(self._configs.keys())[0]
            self._profile_var.set(first)
            self._load_profile()

    def _load_profile(self, _=None):
        name = self._profile_var.get()
        cfg  = self._configs.get(name, {})

        def _set(e, key, default=""):
            e.delete(0, "end")
            e.insert(0, cfg.get(key, default))

        _set(self._host_e,    "host",     "127.0.0.1")
        _set(self._port_e,    "port",     "3306")
        _set(self._user_e,    "user",     "")
        _set(self._db_e,      "db",       "")
        _set(self._ssl_ca_e,  "ssl_ca",   "")
        _set(self._ssl_cert_e,"ssl_cert", "")
        _set(self._ssl_key_e, "ssl_key",  "")

        self._pass_e.delete(0, "end")
        if cfg.get("password_enc"):
            self._pass_e.insert(0, _dec(cfg["password_enc"]))

        # SSH
        use_ssh = cfg.get("use_ssh", False)
        self._ssh_enabled.set(use_ssh)

        _set(self._ssh["host_e"],       "ssh_host",   "")
        _set(self._ssh["port_e"],       "ssh_port",   "22")
        _set(self._ssh["user_e"],       "ssh_user",   "")
        _set(self._ssh["pkey_e"],       "ssh_pkey",   "")
        self._ssh["passphrase_e"].delete(0, "end")
        if cfg.get("ssh_passphrase_enc"):
            self._ssh["passphrase_e"].insert(0, _dec(cfg["ssh_passphrase_enc"]))
        self._ssh["password_e"].delete(0, "end")
        if cfg.get("ssh_password_enc"):
            self._ssh["password_e"].insert(0, _dec(cfg["ssh_password_enc"]))
        self._ssh["auth_mode"].set(cfg.get("ssh_auth_mode", "key"))
        self._ssh["refresh_auth"]()

        # Jump
        use_jump = cfg.get("use_jump", False)
        self._jump_enabled.set(use_jump)

        _set(self._jump["host_e"],      "jump_host",  "")
        _set(self._jump["port_e"],      "jump_port",  "22")
        _set(self._jump["user_e"],      "jump_user",  "")
        _set(self._jump["pkey_e"],      "jump_pkey",  "")
        self._jump["passphrase_e"].delete(0, "end")
        if cfg.get("jump_passphrase_enc"):
            self._jump["passphrase_e"].insert(0, _dec(cfg["jump_passphrase_enc"]))
        self._jump["password_e"].delete(0, "end")
        if cfg.get("jump_password_enc"):
            self._jump["password_e"].insert(0, _dec(cfg["jump_password_enc"]))
        self._jump["auth_mode"].set(cfg.get("jump_auth_mode", "key"))
        self._jump["refresh_auth"]()

        self._update_flow_label()

    def _save_profile(self):
        name = simpledialog.askstring("プロファイル保存", "プロファイル名:",
                                       initialvalue=self._profile_var.get())
        if not name: return
        self._configs[name] = {
            "host":               self._host_e.get(),
            "port":               self._port_e.get(),
            "user":               self._user_e.get(),
            "db":                 self._db_e.get(),
            "password_enc":       _enc(self._pass_e.get()),
            "ssl_ca":             self._ssl_ca_e.get(),
            "ssl_cert":           self._ssl_cert_e.get(),
            "ssl_key":            self._ssl_key_e.get(),
            # SSH
            "use_ssh":            self._ssh_enabled.get(),
            "ssh_host":           self._ssh["host_e"].get(),
            "ssh_port":           self._ssh["port_e"].get(),
            "ssh_user":           self._ssh["user_e"].get(),
            "ssh_auth_mode":      self._ssh["auth_mode"].get(),
            "ssh_pkey":           self._ssh["pkey_e"].get(),
            "ssh_passphrase_enc": _enc(self._ssh["passphrase_e"].get()),
            "ssh_password_enc":   _enc(self._ssh["password_e"].get()),
            # Jump
            "use_jump":            self._jump_enabled.get(),
            "jump_host":           self._jump["host_e"].get(),
            "jump_port":           self._jump["port_e"].get(),
            "jump_user":           self._jump["user_e"].get(),
            "jump_auth_mode":      self._jump["auth_mode"].get(),
            "jump_pkey":           self._jump["pkey_e"].get(),
            "jump_passphrase_enc": _enc(self._jump["passphrase_e"].get()),
            "jump_password_enc":   _enc(self._jump["password_e"].get()),
        }
        save_configs(self._configs)
        self._refresh_profiles()
        self._profile_var.set(name)
        self._log(f"プロファイル「{name}」を保存しました", "ok")

    def _delete_profile(self):
        name = self._profile_var.get()
        if not name: return
        if messagebox.askyesno("削除確認", f"「{name}」を削除しますか？"):
            self._configs.pop(name, None)
            save_configs(self._configs)
            self._refresh_profiles()
            self._log(f"プロファイル「{name}」を削除しました", "warn")

    # ══ エクスポート ══════════════════════════════════════════
    def _run_selected(self):
        if not self._conn:
            self._log("先に接続してください", "warn"); return
        self._save_current_sql()
        sc = self._scenarios[self._sel_idx]
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"{sc['name']}.csv",
            filetypes=[("CSV", "*.csv"), ("全ファイル", "*.*")],
        )
        if not path: return
        self._run_one_btn.disable()
        self._run_all_btn.disable()
        vars_ = self._get_variables()
        threading.Thread(target=self._exec_to_file,
                         args=(sc, vars_, path), daemon=True).start()

    def _run_all(self):
        if not self._conn:
            self._log("先に接続してください", "warn"); return
        self._save_current_sql()
        out_dir = filedialog.askdirectory(title="CSV の出力フォルダを選択")
        if not out_dir: return

        self._run_one_btn.disable()
        self._run_all_btn.disable()
        vars_ = self._get_variables()
        self._log("─── 全シナリオ実行開始 ───", "hdr")
        if vars_:
            self._log(f"変数: {vars_}", "info")

        def _run():
            ok = err = 0
            for i, sc in enumerate(self._scenarios):
                fname = re.sub(r'[\\/:*?"<>|]', "_", sc["name"]) + ".csv"
                path  = os.path.join(out_dir, fname)
                self.after(0, self._log,
                           f"[{i+1}/{len(self._scenarios)}] {sc['name']} ...", "info")
                try:
                    cols, rows = self._exec_query(sc["sql"], vars_)
                    self._write_csv(cols, rows, path)
                    self.after(0, self._log, f"  ✓ {len(rows)} 行 → {fname}", "ok")
                    ok += 1
                except Exception as e:
                    self.after(0, self._log, f"  ✗ エラー: {e}", "err")
                    err += 1
            self.after(0, self._on_all_done, ok, err, out_dir)

        threading.Thread(target=_run, daemon=True).start()

    def _on_all_done(self, ok, err, out_dir):
        self._run_one_btn.enable()
        self._run_all_btn.enable()
        self._log(f"─── 完了: {ok} 成功 / {err} 失敗 ───", "hdr")
        if ok > 0 and messagebox.askyesno("完了",
                f"{ok} 件のCSVを出力しました。\nフォルダを開きますか？\n{out_dir}"):
            self._open_path(out_dir)

    def _exec_to_file(self, sc, vars_, path):
        try:
            cols, rows = self._exec_query(sc["sql"], vars_)
            self._write_csv(cols, rows, path)
            self.after(0, self._on_one_done, path, len(rows))
        except Exception as e:
            self.after(0, self._on_one_error, str(e))

    def _exec_query(self, sql_template, vars_):
        sql = substitute_vars(sql_template, vars_)
        cur = self._conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        cur.close()
        return cols, rows

    def _write_csv(self, cols, rows, path):
        with open(path, "w", newline="", encoding=self._enc_var.get()) as f:
            w = csv.writer(f, delimiter=self._delim_var.get())
            w.writerow(cols)
            w.writerows(rows)

    def _on_one_done(self, path, rows):
        self._run_one_btn.enable()
        self._run_all_btn.enable()
        self._log(f"✓ {rows} 行 → {path}", "ok")
        if messagebox.askyesno("完了", f"{rows} 行をエクスポートしました。\nファイルを開きますか？"):
            self._open_path(path)

    def _on_one_error(self, msg):
        self._run_one_btn.enable()
        self._run_all_btn.enable()
        self._log(f"✗ エラー: {msg}", "err")

    @staticmethod
    def _open_path(path):
        import subprocess
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])

    def _log(self, msg: str, tag: str = "info"):
        ts   = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        self._log_text.config(state="normal")
        self._log_text.insert("end", line, tag)
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    def destroy(self):
        self._cleanup_connections()
        super().destroy()


# ── エントリポイント ──────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
