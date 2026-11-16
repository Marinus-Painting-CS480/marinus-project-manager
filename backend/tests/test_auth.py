from apps.accounts.models import Role, User


def test_csrf_endpoint_sets_cookie(client, db):
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    assert "csrftoken" in response.cookies


def test_login_and_me(api_client, owner):
    client = api_client()
    response = client.post_json(
        "/api/auth/login", {"email": "OWNER@test.local", "password": "pw-12345-test"}
    )
    assert response.status_code == 200
    assert response.json()["role"] == "owner"
    assert client.get("/api/auth/me").json()["email"] == "owner@test.local"


def test_wrong_password_is_rejected(api_client, owner):
    response = api_client().post_json(
        "/api/auth/login", {"email": "owner@test.local", "password": "wrong"}
    )
    assert response.status_code == 401


def test_inactive_user_cannot_sign_in(api_client, db):
    User.objects.create_user(
        email="gone@test.local", name="Gone", password="pw-12345-test", is_active=False
    )
    response = api_client().post_json(
        "/api/auth/login", {"email": "gone@test.local", "password": "pw-12345-test"}
    )
    assert response.status_code == 401


def test_api_requires_sign_in(api_client, db):
    assert api_client().get("/api/auth/me").status_code == 401
    assert api_client().get("/api/projects").status_code == 401


def test_logout(api_client, owner):
    client = api_client(owner)
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_change_language(api_client, employee):
    response = api_client(employee).patch_json("/api/auth/me", {"locale": "es"})
    assert response.json()["locale"] == "es"


def test_only_office_can_list_users(api_client, owner, employee):
    assert api_client(employee).get("/api/users").status_code == 403
    users = api_client(owner).get(f"/api/users?role={Role.EMPLOYEE}").json()
    assert [u["email"] for u in users] == ["worker1@test.local"]
