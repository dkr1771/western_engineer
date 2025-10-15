# apps/accounts/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.core.cache import cache
import random
from django.conf import settings
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from .serializers import (
    UserSerializer,
    SendOTPSerializer,
    VerifyOTPSerializer
)
RATE_LIMIT_WINDOW = 600  # 10 minutes
RATE_LIMIT_MAX_ATTEMPTS = 3
User = get_user_model()


# -------------------- LOGIN --------------------
class LoginView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        identifier = request.data.get("identifier")
        password = request.data.get("password")

        if not identifier or not password:
            return Response({"detail": "Both identifier and password are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Allow login using either email or phone
        try:
            if "@" in identifier:
                user = User.objects.get(email=identifier)
            else:
                user = User.objects.get(phone=identifier)
        except User.DoesNotExist:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        user = authenticate(request, username=user.email or user.phone, password=password)
        if not user:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active or getattr(user, "deleted", False):
            return Response({"detail": "Account disabled"}, status=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        })


# -------------------- LOGOUT --------------------
from rest_framework_simplejwt.tokens import RefreshToken, OutstandingToken, BlacklistedToken

class LogoutView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        refresh_token = request.data.get("refresh")
        access_token = request.headers.get("Authorization", "").split("Bearer ")[-1]

        if not refresh_token:
            return Response({"detail": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST)

        # Blacklist the refresh token
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response({"detail": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)

        # Blacklist the access token
        try:
            if access_token:
                for t in OutstandingToken.objects.filter(token=access_token):
                    BlacklistedToken.objects.get_or_create(token=t)
        except Exception:
            pass  # ignore if token not found

        return Response({"detail": "Logged out successfully"}, status=status.HTTP_200_OK)



# -------------------- PROFILE --------------------
class ProfileView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def put(self, request):
        user = request.user
        user.username = request.data.get("username", user.username)
        user.phone = request.data.get("phone", user.phone)
        user.email = request.data.get("email", user.email)
        user.gender = request.data.get("gender", user.gender)
        user.dob = request.data.get("dob", user.dob)
        user.address = request.data.get("address", user.address)
        user.preferred_language = request.data.get("preferred_language", user.preferred_language)

        if request.data.get("password"):
            user.set_password(request.data.get("password"))

        user.save()
        return Response(UserSerializer(user).data)


# -------------------- OTP SYSTEM --------------------
class SendOTPView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["identifier"]

        # 🔒 Rate limiting logic
        rate_key = f"otp_rate_{identifier}"
        attempts = cache.get(rate_key, 0)
        if attempts >= RATE_LIMIT_MAX_ATTEMPTS:
            return Response(
                {"detail": "Too many OTP requests. Try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        cache.set(rate_key, attempts + 1, timeout=RATE_LIMIT_WINDOW)

        # ✅ OTP Generation (6 digits)
        otp = f"{random.randint(100000, 999999)}"
        otp_key = f"otp_{identifier}"
        cache.set(otp_key, otp, timeout=getattr(settings, "OTP_EXPIRY", 300))

        # Send OTP (email/SMS logic)
        # send_mail(...) or send_sms(...)

        return Response({"detail": "OTP sent successfully."}, status=status.HTTP_200_OK)


class VerifyOTPResetPasswordView(APIView):
    """
    Verify OTP and reset password
    """
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identifier = serializer.validated_data["identifier"]
        otp = serializer.validated_data["otp"]
        new_password = serializer.validated_data["new_password"]
        confirm_password = serializer.validated_data["confirm_password"]

        if new_password != confirm_password:
            return Response({"detail": "Passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)

        cached_otp = cache.get(f"otp_{identifier}")
        if not cached_otp or cached_otp != otp:
            return Response({"detail": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)

        # Find user by email or phone
        try:
            if "@" in identifier:
                user = User.objects.get(email=identifier)
            else:
                user = User.objects.get(phone=identifier)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Set new password
        user.set_password(new_password)
        user.save()
        cache.delete(f"otp_{identifier}")

        return Response({"detail": "Password updated successfully"}, status=status.HTTP_200_OK)


class TokenRefreshViewCustom(TokenRefreshView):
    """
    Custom JWT refresh view. Inherits from SimpleJWT's TokenRefreshView.
    You can add custom logic here if needed.
    """
    serializer_class = TokenRefreshSerializer  # Default serializer

    def post(self, request, *args, **kwargs):
        """
        Override post method to add custom response if needed.
        """
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Optional: add extra data to response if needed
        data = serializer.validated_data
        data["custom_info"] = "Token refreshed successfully"  # Example extra info

        return Response(data, status=status.HTTP_200_OK)

