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
from ggl import record_payment, authenticate_google_sheets, record_training_details, update_training_status, get_participants_for_training, cancel_training_for_user, cache, delete_training_details
from users import get_user_ids, user_confirmed, users, load_latest_poll

ADMIN_ID = [494635818]
poll_data = {}
poll_results = {}
latest_poll = {}
payment_details = {}
message_ids = {}

client = authenticate_google_sheets('vocal-circle-461812-m7-06081970720e.json')

POLL_DATA_FILE = "polls.json"

def is_admin(from_user):
    result = from_user.id in ADMIN_ID
    return result


def load_latest_poll():
    loaded_polls = load_polls()  
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

def set_commands(bot):
    for admin_id in ADMIN_ID:
        admin_scope = telebot.types.BotCommandScopeChat(chat_id=admin_id)
        admin_commands = [
            telebot.types.BotCommand("create_poll", "Создать опрос"),
            telebot.types.BotCommand("check_payments", "Проверить статусы оплат"),
            telebot.types.BotCommand('check_list', "Посмотреть список"),
        ]
        bot.set_my_commands(commands=admin_commands, scope=admin_scope)

def admin_start_command(bot, message):
    if is_admin(message.from_user):  
        first_name = message.from_user.first_name
        chat_id = message.chat.id
        bot.send_message(chat_id, f"Привет, {first_name}! Для создания тренировок нажми команду /create_poll")

def create_poll_command(bot, message):
    if is_admin(message.from_user): 
        chat_id = message.chat.id
        poll_id = str(uuid.uuid4())
        latest_poll["id"] = poll_id
        poll_data[poll_id] = []

        user_confirmed.clear()

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

            training_date = poll_data[poll_id][-1]['date']
            record_training_details(client, "Тренировки", training_date, price)

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
        next_action(message, poll_id, bot)
    else:
        bot.send_message(message.chat.id, "Неверный выбор. Пожалуйста, выберите из предложенных вариантов:")
        bot.register_next_step_handler(message, handle_comment_choice, poll_id, bot)

def get_comment(message, poll_id, bot):
    comment = message.text
    chat_id = message.chat.id
    if poll_id in poll_data and poll_data[poll_id]:
        poll_data[poll_id][-1]['comment'] = comment
        save_polls(poll_data)
    next_action(message, poll_id, bot)

def next_action(message, poll_id, bot):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("Создать опрос"), types.KeyboardButton("Добавить ещё вариант"), types.KeyboardButton("Отменить создание"))

    bot.send_message(message.chat.id, "Что дальше?", reply_markup=keyboard)
    bot.register_next_step_handler(message, handle_next_action_choice, poll_id, bot)

def handle_next_action_choice(message, poll_id, bot):
    action = message.text
    chat_id = message.chat.id
    if action == "Создать опрос":
        bot.send_message(chat_id, "Пожалуйста, отправьте ссылку на оплату СБП:")
        bot.register_next_step_handler(message, save_sbp_link_to_all, poll_id, bot)
    elif action == "Добавить ещё вариант":
        bot.send_message(chat_id, "Введите дату тренировки в формате ДД.ММ (например, 01.01):")
        bot.register_next_step_handler(message, get_date, poll_id, bot)
    elif action == "Отменить создание":
        if poll_id in poll_data:
            for training in poll_data[poll_id]:
                training_date = training.get('date')
                training_price = training.get('price')
                if training_date and training_price:
                    delete_training_details(client, "Тренировки", training_date, training_price)

            del poll_data[poll_id]
            save_polls(poll_data)
            user_confirmed.clear()

        bot.send_message(chat_id, "Создание опроса отменено, данные о тренировках удалены из таблицы.")
        return
    else:
        bot.send_message(message.chat.id, "Неверный выбор. Пожалуйста, выберите из предложенных")

def reset_payment_status(user_id):
    if user_id in confirmed_payments:
        del confirmed_payments[user_id]
    if user_id in awaiting_confirmation:
        del awaiting_confirmation[user_id]

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
                reset_payment_status(user_id)

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


def schedule_the_poll(bot, poll_id, scheduled_time):
    poll_sent = False

    def send_poll_job():
        nonlocal poll_sent  
        if not poll_sent: 
            create_and_send_poll(bot, ADMIN_ID[0], poll_id)
            poll_sent = True 

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
    if is_admin(message.from_user): 
        if awaiting_confirmation:
            text = "Список ожидающих подтверждения оплат:\n"

            for user_id, payments in awaiting_confirmation.items():
                for unique_payment_id, payment_info in payments.items(): 
                    username = payment_info["username"] 
                    total_price = payment_info["total_price"]
                    admin_message = f"Пользователь [{username}](tg://user?id={user_id}) ожидает подтверждение оплаты на сумму {total_price} руб."
                    keyboard = types.InlineKeyboardMarkup()
                    confirm_button = types.InlineKeyboardButton(
                        text="Подтвердить оплату", callback_data=f"admin_confirm_{user_id}_{unique_payment_id}")

                    keyboard.add(confirm_button)

                    bot.send_message(message.chat.id, admin_message, reply_markup=keyboard, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "Список пользователей, ожидающих подтверждения оплат пуст", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "У вас нет прав для просмотра этой информации.")

def handle_poll_confirmation(bot, call):
    chat_id = call.message.chat.id
    callback_data = call.data

    if callback_data.startswith("cancel_creation_"):
        poll_id = callback_data.split("_")[2]
        if poll_id in poll_data:
            del poll_data[poll_id]
            save_polls(poll_data)
            user_confirmed.clear()
        bot.send_message(chat_id, "Создание опроса отменено.")
        return

    if callback_data.startswith('poll_confirm'):
        poll_id = callback_data.split('_')[2]
        bot.send_message(chat_id, "Опрос подтвержден. Расписание установлено.")
        scheduled_time = poll_data[poll_id][0].get('scheduled_time')
        scheduled_date = poll_data[poll_id][0].get('scheduled_date')
        
        if scheduled_time and scheduled_date:
            schedule_the_poll(bot, poll_id, scheduled_time)  
            user_confirmed.clear()  
        else:
            bot.send_message(chat_id, "Ошибка: Не установлены дата или время для отправки опроса.")

    elif callback_data.startswith('poll_edit'):
        poll_id = callback_data.split('_')[2]
        bot.send_message(chat_id, "Начинаем пересоздание опроса...")
        if poll_id in poll_data:
            poll_data[poll_id].clear()
            save_polls(poll_data)
            user_confirmed.clear() 
        bot.send_message(chat_id, "Введите дату тренировки в формате ДД.ММ (например, 01.01):")
        bot.register_next_step_handler(call.message, get_date, poll_id, bot)

def check_list_command(bot, chat_id):
    latest_poll = load_latest_poll()
    if not latest_poll:
        sent_message = bot.send_message(chat_id, "Нет активных опросов.")
        message_ids.setdefault(chat_id, []).append(sent_message.message_id)
        return

    poll_id, training_options = list(latest_poll.items())[0]
    if not isinstance(training_options, list):
        sent_message = bot.send_message(chat_id, "Неверный формат данных опроса.")
        message_ids.setdefault(chat_id, []).append(sent_message.message_id)
        return

    keyboard = types.InlineKeyboardMarkup()
    for i, training in enumerate(training_options):
        date = training.get('date', 'Не указана')
        time = training.get('time', 'Не указана')
        price = training.get('price', 'Не указана')
        button_text = f"{date} {time} {price} руб."
        callback_data = f"training_selected_{poll_id}_{i}"
        button = types.InlineKeyboardButton(text=button_text, callback_data=callback_data)
        keyboard.add(button)

    sent_message = bot.send_message(chat_id, "Выберите тренировку для просмотра списка участников:", reply_markup=keyboard)
    message_ids.setdefault(chat_id, []).append(sent_message.message_id)

def save_sbp_link_to_all(message, poll_id, bot):
    sbp_link = message.text.strip()
    chat_id = message.chat.id
    if poll_id in poll_data:
        for item in poll_data[poll_id]:
            item['payment_link'] = sbp_link
        save_polls(poll_data)
        keyboard = types.InlineKeyboardMarkup()
        bot.send_message(chat_id, "Ссылка на СБП сохранена. Пожалуйста, введите дату для отправки опроса в формате ДД.ММ:", reply_markup=keyboard)
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
        keyboard = types.InlineKeyboardMarkup()
        bot.send_message(chat_id, "Введите время для отправки опроса в формате ЧЧ-ММ:", reply_markup=keyboard)
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

        options = []
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
                options.append(option_string)

        confirmation_message = f"Вы подтверждаете опрос с расписанием на {date} в {scheduled_time}?\n\n"
        confirmation_message += "\n".join(options)
        
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

def admin_confirm_payment(bot, call):
    admin_id = call.from_user.id
    if admin_id in ADMIN_ID:
        user_id = int(call.data.split("_")[2])
        unique_payment_id = call.data.split("_")[3]
        chat_id = call.message.chat.id

        if user_id in awaiting_confirmation:
            if unique_payment_id in awaiting_confirmation[user_id]:
                payment_info = awaiting_confirmation[user_id].pop(unique_payment_id)
                total_price = payment_info['total_price']  
                if user_id not in confirmed_payments:
                    confirmed_payments[user_id] = []
                confirmed_payments[user_id].append(total_price)

                record_payment(client, "Тренировки", int(user_id), int(payment_info["total_price"]))

                update_training_status(client, "Тренировки", user_id, payment_info, "1")

                bot.send_message(chat_id, "Оплата подтверждена и записана в таблицу.")

                try:
                    bot.delete_message(call.message.chat.id, call.message.message_id)
                except Exception as e:
                    print(f"Ошибка удаления сообщения подтверждения: {e}")

                if user_id in awaiting_confirmation and not awaiting_confirmation[user_id]:
                    del awaiting_confirmation[user_id]
            else:
                bot.send_message(chat_id, "Ошибка: Оплата не найдена.")
        else:
            bot.send_message(chat_id, "Ошибка: Оплата не найдена в awaiting_confirmation.")
    else:
        bot.send_message(call.message.chat.id, "У вас нет прав на выполнение этой операции.")


def remove_user_from_training(bot, chat_id, poll_id, training_index, user_index):
    latest_poll = load_latest_poll()
    if not latest_poll or poll_id not in latest_poll:
        bot.send_message(chat_id, "Опрос не найден.")
        return

    training_options = latest_poll[poll_id]
    if not isinstance(training_options, list) or training_index >= len(training_options):
        bot.send_message(chat_id, "Тренировка не найдена.")
        return

    training = training_options[training_index]
    training_date = training.get('date')
    training_price = str(training.get('price'))

    participants = get_participants_for_training(client, "Тренировки", training_date, training_price)

    if not participants or user_index >= len(participants):
        bot.send_message(chat_id, "Участник не найден.")
        return

    user = participants[user_index]  
    user_name = user['name']
    user_status = user['status']


    new_status = "#" if user_status in ("0", "1") else ""
    
    cancel_training_for_user(client, "Тренировки", training_date, training_price, user, new_status)  

    bot.send_message(chat_id, f"Участник {user_name} удален с тренировки.")

    cache_key = f"{training_date}_{training_price}"
    if cache_key in cache:
        del cache[cache_key]

def show_participants_list(bot, chat_id, poll_id, training_index):
    latest_poll = load_latest_poll()
    if not latest_poll:
        sent_message = bot.send_message(chat_id, "Опрос не найден.")
        message_ids.setdefault(chat_id, []).append(sent_message.message_id)
        return
    if poll_id not in latest_poll:
        sent_message = bot.send_message(chat_id, f"Опрос с ID {poll_id} не найден.")
        message_ids.setdefault(chat_id, []).append(sent_message.message_id)
        return

    training_options = latest_poll[poll_id]
    if not isinstance(training_options, list) or training_index >= len(training_options):
        sent_message = bot.send_message(chat_id, "Тренировка не найдена.")
        message_ids.setdefault(chat_id, []).append(sent_message.message_id)
        return

    training = training_options[training_index]
    training_date = training.get('date')
    training_price = str(training.get('price'))

    participants = get_participants_for_training(client, "Тренировки", training_date, training_price)

    if not participants:
        sent_message = bot.send_message(chat_id, "На эту тренировку никто не записался.")
        message_ids.setdefault(chat_id, []).append(sent_message.message_id)
        return

    try:
        participants_list = "\n".join([f"{i+1}) {p['name']}" for i, p in enumerate(participants)])
        message_text = f"Список участников:\n{participants_list}"

        keyboard = types.InlineKeyboardMarkup()
        edit_button = types.InlineKeyboardButton(text="Редактировать список", callback_data=f"edit_list_{poll_id}_{training_index}")
        keyboard.add(edit_button)

        if chat_id is not None:
            sent_message = bot.send_message(chat_id, message_text, reply_markup=keyboard)
            message_ids.setdefault(chat_id, []).append(sent_message.message_id)
    except Exception as e:
        print(f"Произошла ошибка: {e}")

def show_edit_list_options(bot, chat_id, poll_id, training_index):
    latest_poll = load_latest_poll()
    if not latest_poll or poll_id not in latest_poll:
        sent_message = bot.send_message(chat_id, "Опрос не найден.")
        message_ids.setdefault(chat_id, []).append(sent_message.message_id)
        return

    training_options = latest_poll[poll_id]
    if not isinstance(training_options, list) or training_index >= len(training_options):
        sent_message = bot.send_message(chat_id, "Тренировка не найдена.")
        message_ids.setdefault(chat_id, []).append(sent_message.message_id)
        return

    training = training_options[training_index]
    training_date = training.get('date')
    training_price = str(training.get('price'))

    participants = get_participants_for_training(client, "Тренировки", training_date, training_price)

    if not participants:
        sent_message = bot.send_message(chat_id, "На эту тренировку никто не записался.")
        message_ids.setdefault(chat_id, []).append(sent_message.message_id)
        return

    keyboard = types.InlineKeyboardMarkup(row_width=1)

    for i, participant in enumerate(participants):
        user_name = participant['name'].replace(" (Вернуть оплату)", "")
        callback_data = f"remove_user_{poll_id}_{training_index}_{i}"
        button = types.InlineKeyboardButton(text=f"Удалить {user_name}", callback_data=callback_data)
        keyboard.add(button)

    sent_message = bot.send_message(chat_id, "Выберите участника для удаления:", reply_markup=keyboard)
    message_ids.setdefault(chat_id, []).append(sent_message.message_id)


def admin_handle_callback_query(bot, call):
    from_user = call.from_user
    chat_id = call.message.chat.id
    if not is_admin(from_user):
        bot.send_message(chat_id, "У вас нет прав для выполнения этой операции.")
        return 

    if call.data.startswith('training_selected_'):
        poll_id, training_index = call.data[18:].split('_')
        show_participants_list(bot, chat_id, poll_id, int(training_index))
    elif call.data.startswith('edit_list_'):
        poll_id, training_index = call.data[10:].split('_')
        show_edit_list_options(bot, chat_id, poll_id, int(training_index))
    elif call.data.startswith('remove_user_'):
        poll_id, training_index, user_index = call.data[12:].split('_')
        remove_user_from_training(bot, chat_id, poll_id, int(training_index), int(user_index))

        if chat_id in message_ids:
            for message_id in message_ids[chat_id]:
                try:
                    bot.delete_message(chat_id, message_id)
                except Exception as e:
                    print(f"Ошибка при удалении сообщения: {e}")
            del message_ids[chat_id] 

        check_list_command(bot, chat_id)
        return
    elif call.data.startswith('poll_confirm') or call.data.startswith('poll_edit') or call.data.startswith(
            "cancel_creation_"):
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
        for unique_payment_id, payment_info in awaiting_confirmation[user_id].items():
            if str(payment_info['total_price']) == total_price:
                full_name = payment_info["username"]
                confirm_message_id = payment_info["confirm_message_id"]

                try:
                    bot.delete_message(chat_id, confirm_message_id)
                except Exception as e:
                    print(f"confirm_payment: Error deleting user confirmation message: {e}")

                admin_message = f"Пользователь [{full_name}](tg://user?id={user_id}) ожидает подтверждение оплаты на сумму {total_price} руб."
                admin_message = "Оплату нужно подтведить"

                keyboard = types.InlineKeyboardMarkup()
                confirm_button = types.InlineKeyboardButton(
                    text="Подтвердить оплату", callback_data=f"admin_confirm_{user_id}_{unique_payment_id}"
                )
                keyboard.add(confirm_button)
                bot.send_message(chat_id, f"Оплату нужно подтвердить вручную")

                for admin_id in ADMIN_ID:
                    bot.send_message(admin_id, admin_message, reply_markup=keyboard, parse_mode="Markdown")

                return  

        bot.send_message(chat_id, "Ошибка: Соответствующая оплата не найдена.")
    else:
        bot.send_message(chat_id, "Ошибка: Запрос на подтверждение не найден.")

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
