import telebot
from telebot import types
import json
import os

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
    first_name = message.from_users.first_name
    last_name = message.from_users.last_name

    # Сохраняем ID пользователя (если необходимо)
    users_id[users_id] = usersname

    # Устанавливаем дефолтные команды для текущего пользователя
    default_commands = [
        telebot.types.BotCommand("start", "Начать работу с ботом"),
        telebot.types.BotCommand("status", "Проверить свой статус оплаты"),
        telebot.types.BotCommand("voting", "Голосовать за тренировки"),
        telebot.types.BotCommand("help", "Получить справку")
    ]
    bot.set_my_commands(commands=default_commands, scope=telebot.types.BotCommandScopeChat(chat_id=message.chat.id))


    bot.reply_to(message, f"Привет, {first_name}! ...")
    print(f"Новый пользователь: ...")

@bot.message_handler(commands=['status'])
def status(message):
    users_id = message.from_users.id
    # Проверяем, есть ли ID пользователя в нашем словаре (или базе данных)
    if users_id in users_id:
        print(f"Запрос статуса от пользователя: {users_id}")
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
    # latest_poll = get_latest_poll() # Убрал, так как этого файла у меня нет, чтобы не выдавало ошибку
    latest_poll = {'date': '2024-01-01', 'day': 'Пн', 'time': '19:00', 'training_type': 'Обучение', 'location': 'Зал 1', 'price': 500} # Добавил, чтобы код запускался

    if latest_poll:
        question = "Волейбол - выберите подходящий вариант:"
        options = [
            f"{latest_poll['date']} ({latest_poll['day']}) {latest_poll['time']} - {latest_poll['training_type']} ({latest_poll['location']}, {latest_poll['price']} руб.)"
        ]
        bot.send_poll(message.chat.id, question=question, options=options, is_anonymous=False)
    else:
        bot.send_message(message.chat.id, "Нет доступных опросов.")
@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    users_id = poll_answer.users.id
    poll_id = poll_answer.poll_id
    option_ids = poll_answer.option_ids

    # Здесь можно обработать результаты голосования, если это необходимо
    print(f"Пользователь {users_id} проголосовал в опросе {poll_id} с вариантами {option_ids}")
