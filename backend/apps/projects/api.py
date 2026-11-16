"""Customers, projects (walkthrough intake) and photos. Office staff only, except photo
files, which assigned crew members may also open."""

from typing import Literal

from django.conf import settings
from django.db import transaction
from django.db.models import Count, F, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from ninja import File, Form, Router
from ninja.errors import HttpError
from ninja.files import UploadedFile

from apps.accounts.models import Role
from apps.accounts.permissions import require_office, require_roles
from apps.projects.models import Area, Customer, Photo, Project, ProjectStatus
from apps.projects.photos import can_view_project_files, validate_upload
from apps.projects.schemas import (
    CustomerIn,
    CustomerOut,
    PhotoOut,
    PhotoUpdateIn,
    ProjectIn,
    ProjectOut,
    ProjectSummaryOut,
)
from apps.projects.services import save_project, submit_for_estimate

router = Router()


def _project_detail(project_id: int) -> Project:
    queryset = Project.objects.select_related("customer").prefetch_related(
        "areas__scope_items", "photos"
    )
    return get_object_or_404(queryset, pk=project_id)


# ---------- Customers ----------


@router.get("/customers", response=list[CustomerOut], tags=["customers"])
def list_customers(request, search: str = ""):
    require_office(request)
    customers = Customer.objects.all()
    if search:
        customers = customers.filter(
            Q(name__icontains=search) | Q(email__icontains=search) | Q(phone__icontains=search)
        )
    return customers[:100]


@router.post("/customers", response={201: CustomerOut}, tags=["customers"])
def create_customer(request, payload: CustomerIn):
    require_office(request)
    return 201, Customer.objects.create(**payload.dict())


@router.get("/customers/{customer_id}", response=CustomerOut, tags=["customers"])
def get_customer(request, customer_id: int):
    require_office(request)
    return get_object_or_404(Customer, pk=customer_id)


@router.put("/customers/{customer_id}", response=CustomerOut, tags=["customers"])
def update_customer(request, customer_id: int, payload: CustomerIn):
    require_office(request)
    customer = get_object_or_404(Customer, pk=customer_id)
    for field, value in payload.dict().items():
        setattr(customer, field, value)
    customer.save()
    return customer


# ---------- Projects ----------


@router.get("/projects/summary", response=dict[str, int], tags=["projects"])
def project_summary(request):
    """Number of projects per status, for dashboard counters."""
    require_office(request)
    counts = dict(Project.objects.values_list("status").annotate(total=Count("id")).order_by())
    return {status: counts.get(status, 0) for status in ProjectStatus.values}


@router.get("/projects", response=list[ProjectSummaryOut], tags=["projects"])
def list_projects(
    request,
    status: ProjectStatus | None = None,
    search: str = "",
    ordering: Literal["newest", "due_date"] = "newest",
):
    """Owner/estimator dashboards. The estimator queue is
    `?status=waiting_for_estimate&ordering=due_date`."""
    require_office(request)
    projects = Project.objects.select_related("customer")
    if status:
        projects = projects.filter(status=status)
    if search:
        projects = projects.filter(
            Q(title__icontains=search)
            | Q(site_address__icontains=search)
            | Q(customer__name__icontains=search)
        )
    if ordering == "due_date":
        projects = projects.order_by(F("estimate_due_date").asc(nulls_last=True), "created_at")
    return projects[:200]


@router.post("/projects", response={201: ProjectOut}, tags=["projects"])
def create_project(request, payload: ProjectIn):
    require_office(request)
    project = save_project(None, payload, request.user)
    return 201, _project_detail(project.id)


@router.get("/projects/{project_id}", response=ProjectOut, tags=["projects"])
def get_project(request, project_id: int):
    require_office(request)
    return _project_detail(project_id)


@router.put("/projects/{project_id}", response=ProjectOut, tags=["projects"])
def update_project(request, project_id: int, payload: ProjectIn):
    """Save Draft: send the whole intake form."""
    require_office(request)
    project = get_object_or_404(Project, pk=project_id)
    save_project(project, payload, request.user)
    return _project_detail(project_id)


@router.post("/projects/{project_id}/submit", response=ProjectOut, tags=["projects"])
def submit_project(request, project_id: int):
    """Submit for Estimate: moves the project into the estimator's queue."""
    require_office(request)
    submit_for_estimate(get_object_or_404(Project, pk=project_id))
    return _project_detail(project_id)


@router.delete("/projects/{project_id}", response={204: None}, tags=["projects"])
def delete_project(request, project_id: int):
    """Owner only, and only while it is still a draft."""
    require_roles(request, Role.OWNER)
    project = get_object_or_404(Project, pk=project_id)
    if project.status != ProjectStatus.DRAFT:
        raise HttpError(409, "Only draft projects can be deleted.")
    for photo in project.photos.all():
        photo.file.delete(save=False)
    project.delete()
    return 204, None


# ---------- Photos ----------


@router.post("/projects/{project_id}/photos", response={201: list[PhotoOut]}, tags=["photos"])
def upload_photos(
    request,
    project_id: int,
    files: File[list[UploadedFile]],
    area_id: Form[int | None] = None,
    caption: Form[str] = "",
):
    """Multipart upload of one or more photos (camera or gallery). Field name: `files`."""
    require_office(request)
    project = get_object_or_404(Project, pk=project_id)
    if len(files) > settings.PHOTO_MAX_FILES_PER_UPLOAD:
        raise HttpError(422, f"Upload at most {settings.PHOTO_MAX_FILES_PER_UPLOAD} at a time.")
    area = None
    if area_id is not None:
        area = Area.objects.filter(pk=area_id, project=project).first()
        if area is None:
            raise HttpError(422, "That area does not belong to this project.")
    checked = [(upload, validate_upload(upload)) for upload in files]  # all or nothing
    with transaction.atomic():
        photos = [
            Photo.objects.create(
                project=project,
                area=area,
                file=upload,
                content_type=content_type,
                size=upload.size,
                caption=caption,
                uploaded_by=request.user,
            )
            for upload, content_type in checked
        ]
    return 201, photos


@router.get("/photos/{photo_id}/file", tags=["photos"])
def photo_file(request, photo_id: int):
    """The image itself, after a permission check. Use this URL in <img src>."""
    photo = get_object_or_404(Photo.objects.select_related("project"), pk=photo_id)
    if not can_view_project_files(request.user, photo.project):
        raise HttpError(404, "Not found.")  # do not reveal that the photo exists
    response = FileResponse(photo.file.open("rb"), content_type=photo.content_type)
    response["Cache-Control"] = "private, max-age=3600"
    return response


@router.patch("/photos/{photo_id}", response=PhotoOut, tags=["photos"])
def update_photo(request, photo_id: int, payload: PhotoUpdateIn):
    """Move a photo to another area or change its caption."""
    require_office(request)
    photo = get_object_or_404(Photo, pk=photo_id)
    if (
        payload.area_id is not None
        and not Area.objects.filter(pk=payload.area_id, project_id=photo.project_id).exists()
    ):
        raise HttpError(422, "That area does not belong to this project.")
    photo.area_id = payload.area_id
    photo.caption = payload.caption
    photo.save(update_fields=["area", "caption"])
    return photo


@router.delete("/photos/{photo_id}", response={204: None}, tags=["photos"])
def delete_photo(request, photo_id: int):
    require_office(request)
    photo = get_object_or_404(Photo, pk=photo_id)
    photo.file.delete(save=False)
    photo.delete()
    return 204, None
