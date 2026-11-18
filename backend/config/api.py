"""The single Django Ninja API, mounted at /api/. Live docs: http://localhost:8000/api/docs

Sign-in is required by default (Django session cookie + CSRF). Endpoints that must work
without an account (health, login, customer links) say `auth=None` explicitly.

Add each app's endpoints as a Router and register it here with api.add_router(...).
"""

from ninja import NinjaAPI
from ninja.security import django_auth

from apps.accounts.api import router as accounts_router
from apps.estimates.api import router as estimates_router
from apps.projects.api import router as projects_router
from apps.workorders.api import router as workorders_router

api = NinjaAPI(title="Marinus Painting API", version="0.2.0", auth=django_auth)


@api.get("/health", auth=None, tags=["system"])
def health(request):
    return {"status": "ok"}


api.add_router("", accounts_router)
api.add_router("", projects_router)
api.add_router("", estimates_router)
api.add_router("", workorders_router)
