"""
Fikr va baholash uchun bot handlerlari
"""
import logging
from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from asgiref.sync import sync_to_async

from apps.Bot.models.TelegramBot import TelegramUser
from apps.Bot.models.feedback import Feedback

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
        lang = user.lang
    except TelegramUser.DoesNotExist:
        lang = 'uz'

    # Tugmalar
    buttons = {
        'uz': [
            [InlineKeyboardButton("⭐ Baholash", callback_data="feedback_rate")],
            [InlineKeyboardButton("📝 Faqat taklif yozish", callback_data="feedback_suggestion")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="Main_Menu")],
        ],
        'ru': [
            [InlineKeyboardButton("⭐ Оценить", callback_data="feedback_rate")],
            [InlineKeyboardButton("📝 Только предложение", callback_data="feedback_suggestion")],
            [InlineKeyboardButton("🔙 Назад", callback_data="Main_Menu")],
        ],
        'en': [
            [InlineKeyboardButton("⭐ Rate", callback_data="feedback_rate")],
            [InlineKeyboardButton("📝 Suggestion only", callback_data="feedback_suggestion")],
            [InlineKeyboardButton("🔙 Back", callback_data="Main_Menu")],
        ],
    }

    text = {
        'uz': "⭐️ Fikr va baholash\n\nXizmatimizni baholang yoki takliflaringizni yozing:",
        'ru': "⭐️ Отзыв и оценка\n\nОцените нашу услугу или напишите предложения:",
        'en': "⭐️ Feedback and rating\n\nRate our service or write suggestions:",
    }

    keyboard = InlineKeyboardMarkup(buttons.get(lang, buttons['uz']))

    try:
        await query.edit_message_text(
            text=text.get(lang, text['uz']),
            reply_markup=keyboard
        )
    except Exception:
        await context.bot.send_message(
            chat_id=tg_user.id,
            text=text.get(lang, text['uz']),
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
        lang = user.lang
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
        [InlineKeyboardButton("🔙 Orqaga", callback_data="feedback")],
    ]

    text = {
        'uz': "⭐️ Xizmatimizni baholang (1-5):",
        'ru': "⭐️ Оцените нашу услугу (1-5):",
        'en': "⭐️ Rate our service (1-5):",
    }

    keyboard = InlineKeyboardMarkup(buttons)

    try:
        await query.edit_message_text(
            text=text.get(lang, text['uz']),
            reply_markup=keyboard
        )
    except Exception:
        await context.bot.send_message(
            chat_id=tg_user.id,
            text=text.get(lang, text['uz']),
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
        lang = user.lang
    except TelegramUser.DoesNotExist:
        lang = 'uz'

    text = {
        'uz': "📝 Taklifingizni yozing:\n\nYuborish uchun xabaringizni yuboring.",
        'ru': "📝 Напишите ваше предложение:\n\nОтправьте сообщение для отправки.",
        'en': "📝 Write your suggestion:\n\nSend your message to submit.",
    }

    try:
        await query.edit_message_text(text=text.get(lang, text['uz']))
    except Exception:
        await context.bot.send_message(
            chat_id=tg_user.id,
            text=text.get(lang, text['uz'])
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
        lang = user.lang
    except TelegramUser.DoesNotExist:
        lang = 'uz'

    text = {
        'uz': f"⭐️ Siz {rating} yulduz tanladingiz.\n\nQo'shimcha fikringiz bormi? Yuborish uchun xabaringizni yuboring, yoki \"Skip\" tugmasini bosing.",
        'ru': f"⭐️ Вы выбрали {rating} звезд.\n\nЕсть ли дополнительные комментарии? Отправьте сообщение или нажмите \"Skip\".",
        'en': f"⭐️ You selected {rating} stars.\n\nAny additional comments? Send a message or press \"Skip\".",
    }

    buttons = [
        [InlineKeyboardButton("⏭️ Skip", callback_data="rate_skip")],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    try:
        await query.edit_message_text(
            text=text.get(lang, text['uz']),
            reply_markup=keyboard
        )
    except Exception:
        await context.bot.send_message(
            chat_id=tg_user.id,
            text=text.get(lang, text['uz']),
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
        lang = user.lang
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
        response_text = {
            'uz': "✅ Taklifingiz qabul qilindi! Rahmat!",
            'ru': "✅ Ваше предложение принято! Спасибо!",
            'en': "✅ Your suggestion has been accepted! Thank you!",
        }
    else:
        await sync_to_async(Feedback.objects.create)(
            user=user,
            rating=rating,
            text=text,
            is_suggestion_only=False
        )
        response_text = {
            'uz': f"✅ Fikringiz qabul qilindi! ({rating} ⭐)\n\nRahmat!",
            'ru': f"✅ Ваш отзыв принят! ({rating} ⭐)\n\nСпасибо!",
            'en': f"✅ Your feedback has been accepted! ({rating} ⭐)\n\nThank you!",
        }

    await update.message.reply_text(response_text.get(lang, response_text['uz']))

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
        lang = user.lang
    except TelegramUser.DoesNotExist:
        lang = 'uz'

    # Faqat baholashni saqlash
    await sync_to_async(Feedback.objects.create)(
        user=user,
        rating=rating,
        text=None,
        is_suggestion_only=False
    )

    response_text = {
        'uz': f"✅ Baholashingiz qabul qilindi! ({rating} ⭐)\n\nRahmat!",
        'ru': f"✅ Ваша оценка принята! ({rating} ⭐)\n\nСпасибо!",
        'en': f"✅ Your rating has been accepted! ({rating} ⭐)\n\nThank you!",
    }

    try:
        await query.edit_message_text(response_text.get(lang, response_text['uz']))
    except Exception:
        await context.bot.send_message(
            chat_id=tg_user.id,
            text=response_text.get(lang, response_text['uz'])
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
