from flask import Flask, jsonify
import requests
import json
import os
import time
import ssl
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

app = Flask(__name__)

PUSHOVER_TOKEN = 'ap2yae9on7csd1t386vhb3ehbtp5e5'
PUSHOVER_USER = 'utjtwa8eye7p7dype8kvu5i7ro2ukk'
NOTIFIED_FILE = 'notified.json'
URL = 'https://www.sahorseracing.co.za/sahr-php/public.php?feed=fixtures&_='

# Custom HTTPS Adapter that accepts weak DH keys
class UnsafeTLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.set_ciphers('DEFAULT:@SECLEVEL=1')  # Lower security level to accept weak DH keys
        kwargs['ssl_context'] = ctx
        self.poolmanager = PoolManager(*args, **kwargs)

# Use custom session
session = requests.Session()
session.mount('https://', UnsafeTLSAdapter())

def load_notified():
    if os.path.exists(NOTIFIED_FILE):
        with open(NOTIFIED_FILE, 'r') as f:
            return json.load(f)
    return []

def save_notified(data):
    with open(NOTIFIED_FILE, 'w') as f:
        json.dump(data, f)

def send_pushover(message):
    print(f"🔔 Sending notification: {message}")
    requests.post("https://api.pushover.net/1/messages.json", data={
        "token": PUSHOVER_TOKEN,
        "user": PUSHOVER_USER,
        "message": message
    })

@app.route('/')
def home():
    return 'Weight Checker is running. Visit /check to trigger weight detection.'

@app.route('/check')
def check_weights():
    try:
        timestamp = int(time.time() * 1000)
        full_url = URL + str(timestamp)
        response = session.get(full_url, timeout=15, verify:False)

        print("🔎 Full response text:")
        print(response.text[:300])  # Just the first 300 characters for preview

        data = response.json()

        notified = load_notified()
        messages = []
        new_notified = False

        for meeting in data:
            if meeting.get('dStatus') == 'W':
                meeting_key = f"{meeting['clubName']}|{meeting['date']}"
                if meeting_key not in notified:
                    msg = f"Weights are available for {meeting['clubName']} on {meeting['lDate']}"
                    messages.append(msg)
                    notified.append(meeting_key)
                    new_notified = True

        if new_notified:
            save_notified(notified)
            for msg in messages:
                send_pushover(msg)
            return jsonify({"status": "notifications_sent", "messages": messages})

        return jsonify({"status": "no_new_weights", "message": "No new updates."})

    except Exception as e:
        print("❌ Error fetching or parsing:", e)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
