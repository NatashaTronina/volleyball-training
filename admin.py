import re
import telebot
from telebot import types
import json
import os
import datetime
from DATE import get_day_of_week


data = ""
with open('config.json', 'r') as file:
    data = json.load(file)

TOKEN = data.get("token")

bot = telebot.TeleBot(TOKEN)

ADMIN_ID = [494635818]
poll_data = {}
poll_results = {}

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
    # ВСЕ ПОЛЬЗОВАТЕЛИ
    default_commands = [
        telebot.types.BotCommand("start", "Начать работу с ботом"),
        telebot.types.BotCommand("status", "Проверить свой статус оплаты"),
        telebot.types.BotCommand("help", "Получить справку")
    ]
    bot.set_my_commands(commands=default_commands)
    # ТОЛЬКО АДМИН
    for admin_id in ADMIN_ID:
        admin_scope = telebot.types.BotCommandScopeChat(chat_id=admin_id)  # Измените здесь
        admin_commands = [
            telebot.types.BotCommand("create_poll", "Создать опрос"),
            telebot.types.BotCommand("check_payments", "Проверить статусы оплат"),
            telebot.types.BotCommand("edit_list", "Редактировать список"),
            telebot.types.BotCommand("confirm_list", "Подтвердить список")
        ]
        bot.set_my_commands(commands=admin_commands, scope=admin_scope)


@bot.message_handler(commands=['start'])
def create_poll_command(message):
    if is_admin(message):
        chat_id = message.chat.id
        bot.send_message(chat_id, "Выберите команду /create_poll для создания опроса")


@bot.message_handler(commands=['create_poll'])
def create_poll_command(message):
    if is_admin(message):
        chat_id = message.chat.id
        if chat_id not in poll_data:
            poll_data[chat_id] = []  # Инициализируем список для администратора
        
        bot.send_message(chat_id, "Введите дату тренировки в формате ДД.ММ (например, 21.04):")
        bot.register_next_step_handler(message, get_date)  # Запрашиваем дату сразу
    else:
        bot.send_message(message.chat.id, "У вас нет прав для создания опросов.")

def get_date(message):
    date = message.text
    chat_id = message.chat.id
    if re.match(r"^\d{2}\.\d{2}$", date):
        day = get_day_of_week(date)  # Получаем день недели
        year = datetime.date.today().year  # Получаем текущий год
        
        if chat_id in poll_data:
            poll_data[chat_id].append({'date': date, 'day': day, 'year': year})  # Сохраняем дату, день и год
            save_polls()  # Сохраняем изменения
        bot.send_message(chat_id, "Введите время тренировки в формате ЧЧ-ММ (например, 12-00):")
        bot.register_next_step_handler(message, get_time)
    else:
        bot.send_message(chat_id, "Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ:")
        bot.register_next_step_handler(message, get_date)

def get_time(message):
    time = message.text
    chat_id = message.chat.id
    if re.match(r"^\d{2}[:-]\d{2}$", time):
        if chat_id in poll_data and poll_data[chat_id]:
            poll_data[chat_id][-1]['time'] = time  # Устанавливаем время для последнего опроса
            save_polls()  # Сохраняем изменения

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Игровая"), types.KeyboardButton("Техническая"))
        bot.send_message(message.chat.id, "Выберите тип тренировки:", reply_markup=keyboard)
        bot.register_next_step_handler(message, get_training_type)
    else:
        bot.send_message(message.chat.id, "Неверный формат времени. Пожалуйста, введите время в формате ЧЧ-ММ (например, 12-00):")
        bot.register_next_step_handler(message, get_time)

def get_training_type(message):
    training_type = message.text
    chat_id = message.chat.id
    if training_type in ["Игровая", "Техническая"]:
        if chat_id in poll_data and poll_data[chat_id]:
            poll_data[chat_id][-1]['training_type'] = training_type  # Устанавливаем тип тренировки
            save_polls()  # Сохраняем изменения

        bot.send_message(message.chat.id, "Введите цену тренировки:")
        bot.register_next_step_handler(message, get_price)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Игровая"), types.KeyboardButton("Техническая"))
        bot.send_message(message.chat.id, "Неверный тип тренировки. Пожалуйста, выберите из предложенных вариантов:", reply_markup=keyboard)
        bot.register_next_step_handler(message, get_training_type)

def get_price(message):
    price = message.text
    chat_id = message.chat.id

    try:
        price = int(price)
        if chat_id in poll_data and poll_data[chat_id]:
            poll_data[chat_id][-1]['price'] = price  # Устанавливаем цену для последнего опроса
            save_polls()  # Сохраняем изменения

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Гимназия"), types.KeyboardButton("Энергия"))
        bot.send_message(message.chat.id, "Выберите место проведения тренировки:", reply_markup=keyboard)
        bot.register_next_step_handler(message, get_location)
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат цены. Пожалуйста, введите число:")
        bot.register_next_step_handler(message, get_price)

def get_location(message):
    location = message.text
    chat_id = message.chat.id

    if location in ["Гимназия", "Энергия"]:
        if chat_id in poll_data and poll_data[chat_id]:
            poll_data[chat_id][-1]['location'] = location  # Устанавливаем место для последнего опроса
            save_polls()  # Сохраняем изменения

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Добавить комментарий"), types.KeyboardButton("Пропустить"))
        bot.send_message(message.chat.id, "Добавить комментарий к тренировке?", reply_markup=keyboard)
        bot.register_next_step_handler(message, handle_comment_choice)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Гимназия"), types.KeyboardButton("Энергия"))
        bot.send_message(message.chat.id, "Неверное место проведения. Пожалуйста, выберите из предложенных вариантов:", reply_markup=keyboard)
        bot.register_next_step_handler(message, get_location)

def handle_comment_choice(message):
    choice = message.text
    chat_id = message.chat.id

    if choice == "Добавить комментарий":
        bot.send_message(message.chat.id, "Введите комментарий к тренировке:")
        bot.register_next_step_handler(message, get_comment)
    elif choice == "Пропустить":
        if chat_id in poll_data and poll_data[chat_id]:
            poll_data[chat_id][-1]['comment'] = ""  # Сохраняем пустую строку как комментарий
            save_polls()  # Сохраняем изменения
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Создать опрос"), types.KeyboardButton("Добавить еще вариант"))
        bot.send_message(chat_id, "Что дальше?", reply_markup=keyboard)
        bot.register_next_step_handler(message, next_action)
    else:
        bot.send_message(message.chat.id, "Неверный выбор. Пожалуйста, выберите из предложенных вариантов:")
        bot.register_next_step_handler(message, handle_comment_choice)

def get_comment(message):
    comment = message.text
    chat_id = message.chat.id
    if chat_id in poll_data and poll_data[chat_id]:
        poll_data[chat_id][-1]['comment'] = comment  # Сохраняем комментарий
        save_polls()  # Сохраняем изменения
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("Создать опрос"), types.KeyboardButton("Добавить еще вариант"))
    bot.send_message(chat_id, "Что дальше?", reply_markup=keyboard)
    bot.register_next_step_handler(message, next_action)

def create_and_send_poll(message):
    chat_id = message.chat.id
    options = []
    if chat_id in poll_data:
        for option in poll_data[chat_id]:
            date = option.get('date', 'Не указана')
            day = option.get('day', 'Не указан')
            time = option.get('time', 'Не указано')
            training_type = option.get('training_type', 'Не указан')
            price = option.get('price', 'Не указана')
            location = option.get('location', 'Не указано')
            comment = option.get('comment', '')
            options.append(f"{date} ({day}) {time} - {training_type} ({location}, {price} руб.) {comment}")

        options.append("Не пойду на волейбол")
        question = "Волейбол - выберите подходящий вариант:"

        try:
            sent_poll = bot.send_poll(chat_id, question=question, options=options, is_anonymous=False,
                                        allows_multiple_answers=True)

            poll_id = sent_poll.poll.id
            poll_results[poll_id] = {i: 0 for i in range(len(options))}

            keyboard = types.InlineKeyboardMarkup()
            button_correct = types.InlineKeyboardButton(text="Опрос верный", callback_data=f'poll_correct_{poll_id}')
            button_edit = types.InlineKeyboardButton(text="Пересоздать опрос", callback_data=f'poll_edit_{poll_id}')
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

    if callback_data.startswith('poll_correct'):
        bot.send_message(chat_id, "Отлично! Теперь отправьте QR-код для оплаты тренировок (как изображение).")
        bot.register_next_step_handler(call.message, handle_qr_code)

    elif callback_data.startswith('poll_edit'):
        bot.send_message(chat_id, "Начинаем пересоздание опроса...")
        poll_data[chat_id].clear()
        save_polls()  # Сохраняем изменения после очистки
        bot.send_message(chat_id, "Введите дату тренировки в формате ДД.ММ (например, 21.04):")
        bot.register_next_step_handler(call.message, get_date)

def handle_qr_code(message):
    chat_id = message.chat.id

    if message.photo:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        qr_code_path = os.path.join(QR_CODE_DIR, f"qr_code_{chat_id}.png")
        with open(qr_code_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        bot.send_message(chat_id, "QR-код сохранен.")
    else:
        bot.send_message(chat_id, "Пожалуйста, отправьте QR-код как *изображение*.", parse_mode="Markdown")


@bot.message_handler(func=lambda message: True)
def next_action(message):
    action = message.text
    chat_id = message.chat.id

    if is_admin(message):
        if action == "Добавить еще вариант":
            bot.send_message(chat_id, "Введите дату тренировки в формате ДД.ММ (например, 27.03):",
                             reply_markup=types.ReplyKeyboardRemove())
            bot.register_next_step_handler(message, get_date)
        elif action == "Создать опрос":
            create_and_send_poll(message)
        else:
            # Если администратор ввел неверный вариант
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            keyboard.add(types.KeyboardButton("Создать опрос"), types.KeyboardButton("Добавить еще вариант"))
            bot.send_message(chat_id, "Пожалуйста, выберите из предложенных вариантов:", reply_markup=keyboard)
            bot.register_next_step_handler(message, next_action)
    else:
        bot.send_message(chat_id, "У вас нет прав для выполнения этой команды.")

@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    chat_id = poll_answer.user.id
    poll_id = poll_answer.poll_id
    option_ids = poll_answer.option_ids

    global poll_results

    if poll_id not in poll_results:
        print(f"WARNING: poll_id {poll_id} not found in poll_results")
        return

    poll_results_copy = poll_results[poll_id].copy()

    for i in poll_results_copy:
        if i not in option_ids and poll_results_copy[i] > 0:
            poll_results[poll_id][i] -= 1

    for i in option_ids:
        if i not in poll_results_copy:
            poll_results[poll_id][i] = 0
        if i not in poll_results_copy or poll_results_copy[i] == 0:
            poll_results[poll_id][i] += 1

if __name__ == "__main__":
    print("Bot started!")
    set_commands()
    bot.polling()