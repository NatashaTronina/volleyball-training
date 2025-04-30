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
users = {} # {user_id: username} - пример структуры


# @bot.message_handler(commands=['start'])
# def create_poll_command(message):
#     if is_admin(message):
#         bot.send_message(message.chat.id, "Выберите команду /create_poll для создания опроса")
        
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    users[user_id] = username

    # Устанавливаем дефолтные команды для текущего пользователя
    default_commands = [
        telebot.types.BotCommand("start", "Начать работу с ботом"),
        telebot.types.BotCommand("status", "Проверить свой статус оплаты"),
        telebot.types.BotCommand("voting", "Голосовать за тренировки"),
        telebot.types.BotCommand("help", "Получить справку")
    ]
    bot.set_my_commands(commands=default_commands, scope=telebot.types.BotCommandScopeChat(chat_id=message.chat.id))

    bot.send_message(message.chat.id, f"Привет, {first_name}! Для голосования за тренировки нажми команду /voting")

@bot.message_handler(commands=['status'])
def status(message):
    user_id = message.from_user.id
    # Проверяем, есть ли ID пользователя в нашем словаре (или базе данных)
    if user_id in users:
        print(f"Запрос статуса от пользователя: {user_id}")
        # Здесь нужно реализовать логику проверки статуса оплаты пользователя.
        # Это может включать запрос к базе данных, API оплаты и т.д.
        try:
            # Замените на вашу логику
            payment_status = "Оплачено"  # Пример
            bot.reply_to(message, f"Ваш статус оплаты: {payment_status}")
        except Exception as e:
            bot.reply_to(message, f"Ошибка при проверке статуса оплаты: {e}")
    else:
        bot.reply_to(message, "Пожалуйста, сначала используйте команду /start, чтобы зарегистрироваться.")

@bot.message_handler(commands=['help'])
def help(message):
    help_text = """
    Список команд:
    /start - начало работы с ботом
    /status - проверка своего статуса оплаты
    /voting - голосование за тренировки
    /help - получение справки
    """
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['voting'])
def send_latest_poll(message):
    latest_poll = {
        "date": "06.06",
        "day": "Пятница",
        "year": 2025,
        "time": "14-00",
        'training_type': "Игровая",
        'location': "Энергия",
        'price': 500,
        "comment": "Для GD-free"
    }  # Пример опроса

    if latest_poll:
        question = "Волейбол - выберите подходящий вариант:"
        options = [
            f"{latest_poll['date']} ({latest_poll['day']}) {latest_poll['time']} - {latest_poll['training_type']} ({latest_poll['location']}, {latest_poll['price']} руб.) {latest_poll['comment']}",
            "Не пойду на волейбол"  # Добавляем второй вариант
        ]
        bot.send_poll(message.chat.id, question=question, options=options, is_anonymous=False)
    else:
        bot.send_message(message.chat.id, "Нет доступных опросов.")

@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    user_id = poll_answer.user.id
    poll_id = poll_answer.poll_id
    option_ids = poll_answer.option_ids

    # Здесь можно обработать результаты голосования, если это необходимо
    print(f"Пользователь {user_id} проголосовал в опросе {poll_id} с вариантами {option_ids}")
