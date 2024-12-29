from rest_framework import serializers
from .models import Shop, Reward, Redemption

class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'user', 'name', 'max_points', 'img', 'rewards']

class RewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reward
        fields = ['id', 'title', 'description', 'points_required', 'img', 'shop', 'is_visible']

class RedemptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Redemption
        fields = ['id', 'child', 'points_used', 'date_redeemed', 'shop']
