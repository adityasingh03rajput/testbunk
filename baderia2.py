from flask import Flask, request, jsonify
import os
import time

app = Flask(__name__)

# Store messages and files {recipient: [messages]}
messages = {}
files = {}

@app.route("/send_message", methods=["POST"])
def send_message():
    data = request.json
    recipient = data.get("recipient")
    message = data.get("message")
    sender = data.get("sender")
    
    if recipient not in messages:
        messages[recipient] = []
    
    messages[recipient].append({
        "sender": sender,
        "message": message,
        "timestamp": time.time()
    })
    
    return {"status": "message sent"}, 200

@app.route("/send_file", methods=["POST"])
def send_file():
    if 'file' not in request.files:
        return {"error": "No file part"}, 400
    
    file = request.files['file']
    recipient = request.form.get("recipient")
    sender = request.form.get("sender")
    
    if recipient not in files:
        files[recipient] = []
    
    filename = f"{int(time.time())}_{file.filename}"
    file.save(filename)
    
    files[recipient].append({
        "sender": sender,
        "filename": filename,
        "original_name": file.filename,
        "timestamp": time.time()
    })
    
    return {"status": "file received"}, 200

@app.route("/get_messages", methods=["GET"])
def get_messages():
    recipient = request.args.get("recipient")
    user_messages = messages.get(recipient, [])
    messages[recipient] = []  # Clear after reading
    return jsonify({"messages": user_messages})

@app.route("/get_files", methods=["GET"])
def get_files():
    recipient = request.args.get("recipient")
    user_files = files.get(recipient, [])
    files[recipient] = []  # Clear after reading
    return jsonify({"files": user_files})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=20074)
