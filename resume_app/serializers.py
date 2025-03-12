from rest_framework import serializers
from .models import AlipayOrder, WeChatOrder, StripeOrder

class AlipayOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlipayOrder
        fields = '__all__'

class WeChatOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeChatOrder
        fields = '__all__'

class StripeOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = StripeOrder
        fields = '__all__'
