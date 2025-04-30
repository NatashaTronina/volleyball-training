import telebot
from telebot import types
import json
import os
from admin import is_admin, get_latest_poll  # Импортируем функцию для получения последнего опроса

data = ""
with open('config.json', 'r') as file:
    data = json.load(file)

TOKEN = data.get("token")
bot = telebot.TeleBot(TOKEN)

# Словарь для хранения ID пользователей (можно заменить на базу данных)
users = {}  # {user_id: username} - пример структуры

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    users[user_id] = username

    # Устанавливаем дефолтные команды для текущего пользователя
    default_commands = [
        telebot.types.BotCommand("start", "Начать работу с ботом"),
        telebot.types.BotCommand("status", "Проверить свой статус оплаты"),
        telebot.types.BotCommand("voting", "Голосовать за тренировки"),
        telebot.types.BotCommand("help", "Получить справку")
    ]
    bot.set_my_commands(commands=default_commands, scope=telebot.types.BotCommandScopeChat(chat_id=message.chat.id))

    bot.send_message(message.chat.id, f"Привет, {first_name}! Для голосования за тренировки нажми команду /voting")

@bot.message_handler(commands=['status'])
def status(message):
    user_id = message.from_user.id
    if user_id in users:
        print(f"Запрос статуса от пользователя: {user_id}")
        try:
            payment_status = "Оплачено"  # Пример
            bot.reply_to(message, f"Ваш статус оплаты: {payment_status}")
        except Exception as e:
            bot.reply_to(message, f"Ошибка при проверке статуса оплаты: {e}")
    else:
        bot.reply_to(message, "Пожалуйста, сначала используйте команду /start, чтобы зарегистрироваться.")

@bot.message_handler(commands=['help'])
def help(message):
    help_text = """
    Список команд:
    /start - начало работы с ботом
    /status - проверка своего статуса оплаты
    /voting - голосование за тренировки
    /help - получение справки
    """
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['voting'])
def send_latest_poll(message):
    chat_id = message.chat.id
    latest_poll = get_latest_poll()  # Получаем самый свежий опрос

    if latest_poll:
        poll_id, poll_options = list(latest_poll.items())[0]  # Получаем ID и все варианты опроса
        question = "Волейбол - выберите подходящий вариант:"
        
        options = []
        for option in poll_options:
            options.append(f"{option['date']} ({option['day']}) {option['time']} - {option['training_type']} ({option['location']}, {option['price']} руб.) {option['comment']}")
        
        options.append("Не пойду на волейбол")  # Добавляем вариант по умолчанию

        # Отправляем опрос
        bot.send_poll(message.chat.id, question=question, options=options, is_anonymous=False, allows_multiple_answers=True)
    else:
        bot.send_message(message.chat.id, "Нет доступных опросов.")

@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    user_id = poll_answer.user.id
    poll_id = poll_answer.poll_id
    option_ids = poll_answer.option_ids

    # Получаем последний опрос
    latest_poll = get_latest_poll()
    total_price = 0  # Сбрасываем total_price для каждого нового голосования
    has_paid_option = False  # Флаг для отслеживания, выбрана ли платная опция

    # Получаем варианты опроса
    if latest_poll:
        poll_options = list(latest_poll.values())[0]  # Получаем варианты опроса

        # Проверяем, выбрал ли пользователь вариант "Не пойду на волейбол"
        for index in option_ids:
            if index < len(poll_options):  # Проверяем, что индекс в пределах допустимого диапазона
                # Проверяем, не является ли выбранный вариант последним (не пойду на волейбол)
                if index == len(poll_options):  # Предполагаем, что последний вариант - "Не пойду на волейбол"
                    continue  # Пропускаем этот вариант
                price = poll_options[index]['price']  # Получаем цену по индексу
                total_price += price  # Суммируем стоимость
                has_paid_option = True  # Устанавливаем флаг, если выбрана платная опция

            menu = telebot.types.InlineKeyboardMarkup()
            menu.add(types.InlineKeyboardButton("Подтвердить", callback_data=f"confirm_{poll_id}_{total_price}"))
            bot.send_message(user_id, "Вы подтверждаете свои ответы?", reply_markup=menu)

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def confirm_answers(call):
    user_id = call.from_user.id
    poll_data = call.data.split("_")
    poll_id = poll_data[1]
    total_price = poll_data[2]  # Получаем общую сумму из callback_data

    bot.answer_callback_query(call.id) 

    # Проверяем, если сумма 0, отправляем соответствующее сообщение
    if total_price == "0":
        bot.send_message(call.message.chat.id, "Ваши ответы подтверждены. Спасибо!")
    else:
        bot.send_message(call.message.chat.id, f"Ваши ответы подтверждены. <b>Общая сумма: {total_price} руб.</b> Спасибо!", parse_mode='HTML')
if __name__ == "__main__":
    print("User bot started!")
    bot.polling()