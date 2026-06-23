"""
apps/Bot/urls.py

Barcha URL yo'llari bitta joyda, conflict yo'q.

Asosiy urls.py da:
    path('api/', include('apps.Bot.urls')),
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.Bot.views.webapp_user import (
    webapp_view,
    webapp_public_settings_api,
    webapp_profile_api,
    webapp_orders_api,
    webapp_order_detail_api,
    webapp_results_api,
    webapp_appeal_api,
)
from apps.Bot.views.base import (
    # ViewSets
    OrderViewSet, RegionViewSet, DistrictViewSet, BotSettingViewSet,
    ServiceViewSet, TelegramUserViewSet, ChannelViewSet, ReferralViewSet,
    GuideViewSet, AppealViewSet,
    # APIView
    StaffMeAPIView,
    # Function views
    wizard_view,
    admin_panel_view,
    admin_orders_api,
    admin_services_api,
    admin_broadcast_api,
    admin_stats_api,
    admin_settings_api,
)
from apps.Bot.views.doctor import (
    doctor_panel_view,
    doctor_orders_api,
    upload_order_result_api,
)
from apps.Bot.views.courier import (
    courier_panel_view,
    courier_staff_me_api,
    courier_orders_api,
    courier_order_done_api,
    courier_order_start_delivery_api,
)
from apps.Bot.views import admin_staff


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER — ViewSet lar
# ─────────────────────────────────────────────────────────────────────────────
router = DefaultRouter()
router.register(r'regions',   RegionViewSet,       basename='region')
router.register(r'districts', DistrictViewSet,     basename='district')
router.register(r'settings',  BotSettingViewSet,   basename='setting')
router.register(r'users',     TelegramUserViewSet, basename='user')
router.register(r'channels',  ChannelViewSet,      basename='channel')
router.register(r'referrals', ReferralViewSet,     basename='referral')
router.register(r'guides',    GuideViewSet,        basename='guide')
router.register(r'appeals',   AppealViewSet,       basename='appeal')
router.register(r'services',  ServiceViewSet,      basename='services-list-api')

# ⚠️ OrderViewSet router orqali EMAS — chunki create_order_with_payment
#    alohida endpoint sifatida ishlaydi (tspay_payment.py da).
#    Faqat confirm_payment va update_status action lari uchun ro'yxatdan o'tamiz.
router.register(r'orders', OrderViewSet, basename='order-actions')

urlpatterns = [

    # ── Router URL lari ───────────────────────────────────────────────────────
    path('', include(router.urls)),

    # ── Staff Me ──────────────────────────────────────────────────────────────
    # GET /api/staff/me?tg_id=...
    path('staff/me', StaffMeAPIView.as_view(), name='staff_me'),

    # ─────────────────────────────────────────────────────────────────────────
    # BUYURTMA (ORDER) endpointlari
    # Diqqat: router.register da 'orders' o'rniga 'order-actions' ishlatilgan,
    #         shuning uchun quyidagi yo'llar conflict bermaydi.
    # ─────────────────────────────────────────────────────────────────────────


    # ── Foydalanuvchi WebApp ──────────────────────────────────────────────────
    path('webapp/', webapp_view, name='webapp'),
    path('webapp/wizard/', wizard_view, name='webapp-wizard'),
    path('webapp/settings/', webapp_public_settings_api, name='webapp-public-settings'),
    path('webapp/profile/', webapp_profile_api, name='webapp-profile'),
    path('webapp/orders/', webapp_orders_api, name='webapp-orders'),
    path('webapp/orders/<int:order_id>/', webapp_order_detail_api, name='webapp-order-detail'),
    path('webapp/results/', webapp_results_api, name='webapp-results'),
    path('webapp/appeal/', webapp_appeal_api, name='webapp-appeal'),

    # ── Admin Panel ───────────────────────────────────────────────────────────
    path('admin-panel/',     admin_panel_view,     name='admin_panel'),
    path('admin/orders/',    admin_orders_api,     name='admin_orders_api'),
    path('admin/services/',  admin_services_api,   name='admin_services_api'),
    path('admin/broadcast/', admin_broadcast_api,  name='admin_broadcast_api'),
    path('admin/stats/',     admin_stats_api,      name='admin_stats_api'),
    path('admin/settings/',  admin_settings_api,   name='admin_settings_api'),

    # ── Shifokor Paneli ───────────────────────────────────────────────────────
    # GET  /api/doctor/panel/
    # GET  /api/doctor/orders?tg_id=...
    # POST /api/doctor/orders/<order_id>/result
    path('doctor/panel/',                        doctor_panel_view,       name='doctor_panel'),
    path('doctor/orders',                        doctor_orders_api,       name='doctor_orders'),
    path('doctor/orders/<str:order_id>/result',  upload_order_result_api, name='upload_result'),

    # ── Kuryer Paneli ─────────────────────────────────────────────────────────
    # GET  /api/courier/           → HTML sahifa
    # GET  /api/courier/staff/me   → kuryer ma'lumotlari
    # GET  /api/courier/orders     → zakazlar ro'yxati
    # POST /api/courier/orders/<id>/start → paid→delivering
    # POST /api/courier/orders/<id>/done  → delivering→done
    path('courier/',                              courier_panel_view,              name='courier_panel'),
    path('courier/staff/me',                      courier_staff_me_api,            name='courier_staff_me'),
    path('courier/orders',                        courier_orders_api,              name='courier_orders'),
    path('courier/orders/<int:order_id>/start',   courier_order_start_delivery_api, name='courier_order_start'),
    path('courier/orders/<int:order_id>/done',    courier_order_done_api,          name='courier_order_done'),
    
    # ── Admin - Xodimlar boshqaruvi ────────────────────────────────────────────
    path('admin/staff/',                   admin_staff.list_staff,                name='admin_staff_list'),
    path('admin/staff/stats/',             admin_staff.get_staff_stats,           name='admin_staff_stats'),
    path('admin/staff/add/',               admin_staff.add_staff,                 name='admin_staff_add'),
    path('admin/staff/remove/',            admin_staff.remove_staff,              name='admin_staff_remove'),
    path('admin/staff/update-role/',       admin_staff.update_staff_role,         name='admin_staff_update_role'),
    path('admin/staff/assign-district/',   admin_staff.assign_courier_district,   name='admin_staff_assign_district'),
    path('admin/staff/<int:staff_id>/',    admin_staff.get_staff_detail,          name='admin_staff_detail'),
    path('admin/districts/',               admin_staff.get_districts_list,        name='admin_districts_list'),
    
    # ── Admin - Barcha foydalanuvchilar ────────────────────────────────────────
    path('admin/users/',                   admin_staff.list_all_users,            name='admin_users_list'),
]