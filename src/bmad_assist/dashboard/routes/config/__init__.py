"""Config route handlers package.

Provides endpoints for:
- CRUD operations on global/project config
- Schema information
- Backup and restore
- Import/export
"""

from .backup import routes as backup_routes
from .crud import routes as crud_routes
from .import_export import routes as import_export_routes
from .schema import routes as schema_routes

routes = crud_routes + schema_routes + backup_routes + import_export_routes

__all__ = ["routes"]
