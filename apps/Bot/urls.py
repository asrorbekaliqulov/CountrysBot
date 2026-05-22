from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.Bot.views.base import (
    OrderViewSet, RegionViewSet, DistrictViewSet, BotSettingViewSet, ServiceViewSet,
    TelegramUserViewSet, ChannelViewSet, ReferralViewSet,
    GuideViewSet, AppealViewSet, CourierOrderViewSet, 
    wizard_view
)
from django.views.generic import TemplateView

router = DefaultRouter()
router.register(r'regions', RegionViewSet, basename='region')
router.register(r'districts', DistrictViewSet, basename='district')
router.register(r'settings', BotSettingViewSet, basename='setting')
router.register(r'users', TelegramUserViewSet, basename='user')
router.register(r'channels', ChannelViewSet, basename='channel')
router.register(r'referrals', ReferralViewSet, basename='referral')
router.register(r'guides', GuideViewSet, basename='guide')
router.register(r'appeals', AppealViewSet, basename='appeal')
router.register(r'services', ServiceViewSet, basename='services-list-api')
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
    
    # Kuryer paneli uchun Frontend (React) kutayotgan aniq endpoints:
    path('staff/me', TelegramUserViewSet.as_view({'get': 'get_staff_me'}), name='staff-me'),
    path('courier/orders', CourierOrderViewSet.as_view({'get': 'list'}), name='courier-orders'),
    path('courier/orders/<int:pk>/done', CourierOrderViewSet.as_view({'post': 'mark_as_done'}), name='courier-order-done'),



    # 2. Tpay to'lov tizimi muvaffaqiyatli yakunlanganda chaqiriladigan Callback URL
    # (Tpay serveri to'lov holatini bildirish uchun shu endpointga POST so'rovi yuboradi)
    path('payment/tpay-callback/', OrderViewSet.as_view({'post': 'tpay_callback'}), name='tpay-callback'),

    # 3. Foydalanuvchilar Telegram boti orqali kiradigan WebApp sahifasi (HTML)
    # Bu manzilni botdagi WebAppInfo(url="...") qismiga qo'yasiz
    path('webapp/wizard/', wizard_view, name='webapp-wizard'),
]