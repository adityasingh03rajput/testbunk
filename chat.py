import requests
import threading
import os
import time
import json

SERVER_URL = "http://your_server_ip:20074"  # Replace with your server IP
USERNAME = input("Enter your username: ")
FRIEND = input("Enter friend's username: ")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def display_messages(messages):
    clear_screen()
    print("╔══════════════════════════════════╗")
    print(f"║    CHAT WITH {FRIEND.upper():20} ║")
    print("╠══════════════════════════════════╣")
    
    for msg in messages:
        sender = "You" if msg['sender'] == USERNAME else msg['sender']
        print(f"║ {sender}: {msg['message'][:30]:30} ║")
    
    print("╚══════════════════════════════════╝")

def message_poller():
    while True:
        try:
            response = requests.get(f"{SERVER_URL}/get_messages", params={"recipient": USERNAME})
            data = response.json()
            if data['messages']:
                display_messages(data['messages'])
        except Exception as e:
            print(f"Error polling messages: {e}")
        time.sleep(2)

def file_poller():
    while True:
        try:
            response = requests.get(f"{SERVER_URL}/get_files", params={"recipient": USERNAME})
            data = response.json()
            if data['files']:
                for file_info in data['files']:
                    print(f"\nReceived file: {file_info['original_name']} from {file_info['sender']}")
                    # Here you would implement file download logic
        except Exception as e:
            print(f"Error polling files: {e}")
        time.sleep(5)

def start_chat():
    # Start polling threads
    threading.Thread(target=message_poller, daemon=True).start()
    threading.Thread(target=file_poller, daemon=True).start()
    
    while True:
        print("\n1. Send message")
        print("2. Send file")
        print("3. Exit")
        choice = input("Choose option: ")
        
        if choice == "1":
            message = input("Enter message: ")
            requests.post(f"{SERVER_URL}/send_message", json={
                "recipient": FRIEND,
                "sender": USERNAME,
                "message": message
            })
        elif choice == "2":
            filepath = input("Enter file path: ")
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    requests.post(f"{SERVER_URL}/send_file", 
                        files={'file': f},
                        data={'recipient': FRIEND, 'sender': USERNAME}
                    )
                print("File sent!")
            else:
                print("File not found")
        elif choice == "3":
            break

if __name__ == "__main__":
    start_chat()
