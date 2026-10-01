"""
safe_endpoint.py — Safe Simplification Endpoint (the endpoint-v6 image)

FastAPI app with three routes:
  POST /v1/simplify     — the fine-tuned student rewrites the text (vLLM, local), then the three-judge safety gate
                          (Nebius Token Factory) checks the rewrite against the original.
  POST /v1/audit_panel  — VAGT panel selection over the pre-computed verdict pool (pure CPU).
  GET  /health          — readiness: vLLM answers and an API key is set (the judges are not called), plus whether the
                          judge routing keys are set and the pool status.

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
import os
import sys
import time
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal

from prompts import STOP, build_prompt
import safety_gate
from safety_gate import evaluate_safety

app = FastAPI(title="MediSimplifier Safe Endpoint", version="2.0")

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
    t_total = (time.time() - t0) * 1000

    return SimplifyResponse(
        simplified_text=None if safety["blocked"] else simplified,
        truncated=truncated,
        blocked=safety["blocked"],
        safety=safety,
        latency_ms={"vllm_ms": round(t_vllm), "total_ms": round(t_total)},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
