from django.contrib import admin
from ..models.TelegramBot import TelegramUser, Channel, Referral, Guide, Appeal
from ..models.feedback import Feedback
from django.contrib import admin
from unfold.admin import ModelAdmin


@admin.register(TelegramUser)
class UserAdmin(ModelAdmin):
    list_display = ("user_id", "first_name", "username", "is_active", "is_admin", "date_joined", "last_active")
    list_filter = ("is_active", "is_admin")
    search_fields = ("username", "first_name")
    ordering = ("user_id",)
    list_editable = ("is_active", "is_admin")


@admin.register(Channel)
class ChannelAdmin(ModelAdmin):
    list_display = ('name', 'type', 'url', 'channel_id')  # Jadval ustunlari
    list_filter = ('type',)  # Filtrlash uchun ustunlar
    search_fields = ('name', 'channel_id')  # Qidiruv uchun ustunlar


@admin.register(Referral)
class ReferralAdmin(ModelAdmin):
    list_display = ('referrer', 'referred_user', 'created_at')  # Jadval ustunlari
    search_fields = ('referrer__username', 'referred_user__username')  # Qidiruv uchun ustunlar

@admin.register(Guide)
class GuideAdmin(ModelAdmin):
    list_display = ('title', 'status', 'created_at')
    search_fields = ('title', 'content')

@admin.register(Appeal)
class AppealAdmin(ModelAdmin):
    list_display = ('user', 'message', 'created_at')
    search_fields = ('user__username', 'message')
    list_filter = ('created_at',)


@admin.register(Feedback)
class FeedbackAdmin(ModelAdmin):
    """Fikr va baholash boshqaruvi"""
    list_display = ('user', 'rating_display', 'text_preview', 'is_suggestion_only', 'created_at')
    list_filter = ('rating', 'is_suggestion_only', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'text')
    readonly_fields = ('created_at',)
    actions = ['show_rating_stats']

    fieldsets = (
        ("Foydalanuvchi", {
            'fields': ('user',),
        }),
        ("Baholash", {
            'fields': ('rating', 'is_suggestion_only'),
        }),
        ("Fikr matni", {
            'fields': ('text',),
        }),
        ("Ma'lumotlar", {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    @display(description="Baholash")
    def rating_display(self, obj):
        if obj.rating:
            stars = '⭐' * obj.rating
            return f"{stars} ({obj.rating}/5)"
        return "Baholanmagan"

    @display(description="Fikr matni")
    def text_preview(self, obj):
        if obj.text:
            if len(obj.text) > 50:
                return f"{obj.text[:50]}..."
            return obj.text
        return "Matn yo'q"

    @action(description="📊 Reyting statistikasini ko'rsatish")
    def show_rating_stats(self, request, queryset):
        """Admin panelida reyting statistikasini ko'rsatish"""
        from apps.Bot.models.feedback import Feedback
        
        stats = Feedback.get_rating_stats()
        
        message = f"""
📊 <b>Reyting Statistikasi</b>

⭐️ <b>O'rtacha reyting:</b> {stats['average_rating']}/5
👥 <b>Jami ovozlar:</b> {stats['total_votes']}

📈 <b>Baholash taqsimoti:</b>
   ⭐ (1): {stats['by_rating'][1]} ta
   ⭐⭐ (2): {stats['by_rating'][2]} ta
   ⭐⭐⭐ (3): {stats['by_rating'][3]} ta
   ⭐⭐⭐⭐ (4): {stats['by_rating'][4]} ta
   ⭐⭐⭐⭐⭐ (5): {stats['by_rating'][5]} ta

👍 <b>Yoqganlar (4-5 yulduz):</b> {stats['liked_count']} ta
😐 <b>Neytral (3 yulduz):</b> {stats['neutral_count']} ta
👎 <b>Yoqmaganlar (1-2 yulduz):</b> {stats['disliked_count']} ta
        """
        
        self.message_user(request, message, messages.SUCCESS)

from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages

# django-unfold uchun kerakli klasslarni import qilamiz
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.decorators import action, display

from apps.Bot.models.orders import Service, Order, Payment
from apps.Bot.models.bot import Region, District, BotSetting

# ==============================================================================
# 1. INLINES (Unfold dizaynidagi ichma-ich bloklar)
# ==============================================================================



class DistrictInline(TabularInline):
    """Viloyat ichida tumanlarni chiroyli jadval ko'rinishida tahrirlash"""
    model = District
    extra = 1
    fields = ('name', 'is_active', 'delivery_price', 'geo_fetched')
    readonly_fields = ('geo_fetched',)


# ==============================================================================
# 2. MODEL ADMINS (Unfold bilan moslashtirilgan asosiy boshqaruv)
# ==============================================================================

@admin.register(Service)
class ServiceAdmin(ModelAdmin):
    """Xizmatlar / Tahlillar boshqaruvi"""
    list_display = ('name_uz', 'name_ru', 'price_display', 'is_active', 'status_badge')
    list_filter = ('is_active',)
    search_fields = ('name_uz', 'name_ru', 'name_en', 'description')
    list_editable = ('is_active',)
    
    fieldsets = (
        ("Xizmat Nomlari (Ko'p tilli)", {
            'fields': ('name_uz', 'name_ru', 'name_en'),
        }),
        ("Moliyaviy va Holat", {
            'fields': ('price', 'is_active', 'description', 'icon'),
        }),
    )

    # TUZATISH: header=True parametridan oddiy tasvirlashda foydalanilmaydi, uni olib tashlaymiz
    @display(description="Narxi (UZS)")
    def price_display(self, obj):
        return f"{obj.price:,.2f} UZS".replace(",", " ")

    @display(description="Unfold Nishoni", boolean=True)
    def status_badge(self, obj):
        return obj.is_active


# ==============================================================================
# 1. INLINES (To'g'rilangan variant)
# ==============================================================================

class PaymentInline(StackedInline):
    model = Payment
    extra = 0
    tab = True
    fields = ('method', 'status', 'amount', 'transaction_id', 'card_mask', 'screenshot_preview', 'screenshot')
    readonly_fields = ('screenshot_preview',)

    def screenshot_preview(self, obj):
        # TUZATISH: format_html ichiga url parametrini argument sifatida uzatamiz {} orqali
        if obj and obj.screenshot:
            return format_html(
                '<a href="{0}" target="_blank">'
                '<img src="{0}" style="max-height: 180px; border-radius: 12px; border: 2px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);"/>'
                '</a>', 
                obj.screenshot.url
            )
        # TUZATISH: Argument yo'q joyda format_html o'rniga oddiy matn yoki {} bilan format_html ishlatiladi
        return format_html('<span class="text-xs text-gray-400 font-medium">{text}</span>', text="Screenshot yuklanmagan")
    screenshot_preview.short_description = "Chek nusxasi"


# ==============================================================================
# 2. ORDER ADMIN (To'g'rilangan variant)
# ==============================================================================

@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ('id', 'patient_name', 'service', 'patient_type_badge', 'total_price_display', 'payment_status', 'status', 'created_at')
    list_filter = ('status', 'patient_type', 'patient_gender', 'created_at', 'district')
    search_fields = ('patient_name', 'user__username', 'user__first_name', 'id', 'pickup_slot')
    list_editable = ('status',)
    inlines = [PaymentInline]
    list_filter_submit = True
    
    fieldsets = (
        ("Asosiy Holat va Miqdori", {'fields': ('user', 'service', 'status')}),
        ("Bemor Shaxsiy Ma'lumotlari", {'fields': ('patient_type', 'patient_name', 'patient_age', 'patient_gender')}),
        ("Bola uchun qo'shimcha (Qadam 4)", {'fields': ('child_timing', 'uses_diaper'), 'classes': ('collapse',)}),
        ("Shikoyatlar ro'yxati (Qadam 5)", {'fields': ('complaints', 'custom_complaint')}),
        ("Yetkazib berish manzil va vaqti", {'fields': ('pickup_slot', 'district', 'address_note', 'latitude', 'longitude')}),
        ("Moliyaviy hisob-kitob", {'fields': ('base_price', 'extra_fee', 'total_price')}),
    )

    @display(description="Jami summa")
    def total_price_display(self, obj):
        return f"{obj.total_price:,.0f} UZS".replace(",", " ")

    @display(description="Bemor turi")
    def patient_type_badge(self, obj):
        return "Katta yoshli 🧑" if obj.patient_type == 'adult' else "Yosh bola 👶"

    # TUZATISH: format_html parametrlarini to'g'ri taqsimlaymiz
    @display(description="To'lov Holati")
    def payment_status(self, obj):
        try:
            # Agar yangi buyurtma qo'shilayotgan bo'lsa (obj.id yo'q bo'lsa) yoki payment bog'lanmagan bo'lsa
            if not obj or not hasattr(obj, 'payment') or not obj.payment:
                return format_html('<span class="text-xs text-gray-400 italic">{text}</span>', text="To'lov yo'q")
                
            payment = obj.payment
            status = payment.status
            method = payment.get_method_display()
            
            if status == 'success':
                return format_html(
                    '<span class="bg-green-50 text-green-700 border border-green-200 px-2.5 py-0.5 rounded-full text-xs font-semibold inline-flex items-center gap-1">'
                    '● {status_text}</span> <span class="text-xs text-gray-400">({method_text})</span>', 
                    status_text="Muvaffaqiyatli", method_text=method
                )
            elif status == 'failed':
                return format_html(
                    '<span class="bg-red-50 text-red-700 border border-red-200 px-2.5 py-0.5 rounded-full text-xs font-semibold inline-flex items-center gap-1">'
                    '● {status_text}</span> <span class="text-xs text-gray-400">({method_text})</span>', 
                    status_text="Xatolik", method_text=method
                )
            else:
                return format_html(
                    '<span class="bg-amber-50 text-amber-700 border border-amber-200 px-2.5 py-0.5 rounded-full text-xs font-semibold inline-flex items-center gap-1">'
                    '● {status_text}</span> <span class="text-xs text-gray-400">({method_text})</span>', 
                    status_text="Kutilmoqda", method_text=method
                )
        except (Payment.DoesNotExist, AttributeError):
            return format_html('<span class="text-xs text-gray-400 italic">{text}</span>', text="To'lov yo'q")
        
@admin.register(Region)
class RegionAdmin(ModelAdmin):
    """Viloyatlar boshqaruvi"""
    list_display = ('id', 'name', 'districts_count')
    search_fields = ('name',)
    inlines = [DistrictInline]

    @display(description="Tumanlar soni")
    def districts_count(self, obj):
        return obj.districts.count()

@admin.register(District)
class DistrictAdmin(ModelAdmin):
    """Tumanlar boshqaruvi va Geopy koordinatalari"""
    list_display = ('name', 'region', 'is_active', 'delivery_price_display', 'geo_fetched_badge', 'coordinates_display')
    list_filter = ('is_active', 'geo_fetched', 'region')
    search_fields = ('name', 'region__name', 'geo_address')
    list_editable = ('is_active',)
    
    # Unfold Actions (Ro'yxatdan tanlab bajariladigan buyruqlar)
    actions = ['refresh_coordinates']

    fieldsets = (
        ("Hududiy bog'liqlik", {
            'fields': ('region', 'name'),
        }),
        ("Xizmat sozlamalari", {
            'fields': ('is_active', 'delivery_price'),
        }),
        ("Geolokatsiya (Geopy Nominatim)", {
            'fields': ('geo_fetched', 'latitude', 'longitude', 'geo_address'),
        }),
    )

    @display(description="Yetkazish narxi")
    def delivery_price_display(self, obj):
        if obj.delivery_price:
            return f"{obj.delivery_price:,} so'm".replace(",", " ")
        return "0 so'm"

    @display(description="Geo Holati", boolean=True)
    def geo_fetched_badge(self, obj):
        return obj.geo_fetched

    @display(description="Koordinatalar (Lat, Lon)")
    def coordinates_display(self, obj):
        if obj.latitude and obj.longitude:
            return f"{obj.latitude:.4f}, {obj.longitude:.4f}"
        
        # 👑 TO'G'RILANDI: HTML ichiga xavfsiz qiymat joylash uchun {} va argument berildi
        return format_html(
            '<span class="text-red-500 font-medium text-xs">{}</span>', 
            "Koordinata yo'q"
        )

    def save_model(self, request, obj, form, change):
        if not change or 'name' in form.changed_data:
            obj.geo_fetched = False
            
        super().save_model(request, obj, form, change)
        
        if not obj.geo_fetched:
            obj.fetch_coordinates(force=True)
            if obj.geo_fetched:
                self.message_user(request, f"{obj.name} uchun geolokatsiya aniqlandi.", messages.SUCCESS)
            else:
                self.message_user(request, f"{obj.name} geolokatsiyasi topilmadi!", messages.WARNING)

    # Unfold mos decoratorli Action funksiyasi
    @action(description="Tanlangan tumanlar koordinatalarini qayta yangilash")
    def refresh_coordinates(self, request, queryset):
        success_count = 0
        for district in queryset:
            district.fetch_coordinates(force=True)
            if district.geo_fetched:
                success_count += 1
        
        self.message_user(
            request, 
            f"{queryset.count()} tuman tekshirildi. {success_count} tasi yangilandi.", 
            messages.SUCCESS
        )
        
@admin.register(BotSetting)
class BotSettingAdmin(ModelAdmin):
    """Bot sozlamalari"""
    list_display = ('key', 'value_trimmed')
    search_fields = ('key', 'value')
    
    def value_trimmed(self, obj):
        if len(obj.value) > 75:
            return f"{obj.value[:75]}..."
        return obj.value
    value_trimmed.short_description = "Qiymati"


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    """To'lovlarni alohida Unfold paneli"""
    list_display = ('id', 'order', 'amount_display', 'method', 'status', 'created_at')
    list_filter = ('method', 'status', 'created_at')
    search_fields = ('transaction_id', 'card_mask', 'order__patient_name')
    readonly_fields = ('screenshot_preview',)
    
    fields = ('order', 'amount', 'method', 'status', 'transaction_id', 'card_mask', 'screenshot', 'screenshot_preview')

    @display(description="To'lov summasi")
    def amount_display(self, obj):
        return f"{obj.amount:,.0f} UZS".replace(",", " ")

    def screenshot_preview(self, obj):
        if obj.screenshot:
            return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-height: 250px; border-radius: 12px; border: 1px solid #e2e8f0;"/></a>', obj.screenshot.url)
        return "Screenshot yuklanmagan"
    screenshot_preview.short_description = "Chek nusxasi"