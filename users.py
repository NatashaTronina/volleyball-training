import telebot
from telebot import types
import json
from admin import is_admin, get_latest_poll  # Импортируем из админского кода нужные функции

data = ""
with open('config.json', 'r') as file:
    data = json.load(file)

TOKEN = data.get("token")
bot = telebot.TeleBot(TOKEN)

users = {}  # {user_id: username}
user_confirmed = {}  # Хранит, подтверждал ли пользователь свой голос
message_ids = {}  # Для хранения message_ids, ключ - user_id, значение - словарь с keys "poll" и "confirm"

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    users[user_id] = username

    default_commands = [
        telebot.types.BotCommand("start", "Начать работу с ботом"),
        telebot.types.BotCommand("status", "Проверить свой статус оплаты"),
        telebot.types.BotCommand("voting", "Голосовать за тренировки"),
        telebot.types.BotCommand("help", "Получить справку"),
        telebot.types.BotCommand("get_qr", "Получить QR-код для оплаты"),
    ]
    # Устанавливаем команды только для данного пользователя в приватном чате
    bot.set_my_commands(commands=default_commands, scope=telebot.types.BotCommandScopeChat(chat_id=message.chat.id))

    bot.send_message(message.chat.id, f"Привет, {first_name}! Для голосования за тренировки нажми команду /voting")


@bot.message_handler(commands=['status'])
def status(message):
    user_id = message.from_user.id
    if user_id in users:
        print(f"Запрос статуса от пользователя: {user_id}")
        try:
            payment_status = "Оплачено"  # Пример, здесь должна быть реальная логика проверки
            bot.reply_to(message, f"Ваш статус оплаты: {payment_status}")
        except Exception as e:
            bot.reply_to(message, f"Ошибка при проверке статуса оплаты: {e}")
    else:
        bot.reply_to(message, "Пожалуйста, сначала используйте команду /start, чтобы зарегистрироваться.")


@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """
Список команд:
/start - начало работы с ботом
/status - проверка своего статуса оплаты
/voting - голосование за тренировки
/help - получение справки
/get_qr - Получить QR-код после голосования
"""
    bot.reply_to(message, help_text)


@bot.message_handler(commands=['voting'])
def send_latest_poll(message):
    chat_id = message.chat.id
    latest_poll = get_latest_poll()

    if latest_poll:
        poll_id, poll_options = list(latest_poll.items())[0]
        question = "Волейбол - выберите подходящий вариант:"

        options = []
        for option in poll_options:
            if isinstance(option, dict):
                date = option.get('date', 'Не указана')
                day = option.get('day', 'Не указан')
                time = option.get('time', 'Не указано')
                training_type = option.get('training_type', 'Не указан')
                price = option.get('price', 0)
                location = option.get('location', 'Не указано')
                comment = option.get('comment', '')
                options.append(f"{date} ({day}) {time} - {training_type} ({location}, {price} руб.) {comment}")

        options.append("Не пойду на волейбол")

        try:
            sent_poll = bot.send_poll(chat_id, question=question, options=options, is_anonymous=False, allows_multiple_answers=True)
            user_confirmed[message.from_user.id] = False  # Сбрасываем статус подтверждения
            # Сохраняем message_id опроса
            message_ids[message.from_user.id] = message_ids.get(message.from_user.id, {})
            message_ids[message.from_user.id]["poll"] = sent_poll.message_id
        except Exception as e:
            bot.send_message(chat_id, f"Не удалось создать опрос: {e}")
    else:
        bot.send_message(chat_id, "Нет доступных опросов.")


@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    user_id = poll_answer.user.id
    poll_id = poll_answer.poll_id
    option_ids = poll_answer.option_ids
    chat_id = user_id  # Личные сообщения

    latest_poll = get_latest_poll()
    total_price = 0

    if latest_poll:
        poll_id_data, poll_options = list(latest_poll.items())[0]

        if isinstance(poll_options, list) and len(poll_options) > 0:
            for index in option_ids:
                if index < len(poll_options):
                    option = poll_options[index]
                    if isinstance(option, dict):
                        price = option.get('price', 0)
                        total_price += price

        # Проверяем, показывался ли уже запрос подтверждения
        if not user_confirmed.get(user_id, False):
            menu = telebot.types.InlineKeyboardMarkup()
            menu.add(types.InlineKeyboardButton("Подтвердить", callback_data=f"confirm_{poll_id_data}_{total_price}"))
            # Отправляем кнопку подтверждения
            confirmation_message = bot.send_message(chat_id, f"Вы подтверждаете свои ответы?", reply_markup=menu)
            user_confirmed[user_id] = True  # Отмечаем, что подтверждение показано
            # Сохраняем message_id подтверждения
            message_ids[user_id] = message_ids.get(user_id, {})
            message_ids[user_id]["confirm"] = confirmation_message.message_id


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def confirm_answers(call):
    user_id = call.from_user.id
    data = call.data.split("_")
    if len(data) < 3:
        bot.answer_callback_query(call.id, "Неверные данные для подтверждения.")
        return

    poll_id = data[1]
    total_price = data[2]
    chat_id = call.message.chat.id

    bot.answer_callback_query(call.id)

    # Удаляем сообщения подтверждения и опроса, если они есть
    msgs = message_ids.get(user_id, {})
    if "confirm" in msgs:
        try:
            bot.delete_message(chat_id, msgs["confirm"])
        except Exception as e:
            print(f"Ошибка удаления сообщения подтверждения: {e}")
    if "poll" in msgs:
        try:
            bot.delete_message(chat_id, msgs["poll"])
        except Exception as e:
            print(f"Ошибка удаления сообщения с опросом: {e}")

    # Удаляем из словаря id удаленных сообщений
    message_ids.pop(user_id, None)

    if total_price == "0":
        bot.send_message(chat_id, "Ваши ответы подтверждены. Спасибо!")
    else:
        bot.send_message(chat_id, f"Ваши ответы подтверждены. <b>Общая сумма: {total_price} руб.</b> Спасибо!", parse_mode='HTML')


if __name__ == "__main__":
    print("User bot started!")
    bot.polling()

