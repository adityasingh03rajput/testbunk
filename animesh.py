import tkinter as tk
from tkinter import messagebox
import json
import os
import ctypes
import socket
import threading
from datetime import datetime
import requests
import platform

# File to store user data
USER_FILE = "users.json"

# Server configuration
SERVER_URL = "https://deadball.onrender.com"  # Change to your server URL

# Connection settings
PING_INTERVAL = 30

class AttendanceSystem:
    def __init__(self):
        self.users = self.load_users()
        self.username = None
        self.current_wifi = None
        self.setup_wifi_checker()

    def load_users(self):
        if os.path.exists(USER_FILE):
            with open(USER_FILE, "r") as file:
                return json.load(file)
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
        except requests.RequestException as e:
            print(f"Connection error: {e}")

    def setup_wifi_checker(self):
        """Setup WiFi checker based on OS"""
        self.os_type = platform.system()
        if self.os_type == "Windows":
            self.check_wifi = self._check_wifi_windows
        elif self.os_type == "Linux":
            self.check_wifi = self._check_wifi_linux
        else:
            self.check_wifi = lambda: True  # Default to True for unsupported OS

    def _check_wifi_windows(self):
        try:
            import subprocess
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True, text=True
            )
            for line in result.stdout.splitlines():
                if "SSID" in line and not "BSSID" in line:
                    self.current_wifi = line.split(":")[1].strip()
                    return True
            return False
        except:
            return False

    def _check_wifi_linux(self):
        try:
            import subprocess
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
        self.root.mainloop()

    def setup_login_ui(self):
        self.root.title("Student Login")
        self.root.geometry("300x200")
        
        tk.Label(self.root, text="Username:").pack(pady=5)
        self.entry_username = tk.Entry(self.root)
        self.entry_username.pack(pady=5)
        
        tk.Label(self.root, text="Password:").pack(pady=5)
        self.entry_password = tk.Entry(self.root, show="*")
        self.entry_password.pack(pady=5)
        
        tk.Button(self.root, text="Login", command=self.login).pack(pady=10)

    def login(self):
        username = self.entry_username.get()
        password = self.entry_password.get()
        
        if not username or not password:
            messagebox.showwarning("Error", "Please enter both username and password")
            return
            
        if username in self.system.users and self.system.users[username] == password:
            messagebox.showinfo("Login Success", "Login successful!")
            self.system.username = username
            self.root.destroy()
            self.system.send_data("login", username)
            self.start_attendance_timer()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")

    def start_ping_thread(self):
        def ping():
            while True:
                if self.system.username:
                    self.system.send_data("ping", self.system.username)
                threading.Event().wait(PING_INTERVAL)
        
        threading.Thread(target=ping, daemon=True).start()

    def start_attendance_timer(self):
        self.attendance_window = tk.Tk()
        self.attendance_window.title("Attendance Timer")
        self.attendance_window.geometry("400x300")
        
        # Status label
        self.status_label = tk.Label(
            self.attendance_window,
            text="Status: Not Connected",
            font=("Arial", 12)
        )
        self.status_label.pack(pady=10)
        
        # Ring notification
        self.ring_label = tk.Label(
            self.attendance_window,
            text="",
            font=("Arial", 12),
            fg="red"
        )
        self.ring_label.pack(pady=10)
        
        # Start ring check thread
        threading.Thread(target=self.check_rings, daemon=True).start()
        
        # Timer UI
        self.timer_label = tk.Label(
            self.attendance_window,
            text="Click 'Start Attendance' to begin",
            font=("Arial", 14)
        )
        self.timer_label.pack(pady=20)
        
        self.start_button = tk.Button(
            self.attendance_window,
            text="Start Attendance",
            command=self.start_timer,
            font=("Arial", 12),
            bg="#4CAF50",
            fg="white",
            padx=20,
            pady=10
        )
        self.start_button.pack(pady=10)
        
        # Start WiFi check thread
        threading.Thread(target=self.check_wifi_status, daemon=True).start()
        
        self.attendance_window.mainloop()

    def start_timer(self):
        if not self.system.check_wifi():
            messagebox.showwarning("No WiFi", "Please connect to WiFi first")
            return
            
        self.timer = 10  # 10 seconds for demo
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
                                text=f"RANDOM RING ALERT!\nPlease mark attendance now!",
                                fg="red"
                            )
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

def hide_console():
    if os.name == 'nt':
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

if __name__ == "__main__":
    hide_console()
    system = AttendanceSystem()
    StudentClient(system)
