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

Safe Endpoint v2 image:
```bash
docker pull chambul/medisimplifier:endpoint-v3
```
Digest: `sha256:9d950d839497e9ee35c1676b5e75424016b52efa6827930c34f171300ae38795`

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
# Rebuild endpoint-v3
docker build -t chambul/medisimplifier:endpoint-v3 \
             -t cr.eu-north1.nebius.cloud/e00p4ryvm6npw9w9pz/medisimplifier:endpoint-v3 \
             -f docker/Dockerfile.endpoint .
docker push chambul/medisimplifier:endpoint-v3
docker push cr.eu-north1.nebius.cloud/e00p4ryvm6npw9w9pz/medisimplifier:endpoint-v3
```

Note: `docker/requirements_train.txt` pins `cryptography==48.0.1` via a Dockerfile post-install step — resolves the pyOpenSSL/cryptography drift that broke train-v28.

## Adapter Storage Flow

Training jobs write the LoRA adapter to `/output/adapter` inside the job. The job config mounts the `medisimplifier-adapters-v2` bucket to `/output`, so the adapter is automatically persisted to Object Storage. Evaluation and merge jobs mount the same bucket to `/mnt/adapters` and read the adapter from `/mnt/adapters/adapter`.

```
Training Job              Object Storage                Eval/Merge Job
/output/adapter/  ──────►  medisimplifier-adapters-v2  ◄──────  /mnt/adapters/adapter/
                           bucket (persistent)
```
