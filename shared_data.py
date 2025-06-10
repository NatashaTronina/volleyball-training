import json
import os

POLL_DATA_FILE = "polls.json"
awaiting_confirmation = {}
confirmed_payments = {}
user_ids = []

def save_polls(data):
    with open(POLL_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_polls():
    if os.path.exists(POLL_DATA_FILE):
        try:
            with open(POLL_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except json.JSONDecodeError as e:
            print(f"load_polls: Ошибка декодирования JSON: {e}")
            return {}
    else:
        return {}