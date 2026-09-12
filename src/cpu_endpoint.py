"""
cpu_endpoint.py — Always-on CPU service. Serves ONLY /v1/audit_panel + /health.

This is NOT the safety gate and NOT the simplifier. It exposes exactly one capability:
the deterministic VAGT panel-selection endpoint (POST /v1/audit_panel), which runs
pure CPU over the pre-computed audit_pool — no Token Factory calls, no GPU, no API key.

It mounts the SAME audit_router the GPU endpoint uses (src/audit_panel/router.py), so
the /v1/audit_panel contract is byte-for-byte identical to production; only the host
differs. Run:  cd /app/src && uvicorn cpu_endpoint:app --host 0.0.0.0 --port 8000
"""

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="MediSimplifier — audit_panel (CPU)",
    version="cpu-1.0",
    description="Deterministic VAGT panel selection only. No gate, no simplify.",
)

# Public browser demo hits /v1/audit_panel cross-origin from the hosted static page.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Same sys.path shim safe_endpoint.py uses, so router.py's flat imports
# (pool_loader / selector / schemas) resolve identically.
sys.path.insert(0, str(Path(__file__).resolve().parent / "audit_panel"))
try:
    from router import audit_router, POOL_OK, POOL_ERROR
    app.include_router(audit_router, prefix="/v1")
    AUDIT_OK = True
except Exception as e:          # mount failure -> /health reports it; app still starts
    AUDIT_OK = False
    POOL_OK = False
    POOL_ERROR = str(e)


@app.get("/health")
def health():
    """Liveness + pool status. ready == route mounted AND pool loaded."""
    return {
        "service": "audit_panel-cpu",
        "audit_panel": AUDIT_OK,
        "pool_loaded": bool(POOL_OK),
        "ready": bool(AUDIT_OK and POOL_OK),
        "pool_error": None if POOL_OK else POOL_ERROR,
    }
