"""
scripts/record_replay_run.py: one image reference for the endpoint, the container and --image, and the settings on
the container's standard input only. nebius, git and docker are replaced with fakes; the endpoint's record is
invented and holds an invented key, so the tests also show that nothing from the record but its image is printed.
Nothing leaves the machine.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import record_replay_run as rrr  # noqa: E402

DIGEST = "sha256:" + "a" * 64
IMAGE = "chambul/medisimplifier@" + DIGEST
URL = "https://port8000-invented.example.nebius.cloud"
COMMIT = "b" * 40
INVENTED_KEY = "invented-key-from-the-record"
RECORD = {"metadata": {"name": "endpoint-invented", "id": "aiendpoint-invented"},
          "spec": {"image": IMAGE, "environment_variables": [{"name": "NEBIUS_API_KEY", "value": INVENTED_KEY},
                                                             {"name": "QWEN_JUDGE_MODEL", "value": "invented/qwen"}]},
          "status": {"state": "RUNNING", "public_endpoints": [URL]}}
ENV = {"NEBIUS_API_KEY": "invented-key-in-this-environment", "QWEN_JUDGE_MODEL": "invented/qwen-routing-key",
       "LLAMA_JUDGE_MODEL": "invented/llama-routing-key"}
NAMES = {"ENDPOINT_URL", *rrr.SETTINGS}


@pytest.fixture
def run(tmp_path, monkeypatch, capsys):
    """Run the runner with fake nebius, git and docker; return (exit code, output, calls, what each fake was given:
    its environment by program, and docker's standard input)."""
    def _run(args, record=RECORD, changed="", env=None):
        calls, seen = [], {}
        for name, value in (ENV if env is None else env).items():
            monkeypatch.setenv(name, value)

        def fake(command, **kw):
            calls.append(command)
            seen[command[0]] = kw.get("env")
            if command[0] == "nebius":
                return subprocess.CompletedProcess(command, 0, "some banner\n" + json.dumps(record, indent=1), "")
            if command[:4] == ["git", "-C", str(rrr.REPO), "rev-parse"]:
                return subprocess.CompletedProcess(command, 0, COMMIT + "\n", "")
            if command[:4] == ["git", "-C", str(rrr.REPO), "status"]:
                return subprocess.CompletedProcess(command, 0, changed, "")
            if command[0] == "docker":
                seen["stdin"] = kw.get("input")
                return subprocess.CompletedProcess(command, 0)
            raise AssertionError(command)

        monkeypatch.setattr(rrr.subprocess, "run", fake)
        code = rrr.main(args + ["--out-dir", str(tmp_path / "out")])
        return code, capsys.readouterr().out, calls, seen
    return _run


def docker_call(calls):
    return next((c for c in calls if c[0] == "docker"), None)


def after(command, flag):
    return command[command.index(flag) + 1]


def test_one_image_reference_for_the_endpoint_the_container_and_the_recording(run):
    code, out, calls, seen = run(["record", "--endpoint-id", "aiendpoint-invented", "--image", IMAGE])
    docker = docker_call(calls)
    assert code == 0 and docker is not None
    assert docker[docker.index("python3") + 1:].count(IMAGE) == 1           # the container runs the image named
    assert after(docker, "--image") == DIGEST and after(docker, "--commit") == COMMIT
    assert json.loads(seen["stdin"])["ENDPOINT_URL"] == URL and "--rehearsal" not in docker
    assert "--network" not in docker


def test_the_settings_reach_the_container_only_on_its_standard_input(run, monkeypatch):
    monkeypatch.setenv("ENDPOINT_URL", "https://port8000-elsewhere.invented")      # not the record's: never used
    code, out, calls, seen = run(["record", "--endpoint-id", "aiendpoint-invented", "--image", IMAGE])
    docker = docker_call(calls)
    assert code == 0 and "-i" in docker and "-e" not in docker and "--settings-stdin" in docker
    assert seen["stdin"].count("\n") == 1 and json.loads(seen["stdin"]) == {"ENDPOINT_URL": URL, **ENV}
    values = [URL, "https://port8000-elsewhere.invented", *ENV.values()]
    assert not any(v in arg for c in calls for arg in c for v in values)       # on no command line
    for program in ("docker", "nebius", "git"):        # in no child's environment (None: it would inherit them all)
        assert seen[program] is not None and not NAMES & set(seen[program])


def test_stops_when_the_endpoint_runs_another_image(run):
    other = dict(RECORD, spec=dict(RECORD["spec"], image="chambul/medisimplifier@sha256:" + "c" * 64))
    code, out, calls, seen = run(["record", "--endpoint-id", "aiendpoint-invented", "--image", IMAGE], record=other)
    assert code == 2 and "STOP: the endpoint runs" in out and docker_call(calls) is None


def test_prints_nothing_from_the_record_but_its_image(run):
    code, out, calls, seen = run(["record", "--endpoint-id", "aiendpoint-invented", "--image", IMAGE])
    assert INVENTED_KEY not in out and "invented/qwen" not in out and URL not in out
    assert not any(v in out for v in ENV.values())


@pytest.mark.parametrize("record", [
    dict(RECORD, spec=dict(RECORD["spec"], image="chambul/medisimplifier:endpoint-v7")),     # a tag, not a digest
    dict(RECORD, status=dict(RECORD["status"], public_endpoints=[])),                         # no public URL
])
def test_stops_on_a_record_without_a_digest_or_url(run, record):
    code, out, calls, seen = run(["record", "--endpoint-id", "aiendpoint-invented", "--image", IMAGE], record=record)
    assert code == 2 and "STOP:" in out and docker_call(calls) is None


def test_stops_on_a_checkout_with_changes(run):
    code, out, calls, seen = run(["record", "--endpoint-id", "aiendpoint-invented", "--image", IMAGE],
                                 changed=" M src/safety_gate.py")
    assert code == 2 and "clean git checkout" in out and docker_call(calls) is None


def test_stops_without_the_settings(run, monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    code, out, calls, seen = run(["record", "--endpoint-id", "aiendpoint-invented", "--image", IMAGE],
                                 env={"QWEN_JUDGE_MODEL": "q", "LLAMA_JUDGE_MODEL": "l"})
    assert code == 2 and "NEBIUS_API_KEY" in out and calls == []


def test_a_rehearsal_uses_a_stand_in_and_invented_settings_only(run, tmp_path):
    code, out, calls, seen = run(["rehearsal", "--url", "http://127.0.0.1:8766", "--image", IMAGE,
                                  "--checkout", str(tmp_path / "invented")])
    docker = docker_call(calls)
    assert code == 0 and not [c for c in calls if c[0] == "nebius"]
    assert after(docker, "--network") == "host" and after(docker, "--gate-src") == "/rec/src"
    assert "--rehearsal" in docker and "--settings-stdin" in docker and "-e" not in docker
    assert json.loads(seen["stdin"]) == {**rrr.INVENTED, "ENDPOINT_URL": "http://127.0.0.1:8766"}
    assert seen["docker"] is not None and not NAMES & set(seen["docker"])


def test_a_rehearsal_never_runs_against_a_deployed_endpoint(run, tmp_path):
    code, out, calls, seen = run(["rehearsal", "--url", URL, "--image", IMAGE, "--checkout", str(tmp_path)])
    assert code == 2 and "only against a stand-in on this machine" in out and docker_call(calls) is None


def test_resume_goes_through(run):
    code, out, calls, seen = run(["record", "--endpoint-id", "aiendpoint-invented", "--image", IMAGE, "--resume"])
    assert code == 0 and docker_call(calls)[-1] == "--resume"
