"""Estimating and customer approval: quality tiers, estimates, proposals, approvals."""

from django.conf import settings
from django.db import models

from apps.common.money import ZERO, to_money
from apps.projects.models import Project, ScopeItem


class QualityTier(models.Model):
    """Standard / Premium / High-End. Descriptions are written and approved by Marinus."""

    name = models.CharField(max_length=80)
    description = models.TextField(help_text="Preparation, finish expectations and exclusions.")
    version = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)
    sequence = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sequence", "name"]

    def __str__(self):
        return f"{self.name} (v{self.version})"


class Estimate(models.Model):
    """One estimate per project. Each send to the customer creates a new Proposal version."""

    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="estimate")
    tier = models.ForeignKey(
        QualityTier, on_delete=models.PROTECT, null=True, blank=True, related_name="estimates"
    )
    labor_allocation_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30,
        help_text="Suggested starting assumption only; editable per estimate.",
    )
    terms = models.TextField(blank=True, help_text="Contract terms shown to the customer.")
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="estimates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Estimate for {self.project}"

    def totals(self, selected_optional_ids=None) -> dict:
        """All money is calculated here on the server, never trusted from the browser."""
        items = list(self.items.all())
        selected = set(selected_optional_ids or [])
        base = sum((i.line_total for i in items if not i.optional), ZERO)
        optional = sum((i.line_total for i in items if i.optional), ZERO)
        chosen = [i for i in items if not i.optional or i.id in selected]
        contract = sum((i.line_total for i in chosen), ZERO)
        material = sum((to_money(i.estimated_material_cost) for i in chosen), ZERO)
        labor = to_money(contract * self.labor_allocation_percent / 100)
        return {
            "base_total": to_money(base),
            "optional_total": to_money(optional),
            "contract_total": to_money(contract),
            "estimated_labor": labor,
            "estimated_material": to_money(material),
            "estimated_margin": to_money(contract - labor - material),
        }


class EstimateItem(models.Model):
    """A priced line. Usually linked to a scope item; a grouped price may have none."""

    estimate = models.ForeignKey(Estimate, on_delete=models.CASCADE, related_name="items")
    scope_item = models.ForeignKey(
        ScopeItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="estimate_items"
    )
    description = models.TextField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    optional = models.BooleanField(default=False)
    estimated_material_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sequence = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sequence", "id"]

    def __str__(self):
        return self.description[:60]

    @property
    def line_total(self):
        return to_money(self.unit_price * self.quantity)


class ProposalStatus(models.TextChoices):
    SENT = "sent", "Sent"
    APPROVED = "approved", "Approved"
    REVOKED = "revoked", "Revoked"
    SUPERSEDED = "superseded", "Superseded by a newer version"


class Proposal(models.Model):
    """A frozen, versioned copy of the estimate that the customer sees through a private link."""

    estimate = models.ForeignKey(Estimate, on_delete=models.CASCADE, related_name="proposals")
    version = models.PositiveIntegerField()
    token_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(
        max_length=20, choices=ProposalStatus.choices, default=ProposalStatus.SENT
    )
    snapshot = models.JSONField(help_text="Customer-safe copy of scope, tier, terms and prices.")
    base_total = models.DecimalField(max_digits=12, decimal_places=2)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proposals",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(fields=["estimate", "version"], name="unique_proposal_version")
        ]

    def __str__(self):
        return f"{self.estimate.project} v{self.version}"


class Approval(models.Model):
    """The customer's signature. Never edited after it is created."""

    proposal = models.OneToOneField(Proposal, on_delete=models.PROTECT, related_name="approval")
    signer_name = models.CharField(max_length=200)
    signature = models.TextField(help_text="Typed name or drawn signature (image data URL).")
    signed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    selected_item_ids = models.JSONField(default=list)
    accepted_snapshot = models.JSONField()
    final_amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"Approval of {self.proposal} by {self.signer_name}"
