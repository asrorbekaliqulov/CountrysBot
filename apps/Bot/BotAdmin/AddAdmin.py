from telegram import Update, ReplyKeyboardMarkup, KeyboardButton,KeyboardButtonRequestUsers, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from apps.Bot.models.TelegramBot import TelegramUser  # Django modelingizni import qiling
from ..decorators import admin_required
from ..translations import t

from warnings import filterwarnings
from telegram.warnings import PTBUserWarning

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)


# ConversationHandler bosqichlari
ASK_USER_ID, CONFIRM = range(2)

@admin_required
async def start_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Admin qo'shishni boshlaydi.
    """
    tg_user = update.effective_user
    
    # Til aniqlash
    try:
        from asgiref.sync import sync_to_async
        user = await sync_to_async(TelegramUser.objects.get)(user_id=tg_user.id)
        lang = user.lang or 'uz'
    except:
        lang = 'uz'
    
    await update.callback_query.delete_message()
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text=t("admin_add_select_user", lang),
        reply_markup=ReplyKeyboardMarkup([
            [
                KeyboardButton(
                    text=t("admin_add_select_btn", lang), 
                    request_users=KeyboardButtonRequestUsers(
                        request_id=3,
                        user_is_bot=False
                    ))
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True)
    )
    return ASK_USER_ID

@admin_required
async def ask_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Foydalanuvchi ID ni qabul qiladi va tasdiqlashni so'raydi.
    """
    user = update.message.users_shared.to_dict()
    user_id = user['users'][0]['user_id']

    if not update.message.users_shared:
        await update.message.reply_text("Iltimos, pastdagi tugmani bosgan holda foydalanuvchini tanlang.")
        return ASK_USER_ID

    context.user_data['user_id'] = int(user_id)

    await update.message.reply_text(
        f"Foydalanuvchi ID: {user_id}. Ushbu foydalanuvchini admin qilishni tasdiqlaysizmi? (Ha/Yo'q)",
        reply_markup=ReplyKeyboardMarkup([["Ha", "Yo'q"]], one_time_keyboard=True, resize_keyboard=True)
    )
    return CONFIRM

@admin_required
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Tasdiqlash jarayoni.
    """
    choice = update.message.text.lower()
    user_id = context.user_data.get('user_id')
    tg_user = update.effective_user
    
    # Til aniqlash
    try:
        from asgiref.sync import sync_to_async
        admin_user = await sync_to_async(TelegramUser.objects.get)(user_id=tg_user.id)
        lang = admin_user.lang or 'uz'
    except:
        lang = 'uz'

    if choice in ["ha", "yes", "да"]:
        user = await TelegramUser.make_admin(user_id=user_id)
        if user:
            await update.message.reply_text(
                t("admin_add_success", lang, user=user), 
                reply_markup=ReplyKeyboardRemove()
            )
            await context.bot.send_message(
                chat_id=user_id, 
                text=t("admin_add_success_notify", lang)
            )
        else:
            await update.message.reply_text(t("admin_add_not_found", lang))
    elif choice in ["yo'q", "no", "нет"]:
        await update.message.reply_text(t("admin_add_cancelled", lang))
    else:
        await update.message.reply_text("Iltimos, faqat 'Ha' yoki 'Yo'q' deb javob bering.")
        return CONFIRM

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Muloqotni bekor qiladi.
    """
    await update.message.reply_text("Admin qo'shish bekor qilindi.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ConversationHandler ni sozlash
add_admin_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_add_admin, pattern='^add_admin$')],
    states={
        ASK_USER_ID: [MessageHandler(filters.USER & ~filters.COMMAND, ask_user_id)],
        CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)


async def the_first_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        admins_count = await TelegramUser.count_admin_users()
        
        # Til aniqlash
        try:
            from asgiref.sync import sync_to_async
            user = await sync_to_async(TelegramUser.objects.get)(user_id=user_id)
            lang = user.lang or 'uz'
        except:
            lang = 'uz'
        
        if admins_count < 1:
            user = await TelegramUser.make_admin(user_id=user_id)
            await update.message.reply_text(t("admin_first_success", lang))
        else:
            await update.message.reply_text(t("admin_first_exists", lang))
    except:
        await update.message.reply_text(t("error_generic", "uz"))