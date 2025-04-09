import re
import telebot
from telebot import types

# Замените на свой токен
TOKEN = "8168346913:AAGRZOpM82osSB4fUuWrbzWtVLwkeS4hzO0"  # Замените на токен вашего бота
bot = telebot.TeleBot(TOKEN)

# ID администратора (замените на свой ID)
ADMIN_ID = 494635818  # Замените на свой ID

# Состояние опроса (для хранения промежуточных данных)
poll_data = {}  # {chat_id: [ {date, day, time, training_type, price, location, comment}, ... ]}

# Словарь для хранения результатов опросов. Ключ - poll_id, значение - словарь,
# где ключ - индекс варианта, а значение - кол-во проголосовавших.
poll_results = {}  # {poll_id: {option_index: vote_count, ...}, ...}

# Проверка на админа
def is_admin(message):
    return message.from_user.id == ADMIN_ID

# Обработчик команды /create_poll
@bot.message_handler(commands=['create_poll'])
def create_poll_command(message):
    if is_admin(message):
        chat_id = message.chat.id
        poll_data[chat_id] = []  # Инициализируем список вариантов
        # Сразу предлагаем добавить первый вариант
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

        bot.send_message(message.chat.id, "Введите время тренировки в формате ЧЧ-ММ (например, 12-00):",
                         reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, get_time)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        for day_name in days:  # Используем другое имя переменной, чтобы не путать с 'day'
            keyboard.add(types.KeyboardButton(day_name))
        bot.send_message(message.chat.id, "Неверный день недели. Пожалуйста, выберите из предложенных вариантов:",
                         reply_markup=keyboard)
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
        bot.send_message(message.chat.id, "Неверный тип тренировки. Пожалуйста, выберите из предложенных вариантов:",
                        reply_markup=keyboard)
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
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Гимназия"), types.KeyboardButton("Энергия"))
        bot.send_message(message.chat.id, "Неверное место проведения. Пожалуйста, выберите из предложенных вариантов:",
                        reply_markup=keyboard)
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
        # Предлагаем выбор: создать опрос или добавить еще вариант - ReplyKeyboardMarkup
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Создать опрос"), types.KeyboardButton("Добавить еще вариант"))
        bot.send_message(chat_id, "Что дальше?", reply_markup=keyboard)
        bot.register_next_step_handler(message, next_action)
    else:
        bot.send_message(message.chat.id, "Неверный выбор. Пожалуйста, выберите из предложенных вариантов:")
        bot.register_next_step_handler(message, handle_comment_choice)

# Получение комментария
def get_comment(message):
    comment = message.text
    chat_id = message.chat.id
    # Предлагаем выбор: создать опрос или добавить еще вариант - ReplyKeyboardMarkup
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("Создать опрос"), types.KeyboardButton("Добавить еще вариант"))
    bot.send_message(chat_id, "Что дальше?", reply_markup=keyboard)
    bot.register_next_step_handler(message, next_action)


# Создание и отправка опроса
def create_and_send_poll(message):
    chat_id = message.chat.id
    options = []
    for option in poll_data[chat_id]:
        date = option['date']
        day = option['day']
        time = option['time']
        training_type = option['training_type']
        price = option['price']
        location = option['location']
        comment = option.get('comment', '')
        options.append(f"{date} ({day}) {time} - {training_type} ({location}, {price} руб.) {comment}")

    options.append("Не пойду на волейбол")
    question = "Волейбол - выберите подходящий вариант:"

    try:
        # Отправляем опрос
        sent_poll = bot.send_poll(chat_id, question=question, options=options, is_anonymous=False,
                                    allows_multiple_answers=True)  # allow_multiple_answers=True - можно выбирать несколько вариантов

        poll_id = sent_poll.poll.id  # Получаем ID созданного опроса

        # Инициализируем результаты для этого опроса
        poll_results[poll_id] = {}
        for i in range(len(options)):
            poll_results[poll_id][i] = 0

        # Создаем кнопки
        keyboard = types.InlineKeyboardMarkup()
        button_correct = types.InlineKeyboardButton(text="Опрос верный", callback_data=f'poll_correct_{poll_id}')
        button_edit = types.InlineKeyboardButton(text="Пересоздать опрос", callback_data=f'poll_edit_{poll_id}')
        keyboard.add(button_correct, button_edit)

        # Отправляем сообщение с кнопками
        bot.send_message(chat_id, "Подтвердите опрос:", reply_markup=keyboard)

    except Exception as e:
        bot.send_message(chat_id, f"Не удалось создать опрос: {e}")  # Обработка ошибок

@bot.callback_query_handler(func=lambda call: call.data.startswith('poll_correct') or call.data.startswith('poll_edit') or call.data == 'add_option')
def callback_query(call):
    chat_id = call.message.chat.id
    callback_data = call.data

    if callback_data.startswith('poll_correct'):
        # Действия, если опрос верный
        bot.send_message(chat_id, "Отлично! Теперь отправьте QR-код для оплаты тренировок (как изображение).")
        bot.register_next_step_handler(call.message, handle_qr_code) #  Переходим к обработке QR-кода

    elif callback_data.startswith('poll_edit'):
        # Действия, если нужно пересоздать опрос
        bot.send_message(chat_id, "Начинаем пересоздание опроса...")
        # Возвращаемся к началу создания опроса
        poll_data[chat_id].clear()  # Очищаем данные для пересоздания
        bot.send_message(chat_id, "Введите дату тренировки в формате ДД.ММ (например, 27.03):")
        bot.register_next_step_handler(call.message, get_date)
    elif callback_data == 'add_option':
        bot.send_message(chat_id, "Введите дату тренировки в формате ДД.ММ (например, 27.03):")
        bot.register_next_step_handler(call.message, get_date) # Возврат к запросу даты

# Обработчик QR-кода (фотографии)
def handle_qr_code(message):
    chat_id = message.chat.id

    if message.photo:
        #  Получаем информацию о фотографии
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        bot.send_message(chat_id, "QR-код сохранен.")
    else:
        bot.send_message(chat_id, "Пожалуйста, отправьте QR-код как *изображение*.", parse_mode="Markdown") # Предупреждение, если отправлено не изображение

# Обработка выбора - добавить еще или создать опрос
@bot.message_handler(func=lambda message: True)  # Ловим любой текстовый ответ
def next_action(message):
    action = message.text
    chat_id = message.chat.id

    if action == "Добавить еще вариант":
        bot.send_message(chat_id, "Введите дату тренировки в формате ДД.ММ (например, 27.03):",
                        reply_markup=types.ReplyKeyboardRemove())  # Убираем клаву
        bot.register_next_step_handler(message, get_date)  # Запускаем сначала ввод данных
    elif action == "Создать опрос":
        # Создаем и отправляем опрос
        create_and_send_poll(message)
    else:
        bot.send_message(chat_id, "Неверный выбор. Пожалуйста, выберите из предложенных вариантов:")
        # Опять предлагаем выбор: создать опрос или добавить еще вариант - ReplyKeyboardMarkup
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Создать опрос"), types.KeyboardButton("Добавить еще вариант"))
        bot.send_message(chat_id, "Что дальше?", reply_markup=keyboard)
        bot.register_next_step_handler(message, next_action) # Запускаем заново обработчик

@bot.poll_answer_handler()  # Ловим ответы на опросы
def handle_poll_answer(poll_answer):
    chat_id = poll_answer.user.id  # ID пользователя, который ответил на опрос
    poll_id = poll_answer.poll_id
    option_ids = poll_answer.option_ids  # Список номеров выбранных опций

    global poll_results

    # Проверяем, существует ли опрос в poll_results
    if poll_id not in poll_results:
        print(f"WARNING: poll_id {poll_id} not found in poll_results")
        return

    # Создаем копию poll_results[poll_id], чтобы избежать изменения во время итерации
    poll_results_copy = poll_results[poll_id].copy()

    # Сначала уменьшаем голоса для всех опций, которые раньше были выбраны этим пользователем, но теперь не выбраны
    for i in poll_results_copy:
        if i not in option_ids and poll_results_copy[i] > 0:  # Если вариант больше не выбран и за него кто-то голосовал
            poll_results[poll_id][i] -= 1  # Уменьшаем кол-во голосов

    # Теперь увеличиваем голоса для тех опций, которые были выбраны, но ранее не были
    for i in option_ids:
        if i not in poll_results_copy:
            poll_results[poll_id][i] = 0  # Если такого варианта еще нет - создаем
        if i not in poll_results_copy or poll_results_copy[i] == 0:  # Если вариант новый или за него никто не голосовал
            poll_results[poll_id][i] += 1  # Увеличиваем кол-во голосов

if __name__ == "__main__":
    print("Bot started!")
    bot.polling()