import os
from telegram.ext import ContextTypes, ConversationHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
from ..utils import save_user_to_db
from ..models.TelegramBot import TelegramUser
from ..decorators import typing_action, mandatory_channel_required
from django.utils.translation import gettext_lazy as _
from apps.Bot.languages import MESSAGES
from asgiref.sync import sync_to_async
# WebApp URL manzilini sozlamalardan yoki (.env) muhitdan olish
# Agar loyihangizda muhit o'zgaruvchisi bo'lsa, uni quyidagicha oling:
WEB_APP_URL = os.getenv(
    "WEB_APP_URL", 
    "https://cinema-counted-shorter-evaluate.trycloudflare.com/api/webapp/wizard/"
)

async def get_user_keyboard(user_lang: str = "uz"):
    """
    Foydalanuvchi tiliga qarab tugmalarni va WebApp URL manzilini 
    dinamik tarjima qilib qaytaruvchi klaviatura.
    """
    # 1. Til kodini har doim tozalab olamiz (masalan: "uz-uz" bo'lsa "uz" qoladi)
    clean_lang = user_lang.lower().split('-')[0] if user_lang else "uz"
    if clean_lang not in ["uz", "ru", "en"]:
        clean_lang = "uz"

    # 2. WebApp URL manziliga foydalanuvchi tilini parametr sifatida qo'shamiz
    # Shunda frontend (wizard.html) ham avtomatik shu tilda ochiladi
    connector = "&" if "?" in WEB_APP_URL else "?"
    web_app_url_with_lang = f"{WEB_APP_URL}{connector}lang={clean_lang}"

    # 3. Har bir til uchun tugma matnlari lug'ati
    translations = {
        "uz": {
            "order": "🚀 Buyurtma berish (Xizmatlar)",
            "guide": "ℹ️ Qo'llanma",
            "appeal": "📞 Murojaat"
        },
        "ru": {
            "order": "🚀 Сделать заказ (Услуги)",
            "guide": "ℹ️ Инструкция",
            "appeal": "📞 Обратная связь"
        },
        "en": {
            "order": "🚀 Place an Order (Services)",
            "guide": "ℹ️ Guide",
            "appeal": "📞 Contact Support"
        }
    }

    # Joriy tilga mos matnlarni ajratib olamiz
    lang_txt = translations[clean_lang]

    # 4. Klaviaturani qurish
    users_keyboards = [
        [
            InlineKeyboardButton(
                text=lang_txt["order"], 
                web_app=WebAppInfo(url=web_app_url_with_lang)
            )
        ],
        [
            InlineKeyboardButton(text=lang_txt["guide"], callback_data='getGuide'),
            InlineKeyboardButton(text=lang_txt["appeal"], callback_data="appeal")
        ]
    ]
    
    return InlineKeyboardMarkup(users_keyboards)

@typing_action
@mandatory_channel_required
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Botni ishga tushirish uchun start komandasi.
    Eski holatlarni tozalaydi, foydalanuvchini saqlaydi va WebApp menyusini chiqaradi.
    """
    remove_reply_markup = ReplyKeyboardRemove()
    user_data = update.effective_user
    user = await sync_to_async(TelegramUser.objects.get)(user_id=user_data.id)
    user_lang = user.lang  # "uz", "ru" yoki "en" qaytadi
    # 1. Agar start callback_query (masalan, menyuga qaytish tugmasi) orqali chaqirilgan bo'lsa
    if update.callback_query:
        try:
            await update.callback_query.answer("Asosiy menyu")
            await update.callback_query.delete_message()
        except Exception:
            pass

    # 2. Foydalanuvchini bazaga yozish (asinxron)
    await save_user_to_db(user_data)

    # 3. Adminlik huquqini tekshirish va eski reply_keyboard'larni tozalash
    admin_ids = await TelegramUser.get_admin_ids()
    if user_data.id in admin_ids:
        await context.bot.send_message(
            chat_id=user_data.id, 
            text="<b>Main Menu 🖥\n<tg-spoiler>/admin_panel</tg-spoiler></b>", 
            reply_markup=remove_reply_markup, 
            parse_mode="html"
        )

    # 4. Dinamik klaviaturani yaratish (Ichida WebApp tugmasi bilan)
    reply_markup = await get_user_keyboard(user_lang=user_lang)

    # 5. Salomlashish matni va WebApp menyusini yuborish
    welcome_text = MESSAGES["welcome"].get(user_lang, MESSAGES["welcome"]["uz"])

    await context.bot.send_message(
        chat_id=user_data.id, 
        text=welcome_text, 
        parse_mode="html", 
        reply_markup=reply_markup
    ) 
    
    # ConversationHandler jarayonlarini tozalab yopish
    return ConversationHandler.END