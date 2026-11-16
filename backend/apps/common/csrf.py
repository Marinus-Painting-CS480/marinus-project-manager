from django.middleware.csrf import CsrfViewMiddleware
from ninja.errors import HttpError


def enforce_csrf(request):
    """Run Django's CSRF check on an endpoint that has no session auth yet (e.g. login).

    Endpoints that use session auth already get this check from Django Ninja.
    """
    rejection = CsrfViewMiddleware(lambda req: None).process_view(request, None, (), {})
    if rejection is not None:
        raise HttpError(403, "CSRF check failed. Request /api/auth/csrf first.")
