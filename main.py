import telebot
import json
from admin import bot  # Импортируем бота из admin.py
from users import *  # Импортируем все из users.py

# Загрузка токена из конфигурационного файла
data = ""
with open('config.json', 'r') as file:
    data = json.load(file)

TOKEN = data.get("token")
bot = telebot.TeleBot(TOKEN)

if __name__ == "__main__":
    print("Both bot started!")
    bot.polling(none_stop=True)  # Запускаем бота