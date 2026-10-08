"""
Offline tests for the Safe Endpoint's POST /v1/simplify and GET /health: the evaluation prompt and stop markers
(audit #2, #3, #4), the 1,024 default limit and `truncated` (D2), HTTP 413 for inputs that do not fit, a 503 that
names the failed vLLM step, /health's judge routing-key flags (D17) and pool status (audit #48), a slow gate not
holding up other requests, and P2's explanation: only for a flagged rewrite, changing nothing the gate decided (D9),
the same response with it on and off apart from the explanation and the times, given at most its time limit, and
never failing the request (any failure: unavailable, explainer_error; only its kind logged, never any text). vLLM,
the safety gate and the explanation are replaced with fakes; nothing leaves the machine. Also the CORS allowlist,
CORS_ALLOW_ORIGINS, and that CORS limits browsers only.
"""
import asyncio
import importlib
import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from fastapi.testclient import TestClient  # noqa: E402
import explain  # noqa: E402
import prompts  # noqa: E402
import safe_endpoint as se  # noqa: E402

GATE = {"llama_verdict": "SAFE", "qwen_verdict": "SAFE", "nemotron_verdict": "SAFE", "blocked": False,
        "consensus": "SAFE", "warning": None}
EXPLAINED = explain._explanation(None, [{"source_quote": "acute MI"}], False, 5)   # as the reader gets them
NONE_FOUND = explain._explanation("no_omission_found", (), False, 5)


class _Resp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._body


class FakeVLLM:
    """Stands in for httpx.AsyncClient: answers /tokenize, /v1/completions and /health, and records the calls."""
    def __init__(self, count=300, window=4096, text=" The patient had a heart attack.", finish="stop", health=200,
                 tokenize_status=200, generate_status=200):
        self.count, self.window, self.text, self.finish, self.health = count, window, text, finish, health
        self.tokenize_status, self.generate_status = tokenize_status, generate_status
        self.calls = []

    def __call__(self, *args, **kwargs):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, json=None):
        self.calls.append((url, json))
        if url.endswith("/tokenize"):
            return _Resp(self.tokenize_status, {"count": self.count, "max_model_len": self.window, "tokens": []})
        return _Resp(self.generate_status, {"choices": [{"text": self.text, "finish_reason": self.finish}]})

    async def get(self, url):
        return _Resp(self.health, {})


@pytest.fixture
def client(monkeypatch):
    def make(fake, gate=GATE, key="test-key", explain=None):
        monkeypatch.setattr(se, "httpx", SimpleNamespace(AsyncClient=fake))
        monkeypatch.setattr(se, "evaluate_safety", lambda original, simplified, safety_mode: dict(gate))
        monkeypatch.setattr(se, "explain_flag",
                            explain or (lambda original, simplified, **told: dict(EXPLAINED)))
        if key is None:
            monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
        else:
            monkeypatch.setenv("NEBIUS_API_KEY", key)
        return TestClient(se.app)
    return make


def test_prompt_stop_markers_and_default_limit(client):
    fake = FakeVLLM()
    r = client(fake).post("/v1/simplify", json={"text": "Pt with acute MI."})
    assert r.status_code == 200, r.text
    (tok_url, tok_body), (gen_url, gen_body) = fake.calls
    assert tok_url.endswith("/tokenize") and gen_url.endswith("/v1/completions")
    assert gen_body["prompt"] == tok_body["prompt"] == prompts.build_prompt("Pt with acute MI.")
    assert gen_body["stop"] == ["<|im_end|>", "<|im_start|>"]
    assert gen_body["temperature"] == 0 and gen_body["max_tokens"] == 1024
    out = r.json()
    assert out["simplified_text"] == "The patient had a heart attack." and out["truncated"] is False


def test_max_tokens_is_passed_through(client):
    fake = FakeVLLM()
    assert client(fake).post("/v1/simplify", json={"text": "x", "max_tokens": 200}).status_code == 200
    assert fake.calls[1][1]["max_tokens"] == 200


def test_truncated_when_the_limit_cut_the_rewrite(client):
    assert client(FakeVLLM(finish="length")).post("/v1/simplify", json={"text": "x"}).json()["truncated"] is True


def test_input_too_long_is_413_before_any_generation(client):
    fake = FakeVLLM(count=3500, window=4096)   # 3,500 + 1,024 > 4,096
    r = client(fake).post("/v1/simplify", json={"text": "x"})
    assert r.status_code == 413
    d = r.json()["detail"]
    assert (d["prompt_tokens"], d["max_tokens"], d["context_window"]) == (3500, 1024, 4096)
    assert len(fake.calls) == 1   # only /tokenize was called


def test_a_smaller_max_tokens_fits_the_same_input(client):
    r = client(FakeVLLM(count=3500, window=4096)).post("/v1/simplify", json={"text": "x", "max_tokens": 500})
    assert r.status_code == 200


def test_max_tokens_must_be_positive(client):
    assert client(FakeVLLM()).post("/v1/simplify", json={"text": "x", "max_tokens": 0}).status_code == 422


def test_tokenize_failure_is_503_naming_the_step(client, monkeypatch):
    fake = FakeVLLM(tokenize_status=500)
    c = client(fake)
    gate_calls = []
    monkeypatch.setattr(se, "evaluate_safety", lambda *a, **k: gate_calls.append(a) or dict(GATE))
    r = c.post("/v1/simplify", json={"text": "x"})
    assert r.status_code == 503
    assert r.json()["detail"].startswith("vLLM tokenize failed: ")
    assert len(fake.calls) == 1 and gate_calls == []   # no generation, no gate call


def test_generation_failure_is_503_naming_the_step(client, monkeypatch):
    fake = FakeVLLM(generate_status=500)
    c = client(fake)
    gate_calls = []
    monkeypatch.setattr(se, "evaluate_safety", lambda *a, **k: gate_calls.append(a) or dict(GATE))
    r = c.post("/v1/simplify", json={"text": "x"})
    assert r.status_code == 503
    assert r.json()["detail"].startswith("vLLM generation failed: ")
    assert len(fake.calls) == 2 and gate_calls == []   # tokenize, then the failed generation; no gate call


def test_blocked_rewrite_is_withheld(client):
    gate = dict(GATE, consensus="UNSAFE", blocked=True)
    out = client(FakeVLLM(), gate=gate).post("/v1/simplify", json={"text": "x", "safety_mode": "block"}).json()
    assert out["simplified_text"] is None and out["blocked"] is True


def test_health_ready_means_vllm_up_and_key_set(client):
    h = client(FakeVLLM()).get("/health").json()
    assert (h["vllm"], h["token_factory"], h["ready"]) == (True, True, True)
    h = client(FakeVLLM(), key=None).get("/health").json()
    assert (h["token_factory"], h["ready"]) == (False, False)
    h = client(FakeVLLM(health=503)).get("/health").json()
    assert (h["vllm"], h["ready"]) == (False, False)


def test_health_reports_which_judge_routing_keys_are_set(client, monkeypatch):   # D17
    monkeypatch.setattr(se.safety_gate, "JUDGE_MODELS_SET", {"qwen": True, "llama": False})
    h = client(FakeVLLM()).get("/health").json()
    assert h["judge_models_set"] == {"qwen": True, "llama": False}
    assert h["ready"] is True   # reported, not part of readiness


def test_health_audit_panel_needs_its_pool(client, monkeypatch):   # audit #48
    c = client(FakeVLLM())
    h = c.get("/health").json()
    assert (h["audit_panel"], h["pool_loaded"], h["pool_error"]) == (True, True, None)
    monkeypatch.setattr(se, "POOL_OK", False)
    monkeypatch.setattr(se, "POOL_ERROR", "audit pool missing")
    h = c.get("/health").json()
    assert (h["audit_panel"], h["pool_loaded"], h["pool_error"]) == (False, False, "audit pool missing")
    assert h["ready"] is True   # /v1/simplify can still serve


# ── CORS: in browsers, only the demo page and a local dev server; other clients are not restricted ──
def _preflight(app, origin):
    return TestClient(app).options("/v1/simplify", headers={
        "Origin": origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "Content-Type"})


@pytest.mark.parametrize("origin", ["https://deepset01-sys.github.io", "http://localhost:5173"])
def test_cors_allows_the_demo_page(origin):
    r = _preflight(se.app, origin)
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == origin


def test_cors_refuses_other_origins():
    r = _preflight(se.app, "https://example.com")
    assert r.status_code == 400
    assert "access-control-allow-origin" not in r.headers


def test_cors_limits_browsers_only(client):
    """Another origin, or none (curl, a script), is still answered; only the header a browser needs is missing."""
    c = client(FakeVLLM())
    other, none = c.get("/health", headers={"Origin": "https://example.com"}), c.get("/health")
    demo = c.get("/health", headers={"Origin": "https://deepset01-sys.github.io"})
    assert other.status_code == none.status_code == demo.status_code == 200
    assert "access-control-allow-origin" not in other.headers and "access-control-allow-origin" not in none.headers
    assert demo.headers["access-control-allow-origin"] == "https://deepset01-sys.github.io"


def test_cors_header_on_an_error_too(client):
    """The demo page can read an error as well, e.g. the 413 with its token counts."""
    r = client(FakeVLLM(count=3500, window=4096)).post(
        "/v1/simplify", json={"text": "x"}, headers={"Origin": "https://deepset01-sys.github.io"})
    assert r.status_code == 413
    assert r.headers["access-control-allow-origin"] == "https://deepset01-sys.github.io"


@pytest.fixture
def reload_endpoint(monkeypatch):
    """Reload safe_endpoint with CORS_ALLOW_ORIGINS set; restore the default module afterwards."""
    def _reload(value):
        monkeypatch.setenv("CORS_ALLOW_ORIGINS", value)
        return importlib.reload(se)
    yield _reload
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    importlib.reload(se)


def test_cors_allow_origins_replaces_the_list(reload_endpoint):
    app = reload_endpoint("https://me.example.org, http://localhost:3000").app
    assert _preflight(app, "https://me.example.org").headers["access-control-allow-origin"] == "https://me.example.org"
    assert _preflight(app, "http://localhost:3000").status_code == 200
    assert _preflight(app, "https://deepset01-sys.github.io").status_code == 400
    assert se.cors_origins("") == se.cors_origins(" , ") == se.DEFAULT_CORS_ORIGINS   # empty counts as unset


def test_a_slow_gate_does_not_hold_up_other_requests(client, monkeypatch):
    client(FakeVLLM())   # installs the fake vLLM and the API key; this TestClient is not used
    gate_started, health_answered = threading.Event(), threading.Event()
    seen = {}

    def slow_gate(original, simplified, safety_mode):
        gate_started.set()
        # Stands in for a gate still waiting on its judges: it returns once /health has been answered, or after 10 s.
        seen["health_answered_meanwhile"] = health_answered.wait(timeout=10)
        return dict(GATE)

    monkeypatch.setattr(se, "evaluate_safety", slow_gate)

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=se.app), base_url="http://test") as ac:
            simplify = asyncio.create_task(ac.post("/v1/simplify", json={"text": "x"}))
            while not gate_started.is_set() and not simplify.done():
                await asyncio.sleep(0.01)
            health = await ac.get("/health")
            health_answered.set()
            return (await simplify).status_code, health.status_code

    assert asyncio.run(run()) == (200, 200)
    assert seen["health_answered_meanwhile"]   # with the gate on the event loop, /health could not be answered


# ── P2: the grounded explanation ─────────────────────────────────────────────

@pytest.mark.parametrize("consensus", ["SAFE", "ERROR"])
def test_no_explanation_unless_the_gate_flags(client, consensus):
    calls = []
    c = client(FakeVLLM(), gate=dict(GATE, consensus=consensus),
               explain=lambda original, simplified, **told: calls.append(original) or dict(EXPLAINED))
    out = c.post("/v1/simplify", json={"text": "x"}).json()
    assert calls == [] and out["explanation"] is None


@pytest.mark.parametrize("consensus", ["UNSAFE", "DISAGREE"])
def test_a_flagged_rewrite_gets_the_explanation(client, consensus):
    calls = []
    c = client(FakeVLLM(), gate=dict(GATE, consensus=consensus),
               explain=lambda original, simplified, **told: calls.append((original, simplified))
               or dict(EXPLAINED))
    out = c.post("/v1/simplify", json={"text": "Pt with acute MI."}).json()
    assert calls == [("Pt with acute MI.", "The patient had a heart attack.")]
    assert out["explanation"] == EXPLAINED


@pytest.mark.parametrize("mode, blocked", [("flag", False), ("block", False), ("strict", True)])
@pytest.mark.parametrize("explanation", [EXPLAINED, NONE_FOUND])
def test_the_explanation_changes_nothing_the_gate_decided(client, mode, blocked, explanation):   # D9
    gate = dict(GATE, nemotron_verdict="UNSAFE", consensus="DISAGREE", blocked=blocked,
                warning="diagnosis-drop risk: Nemotron flagged UNSAFE but Qwen passed — manual review recommended")
    c = client(FakeVLLM(), gate=gate, explain=lambda original, simplified, **told: dict(explanation))
    out = c.post("/v1/simplify", json={"text": "x", "safety_mode": mode}).json()
    assert out["safety"] == gate and out["blocked"] is blocked
    assert out["simplified_text"] == (None if blocked else "The patient had a heart attack.")
    assert out["explanation"] == explanation


def test_a_withheld_rewrite_stays_withheld_with_its_explanation(client):
    gate = dict(GATE, qwen_verdict="UNSAFE", consensus="UNSAFE", blocked=True)
    r = client(FakeVLLM(), gate=gate).post("/v1/simplify", json={"text": "x", "safety_mode": "block"})
    out = r.json()
    assert out["simplified_text"] is None and out["blocked"] is True and out["explanation"] == EXPLAINED
    assert "heart attack" not in r.text   # the rewrite appears nowhere in the response


def test_a_slow_explanation_does_not_hold_up_other_requests(client):
    explain_started, health_answered = threading.Event(), threading.Event()
    seen = {}

    def slow_explain(original, simplified, **told):
        explain_started.set()
        # Stands in for an explanation still waiting on Nemotron: returns once /health is answered, or after 10 s.
        seen["health_answered_meanwhile"] = health_answered.wait(timeout=10)
        return dict(EXPLAINED)

    client(FakeVLLM(), gate=dict(GATE, consensus="DISAGREE"), explain=slow_explain)   # installs the fakes only

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=se.app), base_url="http://test") as ac:
            simplify = asyncio.create_task(ac.post("/v1/simplify", json={"text": "x"}))
            while not explain_started.is_set() and not simplify.done():
                await asyncio.sleep(0.01)
            health = await ac.get("/health")
            health_answered.set()
            return (await simplify).status_code, health.status_code

    assert asyncio.run(run()) == (200, 200)
    assert seen["health_answered_meanwhile"]


def test_the_explanation_gets_at_most_the_time_limit(client, monkeypatch):
    monkeypatch.setattr(se, "TIME_LIMIT_S", 0.3)
    release = threading.Event()

    def stuck_explain(original, simplified, **told):
        release.wait(timeout=10)   # stands in for an explanation not done in time
        return dict(EXPLAINED)

    gate = dict(GATE, nemotron_verdict="UNSAFE", consensus="DISAGREE")
    client(FakeVLLM(), gate=gate, explain=stuck_explain)   # installs the fakes only

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=se.app), base_url="http://test") as ac:
            t0 = time.time()
            r = await ac.post("/v1/simplify", json={"text": "x"})
            elapsed = time.time() - t0
        release.set()   # the stuck worker thread ends; the response had long gone out
        return r.json(), elapsed

    out, elapsed = asyncio.run(run())
    assert elapsed < 2
    assert out["safety"] == gate and out["simplified_text"] == "The patient had a heart attack."
    e = out["explanation"]
    assert (e["status"], e["reason"], e["possible_omissions"], e["rewrite_cut"]) == (
        "unavailable", "time_limit", [], False)
    assert e["note"] == explain.time_limit_result(0)["note"]
    assert e["model"] == "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B" and 300 <= e["latency_ms"] < 2000


@pytest.mark.parametrize("finish, cut", [("stop", False), ("length", True)])
def test_the_explanation_is_told_whether_the_rewrite_was_cut(client, finish, cut):
    seen = []
    c = client(FakeVLLM(finish=finish), gate=dict(GATE, qwen_verdict="UNSAFE", consensus="UNSAFE"),
               explain=lambda original, simplified, **told: seen.append(told["rewrite_cut"]) or dict(EXPLAINED))
    out = c.post("/v1/simplify", json={"text": "x"}).json()
    assert seen == [cut] and out["truncated"] is cut


@pytest.mark.parametrize("mode, consensus, withheld", [("flag", "UNSAFE", False), ("block", "UNSAFE", True),
                                                       ("block", "DISAGREE", False), ("strict", "DISAGREE", True)])
def test_the_explanation_is_told_whether_the_rewrite_was_withheld(client, mode, consensus, withheld):
    told = []
    c = client(FakeVLLM(), gate=dict(GATE, consensus=consensus, blocked=withheld),
               explain=lambda original, simplified, **kw: told.append(kw) or dict(EXPLAINED))
    out = c.post("/v1/simplify", json={"text": "x", "safety_mode": mode}).json()
    assert told == [{"rewrite_cut": False, "rewrite_withheld": withheld}] and out["blocked"] is withheld


def test_the_switch_is_off_only_for_off_values():
    for value in ("off", "OFF", " false ", "0", "no", "No"):
        assert se._explanation_enabled(value) is False
    for value in (None, "", "on", "1", "true", "yes", "anything"):
        assert se._explanation_enabled(value) is True


def test_switched_off_the_explanation_is_skipped(client, monkeypatch):
    monkeypatch.setattr(se, "EXPLANATION_ENABLED", False)
    calls = []
    c = client(FakeVLLM(), gate=dict(GATE, nemotron_verdict="UNSAFE", consensus="DISAGREE"),
               explain=lambda original, simplified, **kw: calls.append(original) or dict(EXPLAINED))
    out = c.post("/v1/simplify", json={"text": "x"}).json()
    assert calls == [] and out["explanation"] is None and out["safety"]["consensus"] == "DISAGREE"


@pytest.mark.parametrize("value, enabled", [(None, True), ("off", False), ("on", True)])
def test_the_switch_is_read_at_start_up(value, enabled):
    env = {k: v for k, v in os.environ.items() if k != "EXPLANATION"}
    if value is not None:
        env["EXPLANATION"] = value
    run = subprocess.run([sys.executable, "-c", "import safe_endpoint; print(safe_endpoint.EXPLANATION_ENABLED)"],
                         cwd=REPO / "src", env=env, capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr
    assert run.stdout.strip().splitlines()[-1] == str(enabled)


# ── nothing about the explanation can fail the request ──────────────────────

@pytest.mark.parametrize("mode, consensus, blocked", [("flag", "UNSAFE", False), ("flag", "DISAGREE", False),
                                                      ("block", "UNSAFE", True), ("strict", "DISAGREE", True)])
def test_the_response_is_the_same_with_p2_on_and_off(client, monkeypatch, mode, consensus, blocked):
    gate = dict(GATE, consensus=consensus, blocked=blocked)
    out = {}
    for on in (True, False):
        monkeypatch.setattr(se, "EXPLANATION_ENABLED", on)
        out[on] = client(FakeVLLM(), gate=gate).post("/v1/simplify",
                                                     json={"text": "Pt with acute MI.", "safety_mode": mode}).json()
    rest = lambda o: {k: v for k, v in o.items() if k not in ("explanation", "latency_ms")}
    assert rest(out[True]) == rest(out[False])
    assert out[True]["explanation"] == EXPLAINED and out[False]["explanation"] is None
    assert set(out[True]["latency_ms"]) == set(out[False]["latency_ms"]) == {"vllm_ms", "total_ms"}


UNEXPECTED = ("No explanation, because the explainer failed unexpectedly. This is not a finding; the gate's verdict "
              "stands.")


@pytest.mark.parametrize("error", [RuntimeError("boom"), KeyError("source_quote"), ValueError("bad"),
                                   ZeroDivisionError(), TypeError("odd"), MemoryError()],
                         ids=lambda e: type(e).__name__)
def test_any_failure_inside_p2_gives_an_unavailable_explanation_and_a_normal_response(client, error):
    def failing_explain(original, simplified, **told):
        raise error
    gate = dict(GATE, nemotron_verdict="UNSAFE", consensus="DISAGREE")
    r = client(FakeVLLM(), gate=gate, explain=failing_explain).post("/v1/simplify", json={"text": "x"})
    assert r.status_code == 200
    out = r.json()
    assert out["safety"] == gate and out["simplified_text"] == "The patient had a heart attack."
    e = out["explanation"]
    assert (e["status"], e["reason"], e["possible_omissions"], e["note"]) == (
        "unavailable", "explainer_error", [], UNEXPECTED)


def test_a_failing_check_call_inside_the_real_explainer_is_caught(client, monkeypatch):
    class Reply:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": '{"defects": [{"type": "D1", "source_quote": "hypertension"}],'
                                                        ' "verdict": "FAIL"}'}, "finish_reason": "stop"}]}

    def failing_check(*args, **kwargs):
        raise RuntimeError("the check failed")
    monkeypatch.setattr(explain.requests, "post", lambda *a, **k: Reply())
    monkeypatch.setattr(explain, "_found_in_rewrite", failing_check)
    c = client(FakeVLLM(), gate=dict(GATE, qwen_verdict="UNSAFE", consensus="UNSAFE"), explain=explain.explain_flag)
    r = c.post("/v1/simplify", json={"text": "Diagnosis: hypertension."})
    assert r.status_code == 200 and r.json()["explanation"]["reason"] == "explainer_error"


@pytest.mark.parametrize("value", [42, "text", None, [1, 2], {"status": object()}], ids=repr)
def test_an_explanation_that_is_not_plain_json_does_not_fail_the_request(client, value):
    c = client(FakeVLLM(), gate=dict(GATE, consensus="UNSAFE"), explain=lambda original, simplified, **told: value)
    r = c.post("/v1/simplify", json={"text": "x"})
    assert r.status_code == 200 and r.json()["explanation"]["reason"] == "explainer_error"


def test_on_a_failure_only_its_kind_reaches_the_log(client, caplog):
    def failing_explain(original, simplified, **told):
        raise RuntimeError(f"failed on {original} / {simplified}")   # an exception that carries the text
    caplog.set_level(logging.DEBUG)
    c = client(FakeVLLM(text=" REWRITE-TEXT-5512"), gate=dict(GATE, consensus="UNSAFE"), explain=failing_explain)
    r = c.post("/v1/simplify", json={"text": "SOURCE-TEXT-7731 acute MI"})
    assert r.json()["explanation"]["reason"] == "explainer_error" and "failed on" not in r.text
    logged = [(rec.name, rec.levelname, rec.getMessage(), rec.exc_info, rec.exc_text) for rec in caplog.records]
    assert ("safe_endpoint", "WARNING", "explanation unavailable (explainer_error): RuntimeError", None, None) in logged
    assert not any("TEXT-7731" in str(entry) or "TEXT-5512" in str(entry) for entry in logged)


@pytest.mark.parametrize("raised, builder", [(RuntimeError("x"), "error_result"),
                                             (TimeoutError(), "time_limit_result")])
def test_even_a_failing_fallback_cannot_fail_the_request(client, monkeypatch, raised, builder):
    def failing_explain(original, simplified, **told):
        raise raised
    monkeypatch.setattr(se, builder, lambda *args, **kwargs: 1 / 0)
    r = client(FakeVLLM(), gate=dict(GATE, consensus="UNSAFE"), explain=failing_explain).post("/v1/simplify",
                                                                                            json={"text": "x"})
    assert r.status_code == 200 and r.json()["explanation"] == se.EXPLANATION_FAILED
    assert se.EXPLANATION_FAILED["reason"] == "explainer_error"
