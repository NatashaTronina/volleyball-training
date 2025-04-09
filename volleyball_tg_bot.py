import telebot 
from telebot import types
from admin import *


TOKEN = "8168346913:AAGRZOpM82osSB4fUuWrbzWtVLwkeS4hzO0"
bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    item1 = types.KeyboardButton("Начать")
    item2 = types.KeyboardButton("Статус оплаты")
    item3 = types.KeyboardButton("Помощь")
    markup.add(item1, item2, item3)


    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.text == "Начать":
        bot.send_message(message.chat.id, "Вы выбрали 'Начать'")
        # Здесь ваш код для обработки нажатия кнопки "Начать"
    elif message.text == "Статус оплаты":
        bot.send_message(message.chat.id, "Вы выбрали 'Статус оплаты'")
    elif message.text == "Помощь":
        bot.send_message(message.chat.id, "Вы выбрали 'Помощь'")

print("User Bot started!")
bot.polling(none_stop=True)
