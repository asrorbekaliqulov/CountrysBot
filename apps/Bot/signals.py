from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from apps.Bot.models.TelegramBot import TelegramUser
from .utils import send_telegram_notification  # Yuqoridagi funksiyani import qilamiz

@receiver(pre_save, sender=TelegramUser)
def track_user_role_before_save(sender, instance, **kwargs):
    """
    Foydalanuvchi bazaga saqlanishidan oldin uning eski rolini keshlab olamiz.
    Bu orqali rostdan ham rol o'zgarganini aniqlaymiz.
    """
    if instance.id:
        try:
            previous_obj = TelegramUser.objects.get(id=instance.id)
            instance._previous_role = previous_obj.role
        except TelegramUser.DoesNotExist:
            instance._previous_role = None
    else:
        instance._previous_role = None


STAFF_ROLES = frozenset({'admin', 'doctor', 'courier'})


@receiver(post_save, sender=TelegramUser)
def notify_staff_on_role_change(sender, instance, created, **kwargs):
    """Faqat xodim rollari (admin/doctor/courier) uchun — oddiy user ga xabar yo'q."""
    if instance.role not in STAFF_ROLES:
        return

    role_names = {
        'admin': '💻 Admin (Boshqaruvchi)',
        'doctor': '🩺 Shifokor (Doctor)',
        'courier': '🚚 Kuryer / Tibbiy Xodim',
    }

    current_role_display = role_names.get(instance.role, instance.role)
    chat_id = instance.user_id

    if created:
        message_text = (
            f"<b>Hurmatli {instance.first_name}!</b>\n\n"
            f"🎉 Siz <b>Nmed Home Lab</b> tizimiga yangi xodim sifatida muvaffaqiyatli qo'shildingiz.\n\n"
            f"📌 Sizga berilgan rol: <b>{current_role_display}</b>\n"
            f"📞 Ro'yxatdan o'tgan telefon: {instance.phone_number or 'Kiritilmagan'}\n\n"
            f"<i>Ish faoliyatingizda muvaffaqiyatlar tilaymiz! 🔬</i>"
        )
        send_telegram_notification(chat_id, message_text)

    # 2-HOLAT: Mavjud xodimning roli o'zgarganda (Created = False)
    else:
        previous_role = getattr(instance, '_previous_role', None)
        
        # Agar roli rostdan ham o'zgargan bo'lsa xabar yuboramiz
        if previous_role and previous_role != instance.role:
            message_text = (
                f"<b>Diqqat, {instance.first_name}!</b>\n\n"
                f"🔄 Sizning tizimdagi profilingiz va lavozimingiz admin tomonidan yangilandi.\n\n"
                f"📌 Yangi rolingiz: <b>{current_role_display}</b>\n\n"
                f"<i>Tizim imkoniyatlaridan foydalanishni davom ettirishingiz mumkin. 🔬</i>"
            )
            send_telegram_notification(chat_id, message_text)


"""
apps/Bot/signals.py

Order.status o'zgarganda bemorga Telegram orqali avtomatik xabar yuboradi.

Ulanish:
    apps/Bot/apps.py ichida:
        def ready(self):
            import apps.Bot.signals  # noqa
"""

import os
import logging
import requests
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.conf import settings

from apps.Bot.models.orders import Order

logger = logging.getLogger(__name__)

# ─── Har bir status uchun xabar matni ────────────────────────────────────────
STATUS_MESSAGES = {
    'pending': (
        "🕐 *Buyurtmangiz qabul qilindi!*\n\n"
        "📋 Buyurtma #{order_id}\n"
        "🧪 Xizmat: {service}\n\n"
        "Tez orada operator tasdiqlaydi. Kuting..."
    ),
    'paid': (
        "✅ *To'lov tasdiqlandi!*\n\n"
        "📋 Buyurtma #{order_id}\n"
        "💰 To'langan summa: {price} so'm\n\n"
        "Kuryer tez orada yo'lga chiqadi. 🚗"
    ),
    'delivering': (
        "🚗 *Kuryer yo'lda!*\n\n"
        "📋 Buyurtma #{order_id}\n"
        "📍 Kuryer sizning manzilingizga kelmoqda.\n\n"
        "Iltimos, tayyor bo'ling!"
    ),
    'done': (
        "🧪 *Konteyner yetkazildi!*\n\n"
        "📋 Buyurtma #{order_id}\n"
        "Kuryer konteynerni yetkazidi.\n\n"
        "Tahlil natijasi tayyor bo'lgach xabardor qilamiz. ⏳"
    ),
    'result_pending': (
        "🔬 *Tahlil jarayonda!*\n\n"
        "📋 Buyurtma #{order_id}\n"
        "Namunangiz laboratoriyada tekshirilmoqda.\n\n"
        "Natija tayyor bo'lgach darhol yuboramiz. 📊"
    ),
    'result_sent': (
        "📊 *Tahlil natijangiz tayyor!*\n\n"
        "📋 Buyurtma #{order_id}\n"
        "🧪 Xizmat: {service}\n\n"
        "✅ Natija yuqoridagi xabar sifatida yuborildi.\n"
        "🩺 Xizmatimizdan foydalanganingiz uchun rahmat!"
    ),
    'canceled': (
        "❌ *Buyurtmangiz bekor qilindi.*\n\n"
        "📋 Buyurtma #{order_id}\n\n"
        "Savollaringiz bo'lsa, biz bilan bog'laning."
    ),
}


def get_bot_token():
    return getattr(settings, 'BOT_TOKEN', None) or os.getenv('BOT_TOKEN')


def send_telegram_message(chat_id: str, text: str) -> bool:
    """Telegram sendMessage API — matnli xabar"""
    token = get_bot_token()
    if not token:
        logger.warning("[Signal] BOT_TOKEN topilmadi.")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                'chat_id':    str(chat_id),
                'text':       text,
                'parse_mode': 'Markdown',
            },
            timeout=10,
        )
        data = resp.json()
        if not data.get('ok'):
            logger.error("[Signal] Telegram xatosi: %s", data.get('description'))
            return False
        return True
    except requests.exceptions.Timeout:
        logger.error("[Signal] Telegram timeout.")
        return False
    except Exception as exc:
        logger.error("[Signal] Telegram exception: %s", exc)
        return False


def build_message(status: str, order) -> str | None:
    """Statusga mos xabar matnini shakllantiradi"""
    template = STATUS_MESSAGES.get(status)
    if not template:
        return None

    service_name = "—"
    if order.service:
        service_name = order.service.name_uz or "—"

    price_str = "—"
    if order.total_price:
        price_str = f"{order.total_price:,.0f}"

    return template.format(
        order_id=str(order.id),
        service=service_name,
        price=price_str,
    )


def get_patient_tg_id(order) -> str | None:
    """Buyurtmaga bog'liq bemorning Telegram ID sini qaytaradi"""
    if hasattr(order, 'user') and order.user:
        return str(order.user.user_id)
    if hasattr(order, 'telegram_user') and order.telegram_user:
        return str(order.telegram_user.user_id)
    return None


# ─── pre_save — eski statusni eslab qolish ────────────────────────────────────
@receiver(pre_save, sender=Order)
def remember_old_status(sender, instance, **kwargs):
    """
    Yangilanishdan OLDIN eski statusni instance ga yozib qo'yamiz.
    post_save da taqqoslash uchun kerak.
    """
    if instance.pk:
        try:
            instance._old_status = Order.objects.get(pk=instance.pk).status
        except Order.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None   # yangi buyurtma


# ─── post_save — status o'zgarganda xabar yuborish ────────────────────────────
@receiver(post_save, sender=Order)
def notify_patient_on_status_change(sender, instance, created, **kwargs):
    """
    Order saqlangandan KEYIN (on_commit — HTTP javobni bloklamasdan):
    - Yangi buyurtma → 'pending' xabari
    - Status o'zgangan → yangi statusga mos xabar
    """
    from django.db import transaction

    order_id = instance.pk
    new_status = instance.status
    old_status = getattr(instance, '_old_status', None)

    if not created and old_status == new_status:
        return

    def _send_after_commit():
        try:
            order = Order.objects.select_related('service', 'user').get(pk=order_id)
        except Order.DoesNotExist:
            return

        patient_tg_id = get_patient_tg_id(order)
        if not patient_tg_id:
            return

        text = build_message(order.status, order)
        if not text:
            return

        success = send_telegram_message(patient_tg_id, text)
        logger.info(
            "[Signal] Buyurtma #%s | %s → %s | Telegram: %s",
            order.id,
            old_status or "yangi",
            order.status,
            "✅ yuborildi" if success else "❌ xato",
        )

    transaction.on_commit(_send_after_commit)