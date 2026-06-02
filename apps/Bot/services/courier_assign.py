"""Kuryerni buyurtmaga biriktirish (yaqin hududdagi buyurtmalarni bir kuryerga yig'ish)."""
import logging
import os
from datetime import datetime

import requests as req_lib
from django.conf import settings
from django.db.models import Count, Min, Q

from apps.Bot.models.TelegramBot import TelegramUser
from apps.Bot.models.orders import Order

logger = logging.getLogger(__name__)


def notify_courier(courier_tg_id, order: Order, batch_count: int = 1):
    bot_token = getattr(settings, "BOT_TOKEN", None) or os.getenv("BOT_TOKEN")
    if not bot_token:
        return

    service_name = order.service.name_uz if order.service else "Tahlil"
    district_name = order.district.name if order.district else "—"
    phone = order.contact_phone or "—"
    batch_note = (
        f"\n📦 Sizda shu tuman bo'yicha *{batch_count}* ta faol buyurtma bor — bir yo'nalishda olib ketishingiz mumkin."
        if batch_count > 1
        else ""
    )

    text = (
        f"🔔 *Yangi zakaz biriktirildi!*\n\n"
        f"📋 Zakaz: *#{order.id}*\n"
        f"👤 Bemor: {order.patient_name or 'Nomalum'}\n"
        f"📞 Tel: {phone}\n"
        f"🧪 Xizmat: {service_name}\n"
        f"📍 Tuman: {district_name}\n"
        f"🏠 Manzil: {order.address_note or '—'}\n"
        f"🕐 Vaqt: {order.pickup_slot or '—'}"
        f"{batch_note}\n\n"
        f"💳 To'lov tasdiqlandi. Kuryer panelini oching."
    )

    try:
        req_lib.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": courier_tg_id, "text": text, "parse_mode": "Markdown"},
            timeout=8,
        )
    except Exception as exc:
        logger.error("[Courier] Xabar yuborishda xato: %s", exc)


def assign_courier_to_order(order: Order, notify: bool = True):
    """To'lovdan keyin kuryer biriktirish. Bir kuryerga yaqin buyurtmalarni yig'ish ustuvor."""
    if not order.district_id:
        logger.warning("[Courier] Order #%s — district yo'q", order.id)
        order.status = "paid"
        order.save(update_fields=["status"])
        return None

    couriers = TelegramUser.objects.filter(
        role="courier",
        district=order.district,
        is_active=True,
    )
    if not couriers.exists():
        logger.warning("[Courier] %s tumanida kuryer yo'q", order.district.name)
        order.status = "paid"
        order.save(update_fields=["status"])
        return None

    couriers_stats = list(
        couriers.annotate(
            active_count=Count(
                "assigned_orders",
                filter=Q(assigned_orders__status__in=["paid", "delivering"]),
            ),
            first_order_time=Min(
                "assigned_orders__created_at",
                filter=Q(assigned_orders__status__in=["paid", "delivering"]),
            ),
        )
    )

    busy = [c for c in couriers_stats if c.active_count > 0]
    if busy:
        chosen = min(
            busy,
            key=lambda c: (c.active_count, c.first_order_time or datetime.now()),
        )
    else:
        free = [c for c in couriers_stats if c.active_count == 0]
        chosen = (
            free[0]
            if free
            else min(
                couriers_stats,
                key=lambda c: (c.active_count, c.first_order_time or datetime.now()),
            )
        )

    order.courier = chosen
    order.status = "paid"
    order.save(update_fields=["courier", "status"])

    batch_count = Order.objects.filter(
        courier=chosen,
        status__in=["paid", "delivering"],
    ).count()

    logger.info(
        "[Courier] Order #%s → kuryer %s (faol: %s)",
        order.id,
        chosen.user_id,
        batch_count,
    )

    if notify:
        notify_courier(chosen.user_id, order, batch_count=batch_count)
    return chosen
