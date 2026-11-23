"""CSRF: the same flow the React client (src/api/client.js) follows. Data is made up."""

from django.test import Client

LOGIN = {"email": "owner@test.local", "password": "pw-12345-test"}


def test_login_without_csrf_token_is_rejected(owner):
    # enforce_csrf_checks=True: the normal test client skips CSRF, so turn it on
    client = Client(enforce_csrf_checks=True)
    response = client.post("/api/auth/login", LOGIN, content_type="application/json")
    assert response.status_code == 403


def test_login_with_csrf_token_is_accepted(owner):
    client = Client(enforce_csrf_checks=True)
    client.get("/api/auth/csrf")  # 1. ask Django for the cookie
    token = client.cookies["csrftoken"].value  # 2. read the cookie
    response = client.post(
        "/api/auth/login",
        LOGIN,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,  # 3. send it as X-CSRFToken
    )
    assert response.status_code == 200
