import re 
import volleyball_tg_bot
import telebot 
from telebot import types

# Замените на свой токен
TOKEN = "8129343330:AAGIEW_tVihFH_dT9jEADmYShO8ZluWJpDs"
bot = telebot.TeleBot(TOKEN)

# ID администратора (замените на свой ID)
ADMIN_ID = 494635818

# Состояние опроса (для хранения промежуточных данных)
poll_data = {}  # {chat_id: [ {date, day, time, training_type, price, location, comment}, ... ]}

# Проверка на админа
def is_admin(message):
    return message.from_user.id == ADMIN_ID

# Обработчик команды /create_poll
@bot.message_handler(commands=['create_poll'])
def create_poll_command(message):
    if is_admin(message):
        chat_id = message.chat.id
        poll_data[chat_id] = []  # Инициализируем список вариантов

        bot.send_message(chat_id, "Введите дату тренировки в формате ДД.ММ (например, 27.03):")
        bot.register_next_step_handler(message, get_date)
    else:
        bot.send_message(message.chat.id, "У вас нет прав для создания опросов.")

# Получение даты
def get_date(message):
    date = message.text
    chat_id = message.chat.id
    if re.match(r"^\d{2}[./]\d{2}$", date):  # Проверка формата даты
        if chat_id not in poll_data:
            poll_data[chat_id] = []
        poll_data[chat_id].append({'date': date})

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        for day in days:
            keyboard.add(types.KeyboardButton(day))
        bot.send_message(message.chat.id, "Выберите день недели:", reply_markup=keyboard)
        bot.register_next_step_handler(message, get_day_of_week)
    else:
        bot.send_message(message.chat.id, "Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ:")
        bot.register_next_step_handler(message, get_date)

# Получение дня недели
def get_day_of_week(message):
    day = message.text
    chat_id = message.chat.id

    if day in ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]:
        poll_data[chat_id][-1]['day'] = day

        bot.send_message(message.chat.id, "Введите время тренировки в формате ЧЧ-ММ (например, 12-00):", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, get_time)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        for day_name in days:  # Используем другое имя переменной, чтобы не путать с 'day'
            keyboard.add(types.KeyboardButton(day_name))
        bot.send_message(message.chat.id, "Неверный день недели. Пожалуйста, выберите из предложенных вариантов:", reply_markup=keyboard)
        bot.register_next_step_handler(message, get_day_of_week)

# Получение времени
def get_time(message):
    time = message.text
    chat_id = message.chat.id
    if re.match(r"^\d{2}[:-]\d{2}$", time):  # Проверка формата времени
        poll_data[chat_id][-1]['time'] = time
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Игровая"), types.KeyboardButton("Техническая"))
        bot.send_message(message.chat.id, "Выберите тип тренировки:", reply_markup=keyboard)
        bot.register_next_step_handler(message, get_training_type)
    else:
        bot.send_message(message.chat.id, "Неверный формат времени. Пожалуйста, введите время в формате ЧЧ-ММ (например, 12-00):")
        bot.register_next_step_handler(message, get_time)

# Получение типа тренировки
def get_training_type(message):
    training_type = message.text
    chat_id = message.chat.id
    if training_type in ["Игровая", "Техническая"]:
        poll_data[chat_id][-1]['training_type'] = training_type

        # Запрашиваем цену
        bot.send_message(message.chat.id, "Введите цену тренировки:")
        bot.register_next_step_handler(message, get_price)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Игровая"), types.KeyboardButton("Техническая"))
        bot.send_message(message.chat.id, "Неверный тип тренировки. Пожалуйста, выберите из предложенных вариантов:", reply_markup=keyboard)
        bot.register_next_step_handler(message, get_training_type)

# Получение цены
def get_price(message):
    price = message.text
    chat_id = message.chat.id

    try:
        price = int(price)
        poll_data[chat_id][-1]['price'] = price

        # Запрашиваем место проведения
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Гимназия"), types.KeyboardButton("Энергия"))
        bot.send_message(message.chat.id, "Выберите место проведения тренировки:", reply_markup=keyboard)
        bot.register_next_step_handler(message, get_location)
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат цены. Пожалуйста, введите число:")
        bot.register_next_step_handler(message, get_price)

# Получение места проведения
def get_location(message):
    location = message.text
    chat_id = message.chat.id
    if location in ["Гимназия", "Энергия"]:
        poll_data[chat_id][-1]['location'] = location

        # Запрашиваем комментарий
        bot.send_message(message.chat.id, "Введите комментарий к тренировке (или нажмите Enter, чтобы пропустить):")
        bot.register_next_step_handler(message, get_comment)
    else:
         keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True) # Определите keyboard здесь
         keyboard.add(types.KeyboardButton("Гимназия"), types.KeyboardButton("Энергия"))
         bot.send_message(message.chat.id, "Неверное место проведения. Пожалуйста, выберите из предложенных вариантов:", reply_markup=keyboard)
         bot.register_next_step_handler(message, get_location)

#Получение комментария
def get_comment(message):
    comment = message.text
    chat_id = message.chat.id
    poll_data[chat_id][-1]['comment'] = comment

    # После ввода всех данных - предлагаем добавить еще или закончить
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("Добавить еще вариант"), types.KeyboardButton("Создать опрос"))
    bot.send_message(message.chat.id, "Что дальше?", reply_markup=keyboard)
    bot.register_next_step_handler(message, next_action)


# Обработка выбора - добавить еще или создать опрос
def next_action(message):
    action = message.text
    chat_id = message.chat.id
    if action == "Добавить еще вариант":
        bot.send_message(chat_id, "Введите дату тренировки в формате ДД.ММ (например, 27.03):", reply_markup=types.ReplyKeyboardRemove())  # Убираем клаву
        bot.register_next_step_handler(message, get_date)  # Запускаем сначала ввод данных
    elif action == "Создать опрос":
        # Создаем и отправляем опрос
        create_and_send_poll(message)
    else:
        bot.send_message(chat_id, "Неверный выбор. Пожалуйста, выберите из предложенных вариантов:")
        bot.register_next_step_handler(message, next_action)

# Создание и отправка опроса
def create_and_send_poll(message):
    chat_id = message.chat.id
    if chat_id in poll_data and poll_data[chat_id]:
        # Формируем текст опроса
        options = []
        for option in poll_data[chat_id]:
            date = option['date']
            day = option['day']
            time = option['time']
            training_type = option['training_type']
            price = option['price']
            location = option['location']
            comment = option.get('comment', '')  # Получаем комментарий, если он есть, иначе пустая строка

            options.append(f"{date} ({day}) {time} - {training_type} ({location}, {price} руб.) {comment}")  # Включаем комментарий в текст

        question = "Выберите тренировку:"

        # Отправляем опрос
        bot.send_poll(chat_id, question, options, is_anonymous=False)

        # Очищаем данные опроса
        del poll_data[chat_id]
    else:
        bot.send_message(chat_id, "Нет вариантов тренировок для создания опроса.")

# Запускаем бота
if __name__ == "__main__":
    print("Bot started!")
    bot.polling()