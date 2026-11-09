"""The single Django Ninja API, mounted at /api/. Live docs: http://localhost:8000/api/docs

Add each app's endpoints as a Router and register it here with api.add_router(...).
"""

from ninja import NinjaAPI

api = NinjaAPI(title="Marinus Painting API", version="0.1.0")


@api.get("/health", tags=["system"])
def health(request):
    return {"status": "ok"}
