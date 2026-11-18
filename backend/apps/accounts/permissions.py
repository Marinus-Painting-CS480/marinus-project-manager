"""Server-side role checks. Hiding a button in React is never a permission check.

Roles (see docs/ARCHITECTURE.md):
- owner, estimator: office staff; see all projects and financials
- employee: only work orders assigned to them; never prices
- subcontractor: assigned scope plus their own labor budget/hours; never customer price
"""

from ninja.errors import HttpError

from apps.accounts.models import Role

OFFICE_ROLES = (Role.OWNER, Role.ESTIMATOR)
FIELD_ROLES = (Role.EMPLOYEE, Role.SUBCONTRACTOR)


def is_office(user) -> bool:
    return user.is_authenticated and user.role in OFFICE_ROLES


def require_roles(request, *roles):
    """Raise 403 unless the signed-in user has one of `roles`."""
    if request.user.role not in roles:
        raise HttpError(403, "You do not have permission to do this.")


def require_office(request):
    require_roles(request, *OFFICE_ROLES)


def require_owner(request):
    require_roles(request, Role.OWNER)
