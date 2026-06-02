"""
TSPay webhook — checkPerform, createTransaction, performTransaction.
https://docs.tspay.uz — Merchant integratsiyasi
"""

import json
import logging

from django.db import transaction as db_transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from apps.Bot.models.orders import Order, Payment
from apps.tspay.tspay_signature import verify_tspay_webhook_signature

logger = logging.getLogger(__name__)

PAID_ORDER_STATUSES = frozenset({
    'paid', 'delivering', 'done', 'result_pending', 'result_sent',
})


def _auto_assign_courier(order: Order):
    from apps.Bot.services.courier_assign import assign_courier_to_order

    return assign_courier_to_order(order, notify=True)


def _resolve_order_id(params: dict) -> int | None:
    raw = params.get('order_id')
    if raw is None or raw == '':
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _get_payment(order: Order) -> Payment | None:
    return getattr(order, 'payment', None)


@csrf_exempt
def tspay_webhook_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Faqat POST'}, status=405)

    raw_body = request.body
    try:
        body = json.loads(raw_body)
    except Exception:
        logger.error('[TSPay] JSON xato: %s', raw_body[:300])
        return JsonResponse({'error': "JSON noto'g'ri"}, status=400)

    method = body.get('method', '')
    params = body.get('params', {}) or {}
    amount = float(params.get('amount', 0))
    order_pk = _resolve_order_id(params)
    signature_oid = params.get('order_id')

    logger.info(
        '[TSPay] Webhook %s order_id=%s amount=%s cheque=%s',
        method,
        signature_oid,
        amount,
        params.get('cheque_id', ''),
    )

    if not verify_tspay_webhook_signature(
        request.META,
        order_id=signature_oid,
        amount=amount,
    ):
        return JsonResponse({'error': "Imzo noto'g'ri"}, status=400)

    if order_pk is None:
        return JsonResponse({'allow': False, 'reason': 'order_id majburiy'}, status=400)

    try:
        order = Order.objects.select_related('payment', 'service', 'district', 'user').get(pk=order_pk)
    except Order.DoesNotExist:
        logger.error('[TSPay] Order #%s topilmadi', order_pk)
        if method == 'checkPerform':
            return JsonResponse({'allow': False, 'reason': f'#{order_pk} buyurtma topilmadi'})
        return JsonResponse({'success': False, 'reason': f'#{order_pk} buyurtma topilmadi'}, status=404)

    if method == 'checkPerform':
        if order.status in PAID_ORDER_STATUSES or order.status == 'canceled':
            return JsonResponse({
                'allow': False,
                'reason': f"Buyurtma '{order.status}' holatida.",
            })

        if order.total_price and abs(float(order.total_price) - amount) > 1:
            return JsonResponse({
                'allow': False,
                'reason': f'Summa mos emas. Kutilgan: {order.total_price}, kelgan: {amount}',
            })

        payment = _get_payment(order)
        additional = {'order_id': order.id, 'payment_id': payment.id if payment else None}
        logger.info('[TSPay] checkPerform OK #%s', order.id)
        return JsonResponse({'allow': True, 'additional': additional})

    if method == 'createTransaction':
        cheque_id = str(params.get('cheque_id', '') or '')
        payment = _get_payment(order)

        try:
            with db_transaction.atomic():
                if payment is None:
                    payment = Payment.objects.create(
                        order=order,
                        amount=amount,
                        method='tpay',
                        status='pending',
                        transaction_id=cheque_id or None,
                    )
                    logger.info('[TSPay] createTransaction: Payment #%s yaratildi', payment.id)
                    return JsonResponse({'success': True, 'transaction_id': str(payment.id)})

                if payment.status == 'success':
                    return JsonResponse({
                        'success': True,
                        'transaction_id': str(payment.id),
                    })

                if abs(float(payment.amount) - amount) > 1:
                    return JsonResponse({
                        'success': False,
                        'reason': 'Summa mos emas (idempotency)',
                    })

                if cheque_id and payment.transaction_id != cheque_id:
                    payment.transaction_id = cheque_id
                    payment.save(update_fields=['transaction_id'])

            return JsonResponse({'success': True, 'transaction_id': str(payment.id)})
        except Exception as exc:
            logger.exception('[TSPay] createTransaction: %s', exc)
            return JsonResponse({'success': False, 'reason': 'Server xatosi'}, status=500)

    if method == 'performTransaction':
        cheque_id = str(params.get('cheque_id', '') or '')
        tspay_txn_id = str(params.get('transaction_id', '') or '')
        try:
            with db_transaction.atomic():
                payment = _get_payment(order)
                if payment is None:
                    payment = Payment.objects.create(
                        order=order,
                        amount=amount,
                        method='tpay',
                        status='pending',
                        transaction_id=cheque_id or tspay_txn_id or None,
                    )

                if payment.status == 'success' and order.status in PAID_ORDER_STATUSES:
                    return JsonResponse({'success': True})

                payment.status = 'success'
                payment.amount = amount
                if cheque_id:
                    payment.transaction_id = cheque_id
                payment.save()

                _auto_assign_courier(order)

            logger.info('[TSPay] performTransaction OK #%s', order.id)
            return JsonResponse({'success': True})
        except Exception as exc:
            logger.exception('[TSPay] performTransaction: %s', exc)
            return JsonResponse({'success': False, 'reason': 'Server xatosi'}, status=500)

    if method == 'cancelTransaction':
        try:
            with db_transaction.atomic():
                payment = _get_payment(order)
                if payment and payment.status != 'success':
                    payment.status = 'failed'
                    payment.save(update_fields=['status'])
                if order.status == 'pending':
                    order.status = 'canceled'
                    order.save(update_fields=['status'])
            return JsonResponse({'success': True})
        except Exception as exc:
            logger.exception('[TSPay] cancelTransaction: %s', exc)
            return JsonResponse({'success': False, 'reason': 'Server xatosi'}, status=500)

    return JsonResponse({'error': f"Noma'lum metod: {method}"}, status=400)
