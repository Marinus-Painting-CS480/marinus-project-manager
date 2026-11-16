"""Work-order views per role, crew assignment and schedule changes.

Who sees what (playbook 3.4 / 3.5):
- owner, estimator: everything, including financials and every crew member's budget
- employee: assigned jobs only; scope without prices
- subcontractor: assigned jobs only; scope without prices, plus their own budget/hours
- customer (private link): agreed scope, tier, schedule, crew names; no prices or notes
"""

from collections import OrderedDict
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError

from apps.accounts.models import Role, User
from apps.accounts.permissions import FIELD_ROLES, is_office
from apps.audit.models import log_action
from apps.common.money import ZERO, to_money
from apps.estimates.models import EstimateItem
from apps.workorders.models import WorkOrder, WorkOrderAssignment, WorkOrderStatus

SCHEDULE_FIELDS = (
    "status",
    "start_date",
    "arrival_time",
    "estimated_working_days",
    "allowed_work_window",
    "completion_deadline",
)


def work_orders_for(user):
    """The query itself enforces access: crew members can only ever load their own jobs,
    so removing an assignment removes access immediately."""
    queryset = WorkOrder.objects.select_related(
        "project__customer", "approval__proposal__estimate"
    ).prefetch_related("assignments__user")
    if not is_office(user):
        queryset = queryset.filter(assignments__user=user)
    return queryset


def get_work_order_for(user, work_order_id: int) -> WorkOrder:
    # 404 (not 403) for someone else's job, so guessing IDs reveals nothing.
    return get_object_or_404(work_orders_for(user), pk=work_order_id)


# ---------- Building the role-specific views ----------


def _project_ref(work_order):
    project = work_order.project
    return {
        "id": project.id,
        "title": project.title,
        "site_address": project.site_address,
        "project_type": project.project_type,
        "customer_name": project.customer.name,
    }


def _schedule(work_order):
    return {field: getattr(work_order, field) for field in SCHEDULE_FIELDS if field != "status"}


def _crew(work_order):
    return [
        {"name": a.user.name, "is_person_in_charge": a.is_person_in_charge}
        for a in work_order.assignments.all()
    ]


def _scope(snapshot, include_prices: bool):
    """Approved items grouped by area, in the order they were signed."""
    areas = OrderedDict()
    for item in snapshot["items"]:
        line = {
            key: item.get(key, "")
            for key in (
                "description",
                "prep",
                "products",
                "color",
                "sheen",
                "dimensions",
                "unit",
                "quantity",
            )
        }
        line["optional"] = item.get("optional", False)
        if include_prices:
            line["unit_price"] = item["unit_price"]
            line["line_total"] = item["line_total"]
        areas.setdefault(item.get("area") or "General", []).append(line)
    return [{"area": area, "items": items} for area, items in areas.items()]


def _tier(snapshot):
    return {"name": snapshot["tier"]["name"], "description": snapshot["tier"]["description"]}


def _financials(work_order):
    """Contract amount is what the customer signed; costs come from the estimate lines
    that were part of the signed scope."""
    approval = work_order.approval
    estimate = approval.proposal.estimate
    signed_line_ids = [item["id"] for item in approval.accepted_snapshot["items"]]
    material = sum(
        (
            to_money(cost)
            for cost in EstimateItem.objects.filter(id__in=signed_line_ids).values_list(
                "estimated_material_cost", flat=True
            )
        ),
        ZERO,
    )
    contract = to_money(approval.final_amount)
    labor = to_money(contract * estimate.labor_allocation_percent / Decimal(100))
    return {
        "contract_amount": contract,
        "labor_allocation_percent": estimate.labor_allocation_percent,
        "estimated_labor": labor,
        "estimated_material": material,
        "estimated_margin": to_money(contract - labor - material),
    }


def summary_view(work_order, user) -> dict:
    return {
        "id": work_order.id,
        "status": work_order.status,
        "project": _project_ref(work_order),
        "schedule": _schedule(work_order),
        "crew": _crew(work_order),
        "warnings": work_order.schedule_warnings(),
        "contract_amount": work_order.approval.final_amount if is_office(user) else None,
    }


def detail_view(work_order, user) -> dict:
    office = is_office(user)
    snapshot = work_order.approval.accepted_snapshot
    project = work_order.project
    photos = project.photos.select_related("area")
    view = {
        "id": work_order.id,
        "status": work_order.status,
        "project": _project_ref(work_order),
        "important_instructions": project.important_instructions,
        "tier": _tier(snapshot),
        "scope": _scope(snapshot, include_prices=office),
        "exclusions": snapshot.get("exclusions", []),
        "schedule": _schedule(work_order),
        "warnings": work_order.schedule_warnings(),
        "crew": _crew(work_order),
        "photos": [
            {
                "id": photo.id,
                "area": photo.area.name if photo.area else "",
                "caption": photo.caption,
                "url": f"/api/photos/{photo.id}/file",
            }
            for photo in photos
        ],
        "change_notes": [
            {
                "note": note.note,
                "author_name": note.author.name if note.author else "",
                "created_at": note.created_at,
            }
            for note in work_order.change_notes.select_related("author")
        ],
        "financials": None,
        "assignments": None,
        "my_assignment": None,
    }
    if office:
        view["financials"] = _financials(work_order)
        view["assignments"] = [
            {
                "user_id": a.user_id,
                "name": a.user.name,
                "role": a.user.role,
                "is_person_in_charge": a.is_person_in_charge,
                "labor_budget": a.labor_budget,
                "estimated_hours": a.estimated_hours,
            }
            for a in work_order.assignments.all()
        ]
    else:
        mine = next((a for a in work_order.assignments.all() if a.user_id == user.id), None)
        if mine is not None:
            show_budget = user.role == Role.SUBCONTRACTOR
            view["my_assignment"] = {
                "is_person_in_charge": mine.is_person_in_charge,
                "labor_budget": mine.labor_budget if show_budget else None,
                "estimated_hours": mine.estimated_hours if show_budget else None,
            }
    return view


def customer_view(work_order) -> dict:
    snapshot = work_order.approval.accepted_snapshot
    return {
        "status": work_order.status,
        "project": _project_ref(work_order),
        "tier": _tier(snapshot),
        "scope": _scope(snapshot, include_prices=False),
        "exclusions": snapshot.get("exclusions", []),
        "schedule": _schedule(work_order),
        "crew": _crew(work_order),
    }


# ---------- Changes ----------


def update_schedule(work_order, changes: dict, user) -> WorkOrder:
    """Changes only operational data. The signed scope is never touched."""
    old = {field: str(getattr(work_order, field)) for field in changes}
    for field, value in changes.items():
        if field == "allowed_work_window" and value is None:
            value = ""
        setattr(work_order, field, value)
    work_order.save()
    new = {field: str(getattr(work_order, field)) for field in changes}
    log_action(user, "work_order.schedule_changed", work_order, old_values=old, new_values=new)
    return work_order


def set_assignments(work_order, assignments, user) -> WorkOrder:
    user_ids = [a.user_id for a in assignments]
    if len(user_ids) != len(set(user_ids)):
        raise HttpError(422, "Each person can only be assigned once.")
    if sum(1 for a in assignments if a.is_person_in_charge) > 1:
        raise HttpError(422, "Choose at most one person in charge.")
    users = {
        u.id: u for u in User.objects.filter(id__in=user_ids, is_active=True, role__in=FIELD_ROLES)
    }
    missing = set(user_ids) - set(users)
    if missing:
        raise HttpError(422, f"Not active employees/subcontractors: {sorted(missing)}")

    with transaction.atomic():
        old = sorted(work_order.assignments.values_list("user_id", flat=True))
        work_order.assignments.exclude(user_id__in=user_ids).delete()
        for item in assignments:
            WorkOrderAssignment.objects.update_or_create(
                work_order=work_order,
                user_id=item.user_id,
                defaults={
                    "is_person_in_charge": item.is_person_in_charge,
                    "labor_budget": item.labor_budget,
                    "estimated_hours": item.estimated_hours,
                },
            )
        if user_ids and work_order.status == WorkOrderStatus.AWAITING_ASSIGNMENT:
            work_order.status = WorkOrderStatus.SCHEDULED
            work_order.save(update_fields=["status", "updated_at"])
        elif not user_ids and work_order.status == WorkOrderStatus.SCHEDULED:
            work_order.status = WorkOrderStatus.AWAITING_ASSIGNMENT
            work_order.save(update_fields=["status", "updated_at"])
        log_action(
            user,
            "work_order.crew_changed",
            work_order,
            old_values={"user_ids": old},
            new_values={"user_ids": sorted(user_ids)},
        )
    return work_order
