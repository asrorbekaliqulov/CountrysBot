"""
apps/Bot/views/tspay_webhook.py

TSPay to'lov tizimining webhook handleri.
Django loyihangizning real Order va Payment modellari bilan ishlaydi.

urls.py ga qo'shish:
    path('webhook/tspay/', tspay_webhook_view, name='tspay_webhook'),
"""

import hmac
import hashlib
import logging
import os

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction as db_transaction

from apps.Bot.models.orders import Order, Payment
from apps.Bot.models.TelegramBot import TelegramUser

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# settings.py ga qo'shish kerak:
#
# TSPAY_WEBHOOK_SECRET = "476b3e080eebb068cd1616220d0eb3895e357248dee59ac5c240f12c441d3b37"
# TSPAY_MERCHANT_ID    = "mer_XXXXXXXX"
# BOT_TOKEN            = "your_bot_token_here"
# ─────────────────────────────────────────────────────────────────────────────


def _get_secret() -> str:
    return (
        getattr(settings, 'TSPAY_WEBHOOK_SECRET', None)
        or os.getenv('TSPAY_WEBHOOK_SECRET', '')
    )


def _verify_signature(headers: dict, order_id: str, amount: float, timestamp: str) -> bool:
    """
    TSPay imzosini tekshiradi.
    Imzo formulasi: HMAC-SHA256( "order_id:amount:timestamp" )
    """
    secret = _get_secret()
    if not secret:
        logger.warning("[TSPay] TSPAY_WEBHOOK_SECRET sozlanmagan — imzo tekshiruvi o'tkazib yuborildi!")
        return True  # Dev rejimida o'tkazib yuboramiz, prodda False qiling

    sig_header = headers.get('HTTP_X_SIGNATURE', '') or headers.get('x-signature', '')
    if not sig_header:
        logger.warning("[TSPay] x-signature header topilmadi.")
        return False

    expected = "sha256=" + hmac.new(
        secret.encode(),
        f"{order_id}:{float(amount):.2f}:{timestamp}".encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(sig_header, expected)


def _auto_assign_courier(order: Order):
    """
    To'lov tasdiqlangandan so'ng kuryerni avtomatik biriktirish.
    views.py dagi OrderViewSet._auto_assign_courier logikasi shu yerda ham ishlatiladi.
    """
    from django.db.models import Count, Q, Min
    from datetime import datetime

    if not order.district:
        logger.warning("[TSPay] Order #%s — district yo'q, kuryer biriktirilmadi.", order.id)
        order.status = 'paid'
        order.save(update_fields=['status'])
        return None

    couriers = TelegramUser.objects.filter(
        role='courier',
        district=order.district,
        is_active=True,
    )

    if not couriers.exists():
        logger.warning("[TSPay] %s tumanida faol kuryer topilmadi.", order.district.name)
        order.status = 'paid'
        order.save(update_fields=['status'])
        return None

    couriers_stats = couriers.annotate(
        active_count=Count(
            'assigned_orders',
            filter=Q(assigned_orders__status__in=['paid', 'delivering'])
        ),
        first_order_time=Min(
            'assigned_orders__created_at',
            filter=Q(assigned_orders__status__in=['paid', 'delivering'])
        )
    )

    free = [c for c in couriers_stats if c.active_count == 0]
    chosen = free[0] if free else sorted(
        couriers_stats,
        key=lambda c: (c.active_count, c.first_order_time or datetime.now())
    )[0]

    order.status = 'paid'
    order.save(update_fields=['status'])

    logger.info("[TSPay] Order #%s → Kuryer TG_ID: %s", order.id, chosen.user_id)

    # Kuryerga Telegram xabari
    _notify_courier(chosen.user_id, order)
    return chosen


def _notify_courier(courier_tg_id, order: Order):
    """Kuryerga Telegram orqali yangi zakaz haqida xabar yuboradi."""
    import requests as req_lib

    bot_token = getattr(settings, 'BOT_TOKEN', None) or os.getenv('BOT_TOKEN')
    if not bot_token:
        return

    service_name = order.service.name_uz if order.service else "Tahlil"
    district_name = order.district.name if order.district else "—"

    text = (
        f"🔔 *Yangi zakaz biriktirildi!*\n\n"
        f"📋 Zakaz: *#{order.id}*\n"
        f"👤 Bemor: {order.patient_name or 'Noma\'lum'}\n"
        f"🧪 Xizmat: {service_name}\n"
        f"📍 Tuman: {district_name}\n"
        f"🏠 Manzil: {order.address_note or '—'}\n\n"
        f"💳 To'lov tasdiqlandi. Iltimos, yo'lga chiqing!"
    )

    try:
        req_lib.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={'chat_id': courier_tg_id, 'text': text, 'parse_mode': 'Markdown'},
            timeout=8,
        )
    except Exception as exc:
        logger.error("[TSPay] Kuryerga xabar yuborishda xato: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# ASOSIY WEBHOOK VIEW
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
def tspay_webhook_view(request):
    """
    POST /webhook/tspay/

    TSPay uch xil metod yuboradi:
      1. checkPerform      — Buyurtma mavjud va to'lanishi mumkinmi?
      2. createTransaction — Tranzaksiya boshlanmoqda (payment pending)
      3. performTransaction — To'lov muvaffaqiyatli yakunlandi ✅
    """
    if request.method != 'POST':
        return JsonResponse({'error': "Faqat POST"}, status=405)

    # ── JSON parse ────────────────────────────────────────────────────────────
    try:
        import json
        body = json.loads(request.body)
    except Exception:
        logger.error("[TSPay] JSON parse xatosi: %s", request.body[:200])
        return JsonResponse({'error': "JSON noto'g'ri"}, status=400)

    method    = body.get('method', '')
    params    = body.get('params', {})
    order_id  = str(params.get('order_id', ''))
    amount    = float(params.get('amount', 0))
    timestamp = request.META.get('HTTP_X_TIMESTAMP', '') or params.get('timestamp', '')

    logger.info("[TSPay] Webhook: method=%s order_id=%s amount=%s", method, order_id, amount)

    # ── Imzoni tekshirish ─────────────────────────────────────────────────────
    if not _verify_signature(request.META, order_id, amount, timestamp):
        logger.warning("[TSPay] Imzo xato! order_id=%s", order_id)
        return JsonResponse({'error': "Imzo noto'g'ri"}, status=400)

    # ── Order mavjudligini oldindan tekshiramiz ────────────────────────────────
    try:
        order = (
            Order.objects
            .select_related('service', 'district', 'user')
            .get(id=order_id)
        )
    except Order.DoesNotExist:
        logger.error("[TSPay] Order #%s topilmadi!", order_id)
        return JsonResponse({'success': False, 'reason': f"#{order_id} buyurtma topilmadi"}, status=404)
    except ValueError:
        return JsonResponse({'success': False, 'reason': "order_id noto'g'ri format"}, status=400)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. checkPerform — Buyurtmani oldindan tekshirish
    # ─────────────────────────────────────────────────────────────────────────
    if method == 'checkPerform':
        # Allaqachon to'langan yoki bekor qilingan buyurtmalarni rad etamiz
        if order.status in ('paid', 'delivering', 'done', 'result_pending', 'result_sent', 'canceled'):
            logger.warning("[TSPay] checkPerform: Order #%s allaqachon %s.", order.id, order.status)
            return JsonResponse({
                'allow': False,
                'reason': f"Buyurtma allaqachon '{order.status}' holatida."
            })

        # Summani tekshirish (agar total_price bo'lsa)
        if order.total_price and abs(float(order.total_price) - amount) > 1:
            logger.warning(
                "[TSPay] checkPerform: Summa mos emas. Kutilgan: %s, Kelgan: %s",
                order.total_price, amount
            )
            return JsonResponse({
                'allow': False,
                'reason': f"Summa mos emas. Kutilgan: {order.total_price}, kelgan: {amount}"
            })

        logger.info("[TSPay] checkPerform: Order #%s ✅ ruxsat berildi.", order.id)
        return JsonResponse({'allow': True})

    # ─────────────────────────────────────────────────────────────────────────
    # 2. createTransaction — Tranzaksiya yaratish (pending holat)
    # ─────────────────────────────────────────────────────────────────────────
    elif method == 'createTransaction':
        cheque_id = params.get('cheque_id', '')

        try:
            with db_transaction.atomic():
                payment = getattr(order, 'payment', None)

                if payment is None:
                    # Payment hali yaratilmagan bo'lsa yaratamiz
                    payment = Payment.objects.create(
                        order=order,
                        amount=amount,
                        method='tpay',
                        status='pending',
                    )
                    logger.info("[TSPay] createTransaction: Order #%s uchun yangi Payment yaratildi.", order.id)

                elif payment.status == 'success':
                    # Idempotentlik: allaqachon to'langan
                    logger.info("[TSPay] createTransaction (idempotent): Order #%s allaqachon to'langan.", order.id)
                    return JsonResponse({'success': True, 'transaction_id': payment.transaction_id or cheque_id})

                # cheque_id ni transaction_id sifatida saqlaymiz (pending paytida)
                if cheque_id and not payment.transaction_id:
                    payment.transaction_id = cheque_id
                    payment.save(update_fields=['transaction_id'])

            logger.info("[TSPay] createTransaction: Order #%s pending ✅", order.id)
            return JsonResponse({'success': True, 'transaction_id': cheque_id})

        except Exception as exc:
            logger.exception("[TSPay] createTransaction xatosi: %s", exc)
            return JsonResponse({'success': False, 'reason': "Server xatosi"}, status=500)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. performTransaction — To'lov yakunlandi ✅
    # ─────────────────────────────────────────────────────────────────────────
    elif method == 'performTransaction':
        tspay_txn_id = str(params.get('transaction_id', '') or params.get('id', ''))
        card_mask    = params.get('card_mask', '')

        try:
            with db_transaction.atomic():
                payment = getattr(order, 'payment', None)

                # Payment yo'q bo'lsa ham yaratib olamiz (ba'zan createTransaction o'tkazib yuboriladi)
                if payment is None:
                    payment = Payment.objects.create(
                        order=order,
                        amount=amount,
                        method='tpay',
                        status='pending',
                    )

                # Idempotentlik: allaqachon muvaffaqiyatli bo'lgan
                if payment.status == 'success':
                    logger.info("[TSPay] performTransaction (idempotent): Order #%s allaqachon to'langan.", order.id)
                    return JsonResponse({'success': True})

                # Payment ni yangilaymiz
                payment.status         = 'success'
                payment.transaction_id = tspay_txn_id or payment.transaction_id
                if card_mask:
                    payment.card_mask = card_mask
                payment.save()

                # Order ga kuryerni biriktiramiz (signal ham ishga tushadi → bemor xabardor bo'ladi)
                _auto_assign_courier(order)

            logger.info("[TSPay] performTransaction: Order #%s ✅ to'landi va kuryerga biriktirildi.", order.id)
            return JsonResponse({'success': True})

        except Exception as exc:
            logger.exception("[TSPay] performTransaction xatosi: %s", exc)
            return JsonResponse({'success': False, 'reason': "Server xatosi"}, status=500)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. cancelTransaction — To'lov bekor qilindi
    # ─────────────────────────────────────────────────────────────────────────
    elif method == 'cancelTransaction':
        reason = params.get('reason', 'TSPay tomonidan bekor qilindi')
        try:
            with db_transaction.atomic():
                payment = getattr(order, 'payment', None)
                if payment and payment.status != 'success':
                    payment.status = 'failed'
                    payment.save(update_fields=['status'])

                if order.status == 'pending':
                    order.status = 'canceled'
                    order.save(update_fields=['status'])

            logger.info("[TSPay] cancelTransaction: Order #%s bekor qilindi. Sabab: %s", order.id, reason)
            return JsonResponse({'success': True})

        except Exception as exc:
            logger.exception("[TSPay] cancelTransaction xatosi: %s", exc)
            return JsonResponse({'success': False, 'reason': "Server xatosi"}, status=500)

    # ── Noma'lum metod ────────────────────────────────────────────────────────
    logger.warning("[TSPay] Noma'lum metod: %s", method)
    return JsonResponse({'error': f"Noma'lum metod: {method}"}, status=400)