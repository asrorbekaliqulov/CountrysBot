import os
from telegram.ext import ContextTypes, ConversationHandler
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo,
)
from asgiref.sync import sync_to_async

from ..utils import save_user_to_db
from ..models.TelegramBot import TelegramUser
from ..decorators import typing_action, mandatory_channel_required

# ─── WebApp URL ────────────────────────────────────────────────────────────────
WEB_APP_URL = os.getenv(
    "WEB_APP_URL",
    "https://manor-estate-secretariat-strategy.trycloudflare.com/"
)

# ─── TRANSLATIONS ──────────────────────────────────────────────────────────────
MESSAGES = {
    "welcome": {
        "uz": "👋 Xush kelibsiz!\n\n🏥 N-MedHomeLab — uy sharoitida professional tibbiy tahlil xizmati.\nKuryerimiz sizga maxsus konteynerni yetkazib beradi, tahlil natijasini esa bot orqali onlayn tarzda qulay olasiz.\n\nQuyidagilardan birini tanlang 👇",
        "ru": "👋 Добро пожаловать!\n\n🏥 N-MedHomeLab — профессиональные медицинские анализы на дому.\nКурьер доставит вам специальный контейнер, а результаты анализов вы сможете удобно получить онлайн прямо через бот.\n\nВыберите один из вариантов 👇",
        "en": "👋 Welcome!\n\n🏥 <b>N-MedHomeLab</b> — professional home medical analysis.\nA courier will deliver a special container to you, and you can conveniently receive your test results online via the bot.\n\nPlease choose one of the options below 👇"
    },
}

# ─── Tugma tarjimalari ─────────────────────────────────────────────────────────
BTN = {
    "uz": {
        "order":        "🧪 Tahlil buyurtma berish",
        "results":      "📊 Natijalarim",
        "order_status": "🚚 Buyurtma holati",
        "profile":      "👤 Mening profilim",
        "feedback":     "⭐️ Fikr & shikoyat",
        "contact":      "📞 Biz bilan bog'lanish",
    },
    "ru": {
        "order":        "🧪 Заказать анализ",
        "results":      "📊 Мои результаты",
        "order_status": "🚚 Статус заказа",
        "profile":      "👤 Мой профиль",
        "feedback":     "⭐️ Отзыв & жалоба",
        "contact":      "📞 Связаться с нами",
    },
    "en": {
        "order":        "🧪 Order analysis",
        "results":      "📊 My results",
        "order_status": "🚚 Order status",
        "profile":      "👤 My profile",
        "feedback":     "⭐️ Feedback & complaint",
        "contact":      "📞 Contact us",
    },
}

# ─── Admin panel uchun maxsus tugmalar ────────────────────────────────────────
ADMIN_BTN = {
    "uz": "🖥 Admin panel",
    "ru": "🖥 Панель админа",
    "en": "🖥 Admin panel",
}


def _clean_lang(lang: str) -> str:
    """Til kodini tozalaydi: 'uz-UZ' → 'uz'. Noto'g'ri bo'lsa 'uz' qaytaradi."""
    if not lang:
        return "uz"
    code = lang.lower().split("-")[0].split("_")[0]
    return code if code in ("uz", "ru", "en") else "uz"


async def get_main_menu_keyboard(
    user_lang: str = "uz",
    webapp_url: str = f"{WEB_APP_URL}api/webapp/wizard/",
    is_admin: bool = False,
    user_id: int = None,
) -> InlineKeyboardMarkup:
    """
    Foydalanuvchi tiliga qarab asosiy menyu klaviaturasini qaytaradi.

    Tugmalar tartibi (eski bot bilan bir xil):
      [ 🧪 Buyurtma berish  (WebApp) ]
      [ 📊 Natijalar  |  🚚 Buyurtma holati ]
      [ 👤 Profil     |  ⭐️ Fikr & shikoyat ]
      [ 📞 Bog'lanish ]
      [ 🖥 Admin panel ]  ← faqat adminlar uchun
    """
    lang = _clean_lang(user_lang)
    t = BTN[lang]

    # WebApp URL-ga til parametrini qo'shamiz
    connector = "&" if "?" in webapp_url else "?"
    full_url = f"{webapp_url}{connector}lang={lang}"
    if user_id:
        full_url += f"&tg_id={user_id}"

    keyboard = [
        # 1-qator: WebApp tugmasi (katta, butun qator)
        [
            InlineKeyboardButton(
                text=t["order"],
                web_app=WebAppInfo(url=full_url),
            )
        ],
        # 2-qator
        [
            InlineKeyboardButton(text=t["results"],      callback_data="my_results"),
            InlineKeyboardButton(text=t["order_status"], callback_data="order_status"),
        ],
        # 3-qator
        [
            InlineKeyboardButton(text=t["profile"],  callback_data="my_profile"),
            InlineKeyboardButton(text=t["feedback"], callback_data="feedback"),
        ],
        # 4-qator
        [
            InlineKeyboardButton(text=t["contact"], callback_data="appeal"),
        ],
    ]

    # Admin uchun qo'shimcha tugma
    if is_admin:
        keyboard.append([
            InlineKeyboardButton(
                text=ADMIN_BTN.get(lang, ADMIN_BTN["uz"]),
                callback_data="admin_menu",
            )
        ])

    return InlineKeyboardMarkup(keyboard)


@typing_action
@mandatory_channel_required
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start komandasi yoki menyu tugmasidan chaqirilganda ishlaydi.

    Nima qiladi:
      1. Callback orqali chaqirilgan bo'lsa eski xabarni o'chiradi
      2. Foydalanuvchini bazaga saqlaydi (save_user_to_db)
      3. Admin bo'lsa maxsus xabar yuboradi
      4. Asosiy menyuni foydalanuvchi tili bilan ko'rsatadi
    """
    remove_markup = ReplyKeyboardRemove()
    tg_user = update.effective_user

    # ── 1. Callback orqali kelgan bo'lsa (masalan «🔙 Orqaga» tugmasi) ──────────
    if update.callback_query:
        try:
            await update.callback_query.answer("Asosiy menyu")
            await update.callback_query.delete_message()
        except Exception:
            pass

    # ── 2. Foydalanuvchini bazaga yozish ─────────────────────────────────────────
    await save_user_to_db(tg_user)

    # ── 3. Django modelidan foydalanuvchi ma'lumotlarini olish ───────────────────
    try:
        user: TelegramUser = await sync_to_async(
            TelegramUser.objects.get
        )(user_id=tg_user.id)
        user_lang = user.lang          # "uz" | "ru" | "en"
        user_role = user.role          # "user" | "courier" | "doctor" | "admin"
        is_admin  = user.is_admin
    except TelegramUser.DoesNotExist:
        # Yangi foydalanuvchi — hozir save_user_to_db yozishi kerak edi,
        # lekin har ehtimolga qarshi default qiymatlar
        user_lang = "uz"
        user_role = "user"
        is_admin  = False

    lang = _clean_lang(user_lang)
    
    # ── 4. Admin uchun maxsus tizim xabari (eski bot bilan bir xil) ──────────────
    if is_admin:
        await context.bot.send_message(
            chat_id=tg_user.id,
            text="<b>Main Menu 🖥\n<tg-spoiler>/admin_panel</tg-spoiler></b>",
            reply_markup=remove_markup,
            parse_mode="html",
        )
    user_id = user.user_id if user else None
    # ── 5. Rol bo'yicha yo'naltirish ─────────────────────────────────────────────
    #  Kuryer va shifokorlar uchun mos panel (callback_data orqali ochiladi)
    if user_role == "courier":
        webapp_url = f"{str(WEB_APP_URL)}api/courier/?lang={lang}",
        print(f"Courier {tg_user.id} uchun panel URL: {webapp_url}")
        # WebApp URL-ga til parametrini qo'shamiz
        connector = "&" if "?" in webapp_url else "?"
        full_url = f"{webapp_url}{connector}lang={lang}"
        if user_id:
            full_url += f"&tg_id={user_id}"

        kb = InlineKeyboardMarkup([ [
            InlineKeyboardButton(
                "🚗 Kuryer paneli" if lang == "uz" else
                "🚗 Панель курьера" if lang == "ru" else
                "🚗 Courier panel",
                web_app=WebAppInfo(url=str(f"https://methods-slight-thumbnails-nationally.trycloudflare.com/api/courier/?lang=uz&tg_id={user_id}")),
            )
        ]])
        await context.bot.send_message(
            chat_id=tg_user.id,
            text=(
                "🚗 <b>Kuryer paneli</b>" if lang == "uz" else
                "🚗 <b>Панель курьера</b>" if lang == "ru" else
                "🚗 <b>Courier panel</b>"
            ),
            parse_mode="html",
            reply_markup=kb,
        )
        return ConversationHandler.END

    if user_role == "doctor":
        #     # WebApp URL-ga til parametrini qo'shamiz
        # connector = "&" if "?" in webapp_url else "?"
        # full_url = f"{webapp_url}{connector}lang={lang}"
        # if user_id:
        #     full_url += f"&tg_id={user_id}"

        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "👨‍⚕️ Shifokor paneli" if lang == "uz" else
                "👨‍⚕️ Панель врача" if lang == "ru" else
                "👨‍⚕️ Doctor panel",
                web_app=WebAppInfo(url=str(f"https://methods-slight-thumbnails-nationally.trycloudflare.com/api/doctor/panel/?lang=uz&tg_id={user_id}")),
            )
        ]])
        await context.bot.send_message(
            chat_id=tg_user.id,
            text=(
                "👨‍⚕️ <b>Shifokor paneli</b>" if lang == "uz" else
                "👨‍⚕️ <b>Панель врача</b>" if lang == "ru" else
                "👨‍⚕️ <b>Doctor panel</b>"
            ),
            parse_mode="html",
            reply_markup=kb,
        )
        return ConversationHandler.END

    # ── 6. Oddiy foydalanuvchi — asosiy menyu ────────────────────────────────────
    reply_markup = await get_main_menu_keyboard(
        user_lang=lang,
        webapp_url=f"{WEB_APP_URL}api/webapp/wizard/",
        is_admin=is_admin,
        user_id=tg_user.id,
    )

    welcome_text = MESSAGES["welcome"].get(lang, MESSAGES["welcome"]["uz"])

    await context.bot.send_message(
        chat_id=tg_user.id,
        text=welcome_text,
        parse_mode="html",
        reply_markup=reply_markup,
    )

    # ── 7. ConversationHandler holatini tozalash ──────────────────────────────────
    return ConversationHandler.END


# ─── Menyu tugmalari uchun callback handler ───────────────────────────────────
async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Asosiy menyu tugmalarining callback_data larini ushlaydi.
    apps/Bot/handlers/callbacks.py da CallbackQueryHandler ga ulang:

        CallbackQueryHandler(main_menu_callback, pattern="^(my_results|order_status|my_profile|feedback|contact_us|admin_panel)$")
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    tg_user = update.effective_user

    try:
        user: TelegramUser = await sync_to_async(
            TelegramUser.objects.get
        )(user_id=tg_user.id)
        lang = _clean_lang(user.lang)
    except TelegramUser.DoesNotExist:
        lang = "uz"

    # Har bir tugma uchun mos handler chaqiriladi.
    # Siz o'z handler fayllaringizdan import qilib, shu yerda chaqiring.
    if data == "my_results":
        # from ..handlers.results import send_results
        # await send_results(update, context)
        await query.message.reply_text("📊 Natijalar bo'limi tez orada...")

    elif data == "order_status":
        # from ..handlers.orders import send_order_status
        # await send_order_status(update, context)
        await query.message.reply_text("🚚 Buyurtma holati bo'limi tez orada...")

    elif data == "my_profile":
        # from ..handlers.profile import send_profile
        # await send_profile(update, context)
        await query.message.reply_text("👤 Profil bo'limi tez orada...")

    elif data == "feedback":
        # from ..handlers.feedback import send_feedback
        # await send_feedback(update, context)
        await query.message.reply_text("⭐️ Fikr & shikoyat bo'limi tez orada...")

    elif data == "contact_us":
        contacts = {
            "uz": "📞 Biz bilan bog'lanish:\n\n🌐 Sayt: https://1wash.uz\n📱 Telegram: @support",
            "ru": "📞 Связаться с нами:\n\n🌐 Сайт: https://1wash.uz\n📱 Telegram: @support",
            "en": "📞 Contact us:\n\n🌐 Website: https://1wash.uz\n📱 Telegram: @support",
        }
        await query.message.reply_text(contacts.get(lang, contacts["uz"]))

    elif data == "admin_panel":
        # from ..handlers.admin import send_admin_panel
        # await send_admin_panel(update, context)
        await query.message.reply_text("🖥 Admin panel tez orada...")

    elif data == "back_to_menu":
        # Istalgan joydan «🔙 Orqaga» tugmasi uchun
        await start(update, context)