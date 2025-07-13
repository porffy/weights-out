import os
import json
import time
import requests
from flask import Flask, jsonify

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
import ssl

# Custom HTTPS Adapter to avoid DH_KEY_TOO_SMALL SSL error
class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        ctx = ssl.create_default_context()
        # This disables DH parameter check for old servers causing "dh key too small"
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block,
            ssl_context=ctx, **pool_kwargs
        )

app = Flask(__name__)

# Pushover API credentials (replace with your own)
PUSHOVER_TOKEN = 'ap2yae9on7csd1t386vhb3ehbtp5e5'
PUSHOVER_USER = 'utjtwa8eye7p7dype8kvu5i7ro2ukk'

# URL for fixtures JSON feed
URL = 'https://www.sahorseracing.co.za/sahr-php/public.php?feed=fixtures&_='

# File to track which meetings we've notified about
NOTIFIED_FILE = 'notified.json'


def load_notified():
    if os.path.exists(NOTIFIED_FILE):
        with open(NOTIFIED_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
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
def home():
    return "Weight Checker is running. Visit /check to trigger weight detection."


@app.route('/check')
def check_weights():
    try:
        # Create a session with our custom SSL adapter
        session = requests.Session()
        session.mount('https://', SSLAdapter())

        # Timestamp to avoid cached response
        timestamp = int(time.time() * 1000)
        resp = session.get(URL + str(timestamp))
        resp.raise_for_status()

        data = resp.json()

        notified = load_notified()
        messages = []
        new_notifications = False

        for meeting in data:
            # 'W' means weights are available
            if meeting.get('dStatus') == 'W':
                meeting_key = f"{meeting.get('clubName')}|{meeting.get('date')}"
                if meeting_key not in notified:
                    msg = f"Weights are available for {meeting['clubName']} on {meeting['lDate']}"
                    messages.append(msg)
                    notified.append(meeting_key)
                    new_notifications = True
                    print(f"New weights found: {msg}")

        if new_notifications:
            save_notified(notified)
            for msg in messages:
                send_pushover(msg)
            return jsonify({"status": "notifications_sent", "messages": messages})

        return jsonify({"status": "no_new_weights", "message": "No new weight updates."})

    except Exception as e:
        print(f"Error fetching data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
