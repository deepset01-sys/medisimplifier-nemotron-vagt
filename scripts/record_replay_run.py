"""
Run scripts/record_replay.py for the replay recording on the build VM, in a one-off container of the final image,
with one image reference for everything: the endpoint's own record must name it before anything runs, the container
runs it, and the recording carries its digest.

    python3 scripts/record_replay_run.py record --endpoint-id <id> --image <repo>@sha256:<digest> --out-dir <dir>
    python3 scripts/record_replay_run.py rehearsal --url <stand-in URL> --image <repo>@sha256:<digest> \
        --checkout <invented checkout> --out-dir <dir>

Both take --resume to go on with a stopped session in the same out dir. A recording reads from the endpoint's record
(nebius ai endpoint get) only its image and its public URL, and prints neither the record nor any setting; the
checkout is this script's own repository, clean, at the commit git reports, and NEBIUS_API_KEY, QWEN_JUDGE_MODEL and
LLAMA_JUDGE_MODEL come from this environment. They and the endpoint's URL reach the container as one line on its
standard input (docker run -i; record_replay.py --settings-stdin), never as -e, so they are on no command line and in
no record Docker keeps of the container; docker, nebius and git get this environment without them. A rehearsal needs
no endpoint: it runs only against a stand-in on this machine, with the invented checkout's stand-in gate, hands the
container invented settings in place of whatever this environment holds, and its file is marked as a rehearsal. Exit
code: the container's, or 2 if it stopped before the container ran.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parents[1]
IMAGE_REF = re.compile(r"[a-z0-9][a-z0-9._/-]*@(sha256:[0-9a-f]{64})")
ENDPOINT_URL = re.compile(r"https://port8000-[a-z0-9.-]+")
SETTINGS = ("NEBIUS_API_KEY", "QWEN_JUDGE_MODEL", "LLAMA_JUDGE_MODEL")
INVENTED = {"NEBIUS_API_KEY": "invented-rehearsal-key", "QWEN_JUDGE_MODEL": "standin/qwen",
            "LLAMA_JUDGE_MODEL": "standin/llama"}


class Stop(Exception):
    pass


def say(line):
    print(line, flush=True)


def child_env():
    """This environment without the settings: what docker, nebius and git get."""
    return {k: v for k, v in os.environ.items() if k not in ("ENDPOINT_URL", *SETTINGS)}


def run(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, env=child_env(), **kw)


def endpoint_record(endpoint_id):
    """(image, URL) from the endpoint's own record; nothing else is kept, and the record is never printed."""
    r = run(["nebius", "ai", "endpoint", "get", "--id", endpoint_id, "--format", "json"], stdin=subprocess.DEVNULL)
    match = re.search(r"(?m)^[{]", r.stdout or "")
    try:
        record, _ = json.JSONDecoder().raw_decode(r.stdout[match.start():]) if match else (None, 0)
    except ValueError:
        record = None
    if r.returncode != 0 or not isinstance(record, dict):
        raise Stop(f"the endpoint's record could not be read (exit {r.returncode})")
    image = (record.get("spec") or {}).get("image")
    urls = (record.get("status") or {}).get("public_endpoints") or []
    url = next((u for u in urls if isinstance(u, str) and ENDPOINT_URL.fullmatch(u)), None)
    if not isinstance(image, str) or not IMAGE_REF.fullmatch(image) or not url:
        raise Stop("the endpoint's record names no image by digest or no public URL")
    return image, url


def clean_commit():
    """The checkout's commit, from a checkout with no change to a tracked file."""
    commit = run(["git", "-C", str(REPO), "rev-parse", "HEAD"]).stdout.strip()
    changed = run(["git", "-C", str(REPO), "status", "--porcelain", "--untracked-files=no"]).stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or changed:
        raise Stop("the checkout must be a clean git checkout of the image's commit")
    return commit


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the replay recording in a container of the final image.")
    sub = parser.add_subparsers(dest="mode", required=True)
    for mode in ("record", "rehearsal"):
        p = sub.add_parser(mode)
        p.add_argument("--image", required=True, help="the image, <repo>@sha256:<digest>")
        p.add_argument("--out-dir", required=True)
        p.add_argument("--resume", action="store_true")
        if mode == "record":
            p.add_argument("--endpoint-id", required=True)
        else:
            p.add_argument("--url", required=True, help="the stand-in endpoint's URL")
            p.add_argument("--checkout", required=True, help="the invented checkout")
    args = parser.parse_args(argv)
    try:
        ref = IMAGE_REF.fullmatch(args.image)
        if not ref:
            raise Stop("--image must be <repo>@sha256:<64 hex>")
        digest = ref.group(1)
        if args.mode == "record":
            missing = [name for name in SETTINGS if not os.environ.get(name, "").strip()]
            if missing:
                raise Stop(f"not set in this environment: {', '.join(missing)}")
            settings = {name: os.environ[name] for name in SETTINGS}
            image, url = endpoint_record(args.endpoint_id)
            if image != args.image:
                raise Stop(f"the endpoint runs {image}, not {args.image}")
            say(f"the endpoint's record names {image}: the same image")
            checkout, commit, network, extra = REPO, clean_commit(), [], []
        else:
            if urlsplit(args.url).hostname not in ("127.0.0.1", "localhost", "::1"):
                raise Stop("a rehearsal runs only against a stand-in on this machine, never a deployed endpoint")
            settings = dict(INVENTED)               # never a real key in a rehearsal
            url, checkout, commit = args.url, Path(args.checkout).resolve(), "0" * 40
            network, extra = ["--network", "host"], ["--gate-src", "/rec/src", "--rehearsal"]
        settings["ENDPOINT_URL"] = url
        out_dir = Path(args.out_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        command = (["docker", "run", "--rm", "-i", *network, "--entrypoint", "python3",
                    "-v", f"{checkout}:/rec:ro", "-v", f"{out_dir}:/out", args.image,
                    "/rec/scripts/record_replay.py", "record", "--settings-stdin", "--checkout", "/rec",
                    "--image", digest, "--commit", commit, "--out", "/out/replay_recording.json"]
                   + extra + (["--resume"] if args.resume else []))
    except Stop as e:
        say(f"STOP: {e}")
        return 2
    kind = "; rehearsal" if args.mode == "rehearsal" else ""
    say(f"container: {args.image}; --image {digest}; commit {commit}{kind}")
    line = json.dumps(settings) + "\n"              # the settings: on the container's standard input only
    return subprocess.run(command, input=line, text=True, env=child_env()).returncode


if __name__ == "__main__":
    sys.exit(main())
