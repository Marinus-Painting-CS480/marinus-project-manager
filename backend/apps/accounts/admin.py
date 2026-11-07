from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm

from apps.accounts.models import User


class MarinusUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "name", "role", "locale")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = MarinusUserCreationForm
    ordering = ("name",)
    list_display = ("name", "email", "role", "locale", "is_active")
    list_filter = ("role", "locale", "is_active", "is_staff")
    search_fields = ("name", "email")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("name", "role", "locale")}),
        ("Access", {"fields": ("is_active", "is_staff", "is_superuser", "groups")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "role", "locale", "password1", "password2"),
            },
        ),
    )
