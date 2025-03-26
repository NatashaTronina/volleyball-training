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

#Словарь для хранения выбранных пользователями тренировок
user_selections = {} # {user_id: [index1, index2, ...]}

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
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
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

    if day in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]:
        poll_data[chat_id][-1]['day'] = day

        bot.send_message(message.chat.id, "Введите время тренировки в формате ЧЧ-ММ (например, 12-00):", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, get_time)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
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
        keyboard.add(types.KeyboardButton("Игровая"), types.KeyboardButton("Техничка"))
        bot.send_message(message.chat.id, "Выберите тип тренировки:", reply_markup=keyboard)
        bot.register_next_step_handler(message, get_training_type)
    else:
        bot.send_message(message.chat.id, "Неверный формат времени. Пожалуйста, введите время в формате ЧЧ-ММ (например, 12-00):")
        bot.register_next_step_handler(message, get_time)

# Получение типа тренировки
def get_training_type(message):
    training_type = message.text
    chat_id = message.chat.id
    if training_type in ["Игровая", "Техничка"]:
        poll_data[chat_id][-1]['training_type'] = training_type

        # Запрашиваем цену
        bot.send_message(message.chat.id, "Введите цену тренировки:")
        bot.register_next_step_handler(message, get_price)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Игровая"), types.KeyboardButton("Техничка"))
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

        # Предлагаем добавить комментарий или пропустить
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Добавить комментарий"), types.KeyboardButton("Пропустить"))
        bot.send_message(message.chat.id, "Добавить комментарий к тренировке?", reply_markup=keyboard)
        bot.register_next_step_handler(message, handle_comment_choice)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)  # Определите keyboard здесь
        keyboard.add(types.KeyboardButton("Гимназия"), types.KeyboardButton("Энергия"))
        bot.send_message(message.chat.id, "Неверное место проведения. Пожалуйста, выберите из предложенных вариантов:", reply_markup=keyboard)
        bot.register_next_step_handler(message, get_location)

# Обработка выбора - добавить комментарий или пропустить
def handle_comment_choice(message):
    choice = message.text
    chat_id = message.chat.id

    if choice == "Добавить комментарий":
        bot.send_message(message.chat.id, "Введите комментарий к тренировке:")
        bot.register_next_step_handler(message, get_comment)
    elif choice == "Пропустить":
        poll_data[chat_id][-1]['comment'] = ""  # Сохраняем пустую строку как комментарий
        # После ввода всех данных - предлагаем добавить еще или закончить
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Добавить еще вариант"), types.KeyboardButton("Создать опрос"))
        bot.send_message(message.chat.id, "Что дальше?", reply_markup=keyboard)
        bot.register_next_step_handler(message, next_action)
    else:
        bot.send_message(message.chat.id, "Неверный выбор. Пожалуйста, выберите из предложенных вариантов:")
        bot.register_next_step_handler(message, handle_comment_choice)

# Получение комментария
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
        for i, option in enumerate(poll_data[chat_id]):  # Добавляем индекс к каждому варианту
            date = option['date']
            day = option['day']
            time = option['time']
            training_type = option['training_type']
            price = option['price']
            location = option['location']
            comment = option.get('comment', '')

            options.append(f"{date} ({day}) {time} - {training_type} ({location}, {price} руб.) {comment}")

        question = "Выберите тренировки:"

        # Создаем inline-клавиатуру
        keyboard = types.InlineKeyboardMarkup()
        for i, option_text in enumerate(options):
            # Используем индекс в качестве callback_data
            keyboard.add(types.InlineKeyboardButton(text=option_text, callback_data=str(i))) #callback_data - строка

        # Отправляем сообщение с inline-клавиатурой
        bot.send_message(chat_id, question, reply_markup=keyboard)

        # Очищать poll_data не нужно - нужно сохранить варианты для обработки выбора

    else:
        bot.send_message(chat_id, "Нет вариантов тренировок для создания опроса.")

@bot.callback_query_handler(func=lambda call: True) #Ловим все callback_query
def handle_callback_query(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    option_index = int(call.data)  # Получаем индекс выбранной тренировки из callback_data

    if user_id not in user_selections:
        user_selections[user_id] = []

    if option_index in user_selections[user_id]: #Если уже выбран - убираем
       user_selections[user_id].remove(option_index)
    else: #Если не выбран - добавляем
        user_selections[user_id].append(option_index)

    #Собираем текст из выбранных опций
    selected_options_text = ""
    for index in user_selections[user_id]:
        option = poll_data[chat_id][index] #Получаем данные тренировки по индексу
        date = option['date']
        day = option['day']
        time = option['time']
        training_type = option['training_type']
        price = option['price']
        location = option['location']
        comment = option.get('comment', '')
        selected_options_text += f"{date} ({day}) {time} - {training_type} ({location}, {price} руб.) {comment}\n" #Добавляем вариант

    #Создаем текст для сообщения
    if selected_options_text:
        text = f"Вы выбрали:\n{selected_options_text}"
    else:
        text = "Вы ничего не выбрали"


    #Создаем клавиатуру заново - с отметкой о выбранном
    options = []
    for i, option in enumerate(poll_data[chat_id]):  # Добавляем индекс к каждому варианту
            date = option['date']
            day = option['day']
            time = option['time']
            training_type = option['training_type']
            price = option['price']
            location = option['location']
            comment = option.get('comment', '')

            options.append(f"{date} ({day}) {time} - {training_type} ({location}, {price} руб.) {comment}")

    keyboard = types.InlineKeyboardMarkup()
    for i, option_text in enumerate(options):
        if i in user_selections[user_id]: #Если этот вариант выбран - добавляем галочку
            option_text = "✅ " + option_text
        keyboard.add(types.InlineKeyboardButton(text=option_text, callback_data=str(i)))

    #Редактируем сообщение, чтобы обновить клавиатуру и показать выбранные опции
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=keyboard)


# Запускаем бота
if __name__ == "__main__":
    print("Bot started!")
    bot.polling()