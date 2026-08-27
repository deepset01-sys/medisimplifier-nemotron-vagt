# MediSimplifier — Nemotron x VAGT
## Medical Text Simplification with Calibrated LLM Evaluation

Built on MediSimplifier (🥇 First Place — Nebius Serverless AI Builders Challenge).

### What's New in v2
- NVIDIA Nemotron Super as teacher model (reference simplifications)
- NVIDIA Nemotron Nano as calibrated judge (replacing Llama+Qwen)
- VAGT (Veridicality-Anchored G-Theory) — new measurement framework for LLM judge calibration
- MedSimp-JudgeBench v2 with Nemotron judges

### Built With
- Nebius Token Factory (Nemotron Super + Nano)
- Nebius Serverless Jobs (training + evaluation)
- Nebius Object Storage (adapter persistence)
- Nebius Serverless Endpoints (serving)

### Links
- Original project: github.com/deepset01-sys/medisimplifier-nebius
- JudgeBench: huggingface.co/datasets/chambul/MedSimp-JudgeBench
- VAGT framework: [see vagt_section.md in original repo]
