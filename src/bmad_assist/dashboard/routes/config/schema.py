"""Config schema route handlers.

Provides endpoint for config schema with metadata.
"""

import logging

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from bmad_assist.core.config import get_config_schema

logger = logging.getLogger(__name__)


async def get_config_schema_endpoint(request: Request) -> JSONResponse:
    """GET /api/config/schema - Return config schema with metadata.

    Returns the config schema with security levels and UI widget hints.
    DANGEROUS fields are already excluded by get_config_schema().
    Response is cached (schema is static for app lifetime).
    """
    try:
        schema = get_config_schema()
        return JSONResponse(schema)
    except Exception as e:
        logger.exception("Failed to get config schema")
        return JSONResponse(
            {"error": "server_error", "message": str(e)},
            status_code=500,
        )


routes = [
    Route("/api/config/schema", get_config_schema_endpoint, methods=["GET"]),
]
