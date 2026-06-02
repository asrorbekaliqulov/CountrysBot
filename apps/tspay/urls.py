from django.urls import path
from apps.tspay.views.tspay_webhook import tspay_webhook_view
from apps.tspay.views.tspay_payment import (
    create_order_with_payment,
    check_payment_status,
    admin_confirm_payment,
)

urlpatterns = [
        # Yangi buyurtma yaratish + to'lov boshlash (wizard frontend)
    # POST /api/orders/
    path('orders/', create_order_with_payment, name='create_order'),

    # To'lov holatini tekshirish (frontend polling)
    # GET /api/orders/<id>/check_payment/
    path('orders/<int:order_id>/check_payment/', check_payment_status, name='check_payment'),

    # Admin paneldan qo'lda tasdiqlash
    # POST /api/orders/<id>/confirm_payment/
    path('orders/<int:order_id>/confirm_payment/', admin_confirm_payment, name='confirm_payment'),

    # ── TSPay Webhook ─────────────────────────────────────────────────────────
    # POST /api/webhook/tspay/
    # settings.py da: TSPAY_WEBHOOK_URL = "https://domain.uz/api/webhook/tspay/"
    # TSPay ba'zan slashsiz URL chaqiradi — ikkala variant ham kerak
    path('webhook', tspay_webhook_view, name='tspay_webhook_noslash'),
    path('webhook/', tspay_webhook_view, name='tspay_webhook'),

]
