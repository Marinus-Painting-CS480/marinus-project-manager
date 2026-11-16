from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.projects.models import Project, ProjectStatus

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32


def new_project_payload(**overrides):
    payload = {
        "customer": {"name": "New Customer", "phone": "555-0100"},
        "title": "Kitchen repaint",
        "site_address": "9 Sample Rd",
        "project_type": "interior",
        "important_instructions": "Dog in yard",
        "areas": [
            {"name": "Kitchen", "scope_items": [{"description": "Walls"}]},
            {"name": "Hall", "scope_items": [{"description": "Ceiling", "included": False}]},
        ],
    }
    payload.update(overrides)
    return payload


def test_owner_creates_project_with_areas(api_client, owner):
    response = api_client(owner).post_json("/api/projects", new_project_payload())
    assert response.status_code == 201, response.content
    data = response.json()
    assert data["status"] == "draft"
    assert data["customer"]["name"] == "New Customer"
    assert [a["name"] for a in data["areas"]] == ["Kitchen", "Hall"]
    assert data["areas"][1]["scope_items"][0]["included"] is False


def test_save_draft_updates_adds_and_removes(api_client, owner):
    client = api_client(owner)
    created = client.post_json("/api/projects", new_project_payload()).json()
    kitchen = created["areas"][0]
    payload = new_project_payload(
        customer=None,
        customer_id=created["customer"]["id"],
        title="Kitchen + bath",
        areas=[
            {
                "id": kitchen["id"],
                "name": "Kitchen (main)",
                "scope_items": [
                    {"id": kitchen["scope_items"][0]["id"], "description": "Walls, 2 coats"},
                    {"description": "Trim"},
                ],
            },
            {"name": "Bathroom", "scope_items": []},
        ],
    )
    response = client.put_json(f"/api/projects/{created['id']}", payload)
    assert response.status_code == 200, response.content
    data = response.json()
    assert data["title"] == "Kitchen + bath"
    assert [a["name"] for a in data["areas"]] == ["Kitchen (main)", "Bathroom"]  # Hall removed
    assert [i["description"] for i in data["areas"][0]["scope_items"]] == [
        "Walls, 2 coats",
        "Trim",
    ]


def test_cannot_edit_another_projects_area(api_client, owner):
    client = api_client(owner)
    first = client.post_json("/api/projects", new_project_payload()).json()
    second = client.post_json("/api/projects", new_project_payload()).json()
    payload = new_project_payload(areas=[{"id": first["areas"][0]["id"], "name": "Stolen"}])
    assert client.put_json(f"/api/projects/{second['id']}", payload).status_code == 422


def test_submit_for_estimate_and_queue_order(api_client, owner):
    client = api_client(owner)
    late = client.post_json(
        "/api/projects", new_project_payload(title="Later", estimate_due_date="2030-02-01")
    ).json()
    soon = client.post_json(
        "/api/projects", new_project_payload(title="Sooner", estimate_due_date="2030-01-01")
    ).json()
    for project in (late, soon):
        response = client.post(f"/api/projects/{project['id']}/submit")
        assert response.json()["status"] == "waiting_for_estimate"
    queue = client.get("/api/projects?status=waiting_for_estimate&ordering=due_date").json()
    assert [p["title"] for p in queue] == ["Sooner", "Later"]
    assert client.post(f"/api/projects/{soon['id']}/submit").status_code == 409


def test_overdue_flag(api_client, owner, submitted_project):
    submitted_project.estimate_due_date = date(2020, 1, 1)
    submitted_project.save()
    projects = api_client(owner).get("/api/projects").json()
    assert projects[0]["is_overdue"] is True


def test_crew_cannot_use_intake(api_client, employee, subcontractor, submitted_project):
    for user in (employee, subcontractor):
        client = api_client(user)
        assert client.get("/api/projects").status_code == 403
        assert client.get(f"/api/projects/{submitted_project.id}").status_code == 403
        assert client.post_json("/api/projects", new_project_payload()).status_code == 403


def test_only_owner_deletes_drafts(api_client, owner, estimator):
    project = api_client(owner).post_json("/api/projects", new_project_payload()).json()
    assert api_client(estimator).delete(f"/api/projects/{project['id']}").status_code == 403
    assert api_client(owner).delete(f"/api/projects/{project['id']}").status_code == 204
    assert not Project.objects.exists()


def test_photo_upload_and_access(api_client, owner, employee, submitted_project):
    area = submitted_project.areas.first()
    client = api_client(owner)
    response = client.post(
        f"/api/projects/{submitted_project.id}/photos",
        {
            "files": [
                SimpleUploadedFile("a.png", PNG, content_type="image/png"),
                SimpleUploadedFile("b.jpg", JPEG, content_type="image/jpeg"),
            ],
            "area_id": area.id,
        },
    )
    assert response.status_code == 201, response.content
    photos = response.json()
    assert [p["content_type"] for p in photos] == ["image/png", "image/jpeg"]
    assert all(p["area_id"] == area.id for p in photos)

    url = photos[0]["url"]
    assert client.get(url).status_code == 200
    # An employee who is not assigned to this job cannot open the file.
    assert api_client(employee).get(url).status_code == 404


def test_non_image_upload_is_rejected(api_client, owner, submitted_project):
    response = api_client(owner).post(
        f"/api/projects/{submitted_project.id}/photos",
        {"files": [SimpleUploadedFile("evil.png", b"<script>", content_type="image/png")]},
    )
    assert response.status_code == 422
    assert not submitted_project.photos.exists()


def test_project_summary_counts(api_client, owner, submitted_project):
    counts = api_client(owner).get("/api/projects/summary").json()
    assert counts[ProjectStatus.WAITING_FOR_ESTIMATE] == 1
    assert counts[ProjectStatus.DRAFT] == 0
