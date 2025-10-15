from django.core.management.base import BaseCommand
from apps.accounts.models import Role, Permission, RolePermission
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = "Seed default roles, permissions, and owner user"

    def handle(self, *args, **options):
        perms = [
            "user.manage",
            "user.create",
            "user.view",
            "user.update",
            "auth.login",
            "auth.logout",
            # domain permissions for later expansion
            "project.create","project.view",
            "task.create","task.view",
            "attendance.checkin","attendance.view",
            "salary.view","salary.manage",
            "material.view","material.manage",
        ]
        for p in perms:
            Permission.objects.get_or_create(code=p)

        roles_map = {
            "Owner": perms,
            "Manager": ["project.create","project.view","task.create","task.view","attendance.view","material.view","user.view"],
            "Supervisor": ["task.view","attendance.view"],
            "Worker": ["task.view","attendance.checkin"],
        }
        for rname, pcodes in roles_map.items():
            role, _ = Role.objects.get_or_create(name=rname)
            for code in pcodes:
                perm = Permission.objects.get(code=code)
                RolePermission.objects.get_or_create(role=role, permission=perm)

        owner_email = "owner@example.com"
        owner_pass = "Owner@123"
        if not User.objects.filter(email=owner_email).exists():
            owner_role = Role.objects.get(name="Owner")
            owner = User.objects.create_user(email=owner_email, password=owner_pass, role=owner_role)
            owner.is_staff = True
            owner.save()
            self.stdout.write(self.style.SUCCESS(f"Created owner {owner_email} / {owner_pass}"))
        else:
            self.stdout.write("Owner user already exists")
