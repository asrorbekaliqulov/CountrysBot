from apps.Bot.BotCommands.StartCommand import main_menu_callback, set_lang_callback, intro_video_text_callback

from ..MandatoryChannel import AddChannel_ConvHandler, MandatoryChannelOrGroupList, start_delete_mandatory, delete_mandatory
from ..BotCommands import start
from ..BotAdmin import admin_menyu, add_admin_handler, the_first_admin, remove_admin_handler, AdminList
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from ..BotHandler import send_msg_handler, bot_stats, InlineButton, guide, guide_create_conv, guide_update_conv, guide_delete_conv, AdminGuide, appeal_conv, list_appeals, show_appeal_detail, handle_admin_reply, all_appeals, handle_results, handle_profile, handle_order_status, feedback_conv_handler, feedback_start
from datetime import datetime, timedelta
from ..BotCommands.DownDB import DownlBD
import random
import os 
from dotenv import load_dotenv

load_dotenv()

# Bot Token
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! .env faylini tekshiring.")



def main():
    # Application yaratishda persistence va job_queue parametrlarini qo'shamiz
    app = Application.builder().token(TOKEN).build()

    # Commands  
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("DownDataBaza", DownlBD))
    app.add_handler(CommandHandler('admin_panel', admin_menyu))
    app.add_handler(CommandHandler('kjiaufuyerfgvu', the_first_admin))


    
    # Conversation handlers
    app.add_handler(send_msg_handler)
    app.add_handler(add_admin_handler)
    app.add_handler(remove_admin_handler)
    app.add_handler(AddChannel_ConvHandler)
    app.add_handler(guide_create_conv)
    app.add_handler(guide_update_conv)
    app.add_handler(guide_delete_conv)
    app.add_handler(appeal_conv)
    app.add_handler(feedback_conv_handler)



    # Inline hanlder
    app.add_handler(CallbackQueryHandler(start, pattern=r"^Main_Menu$"))
    app.add_handler(CallbackQueryHandler(admin_menyu, pattern=r"^admin_menu$"))
    app.add_handler(CallbackQueryHandler(bot_stats, pattern=r"^botstats$"))
    app.add_handler(CallbackQueryHandler(start, pattern=r"^cancel$"))
    app.add_handler(CallbackQueryHandler(start_delete_mandatory, pattern=r"^Del_mandatory$"))
    app.add_handler(CallbackQueryHandler(delete_mandatory, pattern=r"^xDeleted_"))
    app.add_handler(CallbackQueryHandler(start, pattern=r"^Check_mandatory_channel$"))
    app.add_handler(CallbackQueryHandler(AdminList, pattern=r"^admin_list$"))
    app.add_handler(CallbackQueryHandler(MandatoryChannelOrGroupList, pattern=r"^mandatory_channel$"))
    app.add_handler(CallbackQueryHandler(start, pattern=r"^BackToMainMenu$"))
    app.add_handler(CallbackQueryHandler(guide, pattern=r"^getGuide$"))
    app.add_handler(CallbackQueryHandler(AdminGuide, pattern=r"^AdminGuide$"))
    app.add_handler(CallbackQueryHandler(list_appeals, pattern=r"^AdminAppeal$"))
    app.add_handler(CallbackQueryHandler(show_appeal_detail, pattern=r"^appeal_detail:\d+$"))
    app.add_handler(CallbackQueryHandler(all_appeals, pattern=r"^all_appeals$"))
    app.add_handler(CallbackQueryHandler(handle_order_status, pattern=r"^order_status$"))
    app.add_handler(CallbackQueryHandler(handle_results, pattern=r"^my_results$"))
    app.add_handler(CallbackQueryHandler(handle_profile, pattern=r"^my_profile$"))

    app.add_handler(CallbackQueryHandler(set_lang_callback, pattern=r"^set_lang:(uz|ru|en)$"))
    app.add_handler(CallbackQueryHandler(intro_video_text_callback, pattern=r"^intro_video_text$"))
    app.add_handler(CallbackQueryHandler(
        main_menu_callback,
        pattern="^(feedback|contact_us|appeal|admin_panel|back_to_menu)$"
    ))
    app.add_handler(CallbackQueryHandler(feedback_start, pattern="^feedback$"))

    # Catch-all — barcha aniq pattern handlerlardan keyin turishi shart
    app.add_handler(CallbackQueryHandler(InlineButton))

    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & filters.REPLY, handle_admin_reply))

    
    # Bot start
    print("The bot is running!!!")
    app.run_polling()
