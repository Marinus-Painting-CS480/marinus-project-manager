"""Sign-in with Django session cookies (same origin as the React app) and user lookups."""

from typing import Literal

from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.throttling import AnonRateThrottle

from apps.accounts.models import Role, User
from apps.accounts.permissions import require_office
from apps.common.csrf import enforce_csrf

router = Router()


class CsrfOut(Schema):
    csrf_token: str


class LoginIn(Schema):
    email: str
    password: str


class MeOut(Schema):
    id: int
    email: str
    name: str
    role: str
    locale: str
    is_staff: bool


class MeUpdateIn(Schema):
    locale: Literal["en", "es"]


class UserOut(Schema):
    id: int
    name: str
    email: str
    role: str


@router.get("/auth/csrf", auth=None, response=CsrfOut, tags=["auth"])
def csrf(request):
    """Sets the `csrftoken` cookie. Call once when the app loads, before any POST."""
    return {"csrf_token": get_token(request)}


@router.post(
    "/auth/login",
    auth=None,
    response=MeOut,
    tags=["auth"],
    throttle=[AnonRateThrottle("10/m")],
)
def login_view(request, payload: LoginIn):
    enforce_csrf(request)
    user = authenticate(request, username=payload.email.strip(), password=payload.password)
    if user is None:  # also None for inactive users
        raise HttpError(401, "Invalid email or password.")
    login(request, user)
    return user


@router.post("/auth/logout", response={204: None}, tags=["auth"])
def logout_view(request):
    logout(request)
    return 204, None


@router.get("/auth/me", response=MeOut, tags=["auth"])
def me(request):
    return request.user


@router.patch("/auth/me", response=MeOut, tags=["auth"])
def update_me(request, payload: MeUpdateIn):
    request.user.locale = payload.locale
    request.user.save(update_fields=["locale"])
    return request.user


@router.get("/users", response=list[UserOut], tags=["users"])
def list_users(request, role: Role | None = None):
    """Active users, e.g. `?role=employee` for the crew picker. Office staff only."""
    require_office(request)
    users = User.objects.filter(is_active=True)
    if role:
        users = users.filter(role=role)
    return users
