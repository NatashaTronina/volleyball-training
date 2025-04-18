import telebot 
from telebot import types
from admin import *

data = ""
with open('config.json', 'r') as file:
    data = json.load(file)

TOKEN = data.get("token")

bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    item1 = types.KeyboardButton("Проголосовать")
    item2 = types.KeyboardButton("Статус оплаты")
    item3 = types.KeyboardButton("Помощь")
    markup.add(item1, item2, item3)


    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

@bot.message_handler(commands=['poll'])
def send_poll(message):
    chat_id = message.chat.id
    if chat_id in poll_data and poll_data[chat_id]:
        # Отправляем последний созданный опрос
        last_poll = poll_data[chat_id][-1]  # Получаем последний опрос
        options = [f"{option['date']} {option['time']} - {option['training_type']} ({option['location']}, {option['price']} руб.) {option.get('comment', '')}" for option in poll_data[chat_id]]
        options.append("Не пойду на волейбол")
        question = "Волейбол - выберите подходящий вариант:"
        
        sent_poll = bot.send_poll(chat_id, question=question, options=options, is_anonymous=False, allows_multiple_answers=True)
    else:
        bot.send_message(chat_id, "Нет доступных опросов.")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.text == "Статус оплаты":
        bot.send_message(message.chat.id, "Вы выбрали 'Статус оплаты'")
    elif message.text == "Помощь":
        bot.send_message(message.chat.id, "Вам нужно нажать кнопку 'Проголосовать', чтобы выбрать тренировки")

if __name__ == "__main__":
    print("Bot started!")
    bot.polling()
