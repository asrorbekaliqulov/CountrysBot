from telegram import Update
from telegram.ext import CallbackContext
from ..models.TelegramBot import TelegramUser
from ..decorators import admin_required
from ..translations import t
import os 
from dotenv import load_dotenv

load_dotenv()

# Bot Token
TOKEN = os.getenv("BOT_TOKEN")


async def today_new_users():
    today_new_users = await TelegramUser.get_today_new_users()
    return len(today_new_users)

@admin_required
async def bot_stats(update: Update, context: CallbackContext):
    msg = update.callback_query
    tg_user = update.effective_user
    
    # Foydalanuvchi tilini olish
    try:
        from asgiref.sync import sync_to_async
        user = await sync_to_async(TelegramUser.objects.get)(user_id=tg_user.id)
        lang = user.lang or "uz"
    except TelegramUser.DoesNotExist:
        lang = "uz"
    
    await msg.answer(t("stats_loading", lang))
    bot_token = TOKEN
    blocked_count = await TelegramUser.find_inactive_users(bot_token)
    bot = await context.bot.get_me()
    total_users = await TelegramUser.get_total_users()
    active_users_count = total_users - blocked_count
    admin_users_count = await TelegramUser.count_admin_users()
    new_users_count = await today_new_users()

    stats_text = t("stats_title", lang,
        username=bot.username,
        total=total_users,
        new=new_users_count if new_users_count else 0,
        admins=admin_users_count,
        active=active_users_count,
        inactive=blocked_count
    )

    await msg.edit_message_text(text=stats_text, parse_mode="HTML")