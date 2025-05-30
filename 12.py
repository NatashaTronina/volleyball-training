def admin_confirm_payment(bot, call):Add commentMore actions
    admin_id = call.from_user.id
@@ -383,6 +403,7 @@ def handle_callback_query(bot, call):
        confirm_payment(bot, call)

def confirm_payment(bot, call):
    print("confirm_payment: Функция вызвана!")
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    total_price = call.data.split("_")[-1]
def confirm_payment(bot, call):

        del awaiting_confirmation[user_id]

        admin_message = f"@{username} подтвердил оплату на сумму {total_price}"
        # Формируем сообщение с кликабельным именем пользователя
        admin_message = f"Пользователь [{username}](tg://user?id={user_id}) ожидает подтверждение оплаты на сумму {total_price} руб."

        keyboard = types.InlineKeyboardMarkup()
        confirm_button = types.InlineKeyboardButton(
            text="Подтвердить оплату", callback_data=f"admin_confirm_{user_id}_{total_price}"
        )
        keyboard.add(confirm_button)

        for admin_id in ADMIN_ID:
            bot.send_message(admin_id, admin_message, reply_markup=keyboard)
            bot.send_message(admin_id, admin_message, reply_markup=keyboard, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "Ошибка: Запрос на подтверждение не найден.")
        bot.answer_callback_query(call.id, "Произошла ошибка.")