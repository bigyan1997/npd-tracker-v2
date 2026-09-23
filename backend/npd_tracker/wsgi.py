"""
WSGI config for npd_tracker project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npd_tracker.settings')

application = get_wsgi_application()

# Keep product photos in step with their Google Drive folders. Started here
# (not in AppConfig.ready) so it only runs in the real server, never during
# manage.py commands like migrate.
from products.drive_sync import start_background_sync  # noqa: E402

start_background_sync()
