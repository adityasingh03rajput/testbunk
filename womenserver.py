from flask import Flask, request, jsonify
import time
from datetime import datetime, timedelta

app = Flask(__name__)

# Store devices and alerts
devices = {}  # Format: {device_id: {"ip": str, "last_seen": datetime, "name": str}}
alerts = {}   # Format: {target_id: [{"message": str, "timestamp": datetime, "sender_id": str}]}

DEVICE_TIMEOUT = timedelta(seconds=60)  # Devices timeout after 60 seconds of inactivity
ALERT_RETENTION = timedelta(hours=24)   # Keep alerts for 24 hours

@app.route("/register", methods=["POST"])
def register_device():
    data = request.json
    device_id = data.get("device_id")
    ip = data.get("ip")
    name = data.get("name", f"Device-{device_id[-4:]}")
    
    if not device_id or not ip:
        return jsonify({"error": "Missing device_id or ip"}), 400
    
    devices[device_id] = {
        "ip": ip,
        "last_seen": datetime.now(),
        "name": name
    }
    
    return jsonify({"status": "registered", "device_id": device_id}), 200

@app.route("/ping", methods=["POST"])
def ping():
    data = request.json
    device_id = data.get("device_id")
    
    if not device_id:
        return jsonify({"error": "Missing device_id"}), 400
    
    if device_id in devices:
        devices[device_id]["last_seen"] = datetime.now()
        return jsonify({"status": "pong"}), 200
    else:
        return jsonify({"error": "Device not registered"}), 404

@app.route("/devices", methods=["GET"])
def get_devices():
    now = datetime.now()
    # Clean up old devices
    for device_id in list(devices.keys()):
        if now - devices[device_id]["last_seen"] > DEVICE_TIMEOUT:
            del devices[device_id]
    
    # Return list of active devices
    active_devices = [
        {"id": did, "ip": info["ip"], "name": info["name"]}
        for did, info in devices.items()
    ]
    return jsonify(active_devices)

@app.route("/send_alert", methods=["POST"])
def send_alert():
    data = request.json
    sender_id = data.get("sender_id")
    target_id = data.get("target_id")
    message = data.get("message", "ALERT!")
    
    if not sender_id or not target_id:
        return jsonify({"error": "Missing sender_id or target_id"}), 400
    
    # Verify sender exists
    if sender_id not in devices:
        return jsonify({"error": "Sender device not registered"}), 404
    
    # Create alert entry
    if target_id not in alerts:
        alerts[target_id] = []
    
    alerts[target_id].append({
        "message": f"{devices[sender_id]['name']}: {message}",
        "timestamp": datetime.now(),
        "sender_id": sender_id
    })
    
    return jsonify({"status": "alert queued"}), 200

@app.route("/get_alert", methods=["GET"])
def get_alert():
    device_id = request.args.get("device_id")
    if not device_id:
        return jsonify({"error": "Missing device_id"}), 400
    
    now = datetime.now()
    # Clean up old alerts
    for target_id in list(alerts.keys()):
        alerts[target_id] = [
            alert for alert in alerts[target_id]
            if now - alert["timestamp"] < ALERT_RETENTION
        ]
        if not alerts[target_id]:
            del alerts[target_id]
    
    # Check for alerts for this device
    if device_id in alerts and alerts[device_id]:
        # Return the most recent alert and remove it
        alert = alerts[device_id].pop(0)
        return jsonify({"alert": alert["message"]})
    
    return jsonify({})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=20074, threaded=True)
