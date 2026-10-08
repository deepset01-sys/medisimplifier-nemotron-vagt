"""
safe_endpoint.py — Safe Simplification Endpoint (the endpoint-v6 image)

FastAPI app with three routes:
  POST /v1/simplify     — the fine-tuned student rewrites the text (vLLM, local), then the three-judge safety gate
                          (Nebius Token Factory) checks the rewrite against the original; when the gate flags it, the
                          explanation (src/explain.py, advisory) lists diagnoses from the original it did not find in
                          the rewrite, as possible omissions to check, within at most 30 s. It is on by default;
                          EXPLANATION=off at start-up (also false, 0 or no) skips it, and `explanation` is null.
                          Nothing about the explanation can fail the request: if anything goes wrong there, it is
                          unavailable (explainer_error), and only the kind of failure is logged, never any text.
  POST /v1/audit_panel  — VAGT panel selection over the pre-computed verdict pool (pure CPU).
  GET  /health          — readiness: vLLM answers and an API key is set (the judges are not called), plus whether the
                          judge routing keys are set and the pool status.

Browsers may call it cross-origin only from the project's demo page (GitHub Pages) and a local `npm run dev` of it;
CORS_ALLOW_ORIGINS, a comma-separated list of origins, replaces that list. CORS limits browsers only: any other client
can call the endpoint, so its URL is its only access control.

The rewrite uses the published evaluation's prompt (src/prompts.py), stops at the model's end-of-answer marker, and is
limited to max_tokens (default 1,024; the published evaluation outputs used 512). `truncated` reports a rewrite cut at
that limit. A request whose prompt and max_tokens do not fit the context window together returns HTTP 413.

Deployed as a Nebius AI Endpoint, not a Job: see docs/REPRODUCIBILITY.md and the reference manifest
jobs/safe_endpoint_v2.yaml. Locally, on a GPU machine:
  docker run --gpus all -p 8000:8000 \
    -e NEBIUS_API_KEY=<key> -e QWEN_JUDGE_MODEL=<routing key> -e LLAMA_JUDGE_MODEL=<routing key> \
    chambul/medisimplifier:endpoint-v6
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Literal

from explain import EXPLAIN_ON, TIME_LIMIT_S, error_result, explain_flag, time_limit_result
from prompts import STOP, build_prompt
import safety_gate
from safety_gate import evaluate_safety

app = FastAPI(title="MediSimplifier Safe Endpoint", version="2.0")

# Browsers may call this endpoint cross-origin only from the project's demo page (GitHub Pages) and from a local
# `npm run dev` of it (app/README.md). CORS_ALLOW_ORIGINS, a comma-separated list of origins, replaces this list.
# CORS binds browsers only; it does not restrict other clients: the endpoint URL is the only access control.
DEFAULT_CORS_ORIGINS = ["https://deepset01-sys.github.io", "http://localhost:5173"]


def cors_origins(value):
    """The origins in a CORS_ALLOW_ORIGINS value; the default list when it is unset or empty."""
    return [o.strip() for o in (value or "").split(",") if o.strip()] or list(DEFAULT_CORS_ORIGINS)


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(os.environ.get("CORS_ALLOW_ORIGINS")),   # read once, at start-up
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# ── Mount the /v1/audit_panel router. Graceful: a missing/broken audit_pool
# disables it but leaves /v1/simplify fully working; /health reports the status. ──
sys.path.insert(0, str(Path(__file__).resolve().parent / "audit_panel"))
try:
    from router import audit_router, POOL_OK, POOL_ERROR
    app.include_router(audit_router, prefix="/v1")
    AUDIT_OK = True
except Exception as e:
    AUDIT_OK = False
    POOL_OK = False
    POOL_ERROR = str(e)

VLLM_BASE         = "http://127.0.0.1:8001"
VLLM_URL          = VLLM_BASE + "/v1/completions"
VLLM_TOKENIZE_URL = VLLM_BASE + "/tokenize"
MODEL_NAME        = "chambul/MediSimplifier-OpenBioLLM-v2-merged"
CONTEXT_WINDOW    = 4096   # vLLM's --max-model-len in scripts/start_endpoint.sh; /tokenize reports the live value


def _explanation_enabled(value) -> bool:
    """The EXPLANATION switch: off for "off", "false", "0" or "no" (letter case and surrounding spaces aside); on for
    anything else, unset included."""
    return (value or "").strip().lower() not in ("off", "false", "0", "no")


EXPLANATION_ENABLED = _explanation_enabled(os.environ.get("EXPLANATION"))   # read once, at start-up
EXPLANATION_FAILED = error_result(0)   # the last fallback: built once, here, so returning it cannot fail
log = logging.getLogger("safe_endpoint")


async def _explanation_for(original: str, simplified: str, rewrite_cut: bool, rewrite_withheld: bool) -> dict:
    """P2 for one flagged rewrite. Nothing in it can fail the request: a time-out makes the explanation unavailable
    (time_limit); any other failure, in the explainer, in building its fields, or a value that is not plain JSON, makes
    it unavailable (explainer_error). On such a failure only its kind, the exception's class name, is logged: never its
    message, never any text."""
    t0 = time.time()
    told = {"rewrite_cut": rewrite_cut, "rewrite_withheld": rewrite_withheld}
    try:
        try:
            explanation = await asyncio.wait_for(asyncio.to_thread(explain_flag, original, simplified, **told),
                                                 timeout=TIME_LIMIT_S)
            if not isinstance(explanation, dict):
                raise TypeError
            json.dumps(explanation)   # plain JSON, or the response itself could not be sent
            return explanation
        except asyncio.TimeoutError:
            return time_limit_result(round((time.time() - t0) * 1000), **told)
        except Exception as e:
            log.warning("explanation unavailable (explainer_error): %s", type(e).__name__)
            return error_result(round((time.time() - t0) * 1000), **told)
    except Exception:
        return dict(EXPLANATION_FAILED)


class SimplifyRequest(BaseModel):
    text: str
    max_tokens: int = Field(1024, ge=1)
    safety_mode: Literal["flag", "block", "strict"] = "flag"


class SimplifyResponse(BaseModel):
    simplified_text: Optional[str]
    truncated: bool
    blocked: bool
    safety: dict
    latency_ms: dict
    explanation: Optional[dict] = None   # P2: only when the gate flags the rewrite; advisory, never changes `safety`


@app.get("/health")
async def health():
    """Readiness: vLLM answers and an API key is set. The judges are not called here (the platform probes this route
    often); scripts/verify_endpoint.py checks them through /v1/simplify. judge_models_set says whether
    QWEN_JUDGE_MODEL and LLAMA_JUDGE_MODEL were set (where false, the gate uses this project's default routing key).
    audit_panel is true only when the route is mounted and its verdict pool loaded."""
    vllm_ok = False
    tf_ok = bool(os.environ.get("NEBIUS_API_KEY"))
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(VLLM_BASE + "/health")
            vllm_ok = r.status_code == 200
    except Exception:
        pass
    return {"vllm": vllm_ok, "token_factory": tf_ok, "ready": vllm_ok and tf_ok,
            "judge_models_set": safety_gate.JUDGE_MODELS_SET,
            "audit_panel": bool(AUDIT_OK and POOL_OK), "pool_loaded": bool(POOL_OK),
            "pool_error": None if POOL_OK else POOL_ERROR}


@app.post("/v1/simplify", response_model=SimplifyResponse)
async def simplify(req: SimplifyRequest):
    """Rewrite the text with the student model, then run the three-judge safety gate on the rewrite."""
    t0 = time.time()
    prompt = build_prompt(req.text)

    # ── Step 1: the student rewrite (vLLM) ───────────────────────────
    step = "tokenize"   # named in the 503 detail: which vLLM call failed
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            tok = await client.post(VLLM_TOKENIZE_URL, json={"model": MODEL_NAME, "prompt": prompt})
            tok.raise_for_status()
            counts = tok.json()
            prompt_tokens = counts["count"]
            window = counts.get("max_model_len") or CONTEXT_WINDOW
            if prompt_tokens + req.max_tokens > window:
                raise HTTPException(status_code=413, detail={
                    "error": "input too long: the prompt and max_tokens must fit the context window together",
                    "prompt_tokens": prompt_tokens, "max_tokens": req.max_tokens, "context_window": window})
            step = "generation"
            vllm_resp = await client.post(VLLM_URL, json={
                "model":       MODEL_NAME,
                "prompt":      prompt,
                "max_tokens":  req.max_tokens,
                "temperature": 0,
                "stop":        STOP,
            })
            vllm_resp.raise_for_status()
            choice = vllm_resp.json()["choices"][0]
            simplified = choice["text"].strip()
            truncated = choice.get("finish_reason") == "length"
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"vLLM {step} failed: {e}")

    t_vllm = (time.time() - t0) * 1000

    # ── Step 2: the three-judge safety gate ──────────────────────────
    # In a worker thread: the gate blocks while it waits on the judges (minutes, when one never answers), and the
    # server must go on answering other requests, /health included.
    safety = await asyncio.to_thread(evaluate_safety, req.text, simplified, safety_mode=req.safety_mode)

    # ── Step 3 (P2): the explanation (possible omissions), only for a flagged rewrite, unless switched off ──
    # Advisory: it changes none of the gate's output (D9). Its quotes come from the request's own text, so a withheld
    # rewrite stays withheld. In a worker thread, like the gate, for at most TIME_LIMIT_S (30 s): explain_flag keeps to
    # that limit itself, and if it is still not done then, the response goes out with it unavailable (time_limit).
    # Nothing in it can fail the request (_explanation_for).
    explanation = None
    if EXPLANATION_ENABLED and safety["consensus"] in EXPLAIN_ON:
        explanation = await _explanation_for(req.text, simplified, truncated, safety["blocked"])
    t_total = (time.time() - t0) * 1000

    return SimplifyResponse(
        simplified_text=None if safety["blocked"] else simplified,
        truncated=truncated,
        blocked=safety["blocked"],
        safety=safety,
        latency_ms={"vllm_ms": round(t_vllm), "total_ms": round(t_total)},
        explanation=explanation,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
