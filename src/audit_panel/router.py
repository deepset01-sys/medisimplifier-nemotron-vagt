"""
router.py — FastAPI router for POST /v1/audit_panel.

Loads the audit pool ONCE at import (spec: pre-computed verdicts, ~5MB, loaded at
startup). Request-time work is pure CPU over that in-memory pool — no Token Factory
calls. Mounted in safe_endpoint.py with prefix "/v1".

Flat imports (pool_loader / selector / schemas) match the rest of src/audit_panel
and the test suite; safe_endpoint.py puts this directory on sys.path before import.
"""

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from pool_loader import Pool          # noqa: E402
import selector                       # noqa: E402
from schemas import AuditRequest, AuditResponse  # noqa: E402

audit_router = APIRouter()

# Load once at import. A missing/broken pool is surfaced (503) rather than crashing
# the whole app — safe_endpoint.py also guards the mount so /v1/simplify survives.
try:
    POOL = Pool.load()
    POOL_OK = True
    POOL_ERROR = None
except Exception as e:  # pragma: no cover
    POOL = None
    POOL_OK = False
    POOL_ERROR = str(e)


@audit_router.post("/audit_panel", response_model=AuditResponse)
def audit_panel_route(req: AuditRequest):
    """Rank the candidate pool for the incumbent panel; recommend a third rater.

    Pure CPU over pre-computed verdicts — no live judge calls."""
    if not POOL_OK:
        raise HTTPException(status_code=503, detail=f"audit pool unavailable: {POOL_ERROR}")
    try:
        return selector.audit_panel(
            POOL, req.incumbent_panel, req.candidate_pool,
            bootstrap_iters=req.bootstrap_iters, seed=req.seed,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
