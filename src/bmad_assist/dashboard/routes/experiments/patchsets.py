"""Experiment patch-set template route handlers.

Provides endpoints for listing and viewing patch-set manifests.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

logger = logging.getLogger(__name__)


async def get_experiments_patchsets(request: Request) -> JSONResponse:
    """GET /api/experiments/patch-sets - List patch-set manifests.

    Query parameters:
        sort_by: Sort field (name, run_count, last_run)
        sort_order: Sort direction (asc, desc)

    Returns:
        JSON response with patch_sets array and total count.

    """
    from bmad_assist.dashboard.experiments import (
        PatchSetSummary,
        discover_patchsets,
        discover_runs,
        get_patchset_run_stats,
    )
    from bmad_assist.experiments import load_patchset_manifest

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
        # Discover patch-sets
        patchset_tuples = await discover_patchsets(experiments_dir)
        if not patchset_tuples:
            return JSONResponse({"patch_sets": [], "total": 0})

        # Load manifests and build response
        summaries: list[PatchSetSummary] = []

        for name, path in patchset_tuples:
            try:
                # Load without validating paths (discovery mode)
                manifest = load_patchset_manifest(path, validate_paths=False)

                # Count non-null patches
                patch_count = sum(1 for v in manifest.patches.values() if v is not None)
                override_count = len(manifest.workflow_overrides)

                summaries.append(
                    PatchSetSummary(
                        name=name,
                        description=manifest.description,
                        source=str(path),
                        patches=dict(manifest.patches),
                        workflow_overrides=dict(manifest.workflow_overrides),
                        patch_count=patch_count,
                        override_count=override_count,
                        run_count=0,  # Will be updated below
                        last_run=None,
                    )
                )
            except Exception as e:
                logger.warning("Failed to load patch-set manifest %s: %s", name, e)
                continue

        # Get run statistics
        runs = await discover_runs(experiments_dir)
        patchset_names = [s.name for s in summaries]
        stats = get_patchset_run_stats(patchset_names, runs)

        # Update summaries with stats
        updated_summaries = []
        for summary in summaries:
            patchset_stats = stats.get(summary.name)
            updated_summaries.append(
                PatchSetSummary(
                    name=summary.name,
                    description=summary.description,
                    source=summary.source,
                    patches=summary.patches,
                    workflow_overrides=summary.workflow_overrides,
                    patch_count=summary.patch_count,
                    override_count=summary.override_count,
                    run_count=patchset_stats.run_count if patchset_stats else 0,
                    last_run=patchset_stats.last_run if patchset_stats else None,
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
                "patch_sets": [s.model_dump(mode="json") for s in summaries],
                "total": len(summaries),
            }
        )

    except Exception:
        logger.exception("Failed to list patch-sets")
        return JSONResponse(
            {"error": "server_error", "message": "Internal server error"},
            status_code=500,
        )


async def get_experiment_patchset(request: Request) -> JSONResponse:
    """GET /api/experiments/patch-sets/{patchset_name} - Get patch-set details.

    Path parameters:
        patchset_name: The patch-set manifest identifier

    Returns:
        JSON response with full patch-set details or 404.

    """
    from bmad_assist.dashboard.experiments import (
        PatchSetDetails,
        discover_patchsets,
        discover_runs,
        get_patchset_run_stats,
        get_yaml_content,
        validate_run_id,
    )
    from bmad_assist.experiments import load_patchset_manifest

    server = request.app.state.server
    patchset_name = request.path_params["patchset_name"]

    # Validate patchset_name format
    if not validate_run_id(patchset_name):
        return JSONResponse(
            {"error": "bad_request", "message": f"Invalid patchset_name format: {patchset_name}"},
            status_code=400,
        )

    experiments_dir = server.project_root / "experiments"

    try:
        # Discover patch-sets
        patchset_tuples = await discover_patchsets(experiments_dir)

        # Find patch-set by name
        patchset_path = None
        for name, path in patchset_tuples:
            if name == patchset_name:
                patchset_path = path
                break

        if patchset_path is None:
            return JSONResponse(
                {"error": "not_found", "message": f"Patch-set not found: {patchset_name}"},
                status_code=404,
            )

        # Load manifest
        try:
            manifest = load_patchset_manifest(patchset_path, validate_paths=False)
        except Exception as e:
            return JSONResponse(
                {"error": "server_error", "message": f"Failed to load patch-set: {e}"},
                status_code=500,
            )

        # Get run statistics
        runs = await discover_runs(experiments_dir)
        stats = get_patchset_run_stats([patchset_name], runs)
        patchset_stats = stats.get(patchset_name)

        # Get YAML content
        yaml_content = await get_yaml_content(str(patchset_path))

        # Count non-null patches
        patch_count = sum(1 for v in manifest.patches.values() if v is not None)
        override_count = len(manifest.workflow_overrides)

        # Build response
        details = PatchSetDetails(
            name=patchset_name,
            description=manifest.description,
            source=str(patchset_path),
            patches=dict(manifest.patches),
            workflow_overrides=dict(manifest.workflow_overrides),
            patch_count=patch_count,
            override_count=override_count,
            yaml_content=yaml_content,
            run_count=patchset_stats.run_count if patchset_stats else 0,
            last_run=patchset_stats.last_run if patchset_stats else None,
            recent_runs=patchset_stats.recent_runs if patchset_stats else [],
        )

        return JSONResponse(details.model_dump(mode="json"))

    except Exception:
        logger.exception("Failed to get patch-set %s", patchset_name)
        return JSONResponse(
            {"error": "server_error", "message": "Internal server error"},
            status_code=500,
        )


routes = [
    Route("/api/experiments/patch-sets", get_experiments_patchsets, methods=["GET"]),
    Route("/api/experiments/patch-sets/{patchset_name}", get_experiment_patchset, methods=["GET"]),
]
