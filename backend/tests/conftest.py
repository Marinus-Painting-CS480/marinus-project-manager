"""Shared test fixtures. All data is made up."""

import json

import pytest
from django.core.cache import cache
from django.test import Client

from apps.accounts.models import Role, User
from apps.estimates.models import QualityTier
from apps.projects.models import Area, Customer, Project, ProjectStatus, ScopeItem


@pytest.fixture(autouse=True)
def _isolated(settings, tmp_path):
    cache.clear()  # rate limits use the cache; start every test fresh
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.SITE_URL = "https://app.test"


class ApiClient(Client):
    """Django test client that sends JSON bodies by default."""

    def _json(self, method, path, data=None):
        body = json.dumps(data) if data is not None else ""
        return getattr(super(), method)(path, body, content_type="application/json")

    def post_json(self, path, data=None):
        return self._json("post", path, data)

    def put_json(self, path, data=None):
        return self._json("put", path, data)

    def patch_json(self, path, data=None):
        return self._json("patch", path, data)


def _user(email, role, name=None):
    return User.objects.create_user(
        email=email, name=name or email.split("@")[0], password="pw-12345-test", role=role
    )


@pytest.fixture
def owner(db):
    return _user("owner@test.local", Role.OWNER, "Owner")


@pytest.fixture
def estimator(db):
    return _user("estimator@test.local", Role.ESTIMATOR, "Estimator")


@pytest.fixture
def employee(db):
    return _user("worker1@test.local", Role.EMPLOYEE, "Worker One")


@pytest.fixture
def employee2(db):
    return _user("worker2@test.local", Role.EMPLOYEE, "Worker Two")


@pytest.fixture
def subcontractor(db):
    return _user("sub@test.local", Role.SUBCONTRACTOR, "Sub Co")


@pytest.fixture
def api_client():
    def make(user=None):
        client = ApiClient()
        if user is not None:
            client.force_login(user)
        return client

    return make


@pytest.fixture
def tier(db):
    return QualityTier.objects.create(name="Premium", description="Test tier wording")


@pytest.fixture
def submitted_project(db, owner):
    """Kitchen: required walls + optional cabinets. Hallway: ceiling excluded."""
    customer = Customer.objects.create(name="Test Customer", email="cust@test.local")
    project = Project.objects.create(
        customer=customer,
        title="Test house",
        site_address="1 Test Way",
        status=ProjectStatus.WAITING_FOR_ESTIMATE,
        important_instructions="Use side gate",
        created_by=owner,
    )
    kitchen = Area.objects.create(project=project, name="Kitchen", sequence=0)
    hallway = Area.objects.create(project=project, name="Hallway", sequence=1)
    ScopeItem.objects.create(area=kitchen, description="Walls", color="White", sequence=0)
    ScopeItem.objects.create(area=kitchen, description="Cabinets", optional=True, sequence=1)
    ScopeItem.objects.create(area=hallway, description="Ceiling", included=False)
    return project


PRICES = {"Walls": ("1000.00", "200.00"), "Cabinets": ("250.00", "50.00")}


@pytest.fixture
def priced_estimate(api_client, owner, tier, submitted_project):
    """Walls $1000 (cost $200), optional Cabinets $250 (cost $50), labor 30%."""
    client = api_client(owner)
    estimate = client.post(f"/api/projects/{submitted_project.id}/estimate").json()
    items = [
        {
            "id": item["id"],
            "scope_item_id": item["scope_item_id"],
            "description": item["description"],
            "unit_price": PRICES[item["description"]][0],
            "quantity": "1",
            "optional": item["optional"],
            "estimated_material_cost": PRICES[item["description"]][1],
        }
        for item in estimate["items"]
    ]
    response = client.put_json(
        f"/api/estimates/{estimate['id']}",
        {"tier_id": tier.id, "labor_allocation_percent": "30", "terms": "Net 15", "items": items},
    )
    assert response.status_code == 200, response.content
    return response.json()


@pytest.fixture
def sent_proposal(api_client, owner, priced_estimate):
    """Returns the response of sending the proposal: {proposal, path, url}."""
    response = api_client(owner).post(f"/api/estimates/{priced_estimate['id']}/proposals")
    assert response.status_code == 201, response.content
    return response.json()


def token_from(path):
    return path.rsplit("/", 1)[-1]


@pytest.fixture
def approved(api_client, sent_proposal):
    """Customer approves without the optional cabinets. Returns the approve response."""
    token = token_from(sent_proposal["path"])
    response = api_client().post_json(
        f"/api/public/proposals/{token}/approve",
        {
            "signer_name": "Test Customer",
            "signature": "Test Customer",
            "selected_optional_item_ids": [],
            "accept_terms": True,
        },
    )
    assert response.status_code == 200, response.content
    return response.json()
