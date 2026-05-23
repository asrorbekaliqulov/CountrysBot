from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.Bot.views.base import (
    OrderViewSet, RegionViewSet, DistrictViewSet, BotSettingViewSet, ServiceViewSet,
    TelegramUserViewSet, ChannelViewSet, ReferralViewSet,
    GuideViewSet, AppealViewSet, StaffMeAPIView,
    wizard_view, admin_panel_view, admin_orders_api, admin_services_api,
    admin_broadcast_api, admin_stats_api, admin_settings_api
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
    courier_order_start_delivery_api
)

# ── Yagona Router ─────────────────────────────────────────────────────────────
router = DefaultRouter()
router.register(r'regions',   RegionViewSet,      basename='region')
router.register(r'districts', DistrictViewSet,    basename='district')
router.register(r'settings',  BotSettingViewSet,  basename='setting')
router.register(r'users',     TelegramUserViewSet, basename='user')
router.register(r'channels',  ChannelViewSet,     basename='channel')
router.register(r'referrals', ReferralViewSet,    basename='referral')
router.register(r'guides',    GuideViewSet,       basename='guide')
router.register(r'appeals',   AppealViewSet,      basename='appeal')
router.register(r'services',  ServiceViewSet,     basename='services-list-api')
router.register(r'orders',    OrderViewSet,       basename='order')

urlpatterns = [
    # ── Router (ViewSet) URL lari ─────────────────────────────────────────────
    path('', include(router.urls)),

    # ── Staff Me — barcha rollar (admin | doctor | courier | user) ────────────
    # CountrysBot/urls.py: path("api/", include("apps.Bot.urls"))
    # → yakuniy URL: GET /api/staff/me?tg_id=...
    path('staff/me', StaffMeAPIView.as_view(), name='staff_me'),

    # ── Admin panel ───────────────────────────────────────────────────────────
    path('admin-panel/',      admin_panel_view,      name='admin_panel'),
    path('admin/orders/',     admin_orders_api,      name='admin_orders_api'),
    path('admin/services/',   admin_services_api,    name='admin_services_api'),
    path('admin/broadcast/',  admin_broadcast_api,   name='admin_broadcast_api'),
    path('admin/stats/',      admin_stats_api,       name='admin_stats_api'),
    path('admin/settings/',   admin_settings_api,    name='admin_settings_api'),

    # ── To'lov integratsiyalari ───────────────────────────────────────────────
    path('orders/<int:pk>/confirm_payment/',
         OrderViewSet.as_view({'post': 'confirm_payment'}),
         name='order-confirm-payment'),
    path('payment/tpay-callback/',
         OrderViewSet.as_view({'post': 'tpay_callback'}),
         name='tpay-callback'),

    # ── WebApp wizard ─────────────────────────────────────────────────────────
    path('webapp/wizard/', wizard_view, name='webapp-wizard'),

    # ── Shifokor paneli ───────────────────────────────────────────────────────
    # GET  /api/doctor/panel/   → HTML sahifa
    # GET  /api/doctor/orders?tg_id=...
    # POST /api/doctor/orders/<order_id>/result?tg_id=...
    path('doctor/panel/',                          doctor_panel_view,       name='doctor_panel'),
    path('doctor/orders',                          doctor_orders_api,       name='doctor_orders'),
    path('doctor/orders/<str:order_id>/result',    upload_order_result_api, name='upload_result'),

    # ── Kuryer paneli ─────────────────────────────────────────────────────────
    # GET  /api/courier/staff/me?tg_id=...
    # GET  /api/courier/orders?tg_id=...
    # POST /api/courier/orders/<order_id>/done?tg_id=...
    path('courier/', courier_panel_view, name='courier_panel'),
 
    # API endpoints
    path('courier/staff/me', courier_staff_me_api, name='courier_staff_me'),
    path('courier/orders', courier_orders_api, name='courier_orders'),
    path('courier/orders/<int:order_id>/start', courier_order_start_delivery_api, name='courier_order_start'),
    path('courier/orders/<int:order_id>/done', courier_order_done_api, name='courier_order_done'),
]