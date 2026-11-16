"""Audit trail: who changed what and when (approvals, assignments, schedule changes)."""

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="Empty when a customer acted through a link.",
    )
    action = models.CharField(max_length=60)
    record_type = models.CharField(max_length=60)
    record_id = models.PositiveBigIntegerField()
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["record_type", "record_id"])]

    def __str__(self):
        return f"{self.action} {self.record_type}#{self.record_id}"


def log_action(actor, action, record, old_values=None, new_values=None):
    """Record one change. `actor` may be None (customer link) or an anonymous user."""
    if actor is not None and not getattr(actor, "is_authenticated", False):
        actor = None
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        record_type=record._meta.label_lower,
        record_id=record.pk,
        old_values=old_values,
        new_values=new_values,
    )
