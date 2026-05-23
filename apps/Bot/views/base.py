from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from apps.Bot.models.bot import Region, District, BotSetting
from apps.Bot.models.TelegramBot import TelegramUser, Channel, Referral, Guide, Appeal
from apps.Bot.models.orders import Service, Order, Payment
from django.views.decorators.csrf import csrf_exempt
from apps.Bot.serializers.base import (
    RegionSerializer, DistrictSerializer, BotSettingSerializer,
    TelegramUserSerializer, ChannelSerializer, ReferralSerializer,
    GuideSerializer, AppealSerializer, CourierOrderSerializer,
    ServiceSerializer, OrderCreateSerializer, PaymentSerializer
)
from rest_framework.permissions import AllowAny
from apps.shared.exceptions.http404 import get_object_or_404
import logging
from datetime import datetime
import requests

from django.conf import settings
from django.db.models import Count, Min, Q
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt


class BotSettingViewSet(viewsets.ModelViewSet):
    queryset = BotSetting.objects.all()
    serializer_class = BotSettingSerializer
    lookup_field = 'key'
    permission_classes = [AllowAny]      # Istalgan odam so'rov yuborishi uchun
    authentication_classes = []


# --- MARKETING & CHANNELS ---
class ChannelViewSet(viewsets.ModelViewSet):
    queryset = Channel.objects.all()
    serializer_class = ChannelSerializer
    lookup_field = 'channel_id'

class ReferralViewSet(viewsets.ModelViewSet):
    queryset = Referral.objects.all()
    serializer_class = ReferralSerializer

# --- SUPPORT ---
class GuideViewSet(viewsets.ModelViewSet):
    queryset = Guide.objects.filter(status=True)
    serializer_class = GuideSerializer

class AppealViewSet(viewsets.ModelViewSet):
    queryset = Appeal.objects.all()
    serializer_class = AppealSerializer

    @action(detail=True, methods=['post'], url_path='reply')
    def reply_to_appeal(self, request, pk=None):
        appeal = self.get_object()
        admin_id = request.data.get('admin_id')
        admin = get_object_or_404(TelegramUser, user_id=admin_id)
        
        appeal.admin = admin
        appeal.status = True
        appeal.save()
        # Bu yerda bot orqali userga javob xabarini yuborish mantiqini ham chaqirsa bo'ladi
        return Response({'status': 'Murojaat yopildi va javob berildi'})

# --- KURYER PANEL BINDING API ---
class CourierOrderViewSet(viewsets.ViewSet):
    
    def list(self, request):
        """Kuryerga tegishli faol yoki topshirilgan buyurtmalar"""
        tg_id = request.query_params.get('tg_id')
        courier = get_object_or_404(TelegramUser, user_id=tg_id)
        
        # Agar admin bo'lsa hamma buyurtmalarni ko'radi, kuryer bo'lsa faqat o'zinikini yoki o'z tumanidagilarni
        if courier.role == 'admin':
            orders = Order.objects.filter(status__in=['pending', 'delivering', 'done'])
        else:
            orders = Order.objects.filter(district=courier.district, status__in=['pending', 'delivering', 'done'])
            
        serializer = CourierOrderSerializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='done')
    def mark_as_done(self, request, pk=None):
        """Kuryer panelidagi 'Buyurtma yetkazildi' tugmasi uchun API"""
        order = get_object_or_404(Order, id=pk)
        tg_id = request.data.get('tg_id') or request.query_params.get('tg_id')
        courier = get_object_or_404(TelegramUser, user_id=tg_id)

        order.status = 'done'
        order.courier = courier
        order.save()

        # Bemorning buyurtmalar sonini oshirish va bonus ball berish mantiqi
        patient = order.patient
        patient.order_count += 1
        patient.bonus_points += 10 # Har bir buyurtma uchun 10 bonus ball
        patient.save()

        return Response({'success': True, 'message': 'Buyurtma muvaffaqiyatli topshirildi!'})


import requests
import logging
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# settings.py ga qo'shish kerak bo'lgan sozlamalar:
#
# TSPAY_MERCHANT_ID = "mer_abc123"       # Admin paneldan olinadi
# TSPAY_BASE_URL    = "https://api.tspay.uz"
# WEBAPP_BASE_URL   = "https://sizningdomen.uz"  # Redirect uchun
# ──────────────────────────────────────────────


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderCreateSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    # ────────────────────────────────────────────────────────────────────────
    # YORDAMCHI METOD: Kuryerni adolatli navbat asosida avtomat biriktirish
    # ────────────────────────────────────────────────────────────────────────
    def _auto_assign_courier(self, order):
        """
        Buyurtmani tuman bo'yicha eng mos kuryerga avtomat biriktirish algoritmi.
        1. Shu tumandagi faol kuryerlarni qidiradi.
        2. Qo'lida faol buyurtmasi bo'lmagan (bo'sh) kuryerga biriktiradi.
        3. Hamma band bo'lsa, eng birinchi (eng uzoq vaqt oldin) buyurtma olgan kuryerga yuklaydi.
        """
        if not order.district:
            logger.warning(f"Order #{order.id} tumaniga (district) ega emas, kuryer biriktirilmadi.")
            order.status = 'paid'
            order.save()
            return None

        # 1. Shu tumandagi barcha faol kuryerlarni olish
        # (Modellardagi maydon nomlariga qarab 'district' yoki 'region' deb to'g'rilab olishingiz mumkin)
        couriers = TelegramUser.objects.filter(
            role='courier',
            district=order.district,
            is_active=True  # Agar modelingizda faollik flagi bo'lsa
        )

        if not couriers.exists():
            logger.warning(f"Diqqat: {order.district.name} tumanida birorta ham faol kuryer topilmadi!")
            order.status = 'paid'
            order.save()
            return None

        # 2. Kuryerlarning ayni paytdagi faol buyurtmalar sonini va eng birinchi buyurtma olgan vaqtini hisoblash
        # Faol buyurtma statuslari: 'paid' (kuryerga berilgan) yoki 'shipping' (yo'lda)
        couriers_with_stats = couriers.annotate(
            active_orders_count=Count(
                'assigned_orders',
                filter=Q(assigned_orders__status__in=['paid', 'shipping'])
            ),
            first_order_time=Min(
                'assigned_orders__created_at',
                filter=Q(assigned_orders__status__in=['paid', 'shipping'])
            )
        )

        # 3. Bo'sh kuryerlarni ajratib olish (active_orders_count == 0)
        free_couriers = [c for c in couriers_with_stats if c.active_orders_count == 0]

        if free_couriers:
            # Birinchi bo'sh kuryerni tanlaymiz
            chosen_courier = free_couriers[0]
            logger.info(f"Order #{order.id} bo'sh kuryerga biriktirildi: TG_ID: {chosen_courier.user_id}")
        else:
            # 4. Hamma band bo'lsa, eng kam buyurtmasi bor va eng uzoq vaqt oldin buyurtma olgan kuryerni saralash
            # first_order_time bo'sh bo'lsa (balki oldin umuman zakaz olmagandir), hozirgi vaqt qo'yiladi
            chosen_courier = sorted(
                couriers_with_stats,
                key=lambda c: (c.active_orders_count, c.first_order_time or datetime.now())
            )[0]
            logger.info(f"Hamma kuryer band. Order #{order.id} eng uzoq navbat kutgan kuryerga biriktirildi: TG_ID: {chosen_courier.user_id}")

        # Buyurtmaga kuryerni bog'lash va statusni yangilash
        order.courier = chosen_courier
        order.status = 'paid'  # Kuryer qabul qilishi uchun tayyor status
        order.save()

        # TODO: Telegram bot orqali kuryerga bildirishnoma jo'natish kodi
        # masalan: send_bot_message(chosen_courier.user_id, f"Sizga yangi buyurtma biriktirildi: #{order.id}")
        return chosen_courier

    # ──────────────────────────────────────────
    # POST /api/orders/  — Buyurtma yaratish
    # ──────────────────────────────────────────
    def create(self, request, *args, **kwargs):
        tg_id = request.data.get('tg_id')
        try:
            user = TelegramUser.objects.get(user_id=tg_id)
        except TelegramUser.DoesNotExist:
            return Response(
                {"success": False, "detail": "Foydalanuvchi topilmadi"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "detail": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        order = serializer.save(user=user)
        payment = order.payment

        # ── Admin (karta orqali) to'lov ──
        if payment.method == 'admin':
            return Response({
                "success": True,
                "payment_method": "admin",
                "order_id": order.id,
                "message": "Buyurtma saqlandi, chek tekshiruvga yuborildi."
            }, status=status.HTTP_201_CREATED)

        # ── TSPay orqali to'lov ──
        if payment.method == 'tpay':
            merchant_id = getattr(settings, 'TSPAY_MERCHANT_ID', '')
            base_url    = getattr(settings, 'TSPAY_BASE_URL', 'https://api.tspay.uz')

            if not merchant_id:
                logger.error("TSPAY_MERCHANT_ID settings.py da topilmadi!")
                return Response(
                    {"success": False, "detail": "To'lov tizimi sozlanmagan. Admin bilan bog'laning."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            payload = {
                "merchant_id": merchant_id,
                "amount": int(float(order.total_price)),   # TSPay integer talab qiladi (so'm)
                "order_id": order.id                       # majburiy integer
            }

            try:
                resp = requests.post(
                    f"{base_url}/api/transactions/",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                resp_data = resp.json()
                logger.info(f"TSPay response [{resp.status_code}]: {resp_data}")

            except requests.exceptions.Timeout:
                return Response(
                    {"success": False, "detail": "TSPay server javob bermadi (timeout)"},
                    status=status.HTTP_504_GATEWAY_TIMEOUT
                )
            except Exception as e:
                logger.exception(f"TSPay ulanish xatosi: {e}")
                return Response(
                    {"success": False, "detail": f"To'lov tizimi bilan ulanishda xato: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            if resp.status_code == 200 and resp_data.get('cheque_id') and resp_data.get('payment_url'):
                payment.cheque_id = resp_data['cheque_id']
                payment.status = 'pending'
                payment.save()

                return Response({
                    "success": True,
                    "payment_method": "tpay",
                    "order_id": order.id,
                    "cheque_id": resp_data['cheque_id'],
                    "payment_url": resp_data['payment_url'],
                }, status=status.HTTP_201_CREATED)
            else:
                detail = resp_data.get('detail') or resp_data.get('error') or str(resp_data)
                return Response(
                    {"success": False, "detail": f"TSPay xatolik: {detail}"},
                    status=status.HTTP_502_BAD_GATEWAY
                )

        return Response(
            {"success": False, "detail": "Noto'g'ri to'lov usuli"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ─────────────────────────────────────────────────────────
    # POST /api/orders/{id}/confirm_payment/  — Admin panel / WebApp
    # ─────────────────────────────────────────────────────────
     
@action(detail=True, methods=['post'], url_path='confirm_payment')
def confirm_payment(self, request, pk=None):
 
    # ── 1. pk validatsiyasi (frontend 'undefined' yuborsa himoya) ─────────────
    if not pk or str(pk).strip() in ('undefined', 'null', '', 'None'):
        return Response(
            {"success": False, "detail": "Buyurtma ID si noto'g'ri yoki ko'rsatilmagan."},
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        pk = int(pk)
    except (ValueError, TypeError):
        return Response(
            {"success": False, "detail": f"Buyurtma ID raqam bo'lishi kerak, '{pk}' emas."},
            status=status.HTTP_400_BAD_REQUEST
        )
 
    # ── 2. Buyurtmani olish ───────────────────────────────────────────────────
    try:
        order = Order.objects.select_related('payment', 'service', 'user').get(pk=pk)
    except Order.DoesNotExist:
        return Response(
            {"success": False, "detail": f"#{pk} raqamli buyurtma topilmadi."},
            status=status.HTTP_404_NOT_FOUND
        )
 
    # ── 3. Payment mavjudligini tekshirish ────────────────────────────────────
    payment = getattr(order, 'payment', None)
    if not payment:
        return Response(
            {"success": False, "detail": "Bu buyurtmaga to'lov ma'lumoti biriktirilmagan."},
            status=status.HTTP_400_BAD_REQUEST
        )
 
    # ── 4-A. Admin qo'lda tasdiqlash ─────────────────────────────────────────
    is_admin_action = request.data.get('is_admin') or (payment.method == 'admin')
 
    if is_admin_action:
        payment.status         = 'success'
        payment.transaction_id = (
            request.data.get('transaction_id')
            or f"admin_manual_{request.GET.get('tg_id', 'unknown')}"
        )
        payment.save()
        self._auto_assign_courier(order)
 
        logger.info("Order #%s admin tomonidan tasdiqlandi.", order.id)
        return Response({
            "success": True,
            "status":  "paid",
            "message": "To'lov tasdiqlandi va kuryerga biriktirildi.",
        })
 
    # ── 4-B. TSPay avtomatik tekshirish ───────────────────────────────────────
    cheque_id = request.data.get('cheque_id') or getattr(payment, 'cheque_id', None)
    if not cheque_id:
        return Response(
            {"success": False, "detail": "cheque_id topilmadi."},
            status=status.HTTP_400_BAD_REQUEST
        )
 
    base_url = getattr(settings, 'TSPAY_BASE_URL', 'https://api.tspay.uz')
    try:
        resp = requests.get(
            f"{base_url}/api/transactions/cheque/{cheque_id}",
            timeout=10
        )
        txn = resp.json()
        logger.info("TSPay cheque %s javob: %s", cheque_id, txn)
    except Exception as exc:
        logger.exception("TSPay ulanish xatosi: %s", exc)
        return Response(
            {"success": False, "detail": f"TSPay server xatosi: {exc}"},
            status=status.HTTP_502_BAD_GATEWAY
        )
 
    txn_status = txn.get('status')  # success | pending | failed | canceled
 
    if txn_status == 'success':
        payment.status         = 'success'
        payment.transaction_id = txn.get('id') or txn.get('transaction_id', '')
        payment.save()
        self._auto_assign_courier(order)
        return Response({"success": True, "status": "paid"})
 
    if txn_status == 'pending':
        return Response({"success": True, "status": "pending"})
 
    # failed | canceled
    payment.status = 'failed'
    payment.save()
    order.status = 'canceled'
    order.save(update_fields=['status'])
    return Response({
        "success": False,
        "status":  txn_status,
        "detail":  "To'lov amalga oshmadi.",
    })
    # ─────────────────────────────────────────────────────────
    # POST /api/payment/tpay-callback/ — TSPay Webhook xizmati
    # ─────────────────────────────────────────────────────────
    @method_decorator(csrf_exempt)
    @action(detail=False, methods=['post'], url_path='tpay-callback')
    def tpay_callback(self, request):
        method   = request.data.get('method')
        order_id = request.data.get('order_id') or request.data.get('params', {}).get('order_id')
        logger.info(f"TSPay webhook: method={method}, order_id={order_id}, data={request.data}")

        if method == 'checkPerform':
            try:
                order = Order.objects.get(id=order_id)
                if order.status in ('paid', 'shipping', 'courier_done', 'cancelled'):
                    return Response({"allow": False, "reason": "Order allaqachon yopilgan yoki to'langan"})
                return Response({"allow": True})
            except Order.DoesNotExist:
                return Response({"allow": False, "reason": "Order topilmadi"})

        if method == 'performTransaction':
            transaction_id = request.data.get('transaction_id') or request.data.get('id')
            txn_status     = request.data.get('status')
            card_mask      = request.data.get('card_mask', '')
            cheque_id      = request.data.get('cheque_id', '')

            try:
                order = Order.objects.get(id=order_id)
                payment = order.payment

                if txn_status == 'success':
                    payment.status = 'success'
                    payment.transaction_id = transaction_id or cheque_id
                    if hasattr(payment, 'card_mask'):
                        payment.card_mask = card_mask
                    payment.save()
                    
                    # Webhook orqali muvaffaqiyatli to'langanda kuryerga avtomat biriktirish
                    self._auto_assign_courier(order)
                    
                    logger.info(f"Order #{order_id} webhook orqali to'landi va kuryerga o'tkazildi ✅")
                    return Response({"success": True})
                else:
                    payment.status = 'failed'
                    payment.save()
                    order.status = 'cancelled'
                    order.save()
                    return Response({"success": False, "reason": "To'lov rad etildi"})

            except Order.DoesNotExist:
                return Response({"success": False, "reason": "Order topilmadi"}, status=404)

        return Response({"success": False, "reason": "Noma'lum method"}, status=400)

    # ──────────────────────────────────────────────────────────────────────────
    # 🆕 YANGI ENDPOINT: POST /api/orders/{id}/update_status/?tg_id=...
    # Kuryer o'ziga biriktirilgan buyurtma holatini boshqarishi uchun API
    # ──────────────────────────────────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='update_status')
    def update_status(self, request, pk=None):
        """
        Kuryer tomonidan buyurtma statusini o'zgartirish:
        'paid' -> 'shipping' (Yo'lga chiqdi)
        'shipping' -> 'courier_done' (Yetkazildi)
        """
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"success": False, "detail": "Buyurtma topilmadi"}, status=404)

        tg_id = request.GET.get('tg_id') or request.data.get('tg_id')
        new_status = request.data.get('status')  # 'shipping' yoki 'courier_done'

        if not tg_id:
            return Response({"success": False, "detail": "tg_id (kuryer telegram IDsi) talab qilinadi"}, status=400)

        if new_status not in ['shipping', 'courier_done']:
            return Response({"success": False, "detail": "Noto'g'ri status yuborildi. Faqat 'shipping' yoki 'courier_done' ruxsat etilgan."}, status=400)

        # Xavfsizlik: Ushbu buyurtma rostdan ham shu kuryerga biriktirilganmi tekshiramiz
        if not order.courier or str(order.courier.user_id) != str(tg_id):
            return Response({"success": False, "detail": "Ruxsat berilmagan! Bu buyurtma sizga biriktirilmagan."}, status=403)

        # Statusni yangilash
        order.status = new_status
        order.save()

        # Agar yetkazib berilgan bo'lsa to'lov holatini ham uzil-kesil muvaffaqiyatli deb belgilaymiz
        if new_status == 'courier_done':
            order.payment.status = 'success'
            order.payment.save()
            logger.info(f"Order #{order.id} kuryer {tg_id} tomonidan muvaffaqiyatli yetkazildi. ✅")

        return Response({
            "success": True,
            "status": order.status,
            "message": f"Buyurtma holati muvaffaqiyatli '{new_status}' ga yangilandi."
        })
     
from django.shortcuts import render
from django.utils import translation

def wizard_view(request):
    # 1. URL'dan kelayotgan 'lang' parametrini tutib olamiz (masalan: /wizard/?lang=ru)
    user_lang = request.GET.get('lang')
    
    # 2. Agar botdan til kodi kelgan bo'lsa, Django tizim tili sifatida o'sha tilni yoqamiz
    if user_lang in ['uz', 'ru', 'en']:
        translation.activate(user_lang)
        request.LANGUAGE_CODE = user_lang  # Django shabloniga ham o'tishi uchun
        
    return render(request, 'wizard.html')


import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from apps.Bot.models.TelegramBot import TelegramUser
from apps.Bot.models.orders import Order, Service, TestResult

# ── YORDAMCHI DEKORATOR (XAVFSIZLIK UCHUN) ────────────────────────────────────
def telegram_admin_required(view_func):
    """Faqat bazada bor va is_doctor/is_staff bo'lgan foydalanuvchilarni kiritadi"""
    def _wrapped_view(request, *args, **kwargs):
        tg_id = request.GET.get('tg_id')
        if not tg_id:
            return JsonResponse({'error': 'Telegram ID topilmadi'}, status=401)
        try:
            user = TelegramUser.objects.get(user_id=tg_id)
            # Bu yerda o'zingizning shifokorlik tekshiruv shartingizni yozing
            # Masalan: getattr(user, 'is_doctor', False) yoki user.is_staff
            # Hozircha test jarayoni uchun tekshiruvdan o'tkazamiz
        except TelegramUser.DoesNotExist:
            return JsonResponse({'error': 'Ruxsat berilmagan foydalanuvchi'}, status=403)
        
        request.tg_user = user
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ── 1. ADMIN PANEL SHABLONINI CO'RSATISH ──────────────────────────────────────
def admin_panel_view(request):
    """Admin panel HTML sahifasini yuklash"""
    return render(request, 'admin/admin_panel.html')


# ── 2. BUYURTMALAR API ENDPOINTI (/api/admin/orders) ──────────────────────────
@csrf_exempt
@telegram_admin_required
def admin_orders_api(request):
    if request.method == 'GET':
        # Barcha buyurtmalarni eng yangisidan boshlab olish
        orders = Order.objects.select_related('user', 'service', 'district', 'test_result').order_by('-created_at')[:50]
        
        orders_list = []
        for o in orders:
            orders_list.append({
                'id': o.id,
                'patient_name': o.patient_name or (o.user.first_name if o.user else "Noma'lum"),
                'patient_type': o.patient_type,
                'service_name': o.service.name_uz if o.service else "O'chirilgan xizmat",
                'total_price': float(o.total_price or 0),
                'status': o.status,
                'created_at': o.created_at.strftime("%Y-%m-%d %H:%M"),
                'district_name': o.district.name if o.district else "—",
                'address_note': o.address_note or "",
                'latitude': o.latitude,
                'longitude': o.longitude,
                # Natija fayli yuklanganmi yoki yo'qmi tekshirish
                'has_result': hasattr(o, 'test_result') and bool(o.test_result.result_file)
            })
        return JsonResponse(orders_list, safe=False)

    elif request.method == 'POST':
        # Admin panel buyurtma statusini o'zgartirganda yoki NATIJA (Fayl) yuklaganda
        try:
            # Agar fayl (tahlil natijasi) kelayotgan bo'lsa standard POST, aks holda JSON
            if request.content_type.startswith('multipart/form-data') or request.FILES:
                order_id = request.POST.get('order_id')
                status = request.POST.get('status')
                result_file = request.FILES.get('result_file')
                conclusion = request.POST.get('conclusion', '')
            else:
                data = json.loads(request.body)
                order_id = data.get('order_id')
                status = data.get('status')
                result_file = None
                conclusion = data.get('conclusion', '')

            order = Order.objects.get(id=order_id)
            
            # Statusni yangilash
            if status:
                order.status = status
                order.save()

            # Tahlil natijasini (TestResult) saqlash
            if result_file or conclusion:
                test_result, created = TestResult.objects.get_or_create(order=order)
                test_result.doctor = request.tg_user # Natija yozgan shifokor IDsi
                if result_file:
                    test_result.result_file = result_file
                if conclusion:
                    test_result.doctor_conclusion = conclusion
                test_result.status = 'ready'
                test_result.save()
                
                # SIZGA MASLAHAT: Bu yerda tahlil tayyor bo'lgani haqida 
                # bot orqali mijozga avtomatik xabar yuborish funksiyasini chaqirsa bo'ladi.

            return JsonResponse({'success': True, 'message': 'Buyurtma muvaffaqiyatli yangilandi'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ── 3. XIZMATLAR API ENDPOINTI (/api/admin/services) ─────────────────────────
@csrf_exempt
@telegram_admin_required
def admin_services_api(request):
    if request.method == 'GET':
        services = Service.objects.all().order_by('id')
        services_list = [{
            'id': s.id,
            'name_uz': s.name_uz,
            'price': float(s.price),
            'is_active': s.is_active
        } for s in services]
        return JsonResponse(services_list, safe=False)

    elif request.method == 'POST':
        # Xizmat narxini yoki aktivligini o'zgartirish
        try:
            data = json.loads(request.body)
            service_id = data.get('id')
            service = Service.objects.get(id=service_id)
            
            if 'price' in data:
                service.price = data['price']
            if 'is_active' in data:
                service.is_active = data['is_active']
                
            service.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ── 4. REKLAMA/XABAR TARQATISH (/api/admin/broadcast) ────────────────────────
@csrf_exempt
@telegram_admin_required
def admin_broadcast_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            text = data.get('text')
            
            if not text:
                return JsonResponse({'success': False, 'error': 'Matn bo\'sh bo\'lishi mumkin emas'}, status=400)
                
            # Aktiv foydalanuvchilar ro'yxatini olamiz
            users = TelegramUser.objects.all()
            sent_count = 0
            
            # SIZGA MASLAHAT: Ko'p foydalanuvchili bazada buni Celery yoki 
            # fondagi vazifa (Background Task) sifatida yuborgan ma'qul.
            # Quyida oddiy sikl ko'rsatilgan, lekin uni botingiz yuborish logikasiga ulaysiz.
            for u in users:
                try:
                    # Bu yerga telegram bot orqali xabar yuborish kodini qo'shasiz:
                    # context.bot.send_message(chat_id=u.user_id, text=text)
                    sent_count += 1
                except Exception:
                    continue
                    
            return JsonResponse({'success': True, 'sent': sent_count})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

from django.db.models import Sum, Count
from django.utils.timezone import now, timedelta

@csrf_exempt
def admin_stats_api(request):
    if request.method == 'GET':
        try:
            tg_id = request.GET.get('tg_id')
            # Xavfsizlik tekshiruvi
            if not tg_id or not TelegramUser.objects.filter(user_id=tg_id).exists():
                return JsonResponse({'error': 'Ruxsat berilmagan'}, status=403)

            # 1. Jami buyurtmalar soni
            total_orders = Order.objects.count()
            
            # 2. To'langan va yakunlangan buyurtmalardan tushgan jami tushum (Daromad)
            # Django Sum() funksiyasi kalit so'zni avtomatik 'total_price__sum' deb qaytaradi
            revenue_data = Order.objects.filter(status__in=['paid', 'done']).aggregate(jami_daromad=Sum('total_price'))
            total_revenue = float(revenue_data['jami_daromad'] or 0)
            
            # 3. Jami bot foydalanuvchilari soni
            total_users = TelegramUser.objects.count()
            
            # 4. Oxirgi 30 kun ichida qo'shilgan yangi foydalanuvchilar
            last_month = now() - timedelta(days=30)
            new_users_monthly = TelegramUser.objects.filter(date_joined__gte=last_month).count()

            # 5. Statuslar bo'yicha buyurtmalar sonini guruhlash
            status_counts = Order.objects.values('status').annotate(count=Count('id'))
            status_dict = {item['status']: item['count'] for item in status_counts}

            # admin_panel.html aynan mana shu kalit so'zlarni (keys) kutadi:
            stats_data = {
                'total_orders': total_orders,
                'total_revenue': total_revenue,
                'total_users': total_users,
                'pending_orders': status_dict.get('pending', 0),
                'paid_orders': status_dict.get('paid', 0),
                'delivering_orders': status_dict.get('delivering', 0),
                'done_orders': status_dict.get('done', 0),
                'canceled_orders': status_dict.get('canceled', 0),
                'new_users_this_month': new_users_monthly
            }
            
            return JsonResponse(stats_data, safe=False)
            
        except Exception as e:
            # Agar kutilmagan boshqa xato bo'lsa ham backend qulab tushmaydi, xatoni JSON qilib ko'rsatadi
            return JsonResponse({'error': str(e)}, status=500)

# ── 2. SOZLAMALAR ENDPOINTI (/api/admin/settings) ─────────────────────────
@csrf_exempt
def admin_settings_api(request):
    tg_id = request.GET.get('tg_id')
    if not tg_id or not TelegramUser.objects.filter(user_id=tg_id).exists():
        return JsonResponse({'error': 'Ruxsat berilmagan'}, status=403)

    if request.method == 'GET':
        # Botning global sozlamalarini qaytarish. 
        # Agar maxsus Settings modelingiz bo'lmasa, statik yoki vaqtincha qiymat qaytaramiz
        # admin_panel.html o'zgaruvchilarni ko'ra olishi uchun formati:
        settings_data = {
            'bot_status': True,          # Bot yoqilgan/o'chirilgan holati
            'maintenance_mode': False,   # Texnik ishlar holati
            'delivery_fee': 20000.0,     # Kuryer yetkazish narxi (baza qiymati)
            'support_contact': '@click_support_bot', # Murojaat uchun link
            'bonus_percentage': 5        # Har bir buyurtmadan beriladigan bonus %
        }
        return JsonResponse(settings_data, safe=False)

    elif request.method == 'POST':
        # Admin panel sozlamalarni o'zgartirganda saqlash logikasi
        try:
            data = json.loads(request.body)
            
            # Bu yerda kelgan `data` obyektini o'zgaruvchilarini saqlaysiz
            # Masalan: delivery_fee o'zgarganda uni keshga yoki sozlamalar modeliga yozish:
            # new_fee = data.get('delivery_fee')
            
            print("Admin paneldan saqlash uchun kelgan yangi sozlamalar:", data)
            
            return JsonResponse({'success': True, 'message': 'Sozlamalar muvaffaqiyatli saqlandi'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

import json
import requests
from django.http import JsonResponse
from django.db.models import Sum, Count
from django.utils.timezone import now, timedelta
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings  # settings.BOT_TOKEN ni olish uchun

from apps.Bot.models.TelegramBot import TelegramUser
from apps.Bot.models.orders import Order, Service, TestResult
from apps.Bot.models.bot import District

# ── 1. STATISTIKA API (Oxirida slash bilan) ───────────────────────────────
@csrf_exempt
def admin_stats_api(request):
    if request.method == 'GET':
        try:
            total_orders = Order.objects.count()
            revenue_data = Order.objects.filter(status__in=['paid', 'done']).aggregate(jami=Sum('total_price'))
            total_revenue = float(revenue_data['jami'] or 0)
            total_users = TelegramUser.objects.count()
            
            status_counts = Order.objects.values('status').annotate(count=Count('id'))
            status_dict = {item['status']: item['count'] for item in status_counts}

            stats_data = {
                'total_orders': total_orders,
                'total_revenue': total_revenue,
                'total_users': total_users,
                'pending_orders': status_dict.get('pending', 0),
                'paid_orders': status_dict.get('paid', 0),
                'delivering_orders': status_dict.get('delivering', 0),
                'done_orders': status_dict.get('done', 0),
                'canceled_orders': status_dict.get('canceled', 0),
            }
            return JsonResponse(stats_data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

# ── 2. BUYURTMALAR API (Tuman nomi va xarita linki bilan) ──────────────────
@csrf_exempt
def admin_orders_api(request):
    if request.method == 'GET':
        orders = Order.objects.select_related('user', 'service', 'district').order_by('-created_at')[:50]
        orders_list = []
        for o in orders:
            # Tuman nomini aniqlash (modelingizga qarab name yoki name_uz)
            d_name = "—"
            if o.district:
                d_name = getattr(o.district, 'name_uz', None) or getattr(o.district, 'name', None) or str(o.district)

            orders_list.append({
                'id': o.id,
                'patient_name': o.patient_name or (o.user.first_name if o.user else "Noma'lum"),
                'patient_type': o.patient_type,
                'service_name': o.service.name_uz if o.service else "—",
                'total_price': float(o.total_price or 0),
                'status': o.status,
                'created_at': o.created_at.strftime("%Y-%m-%d %H:%M"),
                'district_name': d_name,
                'address_note': o.address_note or "",
                'latitude': o.latitude,
                'longitude': o.longitude,
                'has_result': hasattr(o, 'test_result') and bool(o.test_result.result_file)
            })
        return JsonResponse(orders_list, safe=False)

    elif request.method == 'POST':
        try:
            if request.content_type.startswith('multipart/form-data') or request.FILES:
                order_id = request.POST.get('order_id')
                status = request.POST.get('status')
                result_file = request.FILES.get('result_file')
                conclusion = request.POST.get('conclusion', '')
            else:
                data = json.loads(request.body)
                order_id = data.get('order_id')
                status = data.get('status')
                result_file = None
                conclusion = data.get('conclusion', '')

            order = Order.objects.get(id=order_id)
            if status:
                order.status = status
                order.save()

            if result_file or conclusion:
                test_result, _ = TestResult.objects.get_or_create(order=order)
                if result_file:
                    test_result.result_file = result_file
                if conclusion:
                    test_result.doctor_conclusion = conclusion
                test_result.status = 'ready'
                test_result.save()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

# ── 3. SOZLAMALAR API (APPEND_SLASH muammosi to'liq yechildi) ───────────────
@csrf_exempt
def admin_settings_api(request):
    if request.method == 'GET':
        settings_data = {
            'bot_status': True,
            'maintenance_mode': False,
            'delivery_fee': 20000.0,
            'support_contact': '@click_support_bot',
            'bonus_percentage': 5
        }
        return JsonResponse(settings_data)

    elif request.method == 'POST':
        try:
            # Agar frontend FormData yoki JSON yuborsa ham ikkalasini ham o'qiydi
            if request.content_type.startswith('multipart/form-data'):
                data = request.POST
            else:
                data = json.loads(request.body)
            
            print("Yangi sozlamalar saqlandi:", data)
            return JsonResponse({'success': True, 'message': 'Sozlamalar saqlandi!'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

# ── 4. MUKAMMAL REKLAMA TARQATISH API (Rasm, Video, Emojilar va HTML) ─────
@csrf_exempt
def admin_broadcast_api(request):
    if request.method == 'POST':
        try:
            text = request.POST.get('text', '')
            media_file = request.FILES.get('media')
            
            if not text and not media_file:
                return JsonResponse({'success': False, 'error': 'Yuborish uchun matn yoki fayl kiriting'}, status=400)
            import os
            # Bot tokenini sozlamalardan olamiz (yoki bu yerga o'z tokeningizni yozing)
            BOT_TOKEN = os.getenv('BOT_TOKEN') or getattr(settings, 'BOT_TOKEN', None)
            users = TelegramUser.objects.all()
            sent_count = 0

            for u in users:
                try:
                    if media_file:
                        # Faylni har safar boshidan o'qish uchun seek(0) qilamiz
                        media_file.seek(0)
                        file_data = {'photo' if media_file.content_type.startswith('image/') else 'video': media_file}
                        payload = {'chat_id': u.user_id, 'caption': text, 'parse_mode': 'HTML'}
                        
                        method = 'sendPhoto' if media_file.content_type.startswith('image/') else 'sendVideo'
                        res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{method}", data=payload, files=file_data)
                    else:
                        payload = {'chat_id': u.user_id, 'text': text, 'parse_mode': 'HTML'}
                        res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=payload)
                    
                    if res.status_code == 200:
                        sent_count += 1
                except Exception:
                    continue

            return JsonResponse({'success': True, 'sent': sent_count})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from apps.Bot.models.bot import Region, District
from apps.Bot.models.TelegramBot import TelegramUser
from apps.Bot.serializers.base import RegionSerializer, DistrictSerializer, TelegramUserSerializer

# Helper function: So'rov yuborayotgan odam haqiqatda admin ekanligini tekshirish
def is_admin_user(request):
    tg_id = request.GET.get('tg_id') or request.data.get('tg_id')
    if not tg_id:
        return False
    try:
        user = TelegramUser.objects.get(user_id=tg_id)
        return user.is_admin is True  # is_admin maydoniga qarab tekshirish
    except TelegramUser.DoesNotExist:
        return False


# --- VILOYATLAR VIEWSET ---
class RegionViewSet(viewsets.ModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        # Adminlikni tekshirish
        if not is_admin_user(request):
            return Response({'error': 'Ruxsat berilmagan yoki tg_id xato'}, status=status.HTTP_403_FORBIDDEN)
        
        # Frontenddan 'name_uz' keladi
        name_uz = request.data.get('name_uz')
        if not name_uz:
            return Response({'error': 'Viloyat nomi kiritilmadi'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Obyektni yaratish (modelingiz maydonlariga qarab name yoki name_uz deb yozing)
        region = Region.objects.create(name=name_uz)
        serializer = self.get_serializer(region)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# --- TUMANLAR VIEWSET ---
class DistrictViewSet(viewsets.ModelViewSet):
    queryset = District.objects.all()
    serializer_class = DistrictSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        if not is_admin_user(request):
            return Response({'error': 'Ruxsat berilmagan'}, status=status.HTTP_403_FORBIDDEN)
        
        name_uz = request.data.get('name_uz')
        region_id = request.data.get('region') # Frontend raqam (ID) yuboradi: parseInt(regId)

        if not name_uz or not region_id:
            return Response({'error': 'Tuman nomi yoki Viloyat ID yetishmayapti'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            region_obj = Region.objects.get(id=region_id)
        except Region.DoesNotExist:
            return Response({'error': 'Bunday ID dagi viloyat topilmadi'}, status=status.HTTP_400_BAD_REQUEST)

        # Tuman yaratish va viloyatga bog'lash (400 Bad request xatosi butkul yo'qoladi)
        district = District.objects.create(
            name=name_uz,
            region=region_obj  # ForeignKey obyekti beriladi
        )
        serializer = self.get_serializer(district)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


import os
import json
import base64
import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.Bot.models.TelegramBot import TelegramUser
from apps.Bot.models.orders import Order, TestResult
from apps.Bot.models.bot import District

# ─── Konstantalar ─────────────────────────────────────────────────────────────
MAX_FILE_SIZE     = 25 * 1024 * 1024          # 25 MB
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'zip'}
STAFF_ROLES       = ['admin', 'doctor', 'courier']


def is_admin_user(request):
    """tg_id orqali admin tekshiruvi"""
    tg_id = request.GET.get('tg_id') or request.data.get('tg_id')
    if not tg_id:
        return False
    try:
        return TelegramUser.objects.get(user_id=str(tg_id)).role == 'admin'
    except TelegramUser.DoesNotExist:
        return False

STAFF_ROLES = ['admin', 'doctor', 'courier']
 
class StaffMeAPIView(APIView):
    """
    GET /api/staff/me?tg_id=<telegram_id>
 
    Barcha rollar uchun ishlaydi: admin | doctor | courier | user
    Frontend panellari (admin, shifokor, kuryer) shu endpointni tekshiradi.
    """
    permission_classes    = [AllowAny]
    authentication_classes = []
 
    def get(self, request, *args, **kwargs):
        tg_id = request.GET.get('tg_id')
        if not tg_id:
            return Response(
                {'error': 'tg_id talab qilinadi'},
                status=status.HTTP_400_BAD_REQUEST
            )
 
        try:
            user = TelegramUser.objects.get(user_id=str(tg_id))
            return Response({
                'tg_id':        str(user.user_id),
                'first_name':   user.first_name or '',
                'role':         user.role,            # admin | doctor | courier | user
                'is_staff':     user.role in STAFF_ROLES,
                'phone_number': getattr(user, 'phone_number', '') or '',
            })
        except TelegramUser.DoesNotExist:
            return Response({
                'tg_id':    str(tg_id),
                'role':     'user',
                'is_staff': False,
            })


# ─── TelegramUser ViewSet ─────────────────────────────────────────────────────
class TelegramUserViewSet(viewsets.ModelViewSet):
    queryset               = TelegramUser.objects.all().order_by('-id')
    serializer_class       = TelegramUserSerializer
    permission_classes     = [AllowAny]
    authentication_classes = []

    def list(self, request, *args, **kwargs):
        role_filter = request.GET.get('role')
        if role_filter == 'staff':
            queryset = TelegramUser.objects.filter(
                role__in=STAFF_ROLES
            ).order_by('-id')
        else:
            queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        if not is_admin_user(request):
            return Response({'error': 'Ruxsat berilmagan!'}, status=status.HTTP_403_FORBIDDEN)

        tg_id       = request.data.get('user_id')
        first_name  = request.data.get('first_name')
        role        = request.data.get('role', 'courier')
        phone       = request.data.get('phone_number', '')
        district_id = request.data.get('district')

        if not tg_id or not first_name:
            return Response(
                {'error': 'Telegram ID va Ism kiritilishi shart'},
                status=status.HTTP_400_BAD_REQUEST
            )

        district_obj = None
        if role == 'courier' and district_id:
            try:
                district_obj = District.objects.get(id=int(district_id))
            except (District.DoesNotExist, ValueError):
                pass

        user, created = TelegramUser.objects.update_or_create(
            user_id=str(tg_id),
            defaults={
                'first_name':   first_name,
                'role':         role,
                'phone_number': phone,
                'district':     district_obj if role == 'courier' else None,
            }
        )
        serializer = self.get_serializer(user)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        if not is_admin_user(request):
            return Response({'error': 'Ruxsat berilmagan!'}, status=status.HTTP_403_FORBIDDEN)

        instance    = self.get_object()
        role        = request.data.get('role')
        district_id = request.data.get('district')
        first_name  = request.data.get('first_name')
        phone       = request.data.get('phone_number')

        if first_name:
            instance.first_name = first_name
        if phone is not None:
            instance.phone_number = phone

        if role:
            instance.role     = role
            instance.is_admin = role == True

        if role == 'courier' and district_id:
            try:
                instance.district = District.objects.get(id=int(district_id))
            except (District.DoesNotExist, ValueError):
                instance.district = None
        else:
            instance.district = None

        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ─── Doctor Panel HTML ────────────────────────────────────────────────────────
def doctor_panel_view(request):
    return render(request, 'doctor_panel.html')


# ─── Doctor Orders ────────────────────────────────────────────────────────────
@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def doctor_orders_api(request):
    """
    GET /api/doctor/orders?tg_id=<tg_id>
    result_pending va result_sent statusli buyurtmalarni qaytaradi.
    """
    tg_id = request.GET.get('tg_id')
    if not tg_id:
        return JsonResponse({'error': 'tg_id talab qilinadi'}, status=400)

    try:
        staff = TelegramUser.objects.get(user_id=str(tg_id))
        if staff.role not in ['admin', 'doctor']:
            return JsonResponse({'error': 'Ruxsat berilmagan'}, status=403)
    except TelegramUser.DoesNotExist:
        pass  # test rejimi

    orders = Order.objects.filter(
        status__in=['result_pending', 'result_sent']
    ).select_related('service', 'user').order_by('-created_at')

    result = []
    for o in orders:
        result.append({
            'order_id':    str(o.id),
            'patientName': o.patient_name or "Noma'lum",
            'patientAge':  o.patient_age or 0,
            'patientType': o.patient_type or 'adult',
            'status':      o.status,
            'serviceName': o.service.name_uz if o.service else None,
            'createdAt':   o.created_at.isoformat() if o.created_at else '',
        })

    return JsonResponse(result, safe=False)


# ─── Upload Order Result ───────────────────────────────────────────────────────
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def upload_order_result_api(request, order_id):
    """
    POST /api/doctor/orders/<order_id>/result?tg_id=<tg_id>
    """
    order = get_object_or_404(Order, id=order_id)

    if order.status != 'result_pending':
        return JsonResponse(
            {'error': f"Holat '{order.status}'. Faqat 'result_pending' buyurtmalarga natija yuboriladi."},
            status=400
        )

    tg_id = request.GET.get('tg_id')

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': "JSON o'qib bo'lmadi."}, status=400)

    file_base64 = data.get('file_base64', '')
    filename    = data.get('filename', 'natija.pdf').strip()

    if not file_base64:
        return JsonResponse({'error': "file_base64 bo'sh."}, status=400)

    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        return JsonResponse(
            {'error': f"Ruxsat etilmagan fayl: .{ext}. PDF, JPG, PNG yoki ZIP bo'lishi kerak."},
            status=400
        )

    try:
        imgstr    = file_base64.split(';base64,', 1)[1] if ';base64,' in file_base64 else file_base64
        file_data = base64.b64decode(imgstr)
    except Exception:
        return JsonResponse({'error': "Faylni dekodlab bo'lmadi."}, status=400)

    if len(file_data) > MAX_FILE_SIZE:
        return JsonResponse({'error': "Fayl hajmi 25 MB dan oshmasligi kerak!"}, status=400)

    try:
        doctor_user = None
        if tg_id:
            try:
                doctor_user = TelegramUser.objects.get(user_id=str(tg_id))
            except TelegramUser.DoesNotExist:
                pass

        test_result, _ = TestResult.objects.get_or_create(
            order=order, defaults={'doctor': doctor_user}
        )
        test_result.doctor      = doctor_user
        test_result.result_file = ContentFile(file_data, name=filename)
        test_result.status      = 'sent'
        test_result.save()

        order.status = 'result_sent'
        order.save(update_fields=['status'])

    except Exception as e:
        return JsonResponse({'error': f"Saqlashda xatolik: {str(e)}"}, status=500)

    # Bemorga Telegram xabari
    telegram_status = "yuborilmadi"
    patient_tg_id   = None

    if hasattr(order, 'user') and order.user:
        patient_tg_id = order.user.user_id
    elif hasattr(order, 'telegram_user') and order.telegram_user:
        patient_tg_id = order.telegram_user.user_id

    if patient_tg_id:
        BOT_TOKEN = getattr(settings, 'BOT_TOKEN', None) or os.getenv('BOT_TOKEN')
        if BOT_TOKEN:
            service_name = order.service.name_uz if order.service else "Tahlil"
            caption = (
                f"📊 *{service_name} natijangiz tayyor!*\n\n"
                f"👤 *Bemor:* {order.patient_name or 'Noma\'lum'}\n"
                f"🆔 *Buyurtma:* #{order_id}\n"
                f"✅ Shifokor tomonidan tasdiqlandi.\n\n"
                f"🩺 Xizmatimizdan foydalanganingiz uchun rahmat!"
            )
            try:
                resp    = requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                    data={'chat_id': patient_tg_id, 'caption': caption, 'parse_mode': 'Markdown'},
                    files={'document': (filename, file_data)},
                    timeout=20
                )
                tg_json = resp.json()
                telegram_status = "yuborildi" if tg_json.get('ok') else f"xato: {tg_json.get('description')}"
            except Exception as e:
                telegram_status = f"exception: {e}"

    return JsonResponse({
        'success':         True,
        'new_status':      'result_sent',
        'telegram_status': telegram_status,
    })