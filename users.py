import telebot
from telebot import types
import qrcode
from io import BytesIO
import datetime
import time
from shared_data import awaiting_confirmation
import admin
from ggl import write_name_to_google_sheet, authenticate_google_sheets, update_training_status
import schedule
import uuid
import time

USER_TRAININGS_CACHE = {}
CACHE_EXPIRATION_TIME = 600

users = {}
ADMIN_ID = [494635818]
user_confirmed = {}
message_ids = {}
payment_timers = {}

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
    
    users[user_id]['awaiting_name'] = True

def handle_name_input(bot, message):
    user_id = message.from_user.id
    if user_id in users and users[user_id].get('awaiting_name'):
        global full_name
        full_name = message.text.strip()
        write_name_to_google_sheet(client, "Тренировки", full_name, user_id)
        users[user_id]['awaiting_name'] = False
        bot.send_message(message.chat.id, f"Спасибо, {full_name}! Ваше имя и фамилия сохранены. \nЕсли вы неверно ввели данные, используйте команду /start \nДля голосования используйте команду /voting")

def status(bot, message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id not in users:
        bot.reply_to(message, "Пожалуйста, сначала используйте команду /start, чтобы зарегистрироваться.")
        return

    try:
        training_list = get_user_trainings(bot, user_id)
        message_text = "Ваш статус:\n"

        if not training_list:
            message_text += "Нет активных тренировок\n"
        else:
            last_trainings = training_list[-3:]
            for i, training in enumerate(last_trainings):
                message_text += f"{i+1}) {training['date']} ({training['price']} руб) : {training['status']}\n"

        keyboard = types.InlineKeyboardMarkup()
        cancel_button = types.InlineKeyboardButton(text="Отменить тренировки", callback_data="cancel_trainings")
        keyboard.add(cancel_button)

        status_message = bot.send_message(chat_id, message_text, reply_markup=keyboard) 
        users[user_id]['status_message_id'] = status_message.message_id 
            
    except Exception as e:
        bot.reply_to(message, f"Ошибка при проверке статуса: {e}")

def get_user_trainings(bot, user_id):

    try:
        sheet = client.open("Тренировки")
        worksheet = sheet.worksheet("В.Расход")

        user_ids = worksheet.col_values(2)


        training_list = []

        if str(user_id) in user_ids:
            row_index = user_ids.index(str(user_id)) + 1

            data_range = f'R{row_index}C10:R{row_index}C{worksheet.col_count}'
            header_range = '4:4'  
            price_range = '3:3'

            batch_result = worksheet.batch_get([data_range, header_range, price_range])

            if len(batch_result) == 3:
                row_data = batch_result[0][0] if batch_result[0] else []
                header_row = batch_result[1][0] if batch_result[1] else []
                price_row = batch_result[2][0] if batch_result[2] else []

                selected_training_infos = get_selected_trainings_from_poll()


                for i, status in enumerate(row_data):
                    if i < len(header_row) and i < len(price_row): 
                        training_info = {'date': header_row[i + 9], 'price': price_row[i+9]}
                        if training_info in selected_training_infos:
                            if status in ("*", "0", "1"):
                                status = "Ожидает оплаты" if status == "*" else (
                                    "Оплата ожидает подтверждения" if status == "0" else "Админ подтвердил оплату")
                                training = {
                                    "date": header_row[i + 9], 
                                    "price": price_row[i + 9], 
                                    "status": status 
                                }
                                training_list.append(training)
        return training_list

    except Exception as e:
        print(f"get_user_trainings: Ошибка при получении тренировок: {e}")
        return []
    
def get_selected_trainings_from_poll():
    latest_poll = load_latest_poll()
    selected_training_infos = []
    if latest_poll:
        poll_id, poll_data_item = list(latest_poll.items())[0]
        if isinstance(poll_data_item, list):
            for option in poll_data_item:
                if isinstance(option, dict) and 'date' in option and 'price' in option:
                   selected_training_infos.append({'date': option['date'], 'price': str(option['price'])})
    return selected_training_infos

def clear_user_trainings_cache(user_id):
    if user_id in USER_TRAININGS_CACHE:
        del USER_TRAININGS_CACHE[user_id]

def help_command(bot, message):
    help_text = """
        Список команд:
        /start - начало работы с ботом, регистрация
        /status - проверка своего статуса оплаты, отмена тренировки
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
                
                message_ids[message.from_user.id] = {
                    "poll": sent_poll.message_id
                }
                
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

    latest_poll = load_latest_poll()

    if latest_poll:
        poll_id_data, poll_data_item = list(latest_poll.items())[0]

        selected_training_infos = []
        total_price = 0

        for index in option_ids:
            if index < len(poll_data_item):
                option = poll_data_item[index]
                if isinstance(option, dict):
                    price = option.get('price', 0)
                    total_price += price
                    selected_training_infos.append(option)

        if not user_confirmed.get(user_id, False):
            menu = telebot.types.InlineKeyboardMarkup()
            option_ids_str = ','.join(map(str, option_ids))
            confirm_yes_button = telebot.types.InlineKeyboardButton(
                text="Да", callback_data=f"confirm_{poll_id_data}_{total_price}_{option_ids_str}")
            confirm_no_button = telebot.types.InlineKeyboardButton(
                text="Нет", callback_data=f"re_{poll_id_data}")
            menu.add(confirm_yes_button, confirm_no_button)

            poll_message = bot.send_message(user_id, f"Вы подтверждаете свои ответы?", reply_markup=menu)

            user_confirmed[user_id] = True
            message_ids[user_id] = {
                "poll": message_ids.get(user_id, {}).get("poll"),
                "confirm": poll_message.message_id}
        else:
            bot.send_message(user_id, "Вы уже подтвердили свои ответы.")
    else:
        bot.send_message(user_id, "Нет доступных тренировок для голосования.")



def schedule_qr_code_send(bot, user_id, training_info):
    training_date = training_info['date']
    training_time = training_info['time'].replace("-", ":") 

    try:
        current_datetime = datetime.datetime.now()
        scheduled_datetime = datetime.datetime.strptime(f"{training_date}.{training_info['year']} {training_time}", "%d.%m.%Y %H:%M")
        time_difference = scheduled_datetime - current_datetime

        if time_difference <= datetime.timedelta(days=1):
            send_payment_info(bot, user_id, training_info)
        else:
    
            send_time = scheduled_datetime - datetime.timedelta(days=1) 
            schedule.every().day.at(send_time.strftime("%H:%M")).do(lambda: send_payment_info(bot, user_id, training_info))

    except ValueError as e:
        print(f"schedule_qr_code_send: Ошибка при обработке даты и времени: {e}")
        bot.send_message(user_id, "Произошла ошибка при обработке даты и времени тренировки. Обратитесь к администратору.")

def send_payment_info(bot, user_id, training_info):
    chat_id = training_info.get('chat_id')
    if not chat_id:
        return

    price = training_info['price']
    date = training_info['date']
    time = training_info['time']
    payment_link = training_info['payment_link']

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=15,
        border=2,
    )
    qr.add_data(payment_link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="rgb(255, 221, 45)")

    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)

    keyboard = types.InlineKeyboardMarkup()
    pay_button = types.InlineKeyboardButton(text="Оплатить по СБП", url=payment_link)
    keyboard.add(pay_button)

    payment_message = bot.send_photo(
        chat_id,
        photo=bio,
        caption=f"Вы проголосовали за тренировки на <b>{date} {time}.</b> \nСумма к оплате <b>{price} руб.</b> Для оплаты нажмите на кнопку или отсканируйте QR-код.",
        parse_mode="HTML",
        reply_markup=keyboard  
    )
    bio.close()
    username = users.get(user_id, {}).get('username', "Неизвестный пользователь") 

    unique_payment_id = str(uuid.uuid4())

    confirm_keyboard = types.InlineKeyboardMarkup()
    confirm_button = types.InlineKeyboardButton(
        text="Да", callback_data=f"paid_{unique_payment_id}_{price}"
    )
    cancel_button = types.InlineKeyboardButton(
        text="Нет", callback_data=f"cancel_payment_{user_id}_{price}"
    )
    confirm_keyboard.add(confirm_button, cancel_button)

    confirm_message = bot.send_message(chat_id, f"Вы подтверждаете оплату?", reply_markup=confirm_keyboard)

    if user_id not in awaiting_confirmation:
        awaiting_confirmation[user_id] = {}

    awaiting_confirmation[user_id][unique_payment_id] = {
        "username": username,
        "chat_id": training_info['chat_id'],
        "confirm_message_id": confirm_message.message_id,
        "qr_message_id": payment_message.message_id,
        "total_price": training_info['price'],
        "unique_payment_id": unique_payment_id,
        "date": training_info['date'], 
        "price": training_info['price']
    }

def confirm_answers(bot, call):
    user_id = call.from_user.id
    data = call.data.split("_")
    chat_id = call.message.chat.id

    bot.answer_callback_query(call.id)

    if data[0] == "re":
        msgs = message_ids.get(user_id, {})
        if "confirm" in msgs:
            delete_message_safe(bot, chat_id, msgs["confirm"])
        if "poll" in msgs:
            delete_message_safe(bot, chat_id, msgs["poll"])
        message_ids.pop(user_id, None)

        bot.send_message(chat_id, "Вы не подтвердили ваши ответы, для повторного голосования нажмите команду /voting")
        return

    if len(data) < 3:
        bot.answer_callback_query(call.id, "Неверные данные для подтверждения.")
        return

    poll_id = data[1]
    total_price = data[2]
    selected_indices = data[3].split(',')


    msgs = message_ids.get(user_id, {})
    message_ids.pop(user_id, None)

    latest_poll = load_latest_poll()

    if latest_poll:
        poll_id, poll_data_item = list(latest_poll.items())[0]


        selected_training_infos = []

        if len(selected_indices) == 1 and int(selected_indices[0]) == len(poll_data_item):
            if "confirm" in msgs:
                delete_message_safe(bot, chat_id, msgs["confirm"])
                message_ids.pop(user_id, None)

            bot.send_message(chat_id, "Спасибо за ответы!")
            return
        else:
            for index in selected_indices:
                try:
                    index = int(index)
                    selected_training_infos.append(poll_data_item[index])
                except ValueError as e:
                    print(f"confirm_answers: Некорректный индекс: {index}, Ошибка: {e}")
                except IndexError as e:
                    print(f"confirm_answers: Индекс за пределами списка: {index}, Ошибка: {e}")


        if "confirm" in msgs:
            delete_message_safe(bot, chat_id, msgs["confirm"])
            message_ids.pop(user_id, None)
        if not selected_training_infos:
            bot.send_message(chat_id, "Вы не выбрали ни одной тренировки.")
            return

        bot.send_message(chat_id, "Ожидайте QR-код для выбранных тренировок")

        for training_info in selected_training_infos:
            training_info['chat_id'] = users.get(user_id, {}).get('chat_id')
            if training_info['chat_id']:
                schedule_qr_code_send(bot, user_id, training_info)
                update_training_status(client, "Тренировки", user_id, training_info, "*")

        user_confirmed.clear()

        if total_price == "0":
            bot.send_message(chat_id, "Ваши ответы подтверждены. Спасибо!")
            user_confirmed[user_id] = False

def payment_timeout(bot, user_id, qr_info, total_price):
    start_time = time.time()

    while user_id in payment_timers:
        time.sleep(82800)
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
    callback_data = call.data.split("_")
    unique_payment_id = callback_data[1]
    price = callback_data[2]

    if user_id in awaiting_confirmation:
        if unique_payment_id in awaiting_confirmation[user_id]:
            payment_info = awaiting_confirmation[user_id][unique_payment_id]

            qr_message_id = payment_info.get("qr_message_id")
            confirm_message_id = payment_info.get("confirm_message_id")

            if qr_message_id:
                try:
                    bot.delete_message(chat_id, qr_message_id)
                except Exception as e:
                    print(f"Ошибка удаления сообщения с QR-кодом: {e}")

            if confirm_message_id:
                try:
                    bot.delete_message(chat_id, confirm_message_id)
                except Exception as e:
                    print(f"Ошибка удаления сообщения 'Вы подтверждаете оплату?': {e}")

            bot.send_message(chat_id, "Спасибо за оплату! Чтобы отслеживать статус тренировки и подтверждение оплаты нажмите команду /status")
            update_training_status(client, "Тренировки", user_id, payment_info, "0")
            clear_user_trainings_cache(user_id)
        else:
            bot.send_message(chat_id, "Ошибка: Оплата не найдена.")

    else:
        bot.send_message(chat_id, "Ошибка: Оплата не найдена.")
        bot.send_message(chat_id, "Ошибка: Запрос на подтверждение не найден.")

def delete_message_safe(bot, chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception as e:
        print(f"delete_message_safe: Не удалось удалить сообщение {message_id} в чате {chat_id}: {e}")

def show_cancel_options(bot, call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    training_list = get_user_trainings(bot, user_id)

    if not training_list:
        bot.send_message(chat_id, "Вы не записаны ни на одну тренировку.")
        return

    keyboard = types.InlineKeyboardMarkup(row_width=3)
    for i, training in enumerate(training_list):
        button = types.InlineKeyboardButton(
            text=f"{i + 1}) {training['date']} ({training['price']} руб)",
            callback_data=f"cancel_training_confirmed_{i}"
        )
        keyboard.add(button)

    bot.send_message(chat_id, "Выберите тренировку для отмены:", reply_markup=keyboard)

def cancel_training(bot, user_id, training_to_cancel):
    try:
        sheet = client.open("Тренировки")
        worksheet = sheet.worksheet("В.Расход")

        user_ids = worksheet.col_values(2)
        if str(user_id) in user_ids:
            row_index = user_ids.index(str(user_id)) + 1

            training_date = training_to_cancel['date']
            training_price = str(training_to_cancel['price'])

            header_row = worksheet.row_values(4)
            date_column_index = None

            for i in reversed(range(len(header_row))):
                if header_row[i] == training_date:
                    price_row = worksheet.row_values(3)
                    if i < len(price_row) and price_row[i] == training_price:
                        date_column_index = i + 1
                        break

            if date_column_index:
                cell_value = worksheet.cell(row_index, date_column_index).value

                if cell_value in ("0", "1"):
                    worksheet.update_cell(row_index, date_column_index, "#")
                elif cell_value == "*":
                    worksheet.update_cell(row_index, date_column_index, "")
    except Exception as e:
        print(f"Ошибка при отмене тренировки в Google Sheets: {e}")

def cancel_training_confirmed(bot, call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    training_index = int(call.data.split("_")[-1])

    training_list = get_user_trainings(bot, user_id)

    if not training_list:
        bot.send_message(chat_id, "У вас нет записанных тренировок для отмены.")
        return

    if 0 <= training_index < len(training_list):
        training_to_cancel = training_list[training_index]

        cancel_training(bot, user_id, training_to_cancel)

        message_text = f"Тренировка {training_to_cancel['date']} успешно отменена."
        bot.send_message(chat_id, message_text)
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except Exception as e:
            print(f"Ошибка при удалении сообщения с выбором тренировки: {e}")

        if 'status_message_id' in users[user_id]:
            try:
                bot.delete_message(chat_id, users[user_id]['status_message_id']) 
                del users[user_id]['status_message_id']
            except Exception as e:
                print(f"Ошибка при удалении сообщения 'Ваш статус:': {e}")
    else:
        bot.send_message(chat_id, "Неверный номер тренировки для отмены.")

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
    elif call.data == "cancel_trainings":
        show_cancel_options(bot, call)
    elif call.data.startswith("cancel_training_confirmed_"):
        cancel_training_confirmed(bot, call)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)  