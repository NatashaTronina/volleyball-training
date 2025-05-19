import telebot  
from telebot import types  
import json  
from admin import get_latest_poll, load_polls  
import qrcode  
from io import BytesIO 
import datetime 
import time 

data = ""
with open('config.json', 'r') as file:  
    data = json.load(file)  

TOKEN = data.get("token")  
bot = telebot.TeleBot(TOKEN)  

users = {}  
user_confirmed = {}  
message_ids = {} 
payment_timers = {}  

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
                    latest_poll = poll_item 
                    latest_poll_id = poll_id 

    if latest_poll:  
        return {latest_poll_id: [latest_poll]}  
    return None 

@bot.message_handler(commands=['start'])  
def start(message):
    user_id = message.from_user.id  
    username = message.from_user.username  
    first_name = message.from_user.first_name  

    users[user_id] = username 

    default_commands = [telebot.types.BotCommand("start", "Начать работу с ботом"),
        telebot.types.BotCommand("status", "Проверить свой статус оплаты"),
        telebot.types.BotCommand("voting", "Голосовать за тренировки"),
        telebot.types.BotCommand("help", "Получить справку")
    ]
    bot.set_my_commands(commands=default_commands, scope=telebot.types.BotCommandScopeChat(chat_id=message.chat.id))  # Устанавливаем список команд для данного чата

    bot.send_message(message.chat.id, f"Привет, {first_name}! Для голосования за тренировки нажми команду /voting")  # Отправляем приветственное сообщение

@bot.message_handler(commands=['status'])  
def status(message):
    user_id = message.from_user.id 
    if user_id in users:  
        print(f"Запрос статуса от пользователя: {user_id}")  
        try:
            payment_status = "Оплачено"  
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
        /voting - голосовать за тренировки
        /help - получение справки
        """
    bot.reply_to(message, help_text)  

@bot.message_handler(commands=['voting'])  
def send_latest_poll(message):
    chat_id = message.chat.id  
    latest_poll = get_latest_poll()  

    if latest_poll:  
        poll_id, poll_data_item = list(latest_poll.items())[0] 

        question = "Волейбол - выберите подходящий вариант:"  

        options = []  
        if isinstance(poll_data_item, list):  
            for option in poll_data_item: 
                if isinstance(option, dict):  
                    date = option.get('date', 'Не указана')  
                    day = option.get('day', 'Не указан') 
                    time = option.get('time', 'Не указано')  
                    training_type = option.get('training_type', 'Не указано') 
                    price = option.get('price', 0)  
                    location = option.get('location', 'Не указано') 
                    comment = option.get('comment', '')  
                    option_string = f"{date} ({day}) {time} - {training_type} ({location}, {price} руб.) {comment}"  
                    if len(option_string) > 90:  
                        option_string = option_string[:87] + "..." 
                    options.append(option_string)  

        options.append("Не пойду на волейбол")  
        try:
           sent_poll = bot.send_poll(message.chat.id, question=question, options=options, is_anonymous=False, allows_multiple_answers=True)  
           user_confirmed[message.from_user.id] = False  
           message_ids[message.from_user.id] = message_ids.get(message.from_user.id, {})  
           message_ids[message.from_user.id]["poll"] = sent_poll.message_id 
        except Exception as e:  
            bot.send_message(chat_id, f"Не удалось создать опрос: {e}")  
    else: 
        bot.send_message(message.chat.id, "Нет доступных опросов.")  

@bot.poll_answer_handler() 
def handle_poll_answer(poll_answer):
    user_id = poll_answer.user.id  
    poll_id = poll_answer.poll_id  
    option_ids = poll_answer.option_ids  
    chat_id = user_id  

    latest_poll = get_latest_poll() 
    total_price = 0

    if latest_poll: 
        poll_id_data, poll_data_item = list(latest_poll.items())[0] 

        if isinstance(poll_data_item, list) and len(poll_data_item) > 0:
            for index in option_ids: 
                if index < len(poll_data_item): 
                    option = poll_data_item[index] 
                    if isinstance(option, dict): 
                        price = option.get('price', 0) 
                        total_price += price 
            if not user_confirmed.get(user_id, False): 
                menu = telebot.types.InlineKeyboardMarkup() 
                menu.add(types.InlineKeyboardButton("Подтвердить", callback_data=f"confirm_{poll_id_data}_{total_price}")) 
                confirmation_message = bot.send_message(chat_id, f"Вы подтверждаете свои ответы?", reply_markup=menu)
                user_confirmed[user_id] = True 
                message_ids[user_id] = message_ids.get(user_id, {})
                message_ids[user_id]["confirm"] = confirmation_message.message_id 

        else: 
            bot.send_message(chat_id, "Не удалось получить данные о тренировках.")

    else: 
        bot.send_message(chat_id, "Нет активных опросов.")
def payment_timeout(user_id, qr_info, total_price):
    time.sleep(30)  # Поменять надо будет на нужное время

    if user_id in payment_timers: 
        try: 
            bot.delete_message(qr_info.chat.id, qr_info.message_id)
        except Exception as e: 
            print(f"Ошибка при удалении сообщения: {e}")

        keyboard = types.InlineKeyboardMarkup()
        pay_button = types.InlineKeyboardButton(text="Повторить получение реквизитов", callback_data=f"get_payment_{total_price}") # Повторно отправить информацию об оплате
        keyboard.add(pay_button)
        bot.send_message(qr_info.chat.id, "Вы не подтвердили оплату в течение 15 минут, нажмите кнопку для получения реквизитов.", reply_markup=keyboard)
        payment_timers.pop(user_id, None)

def show_payment(user_id, chat_id, payment_link, total_price): 
    """Отправляет QR-код и кнопку оплаты."""
    keyboard = types.InlineKeyboardMarkup()
    pay_button = types.InlineKeyboardButton(text="Оплатить", url=payment_link)
    keyboard.add(pay_button)
    # Генерируем QR-код
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(payment_link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="blue", back_color="white")
    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    # Отправляем сообщение с QR-кодом и кнопкой оплаты
    payment_message = bot.send_photo(chat_id, photo=bio, caption=f"Ваши ответы подтверждены. Общая сумма: {total_price} руб.\nДля оплаты нажмите на кнопку или отсканируйте QR-код.", reply_markup=keyboard)
    bio.close()
    confirm_keyboard = types.InlineKeyboardMarkup()
    confirm_button = types.InlineKeyboardButton(text="Да", callback_data=f"paid_{user_id}_{total_price}") # Если все работает как ожидалось, то сохраняем это
    cancel_button = types.InlineKeyboardButton(text="Нет", callback_data=f"cancel_payment_{user_id}_{total_price}") # Логика выполнена правильно.
    confirm_keyboard.add(confirm_button, cancel_button)
    bot.send_message(chat_id, "Вы подтверждаете оплату?", reply_markup=confirm_keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("get_payment_")) # Повторно отправляем оплату
def resend_payment(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    total_price = call.data.split("_")[2]
    latest_poll = get_latest_poll()
    payment_message = None
    if latest_poll:
        poll_id, poll_data_item = list(latest_poll.items())[0] 
        if isinstance(poll_data_item, list) and len(poll_data_item) > 0:
            payment_link = None

            for option in poll_data_item: 
                if isinstance(option, dict):
                    payment_link = option.get('payment_link') 
    show_payment(user_id, chat_id, payment_link, total_price)
    bot.answer_callback_query(call.id, "Реквизиты отправлены заново.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_payment_")) 
def cancel_payment(call): 
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    if user_id in payment_timers:
        payment_timers.pop(user_id, None)
        bot.send_message(chat_id, "Оплата отменена.")
    bot.answer_callback_query(call.id, "Оплата отменена.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("paid_")) 
def payment_confirmation(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    if user_id in payment_timers:
        payment_timers.pop(user_id, None)
    bot.send_message(chat_id, "Спасибо за оплату!")
    bot.answer_callback_query(call.id, "Оплата подтверждена, спасибо!")
    user_confirmed[user_id] = False

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

    message_ids.pop(user_id, None)
    latest_poll = get_latest_poll()
    payment_message = None

    if latest_poll:
        poll_id, poll_data_item = list(latest_poll.items())[0]


        if isinstance(poll_data_item, list) and len(poll_data_item) > 0:
            payment_link = None

            for option in poll_data_item:
                if isinstance(option, dict):
                    payment_link = option.get('payment_link') 
        if total_price == "0": 
            bot.send_message(chat_id, "Ваши ответы подтверждены. Спасибо!")
            user_confirmed[user_id] = False 
        else: 
            payment_message = show_payment(user_id, chat_id, payment_link, total_price)

if __name__ == "__main__": 
    print("User bot started!")
    bot.polling() 
