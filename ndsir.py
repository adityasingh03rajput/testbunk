import tkinter as tk
from tkinter import ttk, messagebox
import json
import random
import threading
import requests
from datetime import datetime

# Cloud server configuration
CLOUD_URL = "https://updatebunk.onrender.com"
UPDATE_INTERVAL = 5  # Seconds between refreshes

class TeacherDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Teacher Dashboard")
        self.root.geometry("1000x700")
        self.students = {}  # Store student data
        self.setup_ui()
        self.register_teacher()
        self.start_update_thread()
        
    def setup_ui(self):
        # Main frame
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Attendance Treeview
        self.tree = ttk.Treeview(main_frame, columns=("Student", "Status", "Last Update"), show="headings")
        self.tree.heading("Student", text="Student")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Last Update", text="Last Update")
        self.tree.column("Student", width=250)
        self.tree.column("Status", width=150)
        self.tree.column("Last Update", width=250)
        self.tree.pack(fill="both", expand=True)
        
        # Control buttons frame
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=10)
        
        # Random Ring Section
        ring_frame = tk.LabelFrame(main_frame, text="Random Ring", padx=10, pady=10)
        ring_frame.pack(fill="x", pady=10)
        
        self.random_names_label = tk.Label(
            ring_frame,
            text="Selected students will appear here",
            font=("Arial", 12),
            height=3,
            relief="groove"
        )
        self.random_names_label.pack(fill="x", pady=5)
        
        tk.Button(
            ring_frame,
            text="Random Ring",
            command=self.trigger_random_ring,
            bg="red",
            fg="white",
            font=("Arial", 12, "bold"),
            padx=20,
            pady=10
        ).pack(pady=5)
        
        # Connection status
        self.connection_label = tk.Label(
            button_frame,
            text="Connected to Cloud Server",
            fg="blue",
            font=("Arial", 10)
        )
        self.connection_label.pack(side="right")
        
        # Refresh button
        tk.Button(
            button_frame,
            text="Refresh Data",
            command=self.manual_refresh,
            font=("Arial", 10)
        ).pack(side="left", padx=5)
        
    def register_teacher(self):
        try:
            response = requests.post(
                f"{CLOUD_URL}/ping",
                json={"type": "teachers", "username": "teacher"},
                timeout=5
            )
            if response.status_code != 200:
                messagebox.showerror("Error", "Failed to register with server")
        except requests.RequestException as e:
            messagebox.showerror("Connection Error", f"Failed to connect to server: {e}")

    def update_data(self):
        try:
            response = requests.get(f"{CLOUD_URL}/get_attendance", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.students = data.get("students", {})
                self.root.after(0, self.update_table)
        except requests.RequestException as e:
            print(f"Update error: {e}")

    def update_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
            
        for student, info in self.students.items():
            status = info.get("status", "absent").capitalize()
            last_update = info.get("last_update", "")
            self.tree.insert("", "end", values=(student, status, last_update))

    def start_update_thread(self):
        def update():
            while True:
                self.update_data()
                threading.Event().wait(UPDATE_INTERVAL)
        
        threading.Thread(target=update, daemon=True).start()

    def manual_refresh(self):
        threading.Thread(target=self.update_data, daemon=True).start()

    def trigger_random_ring(self):
        present_students = [
            student for student, info in self.students.items() 
            if info.get("status") == "present"
        ]
        
        if len(present_students) < 2:
            messagebox.showwarning("Not Enough Students", "Need at least 2 present students")
            return
            
        selected = random.sample(present_students, min(2, len(present_students)))
        names_text = "\n".join(selected)
        self.random_names_label.config(text=names_text)
        
        try:
            response = requests.post(
                f"{CLOUD_URL}/attendance",
                json={"action": "random_ring", "username": "teacher"},
                timeout=5
            )
            if response.status_code == 200:
                # Highlight selected students
                for item in self.tree.get_children():
                    values = self.tree.item(item)["values"]
                    if values and values[0] in selected:
                        self.tree.tag_configure("highlight", background="yellow")
                        self.tree.item(item, tags=("highlight",))
                    else:
                        self.tree.item(item, tags=())
        except requests.RequestException as e:
            messagebox.showerror("Error", f"Failed to send random ring: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = TeacherDashboard(root)
    root.mainloop()
