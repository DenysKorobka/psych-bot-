import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Посилання на Mini App
WEBAPP_URL = "https://denyskorobka.github.io/psych-miniapp/"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    first_name = update.effective_user.first_name or "друже"

    text = (
        f"Привіт, {first_name}! 👋\n\n"
        "Це демо інтерактивного Telegram-додатку, який показує, "
        "як можуть виглядати сучасні боти для бізнесу.\n\n"

        "Всередині ти зможеш подивитись:\n"
        "• AI-чат з помічником\n"
        "• зручний інтерфейс\n"
        "• сценарії взаємодії з клієнтами\n"
        "• автоматизацію заявок та записів\n\n"

        "Спробуй функціонал у дії та подивись, "
        "як подібне рішення може працювати для твого проєкту 👇"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔥 Спробувати додаток",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        ]
    ])

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
