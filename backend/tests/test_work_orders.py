import pytest

from apps.audit.models import AuditLog
from apps.workorders.models import ChangeNote, WorkOrder
from tests.conftest import token_from


@pytest.fixture
def work_order(approved):
    return WorkOrder.objects.get()


def assign(api_client, owner, work_order, assignments):
    return api_client(owner).put_json(
        f"/api/work-orders/{work_order.id}/assignments", {"assignments": assignments}
    )


def test_new_work_order_awaits_assignment(api_client, owner, work_order):
    data = api_client(owner).get(f"/api/work-orders/{work_order.id}").json()
    assert data["status"] == "awaiting_assignment"
    assert data["important_instructions"] == "Use side gate"
    assert data["financials"]["contract_amount"] == "1000.00"
    assert data["financials"]["estimated_labor"] == "300.00"
    assert data["financials"]["estimated_material"] == "200.00"  # cabinets not signed
    assert data["financials"]["estimated_margin"] == "500.00"
    assert "missing_start_date" in data["warnings"]


def test_assignment_and_employee_view(api_client, owner, employee, employee2, work_order):
    response = assign(
        api_client,
        owner,
        work_order,
        [{"user_id": employee.id, "is_person_in_charge": True}, {"user_id": employee2.id}],
    )
    assert response.status_code == 200, response.content
    assert response.json()["status"] == "scheduled"

    data = api_client(employee).get(f"/api/work-orders/{work_order.id}").json()
    assert data["financials"] is None
    assert data["assignments"] is None
    assert data["scope"][0]["items"][0]["unit_price"] is None
    assert "1000.00" not in str(data)
    assert {c["name"] for c in data["crew"]} == {"Worker One", "Worker Two"}
    assert data["my_assignment"]["is_person_in_charge"] is True


def test_unassigned_employee_cannot_see_job(api_client, employee, work_order):
    client = api_client(employee)
    assert client.get("/api/work-orders").json() == []
    assert client.get(f"/api/work-orders/{work_order.id}").status_code == 404


def test_removed_worker_loses_access_immediately(api_client, owner, employee, work_order):
    assign(api_client, owner, work_order, [{"user_id": employee.id}])
    client = api_client(employee)
    assert client.get(f"/api/work-orders/{work_order.id}").status_code == 200
    assign(api_client, owner, work_order, [])
    assert client.get(f"/api/work-orders/{work_order.id}").status_code == 404
    assert WorkOrder.objects.get().status == "awaiting_assignment"


def test_subcontractor_sees_only_own_budget(api_client, owner, employee, subcontractor, work_order):
    assign(
        api_client,
        owner,
        work_order,
        [
            {"user_id": subcontractor.id, "labor_budget": "400.00", "estimated_hours": "16"},
            {"user_id": employee.id, "labor_budget": "999.00"},
        ],
    )
    sub_view = api_client(subcontractor).get(f"/api/work-orders/{work_order.id}").json()
    assert sub_view["my_assignment"]["labor_budget"] == "400.00"
    assert sub_view["financials"] is None
    assert "999.00" not in str(sub_view)
    assert "1000.00" not in str(sub_view)

    employee_view = api_client(employee).get(f"/api/work-orders/{work_order.id}").json()
    assert employee_view["my_assignment"]["labor_budget"] is None


def test_assignment_rules(api_client, owner, estimator, employee, employee2, work_order):
    two_leads = [
        {"user_id": employee.id, "is_person_in_charge": True},
        {"user_id": employee2.id, "is_person_in_charge": True},
    ]
    assert assign(api_client, owner, work_order, two_leads).status_code == 422
    office_user = [{"user_id": estimator.id}]
    assert assign(api_client, owner, work_order, office_user).status_code == 422
    assert (
        api_client(employee)
        .put_json(f"/api/work-orders/{work_order.id}/assignments", {"assignments": []})
        .status_code
        == 403
    )


def test_schedule_change_and_warnings(api_client, owner, employee, work_order):
    client = api_client(owner)
    response = client.patch_json(
        f"/api/work-orders/{work_order.id}",
        {"start_date": "2030-05-10", "arrival_time": "08:00", "completion_deadline": "2030-05-01"},
    )
    assert response.status_code == 200, response.content
    assert response.json()["warnings"] == ["deadline_before_start"]
    assert AuditLog.objects.filter(action="work_order.schedule_changed").exists()
    assert (
        api_client(employee)
        .patch_json(f"/api/work-orders/{work_order.id}", {"start_date": "2030-01-01"})
        .status_code
        == 403
    )


def test_customer_link_shows_safe_latest_details(api_client, owner, subcontractor, approved):
    work_order = WorkOrder.objects.get()
    assign(api_client, owner, work_order, [{"user_id": subcontractor.id, "labor_budget": "400"}])
    api_client(owner).patch_json(f"/api/work-orders/{work_order.id}", {"start_date": "2030-06-01"})
    ChangeNote.objects.create(work_order=work_order, note="INTERNAL-NOTE")

    response = api_client().get(
        f"/api/public/work-orders/{token_from(approved['work_order_path'])}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["schedule"]["start_date"] == "2030-06-01"
    assert data["crew"] == [{"name": "Sub Co", "is_person_in_charge": False}]
    text = response.content.decode()
    for secret in ("INTERNAL-NOTE", "400", "1000.00", "unit_price", "Use side gate"):
        assert secret not in text


def test_customer_link_can_be_replaced(api_client, owner, approved):
    work_order = WorkOrder.objects.get()
    old = token_from(approved["work_order_path"])
    new = api_client(owner).post(f"/api/work-orders/{work_order.id}/customer-link").json()
    assert api_client().get(f"/api/public/work-orders/{old}").status_code == 404
    assert api_client().get(f"/api/public/work-orders/{token_from(new['path'])}").status_code == 200


def test_change_notes(api_client, owner, employee, work_order):
    response = api_client(owner).post_json(
        f"/api/work-orders/{work_order.id}/notes", {"note": "Customer added closet (quote sent)"}
    )
    assert response.status_code == 201
    assert response.json()["change_notes"][0]["author_name"] == "Owner"
    assert (
        api_client(employee)
        .post_json(f"/api/work-orders/{work_order.id}/notes", {"note": "x"})
        .status_code
        == 403
    )
