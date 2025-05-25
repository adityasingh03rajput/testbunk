import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import requests
from datetime import datetime

# Configuration
SERVER_URL = "https://deadball.onrender.com"
UPDATE_INTERVAL = 5  # seconds

class TeacherDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Teacher Dashboard")
        self.root.geometry("1000x800")
        
        # Login Frame
        self.login_frame = tk.Frame(self.root)
        self.login_frame.pack(pady=50)
        
        tk.Label(self.login_frame, text="Teacher Login", font=("Arial", 16)).grid(row=0, columnspan=2, pady=10)
        
        tk.Label(self.login_frame, text="Username:").grid(row=1, column=0, padx=5, pady=5)
        self.username_entry = tk.Entry(self.login_frame)
        self.username_entry.grid(row=1, column=1, padx=5, pady=5)
        
        tk.Label(self.login_frame, text="Password:").grid(row=2, column=0, padx=5, pady=5)
        self.password_entry = tk.Entry(self.login_frame, show="*")
        self.password_entry.grid(row=2, column=1, padx=5, pady=5)
        
        tk.Button(
            self.login_frame, 
            text="Login", 
            command=self.login
        ).grid(row=3, column=0, pady=10, sticky="e")
        
        tk.Button(
            self.login_frame, 
            text="Register", 
            command=self.register
        ).grid(row=3, column=1, pady=10, sticky="w")
        
        # Main Frame (hidden initially)
        self.main_frame = tk.Frame(self.root)
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Attendance Tab
        self.attendance_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.attendance_tab, text="Attendance")
        self.setup_attendance_tab()
        
        # Timetable Tab
        self.timetable_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.timetable_tab, text="Timetable")
        self.setup_timetable_tab()
        
        # Student Management Tab
        self.student_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.student_tab, text="Student Management")
        self.setup_student_tab()
        
        # Status Bar
        self.status_bar = tk.Label(
            self.main_frame,
            text="Status: Not Connected",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.pack(fill=tk.X)
        
        # Start update thread
        threading.Thread(target=self.update_data, daemon=True).start()

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showwarning("Error", "Please enter both username and password")
            return
            
        try:
            response = requests.post(
                f"{SERVER_URL}/login",
                json={"username": username, "password": password},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('type') == 'teacher':
                    self.login_frame.pack_forget()
                    self.main_frame.pack(fill=tk.BOTH, expand=True)
                    self.update_status("Connected")
                else:
                    messagebox.showerror("Error", "Students must use the student portal")
            else:
                messagebox.showerror("Error", data.get('error', 'Login failed'))
        except requests.RequestException:
            messagebox.showerror("Error", "Could not connect to server")

    def register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showwarning("Error", "Please enter both username and password")
            return
            
        try:
            response = requests.post(
                f"{SERVER_URL}/register",
                json={
                    "username": username,
                    "password": password,
                    "type": "teacher"
                },
                timeout=5
            )
            
            if response.status_code == 201:
                messagebox.showinfo("Success", "Teacher registered successfully!")
            else:
                messagebox.showerror("Error", response.json().get('error', 'Registration failed'))
        except requests.RequestException:
            messagebox.showerror("Error", "Could not connect to server")

    def update_status(self, message, color="black"):
        self.status_bar.config(text=f"Status: {message}", fg=color)

    def setup_attendance_tab(self):
        # Attendance Treeview
        self.tree = ttk.Treeview(self.attendance_tab, columns=("Student", "Status", "Last Update"), show="headings")
        self.tree.heading("Student", text="Student")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Last Update", text="Last Update")
        self.tree.column("Student", width=250)
        self.tree.column("Status", width=150)
        self.tree.column("Last Update", width=250)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Random Ring Section
        ring_frame = tk.Frame(self.attendance_tab)
        ring_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.random_names_label = tk.Label(
            ring_frame,
            text="Selected students will appear here",
            font=("Arial", 12),
            height=3,
            relief=tk.GROOVE
        )
        self.random_names_label.pack(fill=tk.X, pady=5)
        
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

    def setup_timetable_tab(self):
        # Timetable Display
        self.timetable_text = tk.Text(self.timetable_tab, height=10, wrap=tk.WORD)
        self.timetable_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Edit Button
        tk.Button(
            self.timetable_tab,
            text="Edit Timetable",
            command=self.edit_timetable,
            padx=10,
            pady=5
        ).pack(pady=10)

    def setup_student_tab(self):
        # Student Registration
        reg_frame = tk.LabelFrame(self.student_tab, text="Register New Student", padx=10, pady=10)
        reg_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(reg_frame, text="Username:").grid(row=0, column=0, padx=5, pady=5)
        self.new_student_user = tk.Entry(reg_frame)
        self.new_student_user.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(reg_frame, text="Password:").grid(row=1, column=0, padx=5, pady=5)
        self.new_student_pass = tk.Entry(reg_frame, show="*")
        self.new_student_pass.grid(row=1, column=1, padx=5, pady=5)
        
        tk.Button(
            reg_frame,
            text="Register Student",
            command=self.register_student,
            padx=10,
            pady=5
        ).grid(row=2, columnspan=2, pady=10)

    def update_data(self):
        while True:
            try:
                # Update attendance
                response = requests.get(f"{SERVER_URL}/get_attendance", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    self.root.after(0, self.update_attendance_table, data)
                
                # Update timetable
                response = requests.get(f"{SERVER_URL}/timetable", timeout=5)
                if response.status_code == 200:
                    timetable = response.json()
                    timetable_text = "Timetable:\n"
                    for time, subject in timetable.items():
                        timetable_text += f"{time}: {subject}\n"
                    self.root.after(0, self.update_timetable_display, timetable_text)
                
                self.update_status("Connected", "blue")
            except requests.RequestException:
                self.update_status("Connection Error", "red")
            
            threading.Event().wait(UPDATE_INTERVAL)

    def update_attendance_table(self, data):
        for row in self.tree.get_children():
            self.tree.delete(row)
            
        for student, info in data.get('students', {}).items():
            status = info.get('status', 'absent').capitalize()
            last_update = info.get('last_update', '')
            self.tree.insert("", tk.END, values=(student, status, last_update))

    def update_timetable_display(self, text):
        self.timetable_text.delete(1.0, tk.END)
        self.timetable_text.insert(tk.END, text)

    def trigger_random_ring(self):
        try:
            response = requests.post(
                f"{SERVER_URL}/attendance",
                json={"action": "random_ring"},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                selected = data.get('students', [])
                names_text = "\n".join(selected)
                self.random_names_label.config(text=names_text)
                
                # Highlight selected students
                for item in self.tree.get_children():
                    values = self.tree.item(item)['values']
                    if values and values[0] in selected:
                        self.tree.tag_configure('highlight', background='yellow')
                        self.tree.item(item, tags=('highlight',))
                    else:
                        self.tree.item(item, tags=())
        except requests.RequestException:
            messagebox.showerror("Error", "Could not connect to server")

    def edit_timetable(self):
        # Get current timetable
        try:
            response = requests.get(f"{SERVER_URL}/timetable", timeout=5)
            if response.status_code == 200:
                current_timetable = response.json()
        except:
            current_timetable = {}
        
        # Create edit dialog
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit Timetable")
        edit_window.geometry("400x400")
        
        # Text widget for editing
        edit_text = tk.Text(edit_window, height=20, width=40)
        edit_text.pack(padx=10, pady=10)
        
        # Populate with current timetable
        for time, subject in current_timetable.items():
            edit_text.insert(tk.END, f"{time}={subject}\n")
        
        # Save button
        tk.Button(
            edit_window,
            text="Save",
            command=lambda: self.save_timetable(edit_text.get("1.0", tk.END), edit_window),
            padx=10,
            pady=5
        ).pack(pady=10)

    def save_timetable(self, text, window):
        timetable = {}
        for line in text.split('\n'):
            if '=' in line:
                time, subject = line.split('=', 1)
                timetable[time.strip()] = subject.strip()
        
        try:
            response = requests.post(
                f"{SERVER_URL}/timetable",
                json={"timetable": timetable},
                timeout=5
            )
            
            if response.status_code == 200:
                messagebox.showinfo("Success", "Timetable updated successfully!")
                window.destroy()
            else:
                messagebox.showerror("Error", "Failed to update timetable")
        except requests.RequestException:
            messagebox.showerror("Error", "Could not connect to server")

    def register_student(self):
        username = self.new_student_user.get()
        password = self.new_student_pass.get()
        
        if not username or not password:
            messagebox.showwarning("Error", "Please enter both username and password")
            return
            
        try:
            # In a real system, we'd have proper student registration endpoint
            # For this demo, we'll just show a success message
            messagebox.showinfo("Success", f"Student {username} registered!")
            self.new_student_user.delete(0, tk.END)
            self.new_student_pass.delete(0, tk.END)
        except:
            messagebox.showerror("Error", "Registration failed")

if __name__ == "__main__":
    root = tk.Tk()
    app = TeacherDashboard(root)
    root.mainloop()
