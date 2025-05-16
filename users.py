import telebot
from telebot import types
import json
import os
from admin import get_latest_poll, load_polls
import qrcode
from io import BytesIO
import datetime

data = ""
with open('config.json', 'r') as file:
    data = json.load(file)

TOKEN = data.get("token")
bot = telebot.TeleBot(TOKEN)

users = {}
user_confirmed = {}
message_ids = {}

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
            payment_status = "Оплачено"  # Пример, здесь должна быть реальная логика проверки
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
        /status - проверка своего статуса оплаты
        /voting - голосование за тренировки
        /help - получение справки
        """
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['voting'])
def send_latest_poll(message):
    chat_id = message.chat.id
    latest_poll = get_latest_poll()

    if latest_poll:
        poll_id, poll_data_item = list(latest_poll.items())[0]

        question = "Волейбол - выберите подходящий вариант:"

        options = []
        if isinstance(poll_data_item, list):
            for option in poll_data_item:
                if isinstance(option, dict):
                    date = option.get('date', 'Не указана')
                    day = option.get('day', 'Не указан')
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

    latest_poll = get_latest_poll()
    total_price = 0
    payment_link = None

    if latest_poll:
        poll_id_data, poll_data_item = list(latest_poll.items())[0]

        if isinstance(poll_data_item, list) and len(poll_data_item) > 0:
            for index in option_ids:
                if index < len(poll_data_item):
                    option = poll_data_item[index]
                    if isinstance(option, dict):
                        price = option.get('price', 0)
                        total_price += price
            if not user_confirmed.get(user_id, False): #Проверяем, показывался ли уже запрос подтверждения
                menu = telebot.types.InlineKeyboardMarkup()
                menu.add(types.InlineKeyboardButton("Подтвердить", callback_data=f"confirm_{poll_id_data}_{total_price}"))
                #Отправляем кнопку подтверждения
                confirmation_message = bot.send_message(chat_id, f"Вы подтверждаете свои ответы?", reply_markup=menu)
                user_confirmed[user_id] = True  #Отмечаем, что подтверждение показано
                #Сохраняем message_id подтверждения
                message_ids[user_id] = message_ids.get(user_id, {})
                message_ids[user_id]["confirm"] = confirmation_message.message_id

        else:
            bot.send_message(chat_id, "Не удалось получить данные о тренировках.")

    else:
        bot.send_message(chat_id, "Нет активных опросов.")

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

    latest_poll = get_latest_poll()
    if latest_poll:
        poll_id, poll_data_item = list(latest_poll.items())[0]

        payment_message = None

        if isinstance(poll_data_item, list) and len(poll_data_item) > 0:
           #Iterate in the items to get everything
            for option in poll_data_item: #Now we should iterate in this.
                if isinstance(option, dict):
                   payment_link = option.get('payment_link') #To last position

        if total_price == "0":
            bot.send_message(chat_id, "Ваши ответы подтверждены. Спасибо!")
        else:
             # Create inline keyboard with the payment link
            keyboard = types.InlineKeyboardMarkup()
            pay_button = types.InlineKeyboardButton(text="Оплатить", url=payment_link)
            keyboard.add(pay_button)

            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(payment_link)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            bio = BytesIO()
            img.save(bio, 'PNG')
            bio.seek(0)

            # Send the message with the QR code and payment button
            bot.send_photo(chat_id, photo=bio, caption=f"Ваши ответы подтверждены. Общая сумма: {total_price} руб.\nДля оплаты нажмите на кнопку или отсканируйте QR-код.", reply_markup=keyboard)
            bio.close()

    user_confirmed[user_id] = False

@bot.message_handler(commands=['get_qr'])
def get_qr_code(message):
    bot.send_message(message.chat.id, "Вам больше не нужна эта команда! QR-код теперь автоматически отправляется после подтверждения ваших ответов.")
#def send_qr_code(message, poll_id):

if __name__ == "__main__":
    print("User bot started!")
    bot.polling()