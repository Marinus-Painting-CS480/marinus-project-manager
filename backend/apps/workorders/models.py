"""Field execution: work orders, crew assignments, change notes."""

from django.conf import settings
from django.db import models

from apps.estimates.models import Approval
from apps.projects.models import Project


class WorkOrderStatus(models.TextChoices):
    AWAITING_ASSIGNMENT = "awaiting_assignment", "Approved - awaiting assignment"
    SCHEDULED = "scheduled", "Scheduled"
    IN_PROGRESS = "in_progress", "In progress"
    COMPLETED = "completed", "Completed"


class WorkOrder(models.Model):
    """Created automatically when a customer approves. Its scope comes from the approval
    snapshot (never edited); only schedule, crew and notes change afterwards."""

    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="work_orders")
    # OneToOne = the database guarantees exactly one work order per approval.
    approval = models.OneToOneField(Approval, on_delete=models.PROTECT, related_name="work_order")
    status = models.CharField(
        max_length=30,
        choices=WorkOrderStatus.choices,
        default=WorkOrderStatus.AWAITING_ASSIGNMENT,
    )
    start_date = models.DateField(null=True, blank=True)
    arrival_time = models.TimeField(null=True, blank=True)
    estimated_working_days = models.PositiveSmallIntegerField(null=True, blank=True)
    allowed_work_window = models.CharField(
        max_length=200, blank=True, help_text='Customer-allowed days/hours, e.g. "Mon-Fri 8-5".'
    )
    completion_deadline = models.DateField(null=True, blank=True)
    customer_token_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_date", "id"]

    def __str__(self):
        return f"Work order {self.pk} - {self.project}"

    def schedule_warnings(self) -> list[str]:
        """Simple warnings only; no scheduling optimization (playbook 3.4)."""
        warnings = []
        if not self.start_date:
            warnings.append("missing_start_date")
        if not self.arrival_time:
            warnings.append("missing_arrival_time")
        if not self.completion_deadline:
            warnings.append("missing_completion_deadline")
        if (
            self.start_date
            and self.completion_deadline
            and self.completion_deadline < self.start_date
        ):
            warnings.append("deadline_before_start")
        return warnings


class WorkOrderAssignment(models.Model):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name="assignments")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assignments"
    )
    is_person_in_charge = models.BooleanField(default=False)
    labor_budget = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, help_text="Subcontractors only."
    )
    estimated_hours = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_person_in_charge", "user__name"]
        constraints = [
            models.UniqueConstraint(fields=["work_order", "user"], name="unique_assignment")
        ]

    def __str__(self):
        return f"{self.user} on {self.work_order}"


class ChangeNote(models.Model):
    """Changes after signature are recorded as notes, never by editing the signed scope."""

    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name="change_notes")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="change_notes",
    )
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.note[:60]
