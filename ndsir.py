import tkinter as tk
from tkinter import ttk
import socket
import json
import threading

HOST = "192.168.115.174"  # Server IP
PORT = 65432

class TeacherDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Teacher Dashboard")
        self.root.geometry("800x600")
        
        self.setup_ui()
        self.connect_to_server()
        
    def setup_ui(self):
        self.tree = ttk.Treeview(self.root, columns=("Student", "Status", "Left Time"), show="headings")
        self.tree.heading("Student", text="Student")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Left Time", text="Left Time")
        self.tree.column("Student", width=200)
        self.tree.column("Status", width=150)
        self.tree.column("Left Time", width=200)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        tk.Button(
            self.root, 
            text="Refresh", 
            command=self.refresh_data,
            font=("Arial", 12)
        ).pack(pady=10)
        
    def connect_to_server(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((HOST, PORT))
        self.send_data("login", "teacher", "teacher")
        
        threading.Thread(target=self.receive_updates, daemon=True).start()
        
    def send_data(self, action, username=None, status=None):
        data = {"action": action, "username": username, "status": status}
        self.client_socket.send(json.dumps(data).encode("utf-8"))
        
    def receive_updates(self):
        while True:
            try:
                data = self.client_socket.recv(1024).decode("utf-8")
                if not data:
                    break
                    
                message = json.loads(data)
                if message.get("action") == "update":
                    self.root.after(0, self.update_table, message.get("data", {}))
                    
            except Exception as e:
                print(f"Error receiving updates: {e}")
                break
                
    def update_table(self, data):
        for row in self.tree.get_children():
            self.tree.delete(row)
            
        for student, info in data.items():
            status = info.get("status", "absent").capitalize()
            left_time = info.get("left_time", "")
            self.tree.insert("", "end", values=(student, status, left_time))
            
    def refresh_data(self):
        self.send_data("refresh")
        
    def on_closing(self):
        self.client_socket.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = TeacherDashboard(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
