import re
import telebot
from telebot import types
import json
import os
import datetime
import uuid
from DATE import get_day_of_week
from shared_data import awaiting_confirmation

ADMIN_ID = [494635818]
poll_data = {}
poll_results = {}
letest_poll = {}
payment_details = {}

POLL_DATA_FILE = "polls.json"

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

# Функция set_commands больше не является обработчиком
def set_commands(bot):
    for admin_id in ADMIN_ID:
        admin_scope = telebot.types.BotCommandScopeChat(chat_id=admin_id)
        admin_commands = [
            telebot.types.BotCommand("create_poll", "Создать опрос"),
            telebot.types.BotCommand("check_payments", "Проверить статусы оплат"),
        ]
        bot.set_my_commands(commands=admin_commands, scope=admin_scope)

def start_command(bot, message):
    user_id = message.from_user.id
    welcome_message = "Привет! Я бот для организации волейбольных тренировок.\n\n"
    if is_admin(message):
        bot.send_message(message.chat.id, "Привет! Вы используете админ панель, для создания тренировок воспользуйтесь командой /create_poll")
    else:
         bot.send_message(message.chat.id, welcome_message + "Используйте /voting для участия в опросе")

def create_poll_command(bot, message):
    if is_admin(message):
        chat_id = message.chat.id
        poll_id = str(uuid.uuid4())
        letest_poll["id"] = poll_id
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
            save_polls()
        bot.send_message(chat_id, "Введите время тренировки в формате ЧЧ-ММ (например, 12-00):")
        bot.register_next_step_handler(message, get_time, poll_id, bot)
    else:
        bot.send_message(chat_id, "Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ:")
        bot.register_next_step_handler(message, get_date, poll_id, bot)

def get_time(message, poll_id, bot):
    time = message.text
    chat_id = message.chat.id
    if re.match(r"^\d{2}[:-]\d{2}$", time):
        if poll_id in poll_data and poll_data[poll_id]:
            poll_data[poll_id][-1]['time'] = time
            save_polls()

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
            save_polls()

        bot.send_message(message.chat.id, "Введите цену тренировки:")
        bot.register_next_step_handler(message, get_price, poll_id, bot)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Игровая"), types.KeyboardButton("Техническая"))
        bot.send_message(message.chat.id, "Неверный тип тренировки. Пожалуйста, выберите из предложенных вариантов:", reply_markup=keyboard)
        bot.register_next_step_handler(message, get_training_type, poll_id, bot)

def get_price(message, poll_id, bot):
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
            save_polls()

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Добавить комментарий"), types.KeyboardButton("Пропустить"))
        bot.send_message(message.chat.id, "Добавить комментарий к тренировке?", reply_markup=keyboard)
        bot.register_next_step_handler(message, handle_comment_choice, poll_id, bot)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Гимназия"), types.KeyboardButton("Энергия"))
        bot.send_message(message.chat.id, "Неверное место проведения. Пожалуйста, выберите из предложенных вариантов:", reply_markup=keyboard)
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
            save_polls()
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
        save_polls()
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

def create_and_send_poll(bot, call, poll_id):
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

def handle_callback_query(bot, call):
    print(f"admin.handle_callback_query: call.data = {call.data}") # Добавили
    if call.data.startswith('poll_correct'):
        callback_query(bot, call)
    elif call.data.startswith('poll_edit'):
        callback_query(bot, call)
    elif call.data.startswith("admin_confirm_"):
        admin_confirm_payment(bot, call)
    elif call.data.startswith("confirm_payment_"):
        confirm_payment(bot, call)

def callback_query(bot, call):
    chat_id = call.message.chat.id
    callback_data = call.data

    # Правильно извлекаем poll_id из callback_data
    poll_id = callback_data.split('_')[2]  # Правильный индекс: poll_correct_pollID - pollID будет на позиции 2

    if callback_data.startswith('poll_correct'):
        bot.send_message(chat_id, "Опрос подтвержден и отправлен пользователям!")

    elif callback_data.startswith('poll_edit'):
        bot.send_message(chat_id, "Начинаем пересоздание опроса...")
        if poll_id in poll_data:
            poll_data[poll_id].clear()
            save_polls()
        bot.send_message(chat_id, "Введите дату тренировки в формате ДД.ММ (например, 01.01):")
        bot.register_next_step_handler(call.message, get_date, poll_id, bot)

def save_sbp_link_to_all(message, poll_id, bot):
    sbp_link = message.text.strip()
    chat_id = message.chat.id

    if poll_id in poll_data:
        for item in poll_data[poll_id]:
            item['payment_link'] = sbp_link

        save_polls()
        bot.send_message(chat_id, "Ссылка на СБП сохранена. Отправляю опрос")

        call = types.CallbackQuery(id='0', from_user=message.from_user, data=f'poll_correct_{poll_id}', message=message, chat_instance='', json_string=None) #id and from_user need to be valid, message will be the current message

        create_and_send_poll(bot, call, poll_id)

    else:
        bot.send_message(chat_id, "Ошибка: Не найден опрос. Пожалуйста, начните сначала.")

def handle_poll_answer(bot, poll_answer):
    user_id = poll_answer.user.id
    poll_id = poll_answer.poll_id
    option_ids = poll_answer.option_ids
    global poll_results
    if poll_id not in poll_results:
        poll_results[poll_id] = {'total_votes': 0, 'options': {}}
    if user_id not in poll_results.get('users', {}):
        # Увеличиваем общее количество голосов за poll_id
        poll_results[poll_id]['total_votes'] += 1
        # Регистрируем пользователя как проголосовавшего (внутри poll_results или в отдельном словаре)
        if 'users' not in poll_results:
            poll_results['users'] = {}
        poll_results['users'][user_id] = poll_id
    for i in option_ids:
        if i not in poll_results[poll_id]['options']:
            poll_results[poll_id]['options'][i] = 0
        poll_results[poll_id]['options'][i] += 1


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
                    latest_poll = poll_list #It should work
                    latest_poll_id  = poll_id  #Save it
    if latest_poll: #Then you return as a dict.
        print(f"Returning latest poll: {{'{latest_poll_id}': [{latest_poll}]}}") # Add this
        return {latest_poll_id: latest_poll} 
    return None

def check_payments(bot, message):
    if is_admin(message):
        if awaiting_confirmation:
            # Формируем текст со списком ожидающих оплат
            text = "Список ожидающих подтверждения оплат:\n"
            for user_id, payment_info in awaiting_confirmation.items():
                username = payment_info["username"]
                total_price = payment_info["total_price"]

                # Формируем сообщение с информацией о пользователе
                admin_message = f"Пользователь [{username}](tg://user?id={user_id}) ожидает подтверждение оплаты на сумму {total_price} руб."

                # Добавляем кнопку подтверждения для каждого пользователя
                keyboard = types.InlineKeyboardMarkup()
                confirm_button = types.InlineKeyboardButton(
                    text="Подтвердить оплату",
                    callback_data=f"admin_confirm_{user_id}_{total_price}",
                )
                keyboard.add(confirm_button)
                bot.send_message(message.chat.id, admin_message, reply_markup=keyboard, parse_mode="Markdown")
        else:
            # Если список пуст, отправляем сообщение об этом
            bot.send_message(message.chat.id, "Список пользователей, ожидающих подтверждения оплат пуст", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "У вас нет прав для просмотра этой информации.")




def admin_confirm_payment(bot, call):
    admin_id = call.from_user.id
    if admin_id in ADMIN_ID:
        user_id = call.data.split("_")[2]
        total_price = call.data.split("_")[3]
        chat_id = call.message.chat.id
        username = awaiting_confirmation[int(user_id)]["username"]
        del awaiting_confirmation[int(user_id)]

        # try:
        #     del payment_details[int(user_id)]
        # except KeyError:
        #     print(f"Ошибка: Не удалось найти payment_details для user_id {user_id}")

        bot.send_message(int(user_id), f"Ваша оплата на сумму {total_price} руб. подтверждена администратором.")
        bot.answer_callback_query(call.id, "Оплата подтверждена.")

        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception as e:
            print(f"Ошибка удаления сообщения подтверждения: {e}")
    else:
        bot.send_message(call.message.chat.id, "У вас нет прав на выполнение этой операции.")
        bot.answer_callback_query(call.id, "Нет прав.")

def handle_callback_query(bot, call):
    if call.data.startswith('poll_correct'):
        callback_query(bot, call)
    elif call.data.startswith('poll_edit'):
        callback_query(bot, call)
    elif call.data.startswith("admin_confirm_"):
        admin_confirm_payment(bot, call)
    elif call.data.startswith("confirm_payment_"):
        confirm_payment(bot, call)

def confirm_payment(bot, call):
    print("confirm_payment: Функция вызвана!")
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    total_price = call.data.split("_")[-1]

    if user_id in awaiting_confirmation:
        username = awaiting_confirmation[user_id]["username"]
        confirm_message_id = awaiting_confirmation[user_id]["confirm_message_id"]

        # Remove confirmation message
        try:
            bot.delete_message(chat_id, confirm_message_id)
        except Exception as e:
            print(f"Error deleting confirmation message: {e}")

        del awaiting_confirmation[user_id]

        # Формируем сообщение с кликабельным именем пользователя
        admin_message = f"Пользователь [{username}](tg://user?id={user_id}) ожидает подтверждение оплаты на сумму {total_price} руб."

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