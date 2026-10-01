"""
scripts/start_endpoint.sh gives up instead of hanging (D15): it exits non-zero, with the reason, if vLLM dies before
it is ready or is not ready within VLLM_START_TIMEOUT. vLLM (python3) and curl are replaced with stubs on PATH, so
nothing is started or downloaded. Needs bash; skipped where there is none.
"""
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "start_endpoint.sh"
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="needs bash")


def _run(tmp_path, python3_body, start_timeout):
    for name, body in (("python3", python3_body), ("curl", "printf 000")):
        stub = tmp_path / name
        stub.write_text("#!/bin/sh\n" + body + "\n", newline="\n")
        stub.chmod(0o755)
    env = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ.get("PATH", ""),
               VLLM_START_TIMEOUT=str(start_timeout))
    t0 = time.time()
    p = subprocess.run([BASH, str(SCRIPT)], env=env, capture_output=True, text=True, timeout=90)
    return p, time.time() - t0


def test_exits_when_vllm_dies_before_it_is_ready(tmp_path):
    p, seconds = _run(tmp_path, "exit 3", start_timeout=1800)
    assert p.returncode == 1, p.stdout + p.stderr
    assert "vLLM exited before it was ready (exit code 3)" in p.stderr
    assert seconds < 45   # one 15 s poll at most, not the 1,800 s limit


def test_gives_up_after_the_start_timeout(tmp_path):
    p, seconds = _run(tmp_path, "exec sleep 60", start_timeout=0)   # exec: the stub IS the long-running process
    assert p.returncode == 1, p.stdout + p.stderr
    assert "vLLM was not ready after 0 s" in p.stderr
    assert seconds < 45
