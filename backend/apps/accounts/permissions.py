from rest_framework import permissions
from .models import RolePermission, UserPermission, UserPermissionScope

def _role_has_permission(role, perm_code):
    if not role:
        return False
    return RolePermission.objects.filter(role=role, permission__code=perm_code).exists()

def _user_direct_permission(user, perm_code, target_scope_type=None, target_scope_id=None):
    """
    Returns:
      True  => explicit grant
      False => explicit revoke
      None  => no explicit user-level override
    """
    qs = UserPermission.objects.filter(user=user, permission__code=perm_code)
    if target_scope_type and target_scope_id is not None:
        qs2 = qs.filter(scope__scope_type=target_scope_type, scope__scope_id=str(target_scope_id))
        up = qs2.first()
        if up:
            return up.allowed
    # check GLOBAL scope
    qs_global = qs.filter(scope__scope_type=UserPermissionScope.SCOPE_GLOBAL)
    if qs_global.exists():
        return qs_global.first().allowed
    # any user permission without scope specific
    up_any = qs.filter(scope__isnull=True).first()
    if up_any:
        return up_any.allowed
    return None

def user_has_permission(user, perm_code, scope_type=None, scope_id=None, target_user_id=None):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True

    # 1) user-specific override for provided scope
    if scope_type and scope_id is not None:
        res = _user_direct_permission(user, perm_code, target_scope_type=scope_type, target_scope_id=scope_id)
        if res is not None:
            return res

    # 2) user-specific override for global
    res = _user_direct_permission(user, perm_code)
    if res is not None:
        return res

    # 3) role default on user (single primary role)
    if user.role and _role_has_permission(user.role, perm_code):
        return True

    # 4) No match -> deny
    return False

class HasPermission(permissions.BasePermission):
    """
    Usage:
      - set view.permission_code = "task.create"
      - optionally set view.permission_scope_type = "SELF" or "GLOBAL" or "CUSTOM"
      - optionally set view.permission_scope_kwarg = "some_kwarg" (value fetched from URL kwargs or query params)
    """
    def has_permission(self, request, view):
        perm_code = getattr(view, "permission_code", None)
        if not perm_code:
            return True  # no permission required for the view
        scope_type = getattr(view, "permission_scope_type", None)
        scope_kw = getattr(view, "permission_scope_kwarg", None)
        scope_id = None
        if scope_kw:
            scope_id = request.parser_context['kwargs'].get(scope_kw) or request.query_params.get(scope_kw)
        # for SELF scope, we may pass target_user_id via kwarg
        target_user_id = None
        if scope_type == UserPermissionScope.SCOPE_SELF:
            # if target_user_id provided in url or default to request.user.user_id
            target_user_id = request.parser_context['kwargs'].get("user_id") or getattr(request.user, "user_id", None)
        return user_has_permission(request.user, perm_code, scope_type, scope_id, target_user_id)
# apps/accounts/permissions.py
from rest_framework.permissions import BasePermission

class IsAdminOrOwner(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (request.user.is_superuser or
             request.user.is_staff or
             (request.user.role and request.user.role.name == "Owner"))
        )
