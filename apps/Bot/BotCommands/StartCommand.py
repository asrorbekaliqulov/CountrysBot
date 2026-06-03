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
    "https://n-medhomelab.uz/",
)

# ─── TRANSLATIONS ──────────────────────────────────────────────────────────────
MESSAGES = {
    "welcome": {
        "uz": """🖤 Assalomu alaykum,
NMED HOME LAB ga xush kelibsiz. Siz premium xizmatimizdan foydalanayotganingizdan mamnunmiz.

🚚 Maxsus konteyner xodimlarimiz tomonidan uyingizga yetkaziladi
🧪 3 kun davomida namunadan kerakli qism konteynerga joylashtiriladi
📦 Tayyor namuna laboratoriyamizga yuboriladi
🔬 Tekshiruv professional standart asosida amalga oshiriladi
📊 Natijalar online tarzda yuboriladi

✨ Laboratoriya endi uyingizda.
""",
        "ru": """🖤 Добро пожаловать в NMED HOME LAB. Мы рады, что вы пользуетесь нашим премиум-сервисом.

    🚚 Специальный контейнер доставят вам домой наши сотрудники.
    🧪 На 3 дня необходимая часть образца помещается в контейнер
    📦 Готовый образец отправляется в нашу лабораторию.
    🔬 Проверка проводится на основании профессиональных стандартов
    📊 Результаты будут отправлены онлайн

    ✨Лаборатория теперь дома.
    """,
        "en": """🖤 Welcome to NMED HOME LAB. We are happy that you are using our premium service.

    🚚 Our employees will deliver the special container to your home.
    🧪 The necessary part of the sample is placed in the container in 3 days
    📦 The ready sample is sent to our laboratory.
    🔬 The check is carried out according to professional standards
    📊 The results are sent online

    ✨ The laboratory is now at home.
    """
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


# ─── Til tanlash ───────────────────────────────────────────────────────────────
LANG_PICK = {
    "prompt": (
        "🌐 <b>NMED HOME LAB</b>\n\n"
        "Tilni tanlang / Выберите язык / Choose language:"
    ),
    "confirmed": {
        "uz": "✅ Til o'zbek tiliga o'rnatildi!",
        "ru": "✅ Язык установлен: русский!",
        "en": "✅ Language set to English!",
    },
    "buttons": {
        "uz": "🇺🇿 O'zbek",
        "ru": "🇷🇺 Русский",
        "en": "🇬🇧 English",
    },
}


def get_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(LANG_PICK["buttons"]["uz"], callback_data="set_lang:uz")],
        [InlineKeyboardButton(LANG_PICK["buttons"]["ru"], callback_data="set_lang:ru")],
        [InlineKeyboardButton(LANG_PICK["buttons"]["en"], callback_data="set_lang:en")],
    ])


async def show_language_picker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Birinchi marta /start bosgan foydalanuvchiga til tanlash."""
    tg_user = update.effective_user
    chat_id = tg_user.id
    if update.callback_query:
        try:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                LANG_PICK["prompt"],
                parse_mode="html",
                reply_markup=get_language_keyboard(),
            )
            return
        except Exception:
            pass
    await context.bot.send_message(
        chat_id=chat_id,
        text=LANG_PICK["prompt"],
        parse_mode="html",
        reply_markup=get_language_keyboard(),
    )


async def set_lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Til tanlash callback — bazaga saqlaydi va asosiy menyuni ko'rsatadi."""
    query = update.callback_query
    await query.answer()
    lang = query.data.split(":")[-1] if query.data else "uz"
    lang = _clean_lang(lang)
    tg_user = update.effective_user

    @sync_to_async
    def save_lang():
        TelegramUser.objects.filter(user_id=tg_user.id).update(lang=lang, lang_chosen=True)

    await save_lang()

    try:
        await query.edit_message_text(
            LANG_PICK["confirmed"].get(lang, LANG_PICK["confirmed"]["uz"]),
            parse_mode="html",
        )
    except Exception:
        pass

    await start(update, context)
    return ConversationHandler.END


def _clean_lang(lang: str) -> str:
    """Til kodini tozalaydi: 'uz-UZ' → 'uz'. Noto'g'ri bo'lsa 'uz' qaytaradi."""
    if not lang:
        return "uz"
    code = lang.lower().split("-")[0].split("_")[0]
    return code if code in ("uz", "ru", "en") else "uz"


def _match_tg_lang(language_code) -> str:
    """Telegram interfeys tilini ('uz-UZ', 'ru', 'en-US' ...) qo'llab-quvvatlanadigan
    tilga moslaydi. Mos kelmasa None qaytaradi — bu holda mavjud til saqlanadi."""
    if not language_code:
        return None
    code = language_code.lower().split("-")[0].split("_")[0]
    return code if code in ("uz", "ru", "en") else None


def _webapp_page_url(page: str, lang: str, user_id: int = None) -> str:
    base = f"{WEB_APP_URL.rstrip('/')}/api/webapp/"
    connector = "?"
    full = f"{base}{connector}page={page}&lang={lang}"
    if user_id:
        full += f"&tg_id={user_id}"
    return full


async def get_main_menu_keyboard(
    user_lang: str = "uz",
    webapp_url: str = None,
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

    order_url = webapp_url or _webapp_page_url("home", lang, user_id)

    keyboard = [
        [
            InlineKeyboardButton(
                text=t["order"],
                web_app=WebAppInfo(url=order_url),
            )
        ],
        [
            InlineKeyboardButton(
                text=t["results"],
                web_app=WebAppInfo(url=_webapp_page_url("results", lang, user_id)),
            ),
        ],
        [
            InlineKeyboardButton(
                text=t["order_status"],
                web_app=WebAppInfo(url=_webapp_page_url("orders", lang, user_id)),
            ),
        ],
        [
            InlineKeyboardButton(
                text=t["profile"],
                web_app=WebAppInfo(url=_webapp_page_url("profile", lang, user_id)),
            ),
        ],
        [
            InlineKeyboardButton(
                text=t["feedback"],
                web_app=WebAppInfo(url=_webapp_page_url("feedback", lang, user_id)),
            ),
        ],
        [
            InlineKeyboardButton(
                text=t["contact"],
                web_app=WebAppInfo(url=_webapp_page_url("support", lang, user_id)),
            ),
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
            data = update.callback_query.data or ""
            if not data.startswith("set_lang:"):
                await update.callback_query.answer("Asosiy menyu")
                await update.callback_query.delete_message()
        except Exception:
            pass

    # ── 2. Foydalanuvchini bazaga yozish ─────────────────────────────────────────
    await save_user_to_db(tg_user)

    # ── 3. Django modelidan foydalanuvchi ma'lumotlarini olish ───────────────────
    user = None
    lang_chosen = True
    try:
        user: TelegramUser = await sync_to_async(
            TelegramUser.objects.get
        )(user_id=tg_user.id)
        user_lang = user.lang          # "uz" | "ru" | "en"
        user_role = user.role          # "user" | "courier" | "doctor" | "admin"
        is_admin  = user.is_admin
        lang_chosen = user.lang_chosen
    except TelegramUser.DoesNotExist:
        user_lang = "uz"
        user_role = "user"
        is_admin  = False
        lang_chosen = False

    # ── 3b. Birinchi marta — til tanlash ─────────────────────────────────────────
    if not lang_chosen and user_role == "user" and not is_admin:
        await show_language_picker(update, context)
        return ConversationHandler.END

    # ── 3c. Keyingi /start — tilni Telegram interfeys tilidan avtomatik yangilash ──
    #   Update ichidagi language_code ('uz' | 'ru' | 'en') bo'yicha bot tilini sinxron
    #   qiladi. Mos kelmasa (masalan 'fr') mavjud til o'zgarmaydi.
    tg_lang = _match_tg_lang(tg_user.language_code)
    if tg_lang and tg_lang != _clean_lang(user_lang):
        user_lang = tg_lang

        @sync_to_async
        def sync_lang():
            TelegramUser.objects.filter(user_id=tg_user.id).update(lang=tg_lang)

        await sync_lang()

    lang = _clean_lang(user_lang)
    
    # ── 4. Admin uchun maxsus tizim xabari (eski bot bilan bir xil) ──────────────
    if is_admin:
        await context.bot.send_message(
            chat_id=tg_user.id,
            text="<b>Main Menu 🖥\n<tg-spoiler>/admin_panel</tg-spoiler></b>",
            reply_markup=remove_markup,
            parse_mode="html",
        )
    user_id = user.user_id if user else tg_user.id
    # ── 5. Rol bo'yicha yo'naltirish ─────────────────────────────────────────────
    if user_role == "courier":
        full_url = f"{WEB_APP_URL.rstrip('/')}/api/courier/?lang={lang}&tg_id={user_id}"

        kb = InlineKeyboardMarkup([ [
            InlineKeyboardButton(
                "🚗 Kuryer paneli" if lang == "uz" else
                "🚗 Панель курьера" if lang == "ru" else
                "🚗 Courier panel",
                web_app=WebAppInfo(url=full_url),
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
        full_url = f"{WEB_APP_URL.rstrip('/')}/api/doctor/panel/?lang={lang}&tg_id={user_id}"

        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "👨‍⚕️ Shifokor paneli" if lang == "uz" else
                "👨‍⚕️ Панель врача" if lang == "ru" else
                "👨‍⚕️ Doctor panel",
                web_app=WebAppInfo(url=full_url),
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
    if data in ("my_results", "order_status", "my_profile", "feedback"):
        page_map = {
            "my_results": "results",
            "order_status": "orders",
            "my_profile": "profile",
            "feedback": "feedback",
        }
        url = _webapp_page_url(page_map[data], lang, tg_user.id)
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("📱 WebAppni ochish", web_app=WebAppInfo(url=url))
        ]])
        OPEN_WEBAPP = {
            "uz": "Bo'limni WebAppda oching 👇",
            "ru": "Откройте раздел в WebApp 👇",
            "en": "Open the section in WebApp 👇",
        }
        await query.message.reply_text(OPEN_WEBAPP.get(lang, OPEN_WEBAPP["uz"]), reply_markup=kb)
        return

    elif data == "contact_us" or data == "appeal":
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