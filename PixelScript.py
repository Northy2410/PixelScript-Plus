import tkinter as tk
from tkinter import filedialog, messagebox, font
import sys
import os
import requests
import webbrowser
import calendar
from datetime import datetime
import configparser
import platform
import importlib.util
import traceback

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
root.geometry("600x400")
root.iconphoto(True, tk.PhotoImage(file=resource_path("Icon.png")))

text_frame = tk.Frame(root)
text_frame.pack(fill="both", expand=True)

line_counter = tk.Text(
    text_frame, width=4, padx=4, takefocus=0, border=0,
    background="#f0f0f0", foreground="gray", state="disabled", font=current_font
)
line_counter.pack(side="left", fill="y")

text_area = tk.Text(text_frame, wrap="word", undo=True, font=current_font)
text_area.pack(side="left", fill="both", expand=True)

def update_line_counter(event=None):
    text = text_area.get("1.0", "end-1c")
    lines = text.count("\n") + 1
    line_numbers = "\n".join(str(i) for i in range(1, lines + 1))
    line_counter.config(state="normal")
    line_counter.delete("1.0", "end")
    line_counter.insert("1.0", line_numbers)
    line_counter.config(state="disabled")

text_area.bind("<KeyRelease>", update_line_counter)
text_area.bind("<MouseWheel>", update_line_counter)
text_area.bind("<ButtonRelease-1>", update_line_counter)
text_area.bind("<<Change>>", update_line_counter)
text_area.bind("<Configure>", update_line_counter)
update_line_counter()

# Github info
OWNER = "Northy2410"
REPO = "PixelScript-Plus"
CURRENT_VERSION = "1.6"

# update check (manual invocation)
def check_for_update(parent=None, silent=False):
    """Check GitHub for the latest release.

    Parameters:
        parent: optional window to associate dialogs with.
        silent (bool): if True suppress info/error dialogs when no update or failure.
    """
    # Load beta updates preference
    check_beta = load_beta_updates_setting()
    
    if check_beta:
        # Get all releases including pre-releases
        url = "https://api.github.com/repos/northy2410/pixelscript-plus/releases"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            releases = response.json()
            # Filter to get the latest release (including pre-releases)
            if not releases:
                raise Exception("No releases found")
            latest_release = releases[0]  # GitHub returns releases sorted by date
        except Exception as e:
            if not silent:
                fail_win = tk.Toplevel(root if parent is None else parent)
                fail_win.title("Update Check Failed")
                fail_win.geometry("360x160")
                fail_win.resizable(False, False)
                fail_win.attributes("-topmost", True)
                msg = tk.Label(
                    fail_win,
                    text=f"Could not check for updates.\n\n{e}",
                    font=("Arial", 12), justify="center"
                )
                msg.pack(pady=18)
                btn = tk.Button(
                    fail_win,
                    text="OK",
                    command=fail_win.destroy,
                    font=("Arial", 11)
                )
                btn.pack(pady=5)
                style_window(fail_win, current_theme)
            return
    else:
        # Get only stable releases
        url = "https://api.github.com/repos/northy2410/pixelscript-plus/releases/latest"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            latest_release = response.json()
        except Exception as e:
            if not silent:
                fail_win = tk.Toplevel(root if parent is None else parent)
                fail_win.title("Update Check Failed")
                fail_win.geometry("360x160")
                fail_win.resizable(False, False)
                fail_win.attributes("-topmost", True)
                msg = tk.Label(
                    fail_win,
                    text=f"Could not check for updates.\n\n{e}",
                    font=("Arial", 12), justify="center"
                )
                msg.pack(pady=18)
                btn = tk.Button(
                    fail_win,
                    text="OK",
                    command=fail_win.destroy,
                    font=("Arial", 11)
                )
                btn.pack(pady=5)
                style_window(fail_win, current_theme)
            return
    
    try:
        latest_version = latest_release.get("tag_name", "").lstrip("vV")
        is_prerelease = latest_release.get("prerelease", False)
        if latest_version and latest_version != CURRENT_VERSION:
            def open_release():
                webbrowser.open(latest_release['html_url'])
                update_win.destroy()
            update_win = tk.Toplevel(root if parent is None else parent)
            update_win.title("Update Available")
            update_win.geometry("360x190")
            update_win.resizable(False, False)
            update_win.attributes("-topmost", True)
            
            version_type = " (Beta)" if is_prerelease else ""
            msg = tk.Label(
                update_win,
                text=f"A new version is available!\n\nLatest: {latest_version}{version_type}\nCurrent: {CURRENT_VERSION}",
                font=("Arial", 12), justify="center"
            )
            msg.pack(pady=15)
            btn = tk.Button(
                update_win,
                text="Open Release Page",
                command=open_release,
                font=("Arial", 11)
            )
            btn.pack(pady=5)
            style_window(update_win, current_theme)
        else:
            if not silent:
                up_win = tk.Toplevel(root if parent is None else parent)
                up_win.title("Up To Date")
                up_win.geometry("360x140")
                up_win.resizable(False, False)
                up_win.attributes("-topmost", True)
                msg = tk.Label(
                    up_win,
                    text=f"You're on the latest version (v{CURRENT_VERSION}).",
                    font=("Arial", 12), justify="center"
                )
                msg.pack(pady=25)
                btn = tk.Button(
                    up_win,
                    text="OK",
                    command=up_win.destroy,
                    font=("Arial", 11)
                )
                btn.pack(pady=5)
                style_window(up_win, current_theme)
    except Exception as e:
        if not silent:
            fail_win = tk.Toplevel(root if parent is None else parent)
            fail_win.title("Update Check Failed")
            fail_win.geometry("360x160")
            fail_win.resizable(False, False)
            fail_win.attributes("-topmost", True)
            msg = tk.Label(
                fail_win,
                text=f"Could not check for updates.\n\n{e}",
                font=("Arial", 12), justify="center"
            )
            msg.pack(pady=18)
            btn = tk.Button(
                fail_win,
                text="OK",
                command=fail_win.destroy,
                font=("Arial", 11)
            )
            btn.pack(pady=5)
            style_window(fail_win, current_theme)

unsaved_changes = False
current_file_path = None

def on_text_modified(event=None):
    global unsaved_changes
    unsaved_changes = text_area.edit_modified()
    text_area.edit_modified(False)

text_area.bind("<<Modified>>", on_text_modified)

def on_closing():
    if unsaved_changes:
        if messagebox.askyesno("Unsaved Changes", "You have unsaved changes. Do you want to exit without saving?"):
            root.destroy()
    else:
        root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

def new_file():
    global unsaved_changes, current_file_path
    text_area.delete(1.0, tk.END)
    unsaved_changes = False
    current_file_path = None
    root.title("PixelScript+")
    update_line_counter()

def open_file():
    global unsaved_changes, current_file_path
    file = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
    if file:
        with open(file, "r", encoding="utf-8") as f:
            text_area.delete(1.0, tk.END)
            text_area.insert(tk.END, f.read())
        unsaved_changes = False
        current_file_path = file
        root.title(f"PixelScript+ - {os.path.basename(file)}")
        update_line_counter()

def save_file():
    """Save to current file, or prompt for filename if no file is open."""
    global unsaved_changes, current_file_path
    if current_file_path:
        # Save to existing file
        with open(current_file_path, "w", encoding="utf-8") as f:
            f.write(text_area.get(1.0, tk.END))
        unsaved_changes = False
        messagebox.showinfo("Saved", "File saved successfully!")
    else:
        # No file open, use Save As
        save_as_file()

def save_as_file():
    """Always prompt for a new filename to save to."""
    global unsaved_changes, current_file_path
    file = filedialog.asksaveasfilename(defaultextension=".txt",
                                        filetypes=[("Text Files", "*.txt")])
    if file:
        with open(file, "w", encoding="utf-8") as f:
            f.write(text_area.get(1.0, tk.END))
        unsaved_changes = False
        current_file_path = file
        root.title(f"PixelScript+ - {os.path.basename(file)}")
        messagebox.showinfo("Saved", "File saved successfully!")

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
        text_area.config(bg="#23272e", fg="#f8f8f2", insertbackground="#f8f8f2")
        menu_bar.config(bg="#23272e", fg="#f8f8f2")
        line_counter.config(bg="#23272e", fg="#5c6370")
    else:
        root.config(bg="SystemButtonFace")
        text_area.config(bg="white", fg="black", insertbackground="black")
        menu_bar.config(bg="SystemButtonFace", fg="black")
        line_counter.config(bg="#f0f0f0", fg="gray")

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
        "A simple, extendable text editor.\n"
        f"Running on: {os_info}\n"
        "\n"
        "© 2025 Riley Northcote. All rights reserved."
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


def open_website():
    try:
        webbrowser.open("https://pixelscriptplus.co.uk")
    except Exception:
        try:
            messagebox.showerror("Open Website", "Unable to open the website in your default browser.")
        except Exception:
            pass


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
file_menu.add_separator()
file_menu.add_command(label="Exit", command=on_closing)
menu_bar.add_cascade(label="File", menu=file_menu)

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
help_menu.add_command(label="Website", command=open_website)
help_menu.add_command(label="Wiki", command=open_wiki)
help_menu.add_command(label="Submit an issue or feature", command=open_help)
menu_bar.add_cascade(label="Help", menu=help_menu)

root.config(menu=menu_bar)

current_theme = load_settings()
apply_theme(current_theme)


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

    # Bind for Control on Windows/Linux and Command on macOS where appropriate
    root.bind_all('<Control-s>', _save)
    root.bind_all('<Control-Shift-S>', _save_as)
    root.bind_all('<Control-o>', _open)
    root.bind_all('<Control-n>', _new)
    try:
        if platform.system() == 'Darwin':
            root.bind_all('<Command-s>', _save)
            root.bind_all('<Command-Shift-S>', _save_as)
            root.bind_all('<Command-o>', _open)
            root.bind_all('<Command-n>', _new)
    except Exception:
        pass


_bind_shortcuts()

root.mainloop()
