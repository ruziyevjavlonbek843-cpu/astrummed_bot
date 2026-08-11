import os
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

BOT_TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎉 BOT ISHLAYAPTI!\n\n"
        "Assalomu alaykum!\n"
        "AstrumMED bot muvaffaqiyatli ishga tushdi."
    )


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ TEST ISHLAYAPTI!")


def main():

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi!")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test))

    print("BOT ISHLAYAPTI...")
    
    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
