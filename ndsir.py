import tkinter as tk
from tkinter import ttk, messagebox
import socket
import json
import threading
import os

class LetsBunkClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("LetsBunk Client")
        self.root.geometry("400x300")
        
        self.server_ip = "192.168.115.49"  # Change to your server IP
        self.server_port = 65432
        self.client_socket = None
        self.username = None
        self.user_type = None
        
        self.create_profile_selection()
        
    def create_profile_selection(self):
        self.clear_window()
        
        tk.Label(self.root, text="Select Profile", font=("Arial", 16)).pack(pady=20)
        
        tk.Button(self.root, text="Student", command=self.student_login, 
                 height=2, width=20).pack(pady=10)
        
        tk.Button(self.root, text="Teacher", command=self.teacher_login,
                 height=2, width=20).pack(pady=10)
    
    def student_login(self):
        self.clear_window()
        self.user_type = "student"
        
        tk.Label(self.root, text="Student Login", font=("Arial", 16)).pack(pady=10)
        
        tk.Label(self.root, text="Username:").pack()
        self.username_entry = tk.Entry(self.root)
        self.username_entry.pack()
        
        tk.Label(self.root, text="Password:").pack()
        self.password_entry = tk.Entry(self.root, show="*")
        self.password_entry.pack()
        
        tk.Button(self.root, text="Login", command=self.connect_as_student).pack(pady=20)
        tk.Button(self.root, text="Back", command=self.create_profile_selection).pack()
    
    def teacher_login(self):
        self.clear_window()
        self.user_type = "teacher"
        
        tk.Label(self.root, text="Teacher Login", font=("Arial", 16)).pack(pady=10)
        
        tk.Label(self.root, text="Username:").pack()
        self.username_entry = tk.Entry(self.root)
        self.username_entry.pack()
        
        tk.Label(self.root, text="Password:").pack()
        self.password_entry = tk.Entry(self.root, show="*")
        self.password_entry.pack()
        
        tk.Button(self.root, text="Login", command=self.connect_as_teacher).pack(pady=20)
        tk.Button(self.root, text="Back", command=self.create_profile_selection).pack()
    
    def connect_as_student(self):
        self.username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not self.username or not password:
            messagebox.showwarning("Error", "Please enter both username and password")
            return
        
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_ip, self.server_port))
            
            # Send login request
            self.send_data("login", self.username, "student")
            
            # Start receive thread
            threading.Thread(target=self.receive_messages, daemon=True).start()
            
            # Show student dashboard
            self.show_student_dashboard()
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {e}")
    
    def connect_as_teacher(self):
        self.username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not self.username or not password:
            messagebox.showwarning("Error", "Please enter both username and password")
            return
        
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_ip, self.server_port))
            
            # Send login request
            self.send_data("login", self.username, "teacher")
            
            # Request attendance data
            self.send_data("get_attendance")
            
            # Start receive thread
            threading.Thread(target=self.receive_messages, daemon=True).start()
            
            # Show teacher dashboard
            self.show_teacher_dashboard()
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {e}")
    
    def show_student_dashboard(self):
        self.clear_window()
        
        tk.Label(self.root, text=f"Student: {self.username}", font=("Arial", 14)).pack(pady=10)
        
        self.status_label = tk.Label(self.root, text="Status: Not Marked", font=("Arial", 12))
        self.status_label.pack(pady=10)
        
        tk.Button(self.root, text="Mark Present", command=self.mark_present,
                 height=2, width=20).pack(pady=10)
        
        tk.Button(self.root, text="Logout", command=self.logout).pack()
    
    def show_teacher_dashboard(self):
        self.clear_window()
        
        tk.Label(self.root, text=f"Teacher: {self.username}", font=("Arial", 14)).pack(pady=10)
        
        # Attendance table
        self.tree = ttk.Treeview(self.root, columns=("Student", "Status"), show="headings")
        self.tree.heading("Student", text="Student")
        self.tree.heading("Status", text="Status")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        tk.Button(self.root, text="Refresh", command=self.refresh_attendance).pack(side="left", padx=10)
        tk.Button(self.root, text="Logout", command=self.logout).pack(side="right", padx=10)
    
    def mark_present(self):
        self.send_data("mark_present", self.username)
        self.status_label.config(text="Status: Present (Marked)")
    
    def refresh_attendance(self):
        self.send_data("get_attendance")
    
    def update_attendance_table(self, data):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for student, status in data.items():
            self.tree.insert("", "end", values=(student, status.capitalize()))
    
    def receive_messages(self):
        while True:
            try:
                data = self.client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                message = json.loads(data)
                if message.get('action') == 'update_attendance':
                    self.root.after(0, self.update_attendance_table, message.get('data', {}))
                
            except (ConnectionResetError, json.JSONDecodeError):
                break
    
    def send_data(self, action, username=None, status=None):
        try:
            data = {"action": action, "username": username, "status": status}
            self.client_socket.send(json.dumps(data).encode('utf-8'))
        except (ConnectionError, OSError) as e:
            messagebox.showerror("Connection Error", f"Failed to send data: {e}")
    
    def logout(self):
        if self.client_socket:
            self.client_socket.close()
        self.username = None
        self.user_type = None
        self.create_profile_selection()
    
    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    client = LetsBunkClient()
    client.run()
