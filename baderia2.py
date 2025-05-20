from flask import Flask, request, jsonify
import time
from datetime import datetime

app = Flask(__name__)

devices = {}  # {ip: last_ping_time}
attendance = {}  # {username: {"status": "present/absent", "last_active": timestamp}}
alerts = {}  # {target_ip: message}

@app.route("/ping", methods=["POST"])
def ping():
    ip = request.remote_addr
    devices[ip] = time.time()
    return {"status": "pong"}, 200

@app.route("/devices", methods=["GET"])
def get_devices():
    now = time.time()
    active_devices = [ip for ip, t in devices.items() if now - t < 60]
    return jsonify(active_devices)

@app.route("/update", methods=["POST"])
def update_attendance():
    data = request.json
    username = data.get("username")
    action = data.get("action")
    status = data.get("status")
    
    if action == "login":
        attendance[username] = {
            "status": "present",
            "last_active": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    elif action == "mark_present":
        if username in attendance:
            attendance[username]["status"] = "present"
            attendance[username]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return {"status": "updated"}, 200

@app.route("/get_attendance", methods=["GET"])
def get_attendance():
    return jsonify(attendance)

@app.route("/send_alert", methods=["POST"])
def send_alert():
    data = request.json
    target_ip = data.get("target_ip")
    message = data.get("message", "ALERT!")
    if target_ip:
        alerts[target_ip] = message
        return {"status": "alert queued"}, 200
    return {"error": "Missing target_ip"}, 400

@app.route("/get_alert", methods=["GET"])
def get_alert():
    ip = request.remote_addr
    alert = alerts.pop(ip, None)
    return jsonify({"alert": alert}) if alert else jsonify({})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=20074)
