# Вспомогательные функции (для хранения данных и т.д.)

# utils.py

import json
import os
import telebot  # Import telebot

# Файлы для хранения данных
POLL_DATA_FILE = "poll_data.json"
QR_CODES_FILE = "qr_codes.json"

def load_data(filename):
    """Загружает данные из JSON файла."""
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print(f"Ошибка при загрузке {filename}. Возможно, файл пустой или поврежден.")
                return {}
    else:
        print(f"Файл {filename} не найден.")
        return {}

def save_data(data, filename):
    """Сохраняет данные в JSON файл."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def handle_qr_code(bot, message):  # Pass bot object
    """Обрабатывает QR-код, отправленный пользователем."""
    chat_id = message.chat.id

    if message.photo:
        #  Получаем информацию о фотографии
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        #  Сохраняем QR-код (в данном случае, просто для примера)
        #  В РЕАЛЬНОМ КОДЕ ЗДЕСЬ НУЖНО СОХРАНИТЬ ФАЙЛ
        #  Например:
        with open("qr_code.jpg", 'wb') as new_file:
           new_file.write(downloaded_file)

        bot.send_message(chat_id, "QR-код сохранен.")
    else:
        bot.send_message(chat_id, "Пожалуйста, отправьте QR-код как *изображение*.", parse_mode="Markdown")  # Предупреждение, если отправлено не изображение