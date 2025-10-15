# apps/accounts/serializers_admin.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Role



User = get_user_model()


class AdminUserManageSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(required=False)
    role = serializers.StringRelatedField(read_only=True)  # <-- uses Role.__str__()
    class Meta:
        model = User
        # Expose personal info as read-only to prevent changes
        fields = (
            "id",
            "email",
            "phone",
            "username",
            "gender",
            "dob",
            "address",
            "preferred_language",
            "role_name",
            "is_active",
            "is_staff",
            "is_superuser","role",
        )
        read_only_fields = (
            "id",
            "email",
            "phone",
            "username",
            "gender",
            "dob",
            "address",
            "preferred_language",
        )
    def get_role(self, obj):
        return obj.role.name if obj.role else None

    def validate_role_name(self, value):
        if value and not Role.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("Invalid role_name")
        return value

    def update(self, instance, validated_data):
        request_user = self.context["request"].user
        owner_role = Role.objects.filter(name__iexact="Owner").first()

        # Role update: only Owner or superuser
        role_name = validated_data.pop("role_name", None)
        if role_name:
            if (request_user.role and owner_role and request_user.role.id == owner_role.id) or request_user.is_superuser:
                role = Role.objects.get(name__iexact=role_name)
                instance.role = role

        # Only allow status updates
        instance.is_active = validated_data.get("is_active", instance.is_active)
        instance.is_staff = validated_data.get("is_staff", instance.is_staff)
        instance.is_superuser = validated_data.get("is_superuser", instance.is_superuser)

        instance.save()
        return instance


class CreateUserByOwnerSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    role_name = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ("email", "username", "phone", "preferred_language", "password", "role_name")

    def validate(self, attrs):
        email = attrs.get("email")
        phone = attrs.get("phone")

        if not email and not phone:
            raise serializers.ValidationError("Either email or phone must be provided.")

        return attrs
    def validate_role_name(self, value):
        if not Role.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("Invalid role_name")
        return value

    def create(self, validated_data):
        role_name = validated_data.pop("role_name")
        password = validated_data.pop("password")
        role = Role.objects.get(name__iexact=role_name)
        user = User.objects.create_user(password=password, role=role, **validated_data)
        return user
