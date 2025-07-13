from flask import Flask, jsonify
import requests
import json
import os
import time
import traceback

app = Flask(__name__)

# Pushover credentials (insert your own)
PUSHOVER_TOKEN = 'ap2yae9on7csd1t386vhb3ehbtp5e5'
PUSHOVER_USER = 'utjtwa8eye7p7dype8kvu5i7ro2ukk'

# URL to fetch fixtures (avoiding cache with timestamp)
BASE_URL = 'https://www.sahorseracing.co.za/sahr-php/public.php?feed=fixtures&_='

# File to store which meetings already triggered notification
NOTIFIED_FILE = 'notified.json'

def load_notified():
    if os.path.exists(NOTIFIED_FILE):
        with open(NOTIFIED_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("⚠️ Invalid JSON in notified.json — starting fresh.")
                return []
    return []

def save_notified(data):
    with open(NOTIFIED_FILE, 'w') as f:
        json.dump(data, f)

def send_pushover(message):
    print(f"📲 Sending notification: {message}")
    try:
        response = requests.post("https://api.pushover.net/1/messages.json", data={
            "token": PUSHOVER_TOKEN,
            "user": PUSHOVER_USER,
            "message": message
        })
        response.raise_for_status()
    except Exception as e:
        print("❌ Failed to send pushover:", e)

@app.route('/')
def home():
    return "✅ Weight Checker is running. Visit /check to trigger."

@app.route('/check')
def check_weights():
    try:
        timestamp = int(time.time() * 1000)
        url = BASE_URL + str(timestamp)
        print(f"🌐 Fetching data from: {url}")
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()
        notified = load_notified()
        messages = []
        updated = False

        for meeting in data:
            if meeting.get('dStatus') == 'W':
                key = f"{meeting['clubName']}|{meeting['date']}"
                if key not in notified:
                    msg = f"Weights are available for {meeting['clubName']} on {meeting['lDate']}"
                    messages.append(msg)
                    notified.append(key)
                    updated = True
                    print(f"✅ New weights: {msg}")

        if updated:
            save_notified(notified)
            for msg in messages:
                send_pushover(msg)
            return jsonify({"status": "notified", "messages": messages})
        else:
            print("ℹ️ No new weight updates.")
            return jsonify({"status": "no_new_weights"})

    except Exception as e:
        print("🔥 Error occurred during /check")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
