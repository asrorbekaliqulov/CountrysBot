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



class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    permission_classes = [AllowAny]      # Istalgan odam so'rov yuborishi uchun
    authentication_classes = []

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderCreateSerializer
    permission_classes = [AllowAny]      # Istalgan odam so'rov yuborishi uchun
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        # Telegram ID ni tekshirish va foydalanuvchini aniqlash
        tg_id = request.data.get('tg_id')
        try:
            user = TelegramUser.objects.get(user_id=tg_id)
        except TelegramUser.DoesNotExist:
            return Response({"error": "Foydalanuvchi topilmadi"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Obyektni saqlash
        order = serializer.save(user=user)
        payment = order.payment

        # Agar TPAY tanlangan bo'lsa, onlayn to'lov havolasini olish
        if payment.method == 'tpay':
            tpay_url = "https://api.tpay.uz/v1/payment/create" # Tpay rasmiy API url manzili
            headers = {
                "Authorization": f"Bearer {getattr(self.settings, 'TPAY_SECRET_KEY', 'TEST_KEY')}",
                "Content-Type": "application/json"
            }
            payload = {
                "amount": float(order.total_price),
                "order_id": str(order.id),
                "return_url": f"https://sizningdomen.uz/api/payment/tpay-callback/",
                "description": f"Order #{order.id} uchun to'lov"
            }
            try:
                # Tpayga so'rov yuborish
                response = requests.post(tpay_url, json=payload, headers=headers, timeout=10)
                res_data = response.json()
                
                if response.status_code == 200 and res_data.get('pay_url'):
                    return Response({
                        "success": True,
                        "payment_method": "tpay",
                        "pay_url": res_data.get('pay_url'),
                        "order_id": order.id
                    }, status=status.HTTP_201_CREATED)
                else:
                    return Response({"error": "Tpay to'lov tizimida xatolik yuz berdi"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                return Response({"error": f"Ulanish xatosi: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Admin orqali bo'lsa
        return Response({
            "success": True,
            "payment_method": "admin",
            "message": "Buyurtma saqlandi, chek tekshiruvga yuborildi.",
            "order_id": order.id
        }, status=status.HTTP_201_CREATED)
    
    @method_decorator(csrf_exempt)
    @action(detail=False, methods=['post'], url_path='tpay-callback')
    def tpay_callback(self, request):
        """Tpay tizimidan keladigan to'lov natijasi xabari"""
        transaction_id = request.data.get('transaction_id')
        order_id = request.data.get('order_id')
        status_payment = request.data.get('status') # 'success' yoki 'failed'
        card_mask = request.data.get('card_mask')

        try:
            order = Order.objects.get(id=order_id)
            payment = order.payment
            
            if status_payment == 'success':
                payment.status = 'success'
                payment.transaction_id = transaction_id
                payment.card_mask = card_mask
                payment.save()

                order.status = 'paid' # Buyurtma holatini to'langan deb o'zgartiramiz
                order.save()
                
                # Bu yerda kuryer yoki shifokorga bot orqali "Yangi to'langan buyurtma keldi" deb xabar yuborish mumkin
                
                return Response({"status": "OK", "message": "To'lov muvaffaqiyatli qabul qilindi"}, status=200)
            else:
                payment.status = 'failed'
                payment.save()
                return Response({"status": "FAIL", "message": "To'lov rad etildi"}, status=400)
                
        except Order.DoesNotExist:
            return Response({"error": "Order topilmadi"}, status=404)

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