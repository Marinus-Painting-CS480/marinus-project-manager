"""Walkthrough and intake: customers, projects, areas, scope items, photos."""

import uuid
from pathlib import Path

from django.conf import settings
from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProjectType(models.TextChoices):
    INTERIOR = "interior", "Interior"
    EXTERIOR = "exterior", "Exterior"
    BOTH = "both", "Interior and exterior"


class ProjectStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    WAITING_FOR_ESTIMATE = "waiting_for_estimate", "Waiting for estimate"
    ESTIMATING = "estimating", "Estimating"
    PROPOSAL_SENT = "proposal_sent", "Proposal sent"
    APPROVED = "approved", "Approved"
    CANCELLED = "cancelled", "Cancelled"


# Intake (areas and scope) can be edited until the customer approves.
EDITABLE_STATUSES = (
    ProjectStatus.DRAFT,
    ProjectStatus.WAITING_FOR_ESTIMATE,
    ProjectStatus.ESTIMATING,
    ProjectStatus.PROPOSAL_SENT,
)


class Project(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="projects")
    title = models.CharField(max_length=200)
    site_address = models.TextField()
    project_type = models.CharField(
        max_length=20, choices=ProjectType.choices, default=ProjectType.INTERIOR
    )
    status = models.CharField(
        max_length=30, choices=ProjectStatus.choices, default=ProjectStatus.DRAFT
    )
    notes = models.TextField(blank=True)
    important_instructions = models.TextField(
        blank=True, help_text="Shown first on every employee work order."
    )
    requested_start_date = models.DateField(null=True, blank=True)
    requested_end_date = models.DateField(null=True, blank=True)
    estimate_due_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_projects",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def is_editable(self) -> bool:
        return self.status in EDITABLE_STATUSES


class Area(models.Model):
    """A room, elevation or component of a project (e.g. "Kitchen", "North elevation")."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="areas")
    name = models.CharField(max_length=120)
    sequence = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sequence", "id"]

    def __str__(self):
        return f"{self.project} / {self.name}"


class ScopeItem(models.Model):
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name="scope_items")
    description = models.TextField()
    prep = models.TextField(blank=True)
    products = models.CharField(max_length=200, blank=True)
    color = models.CharField(max_length=120, blank=True)
    sheen = models.CharField(max_length=60, blank=True)
    dimensions = models.CharField(max_length=120, blank=True)
    included = models.BooleanField(default=True, help_text="False means this is an exclusion.")
    optional = models.BooleanField(default=False, help_text="The customer may choose it.")
    unit = models.CharField(max_length=30, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sequence = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sequence", "id"]

    def __str__(self):
        return self.description[:60]


def photo_upload_path(instance, filename):
    # Random file names: never expose the customer's original file name or a guessable path.
    extension = Path(filename).suffix.lower()[:10]
    return f"photos/project_{instance.project_id}/{uuid.uuid4().hex}{extension}"


class Photo(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="photos")
    area = models.ForeignKey(
        Area, on_delete=models.SET_NULL, null=True, blank=True, related_name="photos"
    )
    file = models.FileField(upload_to=photo_upload_path)
    content_type = models.CharField(max_length=50)
    size = models.PositiveIntegerField()
    caption = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_photos",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at", "id"]

    def __str__(self):
        return f"Photo {self.pk} of {self.project}"
