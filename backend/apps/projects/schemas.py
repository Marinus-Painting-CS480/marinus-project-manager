"""Request/response shapes for intake. These appear in /api/docs as the frontend contract."""

from datetime import date, datetime
from decimal import Decimal

from django.utils import timezone
from ninja import Field, Schema

from apps.projects.models import ProjectStatus, ProjectType


class CustomerIn(Schema):
    name: str = Field(..., min_length=1, max_length=200)
    email: str = ""
    phone: str = ""


class CustomerOut(Schema):
    id: int
    name: str
    email: str
    phone: str


class ScopeItemIn(Schema):
    id: int | None = Field(None, description="Leave empty for a new item.")
    description: str = Field(..., min_length=1)
    prep: str = ""
    products: str = ""
    color: str = ""
    sheen: str = ""
    dimensions: str = ""
    included: bool = Field(True, description="false = exclusion")
    optional: bool = False
    unit: str = ""
    quantity: Decimal | None = None


class AreaIn(Schema):
    id: int | None = Field(None, description="Leave empty for a new area.")
    name: str = Field(..., min_length=1, max_length=120)
    scope_items: list[ScopeItemIn] = []


class ProjectIn(Schema):
    """Save Draft sends the whole form. Areas/items missing from the lists are deleted;
    their order in the lists becomes their display order."""

    customer_id: int | None = Field(None, description="An existing customer, or...")
    customer: CustomerIn | None = Field(None, description="...a new customer to create.")
    title: str = Field(..., min_length=1, max_length=200)
    site_address: str = Field(..., min_length=1)
    project_type: ProjectType = ProjectType.INTERIOR
    notes: str = ""
    important_instructions: str = ""
    requested_start_date: date | None = None
    requested_end_date: date | None = None
    estimate_due_date: date | None = None
    areas: list[AreaIn] = []


class ScopeItemOut(Schema):
    id: int
    description: str
    prep: str
    products: str
    color: str
    sheen: str
    dimensions: str
    included: bool
    optional: bool
    unit: str
    quantity: Decimal | None


class PhotoOut(Schema):
    id: int
    area_id: int | None
    caption: str
    content_type: str
    size: int
    uploaded_at: datetime
    url: str

    @staticmethod
    def resolve_url(obj):
        # Always through the permission-checked endpoint, never a public file path.
        return f"/api/photos/{obj.id}/file"


class PhotoUpdateIn(Schema):
    area_id: int | None = None
    caption: str = ""


class AreaOut(Schema):
    id: int
    name: str
    sequence: int
    scope_items: list[ScopeItemOut]


class ProjectOut(Schema):
    id: int
    customer: CustomerOut
    title: str
    site_address: str
    project_type: ProjectType
    status: ProjectStatus
    notes: str
    important_instructions: str
    requested_start_date: date | None
    requested_end_date: date | None
    estimate_due_date: date | None
    areas: list[AreaOut]
    photos: list[PhotoOut]
    has_estimate: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_has_estimate(obj):
        return hasattr(obj, "estimate")


class ProjectSummaryOut(Schema):
    id: int
    title: str
    customer_name: str
    site_address: str
    project_type: ProjectType
    status: ProjectStatus
    estimate_due_date: date | None
    is_overdue: bool
    created_at: datetime

    @staticmethod
    def resolve_customer_name(obj):
        return obj.customer.name

    @staticmethod
    def resolve_is_overdue(obj):
        return bool(
            obj.estimate_due_date
            and obj.status in (ProjectStatus.WAITING_FOR_ESTIMATE, ProjectStatus.ESTIMATING)
            and obj.estimate_due_date < timezone.localdate()
        )
