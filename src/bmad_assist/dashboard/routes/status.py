"""Status and story route handlers.

Provides endpoints for sprint status, story listing, and epic details.
"""

import logging

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

logger = logging.getLogger(__name__)


async def get_status(request: Request) -> JSONResponse:
    """GET /api/status - Return sprint status.

    Returns current sprint state from sprint-status.yaml including:
    - Current phase
    - Active story
    - Overall progress
    """
    server = request.app.state.server

    try:
        status = server.get_sprint_status()
        return JSONResponse(status)
    except Exception as e:
        logger.exception("Failed to get sprint status")
        return JSONResponse({"error": str(e)}, status_code=500)


async def get_stories(request: Request) -> JSONResponse:
    """GET /api/stories - Return story list with phases.

    Returns hierarchical structure:
    - Epics with metadata
    - Stories within each epic
    - Workflow phases for each story
    """
    server = request.app.state.server

    try:
        stories = server.get_stories()
        return JSONResponse(stories)
    except Exception as e:
        logger.exception("Failed to get stories")
        return JSONResponse({"error": str(e)}, status_code=500)


async def get_epic_details(request: Request) -> JSONResponse:
    """GET /api/epics/{epic_id} - Return epic details with full content.

    Returns epic content from epics.md or sharded epic file.
    Includes frontmatter metadata and markdown content.
    """
    server = request.app.state.server
    epic_id = request.path_params.get("epic_id")

    try:
        details = server.get_epic_details(epic_id)
        if details is None:
            return JSONResponse(
                {"error": f"Epic not found: {epic_id}"},
                status_code=404,
            )
        return JSONResponse(details)
    except Exception as e:
        logger.exception("Failed to get epic details")
        return JSONResponse({"error": str(e)}, status_code=500)


async def get_story_in_epic(request: Request) -> JSONResponse:
    """GET /api/epics/{epic_id}/stories/{story_id} - Return story content from epic.

    Extracts and returns only the specified story's content from within the epic file.
    Supports both sharded and non-sharded epic files.
    """
    server = request.app.state.server
    epic_id = request.path_params.get("epic_id")
    story_id = request.path_params.get("story_id")

    try:
        story = server.get_story_in_epic(epic_id, story_id)
        if story is None:
            return JSONResponse(
                {"error": f"Story {story_id} not found in epic {epic_id}"},
                status_code=404,
            )
        return JSONResponse(story)
    except Exception as e:
        logger.exception("Failed to get story in epic")
        return JSONResponse({"error": str(e)}, status_code=500)


async def get_version(request: Request) -> JSONResponse:
    """GET /api/version - Return bmad-assist version."""
    from bmad_assist import __version__

    return JSONResponse({"version": __version__})


routes = [
    Route("/api/version", get_version, methods=["GET"]),
    Route("/api/status", get_status, methods=["GET"]),
    Route("/api/stories", get_stories, methods=["GET"]),
    Route("/api/epics/{epic_id}", get_epic_details, methods=["GET"]),
    Route("/api/epics/{epic_id}/stories/{story_id}", get_story_in_epic, methods=["GET"]),
]
