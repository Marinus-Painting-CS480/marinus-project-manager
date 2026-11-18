"""Estimating, proposals and customer approval.

The approval runs in ONE transaction: record signature -> freeze approved snapshot ->
create the work order. A second "approve" for the same proposal returns the first result
and never creates a second work order (row lock + OneToOne constraint).
"""

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from ninja.errors import HttpError

from apps.audit.models import log_action
from apps.common.money import ZERO, money_str
from apps.common.tokens import hash_token, new_token
from apps.estimates.models import (
    Approval,
    Estimate,
    EstimateItem,
    Proposal,
    ProposalStatus,
    QualityTier,
)
from apps.estimates.schemas import ApproveIn, EstimateIn
from apps.projects.models import Project, ProjectStatus, ScopeItem
from apps.workorders.models import WorkOrder

ESTIMATE_ITEM_FIELDS = (
    "description",
    "unit_price",
    "quantity",
    "optional",
    "estimated_material_cost",
)


def proposal_path(raw_token: str) -> str:
    return f"/p/{raw_token}"


def work_order_path(raw_token: str) -> str:
    return f"/w/{raw_token}"


def absolute_url(path: str) -> str:
    return settings.SITE_URL.rstrip("/") + path


# ---------- Estimates ----------


def start_estimate(project: Project, user) -> Estimate:
    """Create the estimate (once), pre-filled with one line per included scope item."""
    if project.status == ProjectStatus.DRAFT:
        raise HttpError(409, "Submit the project for estimate first.")
    with transaction.atomic():
        estimate, created = Estimate.objects.get_or_create(
            project=project,
            defaults={
                "prepared_by": user,
                "labor_allocation_percent": settings.DEFAULT_LABOR_ALLOCATION_PERCENT,
            },
        )
        if created:
            scope_items = ScopeItem.objects.filter(area__project=project, included=True)
            EstimateItem.objects.bulk_create(
                EstimateItem(
                    estimate=estimate,
                    scope_item=item,
                    description=item.description,
                    quantity=item.quantity or 1,
                    optional=item.optional,
                    sequence=index,
                )
                for index, item in enumerate(scope_items.order_by("area__sequence", "sequence"))
            )
            if project.status == ProjectStatus.WAITING_FOR_ESTIMATE:
                project.status = ProjectStatus.ESTIMATING
                project.save(update_fields=["status", "updated_at"])
    return estimate


def save_estimate(estimate: Estimate, data: EstimateIn, user) -> Estimate:
    if estimate.project.status in (ProjectStatus.APPROVED, ProjectStatus.CANCELLED):
        raise HttpError(409, "This estimate is closed because the project was approved.")
    with transaction.atomic():
        if data.tier_id is None:
            estimate.tier = None
        else:
            estimate.tier = QualityTier.objects.filter(pk=data.tier_id, active=True).first()
            if estimate.tier is None:
                raise HttpError(422, "Choose an active quality tier.")
        estimate.labor_allocation_percent = data.labor_allocation_percent
        estimate.terms = data.terms
        estimate.prepared_by = user
        estimate.save()

        existing = {item.id: item for item in estimate.items.all()}
        project_scope_ids = set(
            ScopeItem.objects.filter(area__project=estimate.project).values_list("id", flat=True)
        )
        keep = set()
        for sequence, item_in in enumerate(data.items):
            if item_in.scope_item_id is not None and item_in.scope_item_id not in project_scope_ids:
                raise HttpError(422, f"Scope item {item_in.scope_item_id} is not in this project.")
            values = {field: getattr(item_in, field) for field in ESTIMATE_ITEM_FIELDS}
            if item_in.id is None:
                item = EstimateItem.objects.create(
                    estimate=estimate,
                    scope_item_id=item_in.scope_item_id,
                    sequence=sequence,
                    **values,
                )
            else:
                item = existing.get(item_in.id)
                if item is None:
                    raise HttpError(422, f"Line {item_in.id} does not belong to this estimate.")
                for field, value in values.items():
                    setattr(item, field, value)
                item.scope_item_id = item_in.scope_item_id
                item.sequence = sequence
                item.save()
            keep.add(item.id)
        estimate.items.exclude(id__in=keep).delete()
    return estimate


# ---------- Proposals ----------


def build_snapshot(estimate: Estimate, version: int) -> dict:
    """Customer-safe frozen copy: scope, tier, prices, exclusions, terms. No costs/margins."""
    project = estimate.project
    items = []
    for item in estimate.items.select_related("scope_item__area"):
        scope = item.scope_item
        items.append(
            {
                "id": item.id,
                "area": scope.area.name if scope else "",
                "description": item.description,
                "prep": scope.prep if scope else "",
                "products": scope.products if scope else "",
                "color": scope.color if scope else "",
                "sheen": scope.sheen if scope else "",
                "dimensions": scope.dimensions if scope else "",
                "unit": scope.unit if scope else "",
                "quantity": str(item.quantity),
                "unit_price": money_str(item.unit_price),
                "line_total": money_str(item.line_total),
                "optional": item.optional,
            }
        )
    exclusions = [
        {"area": scope.area.name, "description": scope.description}
        for scope in ScopeItem.objects.filter(area__project=project, included=False)
        .select_related("area")
        .order_by("area__sequence", "sequence")
    ]
    totals = estimate.totals()
    return {
        "version": version,
        "project": {
            "title": project.title,
            "site_address": project.site_address,
            "project_type": project.project_type,
            "customer_name": project.customer.name,
        },
        "tier": {
            "name": estimate.tier.name,
            "description": estimate.tier.description,
            "version": estimate.tier.version,
        },
        "items": items,
        "exclusions": exclusions,
        "terms": estimate.terms,
        "base_total": money_str(totals["base_total"]),
        "optional_total": money_str(totals["optional_total"]),
    }


def create_proposal(estimate: Estimate, user) -> tuple[Proposal, str]:
    """Freeze the estimate as a new proposal version. Returns (proposal, raw_token)."""
    if estimate.tier is None:
        raise HttpError(422, "Choose a quality tier before sending.")
    if not estimate.items.exists():
        raise HttpError(422, "Add at least one priced line before sending.")
    if estimate.totals()["base_total"] <= ZERO:
        raise HttpError(422, "The total of the required lines must be more than zero.")
    with transaction.atomic():
        project = Project.objects.select_for_update().get(pk=estimate.project_id)
        if project.status in (ProjectStatus.APPROVED, ProjectStatus.CANCELLED):
            raise HttpError(409, "This project is already approved.")
        last = estimate.proposals.aggregate(last=Max("version"))["last"] or 0
        estimate.proposals.filter(status=ProposalStatus.SENT).update(
            status=ProposalStatus.SUPERSEDED
        )
        raw_token = new_token()
        snapshot = build_snapshot(estimate, last + 1)
        proposal = Proposal.objects.create(
            estimate=estimate,
            version=last + 1,
            token_hash=hash_token(raw_token),
            snapshot=snapshot,
            base_total=Decimal(snapshot["base_total"]),
            expires_at=timezone.now() + timedelta(days=settings.PROPOSAL_LINK_DAYS),
            created_by=user,
        )
        project.status = ProjectStatus.PROPOSAL_SENT
        project.save(update_fields=["status", "updated_at"])
        log_action(user, "proposal.sent", proposal, new_values={"version": proposal.version})
    return proposal, raw_token


def new_proposal_link(proposal: Proposal, user) -> str:
    """Make a fresh link (the old one stops working). Raw tokens are never stored."""
    if proposal.status != ProposalStatus.SENT:
        raise HttpError(409, "Only a proposal waiting for the customer can get a new link.")
    raw_token = new_token()
    proposal.token_hash = hash_token(raw_token)
    proposal.save(update_fields=["token_hash"])
    log_action(user, "proposal.link_rotated", proposal)
    return raw_token


def email_proposal(proposal: Proposal, user) -> str:
    customer = proposal.estimate.project.customer
    if not customer.email:
        raise HttpError(422, "This customer has no email address. Use Copy Link instead.")
    raw_token = new_proposal_link(proposal, user)
    send_mail(
        subject=f"Marinus Painting proposal: {proposal.estimate.project.title}",
        message=(
            f"Hello {customer.name},\n\n"
            f"Please review and sign your painting proposal here:\n"
            f"{absolute_url(proposal_path(raw_token))}\n\n"
            "Marinus Painting"
        ),
        from_email=None,  # DEFAULT_FROM_EMAIL
        recipient_list=[customer.email],
    )
    return raw_token


def find_proposal(raw_token: str) -> Proposal:
    proposal = (
        Proposal.objects.select_related("estimate__project")
        .filter(token_hash=hash_token(raw_token))
        .first()
    )
    if proposal is None:
        raise HttpError(404, "This link is not valid.")
    return proposal


def ensure_open(proposal: Proposal):
    if proposal.status in (ProposalStatus.REVOKED, ProposalStatus.SUPERSEDED):
        raise HttpError(410, "This proposal is no longer available. Ask for a new link.")
    if (
        proposal.status == ProposalStatus.SENT
        and proposal.expires_at
        and proposal.expires_at < timezone.now()
    ):
        raise HttpError(410, "This proposal link has expired. Ask for a new link.")


def approve_proposal(raw_token: str, data: ApproveIn, ip_address, user_agent):
    """Returns (approval, raw work-order token or None if it was already approved)."""
    with transaction.atomic():
        proposal = (
            Proposal.objects.select_for_update()
            .select_related("estimate__project")
            .filter(token_hash=hash_token(raw_token))
            .first()
        )
        if proposal is None:
            raise HttpError(404, "This link is not valid.")
        existing = Approval.objects.filter(proposal=proposal).first()
        if existing is not None:
            return existing, None  # duplicate submit: same answer, no second work order
        ensure_open(proposal)
        if not data.accept_terms:
            raise HttpError(422, "Please accept the terms to sign.")

        snapshot = proposal.snapshot
        optional_ids = {item["id"] for item in snapshot["items"] if item["optional"]}
        selected = set(data.selected_optional_item_ids)
        if not selected <= optional_ids:
            raise HttpError(422, "Only optional items can be selected.")
        accepted_items = [
            item for item in snapshot["items"] if not item["optional"] or item["id"] in selected
        ]
        final_amount = sum((Decimal(item["line_total"]) for item in accepted_items), ZERO)
        accepted_snapshot = {
            **snapshot,
            "items": accepted_items,
            "selected_optional_item_ids": sorted(selected),
            "final_amount": money_str(final_amount),
        }

        approval = Approval.objects.create(
            proposal=proposal,
            signer_name=data.signer_name.strip(),
            signature=data.signature,
            ip_address=ip_address,
            user_agent=(user_agent or "")[:300],
            selected_item_ids=sorted(selected),
            accepted_snapshot=accepted_snapshot,
            final_amount=final_amount,
        )
        proposal.status = ProposalStatus.APPROVED
        proposal.save(update_fields=["status"])
        proposal.estimate.proposals.filter(status=ProposalStatus.SENT).update(
            status=ProposalStatus.SUPERSEDED
        )
        project = proposal.estimate.project
        project.status = ProjectStatus.APPROVED
        project.save(update_fields=["status", "updated_at"])

        raw_work_order_token = new_token()
        work_order = WorkOrder.objects.create(
            project=project,
            approval=approval,
            customer_token_hash=hash_token(raw_work_order_token),
        )
        log_action(
            None,
            "proposal.approved",
            approval,
            new_values={
                "signer_name": approval.signer_name,
                "final_amount": money_str(final_amount),
            },
        )
        log_action(None, "work_order.created", work_order)
    return approval, raw_work_order_token
