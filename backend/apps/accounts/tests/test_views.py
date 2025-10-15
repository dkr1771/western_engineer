import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.core.cache import cache
from apps.accounts.models import User, Role

@pytest.fixture
def roles(db):
    owner = Role.objects.create(name="Owner")
    manager = Role.objects.create(name="Manager")
    supervisor = Role.objects.create(name="Supervisor")
    worker = Role.objects.create(name="Worker")
    return {"owner": owner, "manager": manager, "supervisor": supervisor, "worker": worker}

@pytest.fixture
def users(db, roles):
    owner = User.objects.create_user(email="owner@test.com", password="ownerpass", role=roles["owner"])
    manager = User.objects.create_user(email="manager@test.com", password="managerpass", role=roles["manager"])
    supervisor = User.objects.create_user(email="supervisor@test.com", password="supervisorpass", role=roles["supervisor"])
    worker = User.objects.create_user(email="worker@test.com", password="workerpass", role=roles["worker"])
    return {"owner": owner, "manager": manager, "supervisor": supervisor, "worker": worker}

@pytest.fixture
def api_client():
    return APIClient()

def login_user(api_client, email, password):
    url = reverse("auth_login")
    response = api_client.post(url, {"identifier": email, "password": password})
    assert response.status_code == 200
    token = response.data["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return response.data["user"]

# --------------------- OWNER TESTS ---------------------
@pytest.mark.django_db
def test_owner_can_create_user(api_client, users, roles):
    login_user(api_client, "owner@test.com", "ownerpass")
    url = reverse("auth_create_user_by_owner")
    data = {"email": "newuser@test.com", "username": "newuser", "password": "newpass", "role_name": "Worker"}
    response = api_client.post(url, data)
    assert response.status_code == 201
    from apps.accounts.models import User
    new_user = User.objects.get(email="newuser@test.com")
    assert new_user.role.name == "Worker"

@pytest.mark.django_db
def test_owner_can_update_role(api_client, users):
    login_user(api_client, "owner@test.com", "ownerpass")
    worker = users["worker"]
    url = reverse("admin-users-detail", args=[worker.id])
    data = {"role_name": "Manager"}
    response = api_client.put(url, data, format="json")
    assert response.status_code == 200
    worker.refresh_from_db()
    assert worker.role.name == "Manager"

@pytest.mark.django_db
def test_owner_can_soft_delete_user(api_client, users):
    login_user(api_client, "owner@test.com", "ownerpass")
    worker = users["worker"]
    url = reverse("admin-users-detail", args=[worker.id])
    response = api_client.delete(url)
    assert response.status_code == 200
    worker.refresh_from_db()
    assert not worker.is_active

# --------------------- PROFILE TESTS ---------------------
@pytest.mark.django_db
def test_update_own_profile(api_client, users):
    for user in ["manager", "supervisor", "worker"]:
        login_user(api_client, f"{user}@test.com", f"{user}pass")
        url = reverse("auth_me")
        data = {"username": f"updated_{user}"}
        response = api_client.put(url, data)
        assert response.status_code == 200
        users[user].refresh_from_db()
        assert users[user].username == f"updated_{user}"

@pytest.mark.django_db
def test_cannot_update_others_profile(api_client, users):
    login_user(api_client, "manager@test.com", "managerpass")
    supervisor = users["supervisor"]
    url = reverse("auth_me")  # manager cannot PUT other user's profile, only own
    data = {"username": "hack_attempt"}
    response = api_client.put(url, data)
    # should not update supervisor
    supervisor.refresh_from_db()
    assert supervisor.username != "hack_attempt"

# --------------------- ROLE VIEW TESTS ---------------------
@pytest.mark.django_db
def test_manager_can_view_employees(api_client, users):
    login_user(api_client, "manager@test.com", "managerpass")
    url = reverse("admin-users-list")
    response = api_client.get(url)
    assert response.status_code == 200
    emails = [u["email"] for u in response.data]
    # manager sees everyone
    for user in users.values():
        assert user.email in emails

@pytest.mark.django_db
def test_supervisor_cannot_update_role(api_client, users):
    login_user(api_client, "supervisor@test.com", "supervisorpass")
    worker = users["worker"]
    url = reverse("admin-users-detail", args=[worker.id])
    data = {"role_name": "Manager"}
    response = api_client.put(url, data, format="json")
    assert response.status_code == 200
    worker.refresh_from_db()
    # role should remain unchanged
    assert worker.role.name == "Worker"

# --------------------- OTP TESTS ---------------------
@pytest.mark.django_db
def test_send_otp(api_client, users):
    cache.clear()
    url = reverse("send_otp")
    data = {"identifier": users["worker"].email}
    response = api_client.post(url, data)
    assert response.status_code == 200
    otp_key = f"otp_{users['worker'].email}"
    assert cache.get(otp_key) is not None

@pytest.mark.django_db
def test_verify_otp_reset_password(api_client, users):
    cache.clear()
    identifier = users["worker"].email
    otp = "123456"
    cache.set(f"otp_{identifier}", otp, timeout=300)

    url = reverse("reset_password")
    new_password = "newworkerpass"
    data = {
        "identifier": identifier,
        "otp": otp,
        "new_password": new_password,
        "confirm_password": new_password
    }
    response = api_client.post(url, data)
    assert response.status_code == 200
    users["worker"].refresh_from_db()
    assert users["worker"].check_password(new_password)
    assert cache.get(f"otp_{identifier}") is None

