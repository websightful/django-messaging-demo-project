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


async def position_browser_windows_side_by_side(
    left_page, right_page, screen_width=1792, screen_height=950
):
    """
    Position two browser windows side by side.

    Args:
        left_page: Playwright page for the left window
        right_page: Playwright page for the right window
        screen_width: Total screen width (default: 1792)
        screen_height: Desired viewport height (default: 950)
    """
    half_width = screen_width // 2

    # Set viewport size for both windows
    await left_page.set_viewport_size({"width": half_width, "height": screen_height})
    await right_page.set_viewport_size({"width": half_width, "height": screen_height})

    # Use CDP (Chrome DevTools Protocol) to set window position
    # Note: We only set position (left, top) and width, NOT height
    # The height is controlled by set_viewport_size above

    # Left window: position at x=0
    cdp_left = await left_page.context.new_cdp_session(left_page)

    # Get the actual window ID for the left page
    left_window_info = await cdp_left.send("Browser.getWindowForTarget")
    left_window_id = left_window_info["windowId"]

    await cdp_left.send(
        "Browser.setWindowBounds",
        {
            "windowId": left_window_id,
            "bounds": {
                "left": 0,
                "top": 0,
                "width": half_width,
            },
        },
    )

    # Right window: position at x=half_width
    cdp_right = await right_page.context.new_cdp_session(right_page)

    # Get the actual window ID for the right page
    right_window_info = await cdp_right.send("Browser.getWindowForTarget")
    right_window_id = right_window_info["windowId"]

    await cdp_right.send(
        "Browser.setWindowBounds",
        {
            "windowId": right_window_id,
            "bounds": {
                "left": half_width,
                "top": 0,
                "width": half_width,
            },
        },
    )
