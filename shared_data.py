import json
import os

POLL_DATA_FILE = "polls.json"  


awaiting_confirmation = {}
confirmed_payments = {}
user_ids = []

def save_polls(data):
    try:
        with open(POLL_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"save_polls: Ошибка записи в файл {POLL_DATA_FILE}: {e}")

def load_polls():
    if os.path.exists(POLL_DATA_FILE):
        try:
            with open(POLL_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except json.JSONDecodeError as e:
            print(f"load_polls: Ошибка декодирования JSON в файле {POLL_DATA_FILE}: {e}")
            return {}
        except IOError as e:
            print(f"load_polls: Ошибка при чтении файла {POLL_DATA_FILE}: {e}")
            return {}
        except Exception as e:
            print(f"load_polls: Непредвиденная ошибка при загрузке данных из файла {POLL_DATA_FILE}: {e}")
            return {}
    else:
        print(f"load_polls: Файл {POLL_DATA_FILE} не найден. Создаем пустой файл.")
        save_polls({})  # Создаем пустой файл
        return {}