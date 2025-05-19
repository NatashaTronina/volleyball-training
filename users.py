import telebot
from telebot import types
import json
import os
from admin import load_polls
import qrcode
from io import BytesIO
import datetime
import time
import threading

data = ""
with open('config.json', 'r') as file:
    data = json.load(file)

TOKEN = data.get("token")
bot = telebot.TeleBot(TOKEN)

users = {}
user_confirmed = {}
message_ids = {}
payment_timers = {}

def load_latest_poll():
    loaded_polls = load_polls()
    if not loaded_polls:
        return None

    # Find the poll with the latest 'created_at'
    latest_poll_id = None
    latest_created_at = None
    latest_poll_data = None

    for poll_id, poll_data in loaded_polls.items():
        if isinstance(poll_data, list) and poll_data:
            # Use the creation time of the first option in the poll
            try:
                created_at_str = poll_data[0].get('created_at')
                created_at = datetime.datetime.fromisoformat(created_at_str)
            except (KeyError, ValueError, TypeError):
                # Skip polls without a valid 'created_at'
                continue

            if latest_created_at is None or created_at > latest_created_at:
                latest_created_at = created_at
                latest_poll_id = poll_id
                latest_poll_data = poll_data

    if latest_poll_id:
        print(f"Latest poll found with id: {latest_poll_id}")
        return {latest_poll_id: latest_poll_data}
    else:
        print("No valid polls found.")
        return None

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
            payment_status = "Оплачено"
            bot.reply_to(message, f"Ваш статус оплаты: {payment_status}")
        except Exception as e:
            bot.reply_to(message, f"Ошибка при проверке статуса оплаты: {e}")
    else:
        bot.reply_to(message, "Пожалуйста, сначала используйте команду /start, чтобы зарегистрироваться.")

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """
        Список команд:
        /start - начало работы с ботом
        /status - проверка своего статуса оплаты"),
        /voting - голосование за тренировки"),
        /help - получение справки
        """
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['voting'])
def send_latest_poll(message):
    chat_id = message.chat.id
    latest_poll = load_latest_poll()

    if latest_poll:
        poll_id, poll_data_item = list(latest_poll.items())[0]

        question = "Волейбол - выберите подходящий вариант:"

        options = []
        if isinstance(poll_data_item, list):
            for option in poll_data_item:
                if isinstance(option, dict):
                    date = option.get('date', 'Не указана')
                    day = option.get('day', 'Не указано')
                    time = option.get('time', 'Не указано')
                    training_type = option.get('training_type', 'Не указано')
                    price = option.get('price', 0)
                    location = option.get('location', 'Не указано')
                    comment = option.get('comment', '')
                    option_string = f"{date} ({day}) {time} - {training_type} ({location}, {price} руб.) {comment}"
                    if len(option_string) > 90:
                        option_string = option_string[:87] + "..."
                    options.append(option_string)

        options.append("Не пойду на волейбол")
        try:
           sent_poll = bot.send_poll(message.chat.id, question=question, options=options, is_anonymous=False, allows_multiple_answers=True)
           user_confirmed[message.from_user.id] = False
           message_ids[message.from_user.id] = message_ids.get(message.from_user.id, {})
           message_ids[message.from_user.id]["poll"] = sent_poll.message_id
        except Exception as e:
            bot.send_message(chat_id, f"Не удалось создать опрос: {e}")
    else:
        bot.send_message(message.chat.id, "Нет доступных опросов.")

@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    user_id = poll_answer.user.id
    poll_id = poll_answer.poll_id
    option_ids = poll_answer.option_ids
    chat_id = user_id

    latest_poll = load_latest_poll()
    total_price = 0

    if latest_poll:
        poll_id_data, poll_data_item = list(latest_poll.items())[0]

        if isinstance(poll_data_item, list) and len(poll_data_item) > 0:
            for index in option_ids:
                if index < len(poll_data_item):
                    option = poll_data_item[index]
                    if isinstance(option, dict):
                        price = option.get('price', 0)
                        total_price += price
            if not user_confirmed.get(user_id, False):
                menu = telebot.types.InlineKeyboardMarkup()
                menu.add(types.InlineKeyboardButton("Подтвердить", callback_data=f"confirm_{poll_id_data}_{total_price}"))
                confirmation_message = bot.send_message(user_id, f"Вы подтверждаете свои ответы?", reply_markup=menu)

                user_confirmed[user_id] = True
                message_ids[user_id] = message_ids.get(user_id, {})
                message_ids[user_id]["confirm"] = confirmation_message.message_id

        else:
            bot.send_message(chat_id, "Не удалось получить данные о тренировках.")

    else:
        bot.send_message(chat_id, "Нет активных опросов.")

def payment_timeout(user_id, qr_info, total_price):
    print(f"Функция payment_timeout вызвана для пользователя {user_id}")
    start_time = time.time() 

    while user_id in payment_timers:  
        time.sleep(10)  # поменять
        elapsed_time = time.time() - start_time 

        if user_id in payment_timers:
            print(f"Прошло 15 минут для пользователя {user_id}. Проверяем, подтверждена ли оплата...")
            try:
                bot.delete_message(qr_info["chat_id"], qr_info["qr_message_id"])  # Delete QR code message
                bot.delete_message(qr_info["chat_id"], qr_info["confirm_message_id"])  # Delete confirmation message
            except Exception as e:
                print(f"Error deleting message: {e}")

            bot.send_message(qr_info["chat_id"], "Вы не подтвердили оплату и реквизиты были удалены. Нажмите команду /voting для повторного голосования.")
            payment_timers.pop(user_id, None) 

def show_payment(user_id, chat_id, total_price):

    latest_poll = load_latest_poll()
    if latest_poll:
        poll_id, poll_data_item = list(latest_poll.items())[0]

 
        payment_link = poll_data_item[0].get("payment_link")


        if not payment_link:
            return bot.send_message(chat_id, "Отсутствует ссылка для оплаты, обратитесь к Администратору.")


        keyboard = types.InlineKeyboardMarkup()
        pay_button = types.InlineKeyboardButton(text="Оплатить", url=payment_link)
        keyboard.add(pay_button)

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(payment_link)
        qr.make(fit=True)
        img = qr.make_image(fill_color="rgb(142, 146, 250)", back_color="white")

        bio = BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)

        payment_message = bot.send_photo(chat_id, photo=bio, caption=f"Ваши ответы подтверждены. Общая сумма: <b>{total_price}</b> руб.\nДля оплаты нажмите на кнопку или отсканируйте QR-код.", reply_markup=keyboard, parse_mode="HTML")
        bio.close()

        # Keyboard with confirmation buttons (yes/no)
        confirm_keyboard = types.InlineKeyboardMarkup()
        confirm_button = types.InlineKeyboardButton(text="Да", callback_data=f"paid_{user_id}_{total_price}")
        cancel_button = types.InlineKeyboardButton(text="Нет", callback_data=f"cancel_payment_{user_id}_{total_price}")
        confirm_keyboard.add(confirm_button, cancel_button)
        confirm_message = bot.send_message(chat_id, f"Вы подтверждаете оплату?", reply_markup=confirm_keyboard)

        # Save QR code, confirm message IDs to payment_timers
        payment_timers[user_id] = {
            "qr_message_id": payment_message.message_id,
            "confirm_message_id": confirm_message.message_id,
            "chat_id": chat_id
        }

        return payment_message
    else:
         bot.send_message(chat_id, "Нет активных опросов.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("get_payment_"))
def resend_payment(call):
     user_id = call.from_user.id
     chat_id = call.message.chat.id
     total_price = call.data.split("_")[2]
     latest_poll = load_latest_poll()
     if latest_poll:
        poll_id, poll_data_item = list(latest_poll.items())[0]
        payment_link = poll_data_item[0].get("payment_link")
        show_payment(user_id, chat_id, total_price)
        bot.answer_callback_query(call.id, "Реквизиты отправлены заново.")
     else:
        bot.send_message(chat_id, "Нет активных опросов.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_payment_"))
def cancel_payment(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
     #Clear timer
    if user_id in payment_timers:
        payment_info = payment_timers.pop(user_id, None)
        try:
            bot.delete_message(chat_id, payment_info["qr_message_id"])
            bot.delete_message(chat_id, payment_info["confirm_message_id"])
        except Exception as e:
            print(f"Error deleting message: {e}")
    bot.send_message(chat_id, "Вы не подтвердили оплату, нажмите команду /voting для повторного голосования")
    bot.answer_callback_query(call.id, "Оплата отменена.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("paid_"))
def payment_confirmation(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    #Clear timer
    if user_id in payment_timers:
        payment_info = payment_timers.pop(user_id, None)
        try:
            bot.delete_message(chat_id, payment_info["qr_message_id"])
            bot.delete_message(chat_id, payment_info["confirm_message_id"])
        except Exception as e:
            print(f"Error deleting message: {e}")
    bot.send_message(chat_id, "Спасибо за оплату!")
    bot.answer_callback_query(call.id, "Оплата подтверждена, спасибо!")
    user_confirmed[user_id] = False

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def confirm_answers(call):
    user_id = call.from_user.id
    data = call.data.split("_")
    if len(data) < 3:
        bot.answer_callback_query(call.id, "Неверные данные для подтверждения.")
        return

    poll_id = data[1]
    total_price = data[2]
    chat_id = call.message.chat.id

    bot.answer_callback_query(call.id)

    msgs = message_ids.get(user_id, {})
    if "confirm" in msgs:
        try:
            bot.delete_message(chat_id, msgs["confirm"])
        except Exception as e:
            print(f"Ошибка удаления сообщения подтверждения: {e}")
    if "poll" in msgs:
        try:
            bot.delete_message(chat_id, msgs["poll"])
        except Exception as e:
            print(f"Ошибка удаления сообщения с опросом: {e}")

    message_ids.pop(user_id, None)

    latest_poll = load_latest_poll()

    if latest_poll:
        poll_id, poll_data_item = list(latest_poll.items())[0]

        if isinstance(poll_data_item, list) and len(poll_data_item) > 0:
            payment_link = None

            for option in poll_data_item:
                if isinstance(option, dict):
                    payment_link = option.get('payment_link')
        if total_price == "0":
            bot.send_message(chat_id, "Ваши ответы подтверждены. Спасибо!")
            user_confirmed[user_id] = False
        else:
            payment_message = show_payment(user_id, chat_id, total_price)
            print(f"Запущен таймер оплаты для пользователя {user_id}")
            # Запускаем таймер оплаты только если show_payment вернул не None
            if payment_message:
                qr_info = payment_timers.get(user_id)
                if qr_info:
                    threading.Thread(target=payment_timeout, args=(user_id, qr_info, total_price)).start()

if __name__ == "__main__":
    print("User bot started!")
    bot.infinity_polling()