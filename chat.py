from flask import Flask, request, jsonify
from datetime import datetime
import socket
import threading
import time
import os
import json
import requests
from netaddr import IPNetwork, IPAddress

app = Flask(__name__)

# Store chat messages and user status
messages = []  # Format: {"sender": username, "message": text, "timestamp": datetime, "ip": ip}
users = {}      # Format: {ip: {"username": name, "last_active": datetime, "status": "online/offline"}}
local_ip = socket.gethostbyname(socket.gethostname())
port = 20074
username = ""

def find_available_port(start_port=20074, max_attempts=100):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except socket.error:
            continue
    return start_port

def get_local_network():
    """Get local network IP range"""
    gw = socket.gethostbyname(socket.gethostname())
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((gw, 0))
    ip = s.getsockname()[0]
    return f"{ip.rsplit('.', 1)[0]}.0/24"

def discover_devices():
    """Scan local network for other chat servers"""
    network = get_local_network()
    active_ips = []
    
    def check_ip(ip):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((str(ip), port))
            if result == 0:
                try:
                    response = requests.get(f"http://{ip}:{port}/", timeout=1)
                    if response.status_code == 200:
                        active_ips.append(str(ip))
                except:
                    pass
            sock.close()
        except:
            pass

    threads = []
    for ip in IPNetwork(network):
        if str(ip) == local_ip:
            continue
            
        t = threading.Thread(target=check_ip, args=(ip,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    return active_ips

@app.route("/")
def home():
    return jsonify({
        "status": "Chat server is running",
        "your_ip": local_ip,
        "endpoints": {
            "/login": "POST - Send username to login",
            "/send_message": "POST - Send chat messages",
            "/get_messages": "GET - Retrieve all messages",
            "/get_users": "GET - Get all users",
            "/logout": "POST - Logout user",
            "/discover": "GET - Discover nearby devices"
        }
    })

@app.route("/discover", methods=["GET"])
def discover():
    devices = discover_devices()
    return jsonify({"nearby_devices": devices})

@app.route("/login", methods=["POST"])
def login():
    global username
    data = request.json
    if not data:
        return {"error": "No data provided"}, 400
        
    username = data.get("username")
    if not username:
        return {"error": "username required"}, 400

    users[local_ip] = {
        "username": username,
        "status": "online",
        "last_active": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return {"status": f"login successful for {username}", "your_ip": local_ip}, 200

@app.route("/send_message", methods=["POST"])
def send_message():
    data = request.json
    if not data:
        return {"error": "No data provided"}, 400
        
    sender = data.get("sender")
    message = data.get("message")
    target_ip = data.get("target_ip", local_ip)  # Default to local if not specified
    
    if not sender or not message:
        return {"error": "sender and message required"}, 400
        
    if local_ip not in users:
        return {"error": "user not logged in"}, 403

    messages.append({
        "sender": sender,
        "message": message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": target_ip
    })
    
    # If sending to another device, forward the message
    if target_ip != local_ip:
        try:
            requests.post(
                f"http://{target_ip}:{port}/send_message",
                json={"sender": sender, "message": message, "target_ip": target_ip},
                timeout=1
            )
        except:
            return {"status": "message sent but failed to reach target"}, 200
    
    return {"status": "message sent"}, 200

@app.route("/get_messages", methods=["GET"])
def get_messages():
    filtered = [msg for msg in messages if msg["ip"] == local_ip]
    return jsonify({
        "count": len(filtered),
        "messages": filtered
    })

@app.route("/get_users", methods=["GET"])
def get_users():
    return jsonify({
        "count": len(users),
        "users": users
    })

@app.route("/logout", methods=["POST"])
def logout():
    data = request.json
    if not data:
        return {"error": "No data provided"}, 400
        
    username = data.get("username")
    if not username:
        return {"error": "username required"}, 400
        
    if local_ip not in users:
        return {"error": "username not found"}, 404

    users[local_ip]["status"] = "offline"
    users[local_ip]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {"status": f"logout successful for {username}"}, 200

def print_messages():
    os.system('cls' if os.name == 'nt' else 'clear')
    filtered = [msg for msg in messages if msg["ip"] == local_ip]
    print("\n=== MESSAGES ===")
    for msg in filtered[-10:]:
        print(f"[{msg['timestamp']}] {msg['sender']}: {msg['message']}")
    print("\n")

def chat_interface():
    global username
    while True:
        print("\nOptions:")
        print("1. Send message")
        print("2. Refresh messages")
        print("3. View online users")
        print("4. Discover nearby devices")
        print("5. Exit")
        
        choice = input("Choose an option (1-5): ")
        
        if choice == "1":
            print("\nNearby devices:")
            devices = discover_devices()
            for i, ip in enumerate(devices, 1):
                print(f"{i}. {ip}")
            print(f"{len(devices)+1}. Everyone (broadcast)")
            
            target = input(f"Who to message? (1-{len(devices)+1}): ")
            try:
                target_idx = int(target) - 1
                if target_idx == len(devices):
                    target_ip = "broadcast"
                else:
                    target_ip = devices[target_idx]
            except:
                print("Invalid choice, sending to yourself")
                target_ip = local_ip
                
            message = input("Enter your message: ")
            
            if target_ip == "broadcast":
                for ip in devices:
                    try:
                        requests.post(
                            f"http://{ip}:{port}/send_message",
                            json={"sender": username, "message": message, "target_ip": ip},
                            timeout=1
                        )
                    except:
                        print(f"Failed to send to {ip}")
                messages.append({
                    "sender": username,
                    "message": message,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "ip": local_ip
                })
            else:
                response = requests.post(
                    f"http://localhost:{port}/send_message",
                    json={"sender": username, "message": message, "target_ip": target_ip}
                )
            print("Message sent!")
            
        elif choice == "2":
            print_messages()
            
        elif choice == "3":
            response = requests.get(f"http://localhost:{port}/get_users")
            users_data = response.json()
            print("\n=== ONLINE USERS ===")
            for ip, data in users_data["users"].items():
                print(f"{data['username']} ({data['status']}) - IP: {ip} - last active: {data['last_active']}")
            print()
            
        elif choice == "4":
            devices = discover_devices()
            print("\n=== NEARBY DEVICES ===")
            for ip in devices:
                print(ip)
            print()
            
        elif choice == "5":
            response = requests.post(
                f"http://localhost:{port}/logout",
                json={"username": username}
            )
            print(response.json().get("status", "Logged out"))
            break
            
        else:
            print("Invalid choice. Please try again.")

def run_server():
    global port
    port = find_available_port()
    print(f"Starting chat server on {local_ip}:{port}")
    app.run(host="0.0.0.0", port=port, use_reloader=False)

if __name__ == "__main__":
    # Start server in a separate thread
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Give server time to start
    time.sleep(1)
    
    # User login
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=== P2P CHAT SYSTEM ===")
    username = input("Enter your username: ")
    
    response = requests.post(
        f"http://localhost:{port}/login",
        json={"username": username}
    )
    
    if response.status_code == 200:
        print(f"Logged in as {username}")
        print(f"Your IP: {local_ip}")
        print_messages()
        chat_interface()
    else:
        print("Login failed:", response.json().get("error", "Unknown error"))
