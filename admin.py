import re
import telebot
from telebot import types
import json
import os
import datetime
import uuid
from DATE import get_day_of_week
import qrcode
from io import BytesIO

data = ""
with open('config.json', 'r') as file:
    data = json.load(file)

TOKEN = data.get("token")

bot = telebot.TeleBot(TOKEN)

ADMIN_ID = [494635818]
poll_data = {}
poll_results = {}
letest_poll = {}

POLL_DATA_FILE = "polls.json"
QR_CODE_DIR = "qr_codes"

if not os.path.exists(QR_CODE_DIR):
    os.makedirs(QR_CODE_DIR)

def save_polls():
    with open(POLL_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(poll_data, f, ensure_ascii=False, indent=4)

def load_polls():
    if os.path.exists(POLL_DATA_FILE):
        with open(POLL_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

poll_data = load_polls()

def is_admin(message):
    return message.from_user.id in ADMIN_ID

def set_commands():
    for admin_id in ADMIN_ID:
        admin_scope = telebot.types.BotCommandScopeChat(chat_id=admin_id)
        admin_commands = [
            telebot.types.BotCommand("create_poll", "Создать опрос"),
            telebot.types.BotCommand("check_payments", "Проверить статусы оплат"),
            telebot.types.BotCommand("edit_list", "Редактировать список"),
            telebot.types.BotCommand("confirm_list", "Подтвердить список")
        ]
        bot.set_my_commands(commands=admin_commands, scope=admin_scope)

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    welcome_message = "Привет! Я бот для организации волейбольных тренировок.\n\n"
    if is_admin(message):
        bot.send_message(message.chat.id, "Привет! Вы используете админ панель, для создания тренировок воспользуйтесь командой /create_poll")
    else:
         bot.send_message(message.chat.id, welcome_message +
                    "Используйте /voting для участия в опросе и /get_qr для получения QR-кода после подтверждения вашего голоса.")

@bot.message_handler(commands=['create_poll'])
def create_poll_command(message):
    if is_admin(message):
        chat_id = message.chat.id
        poll_id = str(uuid.uuid4())  # Генерируем уникальный идентификатор для опроса
        letest_poll["id"] = poll_id
        print(f"/create_poll: Создан poll_id: {poll_id}")  # Добавлено
        poll_data[poll_id] = []  # Инициализируем новый опрос с уникальным ID

        bot.send_message(chat_id, "Введите дату тренировки в формате ДД.ММ (например, 01.01):")
        bot.register_next_step_handler(message, get_date, poll_id)  # Передаем poll_id в следующую функцию
    else:
        bot.send_message(message.chat.id, "У вас нет прав для создания опросов.")

def get_date(message, poll_id):
    date = message.text
    chat_id = message.chat.id
    if re.match(r"^\d{2}\.\d{2}$", date):
        day_name = get_day_of_week(date)
        if "Некорректная дата" in day_name:
            bot.send_message(chat_id, day_name)
            bot.send_message(chat_id, "Пожалуйста, введите дату в формате ДД.ММ:")
            bot.register_next_step_handler(message, get_date, poll_id)
            return

        year = datetime.date.today().year

        if poll_id in poll_data:
            poll_data[poll_id].append({'date': date, 'day': day_name, 'year': year, 'created_at': datetime.datetime.now().isoformat()})
            save_polls()
        bot.send_message(chat_id, "Введите время тренировки в формате ЧЧ-ММ (например, 12-00):")
        bot.register_next_step_handler(message, get_time, poll_id)
    else:
        bot.send_message(chat_id, "Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ:")
        bot.register_next_step_handler(message, get_date, poll_id)

def get_time(message, poll_id):
    time = message.text
    chat_id = message.chat.id
    if re.match(r"^\d{2}[:-]\d{2}$", time):
        if poll_id in poll_data and poll_data[poll_id]:
            poll_data[poll_id][-1]['time'] = time
            save_polls()

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Игровая"), types.KeyboardButton("Техническая"))
        bot.send_message(message.chat.id, "Выберите тип тренировки:", reply_markup=keyboard)
        bot.register_next_step_handler(message, get_training_type, poll_id)
    else:
        bot.send_message(chat_id, "Неверный формат времени. Пожалуйста, введите время в формате ЧЧ-ММ (например, 12-00):")
        bot.register_next_step_handler(message, get_time, poll_id)

def get_training_type(message, poll_id):
    training_type = message.text
    chat_id = message.chat.id
    if training_type in ["Игровая", "Техническая"]:
        if poll_id in poll_data and poll_data[poll_id]:
            poll_data[poll_id][-1]['training_type'] = training_type
            save_polls()

        bot.send_message(message.chat.id, "Введите цену тренировки:")
        bot.register_next_step_handler(message, get_price, poll_id)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Игровая"), types.KeyboardButton("Техническая"))
        bot.send_message(message.chat.id, "Неверный тип тренировки. Пожалуйста, выберите из предложенных вариантов:", reply_markup=keyboard)
        bot.register_next_step_handler(message, get_training_type, poll_id)

def get_price(message, poll_id):
    price = message.text
    chat_id = message.chat.id

    try:
        price = int(price)
        if poll_id in poll_data and poll_data[poll_id]:
            poll_data[poll_id][-1]['price'] = price
            save_polls()

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Гимназия"), types.KeyboardButton("Энергия"))
        bot.send_message(message.chat.id, "Выберите место проведения тренировки:", reply_markup=keyboard)
        bot.register_next_step_handler(message, get_location, poll_id)
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат цены. Пожалуйста, введите число:")
        bot.register_next_step_handler(message, get_price, poll_id)

def get_location(message, poll_id):
    location = message.text
    chat_id = message.chat.id

    if location in ["Гимназия", "Энергия"]:
        if poll_id in poll_data and poll_data[poll_id]:
            poll_data[poll_id][-1]['location'] = location
            save_polls()

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Добавить комментарий"), types.KeyboardButton("Пропустить"))
        bot.send_message(message.chat.id, "Добавить комментарий к тренировке?", reply_markup=keyboard)
        bot.register_next_step_handler(message, handle_comment_choice, poll_id)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Гимназия"), types.KeyboardButton("Энергия"))
        bot.send_message(message.chat.id, "Неверное место проведения. Пожалуйста, выберите из предложенных вариантов:", reply_markup=keyboard)
        bot.register_next_step_handler(message, get_location, poll_id)

def handle_comment_choice(message, poll_id):
    choice = message.text
    chat_id = message.chat.id

    if choice == "Добавить комментарий":
        bot.send_message(message.chat.id, "Введите комментарий к тренировке:")
        bot.register_next_step_handler(message, get_comment, poll_id)
    elif choice == "Пропустить":
        if poll_id in poll_data and poll_data[poll_id]:
            poll_data[poll_id][-1]['comment'] = ""
            save_polls()
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Создать опрос"), types.KeyboardButton("Добавить еще вариант"))
        bot.send_message(chat_id, "Что дальше?", reply_markup=keyboard)
        bot.register_next_step_handler(message, next_action, poll_id)
    else:
        bot.send_message(message.chat.id, "Неверный выбор. Пожалуйста, выберите из предложенных вариантов:")
        bot.register_next_step_handler(message, handle_comment_choice, poll_id)

def get_comment(message, poll_id):
    comment = message.text
    chat_id = message.chat.id
    if poll_id in poll_data and poll_data[poll_id]:
        poll_data[poll_id][-1]['comment'] = comment
        save_polls()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("Создать опрос"), types.KeyboardButton("Добавить еще вариант"))
    bot.send_message(chat_id, "Что дальше?", reply_markup=keyboard)
    bot.register_next_step_handler(message, next_action, poll_id)

def next_action(message, poll_id):
    action = message.text
    chat_id = message.chat.id
    print(f"next_action: poll_id: {poll_id}")  # Добавлено

    if action == "Создать опрос":
        bot.send_message(chat_id, "Пожалуйста, отправьте ссылку на оплату СБП:")
        bot.register_next_step_handler(message, save_sbp_link_to_all, poll_id)
    elif action == "Добавить еще вариант":
        bot.send_message(chat_id, "Введите дату тренировки в формате ДД.ММ (например, 01.01):")
        bot.register_next_step_handler(message, get_date, poll_id)
    else:
        bot.send_message(message.chat.id, "Неверный выбор. Пожалуйста, выберите из предложенных")

def create_and_send_poll(call, poll_id):
    print(f"create_and_send_poll: poll_id: {poll_id}") # Добавлено

    chat_id = call.message.chat.id
    options = []
    if poll_id in poll_data:
        for option in poll_data[poll_id]:
            date = option.get('date', 'Не указана')
            day = option.get('day', 'Не указан')
            time = option.get('time', 'Не указано')
            training_type = option.get('training_type', 'Не указана')
            price = option.get('price', 'Не указана')
            location = option.get('location', 'Не указана')
            comment = option.get('comment', '')
            payment_link = option.get('payment_link', '')  # Get the payment link

            #Create a shortened string
            option_string = f"{date} ({day}) {time} - {training_type} ({location}, {price} руб.) {comment}"

            if len(option_string) > 90: #Truncate if too long
                option_string = option_string[:87] + "..." #Truncate and add ellipsis
            options.append(option_string)  # Add payment link to each option

        options.append("Не пойду на волейбол")  # Добавляем вариант по умолчанию
        question = "Волейбол - выберите подходящий вариант:"

        try:
            sent_poll = bot.send_poll(chat_id, question=question, options=options, is_anonymous=False, allows_multiple_answers=True)  # Разрешаем голосовать за несколько вариантов

            poll_id_sent = sent_poll.poll.id
            poll_results[chat_id] = {'voted': False, 'poll_id': poll_id_sent}
            letest_poll["id"] = poll_id
            keyboard = types.InlineKeyboardMarkup()
            button_correct = types.InlineKeyboardButton(text="Опрос верный", callback_data=f'poll_correct_{poll_id_sent}')
            button_edit = types.InlineKeyboardButton(text="Пересоздать опрос", callback_data=f'poll_edit_{poll_id_sent}')
            keyboard.add(button_correct, button_edit)

            bot.send_message(chat_id, "Подтвердите опрос:", reply_markup=keyboard)

        except Exception as e:
            bot.send_message(chat_id, f"Не удалось создать опрос: {e}")
    else:
        bot.send_message(chat_id, "Нет данных для создания опроса.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('poll_correct') or call.data.startswith('poll_edit'))
def callback_query(call):
    chat_id = call.message.chat.id
    callback_data = call.data

    # Правильно извлекаем poll_id из callback_data
    poll_id = callback_data.split('_')[2]  # Правильный индекс: poll_correct_pollID - pollID будет на позиции 2

    if callback_data.startswith('poll_correct'):
        bot.send_message(chat_id, "Опрос подтвержден и отправлен пользователям!")

    elif callback_data.startswith('poll_edit'):
        bot.send_message(chat_id, "Начинаем пересоздание опроса...")
        if poll_id in poll_data:
            poll_data[poll_id].clear()  # Очищаем данные для текущего опроса
            save_polls()
        bot.send_message(chat_id, "Введите дату тренировки в формате ДД.ММ (например, 01.01):")
        bot.register_next_step_handler(call.message, get_date, poll_id)

def save_sbp_link_to_all(message, poll_id):
    print(f"save_sbp_link_to_all: poll_id: {poll_id}") # Добавлено

    sbp_link = message.text.strip()
    chat_id = message.chat.id

    if poll_id in poll_data:
        # Check if the poll ID exists
        for item in poll_data[poll_id]:  # Iterate through all polls for the given id
            item['payment_link'] = sbp_link

        save_polls()
        bot.send_message(chat_id, "Ссылка на СБП сохранена. Отправляю опрос")

        # Create a mock 'call' object
        call = types.CallbackQuery(id='0', from_user=message.from_user, data=f'poll_correct_{poll_id}', message=message, chat_instance='', json_string=None) #id and from_user need to be valid, message will be the current message

        create_and_send_poll(call, poll_id) #Correct call

    else:
        bot.send_message(chat_id, "Ошибка: Не найден опрос. Пожалуйста, начните сначала.")

@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    user_id = poll_answer.user.id
    poll_id = poll_answer.poll_id
    option_ids = poll_answer.option_ids

    global poll_results

    if poll_id not in poll_results:
        poll_results[user_id] = {'voted': True, 'poll_id': poll_id}
        print(f"WARNING: poll_id {poll_id} not found in poll_results")
        return

    if user_id not in poll_results:
          poll_results[user_id] = {'voted': True, 'poll_id': poll_id}

    poll_results[user_id]['voted'] = True
    for i in option_ids:
        if i not in poll_results[poll_id]:
            poll_results[poll_id][i] = 0
        poll_results[poll_id][i] += 1

def get_latest_poll():
    loaded_polls = load_polls()
    print(f"Loaded polls: {loaded_polls}") #Add this
    latest_poll = None
    latest_created_at = None
    latest_poll_id = None #Added this

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
                    latest_poll = poll_item #It should work
                    latest_poll_id  = poll_id  #Save it

    if latest_poll: #Then you return as a dict.
        print(f"Returning latest poll: {{'{latest_poll_id}': [{latest_poll}]}}") # Add this
        return {latest_poll_id: [latest_poll]} #Return as dict
    print("Returning None") # Add this
    return None

if __name__ == "__main__":
    print("Admin bot started")
    set_commands()
    bot.polling()