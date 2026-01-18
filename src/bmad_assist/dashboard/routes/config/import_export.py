"""Config import/export route handlers.

Provides endpoints for exporting and importing config as YAML.
"""

import json
import logging
from datetime import UTC, datetime

import yaml
from anyio import to_thread
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from bmad_assist.core.config import PROJECT_CONFIG_NAME, reload_config
from bmad_assist.core.exceptions import ConfigError, ConfigValidationError

from . import utils

logger = logging.getLogger(__name__)


async def get_config_export(request: Request) -> Response:
    """GET /api/config/export?scope=merged|global|project - Export config as YAML.

    Returns YAML content with Content-Disposition header for download.
    DANGEROUS fields are excluded from export.

    Query params:
        scope: Export scope - "merged" (default), "global", or "project".

    Returns:
        YAML file download response.
        404 if scope=project and no project config exists.

    """
    scope = request.query_params.get("scope", "merged")
    if scope not in ("merged", "global", "project"):
        return JSONResponse(
            {"error": "invalid_scope", "message": "scope must be 'merged', 'global', or 'project'"},
            status_code=400,
        )

    async with utils._config_editor_lock:
        try:
            editor = await to_thread.run_sync(lambda: utils._create_config_editor(request))

            if scope == "merged":
                data = await to_thread.run_sync(editor.get_merged_with_provenance)
                data = utils._strip_provenance(data)
            elif scope == "global":
                data = await to_thread.run_sync(lambda: editor._global_data or {})
            else:
                data = await to_thread.run_sync(lambda: editor._project_data)
                if data is None:
                    return JSONResponse(
                        {"error": "not_found", "message": "No project configuration file found"},
                        status_code=404,
                    )

            # Filter DANGEROUS fields
            full_schema = utils._get_full_schema()
            data = utils._filter_dangerous_fields_for_export(data, full_schema)

            # Generate YAML
            yaml_content = yaml.dump(data, default_flow_style=False, sort_keys=False)

            # Generate filename
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = f"bmad-config-{scope}-{date_str}.yaml"

            return Response(
                content=yaml_content,
                media_type="text/yaml; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        except Exception as e:
            logger.exception("Failed to export config")
            return JSONResponse(
                {"error": "server_error", "message": str(e)},
                status_code=500,
            )


async def post_config_import(request: Request) -> JSONResponse:
    """POST /api/config/import - Import config from YAML content.

    Request body:
    {
        "scope": "global" | "project",
        "content": "<yaml-string>",
        "confirmed": false
    }

    When confirmed=false (preview mode):
        - Parse and validate YAML
        - Calculate diff against current scope
        - Return diff preview with risky fields

    When confirmed=true (apply mode):
        - Apply full replacement to scope
        - Rotate backups before writing
        - Broadcast SSE config_reloaded event

    Returns:
        Preview: {"valid": true, "diff": {...}, "risky_fields": [...]}
        Apply: {"applied": true, "updated_paths": [...]}
        Error: 400/403/422 with error details

    """
    try:
        body = await request.json()
    except json.JSONDecodeError as e:
        return JSONResponse(
            {"error": "invalid_json", "message": f"Invalid JSON body: {e}"},
            status_code=400,
        )

    scope = body.get("scope")
    content = body.get("content", "")
    confirmed = body.get("confirmed", False)

    if scope not in ("global", "project"):
        return JSONResponse(
            {"error": "invalid_scope", "message": "scope must be 'global' or 'project'"},
            status_code=400,
        )

    if len(content) > utils.IMPORT_MAX_SIZE:
        return JSONResponse(
            {
                "error": "content_too_large",
                "message": f"Import exceeds {utils.IMPORT_MAX_SIZE // 1024}KB limit",
            },
            status_code=400,
        )

    # Parse YAML
    try:
        import_data = yaml.safe_load(content)
        if import_data is None or (isinstance(import_data, dict) and not import_data):
            return JSONResponse(
                {
                    "error": "empty_import",
                    "message": "Import file is empty or contains no configuration",
                },
                status_code=400,
            )
        if not isinstance(import_data, dict):
            return JSONResponse(
                {"error": "invalid_yaml", "message": "Import must contain a YAML mapping"},
                status_code=400,
            )
    except yaml.YAMLError as e:
        return JSONResponse(
            {"error": "yaml_parse_error", "message": f"Invalid YAML: {e}"},
            status_code=400,
        )

    # Check for DANGEROUS fields
    full_schema = utils._get_full_schema()
    dangerous = utils._find_dangerous_fields(import_data, full_schema)
    if dangerous:
        return JSONResponse(
            {
                "error": "forbidden",
                "message": "Import contains restricted fields",
                "dangerous_fields": dangerous,
            },
            status_code=403,
        )

    server = request.app.state.server

    async with utils._config_editor_lock:
        try:
            editor = await to_thread.run_sync(lambda: utils._create_config_editor(request))

            # Get current data for scope (may be None for project)
            if scope == "global":
                current_data = editor._global_data or {}
            else:
                current_data = editor._project_data or {}

            if not confirmed:
                # Preview mode - validate and calculate diff
                # AC3 requires validation in preview mode to show errors before apply
                def validate_preview() -> None:
                    original_global = editor._global_data
                    original_project = editor._project_data
                    try:
                        if scope == "global":
                            editor._global_data = import_data
                        else:
                            editor._project_data = import_data
                        editor.validate()
                    finally:
                        # Restore original data after validation
                        editor._global_data = original_global
                        editor._project_data = original_project

                await to_thread.run_sync(validate_preview)

                diff = utils._calculate_diff(current_data, import_data)
                risky = utils._find_risky_fields_in_diff(diff, full_schema)

                return JSONResponse(
                    {
                        "valid": True,
                        "diff": diff,
                        "risky_fields": risky,
                    }
                )
            else:
                # Apply mode - full replacement
                # Calculate diff before modifying for accurate change count
                diff = utils._calculate_diff(current_data, import_data)

                def apply_import() -> None:
                    if scope == "global":
                        editor._global_data = import_data
                    else:
                        # For project scope, ensure project path is set
                        if editor.project_path is None:
                            project_path = server.project_root / PROJECT_CONFIG_NAME
                            editor.project_path = project_path
                        editor._project_data = import_data

                    # Validate and save with backup rotation
                    editor.validate()
                    editor.save(scope)

                await to_thread.run_sync(apply_import)

                # Calculate actual changed paths from diff
                changed_paths = (
                    list(diff.get("added", {}).keys())
                    + list(diff.get("modified", {}).keys())
                    + diff.get("removed", [])
                )

                # Reload config singleton
                await to_thread.run_sync(lambda: reload_config(server.project_root))

                # Broadcast SSE event
                if server.sse_broadcaster is not None:
                    timestamp = datetime.now(UTC).isoformat()
                    await server.sse_broadcaster.broadcast_event(
                        "config_reloaded",
                        {"timestamp": timestamp, "source": "import"},
                    )

                return JSONResponse(
                    {
                        "applied": True,
                        "updated_paths": changed_paths,
                    }
                )

        except ConfigValidationError as e:
            # Return structured validation errors with 422 status
            logger.warning("Import validation failed: %s", e)
            details = []
            for err in e.errors:
                loc = err["loc"]
                details.append(
                    {
                        "loc": list(loc) if isinstance(loc, tuple) else loc,
                        "msg": err["msg"],
                        "type": err["type"],
                    }
                )
            return JSONResponse(
                {"error": "validation_failed", "details": details},
                status_code=422,
            )
        except ConfigError as e:
            logger.exception("Import config error")
            return JSONResponse(
                {"error": "config_error", "message": str(e)},
                status_code=400,
            )
        except Exception as e:
            logger.exception("Failed to import config")
            return JSONResponse(
                {"error": "server_error", "message": str(e)},
                status_code=500,
            )


routes = [
    Route("/api/config/export", get_config_export, methods=["GET"]),
    Route("/api/config/import", post_config_import, methods=["POST"]),
]
