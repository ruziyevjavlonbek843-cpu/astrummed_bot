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

# =========================
# SOZLAMALAR
# =========================

CHANNEL = "@AstrumMED"
CHANNEL_URL = "https://t.me/AstrumMED"

YOUTUBE_URL = "https://youtube.com/@astrummed_1"

ADMIN_ID = 1955686748

# =========================
# LOGGING
# =========================

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
                    first_name TEXT,
                    username TEXT,
                    referred_by BIGINT,
                    referral_count INTEGER DEFAULT 0,
                    referral_counted BOOLEAN DEFAULT FALSE,
                    telegram_verified BOOLEAN DEFAULT FALSE,
                    discount_received BOOLEAN DEFAULT FALSE
                )
            """)

            # Eski jadval bo‘lsa, yangi ustunlarni qo‘shish
            cur.execute("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS first_name TEXT
            """)

            cur.execute("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS username TEXT
            """)

            cur.execute("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS discount_received BOOLEAN DEFAULT FALSE
            """)

        conn.commit()

    logger.info("Database initialized")


# =========================
# FOYDALANUVCHI QO‘SHISH
# =========================

def add_user(
    user_id,
    first_name,
    username,
    referred_by=None
):

    with db() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO users (
                    user_id,
                    first_name,
                    username,
                    referred_by
                )
                VALUES (%s, %s, %s, %s)

                ON CONFLICT (user_id)
                DO UPDATE SET
                    first_name = EXCLUDED.first_name,
                    username = EXCLUDED.username
                """,
                (
                    user_id,
                    first_name,
                    username,
                    referred_by,
                ),
            )

        conn.commit()


# =========================
# USER OLISH
# =========================

def get_user(user_id):

    with db() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    user_id,
                    first_name,
                    username,
                    referred_by,
                    referral_count,
                    referral_counted,
                    telegram_verified,
                    discount_received
                FROM users
                WHERE user_id = %s
                """,
                (user_id,),
            )

            return cur.fetchone()


# =========================
# TELEGRAM OBUNA
# =========================

async def is_subscribed(
    bot,
    user_id
):

    try:

        member = await bot.get_chat_member(
            chat_id=CHANNEL,
            user_id=user_id
        )

        return member.status in (
            "member",
            "administrator",
            "creator",
            "restricted"
        )

    except Exception as e:

        logger.error(
            "Subscription error: %s",
            e,
            exc_info=True
        )

        return False


# =========================
# REFERRAL HISOBLASH
# =========================

def count_referral(user_id):

    user = get_user(user_id)

    if not user:
        return None

    referred_by = user[3]
    already_counted = user[5]

    if not referred_by:
        return None

    if already_counted:
        return None

    if referred_by == user_id:
        return None

    with db() as conn:

        with conn.cursor() as cur:

            # Foydalanuvchining referral'i hisoblanganini belgilash
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

            # Taklif qilgan odamning yangi sonini olish
            cur.execute(
                """
                SELECT referral_count
                FROM users
                WHERE user_id = %s
                """,
                (referred_by,),
            )

            result = cur.fetchone()

        conn.commit()

    if result:
        return result[0]

    return None


# =========================
# START
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    user_id = user.id

    first_name = user.first_name or "Foydalanuvchi"

    username = user.username

    referred_by = None

    # /start 123456789
    if context.args:

        try:

            possible_referrer = int(
                context.args[0]
            )

            if possible_referrer != user_id:

                # Faqat haqiqiy mavjud user bo‘lsa
                referrer = get_user(
                    possible_referrer
                )

                if referrer:

                    referred_by = possible_referrer

        except ValueError:

            referred_by = None

    # Userni bazaga qo‘shamiz
    add_user(
        user_id=user_id,
        first_name=first_name,
        username=username,
        referred_by=referred_by
    )

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
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
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

            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return

    # Telegram obunasi tasdiqlandi
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

    # Referralni hisoblash
    new_referral_count = count_referral(
        user_id
    )

    # Hozirgi user ma'lumoti
    user = get_user(user_id)

    referral_count = user[4]

    # =========================
    # 5/5 BO‘LDI
    # =========================

    if referral_count >= 5:

        # Oldin tabriklangan bo‘lsa qayta bermaymiz
        discount_received = user[7]

        if not discount_received:

            with db() as conn:

                with conn.cursor() as cur:

                    cur.execute(
                        """
                        UPDATE users
                        SET discount_received = TRUE
                        WHERE user_id = %s
                        """,
                        (user_id,),
                    )

                conn.commit()

            await query.edit_message_text(

                "🎉 TABRIKLAYMIZ!\n\n"

                "✅ Siz barcha shartlarni bajardingiz!\n\n"

                "📚 Siz AstrumMED Terapiya kitoblariga "
                "maxsus chegirmaga ega bo‘ldingiz! 🎁"

            )

        else:

            await query.edit_message_text(

                "🎉 Siz barcha shartlarni "
                "allaqachon bajargansiz!\n\n"

                "📚 Siz AstrumMED Terapiya kitoblariga "
                "maxsus chegirmaga egasiz! 🎁"

            )

        return

    # =========================
    # REFERAL LINK
    # =========================

    bot_info = await context.bot.get_me()

    referral_link = (
        f"https://t.me/"
        f"{bot_info.username}"
        f"?start={user_id}"
    )

    share_url = (
        "https://t.me/share/url"
        f"?url={referral_link}"
        "&text=Terapiya kitoblariga maxsus chegirma olish uchun "
        "shu botga kiring:"
    )

    keyboard = [

        [
            InlineKeyboardButton(
                "👥 Do‘stlarni taklif qilish",
                url=share_url
            )
        ],

        [
            InlineKeyboardButton(
                "🔄 Natijani tekshirish",
                callback_data="check_subscription"
            )
        ],

    ]

    await query.edit_message_text(

        f"✅ Telegram kanaliga obunangiz tasdiqlandi!\n\n"

        f"👥 Sizning natijangiz: "
        f"{referral_count}/5\n\n"

        f"📤 Quyidagi tugma orqali "
        f"do‘stlaringizni taklif qiling.\n\n"

        f"⚠️ Do‘stingiz sizning havolangiz orqali "
        f"botga kirib, @AstrumMED kanaliga "
        f"obuna bo‘lgandan keyin hisoblanadi.\n\n"

        f"🔗 Shaxsiy havolangiz:\n"
        f"{referral_link}",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# =========================
# ADMIN STATISTIKA
# =========================

async def stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    # Faqat admin
    if user_id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ Sizda bu buyruqdan foydalanish "
            "huquqi yo‘q."
        )

        return

    with db() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    first_name,
                    username,
                    referral_count
                FROM users
                ORDER BY referral_count DESC,
                         first_name ASC
                """
            )

            users = cur.fetchall()

    if not users:

        await update.message.reply_text(
            "📊 Hozircha foydalanuvchilar yo‘q."
        )

        return

    text = "📊 REFERRAL STATISTIKA\n\n"

    for first_name, username, referral_count in users:

        name = first_name or "Noma'lum"

        if username:

            display_name = f"{name} (@{username})"

        else:

            display_name = name

        if referral_count >= 5:

            status = "✅"

        else:

            status = ""

        text += (
            f"{display_name} — "
            f"{referral_count}/5 "
            f"{status}\n"
        )

    await update.message.reply_text(
        text
    )


# =========================
# ERROR
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

    if not DATABASE_URL:

        raise RuntimeError(
            "DATABASE_URL topilmadi!"
        )

    init_db()

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # /start
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # /stats
    app.add_handler(
        CommandHandler(
            "stats",
            stats
        )
    )

    # Obunani tekshirish
    app.add_handler(
        CallbackQueryHandler(
            check_subscription,
            pattern="^check_subscription$"
        )
    )

    app.add_error_handler(
        error_handler
    )

    logger.info(
        "AstrumMED referral bot started"
    )

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
