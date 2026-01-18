"""Experiment comparison route handlers.

Provides endpoints for comparing experiment runs.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from anyio import to_thread
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from bmad_assist.core.exceptions import ConfigError

logger = logging.getLogger(__name__)


async def _validate_comparison_runs(
    request: Request, server: Any
) -> tuple[list[str], Path, JSONResponse | None]:
    """Validate runs parameter for comparison endpoints.

    Args:
        request: Starlette request.
        server: Dashboard server instance.

    Returns:
        Tuple of (run_ids, runs_dir, error_response).
        If error_response is not None, return it immediately.

    """
    from bmad_assist.dashboard.experiments import validate_run_id
    from bmad_assist.experiments import MAX_COMPARISON_RUNS

    runs_param = request.query_params.get("runs", "")
    if not runs_param:
        return (
            [],
            Path(),
            JSONResponse(
                {"error": "missing_runs", "message": "runs parameter is required"},
                status_code=400,
            ),
        )

    # Parse and deduplicate while preserving order
    seen: set[str] = set()
    run_ids: list[str] = []
    for r in runs_param.split(","):
        r = r.strip()
        if r and r not in seen:
            seen.add(r)
            run_ids.append(r)

    if len(run_ids) < 2:
        return (
            [],
            Path(),
            JSONResponse(
                {
                    "error": "too_few_runs",
                    "message": "At least 2 unique runs required for comparison",
                },
                status_code=400,
            ),
        )
    if len(run_ids) > MAX_COMPARISON_RUNS:
        return (
            [],
            Path(),
            JSONResponse(
                {
                    "error": "too_many_runs",
                    "message": f"Maximum {MAX_COMPARISON_RUNS} runs allowed for comparison",
                },
                status_code=400,
            ),
        )

    for run_id in run_ids:
        if not validate_run_id(run_id):
            return (
                [],
                Path(),
                JSONResponse(
                    {
                        "error": "invalid_run_id",
                        "message": f"Invalid run ID format: {run_id}",
                    },
                    status_code=400,
                ),
            )

    experiments_dir = server.project_root / "experiments"
    runs_dir = experiments_dir / "runs"

    missing_runs = [
        run_id
        for run_id in run_ids
        if not (runs_dir / run_id).exists() or not (runs_dir / run_id / "manifest.yaml").exists()
    ]
    if missing_runs:
        return (
            [],
            Path(),
            JSONResponse(
                {
                    "error": "not_found",
                    "message": f"Runs not found: {', '.join(missing_runs)}",
                },
                status_code=404,
            ),
        )

    return run_ids, runs_dir, None


async def get_experiments_compare(request: Request) -> JSONResponse:
    """GET /api/experiments/compare - Compare experiment runs.

    Query parameters:
        runs: Comma-separated run IDs (2-10 required).

    Returns:
        JSON response with ComparisonReport data.

    """
    from bmad_assist.experiments import ComparisonGenerator

    server = request.app.state.server

    # Use shared validation helper
    run_ids, runs_dir, error = await _validate_comparison_runs(request, server)
    if error:
        return error

    try:
        # Generate comparison in thread pool (file I/O heavy)
        def do_compare() -> dict[str, Any]:
            generator = ComparisonGenerator(runs_dir)
            report = generator.compare(run_ids)
            return report.model_dump(mode="json")

        result = await to_thread.run_sync(do_compare)
        return JSONResponse(result)

    except ValueError as e:
        # ComparisonGenerator validation errors
        return JSONResponse(
            {"error": "validation_error", "message": str(e)},
            status_code=400,
        )
    except ConfigError as e:
        # Run not found during comparison
        return JSONResponse(
            {"error": "not_found", "message": str(e)},
            status_code=404,
        )
    except Exception:
        logger.exception("Failed to generate comparison")
        return JSONResponse(
            {"error": "server_error", "message": "Internal server error"},
            status_code=500,
        )


async def get_experiments_compare_export(request: Request) -> Response:
    """GET /api/experiments/compare/export - Export comparison as Markdown.

    Query parameters:
        runs: Comma-separated run IDs (2-10 required).

    Returns:
        Markdown file download response.

    """
    from bmad_assist.experiments import ComparisonGenerator

    server = request.app.state.server

    # Use shared validation helper
    run_ids, runs_dir, error = await _validate_comparison_runs(request, server)
    if error:
        return error

    try:

        def do_export() -> str:
            generator = ComparisonGenerator(runs_dir)
            report = generator.compare(run_ids)
            return generator.generate_markdown(report)

        markdown = await to_thread.run_sync(do_export)

        # Generate filename with date
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        filename = f"comparison-{date_str}.md"

        return Response(
            content=markdown,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except ValueError as e:
        return JSONResponse(
            {"error": "validation_error", "message": str(e)},
            status_code=400,
        )
    except ConfigError as e:
        return JSONResponse(
            {"error": "not_found", "message": str(e)},
            status_code=404,
        )
    except Exception:
        logger.exception("Failed to export comparison")
        return JSONResponse(
            {"error": "server_error", "message": "Internal server error"},
            status_code=500,
        )


routes = [
    Route("/api/experiments/compare", get_experiments_compare, methods=["GET"]),
    Route("/api/experiments/compare/export", get_experiments_compare_export, methods=["GET"]),
]
