"""Request/response shapes for estimating and proposals. Money is sent as strings."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from ninja import Field, Schema


class QualityTierOut(Schema):
    id: int
    name: str
    description: str
    version: int


class EstimateItemIn(Schema):
    id: int | None = Field(None, description="Leave empty for a new line.")
    scope_item_id: int | None = Field(None, description="Empty for a grouped price line.")
    description: str = Field(..., min_length=1)
    unit_price: Decimal = Field(Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    quantity: Decimal = Field(Decimal("1"), gt=0, max_digits=10, decimal_places=2)
    optional: bool = False
    estimated_material_cost: Decimal = Field(Decimal("0"), ge=0, max_digits=12, decimal_places=2)


class EstimateIn(Schema):
    tier_id: int | None = None
    labor_allocation_percent: Decimal = Field(Decimal("30"), ge=0, le=100, decimal_places=2)
    terms: str = ""
    items: list[EstimateItemIn] = []


class EstimateItemOut(Schema):
    id: int
    scope_item_id: int | None
    area_name: str
    description: str
    unit_price: Decimal
    quantity: Decimal
    optional: bool
    estimated_material_cost: Decimal
    line_total: Decimal

    @staticmethod
    def resolve_area_name(obj):
        return obj.scope_item.area.name if obj.scope_item_id else ""


class TotalsOut(Schema):
    base_total: Decimal
    optional_total: Decimal
    contract_total: Decimal
    estimated_labor: Decimal
    estimated_material: Decimal
    estimated_margin: Decimal


class ApprovalSummaryOut(Schema):
    signer_name: str
    signed_at: datetime
    final_amount: Decimal
    selected_item_ids: list[int]


class ProposalOut(Schema):
    id: int
    version: int
    status: str
    base_total: Decimal
    expires_at: datetime | None
    created_at: datetime
    approval: ApprovalSummaryOut | None

    @staticmethod
    def resolve_approval(obj):
        return getattr(obj, "approval", None)  # None until the customer signs


class EstimateOut(Schema):
    id: int
    project_id: int
    project_title: str
    project_status: str
    tier: QualityTierOut | None
    labor_allocation_percent: Decimal
    terms: str
    items: list[EstimateItemOut]
    totals: TotalsOut
    proposals: list[ProposalOut]

    @staticmethod
    def resolve_project_title(obj):
        return obj.project.title

    @staticmethod
    def resolve_project_status(obj):
        return obj.project.status

    @staticmethod
    def resolve_totals(obj):
        # Totals with every optional item selected (the estimator's maximum).
        return obj.totals(selected_optional_ids=[i.id for i in obj.items.all()])


class ProposalLinkOut(Schema):
    proposal: ProposalOut
    path: str = Field(..., description="Relative link, e.g. /p/<token>. Shown only once.")
    url: str = Field(..., description="Full link using SITE_URL, for Copy Link or email.")


class PublicProposalOut(Schema):
    """What the customer sees: no costs, margins or internal notes."""

    version: int
    status: str
    expires_at: datetime | None
    snapshot: dict[str, Any]
    approval: ApprovalSummaryOut | None

    @staticmethod
    def resolve_approval(obj):
        return getattr(obj, "approval", None)


class ApproveIn(Schema):
    signer_name: str = Field(..., min_length=1, max_length=200)
    signature: str = Field(
        ...,
        min_length=1,
        max_length=300_000,
        description="Typed name, or a drawn signature as an image data URL.",
    )
    selected_optional_item_ids: list[int] = []
    accept_terms: bool


class ApproveOut(Schema):
    signer_name: str
    signed_at: datetime
    final_amount: Decimal
    work_order_path: str | None = Field(
        None, description="Customer work-order link. Only returned the first time."
    )
