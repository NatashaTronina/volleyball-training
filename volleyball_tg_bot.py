import telebot 
from telebot import types
# from admin import *


TOKEN = "8168346913:AAGRZOpM82osSB4fUuWrbzWtVLwkeS4hzO0"
bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    item1 = types.KeyboardButton("Проголосовать")
    item2 = types.KeyboardButton("Статус оплаты")
    item3 = types.KeyboardButton("Помощь")
    markup.add(item1, item2, item3)


    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.text == "Проголосовать":
        bot.send_message(message.chat.id, "Вы выбрали 'Проголосовать'")
        # Здесь ваш код для обработки нажатия кнопки "Начать"
    elif message.text == "Статус оплаты":
        bot.send_message(message.chat.id, "Вы выбрали 'Статус оплаты'")
    elif message.text == "Помощь":
        bot.send_message(message.chat.id, "Вам нужно нажать кнопку 'Проголосовать', чтобы выбрать тренировки")

if __name__ == "__main__":
    print("Bot started!")
    bot.polling()
