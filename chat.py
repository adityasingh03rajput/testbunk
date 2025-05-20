from flask import Flask, request, jsonify
from datetime import datetime
import socket
import threading
import time
import os
import json

app = Flask(__name__)

# Store chat messages and user status
messages = []  # Format: {"sender": username, "message": text, "timestamp": datetime}
users = {}      # Format: {username: {"last_active": datetime, "status": "online/offline"}}

def find_available_port(start_port=20074, max_attempts=100):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except socket.error:
            continue
    return start_port  # Fallback to default if none available

@app.route("/")
def home():
    return jsonify({
        "status": "Chat server is running",
        "endpoints": {
            "/login": "POST - Send username to login",
            "/send_message": "POST - Send chat messages",
            "/get_messages": "GET - Retrieve all messages",
            "/get_users": "GET - Get all users",
            "/logout": "POST - Logout user"
        }
    })

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    if not data:
        return {"error": "No data provided"}, 400
        
    username = data.get("username")
    if not username:
        return {"error": "username required"}, 400

    users[username] = {
        "status": "online",
        "last_active": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return {"status": f"login successful for {username}"}, 200

@app.route("/send_message", methods=["POST"])
def send_message():
    data = request.json
    if not data:
        return {"error": "No data provided"}, 400
        
    username = data.get("sender")
    message = data.get("message")
    
    if not username or not message:
        return {"error": "sender and message required"}, 400
        
    if username not in users:
        return {"error": "user not logged in"}, 403

    messages.append({
        "sender": username,
        "message": message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    return {"status": "message sent"}, 200

@app.route("/get_messages", methods=["GET"])
def get_messages():
    return jsonify({
        "count": len(messages),
        "messages": messages
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
        
    if username not in users:
        return {"error": "username not found"}, 404

    users[username]["status"] = "offline"
    users[username]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {"status": f"logout successful for {username}"}, 200

def run_server():
    port = find_available_port()
    print(f"Starting chat server on port {port}")
    app.run(host="0.0.0.0", port=port, use_reloader=False)

def print_messages():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("\n=== MESSAGES ===")
    for msg in messages[-10:]:  # Show last 10 messages
        print(f"[{msg['timestamp']}] {msg['sender']}: {msg['message']}")
    print("\n")

def chat_interface(username):
    while True:
        print("\nOptions:")
        print("1. Send message")
        print("2. Refresh messages")
        print("3. View online users")
        print("4. Exit")
        
        choice = input("Choose an option (1-4): ")
        
        if choice == "1":
            message = input("Enter your message: ")
            response = requests.post(
                f"http://localhost:{port}/send_message",
                json={"sender": username, "message": message}
            )
            print(response.json().get("status", "Message sent"))
            
        elif choice == "2":
            print_messages()
            
        elif choice == "3":
            response = requests.get(f"http://localhost:{port}/get_users")
            users_data = response.json()
            print("\n=== ONLINE USERS ===")
            for user, data in users_data["users"].items():
                print(f"{user} ({data['status']}) - last active: {data['last_active']}")
            print()
            
        elif choice == "4":
            response = requests.post(
                f"http://localhost:{port}/logout",
                json={"username": username}
            )
            print(response.json().get("status", "Logged out"))
            break
            
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    import requests
    
    # Start server in a separate thread
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Give server time to start
    time.sleep(1)
    
    # Get the port being used
    port = app.config.get('SERVER_PORT', 20074)
    
    # User login
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=== CHAT SYSTEM ===")
    username = input("Enter your username: ")
    
    response = requests.post(
        f"http://localhost:{port}/login",
        json={"username": username}
    )
    
    if response.status_code == 200:
        print(f"Logged in as {username}")
        print_messages()
        chat_interface(username)
    else:
        print("Login failed:", response.json().get("error", "Unknown error"))
