import telebot
from telebot import types
import json
import os
from admin import is_admin, get_latest_poll  # Импортируем функцию для получения последнего опроса

data = ""
with open('config.json', 'r') as file:
    data = json.load(file)

TOKEN = data.get("token")
bot = telebot.TeleBot(TOKEN)

# Словарь для хранения ID пользователей (можно заменить на базу данных)
users = {}  # {user_id: username} - пример структуры

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
    if user_id in users:
        print(f"Запрос статуса от пользователя: {user_id}")
        try:
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
    latest_poll = get_latest_poll()  # Получаем самый свежий опрос

    if latest_poll:
        poll_id, poll_options = list(latest_poll.items())[0]  # Получаем ID и все варианты опроса
        question = "Волейбол - выберите подходящий вариант:"
        
        options = []
        for option in poll_options:
            options.append(f"{option['date']} ({option['day']}) {option['time']} - {option['training_type']} ({option['location']}, {option['price']} руб.) {option['comment']}")
        
        options.append("Не пойду на волейбол")  # Добавляем вариант по умолчанию

        # Убедитесь, что здесь также установлен allows_multiple_answers=True
        bot.send_poll(message.chat.id, question=question, options=options, is_anonymous=False, allows_multiple_answers=True)
    else:
        bot.send_message(message.chat.id, "Нет доступных опросов.")

@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    user_id = poll_answer.user.id
    poll_id = poll_answer.poll_id
    option_ids = poll_answer.option_ids

    # Здесь можно обработать результаты голосования, если это необходимо
    print(f"Пользователь {user_id} проголосовал в опросе {poll_id} с вариантами {option_ids}")

if __name__ == "__main__":
    print("User bot started!")
    bot.polling()