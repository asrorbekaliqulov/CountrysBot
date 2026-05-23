import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny

from apps.Bot.models.TelegramBot import TelegramUser
from apps.Bot.models.orders import Order


def courier_panel_view(request):
    """Kuryer paneli HTML sahifasini yuklash"""
    return render(request, 'courier_panel.html')


@csrf_exempt
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def courier_staff_me_api(request):
    """Kuryer ma'lumotlarini qaytaradi"""
    tg_id = request.GET.get('tg_id')
    if not tg_id:
        return JsonResponse({'error': 'tg_id talab qilinadi'}, status=400)

    try:
        user = TelegramUser.objects.select_related('district').get(user_id=tg_id)
        role = getattr(user, 'role', 'user')
        district_obj = getattr(user, 'district', None)
        region_name = district_obj.name if district_obj else None

        return JsonResponse({
            'role': role,
            'tg_id': tg_id,
            'regionName': region_name,
            'firstName': user.first_name or '',
        })
    except TelegramUser.DoesNotExist:
        return JsonResponse({'role': 'courier', 'tg_id': tg_id, 'regionName': None, 'firstName': ''}, status=200)


@csrf_exempt
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def courier_orders_api(request):
    """
    Kuryer uchun zakazlar ro'yxati.
    Statuslar: 'paid' (To'langan), 'delivering' (Yo'lda), 'done' (Yetkazildi)
    """
    tg_id = request.GET.get('tg_id')
    if not tg_id:
        return JsonResponse({'error': 'tg_id talab qilinadi'}, status=400)

    orders = Order.objects.select_related('district', 'service').filter(
        status__in=['paid', 'delivering', 'done']
    ).order_by('-created_at')

    orders_list = []
    for o in orders:
        phone = getattr(o, 'patient_phone', '') or getattr(o, 'phone', '')
        if not phone and o.user:
            phone = o.user.phone or o.user.phone_number or ''

        address_note = getattr(o, 'address_note', '') or ''

        district_name = "Noma'lum tuman"
        if getattr(o, 'district', None):
            district_name = o.district.name

        service_name = ''
        if getattr(o, 'service', None):
            service_name = o.service.name_uz or ''

        total_price = float(o.total_price) if getattr(o, 'total_price', None) else None

        orders_list.append({
            "orderId": str(o.id),
            "patientName": getattr(o, 'patient_name', 'Noma\'lum') or "Noma'lum",
            "patientAge": getattr(o, 'patient_age', '') or '',
            "districtName": district_name,
            "addressNote": address_note,
            "phone": phone,
            "deliverySlot": getattr(o, 'delivery_slot', None),
            "pickupSlot": getattr(o, 'pickup_slot', None),
            "latitude": float(o.latitude) if getattr(o, 'latitude', None) else None,
            "longitude": float(o.longitude) if getattr(o, 'longitude', None) else None,
            "status": o.status,
            "serviceName": service_name,
            "totalPrice": total_price,
            "createdAt": o.created_at.strftime('%d.%m.%Y %H:%M') if o.created_at else '',
        })

    return JsonResponse(orders_list, safe=False)


@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def courier_order_start_delivery_api(request, order_id):
    """
    'paid' → 'delivering': Kuryer zakazni olib yo'lga chiqdi.
    Bemorga Telegram xabari yuboriladi.
    """
    order = get_object_or_404(Order, id=order_id)

    if order.status != 'paid':
        return JsonResponse({'error': f"Zakaz holati 'paid' emas, hozir: {order.status}"}, status=400)

    try:
        order.status = 'delivering'
        order.save()
        return JsonResponse({'success': True, 'message': 'Kuryer yo\'lga chiqdi. Bemor xabardor qilindi.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def courier_order_done_api(request, order_id):
    """
    'delivering' → 'done': Namuna olindi, kuryer laboratoriyaga qaytdi.
    Bemorga Telegram xabari yuboriladi.
    """
    order = get_object_or_404(Order, id=order_id)

    if order.status not in ['delivering', 'paid']:
        return JsonResponse({'error': f"Zakaz holati noto'g'ri: {order.status}"}, status=400)

    try:
        order.status = 'done'
        order.save()
        return JsonResponse({'success': True, 'message': 'Namuna olindi. Bemor xabardor qilindi.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)