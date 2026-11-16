from django.contrib import admin

from apps.workorders.models import ChangeNote, WorkOrder, WorkOrderAssignment


class AssignmentInline(admin.TabularInline):
    model = WorkOrderAssignment
    extra = 0


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ("project", "status", "start_date", "arrival_time", "completion_deadline")
    list_filter = ("status",)
    readonly_fields = ("approval", "project", "customer_token_hash")
    inlines = [AssignmentInline]


@admin.register(ChangeNote)
class ChangeNoteAdmin(admin.ModelAdmin):
    list_display = ("work_order", "author", "created_at")
