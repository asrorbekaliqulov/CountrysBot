import uuid
import string
import os
from django.db import models
from django.utils.timezone import now
from apps.Bot.models.TelegramBot import TelegramUser
from apps.Bot.models.bot import District

class Service(models.Model):
    """Xizmatlar/Tahlillar uchun model ( nameUz, nameRu, nameEn bilan )"""
    name_uz = models.CharField(max_length=255, verbose_name="Nomi (UZ)")
    name_ru = models.CharField(max_length=255, verbose_name="Nomi (RU)")
    name_en = models.CharField(max_length=255, verbose_name="Nomi (EN)")
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Narxi (UZS)")
    description = models.TextField(blank=True, null=True, verbose_name="Tavsif (qisqa)")
    icon = models.ImageField(upload_to="service_icons/", blank=True, null=True, verbose_name="Ikonka")
    is_active = models.BooleanField(default=True, verbose_name="Faol")

    class Meta:
        db_table = "services"
        verbose_name = "Xizmat"
        verbose_name_plural = "Xizmatlar"

    def __str__(self):
        return self.name_uz


class Order(models.Model):
    """Barcha qadamlar ma'lumotlarini o'zida jamlovchi asosiy buyurtma modeli"""
    PATIENT_TYPE_CHOICES = [('adult', 'Katta yoshli'), ('child', 'Bola')]
    GENDER_CHOICES = [('male', 'Erkak'), ('female', 'Ayol')]
    TIMING_CHOICES = [('morning', 'Ertalab'), ('day', 'Kundan keyin'), ('evening', 'Kechki payt'), ('irregular', 'Noma`lum')]
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('paid', 'To`langan'),
        ('delivering', 'Yo`lda'),
        ('done', 'Yetkazildi'),  # Kuryer analizni olib keldi / topshirdi
        ('result_pending', 'Natija kutilmoqda'),  # Laboratoriya tahlil jarayoni
        ('result_sent', 'Natija jo`natildi'),  # Mijozga PDF/Natija yuborildi
        ('canceled', 'Bekor qilindi')
    ]

    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name="web_orders", null=True, blank=True)
    service = models.ForeignKey(Service, on_delete=models.PROTECT, verbose_name="Tanlangan xizmat", null=True, blank=True)
    
    patient_type = models.CharField(max_length=10, choices=PATIENT_TYPE_CHOICES, blank=True, null=True)
    patient_name = models.CharField(max_length=255, verbose_name="Bemor F.I.Sh", blank=True, null=True)
    patient_age = models.IntegerField(verbose_name="Yoshi", null=True, blank=True)
    patient_gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    
    # Bola uchun qo'shimcha maydonlar
    child_timing = models.CharField(max_length=20, choices=TIMING_CHOICES, blank=True, null=True)
    uses_diaper = models.BooleanField(null=True, blank=True)
    
    # Shikoyatlar
    complaints = models.JSONField(default=list, blank=True, verbose_name="Shikoyatlar ro'yxati")
    custom_complaint = models.TextField(blank=True, null=True, verbose_name="Boshqa shikoyatlar")
    
    # Yetkazib berish va manzil
    pickup_slot = models.CharField(max_length=50, verbose_name="Olib ketish vaqti", blank=True, null=True)
    district = models.ForeignKey(District, on_delete=models.PROTECT, verbose_name="Tuman", null=True, blank=True)
    address_note = models.TextField(blank=True, null=True, verbose_name="Manzil izohi")
    latitude = models.FloatField(verbose_name="Kenglik", blank=True, null=True)
    longitude = models.FloatField(verbose_name="Uzunlik", blank=True, null=True)
    contact_phone = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="Aloqa telefoni"
    )
    courier = models.ForeignKey(
        TelegramUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_orders",
        verbose_name="Kuryer",
    )

    # Moliyaviy va holat qismlari
    base_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    extra_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "web_orders"
        ordering = ["-created_at"]


class Payment(models.Model):
    """To'lov tizimi (Karta Tpay yoki Admin orqali)"""
    PAY_METHOD_CHOICES = [('admin', 'Admin orqali (Karta/Screnshot)'), ('tpay', 'Tpay (Onlayn Karta)')]
    STATUS_CHOICES = [('pending', 'Kutilmoqda'), ('success', 'Muvaffaqiyatli'), ('failed', 'Xatolik')]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=10, choices=PAY_METHOD_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    
    # Tpay yoki tranzaksiya identifikatorlari
    transaction_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    card_mask = models.CharField(max_length=20, blank=True, null=True, verbose_name="Karta maskasi")
    
    screenshot = models.ImageField(upload_to="payment_screenshots/", blank=True, null=True, verbose_name="Admin uchun chek rasmi")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payments"
    


def get_result_upload_path(instance, filename):
    """Natija fayllarini har bir buyurtma uchun maxsus nom bilan papkada saqlash"""
    ext = filename.split('.')[-1]
    # Faylni buyurtma ID si bilan chiroyli nomlaymiz
    new_filename = f"result_order_{instance.order.id}.{ext}"
    return os.path.join('test_results/', new_filename)

class TestResult(models.Model):
    """Shifokorlar bot orqali tahlil natijalarini yuborganda saqlovchi model"""
    RESULT_STATUS_CHOICES = [
        ('processing', 'Jarayonda / Tekshirilmoqda'),
        ('ready', 'Natija tayyor (Tasdiqlangan)'),
        ('sent', 'Mijozga yuborildi')
    ]

    order = models.OneToOneField(
        Order, 
        on_delete=models.CASCADE, 
        related_name="test_result", 
        verbose_name="Buyurtma"
    )
    
    # Endi shifokor Django User emas, TelegramUser-ga bog'lanadi
    doctor = models.ForeignKey(
        TelegramUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="issued_results",
        verbose_name="Mas'ul Shifokor (Telegram)"
    )
    
    # Shifokor botga yozma yuboradigan matnli xulosa
    doctor_conclusion = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Shifokor xulosasi / Izoh"
    )
    
    # Shifokor botga rasm yoki PDF fayl tashlaganda saqlanadigan joy
    result_file = models.FileField(
        upload_to=get_result_upload_path, 
        blank=True, 
        null=True, 
        verbose_name="Natija fayli (PDF/Rasm)"
    )
    
    status = models.CharField(
        max_length=20, 
        choices=RESULT_STATUS_CHOICES, 
        default='processing',
        verbose_name="Natija holati"
    )
    
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Oxirgi o'zgarish vaqti")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")

    class Meta:
        db_table = "test_results"
        verbose_name = "Tahlil natijasi"
        verbose_name_plural = "Tahlil natijalari"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Natija #{self.id} (Buyurtma #{self.order.id})"