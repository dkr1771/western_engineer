# apps/accounts/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LoginView,
     TokenRefreshViewCustom,
    LogoutView,
    ProfileView,
    SendOTPView,
    VerifyOTPResetPasswordView,
)
from .views_admin import UserManageViewSet, CreateUserByOwnerView

# Regular endpoints
urlpatterns = [
    # Auth endpoints
    path("auth/login/", LoginView.as_view(), name="auth_login"),
    path("auth/refresh/", TokenRefreshViewCustom.as_view(), name="token_refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth_logout"),
    path("auth/me/", ProfileView.as_view(), name="auth_me"),

    # OTP-based password reset
    path("auth/send-otp/", SendOTPView.as_view(), name="send_otp"),
    path("auth/verify-otp-reset/", VerifyOTPResetPasswordView.as_view(), name="verify_otp_reset"),

    # User creation by Owner/Admin
    path("auth/users/create/", CreateUserByOwnerView.as_view(), name="auth_create_user_by_owner"),
   path("auth/users/", UserManageViewSet.as_view({'get': 'list'}), name="admin_user_list"),  # list all users
    path("auth/users/<int:pk>/", UserManageViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'update',
        'delete': 'destroy'
    }), name="admin_user_detail"),  # get/update/deactivate
]



