"""
Fikr va baholash uchun bot handlerlari
"""
import logging
from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from asgiref.sync import sync_to_async

from apps.Bot.models.TelegramBot import TelegramUser
from apps.Bot.models.feedback import Feedback
from apps.Bot.translations import t

logger = logging.getLogger(__name__)

# Conversation states
RATING, TEXT = range(2)


async def feedback_start(update: Update, context):
    """Fikr va baholashni boshlash"""
    query = update.callback_query
    await query.answer()

    # Tilni aniqlash
    tg_user = update.effective_user
    try:
        user = await sync_to_async(TelegramUser.objects.get)(user_id=tg_user.id)
        lang = user.lang or 'uz'
    except TelegramUser.DoesNotExist:
        lang = 'uz'

    # Tugmalar
    buttons = [
        [InlineKeyboardButton(t("feedback_rate", lang), callback_data="feedback_rate")],
        [InlineKeyboardButton(t("feedback_suggestion", lang), callback_data="feedback_suggestion")],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="Main_Menu")],
    ]

    keyboard = InlineKeyboardMarkup(buttons)

    try:
        await query.edit_message_text(
            text=t("feedback_title", lang),
            reply_markup=keyboard
        )
    except Exception:
        await context.bot.send_message(
            chat_id=tg_user.id,
            text=t("feedback_title", lang),
            reply_markup=keyboard
        )

    return ConversationHandler.END


async def feedback_rating_start(update: Update, context):
    """Baholashni boshlash"""
    query = update.callback_query
    await query.answer()

    tg_user = update.effective_user
    try:
        user = await sync_to_async(TelegramUser.objects.get)(user_id=tg_user.id)
        lang = user.lang or 'uz'
    except TelegramUser.DoesNotExist:
        lang = 'uz'

    # Yulduzcha tugmalari
    buttons = [
        [
            InlineKeyboardButton("⭐", callback_data="rate_1"),
            InlineKeyboardButton("⭐⭐", callback_data="rate_2"),
            InlineKeyboardButton("⭐⭐⭐", callback_data="rate_3"),
            InlineKeyboardButton("⭐⭐⭐⭐", callback_data="rate_4"),
            InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="rate_5"),
        ],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="feedback")],
    ]

    keyboard = InlineKeyboardMarkup(buttons)

    try:
        await query.edit_message_text(
            text=t("feedback_rate_service", lang),
            reply_markup=keyboard
        )
    except Exception:
        await context.bot.send_message(
            chat_id=tg_user.id,
            text=t("feedback_rate_service", lang),
            reply_markup=keyboard
        )

    return RATING


async def feedback_suggestion_start(update: Update, context):
    """Faqat taklif yozishni boshlash"""
    query = update.callback_query
    await query.answer()

    tg_user = update.effective_user
    try:
        user = await sync_to_async(TelegramUser.objects.get)(user_id=tg_user.id)
        lang = user.lang or 'uz'
    except TelegramUser.DoesNotExist:
        lang = 'uz'

    try:
        await query.edit_message_text(text=t("feedback_write_suggestion", lang))
    except Exception:
        await context.bot.send_message(
            chat_id=tg_user.id,
            text=t("feedback_write_suggestion", lang)
        )

    context.user_data['feedback_type'] = 'suggestion'
    return TEXT


async def feedback_rating_selected(update: Update, context):
    """Baholash tanlandi"""
    query = update.callback_query
    await query.answer()

    rating = int(query.data.split('_')[1])
    context.user_data['rating'] = rating

    tg_user = update.effective_user
    try:
        user = await sync_to_async(TelegramUser.objects.get)(user_id=tg_user.id)
        lang = user.lang or 'uz'
    except TelegramUser.DoesNotExist:
        lang = 'uz'

    buttons = [
        [InlineKeyboardButton(t("feedback_skip", lang), callback_data="rate_skip")],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    try:
        await query.edit_message_text(
            text=t("feedback_rating_selected", lang, rating=rating),
            reply_markup=keyboard
        )
    except Exception:
        await context.bot.send_message(
            chat_id=tg_user.id,
            text=t("feedback_rating_selected", lang, rating=rating),
            reply_markup=keyboard
        )

    context.user_data['feedback_type'] = 'rating'
    return TEXT


async def feedback_text_received(update: Update, context):
    """Fikr matni qabul qilindi"""
    tg_user = update.effective_user
    text = update.message.text
    feedback_type = context.user_data.get('feedback_type', 'rating')
    rating = context.user_data.get('rating')

    try:
        user = await sync_to_async(TelegramUser.objects.get)(user_id=tg_user.id)
        lang = user.lang or 'uz'
    except TelegramUser.DoesNotExist:
        lang = 'uz'

    # Feedbackni saqlash
    if feedback_type == 'suggestion':
        await sync_to_async(Feedback.objects.create)(
            user=user,
            rating=None,
            text=text,
            is_suggestion_only=True
        )
        response_text = t("feedback_suggestion_thanks", lang)
    else:
        await sync_to_async(Feedback.objects.create)(
            user=user,
            rating=rating,
            text=text,
            is_suggestion_only=False
        )
        response_text = t("feedback_thanks", lang, rating=rating)

    await update.message.reply_text(response_text)

    # Asosiy menyuga qaytish
    from ..BotCommands.StartCommand import start
    await start(update, context)

    return ConversationHandler.END


async def feedback_skip(update: Update, context):
    """Fikr matnisiz davom etish"""
    query = update.callback_query
    await query.answer()

    tg_user = update.effective_user
    rating = context.user_data.get('rating')

    try:
        user = await sync_to_async(TelegramUser.objects.get)(user_id=tg_user.id)
        lang = user.lang or 'uz'
    except TelegramUser.DoesNotExist:
        lang = 'uz'

    # Faqat baholashni saqlash
    await sync_to_async(Feedback.objects.create)(
        user=user,
        rating=rating,
        text=None,
        is_suggestion_only=False
    )

    response_text = t("feedback_rating_thanks", lang, rating=rating)

    try:
        await query.edit_message_text(response_text)
    except Exception:
        await context.bot.send_message(
            chat_id=tg_user.id,
            text=response_text
        )

    # Asosiy menyuga qaytish
    from ..BotCommands.StartCommand import start
    await start(update, context)

    return ConversationHandler.END


async def feedback_cancel(update: Update, context):
    """Bekor qilish"""
    query = update.callback_query
    await query.answer()

    from ..BotCommands.StartCommand import start
    await start(update, context)

    return ConversationHandler.END


# Conversation handler
feedback_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(feedback_start, pattern="^feedback$"),
    ],
    states={
        RATING: [
            CallbackQueryHandler(feedback_rating_selected, pattern="^rate_[1-5]$"),
            CallbackQueryHandler(feedback_cancel, pattern="^feedback$"),
        ],
        TEXT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_text_received),
            CallbackQueryHandler(feedback_skip, pattern="^rate_skip$"),
            CallbackQueryHandler(feedback_cancel, pattern="^feedback$"),
        ],
    },
    fallbacks=[
        CallbackQueryHandler(feedback_cancel, pattern="^Main_Menu$"),
    ],
)
