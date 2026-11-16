from django.contrib import admin

from apps.projects.models import Area, Customer, Photo, Project, ScopeItem


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "created_at")
    search_fields = ("name", "email", "phone")


class AreaInline(admin.TabularInline):
    model = Area
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "customer", "project_type", "status", "estimate_due_date")
    list_filter = ("status", "project_type")
    search_fields = ("title", "site_address", "customer__name")
    inlines = [AreaInline]


@admin.register(ScopeItem)
class ScopeItemAdmin(admin.ModelAdmin):
    list_display = ("description", "area", "included", "optional")
    list_filter = ("included", "optional")


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "area", "content_type", "size", "uploaded_at")
    readonly_fields = ("file", "content_type", "size", "uploaded_by", "uploaded_at")
