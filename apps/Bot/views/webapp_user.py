"""
Foydalanuvchi Telegram WebApp API va sahifalari.
"""

import json
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.utils import translation
from django.views.decorators.csrf import csrf_exempt

from apps.Bot.models.TelegramBot import TelegramUser, Appeal
from apps.Bot.models.bot import BotSetting
from apps.Bot.models.orders import Order, TestResult

logger = logging.getLogger(__name__)

SETTING_KEYS = (
    'payment_card_number',
    'payment_card_holder',
    'support_contact',
    'support_phone',
    'support_telegram',
    'default_delivery_fee',
)

DEFAULT_SETTINGS = {
    'payment_card_number': '8600 1234 5678 9012',
    'payment_card_holder': 'X. Alisher',
    'support_contact': '@nmed_support',
    'support_phone': '+998901234567',
    'support_telegram': 'https://t.me/nmed_support',
    'default_delivery_fee': '20000',
}


def _get_settings_dict():
    data = dict(DEFAULT_SETTINGS)
    for key in SETTING_KEYS:
        val = BotSetting.get(key)
        if val is not None and str(val).strip():
            data[key] = val
    return data


def _save_settings_dict(payload: dict):
    mapping = {
        'payment_card_number': payload.get('payment_card_number'),
        'payment_card_holder': payload.get('payment_card_holder'),
        'support_contact': payload.get('support_contact'),
        'support_phone': payload.get('support_phone'),
        'support_telegram': payload.get('support_telegram'),
        'default_delivery_fee': payload.get('delivery_fee') or payload.get('default_delivery_fee'),
    }
    for key, val in mapping.items():
        if val is not None and str(val).strip() != '':
            BotSetting.set(key, val)


def _tg_id_from_request(request):
    return request.GET.get('tg_id') or request.POST.get('tg_id')


def _get_user_or_none(tg_id):
    if not tg_id:
        return None
    try:
        return TelegramUser.objects.get(user_id=str(tg_id))
    except TelegramUser.DoesNotExist:
        return None


def _order_timeline(status: str) -> list:
    steps = [
        {'key': 'received', 'label': "Buyurtma qabul qilindi", 'icon': '📋'},
        {'key': 'courier', 'label': "Kuryer yo'lda", 'icon': '🚚'},
        {'key': 'sample', 'label': 'Namuna olindi', 'icon': '🧪'},
        {'key': 'lab', 'label': 'Laboratoriyada', 'icon': '🔬'},
        {'key': 'result', 'label': 'Natija tayyor', 'icon': '✅'},
    ]
    status_index = {
        'pending': 0,
        'paid': 1,
        'delivering': 1,
        'done': 2,
        'result_pending': 3,
        'result_sent': 4,
        'canceled': -1,
    }
    current = status_index.get(status, 0)
    if status == 'canceled':
        for s in steps:
            s['state'] = 'cancelled'
        return steps

    for i, s in enumerate(steps):
        if i < current:
            s['state'] = 'done'
        elif i == current:
            s['state'] = 'active'
        else:
            s['state'] = 'pending'
    return steps


def webapp_view(request):
    user_lang = request.GET.get('lang')
    if user_lang in ('uz', 'ru', 'en'):
        translation.activate(user_lang)
        request.LANGUAGE_CODE = user_lang
    return render(request, 'webapp/app.html')


@csrf_exempt
def webapp_public_settings_api(request):
    """GET — to'lov kartasi va qo'llab-quvvatlash (ochiq)."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Faqat GET'}, status=405)
    s = _get_settings_dict()
    return JsonResponse({
        'payment_card_number': s['payment_card_number'],
        'payment_card_holder': s['payment_card_holder'],
        'support_contact': s['support_contact'],
        'support_phone': s['support_phone'],
        'support_telegram': s['support_telegram'],
        'default_delivery_fee': float(s.get('default_delivery_fee') or 0),
    })


@csrf_exempt
def webapp_profile_api(request):
    tg_id = _tg_id_from_request(request)
    user = _get_user_or_none(tg_id)
    if not user:
        return JsonResponse({'error': 'Foydalanuvchi topilmadi'}, status=404)

    orders = Order.objects.filter(user__user_id=tg_id)
    total = orders.count()
    completed = orders.filter(status__in=('done', 'result_pending', 'result_sent')).count()
    cycle_pos = user.order_count % 6
    next_free = 6 - cycle_pos if cycle_pos else 6

    return JsonResponse({
        'patient_id': user.patient_id,
        'first_name': user.first_name or '',
        'username': user.username or '',
        'lang': user.lang or 'uz',
        'bonus_points': user.bonus_points,
        'order_count': user.order_count,
        'total_orders': total,
        'completed_orders': completed,
        'cycle_position': cycle_pos,
        'next_free_in': next_free,
        'date_joined': user.date_joined.strftime('%Y-%m-%d') if user.date_joined else '',
        'phone': user.phone or user.phone_number or '',
    })


@csrf_exempt
def webapp_orders_api(request):
    tg_id = _tg_id_from_request(request)
    if not tg_id:
        return JsonResponse({'error': 'tg_id talab qilinadi'}, status=400)

    orders = (
        Order.objects
        .filter(user__user_id=tg_id)
        .select_related('service', 'district', 'payment')
        .order_by('-created_at')[:20]
    )

    result = []
    for o in orders:
        pay_status = ''
        try:
            pay_status = o.payment.status
        except Exception:
            pass

        result.append({
            'id': o.id,
            'order_code': f'NMED-{o.id:05d}',
            'service_name': o.service.name_uz if o.service else '—',
            'patient_name': o.patient_name or '',
            'total_price': float(o.total_price or 0),
            'status': o.status,
            'payment_status': pay_status,
            'district_name': o.district.name if o.district else '',
            'pickup_slot': o.pickup_slot or '',
            'created_at': o.created_at.strftime('%Y-%m-%d %H:%M') if o.created_at else '',
            'timeline': _order_timeline(o.status),
            'has_result': hasattr(o, 'test_result') and bool(getattr(o.test_result, 'result_file', None)),
        })

    return JsonResponse(result, safe=False)


@csrf_exempt
def webapp_order_detail_api(request, order_id):
    tg_id = _tg_id_from_request(request)
    try:
        o = (
            Order.objects
            .select_related('service', 'district', 'payment', 'test_result')
            .get(pk=order_id, user__user_id=tg_id)
        )
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Buyurtma topilmadi'}, status=404)

    tr = getattr(o, 'test_result', None)
    result_url = ''
    if tr and tr.result_file:
        try:
            result_url = tr.result_file.url
        except Exception:
            result_url = str(tr.result_file)

    return JsonResponse({
        'id': o.id,
        'order_code': f'NMED-{o.id:05d}',
        'service_name': o.service.name_uz if o.service else '—',
        'patient_name': o.patient_name,
        'patient_age': o.patient_age,
        'total_price': float(o.total_price or 0),
        'status': o.status,
        'address_note': o.address_note or '',
        'district_name': o.district.name if o.district else '',
        'pickup_slot': o.pickup_slot or '',
        'created_at': o.created_at.strftime('%Y-%m-%d %H:%M') if o.created_at else '',
        'timeline': _order_timeline(o.status),
        'result_url': result_url,
        'doctor_conclusion': tr.doctor_conclusion if tr else '',
    })


@csrf_exempt
def webapp_results_api(request):
    tg_id = _tg_id_from_request(request)
    if not tg_id:
        return JsonResponse({'error': 'tg_id talab qilinadi'}, status=400)

    qs = (
        TestResult.objects
        .filter(order__user__user_id=tg_id, result_file__isnull=False)
        .exclude(result_file='')
        .select_related('order', 'order__service')
        .order_by('-created_at')[:15]
    )

    items = []
    for tr in qs:
        url = ''
        try:
            url = tr.result_file.url
        except Exception:
            url = str(tr.result_file)
        items.append({
            'order_id': tr.order_id,
            'order_code': f'NMED-{tr.order_id:05d}',
            'service_name': tr.order.service.name_uz if tr.order.service else '—',
            'created_at': tr.created_at.strftime('%Y-%m-%d') if tr.created_at else '',
            'doctor_conclusion': tr.doctor_conclusion or '',
            'result_url': url,
            'file_name': tr.result_file.name.split('/')[-1] if tr.result_file else '',
        })

    return JsonResponse(items, safe=False)


@csrf_exempt
def webapp_appeal_api(request):
    """POST — fikr va taklif."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Faqat POST'}, status=405)

    try:
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body)
        else:
            data = request.POST
        tg_id = data.get('tg_id')
        message = (data.get('message') or '').strip()
        if not tg_id or not message:
            return JsonResponse({'error': 'tg_id va xabar talab qilinadi'}, status=400)

        user = _get_user_or_none(tg_id)
        if not user:
            return JsonResponse({'error': 'Foydalanuvchi topilmadi'}, status=404)

        Appeal.objects.create(user=user, message=message)
        return JsonResponse({'success': True})
    except Exception as e:
        logger.exception('Appeal xatosi: %s', e)
        return JsonResponse({'error': str(e)}, status=400)


def get_admin_settings_response():
    s = _get_settings_dict()
    return {
        'bot_status': True,
        'maintenance_mode': False,
        'delivery_fee': float(s.get('default_delivery_fee') or 0),
        'support_contact': s.get('support_contact', ''),
        'support_phone': s.get('support_phone', ''),
        'support_telegram': s.get('support_telegram', ''),
        'payment_card_number': s.get('payment_card_number', ''),
        'payment_card_holder': s.get('payment_card_holder', ''),
    }


def save_admin_settings_from_request(data: dict):
    _save_settings_dict(data)
