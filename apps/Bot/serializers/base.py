from rest_framework import serializers
from apps.Bot.models.bot import Region, District, BotSetting
from apps.Bot.models.TelegramBot import TelegramUser, Channel, Referral, Guide, Appeal
from apps.Bot.models.orders import Service, Order, Payment

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
    class Meta:
        model = Service
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['status', 'transaction_id']

class OrderCreateSerializer(serializers.ModelSerializer):
    payment_method = serializers.CharField(write_only=True)
    screenshot = serializers.ImageField(required=False, write_only=True)

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ['user', 'base_price', 'extra_fee', 'total_price', 'status']

    def create(self, validated_data):
        payment_method = validated_data.pop('payment_method')
        screenshot = validated_data.pop('screenshot', None)
        
        # Hisob-kitob (Tuman yetkazish narxi + Xizmat narxi)
        service = validated_data['service']
        district = validated_data['district']
        
        base_price = service.price
        extra_fee = district.delivery_price
        total_price = base_price + extra_fee
        
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
