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
    bot.reply_to(message, "Привет! Я ваш бот. С помощью меня вы можете выбрать тренировки по волейболу, на которые пойдете.\n Для получения справки используйте /help.")

@bot.message_handler(commands=['status'])
def status(message):
    user_id = message.from_user.id
    # Здесь нужно реализовать логику проверки статуса оплаты пользователя.
    # Это может включать запрос к базе данных, API оплаты и т.д.
    try:
        # Замените на вашу логику
        payment_status = "Оплачено"  # Пример
        bot.reply_to(message, f"Ваш статус оплаты: {payment_status}")
    except Exception as e:
        bot.reply_to(message, f"Ошибка при проверке статуса оплаты: {e}")

@bot.message_handler(commands=['help'])
def help(message):
    help_text = """
    Список команд:
    /start - начало работы с ботом
    /status - проверка своего статуса оплаты
    /help - получение справки
    """
    bot.reply_to(message, help_text)
