"""Playwright status route handlers.

Provides endpoint for checking Playwright installation status.
"""

import asyncio
import logging
from typing import Any

from anyio import to_thread
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

logger = logging.getLogger(__name__)


async def get_playwright_status(request: Request) -> JSONResponse:
    """GET /api/playwright/status - Check Playwright installation status.

    Returns detailed status including:
    - Package installation
    - Browser binaries
    - System dependencies
    - Install commands (if needed)

    Response format:
    {
        "ready": true,
        "package_installed": true,
        "version": "1.40.0",
        "browsers": {
            "chromium": true,
            "firefox": false,
            "webkit": false
        },
        "deps_ok": true,
        "error": null,
        "install_commands": []
    }
    """
    from bmad_assist.utils.playwright_check import (
        check_playwright,
        get_install_commands,
    )

    try:
        # Run blocking check in thread pool with 30s timeout
        # check_playwright() does actual browser launch test (~5-10s)
        status = await asyncio.wait_for(
            to_thread.run_sync(check_playwright),
            timeout=30.0,
        )

        # Build response
        response: dict[str, Any] = {
            "ready": status.ready,
            "package_installed": status.package_installed,
            "version": status.version,
            "browsers": {
                "chromium": status.chromium,
                "firefox": status.firefox,
                "webkit": status.webkit,
            },
            "deps_ok": status.deps_ok,
            "error": status.error,
            "install_commands": [],
        }

        # Include install commands if not ready
        if not status.ready:
            response["install_commands"] = await to_thread.run_sync(
                lambda: get_install_commands(status)
            )

        return JSONResponse(response)

    except TimeoutError:
        logger.warning("Playwright status check timed out after 30s")
        return JSONResponse(
            {"error": "Browser check timed out after 30s"},
            status_code=504,
        )
    except Exception:
        logger.exception("Failed to check Playwright status")
        return JSONResponse(
            {"error": "Internal error while checking Playwright status"},
            status_code=500,
        )


routes = [
    Route("/api/playwright/status", get_playwright_status, methods=["GET"]),
]
