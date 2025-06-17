import telebot
import json
import admin
import users
import threading
from admin import is_admin
from shared_data import load_polls
from ggl import authenticate_google_sheets

client = authenticate_google_sheets('vocal-circle-461812-m7-06081970720e.json')
with open('config.json', 'r') as file:
    config_data = json.load(file)
TOKEN = config_data.get("token")

bot = telebot.TeleBot(TOKEN)

admin.poll_data = load_polls()
admin.set_commands(bot)

def handle_start_command(message):
    if is_admin(message):
        admin.admin_start_command(bot, message)
    else:
        users.users_start_command(bot, message)

@bot.message_handler(commands=['start'])
def handle_start(message):
    handle_start_command(message)

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

@bot.message_handler(commands=['create_poll', 'check_payments', 'check_list'])
def handle_admin_commands(message):
    if not is_admin(message):
        return
    if message.text == '/create_poll':
        admin.create_poll_command(bot, message)
    elif message.text == '/check_payments':
        admin.check_payments(bot, message)
    elif message.text == '/check_list': 
        admin.check_list_command(bot, message)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    if (call.data.startswith("training_selected_") or call.data.startswith("edit_list_") or call.data.startswith("remove_user_") 
        or call.data.startswith("admin_confirm_") or call.data.startswith('poll_confirm') or call.data.startswith('poll_edit') 
        or call.data.startswith("cancel_creation_")):
        admin.admin_handle_callback_query(bot, call)  
    else:
        users.handle_callback_query(bot, call)  

@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    users.handle_poll_answer(bot, poll_answer)

@bot.message_handler(func=lambda message: True)  
def handle_all_text_messages(message):
    if message.text.startswith('/'):
        return
    users.handle_name_input(bot, message)


if __name__ == '__main__':
    print("Бот запущен")
    admin.start_poll_scheduler(bot)
    threading.Thread(target=bot.polling, kwargs={'none_stop': True}).start()