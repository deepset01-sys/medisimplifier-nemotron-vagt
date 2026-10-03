"""
Check a deployed Safe Endpoint end to end: GET /health, then one POST /v1/simplify with a fixed, invented example.

    python scripts/verify_endpoint.py https://<your-endpoint-url> [--all]

Prints one PASS / WARN / FAIL line per check (INFO lines only report) and exits 0 if nothing failed, 1 otherwise.
Qwen3-32B and Nemotron Nano decide the gate's verdict, so an ERROR from either is a FAIL. Llama is advisory: its
ERROR, or a missing LLAMA_JUDGE_MODEL, is a WARN, and a FAIL with --all. A missing QWEN_JUDGE_MODEL is a FAIL and
ends the run. The endpoint does not report why a judge returned ERROR, so the script lists the likely reasons. No key
is needed here: the endpoint calls the judges itself.
"""
import argparse
import sys
import time

import requests

# Invented for this check, not taken from any dataset: a short discharge note with a diagnosis, drugs and a follow-up.
SAMPLE = ("Patient admitted with community-acquired pneumonia and treated with intravenous ceftriaxone, then oral "
          "amoxicillin. Known type 2 diabetes, continued on metformin 500 mg twice daily. Discharged home in stable "
          "condition; follow up with the primary care physician in one week.")
END_MARKERS = ("<|im_end|>", "<|im_start|>")
CONNECT_TIMEOUT = 30
# (key in the response, name, the endpoint variable that routes it, whether it decides the verdict)
JUDGES = (("qwen", "Qwen", "QWEN_JUDGE_MODEL", True),
          ("nemotron", "Nemotron", None, True),
          ("llama", "Llama", "LLAMA_JUDGE_MODEL", False))


def judge_error_reasons(variable):
    if variable:
        where = (f"its dedicated endpoint is stopped or still starting; {variable} is mistyped or names an endpoint "
                 "of another account than NEBIUS_API_KEY's")
        advice = "Check the endpoint's status in the Token Factory console, then run this script again."
    else:
        where = "NEBIUS_API_KEY is not valid for Token Factory or has no access to the model"
        advice = "Check the key and the model in Token Factory, then run this script again."
    return (f"The endpoint does not say why. Possible reasons: {where}; all three attempts (60 s each) failed; or the "
            f"reply could not be read as a verdict. {advice}")


def check_health(health, strict):
    """(level, text) lines for /health, and whether to stop before /v1/simplify."""
    if not health.get("vllm"):
        return [("FAIL", "/health: vLLM is not answering yet (loading the model can take 10-15 minutes)")], True
    if not health.get("token_factory"):
        return [("FAIL", "/health: NEBIUS_API_KEY is not set on the endpoint")], True
    lines = [("PASS", "/health: vLLM answers and NEBIUS_API_KEY is set")]
    flags = health.get("judge_models_set")
    if not isinstance(flags, dict):
        lines.append(("FAIL", "/health has no judge_models_set: the endpoint runs an image older than this code"))
        return lines, True
    if not flags.get("qwen"):
        lines.append(("FAIL", "QWEN_JUDGE_MODEL is not set on the endpoint, so the gate would use this project's own "
                              "Qwen routing key; set it to your Qwen endpoint's routing key"))
        return lines, True
    lines.append(("PASS", "QWEN_JUDGE_MODEL is set"))
    if flags.get("llama"):
        lines.append(("PASS", "LLAMA_JUDGE_MODEL is set"))
    else:
        lines.append(("FAIL" if strict else "WARN",
                      "LLAMA_JUDGE_MODEL is not set, so the gate would use this project's own Llama routing key "
                      "(Llama is advisory" + (")" if strict else "; --all makes this a failure)")))
    pool = "serving its pool" if health.get("audit_panel") else f"not available ({health.get('pool_error')})"
    lines.append(("INFO", f"/v1/audit_panel: {pool}"))
    return lines, False


def check_simplify(body, flags, strict):
    """(level, text) lines for a /v1/simplify response."""
    lines = []
    text = body.get("simplified_text")
    if not text:
        lines.append(("FAIL", "the rewrite is empty"))
    else:
        lines.append(("PASS", f"the rewrite has {len(text)} characters"))
        if any(marker in text for marker in END_MARKERS):
            lines.append(("FAIL", "the rewrite contains the end-of-answer marker, so generation did not stop there"))
    if body.get("truncated"):
        lines.append(("FAIL", "the rewrite stopped at max_tokens (truncated: true)"))
    safety = body.get("safety") or {}
    for key, name, variable, deciding in JUDGES:
        verdict = safety.get(f"{key}_verdict")
        if verdict in ("SAFE", "UNSAFE"):
            lines.append(("PASS", f"the {name} judge answered {verdict}"))
            continue
        level = "FAIL" if deciding or strict else "WARN"
        if verdict != "ERROR":
            lines.append((level, f"the response has no {name} verdict ({verdict!r})"))
            continue
        routing = ""
        if variable:
            routing = (f", although {variable} is set" if flags.get(key) else
                       f" ({variable} is not set, so the gate used this project's own routing key)")
        lines.append((level, f"the {name} judge returned ERROR{routing}. {judge_error_reasons(variable)}"))
    lines.append(("INFO", f"consensus {safety.get('consensus')}; latency {body.get('latency_ms')}"))
    return lines


def report(lines):
    for level, text in lines:
        print(f"{level:4s}  {text}")
    failed = sum(level == "FAIL" for level, _ in lines)
    warned = sum(level == "WARN" for level, _ in lines)
    print(f"verify: {'FAIL' if failed else 'PASS'} ({failed} failed, {warned} warnings)")
    return 1 if failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check a deployed Safe Endpoint end to end.")
    parser.add_argument("url", help="the endpoint's base URL, e.g. https://<host>")
    parser.add_argument("--all", action="store_true",
                        help="also require the advisory Llama judge: its ERROR or a missing variable fails")
    parser.add_argument("--timeout", type=float, default=600,
                        help="seconds to wait for /v1/simplify (default 600; a failing judge can take ~4 minutes)")
    args = parser.parse_args(argv)
    base = args.url.rstrip("/")

    try:
        r = requests.get(base + "/health", timeout=CONNECT_TIMEOUT)
        r.raise_for_status()
        health = r.json()
    except Exception as e:
        return report([("FAIL", f"/health: no usable answer ({e})")])
    lines, stop = check_health(health, args.all)
    if stop:
        return report(lines)

    t0 = time.time()
    try:
        r = requests.post(base + "/v1/simplify", json={"text": SAMPLE, "safety_mode": "flag"},
                          timeout=(CONNECT_TIMEOUT, args.timeout))
    except requests.Timeout:
        lines.append(("FAIL", f"/v1/simplify: no answer within {args.timeout:.0f} s "
                              "(a time-out on this side, not a judge verdict)"))
        return report(lines)
    except requests.RequestException as e:
        lines.append(("FAIL", f"/v1/simplify: the request failed after {time.time() - t0:.0f} s ({e})"))
        return report(lines)
    seconds = time.time() - t0
    if r.status_code != 200:
        hint = " (a proxy in front of the endpoint may have cut a long request)" if r.status_code in (502, 504) else ""
        lines.append(("FAIL", f"/v1/simplify: HTTP {r.status_code} after {seconds:.0f} s{hint}: {r.text[:300]}"))
        return report(lines)
    lines.append(("PASS", f"/v1/simplify answered in {seconds:.0f} s"))
    lines += check_simplify(r.json(), health["judge_models_set"], args.all)
    return report(lines)


if __name__ == "__main__":
    sys.exit(main())
