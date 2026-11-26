"""
Gate A test bootstrap — minimal imports for runtime tests.

Imports only what's necessary for lease, fencing, and recovery tests.
Avoids loading FastAPI app and external dependencies.
"""

import sys
from pathlib import Path

# Add backend directory to path to allow direct module imports
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Import only what's needed for Gate A tests
from app.services.projection_checkpoint_lease_service import ProjectionCheckpointLeaseService
from database.models import ProjectionCheckpoint, Tenant, utc_now

__all__ = [
    "ProjectionCheckpointLeaseService",
    "ProjectionCheckpoint",
    "Tenant",
    "utc_now",
]
