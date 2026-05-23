import os
import json
import base64
import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from apps.Bot.models.TelegramBot import TelegramUser
from apps.Bot.models.orders import Order, TestResult

# ─── Konstantalar ─────────────────────────────────────────────────────────────
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB (bytes)
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'zip'}


# ─── HTML Panel ───────────────────────────────────────────────────────────────
def doctor_panel_view(request):
    """Shifokor paneli HTML sahifasini render qilish"""
    return render(request, 'doctor_panel.html')


# ─── Staff Me ─────────────────────────────────────────────────────────────────
@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def staff_me_api(request):
    """Xodimning rolini telegram ID orqali tekshirish"""
    tg_id = request.GET.get('tg_id')
    if not tg_id:
        return JsonResponse({'error': 'tg_id talab qilinadi'}, status=400)

    try:
        user = TelegramUser.objects.get(user_id=tg_id)
        role = getattr(user, 'role', 'user')
        return JsonResponse({'role': role, 'tg_id': tg_id})
    except TelegramUser.DoesNotExist:
        return JsonResponse({'error': 'Foydalanuvchi topilmadi', 'tg_id': tg_id}, status=404)


# ─── Doctor Orders ────────────────────────────────────────────────────────────
@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def doctor_orders_api(request):
    """
    Shifokor ko'rishi kerak bo'lgan buyurtmalar ro'yxati.
    Faqat 'result_pending' va 'result_sent' statusli buyurtmalar chiqadi.
    """
    tg_id = request.GET.get('tg_id')
    if not tg_id:
        return JsonResponse({'error': 'tg_id talab qilinadi'}, status=400)

    # Shifokor ko'rishi kerak bo'lgan statuslar:
    # result_pending → natija kutilmoqda (harakatli)
    # result_sent    → natija yuborildi (yakunlangan)
    orders = Order.objects.filter(
        status__in=['result_pending', 'result_sent']
    ).select_related('service', 'user').order_by('-created_at')

    orders_list = []
    for o in orders:
        service_name = None
        if o.service:
            service_name = o.service.name_uz  # yoki request tiliga qarab

        orders_list.append({
            "order_id":    str(o.id),
            "patientName": o.patient_name or "Noma'lum",
            "patientAge":  o.patient_age or 0,
            "patientType": o.patient_type or 'adult',
            "status":      o.status,
            "serviceName": service_name,
            "createdAt":   o.created_at.isoformat() if o.created_at else "",
        })

    return JsonResponse(orders_list, safe=False)


# ─── Upload Order Result ───────────────────────────────────────────────────────
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def upload_order_result_api(request, order_id):
    """
    Natija faylini qabul qilib:
    1. Hajm va kengaytmani tekshiradi (max 25 MB, faqat pdf/jpg/png/zip)
    2. TestResult modelida saqlaydi
    3. Order statusini 'result_sent' ga o'zgartiradi
    4. Bemorga Telegram orqali faylni yuboradi
    """
    order = get_object_or_404(Order, id=order_id)

    # Faqat result_pending buyurtmaga natija yuboriladi
    if order.status != 'result_pending':
        return JsonResponse(
            {'error': f"Bu buyurtmaning holati '{order.status}'. Faqat 'result_pending' buyurtmalarga natija yuboriladi."},
            status=400
        )

    tg_id = request.GET.get('tg_id')  # Natija yuborgan shifokorning tg_id si

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        return JsonResponse({'error': "JSON ma'lumotlarni o'qib bo'lmadi."}, status=400)

    file_base64 = data.get('file_base64', '')
    filename    = data.get('filename', 'tahlil_natijasi.pdf').strip()
    file_size   = data.get('file_size', 0)

    # ── 1. Validatsiya ──────────────────────────────────────────────────────────
    if not file_base64:
        return JsonResponse({'error': "Fayl ma'lumotlari topilmadi (file_base64 bo'sh)."}, status=400)

    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        return JsonResponse(
            {'error': f"Ruxsat etilmagan fayl turi: .{ext}. Faqat PDF, JPG, PNG yoki ZIP qabul qilinadi."},
            status=400
        )

    # ── 2. Base64 decode ─────────────────────────────────────────────────────────
    try:
        if ';base64,' in file_base64:
            _, imgstr = file_base64.split(';base64,', 1)
        else:
            imgstr = file_base64

        file_data = base64.b64decode(imgstr)
    except Exception:
        return JsonResponse({'error': "Fayl ma'lumotlarini dekodlab bo'lmadi."}, status=400)

    # ── 3. Hajm tekshiruvi (server tomonida ham) ────────────────────────────────
    if len(file_data) > MAX_FILE_SIZE:
        return JsonResponse({'error': "Fayl hajmi 25 MB dan oshmasligi kerak!"}, status=400)

    # ── 4. Faylni saqlash ─────────────────────────────────────────────────────────
    try:
        content_file = ContentFile(file_data, name=filename)

        # TestResult yaratamiz yoki mavjudini yangilaymiz
        doctor_user = None
        if tg_id:
            try:
                doctor_user = TelegramUser.objects.get(user_id=tg_id)
            except TelegramUser.DoesNotExist:
                pass

        test_result, created = TestResult.objects.get_or_create(
            order=order,
            defaults={'doctor': doctor_user}
        )
        if not created:
            test_result.doctor = doctor_user

        test_result.result_file = content_file
        test_result.status      = 'sent'
        test_result.save()

        # Order statusini yangilaymiz
        order.status = 'result_sent'
        order.save(update_fields=['status'])

    except Exception as e:
        return JsonResponse({'error': f"Faylni saqlashda xatolik: {str(e)}"}, status=500)

    # ── 5. Bemorga Telegram orqali yuborish ──────────────────────────────────────
    patient_tg_id = None
    if hasattr(order, 'user') and order.user:
        patient_tg_id = order.user.user_id
    elif hasattr(order, 'telegram_user') and order.telegram_user:
        patient_tg_id = order.telegram_user.user_id

    telegram_status = "yuborilmadi (tg_id topilmadi)"

    if patient_tg_id:
        BOT_TOKEN = getattr(settings, 'BOT_TOKEN', None) or os.getenv('BOT_TOKEN')

        if BOT_TOKEN:
            service_name = order.service.name_uz if order.service else "Tahlil"
            caption_text = (
                f"📊 *{service_name} natijangiz tayyor!*\n\n"
                f"👤 *Bemor:* {order.patient_name or 'Noma\'lum'}\n"
                f"🆔 *Buyurtma raqami:* #{order_id}\n"
                f"✅ *Holati:* Shifokor tomonidan tasdiqlandi.\n\n"
                f"🩺 Bizning xizmatimizdan foydalanganingiz uchun rahmat!"
            )

            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            try:
                tg_response = requests.post(
                    url,
                    data={
                        'chat_id':    patient_tg_id,
                        'caption':    caption_text,
                        'parse_mode': 'Markdown'
                    },
                    files={'document': (filename, file_data)},
                    timeout=20
                )
                tg_res_json = tg_response.json()
                if tg_res_json.get('ok'):
                    telegram_status = "muvaffaqiyatli yuborildi"
                else:
                    telegram_status = f"xatolik: {tg_res_json.get('description', 'noma\'lum')}"
                    print(f"[Telegram xatosi] {tg_res_json}")
            except requests.exceptions.Timeout:
                telegram_status = "timeout (15 soniya)"
                print("[Telegram] Timeout xatosi")
            except Exception as tg_err:
                telegram_status = f"exception: {str(tg_err)}"
                print(f"[Telegram] Ulana olmadi: {tg_err}")
        else:
            telegram_status = "BOT_TOKEN topilmadi"

    return JsonResponse({
        'success':         True,
        'message':         "Natija saqlandi va Telegram orqali yuborildi.",
        'order_id':        str(order_id),
        'new_status':      'result_sent',
        'telegram_status': telegram_status,
    })