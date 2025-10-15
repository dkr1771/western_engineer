import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

# --------------------- USER MANAGER ---------------------
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)

# --------------------- USER MODEL ---------------------
class User(AbstractBaseUser, PermissionsMixin):
    user_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    username = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(unique=True, blank=False, null=False)
    phone = models.CharField(max_length=32, blank=True, null=True, unique=True)
    gender = models.CharField(max_length=10, blank=True, null=True)  # Male, Female, Other
    dob = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    preferred_language = models.CharField(max_length=32, default="en")

    # Optional profile picture
    profile_picture = models.ForeignKey(
        'attachments.Attachment',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='profile_for_user'
    )

    # Role relationship
    role = models.ForeignKey("Role", on_delete=models.SET_NULL, null=True, blank=True, related_name="users")

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def soft_delete(self):
        self.deleted = True
        self.is_active = False
        self.save(update_fields=["deleted", "is_active"])

    def __str__(self):
        return self.email

# --------------------- ROLE ---------------------
class Role(models.Model):
    name = models.CharField(max_length=128, unique=True)  # Owner, Manager, Supervisor, Worker
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# --------------------- PERMISSIONS ---------------------
class Permission(models.Model):
    code = models.CharField(max_length=128, unique=True)  # e.g. project.create
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="permission_roles")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("role", "permission")

class UserPermissionScope(models.Model):
    SCOPE_GLOBAL = "GLOBAL"
    SCOPE_SELF = "SELF"
    SCOPE_CUSTOM = "CUSTOM"
    SCOPE_CHOICES = [
        (SCOPE_GLOBAL, "Global"),
        (SCOPE_SELF, "Self"),
        (SCOPE_CUSTOM, "Custom"),
    ]
    id = models.BigAutoField(primary_key=True)
    scope_type = models.CharField(max_length=32, choices=SCOPE_CHOICES, default=SCOPE_GLOBAL)
    scope_id = models.CharField(max_length=128, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.scope_type}:{self.scope_id or 'ALL'}"

class UserPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="custom_user_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="user_permissions_custom")
    scope = models.ForeignKey(UserPermissionScope, on_delete=models.SET_NULL, null=True, blank=True)
    allowed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "permission", "scope")

