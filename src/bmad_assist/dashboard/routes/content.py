"""Content route handlers.

Provides endpoints for prompts, validation reports, and report content.
"""

import logging
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

logger = logging.getLogger(__name__)


async def get_prompt(request: Request) -> Response:
    """GET /api/prompt/{epic}/{story}/{phase} - Get compiled template.

    Returns the cached template file for a specific workflow phase.
    Templates are phase-agnostic; epic/story params retained for API consistency.
    """
    server = request.app.state.server

    epic = request.path_params["epic"]
    story = request.path_params["story"]
    phase = request.path_params["phase"]

    try:
        prompt_path = server.get_prompt_path(epic, story, phase)
        if prompt_path and prompt_path.exists():
            content = prompt_path.read_text(encoding="utf-8")
            return Response(
                content,
                media_type="text/plain; charset=utf-8",  # AC 1.4
                headers={"X-Prompt-Path": str(prompt_path)},
            )
        else:
            # AC 1.5: Return 404 with specific error message
            return JSONResponse(
                {"error": f"Template not found for phase: {phase}"},
                status_code=404,
            )
    except Exception as e:
        logger.exception("Failed to get prompt")
        return JSONResponse({"error": str(e)}, status_code=500)


async def get_validation(request: Request) -> Response:
    """GET /api/validation/{epic}/{story} - Get validation reports.

    Returns validation report files for a story.
    """
    server = request.app.state.server

    epic = request.path_params["epic"]
    story = request.path_params["story"]

    try:
        reports = server.get_validation_reports(epic, story)
        return JSONResponse(reports)
    except Exception as e:
        logger.exception("Failed to get validation reports")
        return JSONResponse({"error": str(e)}, status_code=500)


async def get_report_content(request: Request) -> Response:
    """GET /api/report/content?path=<path> - Get report file content.

    Returns the content of a report file with security validation.
    Path must be within project root and not a symlink.
    """
    path_param = request.query_params.get("path")

    # AC 2b.1: path is required
    if not path_param:
        return JSONResponse({"error": "Missing path parameter"}, status_code=400)

    server = request.app.state.server
    report_path = Path(path_param)

    # Security validation
    try:
        # AC 2b.3: Reject symlinks before resolving (defense against symlink attacks)
        if report_path.is_symlink():
            return JSONResponse({"error": "Symlinks not allowed"}, status_code=403)

        # AC 2b.2: Resolve and validate path containment
        resolved_path = report_path.resolve()
        project_root = server.project_root.resolve()

        # Use is_relative_to for proper path containment check (Python 3.9+)
        if not resolved_path.is_relative_to(project_root):
            return JSONResponse({"error": "Path outside project"}, status_code=403)
    except (ValueError, OSError):
        return JSONResponse({"error": "Invalid path"}, status_code=400)

    # AC 2b.4: Return 404 for missing file
    if not resolved_path.exists():
        return JSONResponse({"error": "Report not found"}, status_code=404)

    # AC 2b.5: Return content as text/plain
    try:
        content = resolved_path.read_text(encoding="utf-8")
        return Response(content, media_type="text/plain; charset=utf-8")
    except Exception as e:
        logger.exception("Failed to read report file")
        return JSONResponse({"error": str(e)}, status_code=500)


routes = [
    Route("/api/prompt/{epic}/{story}/{phase}", get_prompt, methods=["GET"]),
    Route("/api/validation/{epic}/{story}", get_validation, methods=["GET"]),
    Route("/api/report/content", get_report_content, methods=["GET"]),
]
