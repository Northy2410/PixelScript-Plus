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
CURRENT_VERSION = "1.4"

# update check (manual invocation)
def check_for_update(parent=None, silent=False):
    """Check GitHub for the latest release.

    Parameters:
        parent: optional window to associate dialogs with.
        silent (bool): if True suppress info/error dialogs when no update or failure.
    """
    url = "https://api.github.com/repos/northy2410/pixelscript-plus/releases/latest"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        latest_release = response.json()
        latest_version = latest_release.get("tag_name", "").lstrip("vV")
        if latest_version and latest_version != CURRENT_VERSION:
            def open_release():
                webbrowser.open(latest_release['html_url'])
                update_win.destroy()
            update_win = tk.Toplevel(root if parent is None else parent)
            update_win.title("Update Available")
            update_win.geometry("360x170")
            update_win.resizable(False, False)
            update_win.attributes("-topmost", True)
            msg = tk.Label(
                update_win,
                text=f"A new version is available!\n\nLatest: {latest_version}\nCurrent: {CURRENT_VERSION}",
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
    global unsaved_changes
    text_area.delete(1.0, tk.END)
    unsaved_changes = False
    update_line_counter()

def open_file():
    global unsaved_changes
    file = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
    if file:
        with open(file, "r", encoding="utf-8") as f:
            text_area.delete(1.0, tk.END)
            text_area.insert(tk.END, f.read())
        unsaved_changes = False
        update_line_counter()

def save_file():
    global unsaved_changes
    file = filedialog.asksaveasfilename(defaultextension=".txt",
                                        filetypes=[("Text Files", "*.txt")])
    if file:
        with open(file, "w", encoding="utf-8") as f:
            f.write(text_area.get(1.0, tk.END))
        unsaved_changes = False
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

SETTINGS_FILE = get_settings_path()

def load_settings():
    config = configparser.ConfigParser()
    if os.path.exists(SETTINGS_FILE):
        config.read(SETTINGS_FILE)
        return config.get("Appearance", "theme", fallback="light")
    return "light"

def save_settings(theme):
    config = configparser.ConfigParser()
    config["Appearance"] = {"theme": theme}
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
    else:
        bg = "SystemButtonFace"
        fg = "black"
        entry_bg = "white"
        entry_fg = "black"
    win.config(bg=bg)
    for widget in win.winfo_children():
        cls = widget.__class__.__name__
        if cls in ("Frame", "LabelFrame"):
            widget.config(bg=bg)
            for child in widget.winfo_children():
                if child.__class__.__name__ == "Label":
                    child.config(bg=bg, fg=fg)
                elif child.__class__.__name__ == "Button":
                    child.config(bg=bg, fg=fg, activebackground=bg, activeforeground=fg)
                elif child.__class__.__name__ == "Entry":
                    child.config(bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)
                elif child.__class__.__name__ == "Radiobutton":
                    child.config(bg=bg, fg=fg, selectcolor=bg, activebackground=bg, activeforeground=fg)
        elif cls == "Label":
            widget.config(bg=bg, fg=fg)
        elif cls == "Button":
            widget.config(bg=bg, fg=fg, activebackground=bg, activeforeground=fg)
        elif cls == "Entry":
            widget.config(bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)
        elif cls == "Radiobutton":
            widget.config(bg=bg, fg=fg, selectcolor=bg, activebackground=bg, activeforeground=fg)

def open_about():
    about_win = tk.Toplevel(root)
    about_win.title("About PixelScript+")
    about_win.geometry("500x400")  # Increased window size
    about_win.resizable(False, False)

    logo_img = tk.PhotoImage(file=resource_path("Icon.png"))
    logo_label = tk.Label(about_win, image=logo_img, bg=about_win.cget("bg"))
    logo_label.image = logo_img  # keep a reference
    logo_label.pack(pady=15)

    info_text = (
        "PixelScript+\n"
        f"Version: {CURRENT_VERSION}\n"
        "A simple, extendable text editor.\n"
        "© 2025 Riley Northcote."
    )
    info_label = tk.Label(about_win, text=info_text, font=("Arial", 14), justify="center")
    info_label.pack(pady=8)

    license_text = "License: Proprietary"
    license_label = tk.Label(about_win, text=license_text, font=("Arial", 12))
    license_label.pack(pady=15)

    close_btn = tk.Button(about_win, text="Close", command=about_win.destroy)
    close_btn.pack(pady=10)

    style_window(about_win, current_theme)

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

def open_settings():
    settings_win = tk.Toplevel(root)
    settings_win.title("Settings")
    settings_win.geometry("350x260")
    settings_win.resizable(False, False)

    theme_var = tk.StringVar(value=current_theme)

    main_frame = tk.Frame(settings_win, padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)

    theme_label = tk.Label(main_frame, text="Theme:", font=("Arial", 12, "bold"))
    theme_label.grid(row=0, column=0, sticky="w", pady=(0, 5))

    theme_frame = tk.Frame(main_frame)
    theme_frame.grid(row=1, column=0, sticky="w")
    tk.Radiobutton(theme_frame, text="Light", variable=theme_var, value="light").pack(side="left", padx=5)
    tk.Radiobutton(theme_frame, text="Dark", variable=theme_var, value="dark").pack(side="left", padx=5)

    future_label = tk.Label(main_frame, text="(More settings coming soon...)", font=("Arial", 10, "italic"), fg="gray")
    future_label.grid(row=2, column=0, sticky="w", pady=(20, 0))

    def save_and_apply():
        global current_theme
        current_theme = theme_var.get()
        save_settings(current_theme)
        apply_theme(current_theme)
        settings_win.destroy()


    save_btn = tk.Button(main_frame, text="Save", command=save_and_apply, width=16)
    save_btn.grid(row=3, column=0, pady=(15, 0), sticky="w")

    update_btn = tk.Button(main_frame, text="Check for Updates", command=lambda: check_for_update(parent=settings_win), width=16)
    update_btn.grid(row=4, column=0, pady=(8, 0), sticky="w")

    about_btn = tk.Button(main_frame, text="About", command=open_about, width=16)
    about_btn.grid(row=5, column=0, pady=(10, 0), sticky="w")

    style_window(settings_win, current_theme)

menu_bar = tk.Menu(root)

file_menu = tk.Menu(menu_bar, tearoff=0)
file_menu.add_command(label="New", command=new_file)
file_menu.add_command(label="Open", command=open_file)
file_menu.add_command(label="Save", command=save_file)
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
help_menu.add_command(label="Submit an issue or feature", command=open_help)
menu_bar.add_cascade(label="Help", menu=help_menu)

root.config(menu=menu_bar)

current_theme = load_settings()
apply_theme(current_theme)

root.mainloop()
