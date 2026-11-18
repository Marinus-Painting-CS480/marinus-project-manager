"""Work orders: dashboards, role-specific detail, crew assignment, schedule, notes,
and the customer's public work-order link."""

from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError
from ninja.throttling import AnonRateThrottle

from apps.accounts.permissions import is_office, require_office
from apps.audit.models import log_action
from apps.common.tokens import hash_token, new_token
from apps.estimates.services import absolute_url, work_order_path
from apps.workorders import services
from apps.workorders.models import ChangeNote, WorkOrder, WorkOrderStatus
from apps.workorders.schemas import (
    AssignmentsIn,
    ChangeNoteIn,
    CustomerLinkOut,
    CustomerWorkOrderOut,
    ScheduleIn,
    WorkOrderOut,
    WorkOrderSummaryOut,
)

router = Router()


@router.get("/work-orders", response=list[WorkOrderSummaryOut], tags=["work orders"])
def list_work_orders(request, status: WorkOrderStatus | None = None):
    """Office staff: all work orders. Employees/subcontractors: only their assigned jobs
    (completed jobs are hidden unless `?status=completed`)."""
    work_orders = services.work_orders_for(request.user)
    if status:
        work_orders = work_orders.filter(status=status)
    elif not is_office(request.user):
        work_orders = work_orders.exclude(status=WorkOrderStatus.COMPLETED)
    return [services.summary_view(wo, request.user) for wo in work_orders.distinct()[:200]]


@router.get("/work-orders/{work_order_id}", response=WorkOrderOut, tags=["work orders"])
def get_work_order(request, work_order_id: int):
    work_order = services.get_work_order_for(request.user, work_order_id)
    return services.detail_view(work_order, request.user)


@router.patch("/work-orders/{work_order_id}", response=WorkOrderOut, tags=["work orders"])
def update_schedule(request, work_order_id: int, payload: ScheduleIn):
    """Change dates, arrival time, work window or status. Response includes `warnings`
    for missing or conflicting dates."""
    require_office(request)
    work_order = services.get_work_order_for(request.user, work_order_id)
    changes = payload.dict(exclude_unset=True)
    if changes.get("status", "") is None:
        raise HttpError(422, "Status cannot be empty.")
    services.update_schedule(work_order, changes, request.user)
    return services.detail_view(
        services.get_work_order_for(request.user, work_order_id), request.user
    )


@router.put("/work-orders/{work_order_id}/assignments", response=WorkOrderOut, tags=["work orders"])
def set_assignments(request, work_order_id: int, payload: AssignmentsIn):
    require_office(request)
    work_order = services.get_work_order_for(request.user, work_order_id)
    services.set_assignments(work_order, payload.assignments, request.user)
    return services.detail_view(
        services.get_work_order_for(request.user, work_order_id), request.user
    )


@router.post(
    "/work-orders/{work_order_id}/notes", response={201: WorkOrderOut}, tags=["work orders"]
)
def add_change_note(request, work_order_id: int, payload: ChangeNoteIn):
    """Changes after signing are notes. New paid scope needs a new customer approval."""
    require_office(request)
    work_order = services.get_work_order_for(request.user, work_order_id)
    ChangeNote.objects.create(work_order=work_order, author=request.user, note=payload.note)
    return 201, services.detail_view(work_order, request.user)


@router.post(
    "/work-orders/{work_order_id}/customer-link",
    response=CustomerLinkOut,
    tags=["work orders"],
)
def new_customer_link(request, work_order_id: int):
    """A fresh customer link (the old one stops working; links are never stored)."""
    require_office(request)
    work_order = services.get_work_order_for(request.user, work_order_id)
    raw_token = new_token()
    work_order.customer_token_hash = hash_token(raw_token)
    work_order.save(update_fields=["customer_token_hash", "updated_at"])
    log_action(request.user, "work_order.customer_link_rotated", work_order)
    path = work_order_path(raw_token)
    return {"path": path, "url": absolute_url(path)}


@router.get(
    "/public/work-orders/{token}",
    auth=None,
    response=CustomerWorkOrderOut,
    tags=["public"],
    throttle=[AnonRateThrottle("60/m")],
)
def public_work_order(request, token: str):
    """Customer link. Always shows the latest schedule and crew; no notification is sent."""
    work_order = get_object_or_404(
        WorkOrder.objects.select_related("project__customer", "approval").prefetch_related(
            "assignments__user"
        ),
        customer_token_hash=hash_token(token),
    )
    return services.customer_view(work_order)
