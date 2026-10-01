"""
The gate's two Token Factory dedicated judge endpoints are configurable (QWEN_JUDGE_MODEL, LLAMA_JUDGE_MODEL), with
this project's endpoints as defaults; surrounding whitespace is removed, an empty or whitespace-only value counts as
unset, and JUDGE_MODELS_SET records which variables were set (D17). Nothing else in the gate changes. Offline:
_call_judge is replaced.
"""
import importlib
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
import safety_gate  # noqa: E402

DEFAULT_QWEN = "dedicated/Qwen/Qwen3-32B-AcpEMaRtFNy6"
DEFAULT_LLAMA = "dedicated/meta-llama/Llama-3.3-70B-Instruct-KrpmhZ"


@pytest.fixture
def reload_gate(monkeypatch):
    """Reload safety_gate under the given environment; restore the default module afterwards."""
    def _reload(qwen=None, llama=None):
        for name, value in (("QWEN_JUDGE_MODEL", qwen), ("LLAMA_JUDGE_MODEL", llama)):
            if value is None:
                monkeypatch.delenv(name, raising=False)
            else:
                monkeypatch.setenv(name, value)
        return importlib.reload(safety_gate)
    yield _reload
    monkeypatch.delenv("QWEN_JUDGE_MODEL", raising=False)
    monkeypatch.delenv("LLAMA_JUDGE_MODEL", raising=False)
    importlib.reload(safety_gate)


def test_defaults_are_this_projects_endpoints(reload_gate):
    sg = reload_gate()
    assert (sg.QWEN_DEDICATED, sg.LLAMA_DEDICATED) == (DEFAULT_QWEN, DEFAULT_LLAMA)


def test_routing_keys_come_from_the_environment(reload_gate):
    sg = reload_gate(qwen="dedicated/Qwen/Qwen3-32B-mine", llama="dedicated/meta-llama/Llama-3.3-70B-Instruct-mine")
    assert sg.QWEN_DEDICATED == "dedicated/Qwen/Qwen3-32B-mine"
    assert sg.LLAMA_DEDICATED == "dedicated/meta-llama/Llama-3.3-70B-Instruct-mine"


def test_judge_models_set_records_which_variables_were_set(reload_gate):   # D17
    assert reload_gate().JUDGE_MODELS_SET == {"qwen": False, "llama": False}
    assert reload_gate(qwen="dedicated/q-mine").JUDGE_MODELS_SET == {"qwen": True, "llama": False}
    assert reload_gate(llama="dedicated/l-mine").JUDGE_MODELS_SET == {"qwen": False, "llama": True}


def test_an_empty_variable_counts_as_unset(reload_gate):   # D17
    sg = reload_gate(qwen="", llama="")
    assert (sg.QWEN_DEDICATED, sg.LLAMA_DEDICATED) == (DEFAULT_QWEN, DEFAULT_LLAMA)
    assert sg.JUDGE_MODELS_SET == {"qwen": False, "llama": False}


def test_a_value_equal_to_the_default_counts_as_set(reload_gate):   # D17: our own runs set exactly these keys
    sg = reload_gate(qwen=DEFAULT_QWEN, llama=DEFAULT_LLAMA)
    assert (sg.QWEN_DEDICATED, sg.LLAMA_DEDICATED) == (DEFAULT_QWEN, DEFAULT_LLAMA)
    assert sg.JUDGE_MODELS_SET == {"qwen": True, "llama": True}


def test_surrounding_whitespace_is_removed(reload_gate):   # D17: a whitespace-only value counts as unset
    sg = reload_gate(qwen="  dedicated/q-mine \n", llama="\tdedicated/l-mine ")
    assert (sg.QWEN_DEDICATED, sg.LLAMA_DEDICATED) == ("dedicated/q-mine", "dedicated/l-mine")
    assert sg.JUDGE_MODELS_SET == {"qwen": True, "llama": True}
    sg = reload_gate(qwen="   ", llama=" \t\n")
    assert (sg.QWEN_DEDICATED, sg.LLAMA_DEDICATED) == (DEFAULT_QWEN, DEFAULT_LLAMA)
    assert sg.JUDGE_MODELS_SET == {"qwen": False, "llama": False}


def test_evaluate_safety_calls_the_configured_endpoints(reload_gate, monkeypatch):
    sg = reload_gate(qwen="dedicated/q-mine", llama="dedicated/l-mine")
    monkeypatch.setenv("NEBIUS_API_KEY", "test-key")
    seen = {}
    monkeypatch.setattr(sg, "_call_judge",
                        lambda original, simplified, model, key, max_tokens: seen.setdefault(model, max_tokens) and "SAFE")
    sg.evaluate_safety("original", "simplified")
    assert seen == {"dedicated/l-mine": 2000, "dedicated/q-mine": 8000, sg.NEMOTRON_NANO: 8000}
