"""
apps/Bot/views/base.py

Faqat bu faylga tegishli viewlar:
  - ViewSet lar (Region, District, Service, Order, TelegramUser, ...)
  - Admin panel HTML + API endpointlar
  - Wizard view
  - StaffMeAPIView
"""

import json
import os
import logging
import requests

from datetime import datetime

from django.conf import settings
from django.db.models import Sum, Count, Min, Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.timezone import now, timedelta
from django.views.decorators.csrf import csrf_exempt
from django.utils import translation
from django.core.files.base import ContentFile

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.Bot.models.bot import Region, District, BotSetting
from apps.Bot.models.TelegramBot import TelegramUser, Channel, Referral, Guide, Appeal
from apps.Bot.models.orders import Service, Order, Payment, TestResult
from apps.Bot.serializers.base import (
    RegionSerializer, DistrictSerializer, BotSettingSerializer,
    TelegramUserSerializer, ChannelSerializer, ReferralSerializer,
    GuideSerializer, AppealSerializer, CourierOrderSerializer,
    ServiceSerializer, OrderCreateSerializer, PaymentSerializer,
)

logger = logging.getLogger(__name__)

STAFF_ROLES = ['admin', 'doctor', 'courier']
MAX_FILE_SIZE = 25 * 1024 * 1024
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'zip'}


# ─────────────────────────────────────────────────────────────────────────────
# YORDAMCHI FUNKSIYALAR
# ─────────────────────────────────────────────────────────────────────────────

def is_admin_user(request):
    """
    Hozircha har doim True (dev rejim).
    Prodda quyidagicha yoqing:
        tg_id = request.GET.get('tg_id') or getattr(request, 'data', {}).get('tg_id')
        try:
            return TelegramUser.objects.get(user_id=tg_id).is_admin
        except TelegramUser.DoesNotExist:
            return False
    """
    return True


def telegram_admin_required(view_func):
    """Faqat bazada bor TelegramUser larni o'tkazadi."""
    def _wrapped(request, *args, **kwargs):
        tg_id = request.GET.get('tg_id')
        if not tg_id:
            return JsonResponse({'error': 'Telegram ID topilmadi'}, status=401)
        try:
            request.tg_user = TelegramUser.objects.get(user_id=tg_id)
        except TelegramUser.DoesNotExist:
            return JsonResponse({'error': 'Ruxsat berilmagan foydalanuvchi'}, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped


# ─────────────────────────────────────────────────────────────────────────────
# BOT SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

class BotSettingViewSet(viewsets.ModelViewSet):
    queryset = BotSetting.objects.all()
    serializer_class = BotSettingSerializer
    lookup_field = 'key'
    permission_classes = [AllowAny]
    authentication_classes = []


# ─────────────────────────────────────────────────────────────────────────────
# MARKETING & CHANNELS
# ─────────────────────────────────────────────────────────────────────────────

class ChannelViewSet(viewsets.ModelViewSet):
    queryset = Channel.objects.all()
    serializer_class = ChannelSerializer
    lookup_field = 'channel_id'

class ReferralViewSet(viewsets.ModelViewSet):
    queryset = Referral.objects.all()
    serializer_class = ReferralSerializer

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
        return Response({'status': 'Murojaat yopildi va javob berildi'})


# ─────────────────────────────────────────────────────────────────────────────
# REGION & DISTRICT
# ─────────────────────────────────────────────────────────────────────────────

class RegionViewSet(viewsets.ModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        if not is_admin_user(request):
            return Response({'error': 'Ruxsat berilmagan'}, status=status.HTTP_403_FORBIDDEN)
        name_uz = request.data.get('name_uz')
        if not name_uz:
            return Response({'error': 'Viloyat nomi kiritilmadi'}, status=status.HTTP_400_BAD_REQUEST)
        region = Region.objects.create(name=name_uz)
        return Response(self.get_serializer(region).data, status=status.HTTP_201_CREATED)


class DistrictViewSet(viewsets.ModelViewSet):
    queryset = District.objects.all()
    serializer_class = DistrictSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def partial_update(self, request, *args, **kwargs):
        if not is_admin_user(request):
            return Response({'error': 'Ruxsat berilmagan'}, status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        if 'is_active' in request.data:
            instance.is_active = request.data['is_active'] in (True, 'true', '1', 1)
        if 'delivery_price' in request.data:
            try:
                instance.delivery_price = int(request.data['delivery_price'])
            except (TypeError, ValueError):
                pass
        if 'name_uz' in request.data and request.data['name_uz']:
            instance.name = request.data['name_uz']
        instance.save()
        return Response(self.get_serializer(instance).data)

    def create(self, request, *args, **kwargs):
        if not is_admin_user(request):
            return Response({'error': 'Ruxsat berilmagan'}, status=status.HTTP_403_FORBIDDEN)
        name_uz = request.data.get('name_uz')
        region_id = request.data.get('region')
        if not name_uz or not region_id:
            return Response({'error': 'Tuman nomi yoki Viloyat ID yetishmayapti'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            region_obj = Region.objects.get(id=region_id)
        except Region.DoesNotExist:
            return Response({'error': 'Bunday ID dagi viloyat topilmadi'}, status=status.HTTP_400_BAD_REQUEST)
        district = District.objects.create(name=name_uz, region=region_obj)
        return Response(self.get_serializer(district).data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────────
# SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def _normalize_names(self, data):
        """name_uz/name_ru/name_en ni bitta kelgan nomdan to'ldiradi."""
        data = data.copy()
        main = data.get('name_uz') or data.get('name_ru') or data.get('name_en') or data.get('name')
        if main:
            data['name_uz'] = main
            data['name_ru'] = main
            data['name_en'] = main
        return data

    def create(self, request, *args, **kwargs):
        data = self._normalize_names(request.data)
        serializer = self.get_serializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        data = self._normalize_names(request.data)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=data, partial=partial)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_update(serializer)
        return Response(serializer.data)


# ─────────────────────────────────────────────────────────────────────────────
# ORDER VIEWSET
# ─────────────────────────────────────────────────────────────────────────────

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderCreateSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def _auto_assign_courier(self, order):
        """
        To'lov tasdiqlangandan so'ng tumandagi bo'sh kuryerga biriktiradi.
        Bo'sh kuryer yo'q bo'lsa — eng kam yukli kuryerga.
        """
        if not order.district:
            logger.warning("[Courier] Order #%s — district yo'q.", order.id)
            order.status = 'paid'
            order.save(update_fields=['status'])
            return None

        couriers = TelegramUser.objects.filter(
            role='courier',
            district=order.district,
            is_active=True,
        )
        if not couriers.exists():
            logger.warning("[Courier] %s tumanida kuryer topilmadi.", order.district.name)
            order.status = 'paid'
            order.save(update_fields=['status'])
            return None

        couriers_stats = couriers.annotate(
            active_count=Count(
                'assigned_orders',
                filter=Q(assigned_orders__status__in=['paid', 'delivering'])
            ),
            first_order_time=Min(
                'assigned_orders__created_at',
                filter=Q(assigned_orders__status__in=['paid', 'delivering'])
            )
        )
        free = [c for c in couriers_stats if c.active_count == 0]
        chosen = free[0] if free else sorted(
            couriers_stats,
            key=lambda c: (c.active_count, c.first_order_time or datetime.now())
        )[0]

        order.status = 'paid'
        order.save(update_fields=['status'])
        logger.info("[Courier] Order #%s → kuryer TG_ID: %s (buyurtmaga courier FK yo'q)", order.id, chosen.user_id)
        return chosen

    # ── Buyurtma yaratish — to'lov boshlash tspay_payment.py ga ko'chirildi ──
    # Bu yerda faqat admin panel uchun qo'shimcha actionlar qoladi.

    @action(detail=True, methods=['post'], url_path='confirm_payment')
    def confirm_payment(self, request, pk=None):
        """
        Admin panel → To'lovni qo'lda tasdiqlash.
        TSPay webhook ishlamagan holatda ham ishlatiladi.
        """
        if not pk or str(pk).strip() in ('undefined', 'null', '', 'None'):
            return Response(
                {"success": False, "detail": "Buyurtma ID noto'g'ri."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            pk = int(pk)
        except (ValueError, TypeError):
            return Response(
                {"success": False, "detail": f"Buyurtma ID raqam bo'lishi kerak, '{pk}' emas."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            order = Order.objects.select_related('payment', 'service', 'user').get(pk=pk)
        except Order.DoesNotExist:
            return Response(
                {"success": False, "detail": f"#{pk} buyurtma topilmadi."},
                status=status.HTTP_404_NOT_FOUND
            )

        payment = getattr(order, 'payment', None)
        if not payment:
            return Response(
                {"success": False, "detail": "Bu buyurtmaga payment biriktirilmagan."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ── Admin qo'lda tasdiqlash ─────────────────────────────────────────
        is_admin_action = request.data.get('is_admin') or (payment.method == 'admin')
        if is_admin_action:
            if payment.status == 'success':
                return Response({"success": True, "status": "paid", "message": "Allaqachon tasdiqlangan."})
            payment.status = 'success'
            payment.transaction_id = (
                request.data.get('transaction_id')
                or f"admin_{request.GET.get('tg_id','?')}_{order.id}"
            )
            payment.save()
            self._auto_assign_courier(order)
            logger.info("[AdminConfirm] Order #%s tasdiqlandi.", order.id)
            return Response({"success": True, "status": "paid", "message": "To'lov tasdiqlandi."})

        # ── TSPay cheque tekshirish ──────────────────────────────────────────
        cheque_id = (
            request.data.get('cheque_id')
            or getattr(payment, 'cheque_id', None)
            or payment.transaction_id
        )
        if not cheque_id:
            return Response(
                {"success": False, "detail": "cheque_id topilmadi."},
                status=status.HTTP_400_BAD_REQUEST
            )

        base_url = getattr(settings, 'TSPAY_BASE_URL', 'https://api.tspay.uz')
        try:
            resp = requests.get(f"{base_url}/api/transactions/cheque/{cheque_id}", timeout=10)
            txn = resp.json()
        except Exception as exc:
            return Response(
                {"success": False, "detail": f"TSPay server xatosi: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY
            )

        txn_status = txn.get('status')
        if txn_status == 'success':
            payment.status = 'success'
            payment.transaction_id = txn.get('id') or txn.get('transaction_id', cheque_id)
            payment.save()
            self._auto_assign_courier(order)
            return Response({"success": True, "status": "paid"})

        if txn_status == 'pending':
            return Response({"success": False, "status": "pending"})

        payment.status = 'failed'
        payment.save()
        order.status = 'canceled'
        order.save(update_fields=['status'])
        return Response({"success": False, "status": txn_status, "detail": "To'lov amalga oshmadi."})

    @action(detail=True, methods=['post'], url_path='update_status')
    def update_status(self, request, pk=None):
        """Kuryer tomonidan status o'zgartirish: paid→delivering, delivering→done"""
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"success": False, "detail": "Buyurtma topilmadi"}, status=404)

        tg_id = request.GET.get('tg_id') or request.data.get('tg_id')
        new_status = request.data.get('status')

        if not tg_id:
            return Response({"success": False, "detail": "tg_id talab qilinadi"}, status=400)
        if new_status not in ['delivering', 'done']:
            return Response({"success": False, "detail": "Faqat 'delivering' yoki 'done' ruxsat."}, status=400)

        order.status = new_status
        order.save(update_fields=['status'])
        logger.info("[Courier] Order #%s → %s (TG: %s)", order.id, new_status, tg_id)
        return Response({"success": True, "status": order.status})


# ─────────────────────────────────────────────────────────────────────────────
# TELEGRAM USER VIEWSET
# ─────────────────────────────────────────────────────────────────────────────

class TelegramUserViewSet(viewsets.ModelViewSet):
    queryset = TelegramUser.objects.all().order_by('-id')
    serializer_class = TelegramUserSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def list(self, request, *args, **kwargs):
        role_filter = request.GET.get('role')
        if role_filter == 'staff':
            qs = TelegramUser.objects.filter(role__in=STAFF_ROLES).order_by('-id')
        else:
            qs = self.filter_queryset(self.get_queryset())
        return Response(self.get_serializer(qs, many=True).data)

    def create(self, request, *args, **kwargs):
        if not is_admin_user(request):
            return Response({'error': 'Ruxsat berilmagan!'}, status=status.HTTP_403_FORBIDDEN)
        tg_id       = request.data.get('user_id')
        first_name  = request.data.get('first_name')
        role        = request.data.get('role', 'courier')
        phone       = request.data.get('phone_number', '')
        district_id = request.data.get('district')

        if not tg_id or not first_name:
            return Response({'error': 'Telegram ID va Ism kiritilishi shart'}, status=status.HTTP_400_BAD_REQUEST)

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
        return Response(
            self.get_serializer(user).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        if not is_admin_user(request):
            return Response({'error': 'Ruxsat berilmagan!'}, status=status.HTTP_403_FORBIDDEN)
        instance    = self.get_object()
        role        = request.data.get('role')
        district_id = request.data.get('district')

        if request.data.get('first_name'):
            instance.first_name = request.data['first_name']
        if request.data.get('phone_number') is not None:
            instance.phone_number = request.data['phone_number']
        if role:
            instance.role = role
        if role == 'courier' and district_id:
            try:
                instance.district = District.objects.get(id=int(district_id))
            except (District.DoesNotExist, ValueError):
                instance.district = None
        elif role and role != 'courier':
            instance.district = None

        instance.save()
        return Response(self.get_serializer(instance).data)


# ─────────────────────────────────────────────────────────────────────────────
# STAFF ME API
# ─────────────────────────────────────────────────────────────────────────────

class StaffMeAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        tg_id = request.GET.get('tg_id')
        if not tg_id:
            return Response({'error': 'tg_id talab qilinadi'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = TelegramUser.objects.get(user_id=str(tg_id))
            return Response({
                'tg_id':        str(user.user_id),
                'first_name':   user.first_name or '',
                'role':         user.role,
                'is_staff':     user.role in STAFF_ROLES,
                'phone_number': getattr(user, 'phone_number', '') or '',
            })
        except TelegramUser.DoesNotExist:
            return Response({'tg_id': str(tg_id), 'role': 'user', 'is_staff': False})


# ─────────────────────────────────────────────────────────────────────────────
# WIZARD VIEW
# ─────────────────────────────────────────────────────────────────────────────

def wizard_view(request):
    """Eski havola — yangi webapp buyurtma oqimiga yo'naltiradi."""
    from django.shortcuts import redirect
    from urllib.parse import urlencode

    q = {}
    if request.GET.get('lang'):
        q['lang'] = request.GET.get('lang')
    if request.GET.get('tg_id'):
        q['tg_id'] = request.GET.get('tg_id')
    q['page'] = 'order'
    return redirect('/api/webapp/?' + urlencode(q))


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN PANEL
# ─────────────────────────────────────────────────────────────────────────────

def admin_panel_view(request):
    return render(request, 'admin/admin_panel.html')


@csrf_exempt
def admin_stats_api(request):
    """GET /api/admin/stats/"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Faqat GET'}, status=405)
    try:
        tg_id = request.GET.get('tg_id')
        if not tg_id or not TelegramUser.objects.filter(user_id=tg_id).exists():
            return JsonResponse({'error': 'Ruxsat berilmagan'}, status=403)

        total_orders  = Order.objects.count()
        revenue_data  = Order.objects.filter(status__in=['paid', 'delivering', 'done']).aggregate(s=Sum('total_price'))
        total_revenue = float(revenue_data['s'] or 0)
        total_users   = TelegramUser.objects.count()
        last_month    = now() - timedelta(days=30)
        new_monthly   = TelegramUser.objects.filter(date_joined__gte=last_month).count()

        status_dict = {
            item['status']: item['count']
            for item in Order.objects.values('status').annotate(count=Count('id'))
        }

        return JsonResponse({
            'total_orders':       total_orders,
            'total_revenue':      total_revenue,
            'total_users':        total_users,
            'pending_orders':     status_dict.get('pending', 0),
            'paid_orders':        status_dict.get('paid', 0),
            'delivering_orders':  status_dict.get('delivering', 0),
            'done_orders':        status_dict.get('done', 0),
            'canceled_orders':    status_dict.get('canceled', 0),
            'new_users_this_month': new_monthly,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def admin_orders_api(request):
    """
    GET  /api/admin/orders/  — to'lov + screenshot ma'lumotlari bilan
    POST /api/admin/orders/  — status yoki natija yangilash
    """
    tg_id = request.GET.get('tg_id')
    if not tg_id or not TelegramUser.objects.filter(user_id=tg_id).exists():
        return JsonResponse({'error': 'Ruxsat berilmagan'}, status=403)

    if request.method == 'GET':
        orders = (
            Order.objects
            .select_related('user', 'service', 'district', 'payment')
            .prefetch_related('test_result')
            .order_by('-created_at')[:50]
        )
        result = []
        for o in orders:
            d_name = '—'
            if o.district:
                d_name = getattr(o.district, 'name_uz', None) or getattr(o.district, 'name', None) or str(o.district)

            # ── Payment ───────────────────────────────────────────────────────
            payment_data = {'method': '', 'status': 'pending', 'transaction_id': '',
                            'card_mask': '', 'screenshot': '', 'created_at': '', 'amount': 0}
            try:
                pay = o.payment
                screenshot_url = ''
                if pay.screenshot:
                    try:
                        screenshot_url = pay.screenshot.url
                    except Exception:
                        screenshot_url = str(pay.screenshot)
                payment_data = {
                    'method':         pay.method or '',
                    'status':         pay.status or 'pending',
                    'transaction_id': pay.transaction_id or '',
                    'card_mask':      getattr(pay, 'card_mask', '') or '',
                    'screenshot':     screenshot_url,
                    'created_at':     pay.created_at.strftime("%Y-%m-%d %H:%M") if pay.created_at else '',
                    'amount':         float(pay.amount) if pay.amount else 0,
                }
            except Exception:
                pass

            # ── TestResult ────────────────────────────────────────────────────
            has_result, conclusion = False, ''
            try:
                tr = o.test_result
                has_result = bool(tr.result_file)
                conclusion = tr.doctor_conclusion or ''
            except Exception:
                pass

            phone = ''
            if o.user:
                phone = o.user.phone or o.user.phone_number or ''

            result.append({
                'id':             o.id,
                'patient_name':   o.patient_name or (o.user.first_name if o.user else "Noma'lum"),
                'patient_type':   o.patient_type or 'adult',
                'service_name':   o.service.name_uz if o.service else '—',
                'total_price':    float(o.total_price or 0),
                'status':         o.status,
                'created_at':     o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else '',
                'district_name':  d_name,
                'address_note':   o.address_note or '',
                'latitude':       o.latitude,
                'longitude':      o.longitude,
                'has_result':     has_result,
                'conclusion':     conclusion,
                'phone':          phone,
                'payment':        payment_data,
                'screenshot_url': payment_data['screenshot'],
            })
        return JsonResponse(result, safe=False)

    elif request.method == 'POST':
        try:
            ct = request.content_type or ''
            if ct.startswith('multipart/form-data') or request.FILES:
                order_id    = request.POST.get('order_id')
                new_status  = request.POST.get('status')
                result_file = request.FILES.get('result_file')
                conclusion  = request.POST.get('conclusion', '')
            else:
                data        = json.loads(request.body)
                order_id    = data.get('order_id')
                new_status  = data.get('status')
                result_file = None
                conclusion  = data.get('conclusion', '')

            order = Order.objects.get(id=order_id)
            if new_status:
                order.status = new_status
                order.save(update_fields=['status'])

            if result_file or conclusion:
                tg_user = TelegramUser.objects.filter(user_id=tg_id).first()
                tr, _ = TestResult.objects.get_or_create(order=order)
                if tg_user:
                    tr.doctor = tg_user
                if result_file:
                    tr.result_file = result_file
                if conclusion:
                    tr.doctor_conclusion = conclusion
                tr.status = 'ready'
                tr.save()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'error': 'Faqat GET yoki POST'}, status=405)


@csrf_exempt
def admin_services_api(request):
    """GET/POST /api/admin/services/"""
    tg_id = request.GET.get('tg_id')
    if not tg_id or not TelegramUser.objects.filter(user_id=tg_id).exists():
        return JsonResponse({'error': 'Ruxsat berilmagan'}, status=403)

    if request.method == 'GET':
        services = Service.objects.all().order_by('id')
        return JsonResponse([{
            'id': s.id, 'name_uz': s.name_uz, 'price': float(s.price), 'is_active': s.is_active
        } for s in services], safe=False)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            svc = Service.objects.get(id=data.get('id'))
            if 'price' in data:
                svc.price = data['price']
            if 'is_active' in data:
                svc.is_active = data['is_active']
            svc.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'error': 'Faqat GET yoki POST'}, status=405)


@csrf_exempt
def admin_settings_api(request):
    """GET/POST /api/admin/settings/ — BotSetting orqali saqlanadi."""
    from apps.Bot.views.webapp_user import get_admin_settings_response, save_admin_settings_from_request

    tg_id = request.GET.get('tg_id')
    if not tg_id or not TelegramUser.objects.filter(user_id=tg_id).exists():
        return JsonResponse({'error': 'Ruxsat berilmagan'}, status=403)

    if request.method == 'GET':
        return JsonResponse(get_admin_settings_response())
    elif request.method == 'POST':
        try:
            ct = request.content_type or ''
            data = request.POST if ct.startswith('multipart') else json.loads(request.body)
            save_admin_settings_from_request(data)
            logger.info("[Settings] Yangilandi: %s", list(data.keys()))
            return JsonResponse({'success': True, 'message': 'Sozlamalar saqlandi!'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'error': 'Faqat GET yoki POST'}, status=405)


@csrf_exempt
def admin_broadcast_api(request):
    """POST /api/admin/broadcast/"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Faqat POST'}, status=405)

    tg_id = request.GET.get('tg_id')
    if not tg_id or not TelegramUser.objects.filter(user_id=tg_id).exists():
        return JsonResponse({'error': 'Ruxsat berilmagan'}, status=403)

    try:
        text       = request.POST.get('text', '')
        media_file = request.FILES.get('media')
        if not text and not media_file:
            return JsonResponse({'success': False, 'error': 'Matn yoki fayl kiriting'}, status=400)

        BOT_TOKEN  = getattr(settings, 'BOT_TOKEN', None) or os.getenv('BOT_TOKEN')
        users      = TelegramUser.objects.filter(role='user')
        sent_count = 0

        for u in users:
            try:
                if media_file:
                    media_file.seek(0)
                    is_photo = media_file.content_type.startswith('image/')
                    method   = 'sendPhoto' if is_photo else 'sendVideo'
                    field    = 'photo' if is_photo else 'video'
                    requests.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
                        data={'chat_id': u.user_id, 'caption': text, 'parse_mode': 'HTML'},
                        files={field: media_file},
                        timeout=8,
                    )
                else:
                    requests.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                        data={'chat_id': u.user_id, 'text': text, 'parse_mode': 'HTML'},
                        timeout=8,
                    )
                sent_count += 1
            except Exception:
                continue

        return JsonResponse({'success': True, 'sent': sent_count})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ─────────────────────────────────────────────────────────────────────────────
# DOCTOR VIEWS  (doctor.py ga ko'chirilgan, bu yerda faqat re-export)
# ─────────────────────────────────────────────────────────────────────────────
# urls.py da to'g'ridan-to'g'ri apps.Bot.views.doctor dan import qiling:
#   from apps.Bot.views.doctor import doctor_panel_view, doctor_orders_api, upload_order_result_api