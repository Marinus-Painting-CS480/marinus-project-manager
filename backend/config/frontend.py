"""Serve the React app's index.html for every page URL (/, /projects/12, /p/<token>, ...).

React Router then shows the right screen. Files such as /assets/app-1234.js are served by
WhiteNoise before this view is reached. In development you use the Vite server
(http://localhost:5173) instead, so this view only matters after `npm run build`.
"""

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound


def spa_index(request, path=""):
    index_file = settings.FRONTEND_DIST / "index.html"
    if not index_file.exists():
        return HttpResponseNotFound(
            "Frontend not built. Run `npm run build` in frontend/, or use the Vite dev server "
            "at http://localhost:5173 during development."
        )
    response = HttpResponse(index_file.read_bytes(), content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "no-cache"  # always pick up the newest deploy
    return response
