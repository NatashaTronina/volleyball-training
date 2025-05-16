# user.py (Revised)

import telebot
from telebot import types
import json
import os
from admin import is_admin, get_latest_poll  # Import admin bot
# from admin import bot as admin_bot  # Not needed, as we don't send the QR code from here
import qrcode

data = ""
with open('config.json', 'r') as file:
    data = json.load(file)

TOKEN = data.get("token")
bot = telebot.TeleBot(TOKEN)

users = {}  # {user_id: username}
user_confirmed = {}  # Track if a user has confirmed for a poll


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    users[user_id] = username

    default_commands = [
        telebot.types.BotCommand("start", "Начать работу с ботом"),
        telebot.types.BotCommand("status", "Проверить свой статус оплаты"),
        telebot.types.BotCommand("voting", "Голосовать за тренировки"),
        telebot.types.BotCommand("help", "Получить справку"),
        telebot.types.BotCommand("get_qr", "Получить QR-код для оплаты"),
    ]
    bot.set_my_commands(commands=default_commands, scope=telebot.types.BotCommandScopeChat(chat_id=message.chat.id))

    bot.send_message(message.chat.id, f"Привет, {first_name}! Для голосования за тренировки нажми команду /voting")


@bot.message_handler(commands=['status'])
def status(message):
    user_id = message.from_user.id
    if user_id in users:
        print(f"Запрос статуса от пользователя: {user_id}")
        try:
            payment_status = "Оплачено"  # Example
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
    /get_qr - Получить QR-код после голосования
    """
    bot.reply_to(message, help_text)


@bot.message_handler(commands=['voting'])
def send_latest_poll(message):
    chat_id = message.chat.id
    latest_poll = get_latest_poll()

    if latest_poll:
        poll_id, poll_options = list(latest_poll.items())[0]
        question = "Волейбол - выберите подходящий вариант:"

        options = []
        for option in poll_options:
            if isinstance(option, dict):
                date = option.get('date', 'Не указана')
                day = option.get('day', 'Не указан')
                time = option.get('time', 'Не указано')
                training_type = option.get('training_type', 'Не указан')
                price = option.get('price', 'Не указана')
                location = option.get('location', 'Не указано')
                comment = option.get('comment', '')
                options.append(f"{date} ({day}) {time} - {training_type} ({location}, {price} руб.) {comment}")

        options.append("Не пойду на волейбол")
        # Send poll and store the poll id
        try:
           sent_poll = bot.send_poll(message.chat.id, question=question, options=options, is_anonymous=False, allows_multiple_answers=True)
           user_confirmed[message.from_user.id] = False  # Reset confirmation status
        except Exception as e:
            bot.send_message(chat_id, f"Не удалось создать опрос: {e}")

    else:
        bot.send_message(message.chat.id, "Нет доступных опросов.")


@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    user_id = poll_answer.user.id
    poll_id = poll_answer.poll_id
    option_ids = poll_answer.option_ids
    chat_id = poll_answer.user.id

    latest_poll = get_latest_poll()
    total_price = 0
    has_paid_option = False

    if latest_poll:
        poll_id, poll_options = list(latest_poll.items())[0]
        #Correct handling

        if isinstance(poll_options, list) and len(poll_options) > 0:
            # Correct handling
            for index in option_ids:
                if index < len(poll_options):
                    if isinstance(poll_options[index], dict):
                        price = poll_options[index].get('price', 0)
                        total_price += price

        #Check for the existing status
        if not user_confirmed.get(user_id, False):
            menu = telebot.types.InlineKeyboardMarkup()
            menu.add(types.InlineKeyboardButton("Подтвердить", callback_data=f"confirm_{poll_id}_{total_price}"))
            bot.send_message(chat_id, f"Вы подтверждаете свои ответы?", reply_markup=menu)
            user_confirmed[user_id] = True  # Mark as shown


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def confirm_answers(call):
    user_id = call.from_user.id
    poll_data = call.data.split("_")
    poll_id = poll_data[1]
    total_price = poll_data[2]
    bot.answer_callback_query(call.id)

    if total_price == "0":
        bot.send_message(call.message.chat.id, "Ваши ответы подтверждены. Спасибо!")
    else:
        bot.send_message(call.message.chat.id, f"Ваши ответы подтверждены. <b>Общая сумма: {total_price} руб.</b> Спасибо!", parse_mode='HTML')

if __name__ == "__main__":
    print("User bot started!")
    bot.polling()