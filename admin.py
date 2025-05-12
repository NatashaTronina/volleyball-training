import re
import telebot
from telebot import types
import json
import os
import datetime
import uuid
import qrcode
from DATE import get_day_of_week

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
    user_scope = telebot.types.BotCommandScopeAllPrivateChats()
    user_commands = [
        telebot.types.BotCommand("start", "Начать"),
        telebot.types.BotCommand("get_qr", "Получить QR-код для оплаты"),
        telebot.types.BotCommand("voting", "Участвовать в опросе")
    ]
    bot.set_my_commands(commands=user_commands, scope=user_scope)

def generate_qr_code(poll_id, user_id):
    if not poll_id:
        print("Poll ID is missing.")
        return None

    payment_link = None
    if poll_id in poll_data:
        for option in poll_data[poll_id]:
            if 'payment_link' in option:
                payment_link = option['payment_link']
                break

    if not payment_link:
        print("Payment link is missing.")
        return None

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(payment_link)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    qr_code_path = os.path.join(QR_CODE_DIR, f"qr_code_{poll_id}_{user_id}.png")
    img.save(qr_code_path)

    return qr_code_path

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
        bot.send_message(message.chat.id, "Неверный формат времени. Пожалуйста, введите время в формате ЧЧ-ММ (например, 12-00):")
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

def create_and_send_poll(message, poll_id):
    chat_id = message.chat.id
    options = []
    if poll_id in poll_data:
        for option in poll_data[poll_id]:
            date = option.get('date', 'Не указана')
            day = option.get('day', 'Не указан')
            time = option.get('time', 'Не указано')
            training_type = option.get('training_type', 'Не указан')
            price = option.get('price', 'Не указана')
            location = option.get('location', 'Не указано')
            comment = option.get('comment', '')
            options.append(f"{date} ({day}) {time} - {training_type} ({location}, {price} руб.) {comment}")

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

    # Извлекаем poll_id из callback_data
    poll_id = callback_data.split('_')[1]  # Предполагаем, что poll_id находится на втором месте

    if callback_data.startswith('poll_correct'):
        bot.send_message(chat_id, "Отлично! Теперь отправьте QR-код для оплаты тренировок (как изображение).")
        bot.register_next_step_handler(call.message, handle_qr_code, poll_id)  # Передаем poll_id

    elif callback_data.startswith('poll_edit'):
        bot.send_message(chat_id, "Начинаем пересоздание опроса...")
        if poll_id in poll_data:
            poll_data[poll_id].clear()  # Очищаем данные для текущего опроса
            save_polls()
        bot.send_message(chat_id, "Введите дату тренировки в формате ДД.ММ (например, 01.01):")
        bot.register_next_step_handler(call.message, get_date, poll_id)  # Передаем poll_id

def handle_qr_code(message, poll_id):  # Добавляем poll_id как аргумент
    chat_id = message.chat.id

    if message.photo:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        qr_code_path = os.path.join(QR_CODE_DIR, f"qr_code_{chat_id}.png")
        with open(qr_code_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        bot.send_message(chat_id, "QR-код сохранен. Теперь введите ссылку на СБП:")
        bot.register_next_step_handler(message, get_sbp_link, qr_code_path, poll_id)  # Передаем poll_id
    else:
        bot.send_message(chat_id, "Пожалуйста, отправьте QR-код как *изображение*.", parse_mode="Markdown")

def get_sbp_link(message, qr_code_path, poll_id):  # Добавляем poll_id как аргумент
    sbp_link = message.text
    chat_id = message.chat.id

    # Сохраняем ссылку на оплату в данных опроса
    if poll_id in poll_data:
        poll_data[poll_id][-1]['payment_link'] = sbp_link  # Сохраняем ссылку на оплату
        save_polls()  # Сохраняем изменения в файл

    # Создаем инлайн клавиатуру с кнопкой ссылки на СБП
    keyboard = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton(text="Оплатить через СБП", url=sbp_link)
    keyboard.add(button)

    with open(qr_code_path, 'rb') as qr_code_file:
        bot.send_photo(chat_id, qr_code_file, reply_markup=keyboard)

    bot.send_message(chat_id, "QR-код и ссылка на СБП отправлены.")

def delete_old_qr_codes(user_id):
    for filename in os.listdir(QR_CODE_DIR):
        if filename.startswith(f"qr_code_{user_id}_"):
            file_path = os.path.join(QR_CODE_DIR, filename)
            try:
                os.remove(file_path)
                print(f"Deleted old QR code: {filename}")
            except Exception as e:
                print(f"Error deleting {filename}: {e}")


@bot.message_handler(func=lambda message: True)
def next_action(message, poll_id):
    action = message.text
    chat_id = message.chat.id
    if is_admin(message):
        if action == "Добавить еще вариант":
            bot.send_message(chat_id, "Введите дату тренировки в формате ДД.ММ (например, 01.01):",
                             reply_markup=types.ReplyKeyboardRemove())
            bot.register_next_step_handler(message, get_date, poll_id)
        elif action == "Создать опрос":
            create_and_send_poll(message, poll_id)
        else:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            keyboard.add(types.KeyboardButton("Создать опрос"), types.KeyboardButton("Добавить еще вариант"))
            bot.send_message(chat_id, "Пожалуйста, выберите из предложенных вариантов:", reply_markup=keyboard)
            bot.register_next_step_handler(message, next_action, poll_id)
    else:
        bot.send_message(chat_id, "У вас нет прав для выполнения этой команды.")

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
    
    latest_poll = None
    latest_created_at = None

    for poll_id, poll in loaded_polls.items():
        if poll and 'created_at' in poll[-1]:  # Проверяем, что есть хотя бы один опрос
            created_at = poll[-1]['created_at']
            if latest_created_at is None or created_at > latest_created_at:
                latest_created_at = created_at
                latest_poll = {poll_id: poll}  # Сохраняем весь список опросов

    return latest_poll

@bot.message_handler(commands=['voting'])
def send_latest_poll(message):
    latest_poll = get_latest_poll()
    if latest_poll:
        poll_id, poll_options = list(latest_poll.items())[0]  # Получаем ID и все варианты опроса
        question = "Волейбол - выберите подходящий вариант:"

        options = []
        for option in poll_options:  # poll_options теперь список опросов
            options.append(f"{option['date']} ({option['day']}) {option['time']} - {option['training_type']} ({option['location']}, {option['price']} руб.) {option['comment']}")

        options.append("Не пойду на волейбол")  # Добавляем вариант по умолчанию

        bot.send_poll(message.chat.id, question=question, options=options, is_anonymous=False, allows_multiple_answers=True)
    else:
        bot.send_message(message.chat.id, "Нет доступных опросов.")
@bot.message_handler(commands=['get_qr'])
def get_qr_command(message):
    user_id = message.from_user.id

    if user_id in poll_results and poll_results[user_id]['voted']:
        poll_id = letest_poll.get("id")  # Получаем ID последнего опроса
        delete_old_qr_codes(user_id)
        qr_code_path = generate_qr_code(poll_id, user_id)
        if qr_code_path:
            try:
                with open(qr_code_path, 'rb') as qr_code_file:
                    bot.send_photo(message.chat.id, qr_code_file, caption="Оплатите тренировку")
            except Exception as e:
                bot.send_message(message.chat.id, f"Произошла ошибка при отправке QR-кода: {e}")
        else:
            bot.send_message(message.chat.id, "Не удалось сгенерировать QR-код. Обратитесь к администратору.")
    else:
        bot.send_message(message.chat.id, "Пожалуйста, сначала проголосуйте в опросе.")
if __name__ == "__main__":
    print("Admin bot started")
    set_commands()
    bot.infinity_polling()