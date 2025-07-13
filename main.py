from flask import Flask, jsonify, redirect
import requests
import json
import os
import time
import ssl
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# SSL adapter to fix DH_KEY_TOO_SMALL error
class UnsafeTLSAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        ctx = ssl.create_default_context()
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx)

# Create session using the custom adapter
session = requests.Session()
session.mount('https://', UnsafeTLSAdapter())

# Flask setup
app = Flask(__name__)

# Pushover credentials
PUSHOVER_TOKEN = 'ap2yae9on7csd1t386vhb3ehbtp5e5'
PUSHOVER_USER = 'utjtwa8eye7p7dype8kvu5i7ro2ukk'

# Endpoint and local storage
URL = 'https://www.sahorseracing.co.za/sahr-php/public.php?feed=fixtures&_='
NOTIFIED_FILE = 'notified.json'

def load_notified():
    if os.path.exists(NOTIFIED_FILE):
        with open(NOTIFIED_FILE, 'r') as f:
            return json.load(f)
    return []

def save_notified(data):
    with open(NOTIFIED_FILE, 'w') as f:
        json.dump(data, f)

def send_pushover(message):
    print(f"Sending notification: {message}")
    requests.post("https://api.pushover.net/1/messages.json", data={
        "token": PUSHOVER_TOKEN,
        "user": PUSHOVER_USER,
        "message": message
    })

@app.route('/')
def root():
    return "✅ Weight Checker is running. Visit /check to trigger weight detection."

@app.route('/check')
def check_weights():
    try:
        timestamp = int(time.time() * 1000)
        response = session.get(URL + str(timestamp), timeout=15, verify=False)
        response.raise_for_status()

        data = response.json()
        notified = load_notified()
        messages = []
        new_notified = False

        for meeting in data:
            if meeting.get('dStatus') == 'W':
                key = f"{meeting.get('clubName')}|{meeting.get('date')}"
                if key not in notified:
                    msg = f"Weights are available for {meeting['clubName']} on {meeting['lDate']}"
                    messages.append(msg)
                    notified.append(key)
                    new_notified = True
                    print("✅ " + msg)

        if new_notified:
            save_notified(notified)
            for msg in messages:
                send_pushover(msg)
            return jsonify({"status": "notifications_sent", "messages": messages})

        return jsonify({"status": "no_new_weights", "message": "No new weight updates."})

    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
