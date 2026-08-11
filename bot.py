import os
import logging
import psycopg

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

TELEGRAM_CHANNEL = "@AstrumMED"
TELEGRAM_CHANNEL_URL = "https://t.me/AstrumMED"
YOUTUBE_URL = "https://youtube.com/@astrummed_1"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================
# DATABASE
# =========================

def db():
    return psycopg.connect(DATABASE_URL)


def init_db():
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    referred_by BIGINT,
                    referral_count INTEGER DEFAULT 0,
                    referral_counted BOOLEAN DEFAULT FALSE,
                    telegram_verified BOOLEAN DEFAULT FALSE
                )
            """)
        conn.commit()


def add_user(user_id, referred_by=None):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (user_id, referred_by)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO NOTHING
                """,
                (user_id, referred_by),
            )
        conn.commit()


def get_user(user_id):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id,
                       referred_by,
                       referral_count,
                       referral_counted,
                       telegram_verified
                FROM users
                WHERE user_id = %s
                """,
                (user_id,),
            )
            return cur.fetchone()


def verify_user(user_id):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET telegram_verified = TRUE
                WHERE user_id = %s
                """,
                (user_id,),
            )
        conn.commit()


def count_referral(user_id):
    """
    Foydalanuvchi kanalga obuna bo'lganda,
    uni taklif qilgan odamga 1 ta referral qo'shiladi.
    """

    user = get_user(user_id)

    if not user:
        return

    referred_by = user[1]
    already_counted = user[3]

    if not referred_by:
        return

    if already_counted:
        return

    if referred_by == user_id:
        return

    with db() as conn:
        with conn.cursor() as cur:

            # Bu foydalanuvchining referral'i hisoblanganini belgilash
            cur.execute(
                """
                UPDATE users
                SET referral_counted = TRUE
                WHERE user_id = %s
                """,
                (user_id,),
            )

            # Taklif qilgan odamga +1
            cur.execute(
                """
                UPDATE users
                SET referral_count = referral_count + 1
                WHERE user_id = %s
                """,
                (referred_by,),
            )

        conn.commit()


# =========================
# TELEGRAM OBUNANI TEKSHIRISH
# =========================

async def is_subscribed(bot, user_id):

    try:
        member = await bot.get_chat_member(
            chat_id=TELEGRAM_CHANNEL,
            user_id=user_id
        )

        return member.status in (
            "member",
            "administrator",
            "creator",
            "restricted"
        )

    except Exception as e:
        logger.error("Subscription check error: %s", e)
        return False


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    referred_by = None

    # /start 123456
    if context.args:

        try:
            referred_by = int(context.args[0])

            # O'zini o'zi taklif qilishni taqiqlash
            if referred_by == user_id:
                referred_by = None

        except ValueError:
            referred_by = None

    add_user(
        user_id=user_id,
        referred_by=referred_by
    )

    keyboard = [

        [
            InlineKeyboardButton(
                "📢 Telegram kanaliga obuna bo‘lish",
                url=TELEGRAM_CHANNEL_URL
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
                callback_data="check"
            )
        ]

    ]

    text = (
        "👋 Assalomu alaykum!\n\n"

        "🎓 Maxsus materialga ega bo‘lish uchun "
        "quyidagi shartlarni bajaring:\n\n"

        "1️⃣ Telegram kanaliga obuna bo‘ling.\n"
        "2️⃣ YouTube kanaliga obuna bo‘ling.\n"
        "3️⃣ «Obunani tekshirish» tugmasini bosing.\n\n"

        "Keyin sizga shaxsiy taklif havolangiz beriladi."
    )

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# OBUNANI TEKSHIRISH
# =========================

async def check_subscription(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    subscribed = await is_subscribed(
        context.bot,
        user_id
    )

    if not subscribed:

        keyboard = [

            [
                InlineKeyboardButton(
                    "📢 Kanalga obuna bo‘lish",
                    url=TELEGRAM_CHANNEL_URL
                )
            ],

            [
                InlineKeyboardButton(
                    "🔄 Qayta tekshirish",
                    callback_data="check"
                )
            ]

        ]

        await query.edit_message_text(
            "❌ Siz hali @AstrumMED kanaliga "
            "obuna bo‘lmagansiz.\n\n"
            "Avval kanalga obuna bo‘ling, "
            "keyin «Qayta tekshirish»ni bosing.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # Telegram obuna tasdiqlandi
    verify_user(user_id)

    # Agar bu odam kimningdir referral havolasi
    # orqali kelgan bo'lsa, referral hisoblanadi
    count_referral(user_id)

    user = get_user(user_id)

    referral_count = user[2]

    keyboard = [

        [
            InlineKeyboardButton(
                "▶️ YouTube kanaliga o‘tish",
                url=YOUTUBE_URL
            )
        ],

        [
            InlineKeyboardButton(
                "👥 5 ta do‘stni taklif qilish",
                callback_data="referral"
            )
        ]

    ]

    await query.edit_message_text(

        f"✅ Telegram obunangiz tasdiqlandi!\n\n"

        f"👥 Siz taklif qilgan do‘stlar: "
        f"{referral_count}/5\n\n"

        f"Endi YouTube kanalimizga ham obuna bo‘ling.\n\n"

        f"Keyin «5 ta do‘stni taklif qilish» tugmasini bosing.",

        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# REFERAL
# =========================

async def referral(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    user = get_user(user_id)

    if not user:
        add_user(user_id)
        user = get_user(user_id)

    referral_count = user[2]

    bot = await context.bot.get_me()

    referral_link = (
        f"https://t.me/{bot.username}?start={user_id}"
    )

    # Telegram share tugmasi
    share_url = (
        "https://t.me/share/url"
        f"?url={referral_link}"
        "&text=Maxsus material uchun botga kiring:"
    )

    # 5 ta odam bo'lsa
    if referral_count >= 5:

        await query.edit_message_text(

            "🎉 TABRIKLAYMIZ!\n\n"

            "✅ Barcha shartlar bajarildi!\n\n"

            "👥 Siz 5 ta do‘stni muvaffaqiyatli "
            "taklif qildingiz.\n\n"

            "🎓 Endi maxsus materialdan foydalanishingiz mumkin."

        )

        return

    keyboard = [

        [
            InlineKeyboardButton(
                "📤 Do‘stlarga yuborish",
                url=share_url
            )
        ],

        [
            InlineKeyboardButton(
                "🔄 Natijani tekshirish",
                callback_data="referral"
            )
        ]

    ]

    await query.edit_message_text(

        f"👥 DO‘STLARNI TAKLIF QILING\n\n"

        f"📊 Natija: {referral_count}/5\n\n"

        f"Quyidagi tugmani bosing va "
        f"shaxsiy havolangizni 5 ta do‘stingizga yuboring.\n\n"

        f"⚠️ Do‘stingiz havola orqali botga kirib, "
        f"@AstrumMED kanaliga obuna bo‘lgandan keyin "
        f"hisoblanadi.\n\n"

        f"🔗 Sizning havolangiz:\n"
        f"{referral_link}",

        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# ERROR
# =========================

async def error_handler(
    update,
    context
):

    logger.error(
        "Bot error:",
        exc_info=context.error
    )


# =========================
# MAIN
# =========================

def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN topilmadi!"
        )

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL topilmadi!"
        )

    init_db()

    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            check_subscription,
            pattern="^check$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            referral,
            pattern="^referral$"
        )
    )

    application.add_error_handler(
        error_handler
    )

    application.run_polling()


if __name__ == "__main__":
    main()
