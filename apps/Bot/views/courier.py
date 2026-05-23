import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny

# Modellaringizni loyihangizga qarab import qiling
from apps.Bot.models.TelegramBot import TelegramUser
from apps.Bot.models.orders import Order

def courier_panel_view(request):
    """Kuryer paneli HTML sahifasini yuklash"""
    return render(request, 'courier_panel.html')



@csrf_exempt
@api_view(['GET'])
@authentication_classes([])  # 401 xatosini yo'qotish uchun standart tekshiruvlarni o'chiramiz
@permission_classes([AllowAny]) # Istalgan foydalanuvchiga API dan foydalanishga ruxsat beramiz
def courier_staff_me_api(request):
    tg_id = request.GET.get('tg_id')
    if not tg_id:
        return JsonResponse({'error': 'tg_id talab qilinadi'}, status=400)
    
    try:
        user = TelegramUser.objects.get(user_id=tg_id)
        role = getattr(user, 'role', 'user')
        # Tuman ob'ektining o'zidan nomini olamiz
        district_obj = getattr(user, 'district', None) or getattr(user, 'region', None)
        region_name = district_obj.name if district_obj else None
        
        return JsonResponse({
            'role': role,
            'tg_id': tg_id,
            'regionName': region_name
        })
    except TelegramUser.DoesNotExist:
        return JsonResponse({'role': 'courier', 'tg_id': tg_id, 'regionName': "Topilmadi"}, status=200)  # Test rejimida default courier rolini qaytaramiz


@csrf_exempt
def courier_orders_api(request):
    # Faqat GET so'rovlarini qabul qilamiz
    if request.method != 'GET':
        return JsonResponse({'error': 'Faqat GET so\'rovi ruxsat etilgan'}, status=405)

    tg_id = request.GET.get('tg_id')
    if not tg_id:
        return JsonResponse({'error': 'tg_id talab qilinadi'}, status=400)

    # Buyurtmalarni olish logikasi
    orders = Order.objects.filter(status__in=['approved', 'courier_done']).order_by('-created_at')

    orders_list = []
    for o in orders:
        phone = getattr(o, 'patient_phone', '') or getattr(o, 'phone', '')
        address_note = getattr(o, 'address_note', '') or getattr(o, 'address', '')
        
        district_name = "Noma'lum tuman"
        if getattr(o, 'district', None):
            district_name = o.district.name
        elif getattr(o, 'region', None):
            district_name = o.region.name

        combined_address = f"{address_note} | Tel: {phone}" if phone else address_note

        orders_list.append({
            "orderId": str(o.id),
            "patientName": getattr(o, 'patient_name', 'Noma\'lum'),
            "patientAge": getattr(o, 'patient_age', ''),
            "districtName": district_name,
            "addressNote": combined_address,
            "deliverySlot": getattr(o, 'delivery_slot', None),
            "pickupSlot": getattr(o, 'pickup_slot', None),
            "latitude": float(o.latitude) if getattr(o, 'latitude', None) else None,
            "longitude": float(o.longitude) if getattr(o, 'longitude', None) else None,
            "status": o.status
        })

    # safe=False bu yerda massiv qaytarish imkonini beradi
    return JsonResponse(orders_list, safe=False)

@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def courier_order_done_api(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    try:
        order.status = 'courier_done'
        order.save()
        return JsonResponse({'success': True, 'message': 'Muvaffaqiyatli yangilandi.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)