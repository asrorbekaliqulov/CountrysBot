from asgiref.sync import sync_to_async
from .models.TelegramBot import TelegramUser, Channel, Referral
import requests

async def save_user_to_db(data):
    user_id = data.id
    first_name = data.first_name  # Changed from `data.id` to `data.first_name`
    username = data.username  # Changed from `data.id` to `data.username`

    try:
        # Wrap the ORM operation with sync_to_async
        @sync_to_async
        def update_or_create_user():
            return TelegramUser.objects.update_or_create(
                user_id=user_id,
                defaults={'first_name': first_name, 'username': username}
            )

        user, created = await update_or_create_user()
        return True
    except Exception as error:
        print(f"Error saving user to DB: {error}")
        return False


@sync_to_async
def create_channel(chat_id, chat_name: str, chat_type: str, url=None):
    channel = Channel.objects.create(
        channel_id=chat_id,
        name=chat_name,
        type=chat_type,
        url=url
    )
    return channel


@sync_to_async
def create_referral(referrer, referred_user, referral_price=0.0):
    referral = Referral.objects.create(
        referrer=referrer,
        referred_user=referred_user,
        referral_price=referral_price
    )
    return referral


import requests
from django.conf import settings
import os

def send_telegram_notification(chat_id, text):
    """
    Foydalanuvchiga Telegram bot orqali bildirishnoma yuborish funksiyasi
    """
    # Bot tokeningizni settings.py dan oladi, agar u yerda bo'lmasa quyiga to'g'ridan-to'g'ri yozishingiz ham mumkin
    token = os.getenv("BOT_TOKEN")  # .env faylidan yoki settings.py dan olingan token
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        return response.ok
    except Exception as e:
        print(f"Telegramga xabar yuborishda xatolik: {e}")
        return False

