import tkinter as tk
from tkinter import messagebox
import json
import os
import ctypes
import threading
import requests
import platform
import subprocess

# Server configuration
SERVER_URL = "https://deadball.onrender.com"
PING_INTERVAL = 30
USER_FILE = "users.json"

class AttendanceSystem:
    def __init__(self):
        self.users = self.load_users()
        self.username = None
        self.current_wifi = None
        self.setup_wifi_checker()

    def load_users(self):
        if os.path.exists(USER_FILE):
            try:
                with open(USER_FILE, "r") as file:
                    return json.load(file)
            except:
                return {}
        return {}

    def save_users(self):
        with open(USER_FILE, "w") as file:
            json.dump(self.users, file, indent=4)

    def send_data(self, action, username=None, status=None):
        try:
            if action == "ping":
                requests.post(
                    f"{SERVER_URL}/ping",
                    json={"type": "students", "username": username},
                    timeout=5
                )
            elif action == "attendance":
                requests.post(
                    f"{SERVER_URL}/attendance",
                    json={"username": username, "status": status},
                    timeout=5
                )
            elif action == "left":
                requests.post(
                    f"{SERVER_URL}/attendance",
                    json={"username": username, "status": "left"},
                    timeout=5
                )
            elif action == "login":
                requests.post(
                    f"{SERVER_URL}/ping",
                    json={"type": "students", "username": username},
                    timeout=5
                )
        except requests.RequestException:
            pass

    def setup_wifi_checker(self):
        self.os_type = platform.system()
        if self.os_type == "Windows":
            self.check_wifi = self._check_wifi_windows
        elif self.os_type == "Linux":
            self.check_wifi = self._check_wifi_linux
        else:
            self.check_wifi = lambda: True

    def _check_wifi_windows(self):
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in result.stdout.splitlines():
                if "SSID" in line and "BSSID" not in line:
                    self.current_wifi = line.split(":")[1].strip()
                    return True
            return False
        except:
            return False

    def _check_wifi_linux(self):
        try:
            result = subprocess.run(
                ["iwgetid", "-r"],
                capture_output=True, text=True
            )
            self.current_wifi = result.stdout.strip()
            return bool(self.current_wifi)
        except:
            return False

class StudentClient:
    def __init__(self, system):
        self.system = system
        self.root = tk.Tk()
        self.setup_login_ui()
        self.start_ping_thread()
        self.hide_console()
        self.root.mainloop()

    def hide_console(self):
        if os.name == 'nt':
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

    def setup_login_ui(self):
        self.root.title("Student Portal")
        self.root.geometry("350x300")
        self.root.resizable(False, False)
        
        # Main frame
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(expand=True)
        
        # Title
        tk.Label(main_frame, text="Student Portal", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        # Username
        tk.Label(main_frame, text="Username:").grid(row=1, column=0, sticky="e", pady=5)
        self.entry_username = tk.Entry(main_frame)
        self.entry_username.grid(row=1, column=1, pady=5, ipadx=20)
        
        # Password
        tk.Label(main_frame, text="Password:").grid(row=2, column=0, sticky="e", pady=5)
        self.entry_password = tk.Entry(main_frame, show="*")
        self.entry_password.grid(row=2, column=1, pady=5, ipadx=20)
        
        # Buttons
        btn_frame = tk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=15)
        
        tk.Button(btn_frame, text="Login", command=self.login, width=10, bg="#4CAF50", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Sign Up", command=self.show_signup, width=10, bg="#2196F3", fg="white").pack(side="left", padx=5)

    def show_signup(self):
        self.signup_window = tk.Toplevel(self.root)
        self.signup_window.title("Sign Up")
        self.signup_window.geometry("350x300")
        self.signup_window.resizable(False, False)
        
        # Main frame
        main_frame = tk.Frame(self.signup_window, padx=20, pady=20)
        main_frame.pack(expand=True)
        
        tk.Label(main_frame, text="Create New Account", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        tk.Label(main_frame, text="Username:").grid(row=1, column=0, sticky="e", pady=5)
        self.signup_username = tk.Entry(main_frame)
        self.signup_username.grid(row=1, column=1, pady=5, ipadx=20)
        
        tk.Label(main_frame, text="Password:").grid(row=2, column=0, sticky="e", pady=5)
        self.signup_password = tk.Entry(main_frame, show="*")
        self.signup_password.grid(row=2, column=1, pady=5, ipadx=20)
        
        tk.Label(main_frame, text="Confirm Password:").grid(row=3, column=0, sticky="e", pady=5)
        self.signup_confirm_password = tk.Entry(main_frame, show="*")
        self.signup_confirm_password.grid(row=3, column=1, pady=5, ipadx=20)
        
        tk.Button(main_frame, text="Register", command=self.signup, bg="#4CAF50", fg="white", width=15).grid(row=4, column=0, columnspan=2, pady=15)

    def signup(self):
        username = self.signup_username.get()
        password = self.signup_password.get()
        confirm_password = self.signup_confirm_password.get()
        
        if not username or not password or not confirm_password:
            messagebox.showwarning("Error", "Please fill all fields")
            return
            
        if password != confirm_password:
            messagebox.showerror("Error", "Passwords don't match")
            return
            
        if username in self.system.users:
            messagebox.showerror("Error", "Username already exists")
            return
            
        self.system.users[username] = password
        self.system.save_users()
        messagebox.showinfo("Success", "Account created successfully!")
        self.signup_window.destroy()

    def login(self):
        username = self.entry_username.get()
        password = self.entry_password.get()
        
        if not username or not password:
            messagebox.showwarning("Error", "Please enter both username and password")
            return
            
        if username in self.system.users and self.system.users[username] == password:
            messagebox.showinfo("Success", "Login successful!")
            self.system.username = username
            self.root.destroy()
            self.system.send_data("login", username)
            self.start_attendance_timer()
        else:
            messagebox.showerror("Error", "Invalid username or password")

    def start_ping_thread(self):
        def ping():
            while True:
                if self.system.username:
                    self.system.send_data("ping", self.system.username)
                threading.Event().wait(PING_INTERVAL)
        
        threading.Thread(target=ping, daemon=True).start()

    def start_attendance_timer(self):
        self.attendance_window = tk.Tk()
        self.attendance_window.title("Attendance System")
        self.attendance_window.geometry("500x400")
        self.attendance_window.resizable(False, False)
        
        # Status frame
        status_frame = tk.Frame(self.attendance_window, padx=10, pady=10)
        status_frame.pack(fill="x")
        
        self.status_label = tk.Label(
            status_frame,
            text="Status: Not Connected",
            font=("Arial", 10),
            anchor="w"
        )
        self.status_label.pack(fill="x")
        
        # Notification frame
        notification_frame = tk.Frame(self.attendance_window, padx=10, pady=5)
        notification_frame.pack(fill="x")
        
        self.ring_label = tk.Label(
            notification_frame,
            text="",
            font=("Arial", 10, "bold"),
            fg="red",
            anchor="w"
        )
        self.ring_label.pack(fill="x")
        
        # Timer frame
        timer_frame = tk.Frame(self.attendance_window, padx=20, pady=20)
        timer_frame.pack(expand=True)
        
        self.timer_label = tk.Label(
            timer_frame,
            text="Click 'Start Attendance' to begin",
            font=("Arial", 14),
            pady=20
        )
        self.timer_label.pack()
        
        self.start_button = tk.Button(
            timer_frame,
            text="Start Attendance",
            command=self.start_timer,
            font=("Arial", 12),
            bg="#4CAF50",
            fg="white",
            padx=20,
            pady=10
        )
        self.start_button.pack(pady=20)
        
        # Start threads
        threading.Thread(target=self.check_rings, daemon=True).start()
        threading.Thread(target=self.check_wifi_status, daemon=True).start()
        
        self.attendance_window.mainloop()

    def start_timer(self):
        if not self.system.check_wifi():
            messagebox.showwarning("No WiFi", "Please connect to WiFi first")
            return
            
        self.timer = 120  # 10 seconds for demo
        self.timer_started = True
        self.start_button.config(state=tk.DISABLED)
        self.system.send_data("attendance", self.system.username, "present")
        self.update_timer()

    def update_timer(self):
        if self.timer_started and self.timer > 0:
            if self.system.check_wifi():
                self.timer_label.config(text=f"Time remaining: {self.timer} seconds")
                self.timer -= 1
                self.attendance_window.after(1000, self.update_timer)
            else:
                self.timer_label.config(text="WiFi disconnected! Timer paused.", fg="red")
                self.system.send_data("left", self.system.username)
                self.check_wifi_reconnect()
        elif self.timer_started:
            self.timer_label.config(text="Attendance Marked Successfully!", fg="green")
            self.timer_started = False
            self.start_button.config(state=tk.NORMAL)

    def check_wifi_reconnect(self):
        if not self.system.check_wifi():
            self.attendance_window.after(1000, self.check_wifi_reconnect)
        else:
            self.timer_label.config(text="WiFi reconnected! Resuming timer.", fg="blue")
            self.update_timer()

    def check_rings(self):
        last_ring = ""
        while True:
            try:
                response = requests.get(f"{SERVER_URL}/get_attendance", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('last_ring') != last_ring:
                        last_ring = data.get('last_ring')
                        ring_students = data.get('ring_students', [])
                        if self.system.username in ring_students:
                            self.ring_label.config(
                                text="RANDOM RING ALERT! Please mark attendance now!",
                                fg="red"
                            )
                            self.attendance_window.bell()  # System beep
            except:
                pass
            threading.Event().wait(10)

    def check_wifi_status(self):
        while True:
            if self.system.check_wifi():
                self.status_label.config(
                    text=f"Status: Connected to {self.system.current_wifi}",
                    fg="green"
                )
            else:
                self.status_label.config(
                    text="Status: Not Connected to WiFi",
                    fg="red"
                )
            threading.Event().wait(5)

if __name__ == "__main__":
    system = AttendanceSystem()
    StudentClient(system)
