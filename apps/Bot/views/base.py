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

# --- REGIONS & SETTINGS ---
class RegionViewSet(viewsets.ModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    permission_classes = [AllowAny]      # Istalgan odam so'rov yuborishi uchun
    authentication_classes = []
    

class DistrictViewSet(viewsets.ModelViewSet):
    queryset = District.objects.all()
    serializer_class = DistrictSerializer
    permission_classes = [AllowAny]      # Istalgan odam so'rov yuborishi uchun
    authentication_classes = []

    @action(detail=True, methods=['post'], url_path='fetch-geo')
    def fetch_geo(self, request, pk=None):
        district = self.get_object()
        district.fetch_coordinates(force=True)
        return Response({'status': 'Koordinatalar yangilandi', 'lat': district.latitude, 'lng': district.longitude})

class BotSettingViewSet(viewsets.ModelViewSet):
    queryset = BotSetting.objects.all()
    serializer_class = BotSettingSerializer
    lookup_field = 'key'

# --- TELEGRAM USERS ---
class TelegramUserViewSet(viewsets.ModelViewSet):
    queryset = TelegramUser.objects.all()
    serializer_class = TelegramUserSerializer
    lookup_field = 'user_id'

    @action(detail=False, methods=['get'], url_path='me')
    def get_staff_me(self, request):
        tg_id = request.query_params.get('tg_id')
        user = get_object_or_404(TelegramUser, user_id=tg_id)
        return Response({
            'role': user.role,
            'regionId': user.district.id if user.district else None
        })

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
            webapp_url  = getattr(settings, 'WEBAPP_BASE_URL', 'https://sizningdomen.uz')

            if not merchant_id:
                logger.error("TSPAY_MERCHANT_ID settings.py da topilmadi!")
                return Response(
                    {"success": False, "detail": "To'lov tizimi sozlanmagan. Admin bilan bog'laning."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            payload = {
                "merchant_id": merchant_id,
                "amount": int(float(order.total_price)),   # TSPay integer talab qiladi (tiyin emas, so'm)
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
                # cheque_id ni bazaga saqlaymiz — keyinchalik status tekshirish uchun
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

    # ──────────────────────────────────────────
    # POST /api/orders/{id}/confirm_payment/
    # Frontend TSPay dan qaytganda chaqiradi
    # ──────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='confirm_payment')
    def confirm_payment(self, request, pk=None):
        """
        Frontend TSPay redirect dan qaytganda shu endpoint chaqiriladi.
        cheque_id orqali TSPay dan so'rab status aniqlanadi.
        """
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"success": False, "detail": "Buyurtma topilmadi"}, status=404)

        cheque_id = request.data.get('cheque_id') or getattr(order.payment, 'cheque_id', None)
        if not cheque_id:
            return Response({"success": False, "detail": "cheque_id topilmadi"}, status=400)

        base_url = getattr(settings, 'TSPAY_BASE_URL', 'https://api.tspay.uz')

        try:
            resp = requests.get(
                f"{base_url}/api/transactions/cheque/{cheque_id}",
                timeout=10
            )
            txn = resp.json()
            logger.info(f"TSPay cheque {cheque_id} status: {txn}")
        except Exception as e:
            logger.exception(f"TSPay status tekshirishda xato: {e}")
            return Response({"success": False, "detail": str(e)}, status=500)

        txn_status = txn.get('status')          # 'success' | 'failed' | 'canceled' | 'pending'
        payment = order.payment

        if txn_status == 'success':
            payment.status = 'success'
            payment.transaction_id = txn.get('id') or txn.get('transaction_id', '')
            payment.save()
            order.status = 'paid'
            order.save()
            # TODO: bot orqali kuryerga/adminga xabar yuborish
            return Response({"success": True, "status": "paid"})

        elif txn_status == 'pending':
            return Response({"success": True, "status": "pending"})

        else:  # failed | canceled
            payment.status = 'failed'
            payment.save()
            return Response({"success": False, "status": txn_status,
                             "detail": "To'lov amalga oshmadi"}, status=200)

    # ──────────────────────────────────────────
    # POST /api/payment/tpay-callback/
    # TSPay server webhook orqali chaqiradi
    # (checkPerform va performTransaction)
    # ──────────────────────────────────────────
    @method_decorator(csrf_exempt)
    @action(detail=False, methods=['post'], url_path='tpay-callback')
    def tpay_callback(self, request):
        """
        TSPay webhook: docs.tspay.uz/integration/webhooks.html
        Ikki xil so'rov keladi:
          method = "checkPerform"     → buyurtma mavjudligini tekshirish
          method = "performTransaction" → to'lovni tasdiqlash
        """
        method   = request.data.get('method')
        order_id = request.data.get('order_id') or request.data.get('params', {}).get('order_id')
        logger.info(f"TSPay webhook: method={method}, order_id={order_id}, data={request.data}")

        # ── 1. checkPerform: "Bu order_id haqiqiy va to'lov qabul qilsa bo'ladimi?" ──
        if method == 'checkPerform':
            try:
                order = Order.objects.get(id=order_id)
                if order.status in ('paid', 'cancelled'):
                    return Response({"allow": False, "reason": "Order allaqachon yopilgan"})
                return Response({"allow": True})
            except Order.DoesNotExist:
                return Response({"allow": False, "reason": "Order topilmadi"})

        # ── 2. performTransaction: "To'lov qilindi, tasdiqlang" ──
        if method == 'performTransaction':
            transaction_id = request.data.get('transaction_id') or request.data.get('id')
            txn_status     = request.data.get('status')          # 'success' | 'failed'
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
                    order.status = 'paid'
                    order.save()
                    logger.info(f"Order #{order_id} to'landi ✅")
                    # TODO: Telegram bot orqali xabar yuborish
                    return Response({"success": True})
                else:
                    payment.status = 'failed'
                    payment.save()
                    return Response({"success": False, "reason": "To'lov rad etildi"})

            except Order.DoesNotExist:
                return Response({"success": False, "reason": "Order topilmadi"}, status=404)

        # Noma'lum method
        logger.warning(f"TSPay webhook: noma'lum method={method}")
        return Response({"success": False, "reason": "Noma'lum method"}, status=400)
    
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