import tkinter as tk
from tkinter import filedialog, messagebox, font, simpledialog, ttk
import sys
import os
import requests
import webbrowser
import calendar
import json
import re
import subprocess
import uuid
from datetime import datetime
import configparser
import platform
import importlib.util
import traceback
import struct
import zlib
from html.parser import HTMLParser
from pixelscript_markdown import export_pdf, extract_headings, markdown_to_html

try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.exceptions import InvalidTag
except ImportError:
    hashes = AESGCM = PBKDF2HMAC = InvalidTag = None

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

root = tk.Tk()
# Prefer Arial when available, otherwise pick a sensible default on the system
preferred_family = "Arial"
available_fonts = list(font.families())
if preferred_family not in available_fonts:
    preferred_family = available_fonts[0] if available_fonts else "TkDefaultFont"
current_font = font.Font(root=root, family=preferred_family, size=12)

root.title("PixelScript+")
root.geometry("900x600")
root.iconphoto(True, tk.PhotoImage(file=resource_path("Icon.png")))

workspace = tk.PanedWindow(root, orient="horizontal", sashwidth=5, sashrelief="raised")
workspace.pack(fill="both", expand=True)
editor_notebook = ttk.Notebook(workspace)
workspace.add(editor_notebook)
documents = {}
document_frames = {}
text_area = None
line_counter = None
current_file_path = None
current_ntsi_password = None
current_ntsi_compressed = False
unsaved_changes = False
recent_files = []
split_enabled = False
split_frame = None
split_editor = None
split_line_counter = None

def update_line_counter(event=None):
    widget = event.widget if event and event.widget in documents else text_area
    _refresh_line_counter(widget)

def _refresh_line_counter(widget):
    if widget is None or widget not in documents:
        return
    text = widget.get("1.0", "end-1c")
    lines = text.count("\n") + 1
    line_numbers = "\n".join(str(i) for i in range(1, lines + 1))
    gutter = documents[widget]["line_counter"]
    gutter.config(state="normal")
    gutter.delete("1.0", "end")
    gutter.insert("1.0", line_numbers)
    gutter.config(state="disabled")

# Github info
OWNER = "Northy2410"
REPO = "PixelScript-Plus"
CURRENT_VERSION = "2.0"

# update check (manual invocation)
def check_for_update(parent=None, silent=False):
    parent = root if parent is None else parent
    check_beta = load_beta_updates_setting()
    url = (
        f"https://api.github.com/repos/{OWNER}/{REPO}/releases"
        if check_beta else
        f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
    )
    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        releases = response.json()
        latest_release = releases[0] if check_beta and releases else releases
        if not isinstance(latest_release, dict):
            raise ValueError("GitHub returned an invalid release response.")
    except (requests.RequestException, ValueError, IndexError) as exc:
        if not silent:
            messagebox.showerror("Update Check Failed", f"Could not check for updates.\n\n{exc}", parent=parent)
        return

    latest_version = latest_release.get("tag_name", "").lstrip("vV")
    release_url = latest_release.get("html_url")
    if not latest_version or not release_url:
        if not silent:
            messagebox.showerror(
                "Update Check Failed",
                "The GitHub release is missing its version or download page.",
                parent=parent,
            )
        return
    latest_numbers = _version_numbers(latest_version)
    current_numbers = _version_numbers(CURRENT_VERSION)
    is_newer = latest_version != CURRENT_VERSION
    if latest_numbers is not None and current_numbers is not None:
        width = max(len(latest_numbers), len(current_numbers))
        is_newer = (
            latest_numbers + (0,) * (width - len(latest_numbers))
            > current_numbers + (0,) * (width - len(current_numbers))
        )
    if not is_newer:
        if not silent:
            messagebox.showinfo("Up To Date", f"You're using v{CURRENT_VERSION}. No newer release is available.", parent=parent)
        return

    update_win = tk.Toplevel(parent)
    update_win.title(f"PixelScript+ {latest_version} Release Notes")
    update_win.geometry("650x520")
    update_win.minsize(480, 360)
    update_win.transient(parent)
    version_type = " (Beta)" if latest_release.get("prerelease", False) else ""
    tk.Label(
        update_win,
        text=f"PixelScript+ {latest_version}{version_type} is available  ·  Current: {CURRENT_VERSION}",
        font=("Arial", 12, "bold"),
        anchor="w",
    ).pack(fill="x", padx=12, pady=(12, 6))
    notes_frame = tk.Frame(update_win)
    notes_frame.pack(fill="both", expand=True, padx=12, pady=6)
    notes = tk.Text(notes_frame, wrap="word", padx=10, pady=8)
    notes_scroll = ttk.Scrollbar(notes_frame, orient="vertical", command=notes.yview)
    notes.configure(yscrollcommand=notes_scroll.set)
    notes.pack(side="left", fill="both", expand=True)
    notes_scroll.pack(side="right", fill="y")
    release_body = latest_release.get("body") or "No release notes were provided."
    renderer = _MarkdownTextRenderer(notes)
    renderer.feed(markdown_to_html(release_body, title="Release Notes"))
    renderer.close()
    notes.configure(state="disabled")
    buttons = tk.Frame(update_win)
    buttons.pack(fill="x", padx=12, pady=(4, 12))
    tk.Button(
        buttons,
        text="Open GitHub Page to Download",
        command=lambda: _open_release_page(release_url, update_win),
        font=("Arial", 10),
    ).pack(side="left")
    tk.Button(buttons, text="Close", command=update_win.destroy, width=12).pack(side="right")
    style_window(update_win, current_theme)

def _open_release_page(url, parent):
    try:
        if not webbrowser.open(url):
            raise OSError("The default browser did not accept the request.")
    except (OSError, webbrowser.Error) as exc:
        messagebox.showerror("Open Release Page", str(exc), parent=parent)

def _version_numbers(version):
    match = re.match(r"^[vV]?(\d+(?:\.\d+)*)(?:[-+].*)?$", version)
    if not match:
        return None
    return tuple(int(part) for part in match.group(1).split("."))

NTSI_MAGIC = bytes.fromhex("A70E19C4")
NTSI_VERSION = 2
NTSI_HEADER_SIZE = 58
NTSI_FLAG_COMPRESSED = 0x0001
NTSI_PBKDF2_ITERATIONS = 300_000
NTSI_HEADER = struct.Struct("<4sHHH16s12sQQI")
MAX_NTSI_TEXT_BYTES = 64 * 1024 * 1024

def require_ntsi_support():
    if AESGCM is None:
        messagebox.showerror(
            "NTSI Support Unavailable",
            "The cryptography package is required to open and save .NTSI files.",
        )
        return False
    return True

def derive_ntsi_key(password, salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=NTSI_PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))

def inspect_ntsi(data):
    if len(data) < NTSI_HEADER_SIZE:
        raise ValueError("File is too small to contain an NTSI header")

    magic, version, header_size, flags, salt, nonce, text_bytes, stored_bytes, crc32 = (
        NTSI_HEADER.unpack(data[:NTSI_HEADER_SIZE])
    )
    if magic != NTSI_MAGIC:
        raise ValueError("Invalid NTSI magic")
    if version != NTSI_VERSION:
        raise ValueError("Unsupported NTSI version")
    if header_size != NTSI_HEADER_SIZE:
        raise ValueError("Invalid NTSI header size")
    if flags & ~NTSI_FLAG_COMPRESSED:
        raise ValueError("Unknown NTSI flags")
    if text_bytes > MAX_NTSI_TEXT_BYTES or stored_bytes > MAX_NTSI_TEXT_BYTES:
        raise ValueError("NTSI file exceeds the supported size limit")
    if len(data) - NTSI_HEADER_SIZE != stored_bytes:
        raise ValueError("Stored payload size does not match the NTSI header")

    return {
        "compressed": bool(flags & NTSI_FLAG_COMPRESSED),
        "text_bytes": text_bytes,
        "stored_bytes": stored_bytes,
        "crc32": crc32,
        "salt": salt,
        "nonce": nonce,
    }

def decode_ntsi(data, password):
    info = inspect_ntsi(data)
    try:
        payload = AESGCM(derive_ntsi_key(password, info["salt"])).decrypt(
            info["nonce"],
            data[NTSI_HEADER_SIZE:],
            data[:NTSI_HEADER_SIZE],
        )
    except InvalidTag as exc:
        raise ValueError("Wrong password or corrupted NTSI file") from exc

    if info["compressed"]:
        payload = zlib.decompress(payload)

    if len(payload) != info["text_bytes"]:
        raise ValueError("Text size does not match the NTSI header")
    if zlib.crc32(payload) & 0xFFFFFFFF != info["crc32"]:
        raise ValueError("CRC32 checksum failed")

    return payload.decode("utf-8")

def encode_ntsi(text, password, compress=False):
    if not password:
        raise ValueError("A non-empty password is required")

    text_bytes = text.encode("utf-8")
    if len(text_bytes) > MAX_NTSI_TEXT_BYTES:
        raise ValueError("Text exceeds the supported NTSI size limit")

    payload = zlib.compress(text_bytes) if compress else text_bytes
    if len(payload) > MAX_NTSI_TEXT_BYTES:
        raise ValueError("Encrypted payload exceeds the supported size limit")

    salt = os.urandom(16)
    nonce = os.urandom(12)
    header = NTSI_HEADER.pack(
        NTSI_MAGIC,
        NTSI_VERSION,
        NTSI_HEADER_SIZE,
        NTSI_FLAG_COMPRESSED if compress else 0,
        salt,
        nonce,
        len(text_bytes),
        len(payload) + 16,
        zlib.crc32(text_bytes) & 0xFFFFFFFF,
    )
    ciphertext = AESGCM(derive_ntsi_key(password, salt)).encrypt(nonce, payload, header)
    return header + ciphertext

def ask_ntsi_password(confirm=False):
    password = simpledialog.askstring(
        "NTSI Password",
        "Enter the NTSI password:",
        parent=root,
        show="*",
    )
    if password is None:
        return None
    if not password:
        messagebox.showerror("Invalid Password", "A non-empty password is required.")
        return None
    if confirm:
        confirmation = simpledialog.askstring(
            "Confirm Password",
            "Confirm the NTSI password:",
            parent=root,
            show="*",
        )
        if confirmation is None:
            return None
        if password != confirmation:
            messagebox.showerror("Password Mismatch", "The passwords do not match.")
            return None
    return password

def _document_title(state):
    path = state["path"]
    title = os.path.basename(path) if path else "Untitled"
    return f"{title}{' *' if state['modified'] else ''}"

def _refresh_document_title(state):
    editor_notebook.tab(state["frame"], text=_document_title(state))
    if state["editor"] is text_area:
        root.title(f"PixelScript+ - {_document_title(state)}")

def _apply_editor_theme(editor, gutter, theme):
    if theme == "dark":
        editor.config(bg="#23272e", fg="#f8f8f2", insertbackground="#f8f8f2")
        gutter.config(bg="#23272e", fg="#5c6370")
    else:
        editor.config(bg="white", fg="black", insertbackground="black")
        gutter.config(bg="#f0f0f0", fg="gray")

def _set_active_document(event=None):
    global text_area, line_counter, current_file_path, current_ntsi_password
    global current_ntsi_compressed, unsaved_changes
    selected = editor_notebook.select()
    if not selected:
        return
    editor = document_frames.get(selected)
    if editor is None:
        return
    state = documents[editor]
    text_area = editor
    line_counter = state["line_counter"]
    current_file_path = state["path"]
    current_ntsi_password = state["ntsi_password"]
    current_ntsi_compressed = state["ntsi_compressed"]
    unsaved_changes = state["modified"]
    if "PLUGIN_API" in globals():
        PLUGIN_API["text_area"] = editor
    update_line_counter()
    _refresh_document_title(state)
    if split_enabled:
        _sync_split_view()

def create_document(text="", path=None, modified=False, password=None,
                    compressed=False, recovery_id=None, select=True):
    frame = ttk.Frame(editor_notebook)
    gutter = tk.Text(
        frame, width=4, padx=4, takefocus=0, border=0, wrap="none",
        background="#f0f0f0", foreground="gray", state="disabled", font=current_font
    )
    gutter.pack(side="left", fill="y")
    editor = tk.Text(frame, wrap="word", undo=True, font=current_font)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=editor.yview)
    editor.configure(yscrollcommand=scrollbar.set)
    editor.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    if "current_theme" in globals():
        _apply_editor_theme(editor, gutter, current_theme)
    if text:
        editor.insert("1.0", text)
    editor.edit_modified(False)
    state = {
        "frame": frame,
        "editor": editor,
        "line_counter": gutter,
        "path": os.path.abspath(path) if path else None,
        "modified": bool(modified),
        "ntsi_password": password,
        "ntsi_compressed": compressed,
        "recovery_id": recovery_id or uuid.uuid4().hex,
        "disk_snapshot": _file_snapshot(path),
        "external_change": False,
        "preview": None,
        "preview_after": None,
    }
    documents[editor] = state
    document_frames[str(frame)] = editor
    editor.bind("<KeyRelease>", update_line_counter)
    editor.bind("<MouseWheel>", update_line_counter)
    editor.bind("<ButtonRelease-1>", update_line_counter)
    editor.bind("<Configure>", update_line_counter)
    editor.bind("<<Modified>>", on_text_modified)
    editor_notebook.add(frame, text=_document_title(state))
    if select:
        editor_notebook.select(frame)
        _set_active_document()
    _refresh_line_counter(editor)
    return editor

def on_text_modified(event=None):
    global unsaved_changes
    editor = event.widget if event else text_area
    state = documents.get(editor)
    if state is None or not editor.edit_modified():
        return
    editor.edit_modified(False)
    state["modified"] = True
    _refresh_document_title(state)
    if editor is text_area:
        unsaved_changes = True
    if state["preview"] and state["preview"].winfo_exists():
        if state["preview_after"]:
            root.after_cancel(state["preview_after"])
        state["preview_after"] = root.after(250, lambda s=state: _refresh_markdown_preview(s))
    if split_enabled and editor is text_area:
        _sync_split_view()

def new_file():
    create_document()

def _file_snapshot(path):
    if not path:
        return None
    try:
        stat = os.stat(path)
        return stat.st_mtime_ns, stat.st_size
    except OSError:
        return None

def on_closing():
    modified = [state for state in documents.values() if state["modified"]]
    if modified:
        choice = messagebox.askyesnocancel(
            "Unsaved Changes",
            "Save all unsaved documents before closing?\n\n"
            "Choose No to keep recovery drafts for the next launch.",
        )
        if choice is None:
            return
        if choice:
            for state in modified:
                editor_notebook.select(state["frame"])
                _set_active_document()
                save_file()
                if state["modified"]:
                    return
        else:
            for state in modified:
                try:
                    _save_recovery_draft(state)
                except (OSError, ValueError, zlib.error) as exc:
                    messagebox.showerror("Draft Recovery", f"Could not save a recovery draft:\n{exc}")
                    return
    _save_session()
    for state in documents.values():
        state["ntsi_password"] = None
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

def open_file():
    file = filedialog.askopenfilename(
        filetypes=[
            ("Text and Markdown Files", "*.txt *.md *.MD"),
            ("Supported Files", "*.txt *.md *.MD *.NTSI"),
            ("Text Files", "*.txt"),
            ("Markdown Files", "*.md *.MD"),
            ("NorthTech S.I.A.V.A. Memory File", "*.NTSI"),
        ]
    )
    if file:
        _load_document(file)

def save_file():
    """Save to current file, or prompt for filename if no file is open."""
    if current_file_path:
        if _write_document(documents[text_area]):
            messagebox.showinfo("Saved", "File saved successfully!")
    else:
        save_as_file()

def save_as_file():
    """Always prompt for a new filename to save to."""
    file = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[
            ("Text Files", "*.txt"),
            ("Markdown Files", "*.md *.MD"),
            ("NorthTech S.I.A.V.A. Memory File", "*.NTSI"),
        ],
    )
    if file and _write_document(documents[text_area], file):
        messagebox.showinfo("Saved", "File saved successfully!")

def save_as_markdown_file():
    file = filedialog.asksaveasfilename(
        defaultextension=".md",
        filetypes=[("Markdown Files", "*.md *.MD")],
    )
    if file and _write_document(documents[text_area], file):
        messagebox.showinfo("Saved", "Markdown file saved successfully!")

def _load_document(path, password=None, recovery_id=None, select=True):
    normalized = os.path.normcase(os.path.abspath(path))
    for editor, state in documents.items():
        if state["path"] and os.path.normcase(state["path"]) == normalized:
            editor_notebook.select(state["frame"])
            _set_active_document()
            return editor
    try:
        if os.path.splitext(path)[1].lower() == ".ntsi":
            if not require_ntsi_support():
                return None
            password = password or ask_ntsi_password()
            if password is None:
                return None
            with open(path, "rb") as stream:
                data = stream.read()
            content = decode_ntsi(data, password)
            compressed = inspect_ntsi(data)["compressed"]
        else:
            with open(path, "r", encoding="utf-8") as stream:
                content = stream.read()
            password = None
            compressed = False
    except (OSError, UnicodeDecodeError, ValueError, zlib.error) as exc:
        messagebox.showerror("Unable to Open File", str(exc))
        return None

    blank_active = (
        text_area is not None
        and text_area in documents
        and not documents[text_area]["path"]
        and not documents[text_area]["modified"]
        and not text_area.get("1.0", "end-1c")
    )
    if blank_active:
        editor = text_area
        state = documents[editor]
    else:
        editor = create_document(select=False)
        state = documents[editor]
    editor.delete("1.0", "end")
    editor.insert("1.0", content)
    editor.edit_modified(False)
    state.update({
        "path": os.path.abspath(path),
        "modified": False,
        "ntsi_password": password,
        "ntsi_compressed": compressed,
        "recovery_id": recovery_id or state["recovery_id"],
        "disk_snapshot": _file_snapshot(path),
        "external_change": False,
    })
    _refresh_document_title(state)
    if select:
        editor_notebook.select(state["frame"])
        _set_active_document()
    _record_recent_file(path)
    return editor

def get_recovery_dir():
    folder = os.path.join(os.path.dirname(SETTINGS_FILE), "recovery")
    os.makedirs(folder, exist_ok=True)
    return folder

def _write_document(state, path=None):
    global current_file_path, current_ntsi_password, current_ntsi_compressed, unsaved_changes
    destination = path or state["path"]
    if not destination:
        return False
    is_ntsi = os.path.splitext(destination)[1].lower() == ".ntsi"
    password = state["ntsi_password"]
    compressed = state["ntsi_compressed"]
    try:
        content = state["editor"].get("1.0", "end-1c")
        if state["external_change"] and destination == state["path"]:
            if not messagebox.askyesno(
                "File Changed on Disk",
                "This file changed outside PixelScript. Overwrite those changes?",
            ):
                return False
        if is_ntsi:
            if not require_ntsi_support():
                return False
            if not password or destination != state["path"]:
                password = ask_ntsi_password(confirm=True)
                if password is None:
                    return False
                compressed = messagebox.askyesno(
                    "Compress NTSI File",
                    "Compress the text before encrypting?",
                )
            data = encode_ntsi(content, password, compress=compressed)
            with open(destination, "wb") as stream:
                stream.write(data)
        else:
            with open(destination, "w", encoding="utf-8", newline="") as stream:
                stream.write(content)
    except (OSError, UnicodeDecodeError, UnicodeEncodeError, ValueError, zlib.error) as exc:
        messagebox.showerror("Unable to Save File", str(exc))
        return False
    state.update({
        "path": os.path.abspath(destination),
        "ntsi_password": password if is_ntsi else None,
        "ntsi_compressed": compressed if is_ntsi else False,
        "modified": False,
        "disk_snapshot": _file_snapshot(destination),
        "external_change": False,
    })
    _remove_recovery_draft(state)
    _refresh_document_title(state)
    _record_recent_file(destination)
    if state["editor"] is text_area:
        current_file_path = state["path"]
        current_ntsi_password = state["ntsi_password"]
        current_ntsi_compressed = state["ntsi_compressed"]
        unsaved_changes = False
    return True

def set_font_family(family):
    current_font.config(family=family)

def set_font_size(size):
    current_font.config(size=size)

def toggle_bold():
    if current_font.actual()['weight'] == 'normal':
        current_font.config(weight='bold')
    else:
        current_font.config(weight='normal')

def toggle_italic():
    if current_font.actual()['slant'] == 'roman':
        current_font.config(slant='italic')
    else:
        current_font.config(slant='roman')

# calculator
def open_calculator():
    calc_win = tk.Toplevel(root)
    calc_win.title("Calculator")
    calc_win.geometry("300x410")

    entry = tk.Entry(calc_win, width=20, font=('Arial', 16), borderwidth=5, relief='ridge')
    entry.grid(row=0, column=0, columnspan=4, pady=10)

    def click(btn):
        entry.insert(tk.END, btn)
        
    def clear():
        entry.delete(0, tk.END)

    def calculate():
        try:
            result = eval(entry.get())
            entry.delete(0, tk.END)
            entry.insert(0, str(result))
        except Exception:
            entry.delete(0, tk.END)
            entry.insert(0, "Error")

    buttons = [
        '7', '8', '9', '/',
        '4', '5', '6', '*',
        '1', '2', '3', '-',
        '0', '.', '=', '+'
    ]

    row_val, col_val = 1, 0
    for btn in buttons:
        if btn == '=':
            b = tk.Button(calc_win, text=btn, width=5, height=2, font=('Arial', 14), command=calculate)
        else:
            b = tk.Button(calc_win, text=btn, width=5, height=2, font=('Arial', 14), command=lambda x=btn: click(x))
        b.grid(row=row_val, column=col_val, padx=5, pady=5)
        col_val += 1
        if col_val > 3:
            col_val = 0
            row_val += 1

    clear_btn = tk.Button(calc_win, text='C', width=5, height=2, font=('Arial', 14), command=clear)
    clear_btn.grid(row=row_val, column=0, padx=5, pady=5)

    style_window(calc_win, current_theme)

# calendar
def open_calendar():
    cal_win = tk.Toplevel(root)
    cal_win.title("Calendar")
    cal_win.geometry("260x320")
    cal_win.resizable(False, False)

    now = datetime.now()
    year_var = tk.IntVar(value=now.year)
    month_var = tk.IntVar(value=now.month)
    selected_day = tk.IntVar(value=now.day)

    header_frame = tk.Frame(cal_win)
    header_frame.pack(pady=8)
    tk.Button(header_frame, text="<", width=2, command=lambda: prev_month()).pack(side="left")

    month_year_label = tk.Label(
        header_frame,
        text=f"{calendar.month_name[month_var.get()]} {year_var.get()}",
        font=('Arial', 14, 'bold'),
        width=15,
        anchor="center"
    )
    month_year_label.pack(side="left", padx=5)

    tk.Button(header_frame, text=">", width=2, command=lambda: next_month()).pack(side="left")

    days_frame = tk.Frame(cal_win)
    days_frame.pack(pady=10)

    def draw_calendar():
        month_year_label.config(text=f"{calendar.month_name[month_var.get()]} {year_var.get()}")
        for widget in days_frame.winfo_children():
            widget.destroy()
        year = year_var.get()
        month = month_var.get()
        cal = calendar.monthcalendar(year, month)
        for i, day in enumerate(['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']):
            tk.Label(days_frame, text=day, width=3, font=('Arial', 9, 'bold')).grid(row=0, column=i)
        for r, week in enumerate(cal, 1):
            for c, day in enumerate(week):
                if day == 0:
                    tk.Label(days_frame, text="", width=3).grid(row=r, column=c)
                else:
                    b = tk.Radiobutton(
                        days_frame, text=str(day), width=3, variable=selected_day, value=day,
                        indicatoron=0, font=('Arial', 9)
                    )
                    b.grid(row=r, column=c)

    def prev_month():
        m, y = month_var.get(), year_var.get()
        if m == 1:
            month_var.set(12)
            year_var.set(y - 1)
        else:
            month_var.set(m - 1)
        draw_calendar()

    def next_month():
        m, y = month_var.get(), year_var.get()
        if m == 12:
            month_var.set(1)
            year_var.set(y + 1)
        else:
            month_var.set(m + 1)
        draw_calendar()

    def show_date():
        y, m, d = year_var.get(), month_var.get(), selected_day.get()
        if d == 0:
            messagebox.showwarning("No Date", "Please select a day.")
        else:
            date_str = f"{y}-{m:02d}-{d:02d}"
            text_area.insert(tk.INSERT, date_str)
            cal_win.destroy()

    tk.Button(cal_win, text="Insert Date", command=show_date).pack(pady=10)

    draw_calendar()
    style_window(cal_win, current_theme)

def get_settings_path():
    if platform.system() == "Windows":
        appdata = os.getenv("APPDATA")
        folder = os.path.join(appdata, "PixelScriptPlus")
    else:
        folder = os.path.expanduser("~/.pixelscriptplus")
    if not os.path.exists(folder):
        os.makedirs(folder)
    return os.path.join(folder, "settings.ini")


def get_plugins_dir():
    r"""Return the plugins directory path and ensure it exists.

    On Windows this will be: %APPDATA%\PixelScriptPlus\plugins
    On other systems: ~/.pixelscriptplus/plugins
    """
    if platform.system() == "Windows":
        appdata = os.getenv("APPDATA")
        folder = os.path.join(appdata, "PixelScriptPlus", "plugins")
    else:
        folder = os.path.expanduser("~/.pixelscriptplus/plugins")
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    return folder

SETTINGS_FILE = get_settings_path()

def load_settings():
    config = configparser.ConfigParser()
    if os.path.exists(SETTINGS_FILE):
        config.read(SETTINGS_FILE)
        return config.get("Appearance", "theme", fallback="light")
    return "light"

def load_beta_updates_setting():
    """Load the beta updates preference from settings."""
    config = configparser.ConfigParser()
    if os.path.exists(SETTINGS_FILE):
        config.read(SETTINGS_FILE)
        return config.getboolean("Updates", "check_beta", fallback=False)
    return False

SESSION_FILE = os.path.join(os.path.dirname(SETTINGS_FILE), "session.json")
RECENT_FILE = os.path.join(os.path.dirname(SETTINGS_FILE), "recent.json")

def _atomic_write(path, data):
    temp_path = f"{path}.{uuid.uuid4().hex}.tmp"
    try:
        with open(temp_path, "wb") as stream:
            stream.write(data)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def _record_recent_file(path):
    global recent_files
    normalized = os.path.abspath(path)
    recent_files = [item for item in recent_files if os.path.normcase(item) != os.path.normcase(normalized)]
    recent_files.insert(0, normalized)
    recent_files = recent_files[:10]
    try:
        _atomic_write(RECENT_FILE, json.dumps(recent_files, indent=2).encode("utf-8"))
    except OSError as exc:
        messagebox.showwarning("Recent Files", f"Could not save the recent files list:\n{exc}")
    if "recent_menu" in globals():
        _refresh_recent_menu()

def _load_recent_files():
    global recent_files
    if not os.path.exists(RECENT_FILE):
        return
    try:
        with open(RECENT_FILE, "r", encoding="utf-8") as stream:
            entries = json.load(stream)
        if not isinstance(entries, list) or not all(isinstance(item, str) for item in entries):
            raise ValueError("Recent files data has an invalid format.")
        recent_files = [item for item in entries if os.path.isfile(item)][:10]
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        messagebox.showwarning("Recent Files", f"Could not load the recent files list:\n{exc}")
        recent_files = []

def _refresh_recent_menu():
    recent_menu.delete(0, "end")
    available = [path for path in recent_files if os.path.isfile(path)]
    if not available:
        recent_menu.add_command(label="(No recent files)", state="disabled")
        return
    for path in available:
        recent_menu.add_command(
            label=path,
            command=lambda selected=path: _load_document(selected),
        )

def _save_session():
    selected = documents.get(text_area, {})
    saved_documents = [
        state for state in documents.values()
        if state["path"] or state["modified"] or state["editor"].get("1.0", "end-1c")
    ]
    session = {
        "version": 1,
        "selected_recovery_id": selected.get("recovery_id"),
        "documents": [
            {
                "path": state["path"],
                "recovery_id": state["recovery_id"],
                "modified": state["modified"],
            }
            for state in saved_documents
        ],
    }
    try:
        if not saved_documents:
            try:
                os.remove(SESSION_FILE)
            except FileNotFoundError:
                pass
            _save_session.last_payload = None
            return
        payload = json.dumps(session, indent=2).encode("utf-8")
        if getattr(_save_session, "last_payload", None) != payload:
            _atomic_write(SESSION_FILE, payload)
            _save_session.last_payload = payload
    except OSError as exc:
        if not getattr(_save_session, "error_shown", False):
            messagebox.showwarning("Session Restore", f"Could not save your open tabs:\n{exc}")
            _save_session.error_shown = True

def _recovery_path(state, encrypted=None):
    if encrypted is None:
        encrypted = bool(state["path"] and os.path.splitext(state["path"])[1].lower() == ".ntsi")
    extension = ".ntsi" if encrypted else ".txt"
    return os.path.join(get_recovery_dir(), state["recovery_id"] + extension)

def _remove_recovery_draft(state):
    for extension in (".txt", ".ntsi"):
        path = os.path.join(get_recovery_dir(), state["recovery_id"] + extension)
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

def _save_recovery_draft(state):
    content = state["editor"].get("1.0", "end-1c")
    encrypted = bool(state["path"] and os.path.splitext(state["path"])[1].lower() == ".ntsi")
    if encrypted and not state["ntsi_password"]:
        return
    path = _recovery_path(state, encrypted)
    if state.get("recovery_content") == content and os.path.exists(path):
        return
    if encrypted:
        payload = encode_ntsi(content, state["ntsi_password"], state["ntsi_compressed"])
    else:
        payload = content.encode("utf-8")
    _atomic_write(path, payload)
    state["recovery_content"] = content

def _set_document_content(state, content, modified=False):
    editor = state["editor"]
    editor.delete("1.0", "end")
    editor.insert("1.0", content)
    editor.edit_modified(False)
    state["modified"] = modified
    state["recovery_content"] = content if modified else None
    _refresh_document_title(state)
    _refresh_line_counter(editor)
    if editor is text_area:
        _set_active_document()

def _restore_session():
    if not os.path.isfile(SESSION_FILE):
        return
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as stream:
            session = json.load(stream)
        if not isinstance(session, dict):
            raise ValueError("Session data has an invalid format.")
        entries = session.get("documents", [])
        if not isinstance(entries, list) or not entries:
            return
        if not all(isinstance(entry, dict) for entry in entries):
            raise ValueError("Session document data has an invalid format.")
        if not messagebox.askyesno(
            "Restore Session",
            f"Restore {len(entries)} document tab(s) from your previous session?",
        ):
            for entry in entries:
                recovery_id = entry.get("recovery_id")
                if isinstance(recovery_id, str):
                    for extension in (".txt", ".ntsi"):
                        try:
                            os.remove(os.path.join(get_recovery_dir(), recovery_id + extension))
                        except FileNotFoundError:
                            pass
            os.remove(SESSION_FILE)
            return
        for state in list(documents.values()):
            editor_notebook.forget(state["frame"])
            state["frame"].destroy()
            documents.pop(state["editor"], None)
            document_frames.pop(str(state["frame"]), None)
        for entry in entries:
            path = entry.get("path")
            recovery_id = entry.get("recovery_id")
            modified = bool(entry.get("modified"))
            if not isinstance(recovery_id, str):
                continue
            candidate = os.path.join(get_recovery_dir(), recovery_id + ".txt")
            encrypted = False
            if not os.path.isfile(candidate):
                candidate = os.path.join(get_recovery_dir(), recovery_id + ".ntsi")
                encrypted = os.path.isfile(candidate)
            if modified and (os.path.isfile(candidate)):
                try:
                    if encrypted:
                        password = ask_ntsi_password()
                        if password is None:
                            continue
                        with open(candidate, "rb") as stream:
                            data = stream.read()
                        content = decode_ntsi(data, password)
                        compressed = inspect_ntsi(data)["compressed"]
                    else:
                        with open(candidate, "r", encoding="utf-8") as stream:
                            content = stream.read()
                        password = None
                        compressed = False
                    editor = create_document(
                        content, path=path if isinstance(path, str) else None,
                        modified=True, password=password, compressed=compressed,
                        recovery_id=recovery_id, select=False,
                    )
                    documents[editor]["recovery_content"] = content
                    continue
                except (OSError, UnicodeDecodeError, ValueError, zlib.error) as exc:
                    messagebox.showwarning("Session Recovery", f"Could not recover a draft:\n{exc}")
            if isinstance(path, str) and os.path.isfile(path):
                _load_document(path, recovery_id=recovery_id, select=False)
            elif isinstance(path, str):
                messagebox.showwarning("Session Restore", f"File no longer exists:\n{path}")
        if not documents:
            create_document()
        wanted = session.get("selected_recovery_id")
        for editor, state in documents.items():
            if state["recovery_id"] == wanted:
                editor_notebook.select(state["frame"])
                break
        _set_active_document()
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        messagebox.showwarning("Session Restore", f"Could not restore the previous session:\n{exc}")

def _reload_document_from_disk(state):
    path = state["path"]
    try:
        if os.path.splitext(path)[1].lower() == ".ntsi":
            password = state["ntsi_password"] or ask_ntsi_password()
            if password is None:
                return
            with open(path, "rb") as stream:
                data = stream.read()
            content = decode_ntsi(data, password)
            state["ntsi_password"] = password
            state["ntsi_compressed"] = inspect_ntsi(data)["compressed"]
        else:
            with open(path, "r", encoding="utf-8") as stream:
                content = stream.read()
        _set_document_content(state, content)
        state["disk_snapshot"] = _file_snapshot(path)
        state["external_change"] = False
        _remove_recovery_draft(state)
    except (OSError, UnicodeDecodeError, ValueError, zlib.error) as exc:
        messagebox.showerror("Reload Failed", str(exc))

def _check_external_changes():
    for state in list(documents.values()):
        path = state["path"]
        if not path:
            continue
        snapshot = _file_snapshot(path)
        if snapshot == state["disk_snapshot"]:
            continue
        state["disk_snapshot"] = snapshot
        state["external_change"] = True
        if state["modified"]:
            messagebox.showwarning(
                "File Changed on Disk",
                f"{os.path.basename(path)} changed outside PixelScript. Your edits are preserved; saving will ask before overwriting it.",
            )
        elif snapshot is None:
            messagebox.showwarning(
                "File Missing",
                f"{os.path.basename(path)} was removed or is no longer accessible.",
            )
        elif messagebox.askyesno(
            "File Changed on Disk",
            f"{os.path.basename(path)} changed outside PixelScript. Reload it?",
        ):
            _reload_document_from_disk(state)

def _autosave_tick():
    for state in list(documents.values()):
        if state["modified"]:
            try:
                _save_recovery_draft(state)
            except (OSError, ValueError, zlib.error) as exc:
                if not state.get("recovery_error_shown"):
                    messagebox.showwarning("Draft Recovery", f"Could not save a recovery draft:\n{exc}")
                    state["recovery_error_shown"] = True
    _check_external_changes()
    _save_session()
    root.after(2000, _autosave_tick)

def close_document(editor=None):
    editor = editor or text_area
    state = documents.get(editor)
    if state is None:
        return
    if state["modified"]:
        editor_notebook.select(state["frame"])
        _set_active_document()
        choice = messagebox.askyesnocancel(
            "Unsaved Changes", f"Save changes to {_document_title(state).rstrip(' *')}?"
        )
        if choice is None:
            return
        if choice:
            if state["path"]:
                if not _write_document(state):
                    return
            else:
                save_file()
                if state["modified"]:
                    return
    _remove_recovery_draft(state)
    if state["preview"] and state["preview"].winfo_exists():
        state["preview"].destroy()
    editor_notebook.forget(state["frame"])
    state["frame"].destroy()
    documents.pop(editor, None)
    document_frames.pop(str(state["frame"]), None)
    if not documents:
        create_document()
    else:
        _set_active_document()
    _save_session()

def toggle_split_view():
    global split_enabled, split_frame, split_editor, split_line_counter
    if split_enabled:
        workspace.forget(split_frame)
        split_frame.destroy()
        split_enabled = False
        split_editor = None
        split_line_counter = None
        return
    split_frame = tk.Frame(workspace)
    tk.Label(split_frame, text="Read-only split view").pack(side="top", anchor="w")
    split_line_counter = tk.Text(
        split_frame, width=4, padx=4, takefocus=0, border=0, wrap="none",
        background="#f0f0f0", foreground="gray", state="disabled", font=current_font
    )
    split_line_counter.pack(side="left", fill="y")
    split_editor = tk.Text(split_frame, wrap="word", undo=False, font=current_font, state="disabled")
    split_scroll = ttk.Scrollbar(split_frame, orient="vertical", command=split_editor.yview)
    split_editor.configure(yscrollcommand=split_scroll.set)
    split_editor.pack(side="left", fill="both", expand=True)
    split_scroll.pack(side="right", fill="y")
    workspace.add(split_frame)
    split_enabled = True
    _sync_split_view()

def _sync_split_view():
    if not split_enabled or split_editor is None or text_area is None:
        return
    content = text_area.get("1.0", "end-1c")
    split_editor.configure(state="normal")
    split_editor.delete("1.0", "end")
    split_editor.insert("1.0", content)
    split_editor.configure(state="disabled")
    split_line_counter.configure(state="normal")
    split_line_counter.delete("1.0", "end")
    split_line_counter.insert("1.0", "\n".join(str(i) for i in range(1, content.count("\n") + 2)))
    split_line_counter.configure(state="disabled")

class _MarkdownTextRenderer(HTMLParser):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.active_tags = []
        self.ignored_depth = 0
        for level in range(1, 7):
            widget.tag_configure(f"h{level}", font=("Arial", max(12, 24 - level * 2), "bold"), spacing1=10)
        widget.tag_configure("strong", font=("Arial", 12, "bold"))
        widget.tag_configure("em", font=("Arial", 12, "italic"))
        widget.tag_configure("code", font=("Courier New", 10), background="#eeeeee")
        widget.tag_configure("blockquote", foreground="#666666", lmargin1=16, lmargin2=16)

    def handle_starttag(self, tag, attrs):
        if tag in {"head", "style", "title"}:
            self.ignored_depth += 1
            return
        if self.ignored_depth:
            return
        if tag.startswith("h") and len(tag) == 2 and tag[1].isdigit():
            self.active_tags.append(tag)
        elif tag in {"strong", "em", "code", "blockquote"}:
            self.active_tags.append(tag)
        elif tag == "pre":
            self.active_tags.append("code")
        elif tag == "p":
            self._newline()
        elif tag == "li":
            self._newline()
            self.widget.insert("end", "\u2022 ")
        elif tag == "br":
            self._newline()

    def handle_endtag(self, tag):
        if tag in {"head", "style", "title"} and self.ignored_depth:
            self.ignored_depth -= 1
            return
        if self.ignored_depth:
            return
        if tag == "pre":
            self._remove_tag("code")
            self._newline()
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6", "strong", "em", "code", "blockquote"}:
            self._remove_tag(tag)
            if tag.startswith("h") or tag == "blockquote":
                self._newline()
        elif tag in {"p", "ul", "ol"}:
            self._newline()

    def handle_data(self, data):
        if not self.ignored_depth:
            self.widget.insert("end", data, tuple(self.active_tags))

    def _remove_tag(self, tag):
        if tag in self.active_tags:
            self.active_tags.remove(tag)

    def _newline(self):
        if not self.widget.get("1.0", "end-1c").endswith("\n"):
            self.widget.insert("end", "\n")

def _refresh_markdown_preview(state):
    state["preview_after"] = None
    win = state["preview"]
    if not win or not win.winfo_exists():
        return
    source = state["editor"].get("1.0", "end-1c")
    outline = state["outline"]
    children = outline.get_children()
    if children:
        outline.delete(*children)
    for line, heading, level in extract_headings(source):
        outline.insert("", "end", iid=str(line), text=f"{'  ' * (level - 1)}{heading}")
    preview = state["preview_text"]
    preview.configure(state="normal")
    preview.delete("1.0", "end")
    parser = _MarkdownTextRenderer(preview)
    parser.feed(markdown_to_html(source))
    parser.close()
    preview.configure(state="disabled")

def open_markdown_preview():
    if text_area is None:
        return
    state = documents[text_area]
    if state["preview"] and state["preview"].winfo_exists():
        state["preview"].deiconify()
        state["preview"].lift()
        _refresh_markdown_preview(state)
        return
    win = tk.Toplevel(root)
    win.title("Markdown Preview")
    win.geometry("850x600")
    split = tk.PanedWindow(win, orient="horizontal", sashwidth=5, sashrelief="raised")
    split.pack(fill="both", expand=True)
    outline = ttk.Treeview(split, show="tree", selectmode="browse")
    outline.column("#0", width=220, stretch=False)
    preview_frame = tk.Frame(split)
    preview = tk.Text(preview_frame, wrap="word", state="disabled", padx=18, pady=14)
    preview_scroll = ttk.Scrollbar(preview_frame, orient="vertical", command=preview.yview)
    preview.configure(yscrollcommand=preview_scroll.set)
    preview.pack(side="left", fill="both", expand=True)
    preview_scroll.configure(command=preview.yview)
    preview_scroll.pack(side="right", fill="y")
    split.add(outline)
    split.add(preview_frame)
    state["preview"] = win
    state["preview_text"] = preview
    state["outline"] = outline

    def jump_to_heading(event=None):
        selected = outline.selection()
        if selected:
            state["editor"].mark_set("insert", f"{selected[0]}.0")
            state["editor"].see("insert")
            state["editor"].focus_set()

    outline.bind("<<TreeviewSelect>>", jump_to_heading)
    win.protocol("WM_DELETE_WINDOW", lambda s=state, w=win: _close_markdown_preview(s, w))
    style_window(win, current_theme)
    _refresh_markdown_preview(state)

def _close_markdown_preview(state, window):
    if state["preview_after"]:
        root.after_cancel(state["preview_after"])
        state["preview_after"] = None
    state["preview"] = None
    window.destroy()

def export_markdown_html():
    if text_area is None:
        return
    path = filedialog.asksaveasfilename(
        defaultextension=".html",
        filetypes=[("HTML files", "*.html")],
    )
    if not path:
        return
    title = os.path.basename(documents[text_area]["path"] or "Markdown Export")
    try:
        with open(path, "w", encoding="utf-8", newline="") as stream:
            stream.write(markdown_to_html(text_area.get("1.0", "end-1c"), title=title))
    except OSError as exc:
        messagebox.showerror("HTML Export Failed", str(exc))
        return
    messagebox.showinfo("Export Complete", f"Markdown exported to:\n{path}")

def export_markdown_pdf():
    if text_area is None:
        return
    path = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf")],
    )
    if not path:
        return
    try:
        export_pdf(text_area.get("1.0", "end-1c"), path)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        messagebox.showerror("PDF Export Failed", str(exc))
        return
    messagebox.showinfo("Export Complete", f"PDF exported to:\n{path}")

def save_settings(theme, check_beta=None):
    """Save settings to file.
    
    Parameters:
        theme: The theme to save ("light" or "dark")
        check_beta: If provided, save the beta updates preference
    """
    config = configparser.ConfigParser()
    if os.path.exists(SETTINGS_FILE):
        config.read(SETTINGS_FILE)
    
    config["Appearance"] = {"theme": theme}
    
    if check_beta is not None:
        if "Updates" not in config:
            config["Updates"] = {}
        config["Updates"]["check_beta"] = str(check_beta)
    
    with open(SETTINGS_FILE, "w") as f:
        config.write(f)

def apply_theme(theme):
    if theme == "dark":
        root.config(bg="#23272e")
        workspace.config(bg="#23272e")
        menu_bar.config(bg="#23272e", fg="#f8f8f2")
    else:
        root.config(bg="SystemButtonFace")
        workspace.config(bg="SystemButtonFace")
        menu_bar.config(bg="SystemButtonFace", fg="black")
    for state in documents.values():
        _apply_editor_theme(state["editor"], state["line_counter"], theme)
    if split_enabled and split_editor is not None:
        split_editor.config(
            bg="#23272e" if theme == "dark" else "white",
            fg="#f8f8f2" if theme == "dark" else "black",
        )
        split_line_counter.config(
            bg="#23272e" if theme == "dark" else "#f0f0f0",
            fg="#5c6370" if theme == "dark" else "gray",
        )
    for window in root.winfo_children():
        if isinstance(window, tk.Toplevel):
            style_window(window, theme)

def style_window(win, theme):
    if theme == "dark":
        bg = "#23272e"
        fg = "#f8f8f2"
        entry_bg = "#2d323b"
        entry_fg = "#f8f8f2"
        frame_bg = "#2d323b"
        button_bg = "#3a3f4b"
        button_fg = "#f8f8f2"
    else:
        bg = "SystemButtonFace"
        fg = "black"
        entry_bg = "white"
        entry_fg = "black"
        frame_bg = "SystemButtonFace"
        button_bg = "SystemButtonFace"
        button_fg = "black"
    
    win.config(bg=bg)
    
    def apply_to_widget(widget):
        cls = widget.__class__.__name__
        try:
            if cls == "Frame":
                widget.config(bg=bg)
            elif cls == "LabelFrame":
                widget.config(bg=bg, fg=fg)
            elif cls == "Label":
                widget.config(bg=bg, fg=fg)
            elif cls == "Button":
                widget.config(bg=button_bg, fg=button_fg, activebackground=button_bg, activeforeground=button_fg)
            elif cls == "Entry":
                widget.config(bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)
            elif cls == "Text":
                widget.config(bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)
            elif cls == "Listbox":
                # Dark theme list styling
                if theme == "dark":
                    widget.config(bg=entry_bg, fg=entry_fg,
                                  selectbackground="#444b5c", selectforeground=entry_fg,
                                  highlightthickness=1, highlightbackground="#3a3f4b",
                                  activestyle="none")
                else:
                    widget.config(bg="white", fg="black",
                                  selectbackground="#cce0ff", selectforeground="black",
                                  highlightthickness=1, highlightbackground="#c0c0c0",
                                  activestyle="dotbox")
            elif cls == "Radiobutton":
                widget.config(bg=bg, fg=fg, selectcolor=frame_bg, activebackground=bg, activeforeground=fg)
            elif cls == "Checkbutton":
                widget.config(bg=bg, fg=fg, selectcolor=frame_bg, activebackground=bg, activeforeground=fg)
            elif cls == "Scrollbar":
                # Basic scrollbar colors for dark/light
                if theme == "dark":
                    widget.config(bg=bg, activebackground=button_bg, troughcolor=frame_bg, highlightbackground=bg)
                else:
                    widget.config(bg=bg)
        except:
            pass
        
        # Recursively apply to children
        for child in widget.winfo_children():
            apply_to_widget(child)
    
    for widget in win.winfo_children():
        apply_to_widget(widget)

def open_about():
    # About dialog with full-width logo banner and simplified content
    about_win = tk.Toplevel(root)
    about_win.title("About PixelScript+")
    about_win.geometry("520x360")
    about_win.resizable(False, False)

    # Banner across the top with centered logo
    banner = tk.Frame(about_win, padx=0, pady=12)
    banner.pack(fill="x")

    img = None
    try:
        img = tk.PhotoImage(file=resource_path("logo.png"))
    except Exception:
        try:
            img = tk.PhotoImage(file=resource_path("Icon.png"))
        except Exception:
            img = None

    if img is not None:
        # Keep banner slim and reasonably narrow
        try:
            max_w = 420
            max_h = 60
            factor_w = max(1, img.width() // max_w)
            factor_h = max(1, img.height() // max_h)
            factor = max(factor_w, factor_h)
            if factor > 1:
                img = img.subsample(factor, factor)
        except Exception:
            pass
        banner_logo = tk.Label(banner, image=img)
        banner_logo.image = img
        banner_logo.pack(side="top")

    # Body content (no product name, just version + details)
    body = tk.Frame(about_win, padx=16, pady=8)
    body.pack(fill="both", expand=True)

    version_line = tk.Label(body, text=f"Version {CURRENT_VERSION}", font=("Arial", 11))
    version_line.pack(anchor="w", pady=(4, 0))

    try:
        os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
    except Exception:
        os_info = platform.platform()

    info_block = (
        "A tabbed, extendable text and Markdown editor.\n"
        f"Running on: {os_info}\n"
        "\n"
        "© 2026 Riley Northcote. All rights reserved."
    )
    info_label = tk.Label(body, text=info_block, font=("Arial", 10), justify="left", anchor="w")
    info_label.pack(anchor="w", pady=(8, 0))

    # License link row
    def open_license():
        try:
            webbrowser.open("https://github.com/Northy2410/PixelScript-Plus/blob/main/Licence")
        except Exception:
            pass

    link_color = "#4ea1ff" if current_theme == "dark" else "#0645AD"
    lic_row = tk.Frame(body)
    lic_row.pack(anchor="w", pady=(12, 0))
    lic_prefix = tk.Label(lic_row, text="This product is licensed under the ", font=("Arial", 10))
    lic_prefix.pack(side="left")
    lic_link = tk.Label(lic_row, text="PixelScript License Terms", font=("Arial", 10, "underline"), fg=link_color, cursor="hand2")
    lic_link.pack(side="left")
    lic_link.bind("<Button-1>", lambda e: open_license())

    # Bottom buttons (OK only)
    bottom = tk.Frame(about_win, padx=16, pady=8)
    bottom.pack(fill="x")
    ok_btn = tk.Button(bottom, text="OK", width=12, command=about_win.destroy)
    ok_btn.pack(side="right")

    # Keyboard: Enter/Esc to close
    about_win.bind("<Return>", lambda e: about_win.destroy())
    about_win.bind("<Escape>", lambda e: about_win.destroy())

    style_window(about_win, current_theme)
    # Re-apply link color after theming
    try:
        lic_link.config(fg=link_color)
    except Exception:
        pass

def open_help():
    help_win = tk.Toplevel(root)
    help_win.title("help")
    help_win.geometry("480x160")
    help_win.resizable(False, False)

    help_msg = (
        "to report an issue or suggest a feature, click the new issue button after being redirected to the webpage using the button below."
    )
    msg = tk.Label(help_win, text=help_msg, font=("Arial", 12), wraplength=440, justify="center")
    msg.pack(pady=12)

    def open_issues():
        webbrowser.open("https://github.com/Northy2410/PixelScript-Plus/issues")

    issue_btn = tk.Button(help_win, text="Redirect me", command=open_issues, font=("Arial", 11), width=14)
    issue_btn.pack(pady=4)

    close_btn = tk.Button(help_win, text="Close", command=help_win.destroy, font=("Arial", 11), width=14)
    close_btn.pack(pady=4)

    style_window(help_win, current_theme)


def open_wiki():
    try:
        webbrowser.open("https://github.com/Northy2410/PixelScript-Plus/wiki")
    except Exception:
        try:
            messagebox.showerror("Open Wiki", "Unable to open the wiki in your default browser.")
        except Exception:
            pass

def open_settings():
    settings_win = tk.Toplevel(root)
    settings_win.title("Settings - PixelScript+")
    settings_win.geometry("520x480")
    settings_win.resizable(False, False)

    theme_var = tk.StringVar(value=current_theme)
    beta_var = tk.BooleanVar(value=load_beta_updates_setting())

    # Header
    header = tk.Frame(settings_win, height=60)
    header.pack(fill="x")
    header_label = tk.Label(header, text="⚙ Settings", font=("Arial", 18, "bold"))
    header_label.pack(pady=15)

    # Separator
    separator1 = tk.Frame(settings_win, height=2, bd=1, relief="sunken")
    separator1.pack(fill="x", padx=15, pady=5)

    # Main scrollable frame
    main_frame = tk.Frame(settings_win, padx=25, pady=10)
    main_frame.pack(fill="both", expand=True)

    # Appearance Section
    appearance_section = tk.LabelFrame(main_frame, text=" Appearance ", font=("Arial", 11, "bold"), 
                                       padx=15, pady=12, relief="groove", bd=2)
    appearance_section.pack(fill="x", pady=(5, 12))

    theme_label = tk.Label(appearance_section, text="Theme:", font=("Arial", 10))
    theme_label.grid(row=0, column=0, sticky="w", pady=5)

    theme_frame = tk.Frame(appearance_section)
    theme_frame.grid(row=1, column=0, sticky="w", padx=10)
    
    light_rb = tk.Radiobutton(theme_frame, text="☀ Light", variable=theme_var, value="light", 
                              font=("Arial", 10), padx=8, pady=4)
    light_rb.pack(side="left", padx=5)
    
    dark_rb = tk.Radiobutton(theme_frame, text="🌙 Dark", variable=theme_var, value="dark", 
                             font=("Arial", 10), padx=8, pady=4)
    dark_rb.pack(side="left", padx=5)

    # Updates Section
    updates_section = tk.LabelFrame(main_frame, text=" Updates ", font=("Arial", 11, "bold"),
                                    padx=15, pady=12, relief="groove", bd=2)
    updates_section.pack(fill="x", pady=(0, 12))
    
    beta_check = tk.Checkbutton(updates_section, text="Check for Beta/Pre-release versions", 
                                variable=beta_var, font=("Arial", 10))
    beta_check.grid(row=0, column=0, sticky="w", pady=5)
    
    beta_hint = tk.Label(updates_section, text="Enable to receive early access to new features", 
                        font=("Arial", 9, "italic"), fg="gray")
    beta_hint.grid(row=1, column=0, sticky="w", padx=20)

    # Quick Actions Section
    actions_section = tk.LabelFrame(main_frame, text=" Quick Actions ", font=("Arial", 11, "bold"),
                                    padx=15, pady=12, relief="groove", bd=2)
    actions_section.pack(fill="x", pady=(0, 12))

    # Row 1: Check for Updates + Save Settings (side by side)
    actions_row1 = tk.Frame(actions_section)
    actions_row1.pack(fill="x")

    def _save_only():
        # Save and close the settings window
        save_and_apply()

    update_btn = tk.Button(actions_row1, text="🔄 Check for Updates",
                           command=lambda: check_for_update(parent=settings_win),
                           font=("Arial", 10), width=22, pady=5)
    update_btn.grid(row=0, column=0, padx=5, pady=4, sticky="w")

    quick_save_btn = tk.Button(actions_row1, text="💾 Save Settings",
                               command=_save_only,
                               font=("Arial", 10), width=22, pady=5)
    quick_save_btn.grid(row=0, column=1, padx=5, pady=4, sticky="e")

    # Row 2: Plugins + About (side by side)
    actions_row2 = tk.Frame(actions_section)
    actions_row2.pack(fill="x")

    plugins_btn = tk.Button(actions_row2, text="🔌 Installed Plugins",
                            command=show_installed_plugins,
                            font=("Arial", 10), width=22, pady=5)
    plugins_btn.grid(row=0, column=0, padx=5, pady=4, sticky="w")

    about_btn = tk.Button(actions_row2, text="ℹ About", command=open_about,
                          font=("Arial", 10), width=22, pady=5)
    about_btn.grid(row=0, column=1, padx=5, pady=4, sticky="e")

    # Status line
    status_var = tk.StringVar(value="")
    status_lbl = tk.Label(actions_section, textvariable=status_var, font=("Arial", 9, "italic"))
    status_lbl.pack(anchor="w", padx=6, pady=(2, 0))

    # Bottom Separator
    separator2 = tk.Frame(settings_win, height=2, bd=1, relief="sunken")
    separator2.pack(fill="x", padx=15, pady=5)

    # Bottom buttons
    button_frame = tk.Frame(settings_win, pady=10)
    button_frame.pack(fill="x", padx=25)

    def save_and_apply():
        global current_theme
        current_theme = theme_var.get()
        save_settings(current_theme, beta_var.get())
        apply_theme(current_theme)
        settings_win.destroy()

    cancel_btn = tk.Button(button_frame, text="Cancel", command=settings_win.destroy, 
                          font=("Arial", 10, "bold"), width=15, pady=6)
    cancel_btn.pack(side="right", padx=5)

    save_btn = tk.Button(button_frame, text="💾 Save & Apply", command=save_and_apply, 
                        font=("Arial", 10, "bold"), width=15, pady=6, 
                        relief="solid", bd=2)
    save_btn.pack(side="right", padx=5)

    style_window(settings_win, current_theme)

menu_bar = tk.Menu(root)

file_menu = tk.Menu(menu_bar, tearoff=0)
file_menu.add_command(label="New (Ctrl+N)", command=new_file)
file_menu.add_command(label="Open (Ctrl+O)", command=open_file)
file_menu.add_command(label="Save (Ctrl+S)", command=save_file)
file_menu.add_command(label="Save As (Ctrl+Shift+S)", command=save_as_file)
file_menu.add_command(label="Save As Markdown...", command=save_as_markdown_file)
file_menu.add_command(label="Close Tab (Ctrl+W)", command=close_document)
recent_menu = tk.Menu(file_menu, tearoff=0)
file_menu.add_cascade(label="Open Recent", menu=recent_menu)
file_menu.add_separator()
file_menu.add_command(label="Exit", command=on_closing)
menu_bar.add_cascade(label="File", menu=file_menu)

view_menu = tk.Menu(menu_bar, tearoff=0)
view_menu.add_command(label="Toggle Split View", command=toggle_split_view)
menu_bar.add_cascade(label="View", menu=view_menu)

markdown_menu = tk.Menu(menu_bar, tearoff=0)
markdown_menu.add_command(label="Live Preview", command=open_markdown_preview)
markdown_menu.add_separator()
markdown_menu.add_command(label="Export as HTML", command=export_markdown_html)
markdown_menu.add_command(label="Export as PDF", command=export_markdown_pdf)
menu_bar.add_cascade(label="Markdown", menu=markdown_menu)

edit_menu = tk.Menu(menu_bar, tearoff=0)

font_menu = tk.Menu(edit_menu, tearoff=0)
for family in ["Arial", "Courier", "Times New Roman", "Verdana"]:
    font_menu.add_command(label=family, command=lambda f=family: set_font_family(f))

size_menu = tk.Menu(edit_menu, tearoff=0)
for size in [10, 12, 14, 16, 18, 20, 24]:
    size_menu.add_command(label=str(size), command=lambda s=size: set_font_size(s))

edit_menu.add_cascade(label="Font Family", menu=font_menu)
edit_menu.add_cascade(label="Font Size", menu=size_menu)
edit_menu.add_command(label="Bold", command=toggle_bold)
edit_menu.add_command(label="Italic", command=toggle_italic)
menu_bar.add_cascade(label="Edit", menu=edit_menu)

maths_menu = tk.Menu(menu_bar, tearoff=0)
maths_menu.add_command(label="Calculator", command=open_calculator)
menu_bar.add_cascade(label="Maths", menu=maths_menu)

utilities_menu = tk.Menu(menu_bar, tearoff=0)
utilities_menu.add_command(label="Calendar", command=open_calendar)
menu_bar.add_cascade(label="Utilities", menu=utilities_menu)

settings_menu = tk.Menu(menu_bar, tearoff=0)
settings_menu.add_command(label="Settings", command=open_settings)
menu_bar.add_cascade(label="Settings", menu=settings_menu)

help_menu = tk.Menu(menu_bar, tearoff=0)
help_menu.add_command(label="Wiki", command=open_wiki)
help_menu.add_command(label="Submit an issue or feature", command=open_help)
menu_bar.add_cascade(label="Help", menu=help_menu)

root.config(menu=menu_bar)

current_theme = load_settings()
editor_notebook.bind("<<NotebookTabChanged>>", _set_active_document)
create_document()
apply_theme(current_theme)
_load_recent_files()
_refresh_recent_menu()
_restore_session()
apply_theme(current_theme)
root.after(2000, _autosave_tick)


# --- Plugin system -------------------------------------------------
class PluginManager:
    """Simple plugin manager that loads Python modules from a plugins folder.

    Plugins should be single .py files and expose a `register(api)` function.
    """
    def __init__(self, plugins_dir, api):
        self.plugins_dir = plugins_dir
        self.api = api
        self.plugins = []

    def discover(self):
        files = []
        try:
            for fname in os.listdir(self.plugins_dir):
                if fname.endswith('.py') and not fname.startswith('_'):
                    files.append(os.path.join(self.plugins_dir, fname))
        except Exception as e:
            print('Plugin discovery failed:', e)
        return files

    def load_plugins(self):
        for path in self.discover():
            name = os.path.splitext(os.path.basename(path))[0]
            try:
                spec = importlib.util.spec_from_file_location(f'pixelscript_plugin_{name}', path)
                if spec is None or spec.loader is None:
                    raise ImportError(f'Invalid spec for {path}')
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, 'register') and callable(module.register):
                    try:
                        module.register(self.api)
                        # collect metadata if provided by plugin
                        plugin_name = getattr(module, 'PLUGIN_NAME', name)
                        plugin_author = getattr(module, 'PLUGIN_AUTHOR', 'Unknown')
                        plugin_version = getattr(module, 'PLUGIN_VERSION', '')
                        info = {
                            'module': module,
                            'file': path,
                            'id': name,
                            'name': plugin_name,
                            'author': plugin_author,
                            'version': plugin_version,
                        }
                        self.plugins.append(info)
                        print(f"Loaded plugin: {plugin_name} (id={name})")
                    except Exception:
                        traceback.print_exc()
                        try:
                            messagebox.showerror('Plugin Error', f"Plugin '{name}' raised an exception during register(). See console for details.")
                        except Exception:
                            pass
                else:
                    print(f"Skipping {name}: no register(api) function found")
            except Exception:
                traceback.print_exc()
                try:
                    messagebox.showerror('Plugin Load Error', f"Failed to load plugin '{name}'. See console for details.")
                except Exception:
                    pass


# Small helper plugin API utilities
def _add_menu(name):
    m = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label=name, menu=m)
    return m

# Public API passed to plugins
PLUGIN_API = {
    'root': root,
    'text_area': text_area,
    'get_active_text_area': lambda: text_area,
    'menu_bar': menu_bar,
    'add_menu': _add_menu,
    'resource_path': resource_path,
    'open_file': open_file,
    'save_file': save_file,
    'save_as_file': save_as_file,
    'show_message': lambda title, msg: messagebox.showinfo(title, msg),
}


def show_installed_plugins():
    """Open a window listing installed plugins and their metadata."""
    win = tk.Toplevel(root)
    win.title("Installed Plugins")
    win.geometry("420x350")
    win.resizable(False, False)

    frame = tk.Frame(win, padx=10, pady=10)
    frame.pack(fill="both", expand=True)

    listbox = tk.Listbox(frame, width=60, height=10)
    listbox.pack(side="top", fill="both", expand=False)

    note_label = tk.Label(frame, text="Note: Restart PixelScript to refresh and apply plugin changes.", fg="gray", anchor="w", justify="left", wraplength=380)
    note_label.pack(side="top", pady=(6, 6), fill="x")

    details = tk.Label(frame, text="Select a plugin to see details", anchor="w", justify="left", wraplength=380)
    details.pack(side="top", pady=(8, 0), fill="x")

    plugins = getattr(plugin_manager, 'plugins', [])
    for idx, p in enumerate(plugins):
        display = f"{p.get('name', p.get('id'))} — {p.get('author', 'Unknown')}"
        listbox.insert(tk.END, display)

    def on_select(evt):
        sel = listbox.curselection()
        if not sel:
            return
        i = sel[0]
        p = plugins[i]
        txt = f"Name: {p.get('name')}\nDeveloper: {p.get('author')}\nID: {p.get('id')}"
        if p.get('version'):
            txt += f"\nVersion: {p.get('version')}"
        details.config(text=txt)

    listbox.bind('<<ListboxSelect>>', on_select)

    def uninstall_selected():
        sel = listbox.curselection()
        if not sel:
            messagebox.showwarning('No Selection', 'Please select a plugin to uninstall.')
            return
        i = sel[0]
        p = plugins[i]
        name = p.get('name') or p.get('id')
        if not messagebox.askyesno('Confirm Uninstall', f"Uninstall plugin '{name}'? This will delete the plugin file from the plugins folder."):
            return
        # Attempt to call unregister if provided
        try:
            module = p.get('module')
            if module and hasattr(module, 'unregister') and callable(module.unregister):
                try:
                    module.unregister(PLUGIN_API)
                except Exception:
                    traceback.print_exc()
        except Exception:
            traceback.print_exc()

        # Safely remove file only if it's inside plugins dir
        path = p.get('file')
        try:
            abs_path = os.path.abspath(path)
            abs_plugins = os.path.abspath(PLUGINS_DIR)
            common = os.path.commonpath([abs_path, abs_plugins])
            if common != abs_plugins:
                raise PermissionError('Plugin file is outside the plugins directory; aborting delete.')
            os.remove(abs_path)
        except Exception as e:
            traceback.print_exc()
            try:
                messagebox.showerror('Uninstall Failed', f"Could not remove plugin file: {e}")
            except Exception:
                pass
            return

        # Remove from internal list and UI
        try:
            del plugins[i]
            listbox.delete(i)
            details.config(text='Plugin uninstalled.')
            messagebox.showinfo('Uninstalled', f"Plugin '{name}' was uninstalled. Please restart PixelScript to refresh and apply changes.")
        except Exception:
            traceback.print_exc()

    uninstall_btn = tk.Button(frame, text="Uninstall", width=12, command=uninstall_selected)
    uninstall_btn.pack(side="right", padx=(0,6), pady=8)

    close_btn = tk.Button(frame, text="Close", width=12, command=win.destroy)
    close_btn.pack(side="right", pady=8)

    style_window(win, current_theme)

PLUGINS_DIR = get_plugins_dir()
plugin_manager = PluginManager(PLUGINS_DIR, PLUGIN_API)
try:
    plugin_manager.load_plugins()
except Exception:
    traceback.print_exc()

# --------------------
# Keyboard shortcuts
# --------------------
def _bind_shortcuts():
    # Handlers accept an optional event arg from tkinter
    def _save(event=None):
        try:
            save_file()
        except Exception:
            traceback.print_exc()
        return "break"

    def _save_as(event=None):
        try:
            save_as_file()
        except Exception:
            traceback.print_exc()
        return "break"

    def _open(event=None):
        try:
            open_file()
        except Exception:
            traceback.print_exc()
        return "break"

    def _new(event=None):
        try:
            new_file()
        except Exception:
            traceback.print_exc()
        return "break"

    def _close(event=None):
        close_document()
        return "break"

    def _markdown_preview(event=None):
        open_markdown_preview()
        return "break"

    # Bind for Control on Windows/Linux and Command on macOS where appropriate
    root.bind_all('<Control-s>', _save)
    root.bind_all('<Control-Shift-S>', _save_as)
    root.bind_all('<Control-o>', _open)
    root.bind_all('<Control-n>', _new)
    root.bind_all('<Control-w>', _close)
    root.bind_all('<Control-Shift-m>', _markdown_preview)
    try:
        if platform.system() == 'Darwin':
            root.bind_all('<Command-s>', _save)
            root.bind_all('<Command-Shift-S>', _save_as)
            root.bind_all('<Command-o>', _open)
            root.bind_all('<Command-n>', _new)
            root.bind_all('<Command-w>', _close)
            root.bind_all('<Command-Shift-m>', _markdown_preview)
    except Exception:
        pass


_bind_shortcuts()

root.mainloop()
