import tkinter as tk
from tkinter import Menu, simpledialog
import win32gui
import win32process
import win32api
import time
import threading
import os
import sys
from PIL import Image, ImageTk  # For image support

# ---------------- CONFIG FILE ----------------
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)  # folder of .exe
else:
    base_path = os.path.dirname(os.path.abspath(__file__))  # folder of script

CONFIG_FILE = os.path.join(base_path, "app_data.txt")

# Ensure the config file exists
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as f:
        for key in ["Program 1", "Program 2", "Program 3"]:
            f.write(f"{key}=\n")
        f.write("Last time: 00:00:00\n")
        f.write("Timeout: 10.0\n")


# ---------------- WINDOWS UTILITIES ----------------
def get_active_window_title():
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        return title, hwnd
    except Exception:
        return None, None


def get_window_pid(hwnd):
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return pid
    except Exception:
        return None


def capture_next_window(callback):
    time.sleep(0.3)
    initial = get_active_window_title()[0]
    while True:
        current_title, current_hwnd = get_active_window_title()
        if current_title != initial and current_title != "":
            callback(current_title, current_hwnd)
            break
        time.sleep(0.1)


# ---------------- APP CLASS ----------------
class App:
    def __init__(self):
        self.win = tk.Tk()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)

        # Dragging
        self.win.bind("<ButtonPress-1>", self.start_move)
        self.win.bind("<ButtonRelease-1>", self.stop_move)
        self.win.bind("<B1-Motion>", self.do_move)

        # State
        self.is_active = False
        self.seconds = 0
        self.linked = {"Program 1": None, "Program 2": None, "Program 3": None}
        self.timeout = 10.0  # default inactivity timeout

        # Layout
        self.white_bar_height = 25
        self.timer_height = 35
        self.bottom_frame_height = 185
        self.window_width = 185

        # Activity tracking
        self.last_input_time = time.time()
        self.last_mouse_pos = win32api.GetCursorPos()

        # Load previous data
        self.load_config()

        # Build UI
        self.build_window()

        # Start loops
        self.update_timer()
        self.win.after(200, self.monitor_active_window)

        # Handle close
        self.win.protocol("WM_DELETE_WINDOW", self.on_close)
        self.win.mainloop()

    # ---------------- BUILD UI ----------------
    def build_window(self):
        total_height = self.white_bar_height + self.timer_height
        self.win.geometry(f"{self.window_width}x{total_height}")
        self.win.config(bg="#F07070")

        # White top bar
        self.white_bar = tk.Frame(self.win, width=self.window_width,
                                  height=self.white_bar_height, bg="white")
        self.white_bar.place(x=0, y=0)

        self.back_label = tk.Label(self.white_bar, text="BACK TO WORK",
                                   bg="white", fg="black", font=("Segoe UI", 9))
        self.back_label.place(relx=0.5, y=self.white_bar_height // 2,
                              anchor="center")

        # Close button
        self.close_btn = tk.Label(self.white_bar, text="✕", bg="white",
                                  fg="#a2a2a2", font=("Courier New", 11),
                                  width=3, height=2, cursor="hand2")
        self.close_btn.place(x=self.window_width - 30, y=-6.15)
        self.close_btn.bind("<Enter>",
                            lambda e: self.close_btn.config(bg="red",
                                                             fg="white"))
        self.close_btn.bind("<Leave>",
                            lambda e: self.close_btn.config(bg="white",
                                                             fg="#a2a2a2"))
        self.close_btn.bind("<Button-1>",
                            lambda e: self.on_close())

        # Timer label
        self.timer_label = tk.Label(self.win, text=self.format_time(self.seconds),
                                    font=("Courier New", 20, "bold"),
                                    bg="#F07070")
        self.timer_label.place(relx=0.375,
                               y=self.white_bar_height + self.timer_height // 2 + 1,
                               anchor="center")

        # Bottom inactive frame
        self.bottom_frame = tk.Frame(self.win, width=self.window_width,
                                     height=self.bottom_frame_height,
                                     bg="#D3D3D3")
        self.bottom_frame.place(x=0,
                                y=self.white_bar_height + self.timer_height)
        self.bottom_frame.lower()

        # PERFECT-FIT IMAGE (external maia.png)
        try:
            image_path = os.path.join(base_path, "maia.png")
            img = Image.open(image_path)
            self.original_img = img
            self.inactive_img = ImageTk.PhotoImage(img)
            self.image_label = tk.Label(self.bottom_frame, image=self.inactive_img, bd=0)
            self.image_label.place(relx=0, rely=0, relwidth=1, relheight=1)

            def resize_image(event=None):
                w = self.bottom_frame.winfo_width()
                h = self.bottom_frame.winfo_height()
                resized = self.original_img.resize((w, h), Image.Resampling.LANCZOS)
                self.inactive_img = ImageTk.PhotoImage(resized)
                self.image_label.config(image=self.inactive_img)

            self.bottom_frame.bind("<Configure>", resize_image)

        except Exception as e:
            print("Failed to load maia.png:", e)

        # MENU
        self.menu_button = tk.Menubutton(self.win, text="MENU",
                                         relief=tk.RAISED,
                                         font=("Courier New", 9, "bold"),
                                         bg="#e1e1e1")
        self.menu_button.place(relx=0.87,
                               y=self.white_bar_height + self.timer_height // 2 + 1,
                               anchor="center",
                               width=45, height=20)

        self.menu = tk.Menu(self.menu_button, tearoff=False)
        self.menu_button.config(menu=self.menu)

        # Menu options
        self.menu.add_command(label="Resume Previous Time",
                              command=self.resume_previous_time)

        # Program entries
        self.program_menu_indices = {}
        for idx, key in enumerate(self.linked.keys()):
            label = f"{key}: {self.get_window_name(self.linked[key])}"
            self.menu.add_command(label=label,
                                  command=lambda k=key: self.set_link_window(k))
            self.program_menu_indices[key] = idx + 2  # +2: Resume Previous Time

        # RESET TIMER at end
        self.menu.add_command(label="Reset Timer",
                              command=self.reset_timer)

        # Center on screen
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        self.win.geometry(f"{self.window_width}x{total_height}+"
                          f"{sw // 2 - self.window_width // 2}+"
                          f"{sh // 2 - total_height // 2}")

    # ---------------- DRAGGING ----------------
    def start_move(self, event):
        self._x = event.x
        self._y = event.y

    def stop_move(self, event):
        self._x = None
        self._y = None

    def do_move(self, event):
        if self._x is None or self._y is None:
            return
        x = self.win.winfo_x() + (event.x - self._x)
        y = self.win.winfo_y() + (event.y - self._y)
        self.win.geometry(f"+{x}+{y}")

    # ---------------- TIMER ----------------
    def update_timer(self):
        if self.is_active:
            self.seconds += 1
            self.timer_label.config(text=self.format_time(self.seconds))
        self.win.after(1000, self.update_timer)

    def format_time(self, sec):
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    # ---------------- LINKED WINDOWS ----------------
    def set_link_window(self, program_name):
        thread = threading.Thread(target=capture_next_window,
                                  args=(lambda title, hwnd:
                                        self.store_link(program_name, hwnd),))
        thread.daemon = True
        thread.start()

    def store_link(self, program_name, hwnd):
        pid = get_window_pid(hwnd)
        if pid:
            self.linked[program_name] = pid
            new_label = f"{program_name}: {win32gui.GetWindowText(hwnd)}"
            idx = self.program_menu_indices[program_name]
            self.menu.entryconfig(idx, label=new_label)

    def get_window_name(self, pid):
        if pid is None:
            return "None"

        def enum_windows(hwnd, result):
            _, win_pid = win32process.GetWindowThreadProcessId(hwnd)
            if win_pid == pid and win32gui.IsWindowVisible(hwnd):
                result.append(win32gui.GetWindowText(hwnd))

        titles = []
        win32gui.EnumWindows(enum_windows, titles)
        return titles[0] if titles else "Unknown"

    # ---------------- MONITOR ----------------
    def monitor_active_window(self):
        active_title, active_hwnd = get_active_window_title()
        active_pid = get_window_pid(active_hwnd)

        if active_pid in self.linked.values():
            if self.detect_user_activity(active_hwnd):
                self.handle_active()
            else:
                self.handle_inactive(timeout_check=True)
        else:
            self.handle_inactive(timeout_check=True)

        self.win.after(200, self.monitor_active_window)

    def detect_user_activity(self, hwnd):
        now = time.time()
        for vk in range(0x08, 0xFF):
            if win32api.GetAsyncKeyState(vk) & 0x8000:
                self.last_input_time = now
                return True

        x, y = win32api.GetCursorPos()
        if (x, y) != self.last_mouse_pos:
            window_under_cursor = win32gui.WindowFromPoint((x, y))
            if (window_under_cursor == hwnd or
                    win32gui.IsChild(hwnd, window_under_cursor)):
                self.last_input_time = now
                self.last_mouse_pos = (x, y)
                return True

        if now - self.last_input_time < self.timeout:
            return True

        return False

    # ---------------- ACTIVE/INACTIVE ----------------
    def handle_active(self):
        if not self.is_active:
            self.is_active = True
            self.win.config(bg="#B0FFFF")
            self.timer_label.config(bg="#B0FFFF")
            self.back_label.config(text="KEEP WORKING")
            self.bottom_frame.lower()
            self.win.geometry(f"{self.window_width}x"
                              f"{self.white_bar_height + self.timer_height}")

    def handle_inactive(self, timeout_check=False):
        if self.is_active or timeout_check:
            self.is_active = False
            self.win.config(bg="#F07070")
            self.timer_label.config(bg="#F07070")
            self.back_label.config(text="BACK TO WORK")
            total_height = (self.white_bar_height + self.timer_height +
                            self.bottom_frame_height)
            self.bottom_frame.lift()
            self.win.geometry(f"{self.window_width}x{total_height}")

    # ---------------- RESUME TIME ----------------
    def resume_previous_time(self):
        last_time_sec = self.load_last_time()
        if last_time_sec is not None:
            self.seconds = last_time_sec
            self.timer_label.config(text=self.format_time(self.seconds))

    # ---------------- RESET TIMER ----------------
    def reset_timer(self):
        self.seconds = 0
        self.timer_label.config(text=self.format_time(self.seconds))

    # ---------------- LOAD CONFIG ----------------
    def load_config(self):
        self.last_time = 0
        if not os.path.exists(CONFIG_FILE):
            return

        with open(CONFIG_FILE, "r") as f:
            lines = f.read().splitlines()

        for line in lines:
            if line.startswith("Program"):
                key, pid = line.split("=")
                pid = pid.strip()
                self.linked[key.strip()] = int(pid) if pid.isdigit() else None
            elif line.startswith("Last time:"):
                text = line.split(":", 1)[1].strip()
                try:
                    h, m, s = map(int, text.split(":"))
                    self.last_time = h * 3600 + m * 60 + s
                except:
                    self.last_time = 0

    def load_last_time(self):
        return getattr(self, "last_time", 0)

    # ---------------- SAVE CONFIG ----------------
    def on_close(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                for key, pid in self.linked.items():
                    f.write(f"{key}={pid if pid else ''}\n")
                f.write(f"Last time: {self.format_time(self.seconds)}\n")
                f.write(f"Timeout: {self.timeout}\n")
        except Exception as e:
            print("Error saving config:", e)
        self.win.destroy()


# ---------------- RUN ----------------
if __name__ == "__main__":
    App()
