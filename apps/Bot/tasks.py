"""
Celery tasks for background jobs
"""
import logging
import os
import requests as req_lib
from celery import shared_task
from django.conf import settings

from apps.Bot.models.feedback import Feedback

logger = logging.getLogger(__name__)


@shared_task
def update_bot_bio():
    """
    Bot bio-ni har 3 kunda yangilash.
    AppStore/PlayMarket o'xshash statistika bilan:
    - O'rtacha reyting
    - Jami ovozlar
    - Yoqganlar/Yoqmaganlar
    """
    bot_token = getattr(settings, "BOT_TOKEN", None) or os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.error("[BotBio] BOT_TOKEN topilmadi")
        return

    try:
        # Yangi statistika funksiyasidan foydalanish
        stats = Feedback.get_rating_stats()

        # Bio matni (AppStore/PlayMarket o'xshash)
        if stats['total_votes'] > 0:
            # Yulduzchalar
            stars = '⭐' * int(round(stats['average_rating']))
            
            bio_text = (
                f"{stars} {stats['average_rating']}/5 ({stats['total_votes']} ta ovoz)\n"
                f"👍 {stats['liked_count']} yoqdi | 👎 {stats['disliked_count']} yoqmadi\n\n"
                f"🧪 Uydan tahlil topshirish | NMED HOME LAB"
            )
        else:
            bio_text = "🧪 Uydan tahlil topshirish | NMED HOME LAB"

        # Telegram API orqali bio yangilash
        url = f"https://api.telegram.org/bot{bot_token}/setMyDescription"
        payload = {
            "description": bio_text
        }

        response = req_lib.post(url, json=payload, timeout=10)
        data = response.json()

        if data.get("ok"):
            logger.info("[BotBio] Bio muvaffaqiyatli yangilandi: %s", bio_text)
        else:
            logger.error("[BotBio] Bio yangilash xatosi: %s", data.get("description"))

    except Exception as e:
        logger.exception("[BotBio] Bio yangilashda xatolik: %s", e)
