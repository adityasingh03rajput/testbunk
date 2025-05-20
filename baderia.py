import socket
import threading
import json
from datetime import datetime

HOST = "0.0.0.0"
PORT = 65432

attendance_records = {}  # Format: {username: {"status": "", "left_time": ""}}
connected_clients = {}

def broadcast_update():
    data = {"action": "update", "data": attendance_records}
    for client in connected_clients.values():
        try:
            client.send(json.dumps(data).encode("utf-8"))
        except:
            pass

def handle_client(conn, addr):
    print(f"Connected: {addr}")
    username = None
    
    try:
        while True:
            data = conn.recv(1024).decode("utf-8")
            if not data:
                break
                
            message = json.loads(data)
            action = message.get("action")
            username = message.get("username")
            
            if action == "login":
                connected_clients[username] = conn
                attendance_records[username] = {
                    "status": "absent",
                    "left_time": ""
                }
                
            elif action == "start_timer":
                attendance_records[username] = {
                    "status": "present",
                    "left_time": ""
                }
                
            elif action == "mark_present":
                attendance_records[username] = {
                    "status": "present",
                    "left_time": ""
                }
                
            elif action == "disconnected":
                attendance_records[username] = {
                    "status": "absent",
                    "left_time": message.get("status")
                }
                
            broadcast_update()
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if username in connected_clients:
            del connected_clients[username]
        if username in attendance_records:
            del attendance_records[username]
        conn.close()
        broadcast_update()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server running on {HOST}:{PORT}")
        
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    start_server()
