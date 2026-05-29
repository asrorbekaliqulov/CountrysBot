from django.db import models
from django.utils.timezone import now
from django.db.models import Count
from asgiref.sync import sync_to_async
from apps.Bot.models.bot import District
import random
import string

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone



class TelegramUserManager(BaseUserManager):
    def create_user(self, user_id, lang="uz", **extra_fields):
        user = self.model(user_id=user_id, lang=lang, **extra_fields)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, user_id, lang="uz", **extra_fields):
        extra_fields.setdefault("is_admin", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")
        return self.create_user(user_id, lang, **extra_fields)


def _generate_patient_id():
    """Noyob bemor ID: MED-XXXXXX"""
    chars = string.ascii_uppercase + string.digits
    return "MED-" + "".join(random.choices(chars, k=6))


    
class TelegramUser(models.Model):
    ROLE_CHOICES = [
        ("user",    "Foydalanuvchi"),
        ("courier", "Kuryer"),
        ("doctor",  "Shifokor"),
        ("admin",   "Admin"),
    ]
    LANG_CHOICES = [
        ("uz", "O'zbek"),
        ("ru", "Русский"),
        ("en", "English"),
    ]
    user_id     = models.BigIntegerField(null=False, unique=True, verbose_name="Telegram User ID")
    first_name  = models.CharField(max_length=256, blank=True, null=True, verbose_name="First Name")
    username    = models.CharField(max_length=256, blank=True, null=True, verbose_name="Username")
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name="Date Joined")
    last_active = models.DateTimeField(auto_now=True, verbose_name="Last Active")
    is_admin    = models.BooleanField(default=False, verbose_name="Is Admin")
    is_active   = models.BooleanField(default=True, verbose_name="Is Active")
    lang        = models.CharField(max_length=5, default="uz", choices=LANG_CHOICES, verbose_name="Til")
    role        = models.CharField(max_length=20, default="user", choices=ROLE_CHOICES, verbose_name="Rol")



    # Bemor ma'lumotlari
    patient_id  = models.CharField(
        max_length=20, unique=True, default=_generate_patient_id, verbose_name="Bemor ID"
    )
    phone       = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefon")
    bonus_points = models.IntegerField(default=0, verbose_name="Bonus ballar")
    order_count  = models.IntegerField(default=0, verbose_name="Buyurtmalar soni")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefon raqami")
    # Xodim (kuryer/shifokor) uchun
    district    = models.ForeignKey(
        District, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="staff_users", verbose_name="Tuman"
    )

    objects = TelegramUserManager()

    USERNAME_FIELD  = "user_id"
    REQUIRED_FIELDS = []

    class Meta:
        db_table     = "telegram_users"
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["lang"]),
        ]

    def __str__(self):
        return f"{self.patient_id} ({self.user_id})"

    @property
    def full_name(self):
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or str(self.user_id)

    @property
    def next_free_order(self):
        """Keyingi bepul buyurtmaga qolgan sonlar (har 6-chi bepul)."""
        pos = self.order_count % 6
        return 6 - pos if pos != 0 else 6

    @property
    def is_next_free(self):
        """Keyingi buyurtma bepulmi?"""
        return self.order_count > 0 and (self.order_count + 1) % 6 == 0
    
    @classmethod
    async def get_admin_ids(cls):
        """
        Admin bo'lgan userlarning IDlarini qaytaradi.
        """
        return await sync_to_async(
            lambda: list(cls.objects.filter(is_admin=True).values_list('user_id', flat=True))
        )()

    @classmethod
    async def get_today_new_users(cls):
        """
        Bugungi yangi foydalanuvchilarni qaytaradi.
        """
        today = now().date()
        return await sync_to_async(lambda: list(cls.objects.filter(date_joined__date=today)))()

    @classmethod
    async def get_daily_new_users(cls):
        """
        Har bir kun uchun yangi foydalanuvchilar sonini qaytaradi.
        """
        return await sync_to_async(
            lambda: list(cls.objects.values('date_joined__date').annotate(count=Count('id')).order_by('-date_joined__date'))
        )()

    @classmethod
    async def get_total_users(cls):
        """
        Umumiy foydalanuvchilar sonini qaytaradi.
        """
        return await sync_to_async(cls.objects.count)()

    @classmethod
    async def count_admin_users(cls):
        """
        Admin bo'lgan foydalanuvchilar sonini qaytaradi.
        """
        return await sync_to_async(lambda: cls.objects.filter(is_admin=True).count())()



    @classmethod
    async def find_inactive_users(cls, bot_token):
        """
        Nofaol foydalanuvchilarni aniqlaydi.
        :param bot_token: Telegram bot tokeni
        :return: Bloklangan foydalanuvchilar soni
        """
        from telegram import Bot
        from telegram.error import TelegramError

        bot = Bot(token=bot_token)
        blocked_users_count = 0

        # SyncToAsync faqat Django ORM bilan ishlashda kerak
        users = await sync_to_async(lambda: list(cls.objects.all()))()

        for user in users:
            try:
                await bot.send_chat_action(chat_id=user.user_id, action="typing")
            except TelegramError:
                blocked_users_count += 1

        return blocked_users_count

    @classmethod
    async def make_admin(cls, user_id):
        """
        Userni admin qiladi.
        :param user_id: Admin qilinadigan foydalanuvchining Telegram user_id-si
        :return: Yangilangan user obyekti yoki None (user topilmasa)
        """
        try:
            user = await sync_to_async(cls.objects.get)(user_id=user_id)
            user.is_admin = True
            await sync_to_async(user.save)(update_fields=['is_admin'])
            return user
        except cls.DoesNotExist:
            print(f"User with ID {user_id} does not exist.")
            return None

    @classmethod
    async def remove_admin(cls, user_id):
        """
        Userni adminlikdan chiqaradi.
        :param user_id: Adminlikdan chiqariladigan foydalanuvchining Telegram user_id-si
        :return: Yangilangan user obyekti yoki None (user topilmasa)
        """
        try:
            user = await sync_to_async(cls.objects.get)(user_id=user_id)
            user.is_admin = False
            await sync_to_async(user.save)(update_fields=['is_admin'])
            return user
        except cls.DoesNotExist:
            print(f"User with ID {user_id} does not exist.")
            return None

from django.db.models import Count, Min
import logging
import datetime

logger = logging.getLogger(__name__)

def auto_assign_courier(order):
    """
    Buyurtmani tuman bo'yicha eng mos kuryerga avtomat biriktirish algoritmi.
    """
    if not order.district:
        logger.warning(f"Order #{order.id} tumaniga ega emas, kuryer biriktirilmadi.")
        return None

    # 1. Shu tumandagi barcha faol kuryerlarni olamiz
    couriers = TelegramUser.objects.filter(
        role='courier',
        district=order.district,  # yoki region=order.district
        is_active=True # Agar sizda foydalanuvchi faollik maydoni bo'lsa
    )

    if not couriers.exists():
        logger.warning(f"{order.district.name} tumanida hech qanday faol kuryer topilmadi.")
        return None

    # 2. Kuryerlarning ayni paytdagi faol buyurtmalari sonini va eng oxirgi buyurtma olgan vaqtini hisoblaymiz
    # Faol statuslar: 'paid' (kuryerga o'tgan), 'picking' (yo'lda/yig'ilmoqda) va h.k.
    from apps.Bot.models.orders import Order

    couriers_with_stats = couriers.annotate(
        active_orders_count=Count(
            'assigned_orders', # Order modelidagi ForeignKey'ning related_name'i
            filter=~Count('assigned_orders', filter=Order.objects.filter(status__in=['courier_done', 'cancelled']))
        ),
        first_order_time=Min('assigned_orders__created_at') # Eng birinchi buyurtma olgan vaqti
    )

    # 3. Bo'sh kuryerlarni qidiramiz (active_orders_count == 0)
    free_couriers = [c for c in couriers_with_stats if c.active_orders_count == 0]
    
    if free_couriers:
        # Bo'sh kuryerlardan birinchisini olamiz
        chosen_courier = free_couriers[0]
        logger.info(f"Order #{order.id} bo'sh kuryerga biriktirildi: {chosen_courier.tg_id}")
    else:
        # 4. Agar hamma band bo'lsa, eng birinchi zakaz olgan (first_order_time eng kichik) kuryerni tanlaymiz
        # Agar hali umuman zakaz olmagan bo'lsa u allaqachon free_couriers ichida ketgan bo'lardi.
        chosen_courier = sorted(
            couriers_with_stats, 
            key=lambda c: (c.active_orders_count, c.first_order_time or datetime.now())
        )[0]
        logger.info(f"Hamma kuryer band. Order #{order.id} eng birinchi zakaz olgan kuryerga biriktirildi: {chosen_courier.tg_id}")

    order.status = 'paid'
    order.save(update_fields=['status'])
    
    # 💥 TODO: Bu yerda Telegram bot orqali kuryerga bildirishnoma yuborish kodi yozilishi mumkin
    # send_bot_message(chosen_courier.tg_id, f"Sizga yangi buyurtma biriktirildi: #{order.id}")
    
    return chosen_courier

class Channel(models.Model):
    """Kanal yoki guruh haqida ma'lumotlarni saqlash uchun model."""
    CHANNEL_TYPE_CHOICES = [
        ('channel', 'Kanal'),
        ('group', 'Guruh'),
        ('joinrequest', 'JoinRequest'),
    ]

    channel_id = models.CharField(max_length=255, unique=True)  # Kanal ID
    name = models.CharField(max_length=255)  # Kanal nomi
    type = models.CharField(max_length=15, choices=CHANNEL_TYPE_CHOICES)  # Kanal turi
    url = models.URLField(null=True, blank=True)  # Kanalning URL manzili (agar mavjud bo'lsa)

    def __str__(self):
        return self.name


class Referral(models.Model):
    referrer = models.ForeignKey(
        "TelegramUser", on_delete=models.CASCADE, related_name="referred_users", verbose_name="Taklif qiluvchi foydalanuvchi"
    )
    referred_user = models.ForeignKey(
        "TelegramUser", on_delete=models.CASCADE, related_name="referrals", verbose_name="Taklif qilingan foydalanuvchi"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Taklif qilingan sana")
    referral_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Referral narxi", default=0.0
    )

    class Meta:
        verbose_name = "Referral"
        verbose_name_plural = "Referral"

    def __str__(self):
        return f"{self.referrer} → {self.referred_user}"

class Guide(models.Model):
    """
    Foydalanuvchilarga yordam berish uchun qo'llanma
    """
    title = models.CharField(max_length=255, verbose_name="Sarlavha")
    content = models.TextField(verbose_name="Kontent")
    status = models.BooleanField(default=True, verbose_name="Holat")  # True - faol, False - nofaol
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")

    class Meta:
        verbose_name = "Guide"
        verbose_name_plural = "Guides"

    def __str__(self):
        return self.title
    
class Appeal(models.Model):
    """
    Foydalanuvchilarning murojaatlarini saqlash uchun model
    """
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, verbose_name="Foydalanuvchi")
    admin = models.ForeignKey(
        TelegramUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="admin_appeals", verbose_name="Admin"
    )
    message_id = models.BigIntegerField(null=True, blank=True, verbose_name="Murojaat xabar ID")
    message = models.TextField(verbose_name="Murojaat matni")
    status = models.BooleanField(default=False, verbose_name="Holat")  # True - ko'rilgan, False - ko'rilmagan
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    
    class Meta:
        verbose_name = "Appeal"
        verbose_name_plural = "Appeals"
    
    def __str__(self):
        return f"Murojaat: {self.user.first_name} - {self.message[:50]}"


