"""Intake business logic. Multi-table changes run inside one database transaction."""

from django.db import transaction
from ninja.errors import HttpError

from apps.projects.models import Area, Customer, Project, ProjectStatus, ScopeItem
from apps.projects.schemas import AreaIn, ProjectIn, ScopeItemIn

PROJECT_FIELDS = (
    "title",
    "site_address",
    "project_type",
    "notes",
    "important_instructions",
    "requested_start_date",
    "requested_end_date",
    "estimate_due_date",
)
SCOPE_FIELDS = (
    "description",
    "prep",
    "products",
    "color",
    "sheen",
    "dimensions",
    "included",
    "optional",
    "unit",
    "quantity",
)


def _resolve_customer(data: ProjectIn) -> Customer:
    if data.customer_id is not None:
        customer = Customer.objects.filter(pk=data.customer_id).first()
        if customer is None:
            raise HttpError(422, "Customer not found.")
        return customer
    if data.customer is not None:
        return Customer.objects.create(**data.customer.dict())
    raise HttpError(422, "Choose an existing customer or enter a new one.")


def save_project(project: Project | None, data: ProjectIn, user) -> Project:
    """Create a project, or save the whole intake form of an existing one (Save Draft)."""
    if project is not None and not project.is_editable:
        raise HttpError(409, "This project can no longer be edited.")
    with transaction.atomic():
        if project is None:
            project = Project(created_by=user)
        project.customer = _resolve_customer(data)
        for field in PROJECT_FIELDS:
            setattr(project, field, getattr(data, field))
        project.save()
        _sync_areas(project, data.areas)
    return project


def _sync_areas(project: Project, areas: list[AreaIn]):
    existing = {area.id: area for area in project.areas.all()}
    keep = set()
    for sequence, area_in in enumerate(areas):
        if area_in.id is None:
            area = Area.objects.create(project=project, name=area_in.name, sequence=sequence)
        else:
            area = existing.get(area_in.id)
            if area is None:
                raise HttpError(422, f"Area {area_in.id} does not belong to this project.")
            area.name = area_in.name
            area.sequence = sequence
            area.save(update_fields=["name", "sequence"])
        keep.add(area.id)
        _sync_scope_items(area, area_in.scope_items)
    project.areas.exclude(id__in=keep).delete()


def _sync_scope_items(area: Area, items: list[ScopeItemIn]):
    existing = {item.id: item for item in area.scope_items.all()}
    keep = set()
    for sequence, item_in in enumerate(items):
        values = {field: getattr(item_in, field) for field in SCOPE_FIELDS}
        if item_in.id is None:
            item = ScopeItem.objects.create(area=area, sequence=sequence, **values)
        else:
            item = existing.get(item_in.id)
            if item is None:
                raise HttpError(422, f"Scope item {item_in.id} does not belong to this area.")
            for field, value in values.items():
                setattr(item, field, value)
            item.sequence = sequence
            item.save()
        keep.add(item.id)
    area.scope_items.exclude(id__in=keep).delete()


def submit_for_estimate(project: Project) -> Project:
    if project.status != ProjectStatus.DRAFT:
        raise HttpError(409, "Only draft projects can be submitted for estimate.")
    if not project.areas.exists():
        raise HttpError(422, "Add at least one area before submitting.")
    project.status = ProjectStatus.WAITING_FOR_ESTIMATE
    project.save(update_fields=["status", "updated_at"])
    return project
