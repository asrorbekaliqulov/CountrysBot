"""
Buyurtma + TSPay to'lov (docs.tspay.uz).
"""

import logging
import os

import requests as req_lib
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, authentication_classes, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny

from apps.Bot.models.orders import Order, Payment
from apps.Bot.models.TelegramBot import TelegramUser
from apps.Bot.serializers.base import OrderCreateSerializer

logger = logging.getLogger(__name__)

TSPAY_STATUS_SUCCESS = frozenset({'success', 'completed', '1'})
TSPAY_STATUS_PENDING = frozenset({'pending', '0'})
TSPAY_STATUS_FAILED = frozenset({'failed', '-9'})
TSPAY_STATUS_CANCELED = frozenset({'canceled', 'cancelled', '-1'})


def _tspay_base() -> str:
    return getattr(settings, 'TSPAY_BASE_URL', 'https://api.tspay.uz')


def _merchant_id() -> str:
    mid = getattr(settings, 'TSPAY_MERCHANT_ID', '') or os.getenv('TSPAY_MERCHANT_ID', '')
    if not mid:
        raise ValueError('TSPAY_MERCHANT_ID sozlanmagan')
    return mid


def _webapp_redirect_url(tg_id: str) -> str:
    base = getattr(settings, 'WEBAPP_URL', 'https://n-medhomelab.uz').rstrip('/')
    return f'{base}/api/webapp/?page=home&tspay_return=1&tg_id={tg_id}'


def _normalize_tspay_status(raw) -> str:
    if raw is None:
        return 'unknown'
    if isinstance(raw, int):
        return {1: 'success', 0: 'pending', -1: 'canceled', -9: 'failed'}.get(raw, 'unknown')
    s = str(raw).lower().strip()
    if s in TSPAY_STATUS_SUCCESS:
        return 'success'
    if s in TSPAY_STATUS_PENDING:
        return 'pending'
    if s in TSPAY_STATUS_FAILED:
        return 'failed'
    if s in TSPAY_STATUS_CANCELED:
        return 'canceled'
    return s


def _create_tspay_cheque(order_id: int, amount_uzs: int, tg_id: str) -> dict:
    payload = {
        'merchant_id': _merchant_id(),
        'amount': int(amount_uzs),
        'order_id': int(order_id),
        'redirect_url': _webapp_redirect_url(tg_id),
    }

    try:
        resp = req_lib.post(
            f'{_tspay_base()}/api/transactions/',
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=12,
        )
        data = resp.json() if resp.content else {}
        logger.info('[TSPay] POST /transactions/ [%s]: %s', resp.status_code, data)

        if resp.status_code == 200 and data.get('cheque_id') and data.get('payment_url'):
            return {
                'ok': True,
                'cheque_id': data['cheque_id'],
                'payment_url': data['payment_url'],
                'tspay_id': data.get('id'),
            }

        detail = data.get('detail') or data.get('error') or str(data)
        return {'ok': False, 'error': f'TSPay: {detail}'}
    except req_lib.exceptions.Timeout:
        return {'ok': False, 'error': 'TSPay server javob bermadi (timeout)'}
    except Exception as exc:
        logger.exception('[TSPay] Cheque xato: %s', exc)
        return {'ok': False, 'error': str(exc)}


def _check_tspay_cheque(cheque_id: str) -> dict:
    try:
        resp = req_lib.get(
            f'{_tspay_base()}/api/transactions/cheque/{cheque_id}',
            timeout=10,
        )
        data = resp.json() if resp.content else {}
        status = _normalize_tspay_status(data.get('status'))
        data['status'] = status
        logger.info('[TSPay] GET cheque/%s → %s', cheque_id, status)
        return data
    except req_lib.exceptions.Timeout:
        return {'status': 'unknown', 'error': 'TSPay timeout'}
    except Exception as exc:
        logger.exception('[TSPay] Cheque tekshirish: %s', exc)
        return {'status': 'unknown', 'error': str(exc)}


def _mark_order_paid(order: Order, payment: Payment, cheque_data: dict | None = None):
    from django.db import transaction as db_txn
    from apps.tspay.views.tspay_webhook import _auto_assign_courier

    with db_txn.atomic():
        payment.status = 'success'
        if cheque_data:
            if cheque_data.get('cheque_id'):
                payment.transaction_id = cheque_data['cheque_id']
        payment.save()
        if order.status not in ('paid', 'delivering', 'done', 'result_pending', 'result_sent'):
            _auto_assign_courier(order)


def _order_payload(order: Order, payment: Payment | None, order_code: str) -> dict:
    return {
        'order_id': order.id,
        'order_code': order_code,
        'order_status': order.status,
        'payment_status': payment.status if payment else None,
        'payment_method': payment.method if payment else None,
        'cheque_id': payment.transaction_id if payment else None,
    }


@csrf_exempt
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
@authentication_classes([])
@permission_classes([AllowAny])
def create_order_with_payment(request):
    tg_id = request.data.get('tg_id') or request.POST.get('tg_id')
    if not tg_id:
        return JsonResponse({'success': False, 'detail': 'tg_id talab qilinadi'}, status=400)

    try:
        user = TelegramUser.objects.get(user_id=str(tg_id))
    except TelegramUser.DoesNotExist:
        return JsonResponse({'success': False, 'detail': 'Foydalanuvchi topilmadi'}, status=400)

    try:
        payload = request.data
        if hasattr(payload, 'copy'):
            payload = payload.copy()
        if request.FILES.get('screenshot') and 'screenshot' not in payload:
            payload['screenshot'] = request.FILES['screenshot']

        serializer = OrderCreateSerializer(data=payload, context={'request': request})
        if not serializer.is_valid():
            from apps.Bot.serializers.base import flatten_serializer_errors
            detail = flatten_serializer_errors(serializer.errors)
            return JsonResponse(
                {'success': False, 'detail': detail, 'errors': serializer.errors},
                status=400,
            )

        order = serializer.save(user=user)
        order_code = f'NMED-{order.id:05d}'
        payment = order.payment

        if payment.method == 'admin':
            logger.info('[Payment] Order #%s admin (screenshot=%s)', order.id, bool(payment.screenshot))
            return JsonResponse({
                'success': True,
                'payment_method': 'admin',
                **_order_payload(order, payment, order_code),
                'message': "Buyurtma qabul qilindi. Operator to'lovni tekshiradi.",
            }, status=201)

        if payment.method == 'tpay':
            try:
                amount_uzs = int(float(order.total_price))
            except (TypeError, ValueError):
                return JsonResponse({'success': False, 'detail': "total_price noto'g'ri"}, status=400)

            if amount_uzs < 1000:
                return JsonResponse({'success': False, 'detail': 'Minimal summa 1000 so\'m'}, status=400)

            result = _create_tspay_cheque(order.id, amount_uzs, str(tg_id))

            if result['ok']:
                payment.transaction_id = result['cheque_id']
                payment.status = 'pending'
                payment.save(update_fields=['transaction_id', 'status'])
                logger.info('[TSPay] Order #%s cheque=%s', order.id, result['cheque_id'])
                return JsonResponse({
                    'success': True,
                    'payment_method': 'tpay',
                    **_order_payload(order, payment, order_code),
                    'cheque_id': result['cheque_id'],
                    'payment_url': result['payment_url'],
                }, status=201)

            logger.error('[TSPay] Order #%s cheque xato: %s', order.id, result['error'])
            return JsonResponse({
                'success': False,
                'detail': result['error'],
                **_order_payload(order, payment, order_code),
            }, status=502)

        return JsonResponse({'success': False, 'detail': "Noto'g'ri to'lov usuli"}, status=400)

    except Exception as exc:
        logger.exception('[Payment] Buyurtma yaratish: %s', exc)
        return JsonResponse({'success': False, 'detail': str(exc)}, status=500)


@csrf_exempt
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def check_payment_status(request, order_id):
    try:
        order = Order.objects.select_related('payment').get(id=order_id)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'detail': 'Buyurtma topilmadi'}, status=404)

    payment = getattr(order, 'payment', None)
    order_code = f'NMED-{order.id:05d}'
    base = {'success': False, 'order_code': order_code, **_order_payload(order, payment, order_code)}

    if order.status in ('paid', 'delivering', 'done', 'result_pending', 'result_sent'):
        return JsonResponse({**base, 'success': True, 'status': 'paid'})

    if order.status == 'canceled':
        return JsonResponse({**base, 'status': 'canceled'})

    if not payment or payment.method != 'tpay':
        return JsonResponse({**base, 'status': 'pending'})

    if payment.status == 'success':
        if order.status == 'pending':
            from apps.tspay.views.tspay_webhook import _auto_assign_courier
            _auto_assign_courier(order)
        return JsonResponse({**base, 'success': True, 'status': 'paid'})

    cheque_id = payment.transaction_id
    if not cheque_id:
        return JsonResponse({**base, 'status': 'pending', 'detail': 'cheque_id yo\'q'})

    cheque_data = _check_tspay_cheque(cheque_id)
    txn_status = cheque_data.get('status', 'unknown')

    if txn_status == 'success':
        _mark_order_paid(order, payment, cheque_data)
        order.refresh_from_db()
        return JsonResponse({**base, 'success': True, 'status': 'paid', 'order_status': order.status})

    if txn_status == 'pending':
        return JsonResponse({**base, 'status': 'pending'})

    if txn_status in ('failed', 'canceled'):
        payment.status = 'failed'
        payment.save(update_fields=['status'])
        if order.status == 'pending':
            order.status = 'canceled'
            order.save(update_fields=['status'])
        return JsonResponse({**base, 'status': txn_status})

    return JsonResponse({**base, 'status': 'pending', 'detail': cheque_data.get('error', '')})


@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def admin_confirm_payment(request, order_id):
    tg_id = request.GET.get('tg_id') or request.data.get('tg_id')
    if not tg_id:
        return JsonResponse({'success': False, 'detail': 'tg_id talab qilinadi'}, status=400)

    try:
        order_id = int(order_id)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'detail': 'order_id raqam bo\'lishi kerak'}, status=400)

    try:
        order = Order.objects.select_related('payment').get(pk=order_id)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'detail': f'#{order_id} topilmadi'}, status=404)

    payment = getattr(order, 'payment', None)
    if not payment:
        return JsonResponse({'success': False, 'detail': 'Payment yo\'q'}, status=400)

    if payment.status == 'success':
        return JsonResponse({'success': True, 'status': 'paid', 'message': 'Allaqachon tasdiqlangan'})

    from django.db import transaction as db_txn
    from apps.tspay.views.tspay_webhook import _auto_assign_courier

    try:
        with db_txn.atomic():
            payment.status = 'success'
            if not payment.transaction_id:
                payment.transaction_id = f'admin_{tg_id}_{order_id}'
            payment.save()
            _auto_assign_courier(order)

        logger.info('[AdminConfirm] Order #%s tasdiqlandi (admin %s)', order_id, tg_id)
        return JsonResponse({
            'success': True,
            'status': 'paid',
            'order_code': f'NMED-{order.id:05d}',
            'message': "To'lov tasdiqlandi.",
        })
    except Exception as exc:
        logger.exception('[AdminConfirm] %s', exc)
        return JsonResponse({'success': False, 'detail': str(exc)}, status=500)
