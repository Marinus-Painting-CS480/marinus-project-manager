from django.contrib.auth import authenticate

from apps.accounts.models import Locale, Role, User


def test_new_users_default_to_employee_in_english(db):
    user = User.objects.create_user(email="worker@test.local", name="Worker", password="pw-12345")
    assert user.role == Role.EMPLOYEE
    assert user.locale == Locale.ENGLISH
    assert not user.is_staff


def test_superuser_is_an_owner(db):
    user = User.objects.create_superuser(email="boss@test.local", name="Boss", password="pw-12345")
    assert user.role == Role.OWNER
    assert user.is_staff and user.is_superuser


def test_email_is_stored_lowercase_and_matched_case_insensitively(db):
    User.objects.create_user(email="Mixed.Case@Test.Local", name="Mixed", password="pw-12345")
    assert User.objects.get().email == "mixed.case@test.local"
    assert authenticate(username="MIXED.case@test.local", password="pw-12345") is not None
