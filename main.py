import telebot
import json

import admin
import users

with open('config.json', 'r') as file:
    config_data = json.load(file)
TOKEN = config_data.get("token")

bot = telebot.TeleBot(TOKEN)
awaiting_confirmation = {}

admin.set_commands(bot)

# Обработчики для команд пользователей
@bot.message_handler(commands=['start', 'help', 'status', 'voting'])
def handle_users_commands(message):
    if message.text == '/start':
        users.start_command(bot, message)
    elif message.text == '/help':
        users.help_command(bot, message)
    elif message.text == '/status':
        users.status(bot, message)
    elif message.text == '/voting':
        users.voting(bot, message)

# Обработчики для команд администратора
@bot.message_handler(commands=['create_poll', 'check_payments', 'edit_list', 'confirm_list'])
def handle_admin_commands(message):
    if message.text == '/create_poll':
        admin.create_poll_command(bot, message)
    elif message.text == '/check_payments':
        admin.check_payments(bot, message)
    elif message.text == '/edit_list':
        admin.check_payments(bot, message)
    elif message.text == '/confirm_list':
        admin.check_payments(bot, message)

# Обработчики для callback_query (кнопки)
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    if call.data.startswith('poll_correct') or call.data.startswith('poll_edit') or call.data.startswith("admin_confirm_"):
        admin.handle_callback_query(bot, call)
    elif call.data.startswith("confirm_payment_") or call.data.startswith("cancel_payment_") or call.data.startswith("paid_") or call.data.startswith("confirm_") or call.data.startswith("get_payment_") or call.data.startswith("re"):
        users.handle_callback_query(bot, call)

# Обработчик для poll_answer
@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    users.handle_poll_answer(bot, poll_answer)

# Бесконечный цикл работы бота
print("Бот запущен")
bot.polling()