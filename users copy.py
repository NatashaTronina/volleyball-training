import telebot
from telebot import types
import json
import os
from admin import is_admin
data = ""
with open('config.json', 'r') as file:
    data = json.load(file)

TOKEN = data.get("token")
bot = telebot.TeleBot(TOKEN)

# Словарь для хранения ID пользователей (можно заменить на базу данных)
users_id = {}  # {users_id: usersname} - пример структуры


@bot.message_handler(commands=['start'])
def start(message):
    users_id = message.from_users.id
    usersname = message.from_users.usersname
    users_id[users_id] = usersname
    if not is_admin(message):
        bot.send_message(message.chat.id, f"Привет, {usersname}! Выберите команду /voting для голосование за тренировки")

@bot.message_handler(commands=['status'])
def status(message):
    if not is_admin(message):
        bot.send_message(message.chat.id, "Выберите команду /voting для голосование за тренировки")

@bot.message_handler(commands=['voting'])
def voting(message):
    if not is_admin(message):
        bot.send_message(message.chat.id, "Выберите команду /voting для голосование за тренировки")


if __name__ == "__main__":
    print("Bot started!")
    # set_commands()
    bot.polling()