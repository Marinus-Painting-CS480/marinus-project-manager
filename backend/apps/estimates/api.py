"""Estimates and proposals (office staff), plus the customer's public proposal link."""

from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError
from ninja.throttling import AnonRateThrottle

from apps.accounts.permissions import require_office
from apps.audit.models import log_action
from apps.estimates import services
from apps.estimates.models import Estimate, Proposal, ProposalStatus, QualityTier
from apps.estimates.schemas import (
    ApproveIn,
    ApproveOut,
    EstimateIn,
    EstimateOut,
    ProposalLinkOut,
    ProposalOut,
    PublicProposalOut,
    QualityTierOut,
)
from apps.projects.models import Project

router = Router()


def _estimate(estimate_id: int) -> Estimate:
    queryset = Estimate.objects.select_related("project", "tier").prefetch_related(
        "items__scope_item__area", "proposals__approval"
    )
    return get_object_or_404(queryset, pk=estimate_id)


def _link(proposal: Proposal, raw_token: str) -> dict:
    path = services.proposal_path(raw_token)
    return {"proposal": proposal, "path": path, "url": services.absolute_url(path)}


@router.get("/quality-tiers", response=list[QualityTierOut], tags=["estimates"])
def list_quality_tiers(request):
    """Active tiers. Office staff edit the wording in the Django admin."""
    require_office(request)
    return QualityTier.objects.filter(active=True)


@router.post("/projects/{project_id}/estimate", response=EstimateOut, tags=["estimates"])
def start_estimate(request, project_id: int):
    """Open the project's estimate, creating it the first time."""
    require_office(request)
    project = get_object_or_404(Project, pk=project_id)
    estimate = services.start_estimate(project, request.user)
    return _estimate(estimate.id)


@router.get("/estimates/{estimate_id}", response=EstimateOut, tags=["estimates"])
def get_estimate(request, estimate_id: int):
    require_office(request)
    return _estimate(estimate_id)


@router.put("/estimates/{estimate_id}", response=EstimateOut, tags=["estimates"])
def save_estimate(request, estimate_id: int, payload: EstimateIn):
    """Save tier, prices and lines. Totals in the response are calculated by the server."""
    require_office(request)
    services.save_estimate(_estimate(estimate_id), payload, request.user)
    return _estimate(estimate_id)


@router.post(
    "/estimates/{estimate_id}/proposals", response={201: ProposalLinkOut}, tags=["proposals"]
)
def send_proposal(request, estimate_id: int):
    """Freeze a new proposal version and get its private link (shown only once)."""
    require_office(request)
    proposal, raw_token = services.create_proposal(_estimate(estimate_id), request.user)
    return 201, _link(proposal, raw_token)


@router.post("/proposals/{proposal_id}/link", response=ProposalLinkOut, tags=["proposals"])
def new_link(request, proposal_id: int):
    """Copy Link: makes a fresh link because old links are never stored. Old link stops."""
    require_office(request)
    proposal = get_object_or_404(Proposal, pk=proposal_id)
    return _link(proposal, services.new_proposal_link(proposal, request.user))


@router.post("/proposals/{proposal_id}/email", response=ProposalLinkOut, tags=["proposals"])
def email_proposal(request, proposal_id: int):
    """Send by Email (if the customer has an email). Also returns the link as a fallback."""
    require_office(request)
    proposal = get_object_or_404(
        Proposal.objects.select_related("estimate__project__customer"), pk=proposal_id
    )
    return _link(proposal, services.email_proposal(proposal, request.user))


@router.post("/proposals/{proposal_id}/revoke", response=ProposalOut, tags=["proposals"])
def revoke_proposal(request, proposal_id: int):
    require_office(request)
    proposal = get_object_or_404(Proposal, pk=proposal_id)
    if proposal.status != ProposalStatus.SENT:
        raise HttpError(409, "Only a proposal waiting for the customer can be revoked.")
    proposal.status = ProposalStatus.REVOKED
    proposal.save(update_fields=["status"])
    log_action(request.user, "proposal.revoked", proposal)
    return proposal


# ---------- Public: customer proposal link (no account) ----------


@router.get(
    "/public/proposals/{token}",
    auth=None,
    response=PublicProposalOut,
    tags=["public"],
    throttle=[AnonRateThrottle("60/m")],
)
def public_proposal(request, token: str):
    proposal = services.find_proposal(token)
    services.ensure_open(proposal)
    return proposal


@router.post(
    "/public/proposals/{token}/approve",
    auth=None,
    response=ApproveOut,
    tags=["public"],
    throttle=[AnonRateThrottle("10/m")],
)
def approve(request, token: str, payload: ApproveIn):
    """Customer signs. Safe to submit twice: only one work order is ever created."""
    approval, raw_work_order_token = services.approve_proposal(
        token,
        payload,
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT"),
    )
    return {
        "signer_name": approval.signer_name,
        "signed_at": approval.signed_at,
        "final_amount": approval.final_amount,
        "work_order_path": (
            services.work_order_path(raw_work_order_token) if raw_work_order_token else None
        ),
    }
