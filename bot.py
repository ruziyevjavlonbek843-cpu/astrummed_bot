import os
import json
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# =====================================================
# SOZLAMALAR
# =====================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

CHANNEL = "@AstrumMED"
CHANNEL_URL = "https://t.me/AstrumMED"

YOUTUBE_URL = "https://youtube.com/@astrummed_1"

ADMIN_ID = 1955686748

DATA_FILE = "users.json"

# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =====================================================
# DATABASE O'RNIGA JSON
# =====================================================

def load_users():

    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:

        return {}


def save_users(users):

    with open(
        DATA_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            users,
            file,
            ensure_ascii=False,
            indent=2
        )


def get_user(users, user_id):

    return users.get(str(user_id))


# =====================================================
# FOYDALANUVCHI YARATISH
# =====================================================

def create_user(
    users,
    user_id,
    first_name,
    username,
    referred_by=None
):

    user_key = str(user_id)

    if user_key not in users:

        users[user_key] = {
            "user_id": user_id,
            "first_name": first_name,
            "username": username,
            "referred_by": referred_by,
            "referral_count": 0,
            "referral_counted": False,
            "telegram_verified": False,
            "discount_received": False,
        }

    else:

        # Ism yoki username o'zgargan bo'lishi mumkin
        users[user_key]["first_name"] = first_name
        users[user_key]["username"] = username

    save_users(users)


# =====================================================
# START
# =====================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    user_id = user.id

    first_name = user.first_name or "Foydalanuvchi"

    username = user.username

    users = load_users()

    referred_by = None

    # -------------------------------------------------
    # /start 123456
    # -------------------------------------------------

    if context.args:

        try:

            possible_referrer = int(
                context.args[0]
            )

            # O'zini o'zi taklif qilmasin
            if possible_referrer != user_id:

                # Taklif qilgan odam haqiqatan botda
                # ro'yxatdan o'tgan bo'lishi kerak
                if str(possible_referrer) in users:

                    referred_by = possible_referrer

        except ValueError:

            referred_by = None

    # -------------------------------------------------
    # User yaratish
    # -------------------------------------------------

    create_user(
        users,
        user_id,
        first_name,
        username,
        referred_by
    )

    # -------------------------------------------------
    # Agar user oldindan mavjud bo'lsa,
    # referred_by ni qayta o'zgartirmaymiz
    # -------------------------------------------------

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
                callback_data="check"
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


# =====================================================
# TELEGRAM OBUNASINI TEKSHIRISH
# =====================================================

async def check_subscription(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    users = load_users()

    user_key = str(user_id)

    # User mavjudligini tekshirish
    if user_key not in users:

        users[user_key] = {
            "user_id": user_id,
            "first_name": query.from_user.first_name
                or "Foydalanuvchi",
            "username": query.from_user.username,
            "referred_by": None,
            "referral_count": 0,
            "referral_counted": False,
            "telegram_verified": False,
            "discount_received": False,
        }

        save_users(users)

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
            "Subscription error: %s",
            e,
            exc_info=True
        )

        await query.edit_message_text(
            "⚠️ Obunani tekshirishda xatolik yuz berdi.\n\n"
            "Iltimos, birozdan keyin qayta urinib ko‘ring."
        )

        return

    # =================================================
    # OBUNA YO'Q
    # =================================================

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
                    callback_data="check"
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

    # =================================================
    # OBUNA BOR
    # =================================================

    users[user_key]["telegram_verified"] = True

    # =================================================
    # REFERRALNI HISOBLASH
    # =================================================

    referred_by = users[user_key].get(
        "referred_by"
    )

    already_counted = users[user_key].get(
        "referral_counted",
        False
    )

    if (
        referred_by
        and not already_counted
        and str(referred_by) in users
        and referred_by != user_id
    ):

        referrer_key = str(referred_by)

        users[referrer_key]["referral_count"] += 1

        users[user_key]["referral_counted"] = True

        logger.info(
            "Referral counted: %s -> %s",
            referred_by,
            user_id
        )

    save_users(users)

    # =================================================
    # TAKLIF QILGAN ODAMNING HOLATI
    # =================================================

    current_user = users[user_key]

    referral_count = current_user.get(
        "referral_count",
        0
    )

    # =================================================
    # 5/5 BO'LDI
    # =================================================

    if referral_count >= 5:

        if not current_user.get(
            "discount_received",
            False
        ):

            current_user[
                "discount_received"
            ] = True

            save_users(users)

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

    # =================================================
    # SHAXSIY REFERAL LINK
    # =================================================

    bot_info = await context.bot.get_me()

    referral_link = (
        f"https://t.me/"
        f"{bot_info.username}"
        f"?start={user_id}"
    )

    share_url = (
        "https://t.me/share/url"
        f"?url={referral_link}"
        "&text=Terapiya kitoblariga maxsus chegirma "
        "olish uchun shu botga kiring:"
    )

    keyboard = [

        [
            InlineKeyboardButton(
                "📤 5 ta do‘stga yuborish",
                url=share_url
            )
        ],

        [
            InlineKeyboardButton(
                "🔄 Natijani tekshirish",
                callback_data="check"
            )
        ],

    ]

    await query.edit_message_text(

        f"✅ Telegram kanaliga obunangiz tasdiqlandi!\n\n"

        f"👥 Sizning natijangiz: "
        f"{referral_count}/5\n\n"

        f"📤 Quyidagi tugma orqali "
        f"shaxsiy havolangizni do‘stlaringizga yuboring.\n\n"

        f"⚠️ Do‘stingiz sizning havolangiz orqali "
        f"botga kirib, @AstrumMED kanaliga "
        f"obuna bo‘lgandan keyin hisoblanadi.\n\n"

        f"🔗 Sizning shaxsiy havolangiz:\n"
        f"{referral_link}",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# =====================================================
# ADMIN STATISTIKA
# =====================================================

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

    users = load_users()

    if not users:

        await update.message.reply_text(
            "📊 Hozircha foydalanuvchilar yo‘q."
        )

        return

    # Eng ko'p referral olib kelganlar yuqorida
    sorted_users = sorted(
        users.values(),
        key=lambda x: (
            x.get("referral_count", 0),
            x.get("first_name", "")
        ),
        reverse=True
    )

    text = "📊 REFERRAL STATISTIKA\n\n"

    for user in sorted_users:

        name = user.get(
            "first_name",
            "Noma'lum"
        )

        count = user.get(
            "referral_count",
            0
        )

        if count >= 5:

            status = "✅"

        else:

            status = ""

        text += (
            f"{name} — "
            f"{count}/5 "
            f"{status}\n"
        )

    await update.message.reply_text(
        text
    )


# =====================================================
# ADMIN: JAMI STATISTIKA
# =====================================================

async def total_stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    if user_id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ Ruxsat yo‘q."
        )

        return

    users = load_users()

    total_users = len(users)

    completed = sum(
        1
        for user in users.values()
        if user.get("referral_count", 0) >= 5
    )

    text = (
        "📊 ASTRUMMED BOT\n\n"

        f"👥 Jami foydalanuvchilar: "
        f"{total_users}\n\n"

        f"🎯 5/5 bajarganlar: "
        f"{completed}\n\n"

        f"⏳ Jarayondagilar: "
        f"{total_users - completed}"
    )

    await update.message.reply_text(
        text
    )


# =====================================================
# ERROR
# =====================================================

async def error_handler(
    update,
    context
):

    logger.error(
        "BOT ERROR: %s",
        context.error,
        exc_info=True
    )


# =====================================================
# MAIN
# =====================================================

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

    # /total
    app.add_handler(
        CommandHandler(
            "total",
            total_stats
        )
    )

    # Obuna tekshirish
    app.add_handler(
        CallbackQueryHandler(
            check_subscription,
            pattern="^check$"
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


# =====================================================
# START BOT
# =====================================================

if __name__ == "__main__":

    main()
