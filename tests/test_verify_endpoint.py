"""
scripts/verify_endpoint.py: which checks pass, warn or fail, and when it stops before /v1/simplify (D11: a Qwen or
Nemotron ERROR fails, a Llama ERROR warns and fails with --all; a missing QWEN_JUDGE_MODEL fails and stops, a missing
LLAMA_JUDGE_MODEL warns and fails with --all). requests is replaced with fakes; nothing leaves the machine.
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import verify_endpoint as ve  # noqa: E402

HEALTH = {"vllm": True, "token_factory": True, "ready": True, "judge_models_set": {"qwen": True, "llama": True},
          "audit_panel": True, "pool_loaded": True, "pool_error": None}
BODY = {"simplified_text": "The patient had a lung infection.", "truncated": False, "blocked": False,
        "safety": {"llama_verdict": "SAFE", "qwen_verdict": "SAFE", "nemotron_verdict": "SAFE", "blocked": False,
                   "consensus": "SAFE", "warning": None},
        "latency_ms": {"vllm_ms": 900, "total_ms": 25000}}


class _Resp:
    def __init__(self, status, body):
        self.status_code, self._body, self.text = status, body, str(body)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise ve.requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._body


@pytest.fixture
def run(monkeypatch, capsys):
    """Run the script against fake /health and /v1/simplify answers; return (exit code, output, posted)."""
    def _run(health=HEALTH, body=BODY, status=200, post_error=None, args=()):
        posted = []

        def get(url, timeout):
            if isinstance(health, Exception):
                raise health
            return _Resp(200, health)

        def post(url, json, timeout):
            posted.append(json)
            if post_error:
                raise post_error
            return _Resp(status, body)

        monkeypatch.setattr(ve.requests, "get", get)
        monkeypatch.setattr(ve.requests, "post", post)
        code = ve.main(["https://endpoint.example", *args])
        return code, capsys.readouterr().out, posted
    return _run


def with_verdict(judge, verdict):
    return dict(BODY, safety=dict(BODY["safety"], **{f"{judge}_verdict": verdict}))


def test_all_checks_pass(run):
    code, out, posted = run()
    assert code == 0 and "verify: PASS (0 failed, 0 warnings)" in out
    assert posted == [{"text": ve.SAMPLE, "safety_mode": "flag"}]


@pytest.mark.parametrize("health, expected", [
    (ConnectionError("refused"), "/health: no usable answer"),
    (dict(HEALTH, vllm=False, ready=False), "vLLM is not answering yet"),
    (dict(HEALTH, token_factory=False, ready=False), "NEBIUS_API_KEY is not set"),
    ({k: v for k, v in HEALTH.items() if k != "judge_models_set"}, "image older than this code"),
    (dict(HEALTH, judge_models_set={"qwen": False, "llama": True}), "QWEN_JUDGE_MODEL is not set"),
])
def test_stops_before_simplify(run, health, expected):
    code, out, posted = run(health=health)
    assert code == 1 and expected in out and posted == []


@pytest.mark.parametrize("args, level, code", [((), "WARN", 0), (("--all",), "FAIL", 1)])
def test_missing_llama_variable_warns_and_fails_with_all(run, args, level, code):
    got, out, posted = run(health=dict(HEALTH, judge_models_set={"qwen": True, "llama": False}), args=args)
    assert got == code and posted
    assert any(line.startswith(level) and "LLAMA_JUDGE_MODEL is not set" in line for line in out.splitlines())


@pytest.mark.parametrize("judge, args, level, code", [
    ("qwen", (), "FAIL", 1), ("nemotron", (), "FAIL", 1), ("llama", (), "WARN", 0), ("llama", ("--all",), "FAIL", 1),
])
def test_judge_error_levels(run, judge, args, level, code):
    got, out, _ = run(body=with_verdict(judge, "ERROR"), args=args)
    line = next(l for l in out.splitlines() if "returned ERROR" in l)
    assert got == code and line.startswith(level) and "The endpoint does not say why" in line


@pytest.mark.parametrize("body, expected", [
    (dict(BODY, simplified_text=""), "the rewrite is empty"),
    (dict(BODY, truncated=True), "stopped at max_tokens"),
    (dict(BODY, simplified_text="Done.<|im_end|>"), "end-of-answer marker"),
])
def test_rewrite_checks(run, body, expected):
    code, out, _ = run(body=body)
    assert code == 1 and expected in out


def test_http_error_is_reported_with_its_detail(run):
    code, out, _ = run(status=503, body={"detail": "vLLM generation failed: HTTP 500"})
    assert code == 1 and "HTTP 503" in out and "vLLM generation failed" in out


def test_client_time_out_is_not_a_judge_verdict(run):
    code, out, _ = run(post_error=ve.requests.Timeout("read timed out"))
    assert code == 1 and "no answer within 600 s" in out and "returned ERROR" not in out
