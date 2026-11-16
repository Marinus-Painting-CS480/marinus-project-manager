from django.contrib import admin

from apps.estimates.models import Approval, Estimate, EstimateItem, Proposal, QualityTier


@admin.register(QualityTier)
class QualityTierAdmin(admin.ModelAdmin):
    """Office staff edit tier descriptions here (owner-approved wording only)."""

    list_display = ("name", "version", "active", "sequence")
    list_filter = ("active",)


class EstimateItemInline(admin.TabularInline):
    model = EstimateItem
    extra = 0


@admin.register(Estimate)
class EstimateAdmin(admin.ModelAdmin):
    list_display = ("project", "tier", "labor_allocation_percent", "updated_at")
    inlines = [EstimateItemInline]


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ("estimate", "version", "status", "base_total", "expires_at", "created_at")
    list_filter = ("status",)
    readonly_fields = ("token_hash", "snapshot", "base_total", "version", "created_by")


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    """Signed approvals are evidence: view only, never edited."""

    list_display = ("proposal", "signer_name", "final_amount", "signed_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
