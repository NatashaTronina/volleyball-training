
import telebot
from admin import bot
from admin import ADMIN_ID

def set_commands():
    # ВСЕ ПОЛЬЗОВАТЕЛИ
    default_commands = [
        telebot.types.BotCommand("start", "Начать работу с ботом"),
        telebot.types.BotCommand("status", "Проверить свой статус оплаты"),
        telebot.types.BotCommand("help", "Получить справку")
    ]
    bot.set_my_commands(commands=default_commands)
    # ТОЛЬКО АДМИН
    for admin_id in ADMIN_ID:
        admin_scope = telebot.types.botCommandScopeChatAdmins(chat_id=admin_id)
        admin_commands = [
            telebot.types.BotCommand("create_poll", "Создать опрос"),
            telebot.types.BotCommand("check_payments", "Проверить статусы оплат"),
            telebot.types.BotCommand("edit_list", "Редактировать список"),
            telebot.types.BotCommand("confirm_list", "Подтвердить список")
        ]
        bot.set_my_commands(commands=admin_commands, scope=admin_scope)

set_commands()