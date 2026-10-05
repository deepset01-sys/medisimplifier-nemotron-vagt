# Reproducibility — Container Images & Storage Flow

This document holds the full reproduction artifacts for MediSimplifier v2 — the container image digests, registry paths, rebuild commands, and the adapter storage flow between Jobs and Object Storage. These are relocated out of the main README to keep it readable; they are complete and authoritative here.

## Container Images

The v2 Jobs pipeline uses **four images**, all built from `docker/Dockerfile.train` — one per stage:

| Image | Used by | Digest (full list below) |
|--|--|--|
| `train-v29` | training (`job_train_v2.yaml`) | `sha256:bbbf6df1...` |
| `train-v30` | evaluation (`job_eval_v2.yaml`) | `sha256:6c3cd4cd...` |
| `train-v31` | merge (`job_merge_v2.yaml`) | `sha256:9d832391...` |
| `train-v32` | Nemotron-refs eval / --save-predictions (`job_eval_v2_nemotron_refs.yaml`) | `sha256:2c95dfef...` |

**Docker Hub (public):**
```bash
docker pull chambul/medisimplifier:train-v29   # training
docker pull chambul/medisimplifier:train-v30   # evaluation
docker pull chambul/medisimplifier:train-v31   # merge
docker pull chambul/medisimplifier:train-v32   # Nemotron-refs eval (--save-predictions)
```

**Nebius Container Registry (used in job configs):**

    cr.eu-north1.nebius.cloud/e00p4ryvm6npw9w9pz/medisimplifier:train-v29   (training)
    cr.eu-north1.nebius.cloud/e00p4ryvm6npw9w9pz/medisimplifier:train-v30   (evaluation)
    cr.eu-north1.nebius.cloud/e00p4ryvm6npw9w9pz/medisimplifier:train-v31   (merge)
    cr.eu-north1.nebius.cloud/e00p4ryvm6npw9w9pz/medisimplifier:train-v32   (Nemotron-refs eval)

Full digests:
- `train-v29` — `sha256:bbbf6df1b1649c6dbd3828de8156a55970b541e0e0549cf3839df7dc6dd457f5`
- `train-v30` — `sha256:6c3cd4cd99480ced3fd4dfe1977a1f4fd42e0ff18f970a5cc3fe08ca7aa70cd6`
- `train-v31` — `sha256:9d832391f85130114534a36881b8e5acab895d36ceed522126c86fbef02f728f`
- `train-v32` — `sha256:2c95dfef0a298ce258f094fa5d5647b0d7c84e297850bff8b7daba5a719694dc`

Safe Endpoint image (current: **endpoint-v6** — the published evaluation's prompt, judge routing keys from environment variables, a pinned vLLM base and model revision, and the v2 pool on `/v1/audit_panel`; supersedes v5):
```bash
docker pull chambul/medisimplifier@sha256:48265cd103c9f37fe37d9d135455573139126cb9f05991974c5c915e38caa176
```
Digests:
- `endpoint-v6` — `sha256:48265cd103c9f37fe37d9d135455573139126cb9f05991974c5c915e38caa176`  (deploy this)
- `endpoint-v5` — `sha256:0e40cff4d8db7d3b4fcfde81ccf6ace22c64feb9246e3e6c7db3876d99e50bfe`  (superseded; selector blind-spot-first ranking → Nano)
- `endpoint-v4` — `sha256:0e1d1b5abf5afb08d85dabaa5483399a8035bafbb620c11d82e01c92d17f547f`  (superseded; old selector → gemma)
- `endpoint-v3` — `sha256:9d950d839497e9ee35c1676b5e75424016b52efa6827930c34f171300ae38795`  (prior, no audit_panel)

Built from `docker/Dockerfile.train` and `docker/Dockerfile.endpoint`.
To rebuild:
```bash
cd ~/medisimplifier-nemotron-vagt && git pull
docker build -t chambul/medisimplifier:train-v31 \
             -t cr.eu-north1.nebius.cloud/e00p4ryvm6npw9w9pz/medisimplifier:train-v31 \
             -f docker/Dockerfile.train .
docker push chambul/medisimplifier:train-v31
docker push cr.eu-north1.nebius.cloud/e00p4ryvm6npw9w9pz/medisimplifier:train-v31
```

Note: train-v29 and train-v30 use the same Dockerfile.train — rebuild with the appropriate tag (e.g., train-v29 for training, train-v30 for evaluation).

```bash
# Rebuild the Safe Endpoint image (endpoint-v6) under your own name. Dockerfile.endpoint pins the vLLM base by digest
# and COPYs src/ + both pools (serves /v1/audit_panel); scripts/start_endpoint.sh pins the model revision.
git clone https://github.com/deepset01-sys/medisimplifier-nemotron-vagt.git
cd medisimplifier-nemotron-vagt
docker build -t <your-image>:endpoint-v6 -f docker/Dockerfile.endpoint .
docker login <registry-host>
docker push <your-image>:endpoint-v6
```
`<your-image>` is your repository, e.g. `docker.io/<user>/medisimplifier` or `cr.eu-north1.nebius.cloud/<registry-id>/medisimplifier`, and `<registry-host>` its host (`docker.io`, `cr.eu-north1.nebius.cloud`). Your build gets its own digest, which `docker push` prints; deploy it by that digest (**Deploy the endpoint**, step 3).

Note: `docker/requirements_train.txt` pins `cryptography==48.0.1` via a Dockerfile post-install step — resolves the pyOpenSSL/cryptography drift that broke train-v28.

## CPU audit_panel service

A slim, CPU-only image that serves **only** `/v1/audit_panel` + `/health` — no vLLM,
no torch, no CUDA, no gate, no simplifier. Request-time work is pure CPU over the
committed `audit_pool/` verdict files, so it needs **no API key** and no GPU. This is
the demo's live backend (the deterministic VAGT panel selector), decoupled from the
H100 endpoint (~$1–3/day while running, instead of ~$4/hr). Since 4808ff2 it runs as the Nebius
endpoint `medisimplifier-cpu-v2-1`, started for judging windows and stopped between them.

- **Image:** `chambul/medisimplifier:audit-cpu-v2.1` (current since 4808ff2 — built at 400ef54, after vagt_core's σ²_N estimator fix; serves the v2 hand-verified pool, `audit_pool_v2/`)
- **Digest:** `sha256:5e09e9df2d153cfe312e0af7b2bbdbde5696dfe21308effe0011a75400ac8270`
- **Earlier images:** `chambul/medisimplifier:audit-cpu-v2` @ `sha256:44cec5211cd0904d568e4f6715dcd865d5daed406c247bd32203a957d30d0d67` (v2 pool, σ²_N estimator before the fix; `results/audit_panel_live_receipt_v2.json` was captured from it) and `chambul/medisimplifier:audit-cpu` @ `sha256:3df2a39ead023bc2ca79feddccd43d6988366f0197966b43ed36aa8e457cb06d` (earlier automated pool); both superseded, kept for reproducibility
- **Pool selection:** `AUDIT_POOL_DIR` (the v2 image sets `audit_pool_v2`; run with `-e AUDIT_POOL_DIR=` to serve the earlier `audit_pool/`)
- **Serves:** `POST /v1/audit_panel` + `GET /health` ONLY
- **Built from:** `docker/Dockerfile.cpu` (app `src/cpu_endpoint.py`, launcher `scripts/start_cpu_endpoint.sh`)

Pull and run:
```bash
docker pull chambul/medisimplifier@sha256:5e09e9df2d153cfe312e0af7b2bbdbde5696dfe21308effe0011a75400ac8270
docker run -p 8000:8000 chambul/medisimplifier@sha256:5e09e9df2d153cfe312e0af7b2bbdbde5696dfe21308effe0011a75400ac8270
```

Verify:
```bash
curl localhost:8000/health
# → {"service":"audit_panel-cpu","audit_panel":true,"pool_loaded":true,"benchmark":"MedSimp-JudgeBench-v2","ready":true,"pool_error":null}
```

Rebuild:
```bash
cd ~/medisimplifier-nemotron-vagt && git pull
docker build -t chambul/medisimplifier:audit-cpu-v2.1 -f docker/Dockerfile.cpu .
docker push chambul/medisimplifier:audit-cpu-v2.1
# Deploy: Nebius Console → point the CPU service at the new digest (the deploy is not scripted in this repo)
```

## Deploy the endpoint

The Safe Endpoint runs as a Nebius AI Endpoint, created with the Nebius CLI (step 4). `jobs/safe_endpoint_v2.yaml` is a reference manifest of the same settings ("v2" in its file name is the project generation, not the image version); no step below reads it. Steps marked *not re-run by us* are written from our own setup; we did not repeat them from a new account. The commands in this section assume a bash shell (on Windows, Git Bash).

**Prerequisites**
- A Nebius AI Cloud account with billing set up, and a project in `eu-north1` with a subnet (*not re-run by us*).
- GPU quota for one H100 (`gpu-h100-sxm`) for the endpoint (*not re-run by us*).
- The Nebius CLI, installed and logged in with a profile for your project: `nebius ai endpoint create` takes the project from the profile (`--parent-id` sets another) (*not re-run by us*).
- A Token Factory API key (`NEBIUS_API_KEY`) for the three judges: your two dedicated endpoints (step 1) and serverless Nemotron Nano (`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`).
- No HuggingFace token: the endpoint loads the public `chambul/MediSimplifier-OpenBioLLM-v2-merged`, at the revision pinned in `scripts/start_endpoint.sh`.
- For step 5, a clone of this repository and Python with `requests` (`pip install -r requirements.txt`). Docker only to copy or rebuild the image.

**Cost** (Nebius list prices during this project): about $3.85/h for the endpoint's H100, $0.07/min for the Qwen3-32B judge endpoint and $0.08/min for the Llama-3.3-70B one — about $12.85/h while all three run; Nemotron Nano is billed per token. Loading the model takes 10–15 min of endpoint time. Stop all three when you are done (step 6).

**1. Create the two judge endpoints** (Token Factory console; *not re-run by us*). In the model catalog, open the model, choose **Deploy dedicated endpoint**, fill in the form as below, then **Review configuration**. Our settings:

| Judge | Base model | GPU, region | Quantization | GPUs per replica | Autoscaling |
|--|--|--|--|--|--|
| Qwen3-32B | `Qwen/Qwen3-32B` | H100 NVLink (`gpu-h100-sxm`), eu-north1 | FP8 | 1 | 1–1 |
| Llama-3.3-70B | `meta-llama/Llama-3.3-70B-Instruct` | H200 NVLink (`gpu-h200-sxm`), us-central1 | FP8 | 1 | 1–1 |

Flavor: base. The console offers the GPU types available without a reservation, which may change. Each endpoint's card shows a **routing key** (`dedicated/…`) and a separate Endpoint ID; the gate needs the routing key, which stays the same when the endpoint is stopped and started. Qwen3-32B and Nemotron Nano decide the gate's verdict. Llama-3.3-70B's verdict is advisory: it is returned with the others but does not change the consensus (README **B4**). This path sets up all three judges anyway, and step 5 checks all three. Start both (Start on each card) before step 5.

**2. Variables** for the endpoint (step 4):

| Variable | Required | Value |
|--|--|--|
| `NEBIUS_API_KEY` | yes | your Token Factory API key; the gate calls all three judges with it |
| `QWEN_JUDGE_MODEL` | yes | the routing key of your Qwen3-32B endpoint |
| `LLAMA_JUDGE_MODEL` | yes | the routing key of your Llama-3.3-70B endpoint (the advisory judge) |
| `VLLM_START_TIMEOUT` | no | seconds `/start.sh` waits for vLLM to load before it stops with an error (default 1800) |

Where `QWEN_JUDGE_MODEL` or `LLAMA_JUDGE_MODEL` is unset or empty, the gate uses this project's own routing key, which belongs to this project's account; `/health` shows which are set (`judge_models_set`, README **B3**). The image already sets `PYTHONUNBUFFERED=1` and `HF_HOME=/tmp/hf_cache`.

**3. Image** — public on Docker Hub, pinned by digest: `chambul/medisimplifier@sha256:48265cd103c9f37fe37d9d135455573139126cb9f05991974c5c915e38caa176` (`endpoint-v6`). Pulling it needs no login and no `--registry-*` flag. Only if your endpoint must pull from your own registry, copy the image there first (`<your-image>` and `<registry-host>` as in the rebuild above):
```bash
docker login <registry-host>
docker pull chambul/medisimplifier@sha256:48265cd103c9f37fe37d9d135455573139126cb9f05991974c5c915e38caa176
docker tag  chambul/medisimplifier@sha256:48265cd103c9f37fe37d9d135455573139126cb9f05991974c5c915e38caa176 <your-image>:endpoint-v6
docker push <your-image>:endpoint-v6
```
Then deploy with `--image <your-image>@<digest>`, using the digest `docker push` prints, and pass `--registry-username` and `--registry-password` (or `--registry-secret`) if your registry needs credentials. Deploying from a copy was *not re-run by us*.

**4. Create the endpoint:**
```bash
nebius ai endpoint create \
  --name medisimplifier-safe-endpoint-v6 \
  --container-port 8000 \
  --platform gpu-h100-sxm \
  --preset 1gpu-16vcpu-200gb \
  --disk-size 250Gi \
  --image chambul/medisimplifier@sha256:48265cd103c9f37fe37d9d135455573139126cb9f05991974c5c915e38caa176 \
  --container-command /start.sh \
  --env NEBIUS_API_KEY=<your-token-factory-key> \
  --env QWEN_JUDGE_MODEL=<your-qwen-routing-key> \
  --env LLAMA_JUDGE_MODEL=<your-llama-routing-key> \
  --subnet-id <your-subnet-id> \
  --timeout 30m | grep 'Endpoint created'
```
The command waits for the endpoint to be created and prints its ID; the `grep` keeps only that line. `--timeout 30m` raises the CLI's limit for a request, one minute by default (`--help`). The endpoint's settings hold the value of `NEBIUS_API_KEY` in plain text, so no command in steps 4–6 prints them. The endpoint has no authentication (the CLI's default, `--auth none`): anyone with its URL can call it, at your cost, while it runs. To keep the key out of the command, `--env-secret NEBIUS_API_KEY=<secret-selector>` reads it from Nebius MysteryBox (secret store) — the production-secure form, not exercised in our runs.

**5. Check it.** Print the endpoint's URL, the `https://port8000-…` address in its `status.public_endpoints`, and nothing else, since the full output includes the key:
```bash
nebius ai endpoint get --id <endpoint-id> --format json | grep -o 'https://port8000-[^"]*'
```
vLLM first loads the model (10–15 min); the URL answers once it is ready. Then, from your clone of this repository:
```bash
curl https://<your-endpoint-url>/health
python scripts/verify_endpoint.py https://<your-endpoint-url> --all
```
`/health` should show `"ready": true` and `"judge_models_set": {"qwen": true, "llama": true}`. The script checks `/health`, sends one `/v1/simplify` request and prints one PASS / WARN / FAIL line per check, ending in `verify: PASS (0 failed, 0 warnings)` when everything works; `--all` also requires the advisory Llama judge. A judge endpoint that does not answer can hold the request for about 4 minutes before that judge's verdict becomes `ERROR` (README **B3**).

**6. Stop** the endpoint when you are done, and both judge endpoints (Stop on each card in the Token Factory console). `stop` waits until the endpoint has stopped and then prints it, settings included, so its output is discarded:
```bash
nebius ai endpoint stop --id <endpoint-id> --timeout 15m > /dev/null
```

## Adapter Storage Flow

Training jobs write the LoRA adapter to `/output/adapter` inside the job. The job config mounts the `medisimplifier-adapters-v2` bucket to `/output`, so the adapter is automatically persisted to Object Storage. Evaluation and merge jobs mount the same bucket to `/mnt/adapters` and read the adapter from `/mnt/adapters/adapter`.

```
Training Job              Object Storage                Eval/Merge Job
/output/adapter/  ──────►  medisimplifier-adapters-v2  ◄──────  /mnt/adapters/adapter/
                           bucket (persistent)
```
