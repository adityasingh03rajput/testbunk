from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Store chat messages and user status
messages = []  # Format: {"sender": username, "message": text, "timestamp": datetime}
users = {}      # Format: {username: {"last_active": datetime, "status": "online/offline"}}

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    
    if username:
        users[username] = {
            "status": "online",
            "last_active": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return {"status": "login successful"}, 200
    return {"error": "username required"}, 400

@app.route("/send_message", methods=["POST"])
def send_message():
    data = request.json
    username = data.get("sender")
    message = data.get("message")
    
    if username and message:
        messages.append({
            "sender": username,
            "message": message,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return {"status": "message sent"}, 200
    return {"error": "sender and message required"}, 400

@app.route("/get_messages", methods=["GET"])
def get_messages():
    return jsonify({"messages": messages})

@app.route("/get_users", methods=["GET"])
def get_users():
    return jsonify(users)

@app.route("/logout", methods=["POST"])
def logout():
    data = request.json
    username = data.get("username")
    
    if username and username in users:
        users[username]["status"] = "offline"
        users[username]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {"status": "logout successful"}, 200
    return {"error": "username not found"}, 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=20074)
