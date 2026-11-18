"""Entry point for cPanel's "Setup Python App" (Phusion Passenger).

cPanel looks for a module named passenger_wsgi with an `application` object.
Other hosts use: gunicorn config.wsgi --bind 0.0.0.0:$PORT
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
