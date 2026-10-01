"""
Static checks on the endpoint image's build files, so the pins cannot drift unnoticed: the vLLM base pinned by
digest, no unpinned pip installs, the v2 pool served, /start.sh as the entry point, the served model's revision
pinned, and the context window matching the endpoint's fallback. Offline; nothing is built.
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOCKERFILE = (REPO / "docker" / "Dockerfile.endpoint").read_text(encoding="utf-8")
START = (REPO / "scripts" / "start_endpoint.sh").read_text(encoding="utf-8")


def _instructions():
    return [line.strip() for line in DOCKERFILE.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def test_base_image_pinned_by_digest():
    froms = [i for i in _instructions() if i.startswith("FROM ")]
    assert froms == ["FROM vllm/vllm-openai:v0.25.0@sha256:fc56161ee42a011aeee78b65d0a81b6683c7d04402fd40503d14d4d6c98f07cb"]


def test_no_unpinned_pip_install():
    assert not any("pip install" in i for i in _instructions())


def test_serves_the_v2_pool_and_starts_with_start_sh():
    ins = _instructions()
    assert "COPY audit_pool_v2/ ./audit_pool_v2/" in ins
    assert "ENV AUDIT_POOL_DIR=audit_pool_v2" in ins
    assert ins[-1] == 'ENTRYPOINT ["/start.sh"]'


def test_served_model_revision_pinned():
    rev = re.search(r'^MODEL_REVISION="([0-9a-f]{40})"', START, re.M)
    assert rev, "MODEL_REVISION must be a 40-character commit hash"
    assert '--revision "${MODEL_REVISION}"' in START and '--tokenizer-revision "${MODEL_REVISION}"' in START


def test_context_window_matches_the_endpoint_fallback():
    sys.path.insert(0, str(REPO / "src"))
    import safe_endpoint
    assert re.search(r"--max-model-len (\d+)", START).group(1) == str(safe_endpoint.CONTEXT_WINDOW)
