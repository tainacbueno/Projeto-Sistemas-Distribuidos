import json
import os
from datetime import datetime
import pytz

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(DATA_DIR, exist_ok=True)

SERVER_ID = os.getenv("SERVER_ID", "server")

LOG_FILE = os.path.join(
    DATA_DIR,
    f"messages_{SERVER_ID}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
)

def save_message(data):
    data["stored_at"] = now_brt()

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

def load_publish_messages():
    messages = []
    event_ids = set()

    if not os.path.exists(DATA_DIR):
        return messages

    for filename in os.listdir(DATA_DIR):
        if not filename.endswith(".log"):
            continue

        path = os.path.join(DATA_DIR, filename)

        with open(path, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                except Exception:
                    continue

                if data.get("type") != "publish":
                    continue

                event_id = data.get("event_id")

                if not event_id or event_id in event_ids:
                    continue

                event_ids.add(event_id)
                messages.append(data)

    return messages

def now_brt():
    tz = pytz.timezone("America/Sao_Paulo")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S BRT")