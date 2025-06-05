import telebot
from telebot import types
import qrcode
from io import BytesIO
import datetime
import time
import threading
from shared_data import awaiting_confirmation, confirmed_payments
import admin
from ggl import write_name_to_google_sheet, authenticate_google_sheets
import schedule

users = {}
user_confirmed = {}
message_ids = {}
payment_timers = {}

def load_latest_poll():
    loaded_polls = admin.load_polls() 
    return loaded_polls

def get_user_ids():
    return list(users.keys())

def load_latest_poll():
    loaded_polls = admin.load_polls()  
    if not loaded_polls:
        return None

    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M")  
    current_date = now.strftime("%d.%m")

    eligible_polls = {}

    for poll_id, poll_data in loaded_polls.items():
        if isinstance(poll_data, list) and poll_data:
            eligible_options = []
            for option in poll_data:
                try:
                    scheduled_date = option.get('scheduled_date')
                    scheduled_time = option.get('scheduled_time')

                    if (scheduled_date < current_date) or (scheduled_date == current_date and scheduled_time <= current_time):
                        eligible_options.append(option)
                except (KeyError, ValueError, TypeError):
                    continue

            if eligible_options:
                eligible_polls[poll_id] = eligible_options

    latest_poll_id = None
    latest_created_at = None
    latest_poll_data = None

    for poll_id, poll_data in eligible_polls.items():
        try:
            created_at_str = poll_data[0].get('created_at')
            created_at = datetime.datetime.fromisoformat(created_at_str)
        except (KeyError, ValueError, TypeError, IndexError):
            continue

        if latest_created_at is None or created_at > latest_created_at:
            latest_created_at = created_at
            latest_poll_id = poll_id
            latest_poll_data = poll_data

    if latest_poll_id:
        return {latest_poll_id: latest_poll_data}
    else:
        return None

client = authenticate_google_sheets('vocal-circle-461812-m7-06081970720e.json')

def users_start_command(bot, message):
    global users
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    users[int(user_id)] = {"username": username, "chat_id": message.chat.id}

    default_commands = [
        telebot.types.BotCommand("start", "Начать работу с ботом"),
        telebot.types.BotCommand("status", "Проверить свой статус оплаты"),
        telebot.types.BotCommand("voting", "Голосовать за тренировки"),
        telebot.types.BotCommand("help", "Получить справку")
    ]
    bot.set_my_commands(commands=default_commands, scope=telebot.types.BotCommandScopeChat(chat_id=message.chat.id))

    bot.send_message(message.chat.id, f"Привет, {first_name}! Введите ваше полное имя и фамилию в формате 'Иван Иванов'")
    
    # Устанавливаем флаг ожидания
    users[user_id]['awaiting_name'] = True

def handle_name_input(bot, message):
    user_id = message.from_user.id
    if user_id in users and users[user_id].get('awaiting_name'):
        global full_name
        full_name = message.text.strip()
        # Записываем имя в Google таблицу
        write_name_to_google_sheet(client, "Тренировки", full_name, user_id)
        # Удаляем флаг ожидания
        users[user_id]['awaiting_name'] = False
        bot.send_message(message.chat.id, f"Спасибо, {full_name}! Ваше имя и фамилия сохранены. Для голосования используйте команду /voting")

def status(bot, message):
    user_id = message.from_user.id
    if user_id in users:
        try:
            if user_id in awaiting_confirmation:
                total_price = awaiting_confirmation[user_id]["total_price"]
                bot.reply_to(message, f"Ваша оплата не подтверждена администратором.")
            elif user_id in confirmed_payments:
                total_price = confirmed_payments[user_id]
                bot.reply_to(message, f"Ваша оплата на сумму {total_price} руб. подтверждена администратором.")
            else:
                bot.reply_to(message, "У вас нет активных оплат.")
        except Exception as e:
            bot.reply_to(message, f"Ошибка при проверке статуса оплаты: {e}")
    else:
        bot.reply_to(message, "Пожалуйста, сначала используйте команду /start, чтобы зарегистрироваться.")

def help_command(bot, message):
    help_text = """
        Список команд:
        /start - начало работы с ботом
        /status - проверка своего статуса оплаты
        /voting - голосование за тренировки
        /help - получение справки
        """
    bot.reply_to(message, help_text)

def voting(bot, message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    latest_poll = load_latest_poll()
    if user_id in users:
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
                
                # Initialize message_ids for the user
                message_ids[message.from_user.id] = {
                    "poll": sent_poll.message_id
                }
                
                print(f"Опрос отправлен пользователю {user_id}. ID опроса: {sent_poll.message_id}")
                
            except Exception as e:
                bot.send_message(chat_id, f"Не удалось создать опрос: {e}")
        else:
            bot.send_message(message.chat.id, "Нет доступных опросов.")
    else:
        bot.reply_to(message, "Пожалуйста, сначала используйте команду /start, чтобы зарегистрироваться.")
def handle_poll_answer(bot, poll_answer):
    user_id = poll_answer.user.id
    poll_id = poll_answer.poll_id
    option_ids = poll_answer.option_ids

    print(f"Пользователь {user_id} проголосовал в опросе {poll_id}. Выбранные варианты: {option_ids}")

    latest_poll = load_latest_poll()
    total_price = 0

    if latest_poll:
        poll_id_data, poll_data_item = list(latest_poll.items())[0]

        for index in option_ids:
            if index < len(poll_data_item):
                option = poll_data_item[index]
                if isinstance(option, dict):
                    price = option.get('price', 0)
                    total_price += price

        if not user_confirmed.get(user_id, False):
            menu = telebot.types.InlineKeyboardMarkup()
            confirm_yes_button = telebot.types.InlineKeyboardButton(
                text="Да", callback_data=f"confirm_{poll_id_data}_{total_price}"
            )
            confirm_no_button = telebot.types.InlineKeyboardButton(
                text="Нет", callback_data=f"re_{poll_id_data}"
            )
            menu.add(confirm_yes_button, confirm_no_button)

            # Отправляем сообщение с запросом на подтверждение
            poll_message = bot.send_message(user_id, f"Вы подтверждаете свои ответы?", reply_markup=menu)

            user_confirmed[user_id] = True
            message_ids[user_id] = {
                "poll": message_ids.get(user_id, {}).get("poll"),
                "confirm": poll_message.message_id
            }

            print(f"Пользователь {user_id} получил запрос на подтверждение голосования.")
        else:
            print(f"Пользователь {user_id} уже подтвердил свои ответы.")
            bot.send_message(user_id, "Вы уже подтвердили свои ответы.")

        # Запланировать отправку QR-кода за сутки до тренировки
        for index in option_ids:
            if index < len(poll_data_item):
                option = poll_data_item[index]
                if isinstance(option, dict):
                    training_info = {
                        'price': option['price'],
                        'date': option['date'],
                        'time': option['time'],
                        'payment_link': option['payment_link']
                    }
                    print(f"Запланирована отправка QR-кода за сутки до тренировки: {training_info}")
                    schedule_qr_code_send(bot, user_id, training_info)


def schedule_qr_code_send(bot, user_id, training_info):
    # Извлечение даты и времени тренировки
    training_date = training_info['date']
    training_time = training_info['time'].replace("-", ":")  # Заменяем '-' на ':'
    
    # Преобразование даты и времени в datetime
    scheduled_datetime = datetime.datetime.strptime(f"{training_date} {training_time}", "%d.%m %H:%M")
    send_time = scheduled_datetime - datetime.timedelta(days=1)  # За сутки до

    print(f"QR-код будет отправлен пользователю {user_id} в {send_time.strftime('%H:%M')} на дату {training_date}.")

    # Запланировать задачу
    schedule.every().day.at(send_time.strftime("%H:%M")).do(send_payment_info, bot, user_id, training_info)

def send_payment_info(bot, user_id, training_info):
    chat_id = users[user_id]["chat_id"]
    price = training_info['price']
    date = training_info['date']
    time = training_info['time']
    payment_link = training_info['payment_link']

    # Генерация QR-кода
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

    # Отправка QR-кода
    payment_message = bot.send_photo(
        chat_id,
        photo=bio,
        caption=f"Вы проголосовали за тренировки на {date} {time}. Сумма к оплате <b>{price} руб.</b> Для оплаты нажмите на кнопку или отсканируйте QR-код.",
        parse_mode="HTML",
    )
    bio.close()

    # Создание кнопки для оплаты
    keyboard = types.InlineKeyboardMarkup()
    pay_button = types.InlineKeyboardButton(text="Оплатить", url=payment_link)
    keyboard.add(pay_button)

    # Отправка сообщения с подтверждением оплаты
    confirm_keyboard = types.InlineKeyboardMarkup()
    confirm_button = types.InlineKeyboardButton(
        text="Да", callback_data=f"paid_{user_id}_{price}"
    )
    cancel_button = types.InlineKeyboardButton(
        text="Нет", callback_data=f"cancel_payment_{user_id}_{price}"
    )
    confirm_keyboard.add(confirm_button, cancel_button)

    confirm_message = bot.send_message(
        chat_id, f"Вы подтверждаете оплату?", reply_markup=confirm_keyboard
    )

    payment_timers[user_id] = {
        "qr_message_id": payment_message.message_id,
        "confirm_message_id": confirm_message.message_id,
        "chat_id": chat_id,
    }

    # Получаем имя пользователя из словаря users
    username = users.get(user_id, "Неизвестный пользователь")

    # Передаем имя пользователя в awaiting_confirmation
    awaiting_confirmation[user_id] = {
        "username": username,
        "confirm_message_id": confirm_message.message_id,
        "total_price": price
    }
    print(f"Пользователь {user_id} получил ссылку на оплату.")

def confirm_answers(bot, call):
    user_id = call.from_user.id
    data = call.data.split("_")

    if data[0] == "re":
        msgs = message_ids.get(user_id, {})
        if "confirm" in msgs:
            delete_message_safe(bot, call.message.chat.id, msgs["confirm"])
            bot.send_message(call.message.chat.id, "Вы подтвердили ответы, ожидайте QR-код за сутки до выбранной тренировки.")
        if "poll" in msgs:
            delete_message_safe(bot, call.message.chat.id, msgs["poll"])
        message_ids.pop(user_id, None)

        bot.send_message(call.message.chat.id, "Вы не подтвердили ваши ответы, для повторного голосования нажмите команду /voting")
        return

    if len(data) < 3:
        bot.answer_callback_query(call.id, "Неверные данные для подтверждения.")
        return

    poll_id = data[1]
    total_price = data[2]
    chat_id = call.message.chat.id

    bot.answer_callback_query(call.id)

    msgs = message_ids.get(user_id, {})
    if "confirm" in msgs:
        delete_message_safe(bot, chat_id, msgs["confirm"])
        bot.send_message(call.message.chat.id, "Вы подтвердили ответы, ожидайте QR-код за сутки до выбранной тренировки.")

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
            print(f"Отправка QR-кода не должна происходить здесь. Пользователь {user_id} подтвердил свои ответы, но QR-код не будет отправлен.")


def payment_timeout(bot, user_id, qr_info, total_price):
    start_time = time.time()

    while user_id in payment_timers:
        time.sleep(900)
        elapsed_time = time.time() - start_time

        if user_id in payment_timers:
            try:
                bot.delete_message(qr_info["chat_id"], qr_info["qr_message_id"])
                bot.delete_message(qr_info["chat_id"], qr_info["confirm_message_id"])
            except Exception as e:
                print(f"Ошибка удаления сообщения: {e}")

            bot.send_message(qr_info["chat_id"],
                            "Вы не подтвердили оплату и реквизиты были удалены. Нажмите команду /voting для повторного голосования.",)
            payment_timers.pop(user_id, None)

def resend_payment(bot, call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    total_price = call.data.split("_")[2]
    latest_poll = load_latest_poll()
    if latest_poll:
        poll_id, poll_data_item = list(latest_poll.items())[0]
        payment_link = poll_data_item[0].get("payment_link")
        send_payment_info(bot, user_id, chat_id, total_price)
        bot.answer_callback_query(call.id, "Реквизиты отправлены заново.")
    else:
        bot.send_message(chat_id, "Нет активных опросов.")

def cancel_payment(bot, call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    # Clear timer
    if user_id in payment_timers:
        payment_info = payment_timers.pop(user_id, None)
        try:
            bot.delete_message(chat_id, payment_info["qr_message_id"])
            bot.delete_message(chat_id, payment_info["confirm_message_id"])
        except Exception as e:
            print(f"Ошибка удаления сообщения: {e}")
    bot.send_message(
        chat_id, "Вы не подтвердили оплату, нажмите команду /voting для повторного голосования"
    )
    bot.answer_callback_query(call.id, "Оплата отменена.")

def payment_confirmation(bot, call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    if user_id in payment_timers:
        payment_info = payment_timers.pop(user_id, None)
        try:
            bot.delete_message(chat_id, payment_info["qr_message_id"])
            bot.delete_message(chat_id, payment_info["confirm_message_id"])
        except Exception as e:
            print(f"Ошибка удаления сообщения: {e}")
    bot.send_message(chat_id, f"Спасибо за оплату! Чтобы отслеживать статус тренировки нажмите команду /status")
    bot.answer_callback_query(call.id, "Оплата подтверждена, спасибо!")
    user_confirmed[user_id] = False

def delete_message_safe(bot, chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
        print(f"Удалено сообщение {message_id} в чате {chat_id}")
    except telebot.apihelper.ApiTelegramException as e:
        if 'message to delete not found' in str(e).lower():
            print(f"Сообщение для удаления {message_id} в чате {chat_id} не найдено, игнорируем.")
        else:
            print(f"Ошибка при удалении сообщения {message_id} в чате {chat_id}: {e}")



def handle_callback_query(bot, call):
    if call.data.startswith("cancel_payment_"):
        cancel_payment(bot, call)
    elif call.data.startswith("paid_"):
        payment_confirmation(bot, call)
    elif call.data.startswith("confirm_"):
        confirm_answers(bot, call)
    elif call.data.startswith("get_payment_"):
        resend_payment(bot, call)
    elif call.data.startswith("re"):
        confirm_answers(bot, call)
