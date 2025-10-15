# apps/accounts/views_admin.py
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from .serializers_admin import AdminUserManageSerializer, CreateUserByOwnerSerializer
from .serializers import UserSerializer
from .permissions import IsAdminOrOwner
from .models import Role

User = get_user_model()


class CreateUserByOwnerView(APIView):
    """
    Only Owner or superuser can create new users with a role.
    Staff/admin without Owner role cannot create users.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        creator = request.user
        owner_role = Role.objects.filter(name__iexact="Owner").first()

        # Only Owner or superuser can create users
        if not ((creator.role and owner_role and creator.role.id == owner_role.id) or creator.is_superuser):
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

        serializer = CreateUserByOwnerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_user = serializer.save()

        return Response(UserSerializer(new_user).data, status=status.HTTP_201_CREATED)


class UserManageViewSet(viewsets.ModelViewSet):
    """
    Admin/Owner can:
    - List all users
    - Retrieve user details
    - Update role/status (Owner or superuser can update role)
    - Soft delete (deactivate)
    """
    queryset = User.objects.all()
    serializer_class = AdminUserManageSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrOwner]

    # Disable POST to prevent duplicate user creation
    http_method_names = ['get', 'put', 'patch', 'delete']

    def update(self, request, *args, **kwargs):
        """
        Only Owner or superuser can update roles.
        Admin/Owner can update status flags (is_active, is_staff, is_superuser).
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        request_user = request.user
        owner_role = Role.objects.filter(name__iexact="Owner").first()

        # Role update logic
        role_name = serializer.validated_data.pop("role_name", None)
        if role_name:
            if (request_user.role and owner_role and request_user.role.id == owner_role.id) or request_user.is_superuser:
                role = Role.objects.get(name__iexact=role_name)
                instance.role = role
            # Ignore role change if not Owner/superuser

        # Update status flags
        instance.is_active = serializer.validated_data.get("is_active", instance.is_active)
        instance.is_staff = serializer.validated_data.get("is_staff", instance.is_staff)
        instance.is_superuser = serializer.validated_data.get("is_superuser", instance.is_superuser)

        instance.save()
        return Response(AdminUserManageSerializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete: deactivate user instead of hard delete.
        """
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({"detail": "User deactivated instead of hard delete."}, status=status.HTTP_200_OK)


