"""Experiments route handlers package.

Provides endpoints for:
- Listing and viewing experiment runs
- Fixtures management
- Config, loop, and patch-set templates
- Run comparison
- Experiment triggering and cancellation
"""

from .compare import routes as compare_routes
from .configs import routes as configs_routes
from .fixtures import routes as fixtures_routes
from .loops import routes as loops_routes
from .patchsets import routes as patchsets_routes
from .runs import routes as runs_routes

routes = (
    runs_routes
    + fixtures_routes
    + compare_routes
    + configs_routes
    + loops_routes
    + patchsets_routes
)

__all__ = ["routes"]
