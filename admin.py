import re
import time
import telebot
from telebot import types
import datetime
import uuid
from DATE import get_day_of_week
from shared_data import awaiting_confirmation, confirmed_payments, save_polls, load_polls
import threading
import schedule  
from users import get_user_ids, users
from ggl import record_payment, authenticate_google_sheets

ADMIN_ID = [494635818]
poll_data = {}
poll_results = {}
latest_poll = {}
payment_details = {}

POLL_DATA_FILE = "polls.json"

def is_admin(message):
    return message.from_user.id in ADMIN_ID

def set_commands(bot):
    for admin_id in ADMIN_ID:
        admin_scope = telebot.types.BotCommandScopeChat(chat_id=admin_id)
        admin_commands = [
            telebot.types.BotCommand("create_poll", "Создать опрос"),
            telebot.types.BotCommand("check_payments", "Проверить статусы оплат"),
            telebot.types.BotCommand('edit_list', "Редактировать список"),
            telebot.types.BotCommand('confirm_list', "Подтвердить список"),
        ]
        bot.set_my_commands(commands=admin_commands, scope=admin_scope)

def admin_start_command(bot, message):
    if is_admin(message):
        first_name = message.from_user.first_name
        chat_id = message.chat.id

        bot.send_message(chat_id, f"Привет, {first_name}! Для создания тренировок нажми команду /create_poll")

def create_poll_command(bot, message):
    if is_admin(message):
        chat_id = message.chat.id
        poll_id = str(uuid.uuid4())
        latest_poll["id"] = poll_id
        poll_data[poll_id] = []

        bot.send_message(chat_id, "Введите дату тренировки в формате ДД.ММ (например, 01.01):")
        bot.register_next_step_handler(message, get_date, poll_id, bot)
    else:
        bot.send_message(message.chat.id, "У вас нет прав для создания опросов.")

def get_date(message, poll_id, bot):
    date = message.text
    chat_id = message.chat.id
    if re.match(r"^\d{2}\.\d{2}$", date):
        day_name = get_day_of_week(date)
        if "Некорректная дата" in day_name:
            bot.send_message(chat_id, day_name)
            bot.send_message(chat_id, "Пожалуйста, введите дату в формате ДД.ММ:")
            bot.register_next_step_handler(message, get_date, poll_id, bot)
            return

        year = datetime.date.today().year
        if poll_id in poll_data:
            poll_data[poll_id].append({'date': date, 'day': day_name, 'year': year, 'created_at': datetime.datetime.now().isoformat()})
            save_polls(poll_data)
        bot.send_message(chat_id, "Введите время тренировки в формате ЧЧ-ММ (например, 12-00):")
        bot.register_next_step_handler(message, get_time, poll_id, bot)
    else:
        bot.send_message(chat_id, "Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ:")
        bot.register_next_step_handler(message, get_date, poll_id, bot)

def get_time(message, poll_id, bot):
    time_input = message.text
    chat_id = message.chat.id
    if re.match(r"^\d{2}[:-]\d{2}$", time_input):
        if poll_id in poll_data and poll_data[poll_id]:
            poll_data[poll_id][-1]['time'] = time_input
            save_polls(poll_data)

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Игровая"), types.KeyboardButton("Техническая"))
        bot.send_message(message.chat.id, "Выберите тип тренировки:", reply_markup=keyboard)
        bot.register_next_step_handler(message, get_training_type, poll_id, bot)
    else:
        bot.send_message(chat_id, "Неверный формат времени. Пожалуйста, введите время в формате ЧЧ-ММ (например, 12-00):")
        bot.register_next_step_handler(message, get_time, poll_id, bot)

def get_training_type(message, poll_id, bot):
    training_type = message.text
    chat_id = message.chat.id
    if training_type in ["Игровая", "Техническая"]:
        if poll_id in poll_data and poll_data[poll_id]:
            poll_data[poll_id][-1]['training_type'] = training_type
            save_polls(poll_data)

        bot.send_message(message.chat.id, "Введите цену тренировки:")
        bot.register_next_step_handler(message, get_price, poll_id, bot)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Игровая"), types.KeyboardButton("Техническая"))
        bot.send_message(message.chat.id, "Неверный тип тренировки. Пожалуйста, выберите из предложенных вариантов:",
                           reply_markup=keyboard)
        bot.register_next_step_handler(message, get_training_type, poll_id, bot)

def get_price(message, poll_id, bot):
    price = message.text
    chat_id = message.chat.id

    try:
        price = int(price)
        if poll_id in poll_data and poll_data[poll_id]:
            poll_data[poll_id][-1]['price'] = price
            save_polls(poll_data)

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Гимназия"), types.KeyboardButton("Энергия"))
        bot.send_message(message.chat.id, "Выберите место проведения тренировки:", reply_markup=keyboard)
        bot.register_next_step_handler(message, get_location, poll_id, bot)
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат цены. Пожалуйста, введите число:")
        bot.register_next_step_handler(message, get_price, poll_id, bot)

def get_location(message, poll_id, bot):
    location = message.text
    chat_id = message.chat.id

    if location in ["Гимназия", "Энергия"]:
        if poll_id in poll_data and poll_data[poll_id]:
            poll_data[poll_id][-1]['location'] = location
            save_polls(poll_data)

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Добавить комментарий"), types.KeyboardButton("Пропустить"))
        bot.send_message(message.chat.id, "Добавить комментарий к тренировке?", reply_markup=keyboard)
        bot.register_next_step_handler(message, handle_comment_choice, poll_id, bot)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Гимназия"), types.KeyboardButton("Энергия"))
        bot.send_message(message.chat.id, "Неверное место проведения. Пожалуйста, выберите из предложенных вариантов:",
                           reply_markup=keyboard)
        bot.register_next_step_handler(message, get_location, poll_id, bot)

def handle_comment_choice(message, poll_id, bot):
    choice = message.text
    chat_id = message.chat.id

    if choice == "Добавить комментарий":
        bot.send_message(message.chat.id, "Введите комментарий к тренировке:")
        bot.register_next_step_handler(message, get_comment, poll_id, bot)
    elif choice == "Пропустить":
        if poll_id in poll_data and poll_data[poll_id]:
            poll_data[poll_id][-1]['comment'] = ""
            save_polls(poll_data)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Создать опрос"), types.KeyboardButton("Добавить еще вариант"))
        bot.send_message(chat_id, "Что дальше?", reply_markup=keyboard)
        bot.register_next_step_handler(message, next_action, poll_id, bot)
    else:
        bot.send_message(message.chat.id, "Неверный выбор. Пожалуйста, выберите из предложенных вариантов:")
        bot.register_next_step_handler(message, handle_comment_choice, poll_id, bot)

def get_comment(message, poll_id, bot):
    comment = message.text
    chat_id = message.chat.id
    if poll_id in poll_data and poll_data[poll_id]:
        poll_data[poll_id][-1]['comment'] = comment
        save_polls(poll_data)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("Создать опрос"), types.KeyboardButton("Добавить еще вариант"))
    bot.send_message(chat_id, "Что дальше?", reply_markup=keyboard)
    bot.register_next_step_handler(message, next_action, poll_id, bot)

def next_action(message, poll_id, bot):
    action = message.text
    chat_id = message.chat.id
    if action == "Создать опрос":
        bot.send_message(chat_id, "Пожалуйста, отправьте ссылку на оплату СБП:")
        bot.register_next_step_handler(message, save_sbp_link_to_all, poll_id, bot)
    elif action == "Добавить еще вариант":
        bot.send_message(chat_id, "Введите дату тренировки в формате ДД.ММ (например, 01.01):")
        bot.register_next_step_handler(message, get_date, poll_id, bot)
    else:
        bot.send_message(message.chat.id, "Неверный выбор. Пожалуйста, выберите из предложенных")
        
def create_and_send_poll(bot, chat_id, poll_id):
    options = []
    if poll_id in poll_data:
        for option in poll_data[poll_id]:
            date = option.get('date', 'Не указана')
            day = option.get('day', 'Не указана')
            time = option.get('time', 'Не указана')
            training_type = option.get('training_type', 'Не указана')
            price = option.get('price', 'Не указана')
            location = option.get('location', 'Не указана')
            comment = option.get('comment', '')

            if date != 'Не указана' and day != 'Не указана' and time != 'Не указана':
                option_string = f"{date} ({day}) {time} - {training_type} ({location}, {price} руб.) {comment}"
                if len(option_string) > 90:
                    option_string = option_string[:87] + "..."
                options.append(option_string)

        options.append("Не пойду на волейбол")
        question = "Волейбол - выберите подходящий вариант:"

        try:
            user_ids = get_user_ids()
            user_ids = [int(user_id) for user_id in user_ids] 

            for user_id in user_ids:
                try:
                    user_info = users.get(user_id)
                    if user_info and "chat_id" in user_info:
                        chat_id = user_info["chat_id"]
                        sent_poll = bot.send_poll(chat_id, question=question, options=options,
                                                  is_anonymous=False, allows_multiple_answers=True)
                        poll_id_sent = sent_poll.poll.id
                        poll_results = {}
                        poll_results[user_id] = {'voted': False, 'poll_id': poll_id_sent}
                        latest_poll = {}
                        latest_poll["id"] = poll_id

                except telebot.apihelper.ApiTelegramException as e:
                    print(
                        f"create_and_send_poll: Ошибка отправки опроса пользователю {user_id}: {e}")
        except Exception as e:
            bot.send_message(ADMIN_ID[0], f"Не удалось создать и отправить опрос: {e}")
    else:
        bot.send_message(ADMIN_ID[0], "Нет данных для создания опроса.")

def save_sbp_link_to_all(message, poll_id, bot):
    sbp_link = message.text.strip()
    chat_id = message.chat.id
    if poll_id in poll_data:
        for item in poll_data[poll_id]:
            item['payment_link'] = sbp_link
        save_polls(poll_data)
        bot.send_message(chat_id, "Ссылка на СБП сохранена. Пожалуйста, введите дату для отправки опроса в формате ДД.ММ:")
        bot.register_next_step_handler(message, get_scheduled_date, poll_id, bot)
    else:
        bot.send_message(chat_id, "Ошибка: Не найден опрос. Пожалуйста, начните сначала.")

def get_scheduled_date(message, poll_id, bot):
    date = message.text
    chat_id = message.chat.id
    if re.match(r"^\d{2}\.\d{2}$", date):
        if poll_id in poll_data:
            for item in poll_data[poll_id]:
                item['scheduled_date'] = date
            save_polls(poll_data)
        else:
            bot.send_message(chat_id, "Ошибка: Не найден опрос с данным poll_id.")
            return
        bot.send_message(chat_id, "Введите время для отправки опроса в формате ЧЧ-ММ:")
        bot.register_next_step_handler(message, get_scheduled_time, poll_id, bot)
    else:
        bot.send_message(chat_id, "Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ:")
        bot.register_next_step_handler(message, get_scheduled_date, poll_id, bot)

def get_scheduled_time(message, poll_id, bot):
    time_input = message.text
    chat_id = message.chat.id
    if re.match(r"^\d{2}[:-]\d{2}$", time_input):
        scheduled_time = time_input.replace("-", ":") 
        if poll_id in poll_data and poll_data[poll_id]:
            for item in poll_data[poll_id]:
                item['scheduled_time'] = scheduled_time
            save_polls(poll_data)

        # Prepare the options for confirmation
        options = []
        for option in poll_data[poll_id]:
            date = option.get('date', 'Не указана')
            day = option.get('day', 'Не указана')
            time = option.get('time', 'Не указано')
            training_type = option.get('training_type', 'Не указано')
            price = option.get('price', 'Не указана')
            location = option.get('location', 'Не указана')
            comment = option.get('comment', '')

            if date != 'Не указана' and day != 'Не указана' and time != 'Не указана':
                option_string = f"{date} ({day}) {time} - {training_type} ({location}, {price} руб.) {comment}"
                options.append(option_string)

        # Create the confirmation message
        confirmation_message = f"Вы подтверждаете опрос с расписанием на {date} в {scheduled_time}?\n\n"
        confirmation_message += "\n".join(options)
        
        # Create confirmation buttons
        keyboard = types.InlineKeyboardMarkup()
        button_correct = types.InlineKeyboardButton(text="Подтверждаю", callback_data=f'poll_confirm_{poll_id}')
        button_edit = types.InlineKeyboardButton(text="Не подтверждаю", callback_data=f'poll_edit_{poll_id}')
        keyboard.add(button_correct, button_edit)

        bot.send_message(chat_id, confirmation_message, reply_markup=keyboard)
    else:
        bot.send_message(chat_id, "Неверный формат времени. Пожалуйста, введите время в формате ЧЧ-ММ:")
        bot.register_next_step_handler(message, get_scheduled_time, poll_id, bot)


def schedule_the_poll(bot, poll_id, scheduled_time):
    poll_sent = False

    def send_poll_job():
        nonlocal poll_sent  
        if not poll_sent: 
            create_and_send_poll(bot, ADMIN_ID[0], poll_id)
            poll_sent = True 

    # Запланировать задачу на указанное время
    schedule.every().day.at(scheduled_time).do(send_poll_job)

def send_scheduled_poll(bot):
    current_time = datetime.datetime.now().strftime("%H-%M")
    current_date = datetime.datetime.now().strftime("%d.%m")

    for poll_id, poll_data_item in poll_data.items():

        for option in poll_data_item:
            scheduled_date = option.get('scheduled_date')
            scheduled_time = option.get('scheduled_time')


            if scheduled_date == current_date and scheduled_time <= current_time:  

                create_and_send_poll(bot, ADMIN_ID[0], poll_id)
            
def handle_poll_answer(bot, poll_answer):
    user_id = poll_answer.user.id
    poll_id = poll_answer.poll_id
    option_ids = poll_answer.option_ids
    global poll_results
    if poll_id not in poll_results:
        poll_results[poll_id] = {'total_votes': 0, 'options': {}}
    if user_id not in poll_results.get('users', {}):
        poll_results[poll_id]['total_votes'] += 1
        if 'users' not in poll_results:
            poll_results['users'] = {}
        poll_results['users'][user_id] = poll_id
    for i in option_ids:
        if i not in poll_results[poll_id]['options']:
            poll_results[poll_id]['options'][i] = 0
        poll_results[poll_id]['options'][i] += 1

def get_latest_poll():
    loaded_polls = load_polls()
    latest_poll = None
    latest_created_at = None
    latest_poll_id = None  
    for poll_id, poll_list in loaded_polls.items():
        if poll_list and isinstance(poll_list, list) and len(poll_list) > 0:
            for poll_item in poll_list:
                try:
                    created_at_str = poll_item.get('created_at')
                    created_at = datetime.datetime.fromisoformat(created_at_str)
                except (KeyError, ValueError, TypeError):
                    continue
                if latest_created_at is None or created_at > latest_created_at:
                    latest_created_at = created_at
                    latest_poll = poll_list 
                    latest_poll_id = poll_id
    if latest_poll:  
        return {latest_poll_id: latest_poll}
    return None

def check_payments(bot, message):
    if is_admin(message):
        # Логируем содержимое awaiting_confirmation
        if awaiting_confirmation:
            text = "Список ожидающих подтверждения оплат:\n"
            bot.send_message(message.chat.id, text)
            for user_id, payment_info in awaiting_confirmation.items():
                # Извлекаем имя пользователя из вложенного словаря
                username = payment_info["username"]["username"]  # Изменено здесь
                total_price = payment_info["total_price"]
                
                # Создаем кликабельную ссылку на пользователя
                admin_message = f"Пользователь [{username}](tg://user?id={user_id}) ожидает подтверждение оплаты на сумму {total_price} руб."
                
                # Отправляем сообщение админу с кликабельной ссылкой
                keyboard = types.InlineKeyboardMarkup()
                confirm_button = types.InlineKeyboardButton(
                    text="Подтвердить оплату", callback_data=f"admin_confirm_{user_id}_{total_price}"
                )
                keyboard.add(confirm_button)

                # Отправляем сообщение с кликабельным именем
                bot.send_message(message.chat.id, admin_message, reply_markup=keyboard, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "Список пользователей, ожидающих подтверждения оплат пуст", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "У вас нет прав для просмотра этой информации.")


def handle_poll_confirmation(bot, call):
    chat_id = call.message.chat.id
    callback_data = call.data
    poll_id = callback_data.split('_')[2]

    if callback_data.startswith('poll_confirm'):
        bot.send_message(chat_id, "Опрос подтвержден. Расписание установлено.")
        scheduled_time = poll_data[poll_id][0].get('scheduled_time')
        scheduled_date = poll_data[poll_id][0].get('scheduled_date')
        
        if scheduled_time and scheduled_date:
            schedule_the_poll(bot, poll_id, scheduled_time)  # Schedule the poll
        else:
            bot.send_message(chat_id, "Ошибка: Не установлены дата или время для отправки опроса.")

    elif callback_data.startswith('poll_edit'):
        bot.send_message(chat_id, "Начинаем пересоздание опроса...")
        if poll_id in poll_data:
            poll_data[poll_id].clear()
            save_polls(poll_data)
        bot.send_message(chat_id, "Введите дату тренировки в формате ДД.ММ (например, 01.01):")
        bot.register_next_step_handler(call.message, get_date, poll_id, bot)


client = authenticate_google_sheets('vocal-circle-461812-m7-06081970720e.json')


def admin_confirm_payment(bot, call, client):
    admin_id = call.from_user.id
    if admin_id in ADMIN_ID:
        user_id = call.data.split("_")[2]
        total_price = call.data.split("_")[3]
        chat_id = call.message.chat.id
        username = awaiting_confirmation[int(user_id)]["username"]

        del awaiting_confirmation[int(user_id)]
        confirmed_payments[int(user_id)] = total_price
        bot.answer_callback_query(call.id, "Оплата подтверждена.")

        # Запись даты и суммы в таблицу
        record_payment(client, "Тренировки", user_id, total_price)

        # Удаляем сообщение сразу после успешной записи
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception as e:
            print(f"Ошибка удаления сообщения подтверждения: {e}")
    else:
        bot.send_message(call.message.chat.id, "У вас нет прав на выполнение этой операции.")
        bot.answer_callback_query(call.id, "Нет прав.")

def handle_callback_query(bot, call):
    if call.data.startswith('poll_confirm') or call.data.startswith('poll_edit'):
        handle_poll_confirmation(bot, call)
    elif call.data.startswith("admin_confirm_"):
        admin_confirm_payment(bot, call)
    elif call.data.startswith("confirm_payment_"):
        confirm_payment(bot, call)

def confirm_payment(bot, call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    total_price = call.data.split("_")[-1]

    if user_id in awaiting_confirmation:
        full_name = awaiting_confirmation[user_id]["username"]["username"]
        confirm_message_id = awaiting_confirmation[user_id]["confirm_message_id"]

        try:
            bot.delete_message(chat_id, confirm_message_id)
        except Exception as e:
            print(f"Error deleting confirmation message: {e}")

        del awaiting_confirmation[user_id]

        # Отправка сообщения админу с кликабельным именем пользователя
        admin_message = f"Пользователь [{full_name}](tg://user?id={user_id}) ожидает подтверждение оплаты на сумму {total_price} руб."

        keyboard = types.InlineKeyboardMarkup()
        confirm_button = types.InlineKeyboardButton(
            text="Подтвердить оплату", callback_data=f"admin_confirm_{user_id}_{total_price}"
        )
        keyboard.add(confirm_button)

        for admin_id in ADMIN_ID:
            bot.send_message(admin_id, admin_message, reply_markup=keyboard, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "Ошибка: Запрос на подтверждение не найден.")
        bot.answer_callback_query(call.id, "Произошла ошибка.")

def schedule_poll(bot):
    while True:
        send_scheduled_poll(bot)
        time.sleep(60) 

def start_poll_scheduler(bot):
    def run_scheduler():
        while True:
            try:
                schedule.run_pending()
            except Exception as e:
                print(f"Произошла ошибка в планировщике: {e}")
            time.sleep(60) 

    threading.Thread(target=run_scheduler, daemon=True).start()