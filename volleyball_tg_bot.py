import telebot 
from telebot import types

bot = telebot.TeleBot('8129343330:AAGIEW_tVihFH_dT9jEADmYShO8ZluWJpDs')


@bot.message_handler(commands=['start'])

def start(message):
    bot.send_message(message.chat.id, f'Hello, {message.from_user.first_name}!')

@bot.message_handler(commands=['status'])

def status(message):
    bot.send_message(message.chat.id, 'Вы еще не записаны на тренировки')

@bot.message_handler(commands=['help'])

def help(message):
    bot.send_message(message.chat.id, 'Вам нужно выбрать даты тренировок, на которые вы придете')

@bot.message_handler(content_types=['photo'])

def get_photo(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Понедельник', callback_data='delete'))
    markup.add(types.InlineKeyboardButton('Вторник', callback_data='delete'))
    markup.add(types.InlineKeyboardButton('Среда', callback_data='delete'))
    markup.add(types.InlineKeyboardButton('Четверг', callback_data='delete'))
    markup.add(types.InlineKeyboardButton('Пятница', callback_data='delete'))
    markup.add(types.InlineKeyboardButton('Суббота', callback_data='delete'))
    markup.add(types.InlineKeyboardButton('Воскресенье', callback_data='delete'))
    bot.reply_to(message, 'Какое красивое фото', reply_markup=markup)


@bot.message_handler()

def info(message):
    if message.text.lower() == 'hello':
        bot.send_message(message.chat.id, f'Hello, {message.from_user.first_name}!')
    elif message.text.lower() == 'id':
        bot.reply_to(message, f'ID: {message.from_user.id}')

bot.polling(non_stop=True)