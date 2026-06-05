import json

from rest_framework import serializers
from apps.Bot.models.bot import Region, District, BotSetting
from apps.Bot.models.TelegramBot import TelegramUser, Channel, Referral, Guide, Appeal
from apps.Bot.models.orders import Service, Order, Payment
from apps.Bot.models.feedback import Feedback

# --- Bot Settings & Regions ---
class BotSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotSetting
        fields = '__all__'

class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = '__all__'

class RegionSerializer(serializers.ModelSerializer):
    districts = DistrictSerializer(many=True, read_only=True)

    class Meta:
        model = Region
        fields = ['id', 'name', 'districts']

# --- Users ---
class TelegramUserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    next_free_order = serializers.ReadOnlyField()
    is_next_free = serializers.ReadOnlyField()

    class Meta:
        model = TelegramUser
        fields = [
            'id', 'user_id', 'first_name', 'username', 'lang', 'role', 
            'patient_id', 'phone', 'bonus_points', 'order_count', 
            'district', 'is_admin', 'is_active', 'full_name', 
            'next_free_order', 'is_next_free', 'last_active'
        ]
        read_only_fields = ['patient_id', 'bonus_points', 'order_count']

# --- Channels & Marketing ---
class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = '__all__'

class ReferralSerializer(serializers.ModelSerializer):
    referrer_name = serializers.CharField(source='referrer.full_name', read_only=True)
    referred_user_name = serializers.CharField(source='referred_user.full_name', read_only=True)

    class Meta:
        model = Referral
        fields = '__all__'

# --- Support & Content ---
class GuideSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guide
        fields = '__all__'

class AppealSerializer(serializers.ModelSerializer):
    user_details = TelegramUserSerializer(source='user', read_only=True)

    class Meta:
        model = Appeal
        fields = '__all__'

class FeedbackSerializer(serializers.ModelSerializer):
    user_details = TelegramUserSerializer(source='user', read_only=True)
    rating_display = serializers.SerializerMethodField()

    class Meta:
        model = Feedback
        fields = '__all__'
        read_only_fields = ['created_at']

    def get_rating_display(self, obj):
        if obj.rating:
            stars = '⭐' * obj.rating
            return f"{stars} ({obj.rating}/5)"
        return "Baholanmagan"

# --- Kuryer va Buyurtmalar Tizimi ---
class CourierOrderSerializer(serializers.ModelSerializer):
    patientName = serializers.CharField(source='patient.full_name', read_only=True)
    patientAge = serializers.IntegerField(default=25, read_only=True) # Static yoki tug'ilgan yildan hisoblanadi
    districtId = serializers.IntegerField(source='district.id', read_only=True)
    addressNote = serializers.CharField(source='address_note')
    deliverySlot = serializers.CharField(source='delivery_slot')
    pickupSlot = serializers.CharField(source='pickup_slot')
    orderId = serializers.IntegerField(source='id', read_only=True)

    class Meta:
        model = Order
        fields = [
            'orderId', 'patientName', 'patientAge', 'districtId', 
            'addressNote', 'deliverySlot', 'pickupSlot', 
            'latitude', 'longitude', 'status'
        ]


class ServiceSerializer(serializers.ModelSerializer):
    icon_url = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = '__all__'

    def get_icon_url(self, obj):
        if obj.icon:
            request = self.context.get('request')
            url = obj.icon.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['status', 'transaction_id']

def _parse_bool(value):
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in ('true', '1', 'yes', 'ha'):
        return True
    if s in ('false', '0', 'no', "yo'q", 'yoq'):
        return False
    return None


def flatten_serializer_errors(errors):
    """DRF xatolarini foydalanuvchi uchun oddiy matnga aylantirish."""
    if not errors:
        return 'Ma\'lumot noto\'g\'ri'
    if isinstance(errors, str):
        return errors
    if isinstance(errors, list):
        return ' '.join(str(e) for e in errors)
    parts = []
    for key, val in errors.items():
        if isinstance(val, (list, tuple)):
            for item in val:
                parts.append(f'{key}: {item}')
        else:
            parts.append(f'{key}: {val}')
    return ' '.join(parts) if parts else 'Ma\'lumot noto\'g\'ri'


def _parse_complaints(value):
    if value is None or value == '':
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    return []


class OrderCreateSerializer(serializers.ModelSerializer):
    payment_method = serializers.CharField(write_only=True)
    screenshot = serializers.ImageField(required=False, write_only=True)
    phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    complaints = serializers.JSONField(required=False, default=list)
    uses_diaper = serializers.BooleanField(required=False, allow_null=True)

    class Meta:
        model = Order
        fields = [
            'service', 'patient_type', 'patient_name', 'patient_age', 'patient_gender',
            'child_timing', 'uses_diaper', 'complaints', 'custom_complaint',
            'pickup_slot', 'district', 'address_note', 'latitude', 'longitude',
            'payment_method', 'screenshot', 'phone',
        ]
        read_only_fields = ['user', 'base_price', 'extra_fee', 'total_price', 'status', 'courier']
        extra_kwargs = {
            'child_timing': {'required': False, 'allow_null': True, 'allow_blank': True},
            'custom_complaint': {'required': False, 'allow_blank': True},
            'address_note': {'required': False, 'allow_blank': True},
        }

    def validate_complaints(self, value):
        return _parse_complaints(value)

    def validate_uses_diaper(self, value):
        return _parse_bool(value)

    def validate_child_timing(self, value):
        if value in (None, ''):
            return None
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        raw = self.initial_data
        payment_method = raw.get('payment_method')
        if payment_method == 'admin':
            has_file = False
            if request and getattr(request, 'FILES', None) and request.FILES.get('screenshot'):
                has_file = True
                attrs['screenshot'] = request.FILES['screenshot']
            elif attrs.get('screenshot'):
                has_file = True
            if not has_file:
                raise serializers.ValidationError({'screenshot': 'Admin to\'lovi uchun chek rasmi majburiy'})
        if payment_method not in ('admin', 'tpay'):
            raise serializers.ValidationError({'payment_method': 'To\'lov usulini tanlang'})
        if attrs.get('patient_type') == 'child':
            if not attrs.get('child_timing'):
                raise serializers.ValidationError({'child_timing': 'Hojat vaqtini tanlang'})
            if attrs.get('uses_diaper') is None:
                raise serializers.ValidationError({'uses_diaper': 'Taglik ha/yo\'q ni tanlang'})
        else:
            attrs['child_timing'] = None
            attrs['uses_diaper'] = None
        return attrs

    def create(self, validated_data):
        payment_method = validated_data.pop('payment_method')
        screenshot = validated_data.pop('screenshot', None)
        phone = validated_data.pop('phone', None)
        if phone:
            validated_data['contact_phone'] = phone
        
        # Hisob-kitob (Tuman yetkazish narxi + Xizmat narxi)
        service = validated_data['service']
        district = validated_data['district']
        
        base_price = service.price
        extra_fee = 0
        total_price = base_price
        
        validated_data['base_price'] = base_price
        validated_data['extra_fee'] = extra_fee
        validated_data['total_price'] = total_price

        order = Order.objects.create(**validated_data)
        
        # To'lov obyektini yaratish
        Payment.objects.create(
            order=order,
            amount=total_price,
            method=payment_method,
            screenshot=screenshot,
            status='pending'
        )
        return order
