import telebot
import json
import admin
import users
import schedule
import threading
import datetime
import time
from admin import is_admin, admin_confirm_payment
from users import handle_poll_answer as users_handle_poll_answer
from users import handle_callback_query as users_handle_callback_query
from shared_data import load_polls

with open('config.json', 'r') as file:
    config_data = json.load(file)
TOKEN = config_data.get("token")

bot = telebot.TeleBot(TOKEN)

# Загрузка данных при старте бота
admin.poll_data = load_polls()
print(f"Main.py: admin.poll_data после загрузки: {admin.poll_data}") #Новая строка

# Установка команд при запуске
admin.set_commands(bot)


# Обработчик для команды /start для пользователей (в том числе и админов, но с каким-то условием)
@bot.message_handler(commands=['start'])
def handle_start(message):
    if is_admin(message):
        # Вызываем админскую команду вручную для админа:
        admin.admin_start_command(bot, message)
    else:
        # Обычный пользователь
        users.users_start_command(bot, message)


# Остальные команды пользователей
@bot.message_handler(commands=['help', 'status', 'voting'])
def handle_user_other_commands(message):
    if is_admin(message):
        return
    if message.text == '/help':
        users.help_command(bot, message)
    elif message.text == '/status':
        users.status(bot, message)
    elif message.text == '/voting':
        users.voting(bot, message)


# Админские команды
@bot.message_handler(commands=['create_poll', 'check_payments', 'edit_list', 'confirm_list'])
def handle_admin_commands(message):
    if not is_admin(message):
        # Блокируем доступ для не админов
        return
    if message.text == '/create_poll':
        admin.create_poll_command(bot, message)
    elif message.text == '/check_payments':
        admin.check_payments(bot, message)
    elif message.text == '/edit_list':
        admin.edit_list_command(bot, message)
    elif message.text == '/confirm_list':
        admin.confirm_list_command(bot, message)


# Обработчики для callback_query
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    if call.data.startswith("admin_confirm_"):
        admin.admin_confirm_payment(bot, call)  # Вызов функции для админа
    else:
        users.handle_callback_query(bot, call)  # Вызов функции для users.py


# Обработчик для poll_answer
@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    users.handle_poll_answer(bot, poll_answer)


if __name__ == '__main__':
    print("Бот запущен")
    admin.start_poll_scheduler(bot)  # Запуск планировщика
    # Запускаем бота в отдельном потоке
    threading.Thread(target=bot.polling, kwargs={'none_stop': True}).start()