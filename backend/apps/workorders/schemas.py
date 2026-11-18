"""Work-order shapes. One detail schema serves every role: fields a role may not see are
returned as null (e.g. `financials` is null for employees and subcontractors)."""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated

from ninja import Field, Schema

from apps.workorders.models import WorkOrderStatus


class CrewMemberOut(Schema):
    name: str
    is_person_in_charge: bool


class AssignmentOut(Schema):
    user_id: int
    name: str
    role: str
    is_person_in_charge: bool
    labor_budget: Decimal | None
    estimated_hours: Decimal | None


class MyAssignmentOut(Schema):
    is_person_in_charge: bool
    labor_budget: Decimal | None
    estimated_hours: Decimal | None


class ScopeLineOut(Schema):
    description: str
    prep: str
    products: str
    color: str
    sheen: str
    dimensions: str
    unit: str
    quantity: str
    optional: bool
    unit_price: str | None = Field(None, description="Office staff only.")
    line_total: str | None = Field(None, description="Office staff only.")


class ScopeAreaOut(Schema):
    area: str
    items: list[ScopeLineOut]


class CustomerScopeLineOut(Schema):
    """Scope line for the customer link: no price fields at all."""

    description: str
    prep: str
    products: str
    color: str
    sheen: str
    dimensions: str
    unit: str
    quantity: str
    optional: bool


class CustomerScopeAreaOut(Schema):
    area: str
    items: list[CustomerScopeLineOut]


class ExclusionOut(Schema):
    area: str
    description: str


class TierOut(Schema):
    name: str
    description: str


class ScheduleOut(Schema):
    start_date: date | None
    arrival_time: time | None
    estimated_working_days: int | None
    allowed_work_window: str
    completion_deadline: date | None


class PhotoRefOut(Schema):
    id: int
    area: str
    caption: str
    url: str


class ChangeNoteOut(Schema):
    note: str
    author_name: str
    created_at: datetime


class FinancialsOut(Schema):
    contract_amount: Decimal
    labor_allocation_percent: Decimal
    estimated_labor: Decimal
    estimated_material: Decimal
    estimated_margin: Decimal


class ProjectRefOut(Schema):
    id: int
    title: str
    site_address: str
    project_type: str
    customer_name: str


class WorkOrderSummaryOut(Schema):
    id: int
    status: WorkOrderStatus
    project: ProjectRefOut
    schedule: ScheduleOut
    crew: list[CrewMemberOut]
    warnings: list[str]
    contract_amount: Decimal | None = Field(None, description="Office staff only.")


class WorkOrderOut(Schema):
    id: int
    status: WorkOrderStatus
    project: ProjectRefOut
    important_instructions: str
    tier: TierOut
    scope: list[ScopeAreaOut]
    exclusions: list[ExclusionOut]
    schedule: ScheduleOut
    warnings: list[str]
    crew: list[CrewMemberOut]
    photos: list[PhotoRefOut]
    change_notes: list[ChangeNoteOut]
    financials: FinancialsOut | None = Field(None, description="Owner/estimator only.")
    assignments: list[AssignmentOut] | None = Field(None, description="Owner/estimator only.")
    my_assignment: MyAssignmentOut | None = Field(
        None, description="The signed-in crew member's own assignment (budget/hours)."
    )


class CustomerWorkOrderOut(Schema):
    """Customer link: agreed scope, tier, schedule and crew names. No prices, notes,
    budgets or profit."""

    status: WorkOrderStatus
    project: ProjectRefOut
    tier: TierOut
    scope: list[CustomerScopeAreaOut]
    exclusions: list[ExclusionOut]
    schedule: ScheduleOut
    crew: list[CrewMemberOut]


class ScheduleIn(Schema):
    """Send only the fields you want to change."""

    status: WorkOrderStatus | None = None
    start_date: date | None = None
    arrival_time: time | None = None
    estimated_working_days: Annotated[int, Field(ge=0, le=365)] | None = None
    allowed_work_window: Annotated[str, Field(max_length=200)] | None = None
    completion_deadline: date | None = None


class AssignmentIn(Schema):
    user_id: int
    is_person_in_charge: bool = False
    labor_budget: Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)] | None = None
    estimated_hours: Annotated[Decimal, Field(ge=0, max_digits=7, decimal_places=2)] | None = None


class AssignmentsIn(Schema):
    """The full crew list. Anyone not in the list is removed (and loses access at once)."""

    assignments: list[AssignmentIn]


class ChangeNoteIn(Schema):
    note: str = Field(..., min_length=1)


class CustomerLinkOut(Schema):
    path: str
    url: str
