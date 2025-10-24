"""
Pytest configuration for frontend tests

This configuration supports two test modes:
1. Polling mode (default) - Uses polling transport with StaticLiveServerTestCase
2. WebSocket mode - Uses WebSocket transport with Daphne server (for WebSocket tests)

To run polling tests:
    pytest demo_project/tests/ -v -m "frontend and not websocket"

To run WebSocket tests:
    pytest demo_project/tests/ -v -m "frontend and websocket"
"""

import pytest
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo_project.settings")


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Enable database access for all tests"""
    pass


@pytest.fixture(autouse=True)
def configure_transport_for_tests(request, settings):
    """
    Configure transport based on test markers.

    - Tests marked with 'websocket' use WebSocket transport
    - All other tests use polling transport (works with StaticLiveServerTestCase)
    """
    if request.node.get_closest_marker("websocket"):
        settings.DJANGO_MESSAGING = {
            "TRANSPORT": "websocket",
            "SHOW_DELETED_MESSAGE_INDICATORS": True,
        }
    else:
        settings.DJANGO_MESSAGING = {
            "TRANSPORT": "polling",
            "SHOW_DELETED_MESSAGE_INDICATORS": True,
        }


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Force file-based database for Channels testing"""
    from django.conf import settings

    settings.DATABASES["default"]["TEST"]["NAME"] = "test_db.sqlite3"
    settings.DATABASES["default"]["NAME"] = "test_db.sqlite3"
