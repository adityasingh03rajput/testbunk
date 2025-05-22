import json
import logging
import time
import threading
from websocket import WebSocketApp, WebSocketConnectionClosedException
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
import subprocess
import platform
import sys

# Configuration
SERVER_WS_URL = "ws://your-server-public-ip:5000/ws"  # Replace with your server's public IP/domain
HEARTBEAT_INTERVAL = 25  # seconds
RECONNECT_DELAY = 5  # seconds
WIFI_CHECK_INTERVAL = 10  # seconds

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('student_client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class StudentClient:
    def __init__(self):
        self.ws = None
        self.connected = False
        self.username = None
        self.password = None
        self.role = None
        self.stop_event = threading.Event()
        self.wifi_thread = None
        self.heartbeat_thread = None
        self.reconnect_thread = None
        self.last_wifi_state = None
        
        # Setup GUI
        self.root = tk.Tk()
        self.root.title("Student Attendance System")
        self.setup_login_gui()
        
        # Start connection manager
        self.connection_manager_thread = threading.Thread(target=self.connection_manager, daemon=True)
        self.connection_manager_thread.start()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def setup_login_gui(self):
        self.root.geometry("350x250")
        
        # Main frame
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(pady=20)
        
        # Title
        tk.Label(self.main_frame, text="Student Portal", font=("Arial", 16)).grid(row=0, column=0, columnspan=2, pady=10)
        
        # Username
        tk.Label(self.main_frame, text="Username:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.entry_username = tk.Entry(self.main_frame)
        self.entry_username.grid(row=1, column=1, padx=5, pady=5)
        
        # Password
        tk.Label(self.main_frame, text="Password:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.entry_password = tk.Entry(self.main_frame, show="*")
        self.entry_password.grid(row=2, column=1, padx=5, pady=5)
        
        # Buttons
        self.btn_frame = tk.Frame(self.main_frame)
        self.btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        tk.Button(self.btn_frame, text="Login", command=self.login).pack(side="left", padx=5)
        tk.Button(self.btn_frame, text="Sign Up", command=self.signup).pack(side="left", padx=5)
        
        # Status label
        self.status_label = tk.Label(self.root, text="Not connected", fg="red")
        self.status_label.pack(pady=5)

    def setup_attendance_gui(self):
        # Clear the window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.root.geometry("400x350")
        
        # Title
        tk.Label(self.root, text="Attendance System", font=("Arial", 16)).pack(pady=10)
        
        # Connection status
        self.connection_status = tk.Label(self.root, text="", font=("Arial", 10))
        self.connection_status.pack(pady=5)
        
        # Wifi status
        self.wifi_status = tk.Label(self.root, text="", font=("Arial", 10))
        self.wifi_status.pack(pady=5)
        
        # Attendance status
        self.attendance_status = tk.Label(self.root, text="Status: Not marked", font=("Arial", 12))
        self.attendance_status.pack(pady=10)
        
        # Last seen
        self.last_seen_label = tk.Label(self.root, text="Last seen: Never", font=("Arial", 10))
        self.last_seen_label.pack(pady=5)
        
        # Mark attendance button
        self.mark_btn = tk.Button(self.root, text="Mark Attendance", 
                                command=self.mark_attendance,
                                state=tk.NORMAL)
        self.mark_btn.pack(pady=20)
        
        # Messages frame
        self.messages_frame = tk.Frame(self.root)
        self.messages_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(self.messages_frame, text="Messages:").pack(anchor="w")
        self.messages_text = tk.Text(self.messages_frame, height=4, state=tk.DISABLED)
        self.messages_text.pack(fill=tk.BOTH, expand=True)
        
        # Start updating status
        self.update_ui_status()

    def update_ui_status(self):
        # Update connection status
        if self.connected:
            self.connection_status.config(text="Connected to server", fg="green")
        else:
            self.connection_status.config(text="Disconnected from server", fg="red")
        
        # Update wifi status
        wifi_connected = self.check_wifi_connection()
        if wifi_connected:
            self.wifi_status.config(text="On campus network", fg="green")
        else:
            self.wifi_status.config(text="Off campus network", fg="red")
        
        self.root.after(1000, self.update_ui_status)

    def check_wifi_connection(self):
        """Check if connected to authorized WiFi (platform specific)"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(["netsh", "wlan", "show", "interfaces"], 
                                      capture_output=True, text=True)
                return "Your-SSID" in result.stdout  # Replace with your SSID
            elif platform.system() == "Linux":
                result = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True)
                return "Your-SSID" in result.stdout.strip()
            elif platform.system() == "Darwin":
                result = subprocess.run(["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-I"], 
                                      capture_output=True, text=True)
                return "Your-SSID" in result.stdout
            return False
        except Exception:
            return False

    def on_ws_open(self, ws):
        logger.info("WebSocket connection opened")
        self.connected = True
        self.status_label.config(text="Connected", fg="green")
        
        # Authenticate
        auth_msg = {
            "type": "auth",
            "username": self.username,
            "password": self.password
        }
        self.ws.send(json.dumps(auth_msg))
        
        # Start heartbeat
        self.start_heartbeat()

    def on_ws_close(self, ws, close_status_code, close_msg):
        logger.info(f"WebSocket connection closed: {close_status_code} - {close_msg}")
        self.connected = False
        self.status_label.config(text="Disconnected", fg="red")
        
        # Stop heartbeat
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=1)
        
        # Try to reconnect
        if not self.stop_event.is_set():
            self.schedule_reconnect()

    def on_ws_message(self, ws, message):
        try:
            data = json.loads(message)
            logger.debug(f"Received message: {data}")
            
            if data.get("type") == "auth_ack":
                if data.get("status") == "success":
                    self.role = "student"
                    self.setup_attendance_gui()
                else:
                    messagebox.showerror("Error", "Authentication failed")
            
            elif data.get("type") == "notification":
                self.show_message(data.get("from", "Teacher"), data.get("message", ""))
            
        except json.JSONDecodeError:
            logger.error("Invalid JSON message received")

    def on_ws_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")
        self.connected = False
        self.status_label.config(text="Connection error", fg="red")

    def connection_manager(self):
        while not self.stop_event.is_set():
            if self.username and not self.connected and not self.reconnect_thread:
                self.schedule_reconnect()
            time.sleep(1)

    def schedule_reconnect(self):
        if not self.reconnect_thread or not self.reconnect_thread.is_alive():
            self.reconnect_thread = threading.Thread(target=self.reconnect, daemon=True)
            self.reconnect_thread.start()

    def reconnect(self):
        while not self.connected and not self.stop_event.is_set():
            logger.info("Attempting to reconnect...")
            try:
                self.connect_websocket()
                # Wait for connection to establish or fail
                time.sleep(2)
                if not self.connected:
                    time.sleep(RECONNECT_DELAY)
            except Exception as e:
                logger.error(f"Reconnect attempt failed: {e}")
                time.sleep(RECONNECT_DELAY)

    def connect_websocket(self):
        try:
            self.ws = WebSocketApp(
                SERVER_WS_URL,
                on_open=self.on_ws_open,
                on_message=self.on_ws_message,
                on_error=self.on_ws_error,
                on_close=self.on_ws_close
            )
            
            # Start WebSocket in a separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            self.ws_thread.start()
            
        except Exception as e:
            logger.error(f"Error connecting WebSocket: {e}")
            self.connected = False

    def start_heartbeat(self):
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            return
            
        self.heartbeat_thread = threading.Thread(target=self.send_heartbeat, daemon=True)
        self.heartbeat_thread.start()

    def send_heartbeat(self):
        while self.connected and not self.stop_event.is_set():
            try:
                if self.ws and self.connected:
                    heartbeat = {
                        "type": "heartbeat",
                        "timestamp": datetime.now().isoformat()
                    }
                    self.ws.send(json.dumps(heartbeat))
                    logger.debug("Sent heartbeat")
            except WebSocketConnectionClosedException:
                self.connected = False
                logger.warning("Connection closed during heartbeat")
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                self.connected = False
                break
                
            time.sleep(HEARTBEAT_INTERVAL)

    def monitor_wifi(self):
        while not self.stop_event.is_set():
            current_state = self.check_wifi_connection()
            
            if self.last_wifi_state is not None and current_state != self.last_wifi_state:
                if self.connected and self.username:
                    status_msg = {
                        "type": "status_update",
                        "status": "present" if current_state else "absent"
                    }
                    try:
                        self.ws.send(json.dumps(status_msg))
                    except:
                        pass
                        
            self.last_wifi_state = current_state
            time.sleep(WIFI_CHECK_INTERVAL)

    def login(self):
        self.username = self.entry_username.get()
        self.password = self.entry_password.get()
        
        if not self.username or not self.password:
            messagebox.showwarning("Error", "Please enter both username and password")
            return
        
        # Connect WebSocket if not already connected
        if not self.connected:
            self.connect_websocket()
            time.sleep(1)  # Small delay for connection to establish
            
        # Start WiFi monitoring
        if not self.wifi_thread or not self.wifi_thread.is_alive():
            self.wifi_thread = threading.Thread(target=self.monitor_wifi, daemon=True)
            self.wifi_thread.start()

    def signup(self):
        username = self.entry_username.get()
        password = self.entry_password.get()
        
        if not username or not password:
            messagebox.showwarning("Error", "Please enter both username and password")
            return
        
        # In a real app, this would send to server
        messagebox.showinfo("Info", "Please contact administrator to create an account")
        # Alternatively implement API registration if available

    def mark_attendance(self):
        if not self.connected:
            messagebox.showwarning("Error", "Not connected to server")
            return
            
        if not self.check_wifi_connection():
            messagebox.showwarning("Error", "You must be on campus network to mark attendance")
            return
            
        try:
            status_msg = {
                "type": "status_update",
                "status": "present"
            }
            self.ws.send(json.dumps(status_msg))
            self.attendance_status.config(text="Status: Present", fg="green")
            self.last_seen_label.config(text=f"Last seen: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            messagebox.showinfo("Success", "Attendance marked successfully")
        except:
            messagebox.showerror("Error", "Failed to mark attendance")

    def show_message(self, sender, message):
        self.messages_text.config(state=tk.NORMAL)
        self.messages_text.insert(tk.END, f"{sender}: {message}\n")
        self.messages_text.config(state=tk.DISABLED)
        self.messages_text.see(tk.END)

    def on_closing(self):
        self.stop_event.set()
        
        # Close WebSocket
        if self.ws:
            self.ws.close()
        
        # Wait for threads to finish
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=1)
        
        if self.wifi_thread and self.wifi_thread.is_alive():
            self.wifi_thread.join(timeout=1)
        
        self.root.destroy()
        sys.exit(0)

if __name__ == "__main__":
    StudentClient()
