from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from ..models.TelegramBot import TelegramUser, Appeal
from ..decorators import mandatory_channel_required, admin_required, typing_action
from asgiref.sync import sync_to_async
from django.utils.html import strip_tags
from ..translations import t



@mandatory_channel_required
async def Message_to_Admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    
    # Til aniqlash
    try:
        user = await sync_to_async(TelegramUser.objects.get)(user_id=tg_user.id)
        lang = user.lang or 'uz'
    except:
        lang = 'uz'
    
    await update.callback_query.edit_message_text(
        text=t("support_send_message", lang),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(t("btn_cancel", lang), callback_data="cancel")]
        ])
    )
    return "Send_Message_to_Admin"
    

async def Send_Message_to_Admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    message_id = update.message.message_id
    admin_ids = await TelegramUser.get_admin_ids()
    if not admin_ids:
        admin_ids = [6194484795]  # Default admin ID if no admins are found
    user = await sync_to_async(TelegramUser.objects.get)(user_id=update.effective_user.id)
    lang = user.lang or 'uz'
    
    user_info = f"<b>User ID: <code>{user.user_id}</code>\nUsername: @{user.username}\nFull Name: {user.first_name}</b>"
    await sync_to_async(Appeal.objects.create)(user=user, message=message_text, message_id=message_id)
    message_text = f"{user_info}\n\n{message_text}"
    for admin_id in admin_ids:
        await context.bot.send_message(chat_id=admin_id, text=f"Yangi xabar:\n\n{message_text}", parse_mode="HTML")
    
    await update.message.reply_text(
        t("support_message_sent", lang), 
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(t("btn_back", lang), callback_data="Main_Menu")]
        ])
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(text="Amal bekor qilindi.", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Asosiy menyu", callback_data="Main_Menu")]
    ]))
    return ConversationHandler.END

appeal_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(Message_to_Admin, pattern='^appeal$')],
    states={
        "Send_Message_to_Admin": [
            MessageHandler(filters.TEXT & ~filters.COMMAND, Send_Message_to_Admin)
        ]
    },
    fallbacks=[CallbackQueryHandler(cancel, pattern='^cancel$')],
    allow_reentry=True
)



ITEMS_PER_PAGE = 10



def get_appeals(offset, limit):
    return list(
        Appeal.objects.filter(status=False)
        .select_related("user")  # ForeignKey optimallashtirildi
        .order_by("created_at")[offset:offset + limit]
    )
async def get_appeals_page(page):
    offset = (page - 1) * ITEMS_PER_PAGE
    appeals = await sync_to_async(get_appeals)(offset, ITEMS_PER_PAGE)
    total = await sync_to_async(lambda: Appeal.objects.filter(status=False).count())()
    return appeals, total

@admin_required
async def list_appeals(update: Update, _):
    query = update.callback_query
    await query.answer()

    page = int(query.data.split(":")[1]) if query and query.data.startswith("appeals_page:") else 1

    appeals, total = await get_appeals_page(page)
    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    if not appeals:
        await query.edit_message_text("Hozircha murojaatlar yo‘q.")
        await query.edit_message_reply_markup(
            InlineKeyboardMarkup([
                [InlineKeyboardButton("Barcha murojaatlar", callback_data="all_appeals")]
            ])
        )
        return

    text_lines = []
    for idx, appeal in enumerate(appeals, start=1 + (page - 1) * ITEMS_PER_PAGE):
        short_msg = strip_tags(appeal.message)[:50]
        status = "✅" if appeal.status else "❗"
        text_lines.append(f"{idx}. {appeal.user.first_name}: {status} {short_msg}")

    text = "\n".join(text_lines)

    # Inline tugmalar
    buttons = []
    for i in range(1, len(appeals) + 1):
        buttons.append(InlineKeyboardButton(str(i), callback_data=f"appeal_detail:{(page - 1) * ITEMS_PER_PAGE + i}"))

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⏮️ Oldingi", callback_data=f"appeals_page:{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Keyingi ⏭️", callback_data=f"appeals_page:{page + 1}"))

    keyboard = [buttons[i:i+5] for i in range(0, len(buttons), 5)]  # 5 ta tugma 1 qatorda
    if nav_buttons:
        keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("Asosiy menyu", callback_data="Main_Menu"), InlineKeyboardButton("Barcha murojaatlar", callback_data="all_appeals")])
    await query.edit_message_text(
        text=f"<b>Murojaatlar — sahifa {page}/{total_pages}</b>\n\n{text}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# models.py dagi ID bo'yicha murojaat olish
@sync_to_async
def get_appeal_by_index(index: int):
    try:
        appeal = list(
            Appeal.objects.all()
            .select_related("user")
            .order_by("created_at")
        )[index - 1]
        return appeal
    except IndexError:
        return None


async def show_appeal_detail(update: Update, _):
    query = update.callback_query
    await query.answer()

    try:
        index = int(query.data.split(":")[1])
    except (IndexError, ValueError):
        await query.edit_message_text("Noto‘g‘ri murojaat ID.")
        return

    appeal = await get_appeal_by_index(index)
    if not appeal:
        await query.edit_message_text("Murojaat topilmadi.")
        return

    user = appeal.user
    msg = (
        f"<b>Yangi xabar:</b>\n\n"
        f"<b>User ID:</b> <code>{user.user_id}</code>\n"
        f"<b>Username:</b> @{user.username or 'yo‘q'}\n"
        f"<b>Full Name:</b> {user.first_name}\n\n"
        f"{appeal.message}"
    )

    await query.edit_message_text(
        text=msg,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Bekor qilish", callback_data="cancel")]
        ])
    )
 

import re

def extract_user_id(text: str) -> int | None:
    match = re.search(r"<code>(\d+)</code>", text)
    return int(match.group(1)) if match else None

@sync_to_async
def get_appeal_by_user_id(user_id: int) -> Appeal | None:
    return Appeal.objects.filter(user__user_id=user_id, status=False).order_by('-created_at').first()

@sync_to_async
def mark_appeal_as_answered(appeal: Appeal):
    appeal.status = True
    appeal.save()


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.reply_to_message:
        return  # Faqat reply xabarlarga ishlaydi

    original_text = message.reply_to_message.text_html
    user_id = extract_user_id(original_text)
    if not user_id:
        await message.reply_text("Xatolik: <code>User ID topilmadi.</code>")
        return

    # Foydalanuvchiga yuboriladigan xabar
    try:
        await context.bot.send_message(chat_id=user_id, text=f"<b>Admin javobi:</b> {message.text}", parse_mode="HTML")
    except Exception as e:
        await message.reply_text(f"Xatolik: foydalanuvchiga xabar yuborib bo‘lmadi.\n{e}")
        return

    # Statusni yangilash
    appeal = await get_appeal_by_user_id(user_id)
    if appeal:
        await mark_appeal_as_answered(appeal)
        await message.reply_text("✅ Javob yuborildi va murojaat holati yangilandi.")
    else:
        await message.reply_text("❗ Murojaat topilmadi yoki allaqachon ko‘rilgan.")




def all_get_appeals(offset, limit):
    return list(
        Appeal.objects.all()
        .select_related("user")  # ForeignKey optimallashtirildi
        .order_by("created_at")[offset:offset + limit]
    )
async def all_appeals_page(page):
    offset = (page - 1) * ITEMS_PER_PAGE
    appeals = await sync_to_async(all_get_appeals)(offset, ITEMS_PER_PAGE)
    total = await sync_to_async(lambda: Appeal.objects.all().count())()
    return appeals, total

@admin_required
async def all_appeals(update: Update, _):
    query = update.callback_query
    await query.answer()

    page = int(query.data.split(":")[1]) if query and query.data.startswith("appeals_page:") else 1

    appeals, total = await all_appeals_page(page)
    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    if not appeals:
        await query.edit_message_text("Hozircha murojaatlar yo‘q.")
        return

    text_lines = []
    for idx, appeal in enumerate(appeals, start=1 + (page - 1) * ITEMS_PER_PAGE):
        short_msg = strip_tags(appeal.message)[:50]
        status = "✅" if appeal.status else "❗"
        text_lines.append(f"{idx}. {appeal.user.first_name}: {status} {short_msg}")

    text = "\n".join(text_lines)

    # Inline tugmalar
    buttons = []
    for i in range(1, len(appeals) + 1):
        buttons.append(InlineKeyboardButton(str(i), callback_data=f"appeal_detail:{(page - 1) * ITEMS_PER_PAGE + i}"))

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⏮️ Oldingi", callback_data=f"appeals_page:{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Keyingi ⏭️", callback_data=f"appeals_page:{page + 1}"))

    keyboard = [buttons[i:i+5] for i in range(0, len(buttons), 5)]  # 5 ta tugma 1 qatorda
    if nav_buttons:
        keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("Asosiy menyu", callback_data="Main_Menu")])
    await query.edit_message_text(
        text=f"<b>Murojaatlar — sahifa {page}/{total_pages}</b>\n\n{text}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
