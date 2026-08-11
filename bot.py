import os
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Telegram kanal
CHANNEL = "@AstrumMED"
CHANNEL_URL = "https://t.me/AstrumMED"

# YouTube kanal
YOUTUBE_URL = "https://youtube.com/@astrummed_1"


# =========================
# LOGGING
# =========================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================
# START
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    keyboard = [
        [
            InlineKeyboardButton(
                "📢 Telegram kanaliga obuna bo‘lish",
                url=CHANNEL_URL
            )
        ],
        [
            InlineKeyboardButton(
                "▶️ YouTube kanaliga obuna bo‘lish",
                url=YOUTUBE_URL
            )
        ],
        [
            InlineKeyboardButton(
                "✅ Obunani tekshirish",
                callback_data="check_subscription"
            )
        ],
    ]

    text = (
        "Assalomu alaykum, hurmatli doktor! 👋\n\n"
        "📚 AstrumMED kanaliga tegishli Terapiya kitoblari "
        "uchun maxsus chegirmaga ega bo‘lmoqchi bo‘lsangiz, "
        "quyidagi kanallarga obuna bo‘lishingiz va "
        "maxsus linkni olishingizni so‘raymiz!"
    )

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# TELEGRAM OBUNANI TEKSHIRISH
# =========================

async def check_subscription(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    try:

        member = await context.bot.get_chat_member(
            chat_id=CHANNEL,
            user_id=user_id
        )

        subscribed = member.status in (
            "member",
            "administrator",
            "creator",
            "restricted"
        )

    except Exception as e:

        logger.error(
            "Subscription check error: %s",
            e,
            exc_info=True
        )

        await query.edit_message_text(
            "⚠️ Obunani tekshirishda xatolik yuz berdi.\n\n"
            "Iltimos, birozdan keyin qayta urinib ko‘ring."
        )

        return


    # =========================
    # OBUNA BO'LMAGAN
    # =========================

    if not subscribed:

        keyboard = [
            [
                InlineKeyboardButton(
                    "📢 Telegram kanaliga obuna bo‘lish",
                    url=CHANNEL_URL
                )
            ],
            [
                InlineKeyboardButton(
                    "🔄 Qayta tekshirish",
                    callback_data="check_subscription"
                )
            ],
        ]

        await query.edit_message_text(
            "❌ Siz hali @AstrumMED kanaliga "
            "obuna bo‘lmagansiz.\n\n"
            "Avval kanalga obuna bo‘ling, "
            "keyin «Qayta tekshirish» tugmasini bosing.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return


    # =========================
    # OBUNA BO'LGAN
    # =========================

    keyboard = [
        [
            InlineKeyboardButton(
                "▶️ YouTube kanaliga o‘tish",
                url=YOUTUBE_URL
            )
        ],
        [
            InlineKeyboardButton(
                "👥 Keyingi bosqich",
                callback_data="next_step"
            )
        ],
    ]

    await query.edit_message_text(
        "✅ Telegram kanaliga obunangiz tasdiqlandi!\n\n"
        "Endi YouTube kanalimizga ham obuna bo‘ling.\n\n"
        "▶️ YouTube kanaliga o‘tish tugmasini bosing.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# KEYINGI BOSQICH
# =========================

async def next_step(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    await query.edit_message_text(
        "🎉 Birinchi bosqich muvaffaqiyatli bajarildi!\n\n"
        "✅ Telegram kanal obunasi tasdiqlandi.\n\n"
        "👥 Keyingi bosqichda 5 ta do‘stni taklif qilish "
        "tizimini qo‘shamiz."
    )


# =========================
# ERROR HANDLER
# =========================

async def error_handler(
    update,
    context
):

    logger.error(
        "BOT ERROR: %s",
        context.error,
        exc_info=True
    )


# =========================
# MAIN
# =========================

def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN topilmadi!"
        )

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            check_subscription,
            pattern="^check_subscription$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            next_step,
            pattern="^next_step$"
        )
    )

    app.add_error_handler(
        error_handler
    )

    logger.info(
        "AstrumMED bot started successfully"
    )

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
