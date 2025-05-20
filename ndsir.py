import tkinter as tk
from tkinter import ttk
import requests
import threading
import time

SERVER_URL = "http://localhost:20074"  # Flask server URL

class TeacherDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Teacher Dashboard")
        self.root.geometry("800x600")
        
        self.setup_ui()
        self.connect_to_server()
        
    def setup_ui(self):
        self.tree = ttk.Treeview(self.root, columns=("Student", "Status", "Last Active"), show="headings")
        self.tree.heading("Student", text="Student")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Last Active", text="Last Active")
        self.tree.column("Student", width=200)
        self.tree.column("Status", width=150)
        self.tree.column("Last Active", width=200)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.alert_button = tk.Button(
            self.root, 
            text="Send Alert", 
            command=self.send_alert,
            font=("Arial", 12)
        )
        self.alert_button.pack(pady=5)
        
        tk.Button(
            self.root, 
            text="Refresh", 
            command=self.refresh_data,
            font=("Arial", 12)
        ).pack(pady=10)
        
    def connect_to_server(self):
        # Register as teacher
        requests.post(f"{SERVER_URL}/ping")
        self.refresh_data()
        threading.Thread(target=self.check_updates, daemon=True).start()
        
    def refresh_data(self):
        try:
            response = requests.get(f"{SERVER_URL}/devices")
            if response.status_code == 200:
                self.update_table(response.json())
        except requests.RequestException as e:
            print(f"Error refreshing data: {e}")
            
    def update_table(self, devices):
        for row in self.tree.get_children():
            self.tree.delete(row)
            
        for device in devices:
            self.tree.insert("", "end", values=(device, "Active", "Now"))
            
    def check_updates(self):
        while True:
            self.refresh_data()
            time.sleep(5)
            
    def send_alert(self):
        selected = self.tree.focus()
        if selected:
            student = self.tree.item(selected)['values'][0]
            requests.post(f"{SERVER_URL}/send_alert", json={
                "target_ip": student,
                "message": "Please focus on your work!"
            })
            tk.messagebox.showinfo("Alert Sent", f"Alert sent to {student}")

if __name__ == "__main__":
    root = tk.Tk()
    app = TeacherDashboard(root)
    root.mainloop()
