from django.contrib import admin
from django.urls import path, re_path

from config.api import api
from config.frontend import spa_index

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    # Everything else is a page of the React app (must stay last).
    re_path(r"^(?!api(?:/|$)|admin(?:/|$)|static/).*$", spa_index),
]
