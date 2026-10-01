"""
Offline tests for the Safe Endpoint's POST /v1/simplify and GET /health: the evaluation prompt and stop markers
(audit #2, #3, #4), the 1,024 default limit and `truncated` (D2), HTTP 413 for inputs that do not fit, a 503 that
names the failed vLLM step, and /health's judge routing-key flags (D17) and pool status (audit #48). vLLM and the
safety gate are replaced with fakes; nothing leaves the machine.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from fastapi.testclient import TestClient  # noqa: E402
import prompts  # noqa: E402
import safe_endpoint as se  # noqa: E402

GATE = {"llama_verdict": "SAFE", "qwen_verdict": "SAFE", "nemotron_verdict": "SAFE", "blocked": False,
        "consensus": "SAFE", "warning": None}


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
    def make(fake, gate=GATE, key="test-key"):
        monkeypatch.setattr(se, "httpx", SimpleNamespace(AsyncClient=fake))
        monkeypatch.setattr(se, "evaluate_safety", lambda original, simplified, safety_mode: dict(gate))
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
