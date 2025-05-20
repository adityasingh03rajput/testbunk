import tkinter as tk
from tkinter import messagebox
import json
import os
import ctypes
import subprocess
import socket
import threading
from datetime import datetime

# File to store user data
USER_FILE = "users.json"

# Server configuration
HOST = "192.168.115.174"  # Change to server IP if different
PORT = 65432

# Connect to the server
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))

# Load existing users from the file
def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as file:
            return json.load(file)
    return {}

# Save users to the file
def save_users(users):
    with open(USER_FILE, "w") as file:
        json.dump(users, file, indent=4)

# Function to send data to server
def send_data(action, username=None, status=None):
    try:
        data = {"action": action, "username": username, "status": status}
        client_socket.send(json.dumps(data).encode("utf-8"))
    except (ConnectionError, OSError) as e:
        messagebox.showerror("Connection Error", f"Failed to send data: {e}")

# Signup function
def signup():
    username = entry_username.get()
    password = entry_password.get()

    if not username or not password:
        messagebox.showwarning("Input Error", "Please fill in all fields.")
        return

    users = load_users()
    if username in users:
        messagebox.showwarning("Signup Error", "Username already exists.")
        return

    users[username] = password
    save_users(users)
    messagebox.showinfo("Signup Success", "Signup successful!")
    clear_entries()

# Login function
def login():
    username = entry_username.get()
    password = entry_password.get()

    if not username or not password:
        messagebox.showwarning("Input Error", "Please fill in all fields.")
        return

    users = load_users()
    if username in users and users[username] == password:
        messagebox.showinfo("Login Success", "Login successful!")
        clear_entries()
        root.destroy()  # Close the login window
        send_data("login", username, "student")  # Notify server of login
        start_attendance_timer(username)  # Launch the attendance timer
    else:
        messagebox.showerror("Login Failed", "Invalid username or password.")
        clear_entries()

# Clear input fields
def clear_entries():
    entry_username.delete(0, tk.END)
    entry_password.delete(0, tk.END)

# Hide the console window (Windows only)
if os.name == 'nt':
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# Authorized Wi-Fi BSSID
AUTHORIZED_BSSID = "4a:63:34:a7:f6:a8"

# Function to check Wi-Fi connection
def check_wifi_connection():
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            if "BSSID" in line:
                bssid = ":".join(line.split(":")[1:]).strip().lower()
                if bssid == AUTHORIZED_BSSID.lower():
                    return True
    except Exception as e:
        messagebox.showerror("Error", f"Error checking Wi-Fi status: {e}")
    return False

# Global timer variables
timer = 10  # 10 seconds for demo (change to actual duration)
timer_started = False

# Function to update the timer
def update_timer(username):
    global timer, timer_started
    if timer_started:
        if timer > 0:
            if check_wifi_connection():
                timer_label.config(text=f"Time remaining: {timer} seconds")
                timer -= 1
                root_attend.after(1000, update_timer, username)
            else:
                timer_label.config(text="Unauthorized Wi-Fi! Timer paused.", fg="red")
                # Send left time when WiFi disconnects
                left_time = datetime.now().strftime("%I:%M %p")
                send_data("left", username, left_time)
                check_wifi_reconnect(username)
        else:
            timer_label.config(text="Time's up! Attendance Marked.", fg="green")
            messagebox.showinfo("Attendance", "You are now marked as present.")
            timer_started = False
            start_button.config(state=tk.NORMAL)
            send_data("mark_present", username, "present")

# Function to check Wi-Fi reconnection
def check_wifi_reconnect(username):
    if not check_wifi_connection():
        root_attend.after(1000, check_wifi_reconnect, username)
    else:
        timer_label.config(text="Authorized Wi-Fi reconnected! Resuming timer.", fg="blue")
        update_timer(username)

# Function to start the timer
def start_timer(username):
    global timer, timer_started
    timer = 10  # Reset the timer (change to desired duration)
    timer_started = True
    start_button.config(state=tk.DISABLED)
    send_data("mark_present", username, "present")  # Immediately mark as present when timer starts
    update_timer(username)

# Function to start the attendance timer system
def start_attendance_timer(username):
    global root_attend, timer_label, start_button

    root_attend = tk.Tk()
    root_attend.title("Attendance Timer")
    root_attend.geometry("400x250")
    root_attend.resizable(False, False)

    title_label = tk.Label(root_attend, text="Attendance Timer 🕒", font=("Arial", 18, "bold"))
    title_label.pack(pady=10)

    instructions_label = tk.Label(
        root_attend,
        text="Click 'Start Timer' to begin. The timer will only run if you're connected to the authorized Wi-Fi.",
        wraplength=350,
        font=("Arial", 10)
    )
    instructions_label.pack(pady=10)

    timer_label = tk.Label(root_attend, text="", font=("Arial", 14))
    timer_label.pack(pady=20)

    start_button = tk.Button(
        root_attend,
        text="Start Timer",
        command=lambda: start_timer(username),
        font=("Arial", 12),
        bg="#4CAF50",
        fg="white",
        padx=20,
        pady=10
    )
    start_button.pack(pady=10)

    root_attend.mainloop()

# Function to handle server messages
def receive_messages():
    while True:
        try:
            data = client_socket.recv(1024).decode("utf-8")
            if not data:
                break
            # Handle server messages if needed
        except:
            break

# Start the receive thread
threading.Thread(target=receive_messages, daemon=True).start()

# Create the main login window
root = tk.Tk()
root.title("Signup and Login System")
root.geometry("300x200")

# Username Label and Entry
label_username = tk.Label(root, text="Username:")
label_username.pack(pady=5)
entry_username = tk.Entry(root)
entry_username.pack(pady=5)

# Password Label and Entry
label_password = tk.Label(root, text="Password:")
label_password.pack(pady=5)
entry_password = tk.Entry(root, show="*")
entry_password.pack(pady=5)

# Signup Button
button_signup = tk.Button(root, text="Signup", command=signup)
button_signup.pack(pady=10)

# Login Button
button_login = tk.Button(root, text="Login", command=login)
button_login.pack(pady=10)

# Close socket when application exits
def on_closing():
    client_socket.close()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()
