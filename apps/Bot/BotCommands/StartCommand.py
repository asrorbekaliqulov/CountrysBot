from telegram.ext import ContextTypes, ConversationHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from ..utils import save_user_to_db
from ..models.TelegramBot import TelegramUser
from ..decorators import typing_action, mandatory_channel_required
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove


async def get_user_keyboard():
    """Bot uchun inline keyboardni dinamik yaratish."""
    # Asinxron holda guide ma'lumotini olish
    # Asosiy keyboard tugmalari
    users_keyboards = [
        [
            InlineKeyboardButton(text="ℹ️ Qo'llanma", callback_data='getGuide'),
            InlineKeyboardButton(text="📞 Murojaat", callback_data="appeal")
        ]
    ]

    return InlineKeyboardMarkup(users_keyboards)




@typing_action
@mandatory_channel_required
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Botni ishga tushirish uchun komanda.
    """
    remove = ReplyKeyboardRemove()

    data = update.effective_user
    if update.callback_query:
        await update.callback_query.answer("Asosiy menyu")
        await update.callback_query.delete_message()
    reply_markup = await get_user_keyboard()
    is_save = await save_user_to_db(data)
    admin_id = await TelegramUser.get_admin_ids()
    if update.effective_user.id in admin_id:
        await context.bot.send_message(chat_id=update.effective_user.id, text="<b>Main Menu 🖥\n<tg-spoiler>/admin_panel</tg-spoiler></b>", reply_markup=remove, parse_mode="html")

    await context.bot.send_message(chat_id=update.effective_user.id, text=f"<b>Hello 👋</b>", parse_mode="html", reply_markup=reply_markup) 
    return ConversationHandler.END


    