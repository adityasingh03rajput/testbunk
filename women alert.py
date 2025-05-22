import socket
import threading
import time
import os
import requests
from uuid import getnode as get_mac

SERVER_URL = "http://192.168.205.122:20074"  # Replace with your actual server IP or domain
DISCOVERY_PING_INTERVAL = 30
RECONNECT_INTERVAL = 10  # Seconds to wait before reconnecting if connection fails

class SafetyDevice:
    def __init__(self, port=65432):
        self.port = port
        self.device_id = str(get_mac())  # Unique identifier for this device
        self.local_ip = self.get_local_ip()
        self.running = True
        self.last_alert_time = 0
        self.alert_cooldown = 10
        self.partner_ids = []
        self.connected = False
        self.server_available = False
        self.partner_list = []
        
        self.register_device()
        self.start_ping_thread()
        self.start_alert_polling()
        self.start_interface()

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def register_device(self):
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                response = requests.post(
                    f"{SERVER_URL}/register",
                    json={
                        "device_id": self.device_id,
                        "ip": self.local_ip,
                        "name": f"Device-{self.device_id[-4:]}"
                    },
                    timeout=5
                )
                if response.status_code == 200:
                    self.connected = True
                    self.server_available = True
                    print("Successfully connected to server!")
                    return
            except requests.exceptions.RequestException as e:
                print(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(RECONNECT_INTERVAL)
        
        print("Could not connect to server. Running in offline mode.")
        self.connected = False
        self.server_available = False

    def start_ping_thread(self):
        def ping():
            while self.running:
                if self.server_available:
                    try:
                        response = requests.post(
                            f"{SERVER_URL}/ping",
                            json={"device_id": self.device_id},
                            timeout=3
                        )
                        if response.status_code != 200:
                            self.server_available = False
                    except:
                        self.server_available = False
                else:
                    # Attempt to reconnect
                    self.register_device()
                
                time.sleep(DISCOVERY_PING_INTERVAL)
        
        thread = threading.Thread(target=ping)
        thread.daemon = True
        thread.start()

    def refresh_partner_list(self):
        try:
            response = requests.get(f"{SERVER_URL}/devices", timeout=5)
            if response.status_code == 200:
                devices = response.json()
                # Filter out our own device and format for display
                self.partner_list = [
                    {"id": dev["id"], "name": dev["name"], "ip": dev["ip"]}
                    for dev in devices if dev["id"] != self.device_id
                ]
                return True
        except:
            pass
        return False

    def select_partners(self):
        if not self.refresh_partner_list():
            print("Could not retrieve partner list from server.")
            manual_ip = input("Enter partner IP manually (leave empty to skip): ").strip()
            if manual_ip:
                self.partner_ids = [{"ip": manual_ip, "name": "Manual Entry"}]
            return

        print("\nAvailable devices:")
        for idx, device in enumerate(self.partner_list):
            print(f"{idx + 1}. {device['name']} ({device['ip']})")

        while True:
            choice = input("Enter number(s) (comma separated) or 'r' to refresh: ").strip().lower()
            if choice == 'r':
                if self.refresh_partner_list():
                    print("\nRefreshed partner list:")
                    for idx, device in enumerate(self.partner_list):
                        print(f"{idx + 1}. {device['name']} ({device['ip']})")
                else:
                    print("Failed to refresh partner list.")
                continue
            
            try:
                if choice:
                    selected = [int(i.strip()) - 1 for i in choice.split(',') if i.strip().isdigit()]
                    self.partner_ids = [self.partner_list[i]["id"] for i in selected if 0 <= i < len(self.partner_list)]
                    if self.partner_ids:
                        break
                    print("No valid selections. Please try again.")
                else:
                    print("No partners selected. You can add partners later.")
                    break
            except ValueError:
                print("Invalid input. Please enter numbers separated by commas.")

    def start_alert_polling(self):
        def poll():
            while self.running:
                if self.server_available:
                    try:
                        response = requests.get(
                            f"{SERVER_URL}/get_alert",
                            params={"device_id": self.device_id},
                            timeout=5
                        )
                        if response.status_code == 200:
                            data = response.json()
                            if "alert" in data and data["alert"]:
                                self.display_received_alert(data["alert"])
                    except:
                        pass
                time.sleep(5)
        
        thread = threading.Thread(target=poll)
        thread.daemon = True
        thread.start()

    def display_received_alert(self, msg):
        self.clear_screen()
        print("╔════════════════════════════════════════╗")
        print("║        EMERGENCY ALERT!                ║")
        print("╠════════════════════════════════════════╣")
        print(f"║  {msg.center(38)}  ║")
        print("╚════════════════════════════════════════╝")
        input("\nPress Enter to acknowledge...")
        self.display_interface()

    def send_alert(self):
        success = False
        for partner_id in self.partner_ids:
            try:
                response = requests.post(
                    f"{SERVER_URL}/send_alert",
                    json={
                        "sender_id": self.device_id,
                        "target_id": partner_id,
                        "message": "USER IS IN DANGER!"
                    },
                    timeout=5
                )
                if response.status_code == 200:
                    success = True
            except Exception as e:
                print(f"Error sending alert: {e}")

        return success

    def display_interface(self):
        self.clear_screen()
        print("╔════════════════════════════════════════╗")
        print("║    WOMEN'S SAFETY ALERT SYSTEM         ║")
        print("╠════════════════════════════════════════╣")
        print(f"║ Your Device ID: {self.device_id[-8:]:22} ║")
        print(f"║ Your IP: {self.local_ip:30} ║")
        print("║ Server: " + ("Connected" if self.server_available else "Disconnected").ljust(31) + "║")
        print("║ Partner Devices:                       ║")
        
        if not self.partner_ids:
            print("║  - No partners selected                ║")
        else:
            for partner in self.partner_ids:
                # Find partner details
                partner_info = next((p for p in self.partner_list if p["id"] == partner), 
                                  {"name": "Unknown", "ip": partner})
                print(f"║  - {partner_info['name']} ({partner_info['ip']:15})       ║")
        
        print("║                                        ║")
        print("║   Options:                             ║")
        print("║   1. Press ENTER to send alert         ║")
        print("║   2. Press 'A' to add partners        ║")
        print("║   3. Press 'Q' to quit                ║")
        print("╚════════════════════════════════════════╝")

    def start_interface(self):
        while self.running:
            self.display_interface()
            user_input = input().strip().lower()
            
            if user_input == 'q':
                self.running = False
                break
            elif user_input == 'a':
                self.select_partners()
            else:
                if time.time() - self.last_alert_time < self.alert_cooldown:
                    print(f"Wait {self.alert_cooldown - int(time.time() - self.last_alert_time)}s before next alert.")
                    time.sleep(2)
                    continue
                
                if not self.partner_ids:
                    print("No partners selected. Please add partners first.")
                    time.sleep(2)
                    continue
                
                if self.send_alert():
                    self.last_alert_time = time.time()
                    self.clear_screen()
                    print("╔════════════════════════════════════════╗")
                    print("║     ALERT SENT SUCCESSFULLY           ║")
                    print("╚════════════════════════════════════════╝")
                else:
                    print("╔════════════════════════════════════════╗")
                    print("║     FAILED TO SEND ALERT               ║")
                    print("╚════════════════════════════════════════╝")
                input("\nPress Enter to continue...")

if __name__ == "__main__":
    SafetyDevice()
