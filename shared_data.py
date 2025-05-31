import json
import os

POLL_DATA_FILE = "polls.json"
awaiting_confirmation = {}
confirmed_payments = {}
user_ids = []

def save_polls(data):
    print(f"save_polls: Сохранение данных: {data}")  # Добавляем отладочный вывод
    with open(POLL_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_polls():
    print(f"load_polls: Попытка загрузки из файла {POLL_DATA_FILE}") # Добавляем отладочный вывод
    if os.path.exists(POLL_DATA_FILE):
        try:
            with open(POLL_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"load_polls: Данные загружены: {data}")  # Добавляем отладочный вывод
                return data
        except json.JSONDecodeError as e:
            print(f"load_polls: Ошибка декодирования JSON: {e}")
            return {}
    else:
        print(f"load_polls: Файл {POLL_DATA_FILE} не найден.")
        return {}