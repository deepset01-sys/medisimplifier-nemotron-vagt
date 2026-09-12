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

Safe Endpoint image (current: **endpoint-v5** — selector blind-spot-first fix → recommends Nemotron Nano; supersedes v4/v3):
```bash
docker pull chambul/medisimplifier:endpoint-v5
```
Digests:
- `endpoint-v5` — `sha256:0e40cff4d8db7d3b4fcfde81ccf6ace22c64feb9246e3e6c7db3876d99e50bfe`  (deploy this; selector blind-spot-first ranking → Nano)
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
# Rebuild endpoint-v5 (Dockerfile.endpoint COPYs src/ + audit_pool/ → serves /v1/audit_panel)
docker build -t chambul/medisimplifier:endpoint-v5 \
             -t cr.eu-north1.nebius.cloud/e00p4ryvm6npw9w9pz/medisimplifier:endpoint-v5 \
             -f docker/Dockerfile.endpoint .
docker push chambul/medisimplifier:endpoint-v5
docker push cr.eu-north1.nebius.cloud/e00p4ryvm6npw9w9pz/medisimplifier:endpoint-v5
```

Note: `docker/requirements_train.txt` pins `cryptography==48.0.1` via a Dockerfile post-install step — resolves the pyOpenSSL/cryptography drift that broke train-v28.

## CPU audit_panel service (always-on)

A slim, CPU-only image that serves **only** `/v1/audit_panel` + `/health` — no vLLM,
no torch, no CUDA, no gate, no simplifier. Request-time work is pure CPU over the
committed `audit_pool/` verdict files, so it needs **no API key** and no GPU. This is
the always-on demo floor (the deterministic VAGT panel selector), decoupled from the
H100 endpoint (~$1–3/day instead of ~$4/hr).

- **Image:** `chambul/medisimplifier:audit-cpu`
- **Digest:** `sha256:3df2a39ead023bc2ca79feddccd43d6988366f0197966b43ed36aa8e457cb06d`
- **Size:** 370 MB (vs ~8.8 GB for the GPU endpoint — vLLM/torch/CUDA dropped)
- **Serves:** `POST /v1/audit_panel` + `GET /health` ONLY
- **Built from:** `docker/Dockerfile.cpu` (app `src/cpu_endpoint.py`, launcher `scripts/start_cpu_endpoint.sh`)

Pull and run:
```bash
docker pull chambul/medisimplifier@sha256:3df2a39ead023bc2ca79feddccd43d6988366f0197966b43ed36aa8e457cb06d
docker run -p 8000:8000 chambul/medisimplifier:audit-cpu
```

Verify:
```bash
curl localhost:8000/health
# → {"service":"audit_panel-cpu","audit_panel":true,"pool_loaded":true,"ready":true,"pool_error":null}
```

Rebuild:
```bash
cd ~/medisimplifier-nemotron-vagt && git pull
docker build -t chambul/medisimplifier:audit-cpu -f docker/Dockerfile.cpu .
docker push chambul/medisimplifier:audit-cpu
```

## Deploy the endpoint

The Safe Endpoint runs as a Nebius AI Endpoint from `jobs/safe_endpoint_v2.yaml`. To stand it up on your own Nebius account:

**Prerequisites**
- `NEBIUS_PROJECT_ID`, `NEBIUS_SUBNET_ID` — your Nebius project and subnet.
- `HF_TOKEN` — a HuggingFace token with access to the gated base model (`aaditya/Llama3-OpenBioLLM-8B`).
- `NEBIUS_API_KEY` — used for the Token Factory judge calls (Llama-3.3-70B, Nemotron Nano).
- **The Qwen3-32B judge dedicated endpoint must be running.** The gate's Qwen verdict comes from a *separate* dedicated Nebius endpoint (`dedicated/Qwen/Qwen3-32B-…`), not Token Factory — start it before testing `/v1/simplify`, or the gate returns `ERROR` on the Qwen verdict (see README **B7**).
- An H100 quota (`gpu-h100-sxm`); vLLM cold-starts in ~10–15 min.

**Image** — public on Docker Hub, digest-pinned: `chambul/medisimplifier:endpoint-v5@sha256:0e40cff4…`. If your Nebius endpoint pulls only from your own Container Registry, mirror it first:
```bash
docker pull chambul/medisimplifier:endpoint-v5
docker tag  chambul/medisimplifier:endpoint-v5 <your-cr>/medisimplifier:endpoint-v5
docker push <your-cr>/medisimplifier:endpoint-v5
```

**Create the endpoint — Nebius Console (primary).** In the Nebius AI Endpoints console, create an endpoint with the image, preset (`gpu-h100-sxm` / `1gpu-16vcpu-200gb`), command (`/start.sh`), and the env vars above, exactly as declared in `jobs/safe_endpoint_v2.yaml`. See README **B7** for the deployment walkthrough.

**Or via CLI (secondary)** — flag-based, the same form v1 used (`jobs/safe_endpoint_v2.yaml` above is a *reference* manifest, not the Endpoint deploy form):
```bash
nebius ai endpoint create \
  --name medisimplifier-safe-endpoint-v5 \
  --public --container-port 8000 \
  --platform gpu-h100-sxm \
  --preset 1gpu-16vcpu-200gb \
  --disk-size 250Gi \
  --image chambul/medisimplifier:endpoint-v5@sha256:0e40cff4d8db7d3b4fcfde81ccf6ace22c64feb9246e3e6c7db3876d99e50bfe \
  --container-command /start.sh \
  --env HF_HOME=/tmp/hf_cache \
  --env HF_TOKEN=<your-hf-token> \
  --env NEBIUS_API_KEY=<your-nebius-api-key> \
  --subnet-id <your-subnet-id>
```
Flags verified against the live Nebius CLI (`nebius ai endpoint create --help`, eu-north1). The public Docker Hub image requires no `--registry-*` auth flags. Or use `--env-secret HF_TOKEN=<secret-selector>` if the token is stored in Nebius MysteryBox (secret store) — the production-secure form.

## Adapter Storage Flow

Training jobs write the LoRA adapter to `/output/adapter` inside the job. The job config mounts the `medisimplifier-adapters-v2` bucket to `/output`, so the adapter is automatically persisted to Object Storage. Evaluation and merge jobs mount the same bucket to `/mnt/adapters` and read the adapter from `/mnt/adapters/adapter`.

```
Training Job              Object Storage                Eval/Merge Job
/output/adapter/  ──────►  medisimplifier-adapters-v2  ◄──────  /mnt/adapters/adapter/
                           bucket (persistent)
```
