from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Role
from django.core.cache import cache
import random

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    role = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = User
        fields = ("user_id", "id", "email", "phone", "username", "gender",
                  "dob", "address", "preferred_language", "profile_picture", "role", "is_active", "created_at")


class SendOTPSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=True)  # email or phone

    def validate_identifier(self, value):
        if not User.objects.filter(email=value).exists() and not User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("User not found with given identifier")
        return value


class VerifyOTPSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=True)
    otp = serializers.CharField(required=True)
    new_password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)
