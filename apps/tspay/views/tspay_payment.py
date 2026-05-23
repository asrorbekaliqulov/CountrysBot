"""
apps/Bot/views/tspay_payment.py

Frontend (Wizard) → Bu view → TSPay API → payment_url qaytaradi → Foydalanuvchi to'laydi
                                        ↓
                              /webhook/tspay/ (performTransaction)
                                        ↓
                              Order.status = 'paid', kuryer biriktiriladi
"""

import logging
import os

import requests as req_lib
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny

from apps.Bot.models.orders import Order, Payment
from apps.Bot.models.TelegramBot import TelegramUser
from apps.Bot.serializers.base import OrderCreateSerializer

logger = logging.getLogger(__name__)


def _tspay_base() -> str:
    return getattr(settings, 'TSPAY_BASE_URL', 'https://api.tspay.uz')


def _merchant_id() -> str:
    mid = getattr(settings, 'TSPAY_MERCHANT_ID', '') or os.getenv('TSPAY_MERCHANT_ID', '')
    if not mid:
        raise ValueError("TSPAY_MERCHANT_ID settings.py da yoki .env da sozlanmagan!")
    return mid


# ─────────────────────────────────────────────────────────────────────────────
# TSPay API: Yangi to'lov (cheque) yaratish
# ─────────────────────────────────────────────────────────────────────────────
def _create_tspay_cheque(order_id: int, amount_uzs: int) -> dict:
    """
    TSPay serveriga yangi to'lov so'rovi yuboradi.
    Qaytaradi: {'cheque_id': '...', 'payment_url': 'https://...'}
    """
    payload = {
        "merchant_id": _merchant_id(),
        "amount":      amount_uzs,   # so'm, butun son
        "order_id":    order_id,
    }

    try:
        resp = req_lib.post(
            f"{_tspay_base()}/api/transactions/",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=12,
        )
        data = resp.json()
        logger.info("[TSPay] Cheque yaratish javobi [%s]: %s", resp.status_code, data)

        if resp.status_code == 200 and data.get('cheque_id') and data.get('payment_url'):
            return {'ok': True, 'cheque_id': data['cheque_id'], 'payment_url': data['payment_url']}

        detail = data.get('detail') or data.get('error') or str(data)
        return {'ok': False, 'error': f"TSPay: {detail}"}

    except req_lib.exceptions.Timeout:
        return {'ok': False, 'error': "TSPay server javob bermadi (timeout)"}
    except Exception as exc:
        logger.exception("[TSPay] Cheque yaratishda kutilmagan xato: %s", exc)
        return {'ok': False, 'error': str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TSPay API: To'lov holatini tekshirish (polling)
# ─────────────────────────────────────────────────────────────────────────────
def _check_tspay_cheque(cheque_id: str) -> dict:
    """
    Berilgan cheque_id bo'yicha to'lov holatini TSPay dan so'raydi.
    Qaytaradi: {'status': 'success' | 'pending' | 'failed' | 'canceled'}
    """
    try:
        resp = req_lib.get(
            f"{_tspay_base()}/api/transactions/cheque/{cheque_id}",
            timeout=10,
        )
        data = resp.json()
        logger.info("[TSPay] Cheque holati [%s]: %s", cheque_id, data)
        return data
    except req_lib.exceptions.Timeout:
        return {'status': 'unknown', 'error': 'TSPay server javob bermadi'}
    except Exception as exc:
        logger.exception("[TSPay] Cheque tekshirishda xato: %s", exc)
        return {'status': 'unknown', 'error': str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# VIEW 1: Buyurtma yaratish + to'lov boshlash
# POST /api/orders/
# ─────────────────────────────────────────────────────────────────────────────
@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def create_order_with_payment(request):
    """
    Wizard frontend dan kelgan ma'lumotlar asosida:
      1. Buyurtma (Order) yaratadi
      2. Payment metodiga qarab yo'l tanlaydi:
         - 'admin' → chek screenshot kutiladi (admin paneldan tasdiqlanadi)
         - 'tpay'  → TSPay cheque yaratib payment_url qaytaradi
    """
    tg_id = request.data.get('tg_id')
    if not tg_id:
        return JsonResponse({'success': False, 'detail': 'tg_id talab qilinadi'}, status=400)

    try:
        user = TelegramUser.objects.get(user_id=str(tg_id))
    except TelegramUser.DoesNotExist:
        return JsonResponse({'success': False, 'detail': 'Foydalanuvchi topilmadi'}, status=400)

    serializer = OrderCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return JsonResponse({'success': False, 'detail': serializer.errors}, status=400)

    order   = serializer.save(user=user)
    payment = order.payment   # OrderCreateSerializer ichida yaratiladi

    # ── Admin (qo'lda) to'lov ─────────────────────────────────────────────────
    if payment.method == 'admin':
        logger.info("[Payment] Order #%s admin usulida yaratildi.", order.id)
        return JsonResponse({
            'success':        True,
            'payment_method': 'admin',
            'order_id':       order.id,
            'message':        "Buyurtma saqlandi. Chek tasvirini yuboring.",
        }, status=201)

    # ── TSPay to'lov ──────────────────────────────────────────────────────────
    if payment.method == 'tpay':
        try:
            amount_uzs = int(float(order.total_price))
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'detail': 'total_price noto\'g\'ri'}, status=400)

        result = _create_tspay_cheque(order.id, amount_uzs)

        if result['ok']:
            payment.transaction_id = result['cheque_id']
            payment.status         = 'pending'
            payment.save(update_fields=['transaction_id', 'status'])

            logger.info("[TSPay] Order #%s → cheque_id: %s", order.id, result['cheque_id'])

            return JsonResponse({
                'success':        True,
                'payment_method': 'tpay',
                'order_id':       order.id,
                'cheque_id':      result['cheque_id'],
                'payment_url':    result['payment_url'],
            }, status=201)

        # TSPay dan xato keldi — orderni saqlab qo'yamiz, to'lov keyinroq qayta urinilishi mumkin
        logger.error("[TSPay] Order #%s uchun cheque yaratilmadi: %s", order.id, result['error'])
        return JsonResponse({
            'success': False,
            'detail':  result['error'],
            'order_id': order.id,    # Frontend bu IDni saqlashi kerak, keyinroq qayta urinish uchun
        }, status=502)

    return JsonResponse({'success': False, 'detail': "Noto'g'ri to'lov usuli"}, status=400)


# ─────────────────────────────────────────────────────────────────────────────
# VIEW 2: Foydalanuvchi to'lovdan qaytganda holatni tekshirish (polling)
# GET /api/orders/<order_id>/check_payment/
# ─────────────────────────────────────────────────────────────────────────────
@csrf_exempt
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def check_payment_status(request, order_id):
    """
    Frontend to'lov sahifasidan qaytgandan so'ng bu endpoint ni so'raydi.
    Webhook allaqachon ishlagan bo'lsa — order.status 'paid' bo'ladi.
    Aks holda TSPay dan qayta so'rab tekshiradi.
    """
    try:
        order = Order.objects.select_related('payment').get(id=order_id)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'detail': 'Buyurtma topilmadi'}, status=404)

    payment = getattr(order, 'payment', None)

    # ── Webhook allaqachon ishlagan ──
    if order.status in ('paid', 'delivering', 'done'):
        return JsonResponse({'success': True, 'status': 'paid', 'order_status': order.status})

    if order.status == 'canceled':
        return JsonResponse({'success': False, 'status': 'canceled', 'order_status': 'canceled'})

    # ── TSPay dan polling ──────────────────────────────────────────────────────
    if payment and payment.method == 'tpay' and payment.transaction_id:
        cheque_data = _check_tspay_cheque(payment.transaction_id)
        txn_status  = cheque_data.get('status', 'unknown')

        if txn_status == 'success' and payment.status != 'success':
            # Webhook kelmagan bo'lsa ham biz o'zimiz tasdiqlashimiz mumkin
            from django.db import transaction as db_txn
            with db_txn.atomic():
                payment.status         = 'success'
                payment.transaction_id = cheque_data.get('id') or payment.transaction_id
                if cheque_data.get('card_mask'):
                    payment.card_mask = cheque_data['card_mask']
                payment.save()

                from apps.tspay.views.tspay_webhook import _auto_assign_courier
                _auto_assign_courier(order)

            return JsonResponse({'success': True, 'status': 'paid', 'order_status': 'paid'})

        if txn_status == 'pending':
            return JsonResponse({'success': False, 'status': 'pending', 'order_status': order.status})

        if txn_status in ('failed', 'canceled'):
            payment.status = 'failed'
            payment.save(update_fields=['status'])
            order.status = 'canceled'
            order.save(update_fields=['status'])
            return JsonResponse({'success': False, 'status': txn_status, 'order_status': 'canceled'})

    # Hali aniqlanmagan holat
    return JsonResponse({'success': False, 'status': 'pending', 'order_status': order.status})


# ─────────────────────────────────────────────────────────────────────────────
# VIEW 3: Admin panel — qo'lda to'lovni tasdiqlash
# POST /api/orders/<order_id>/confirm_payment/
# ─────────────────────────────────────────────────────────────────────────────
@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def admin_confirm_payment(request, order_id):
    """
    Admin panel tugmasiga bosilganda:
      - Payment.status = 'success'
      - Kuryer biriktiriladi
      - Signals ishga tushadi → bemor Telegram xabari oladi
    """
    # Tekshirish: admin ekanligini
    tg_id = request.GET.get('tg_id') or request.data.get('tg_id')
    if not tg_id:
        return JsonResponse({'success': False, 'detail': 'tg_id talab qilinadi'}, status=400)

    # pk validatsiya
    try:
        order_id = int(order_id)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'detail': 'order_id raqam bo\'lishi kerak'}, status=400)

    try:
        order = Order.objects.select_related('payment', 'service', 'user', 'district').get(pk=order_id)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'detail': f'#{order_id} buyurtma topilmadi'}, status=404)

    payment = getattr(order, 'payment', None)
    if not payment:
        return JsonResponse({'success': False, 'detail': 'Bu buyurtmaga payment biriktirilmagan'}, status=400)

    if payment.status == 'success':
        return JsonResponse({'success': True, 'message': 'Allaqachon tasdiqlangan', 'status': 'paid'})

    from django.db import transaction as db_txn
    try:
        with db_txn.atomic():
            payment.status         = 'success'
            payment.transaction_id = (
                request.data.get('transaction_id')
                or f"admin_{tg_id}_{order_id}"
            )
            payment.save()

            from apps.tspay.views.tspay_webhook import _auto_assign_courier
            _auto_assign_courier(order)

        logger.info("[AdminConfirm] Order #%s admin %s tomonidan tasdiqlandi.", order_id, tg_id)
        return JsonResponse({
            'success': True,
            'status':  'paid',
            'message': 'To\'lov tasdiqlandi va kuryer biriktirildi.',
        })

    except Exception as exc:
        logger.exception("[AdminConfirm] Xato: %s", exc)
        return JsonResponse({'success': False, 'detail': str(exc)}, status=500)