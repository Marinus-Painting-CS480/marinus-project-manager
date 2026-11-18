from datetime import timedelta

from django.utils import timezone

from apps.estimates.models import Proposal, ProposalStatus
from apps.projects.models import ProjectStatus
from apps.workorders.models import WorkOrder
from tests.conftest import token_from


def test_estimate_is_prefilled_from_included_scope(api_client, owner, submitted_project):
    estimate = api_client(owner).post(f"/api/projects/{submitted_project.id}/estimate").json()
    assert [i["description"] for i in estimate["items"]] == ["Walls", "Cabinets"]  # no Ceiling
    assert estimate["project_status"] == ProjectStatus.ESTIMATING
    # Opening it again returns the same estimate.
    again = api_client(owner).post(f"/api/projects/{submitted_project.id}/estimate").json()
    assert again["id"] == estimate["id"]


def test_totals_are_calculated_on_the_server(priced_estimate):
    totals = priced_estimate["totals"]
    assert totals["base_total"] == "1000.00"
    assert totals["optional_total"] == "250.00"
    assert totals["contract_total"] == "1250.00"
    assert totals["estimated_labor"] == "375.00"  # 30%
    assert totals["estimated_material"] == "250.00"
    assert totals["estimated_margin"] == "625.00"


def test_crew_cannot_see_estimates(api_client, employee, subcontractor, priced_estimate):
    for user in (employee, subcontractor):
        assert api_client(user).get(f"/api/estimates/{priced_estimate['id']}").status_code == 403


def test_tier_is_required_to_send(api_client, owner, submitted_project):
    client = api_client(owner)
    estimate = client.post(f"/api/projects/{submitted_project.id}/estimate").json()
    response = client.post(f"/api/estimates/{estimate['id']}/proposals")
    assert response.status_code == 422


def test_proposal_link_and_customer_view_hide_costs(api_client, sent_proposal):
    assert sent_proposal["url"].startswith("https://app.test/p/")
    token = token_from(sent_proposal["path"])
    stored = Proposal.objects.get()
    assert token not in stored.token_hash  # only the hash is stored

    response = api_client().get(f"/api/public/proposals/{token}")
    assert response.status_code == 200
    text = response.content.decode()
    for secret in ("estimated_material", "margin", "labor_allocation", "200.00"):
        assert secret not in text
    data = response.json()
    assert data["snapshot"]["base_total"] == "1000.00"
    assert data["snapshot"]["exclusions"] == [{"area": "Hallway", "description": "Ceiling"}]


def test_bad_token_is_404(api_client, db):
    assert api_client().get("/api/public/proposals/not-a-real-token").status_code == 404


def test_customer_approval_creates_exactly_one_work_order(api_client, sent_proposal, approved):
    assert approved["final_amount"] == "1000.00"  # optional cabinets not selected
    assert approved["work_order_path"].startswith("/w/")
    work_order = WorkOrder.objects.get()
    scope = [i["description"] for i in work_order.approval.accepted_snapshot["items"]]
    assert scope == ["Walls"]
    assert work_order.project.status == ProjectStatus.APPROVED

    # Pressing "approve" again does not create a second work order.
    token = token_from(sent_proposal["path"])
    again = api_client().post_json(
        f"/api/public/proposals/{token}/approve",
        {
            "signer_name": "X",
            "signature": "X",
            "selected_optional_item_ids": [],
            "accept_terms": True,
        },
    )
    assert again.status_code == 200
    assert again.json()["work_order_path"] is None
    assert WorkOrder.objects.count() == 1


def test_selected_optional_items_are_added(api_client, sent_proposal):
    token = token_from(sent_proposal["path"])
    cabinets = next(
        i for i in Proposal.objects.get().snapshot["items"] if i["description"] == "Cabinets"
    )
    response = api_client().post_json(
        f"/api/public/proposals/{token}/approve",
        {
            "signer_name": "C",
            "signature": "C",
            "selected_optional_item_ids": [cabinets["id"]],
            "accept_terms": True,
        },
    )
    assert response.json()["final_amount"] == "1250.00"


def test_approval_validation(api_client, sent_proposal):
    token = token_from(sent_proposal["path"])
    walls = next(i for i in Proposal.objects.get().snapshot["items"] if not i["optional"])
    base = {"signer_name": "C", "signature": "C", "selected_optional_item_ids": []}
    client = api_client()
    url = f"/api/public/proposals/{token}/approve"
    assert client.post_json(url, {**base, "accept_terms": False}).status_code == 422
    bad_selection = {**base, "selected_optional_item_ids": [walls["id"]], "accept_terms": True}
    assert client.post_json(url, bad_selection).status_code == 422
    assert not WorkOrder.objects.exists()


def test_revoked_expired_and_superseded_links_stop_working(api_client, owner, priced_estimate):
    client = api_client(owner)
    first = client.post(f"/api/estimates/{priced_estimate['id']}/proposals").json()
    second = client.post(f"/api/estimates/{priced_estimate['id']}/proposals").json()
    customer = api_client()
    assert customer.get(f"/api/public/proposals/{token_from(first['path'])}").status_code == 410
    assert second["proposal"]["version"] == 2

    Proposal.objects.filter(version=2).update(expires_at=timezone.now() - timedelta(days=1))
    assert customer.get(f"/api/public/proposals/{token_from(second['path'])}").status_code == 410

    Proposal.objects.filter(version=2).update(expires_at=None)
    client.post(f"/api/proposals/{second['proposal']['id']}/revoke")
    assert Proposal.objects.get(version=2).status == ProposalStatus.REVOKED
    assert customer.get(f"/api/public/proposals/{token_from(second['path'])}").status_code == 410


def test_new_link_replaces_old_one(api_client, owner, sent_proposal):
    old_token = token_from(sent_proposal["path"])
    fresh = api_client(owner).post(f"/api/proposals/{sent_proposal['proposal']['id']}/link")
    new_token = token_from(fresh.json()["path"])
    assert api_client().get(f"/api/public/proposals/{old_token}").status_code == 404
    assert api_client().get(f"/api/public/proposals/{new_token}").status_code == 200


def test_email_proposal(api_client, owner, sent_proposal, mailoutbox):
    response = api_client(owner).post(f"/api/proposals/{sent_proposal['proposal']['id']}/email")
    assert response.status_code == 200
    assert len(mailoutbox) == 1
    assert response.json()["url"] in mailoutbox[0].body


def test_estimate_is_locked_after_approval(api_client, owner, priced_estimate, approved):
    response = api_client(owner).put_json(
        f"/api/estimates/{priced_estimate['id']}",
        {"tier_id": None, "labor_allocation_percent": "30", "terms": "", "items": []},
    )
    assert response.status_code == 409
