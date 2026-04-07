import json
import os
from datetime import datetime
import pytz

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(DATA_DIR, exist_ok=True)

LOG_FILE = os.path.join(
    DATA_DIR,
    f"messages_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
)

def save_message(data):
    data["stored_at"] = now_brt()

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def now_brt():
    tz = pytz.timezone("America/Sao_Paulo")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S BRT")