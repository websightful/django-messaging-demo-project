"""
ASGI config for demo_project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
import django
from django.apps import apps

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo_project.settings")

# Explicitly set up Django before importing anything
# This is required for the Daphne test server subprocess
# Only call setup() if apps aren't ready yet
if not apps.ready:
    django.setup()

# Import Django's ASGI application
from django.core.asgi import get_asgi_application

# Get the Django ASGI application early to ensure AppRegistry is populated
django_asgi_app = get_asgi_application()

# Now import Channels components and routing (after Django is set up)
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django_messaging.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
