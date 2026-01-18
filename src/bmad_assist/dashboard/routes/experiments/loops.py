"""Experiment loop template route handlers.

Provides endpoints for listing and viewing loop templates.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

logger = logging.getLogger(__name__)


async def get_experiments_loops(request: Request) -> JSONResponse:
    """GET /api/experiments/loops - List loop templates.

    Query parameters:
        sort_by: Sort field (name, run_count, last_run)
        sort_order: Sort direction (asc, desc)

    Returns:
        JSON response with loops array and total count.

    """
    from bmad_assist.dashboard.experiments import (
        LoopSummary,
        discover_loops,
        discover_runs,
        get_loop_run_stats,
    )
    from bmad_assist.experiments import load_loop_template

    server = request.app.state.server
    experiments_dir = server.project_root / "experiments"

    # Parse and validate query params
    sort_by = request.query_params.get("sort_by", "name")
    sort_order = request.query_params.get("sort_order", "asc")

    valid_sort_fields = {"name", "run_count", "last_run"}
    if sort_by not in valid_sort_fields:
        return JSONResponse(
            {"error": "invalid_sort_by", "message": f"Invalid sort_by: {sort_by}"},
            status_code=400,
        )

    if sort_order not in {"asc", "desc"}:
        return JSONResponse(
            {"error": "invalid_sort_order", "message": f"Invalid sort_order: {sort_order}"},
            status_code=400,
        )

    try:
        # Discover loops
        loop_tuples = await discover_loops(experiments_dir)
        if not loop_tuples:
            return JSONResponse({"loops": [], "total": 0})

        # Load templates and build response
        summaries: list[LoopSummary] = []

        for name, path in loop_tuples:
            try:
                template = load_loop_template(path)

                # Build sequence list
                sequence = [
                    {"workflow": step.workflow, "required": step.required}
                    for step in template.sequence
                ]

                summaries.append(
                    LoopSummary(
                        name=name,
                        description=template.description,
                        source=str(path),
                        sequence=sequence,
                        step_count=len(template.sequence),
                        run_count=0,  # Will be updated below
                        last_run=None,
                    )
                )
            except Exception as e:
                logger.warning("Failed to load loop template %s: %s", name, e)
                continue

        # Get run statistics
        runs = await discover_runs(experiments_dir)
        loop_names = [s.name for s in summaries]
        stats = get_loop_run_stats(loop_names, runs)

        # Update summaries with stats
        updated_summaries = []
        for summary in summaries:
            loop_stats = stats.get(summary.name)
            updated_summaries.append(
                LoopSummary(
                    name=summary.name,
                    description=summary.description,
                    source=summary.source,
                    sequence=summary.sequence,
                    step_count=summary.step_count,
                    run_count=loop_stats.run_count if loop_stats else 0,
                    last_run=loop_stats.last_run if loop_stats else None,
                )
            )
        summaries = updated_summaries

        # Apply sorting
        min_datetime = datetime.min.replace(tzinfo=UTC)
        sort_key_funcs: dict[str, Any] = {
            "name": lambda s: s.name.lower(),
            "run_count": lambda s: s.run_count,
            "last_run": lambda s: s.last_run or min_datetime,
        }
        summaries.sort(key=sort_key_funcs[sort_by], reverse=(sort_order == "desc"))

        return JSONResponse(
            {
                "loops": [s.model_dump(mode="json") for s in summaries],
                "total": len(summaries),
            }
        )

    except Exception:
        logger.exception("Failed to list loops")
        return JSONResponse(
            {"error": "server_error", "message": "Internal server error"},
            status_code=500,
        )


async def get_experiment_loop(request: Request) -> JSONResponse:
    """GET /api/experiments/loops/{loop_name} - Get loop details.

    Path parameters:
        loop_name: The loop template identifier

    Returns:
        JSON response with full loop details or 404.

    """
    from bmad_assist.dashboard.experiments import (
        LoopDetails,
        discover_loops,
        discover_runs,
        get_loop_run_stats,
        get_yaml_content,
        validate_run_id,
    )
    from bmad_assist.experiments import load_loop_template

    server = request.app.state.server
    loop_name = request.path_params["loop_name"]

    # Validate loop_name format
    if not validate_run_id(loop_name):
        return JSONResponse(
            {"error": "bad_request", "message": f"Invalid loop_name format: {loop_name}"},
            status_code=400,
        )

    experiments_dir = server.project_root / "experiments"

    try:
        # Discover loops
        loop_tuples = await discover_loops(experiments_dir)

        # Find loop by name
        loop_path = None
        for name, path in loop_tuples:
            if name == loop_name:
                loop_path = path
                break

        if loop_path is None:
            return JSONResponse(
                {"error": "not_found", "message": f"Loop not found: {loop_name}"},
                status_code=404,
            )

        # Load template
        try:
            template = load_loop_template(loop_path)
        except Exception as e:
            return JSONResponse(
                {"error": "server_error", "message": f"Failed to load loop: {e}"},
                status_code=500,
            )

        # Get run statistics
        runs = await discover_runs(experiments_dir)
        stats = get_loop_run_stats([loop_name], runs)
        loop_stats = stats.get(loop_name)

        # Get YAML content
        yaml_content = await get_yaml_content(str(loop_path))

        # Build sequence list
        sequence = [
            {"workflow": step.workflow, "required": step.required} for step in template.sequence
        ]

        # Build response
        details = LoopDetails(
            name=loop_name,
            description=template.description,
            source=str(loop_path),
            sequence=sequence,
            step_count=len(template.sequence),
            yaml_content=yaml_content,
            run_count=loop_stats.run_count if loop_stats else 0,
            last_run=loop_stats.last_run if loop_stats else None,
            recent_runs=loop_stats.recent_runs if loop_stats else [],
        )

        return JSONResponse(details.model_dump(mode="json"))

    except Exception:
        logger.exception("Failed to get loop %s", loop_name)
        return JSONResponse(
            {"error": "server_error", "message": "Internal server error"},
            status_code=500,
        )


routes = [
    Route("/api/experiments/loops", get_experiments_loops, methods=["GET"]),
    Route("/api/experiments/loops/{loop_name}", get_experiment_loop, methods=["GET"]),
]
