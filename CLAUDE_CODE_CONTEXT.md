# CLAUDE CODE CONTEXT — MediSimplifier v2
# Nebius x NVIDIA Global AI Hackathon
# Last updated: 2026-09-10 (Session: NEXT-SEQ Step 2 — Fable 5 regular 28/40; all critical fixes ✅ (contradictions, strict mode, κ+FK cited); student diagnosis-retention audit COMPLETE (1001/1001, flagged 52.0%); dual-auditor review COMPLETE (Claude Sonnet 5 + Gemini 2.5 Pro, 70% agreement, 2/20 confirmed drops, 6 contested); README "preserves diagnoses" claim REPLACED with measured audit result; physician adjudication PENDING; README consistency pass ✅ (billing→$225.45, project structure, What's-new rows, B-track polish); Steps 1/2/3/16/18 ✅; Fable v4 review 28/40 → ALL README fix-levers landed (cost-table Qwen, 3-judge→2-judge + advisory-Llama justified, deployed DISAGREE 34.7%, B4 decision-rule table, patient-first opening ¶1-3) ✅, billing export ⬜ (Console); **STRATEGIC PIVOT → VAGT-as-product (`/v1/audit_panel`)**; Step 6 COMPLETE ✅ — all 5×708 generated + pooled (pool=8, pending:[]); diag ΔΦ_V: Ultra 550B +0.0721 ≈ gpt-oss +0.0719 ≈ Nano 30B +0.071 (scale-flat within family; diversity-can-but-not-always; Nano wins on merit — smallest dose penalty −0.013); Step 8 COMPLETE ✅ (README ## Why VAGT section, dddbb24); Step 7 endpoint-v4 built+deployed ✅ (digest 0e1d1b5a); live smoke: /health audit_panel:true ✅, /v1/audit_panel live ✅, /v1/simplify ✅ but Qwen judge ERROR (dedicated endpoint stopped); selector maximin bug fixed (5f22863) + **endpoint-v5 BUILT + DEPLOYED + LIVE-VERIFIED ✅** (digest 0e40cff4): /health audit_panel:true, /v1/simplify gate healthy (Qwen restored), /v1/audit_panel → **Nemotron Nano, CI [0.0552,0.0866] = README receipt** (live receipts committed 82eaeeb); STEP 7 COMPLETE; README polished (all endpoint labels → v5, Why-VAGT bridge, dd9222a); Fable v6 review = **29/40 (+1 → Impact 7; audit_panel = "broadest-impact piece")**; P1 B3 /v1/audit_panel contract + /health fix (9b67e10) + Rule#2 Why-VAGT fixes (inverted blind-spot claim + false "zero errors", d6fdd08) ✅; remaining Fable v6 fixes ALL LANDED (f33ede2 What's-new audit_panel rows; e311127 project-structure audit_panel/+audit_pool/ + 2-judge intro + soften all-Nemotron; a8aae74 cost table → **$248.10** + tests/; f1fee87 Why-VAGT re-scope — pool-specific framing, no paired-CI claim, audit_panel=pre-computed); **BONUS REVIEW run: review_output_bonus_v1_fable5.txt = 29/40 (Idea 8↑7)** — Track A physician real-failure benchmark, Track B live BYO service + 2nd domain, Overall Research-Top-3-yes/Product-no, single gap = no human-anchored τ; **DIRECTION B SELECTED (2026-09-11)** — W1 app layer (two-pane UI + streaming), W2-6 physician validation + VAGT replication on real failures (MedSimp-JudgeBench-Clinical), physician brief ready to send; bonus v3-prompt run: review_output_bonus_v2_fable5.txt = **27/40** ("first-place README, not yet first-place app"; both bonus prompts triangulate on human-anchored τ); **W1 APP LAYER COMPLETE ✅** — Act 1 gate CACHED (DISAGREE, case #44) + dropped-diagnosis highlight/tooltip + auditor-confirm; Act 2 audit_panel card (ΔΦ_V chart) + **deterministic live button** (`/v1/audit_panel` via Vite proxy → same +0.0706 [0.0552,0.0866] every call); bridge "we don't trust one call, we measured it"; SAFE toggle (case #820) ends clean at ✅ banner; gate "Run it live" REMOVED (non-deterministic on borderline #44 → moved live proof to the deterministic audit_panel); Vite proxy solves browser CORS (endpoint has none); clone-and-run Vite project committed (app/, build-verified); unified physician brief shipped (0ad257a); **W2 PHYSICIAN INSTRUMENT COMPLETE ✅** — physician_review.csv (50 blinded rows, seed=42: 6 contested scattered + 44 new [20 UNSAFE/15 DISAGREE/9 SAFE], idx 44 incl. at case#39) + physician_review_KEY.csv (def028d); reproducible scripts/build_physician_review.py (byte-identical regen verified) + scripts/merge_physician_labels.py (merge + agreement + Cohen's κ + A-E counts, synthetic-tested κ=+0.82); brief SENT to 4-5 doctors, awaiting labels; NEXT = physician labels → merge_physician_labels.py → VAGT replication on human τ; parallel: entity-grounded triage pipeline (scispaCy/UMLS vs source); HEAD = def028d + scripts commit)

## WORKING METHODOLOGY
1. Always slow and methodical
2. Never fabricate results or numbers — zero tolerance
3. Show diff before committing — always
4. Commit after each meaningful step
5. Pin ALL dependencies in Docker images
6. Verify paths from actual file listing
7. Never commit without verification

---

## PROJECT

**Repo:** github.com/deepset01-sys/medisimplifier-nemotron-vagt
**Local:** C:\Users\User\Desktop\medisimplifier-nemotron-vagt\
**Deadline:** October 30, 2026
**Track:** Best Apps and Agents
**Prize:** $20,000

---

## STRATEGIC PIVOT — VAGT as Product

Key insight (from `vagt_section.md` + `vagt_estimand.md` analysis):

VAGT was conceived as a **DECISION TOOL** (panel selection, raters-vs-calibration tradeoff — the dependability ceiling Φ_V(∞); "judge choice" is a named calibration lever), **not just a measurement tool**. v2 shipped only the measurement half (one ΔΦ_V from a 2→3 rater ANOVA; the full vision was 20 raters, Bayesian probit, per-feature CAI index).

The stronger product: **`/v1/audit_panel`** — a callable Nebius-native service that tells you *which judge to add and by how much* (ΔΦ_V + CI on the panel's blindest stratum). Steps 1–5 built offline (13/13 tests; reproduces the +0.071 receipt bit-for-bit); Steps 6–8 remain.

**NEXT SEQUENCE:**
- **Step 6:** Generate verdicts for pool models (2–3 additional from Token Factory — use verified-live: DeepSeek-V4-Flash, gemma-3-27b-it, nemotron-super).
- **Step 7:** Rebuild endpoint (endpoint-v4) with `/v1/audit_panel` route live + smoke test.
- **Step 8:** README reframe (VAGT-as-product) + public receipt.

This converts VAGT from *'evidence for a decision'* into *'the decision tool itself'* — the win move both Opus reviews flagged. On-theme (Nebius-native judges), ~60% built; C-analysis verdict: the weakness is **exposure, not the research**. Scope Steps 6–8 tightly (3 verified pool models, one reproducible receipt) to avoid creep.

**STEP 6 STATUS — COMPLETE ✅ (2026-09-09):** `gen_pool_verdicts.py` (fa78088) generated all 5 candidates' 708-row verdicts; each PASSED `vagt_core` (incumbent diag ΔΦ_V reproduced 0.0706, row_id aligned) and moved pending→pooled. **Pool = 8 members** (incumbents Llama/Qwen/Nemotron-Nano + gemma/gpt-oss/super/DeepSeek/Ultra); `pending: []`.

Diagnosis ΔΦ_V — each candidate added to the Llama+Qwen incumbent (vs the +0.071 Nemotron-Nano reference):

| Candidate | Size | diag ΔΦ_V | dose ΔΦ_V | ERR | commit |
|--|--|--|--|--|--|
| Nemotron Nano (ref) | 30B | +0.071 | −0.013 | ~0 | (incumbent) |
| Nemotron-3-Ultra | 550B | +0.0721 | −0.032 | 0 | 28300cd |
| gpt-oss-120b | 120B | +0.0719 | −0.030 | 0 | 9924297 |
| nemotron-super | 120B | +0.0653 | −0.059 | 3 | cc975de |
| DeepSeek-V4-Flash-0731 | — | +0.0597 | −0.032 | 12* | 04afe6b |
| gemma-3-27b-it | 27B | +0.0017 | +0.038 | 0 | 37f600f |

*DeepSeek: 55→12 ERR after one resume (43 transient cleared; 12 residual ~truncation, complete-case-dropped).

**FINDINGS:** (1) **Scale-flat within family** — 30B Nano (+0.071) ≈ 550B Ultra (+0.0721) over an 18× size range → shared bias doesn't shrink with scale (the VAGT thesis, measured). (2) **Diversity CAN break the blind spot but isn't sufficient** — gpt-oss (diverse family) ties the Nemotrons; gemma (diverse) fails (+0.0017). (3) **On-merit recommendation = Nemotron Nano** — tied-best diagnosis fix, **smallest dose penalty** (−0.013 vs −0.032/−0.030/−0.059), smallest/cheapest/fastest, most reliable (0 err). The audit_panel recommends the 30B NVIDIA model over a 550B sibling + a 120B OpenAI rival — by the numbers, not the theme. Honest nuance: my "smaller is better" prior was too strong; the true result is "flat across scale" (+0.0721 vs +0.071 is noise).

**STEP 8 — COMPLETE ✅ (dddbb24):** README `## Why VAGT — the panel selection finding` inserted after the opening — decision-tool framing + 6-row pool table (Family/Size/diag ΔΦ_V/dose ΔΦ_V) + 3 findings (scale-flat / diversity-can-but-not-always / Nano-on-merit) + `/v1/audit_panel` pointer (→ #b3-api-contract).

**STEP 7 — CODE/CONFIG COMPLETE ✅ (5b2e711); BUILD+DEPLOY PENDING (your side):** `router.py` was already mounted in safe_endpoint.py; the gap was packaging — the old Dockerfile copied neither `src/audit_panel/` nor `audit_pool/`, so the route silently 404'd. Fixed: `Dockerfile.endpoint` now `COPY src/ ./src/` + `COPY audit_pool/ ./audit_pool/` (structure-preserving), and `start_endpoint.sh` runs from `cd /app/src` — so `pool_loader._HERE.parents[1]/"audit_pool"` resolves to `/app/audit_pool` and `safe_endpoint`'s `sys.path.insert(…/"audit_panel")` resolves to `/app/src/audit_panel` (both traced). No `.py`/pip changes (numpy in vLLM base; pool_loader reads JSON only, no PyYAML). REMAINING (your side): (1) 🔴 rotate NEBIUS_API_KEY; (2) `docker build -f docker/Dockerfile.endpoint` → endpoint-v4, dual-tag Docker Hub + Nebius CR; (3) redeploy Nebius GPU Endpoint w/ fresh key; (4) live smoke: `GET /health` → `"audit_panel": true`; `POST /v1/audit_panel` {incumbent [Llama,Qwen] + 8-model pool} → recommendation + ΔΦ_V + CI, capture to results/.

**STEP 7 — endpoint-v4 BUILT + DEPLOYED ✅:** built on VM ubuntu@195.242.28.221 (git pull → d7dac0d ⊇ 5b2e711; `COPY src/` + `COPY audit_pool/` confirmed), dual-pushed CR + Docker Hub, **digest `sha256:0e1d1b5abf5afb08d85dabaa5483399a8035bafbb620c11d82e01c92d17f547f`** (safe_endpoint_v2.yaml → v4 @ 5da315f; CCC/REPRODUCIBILITY @ acc519d). Live smoke (via python requests — Windows curl schannel TLS fails on the tunnel URL): `/health` → `{"audit_panel": true, "ready": true}` ✅; `/v1/simplify` → 200, simplification OK BUT **qwen_verdict=ERROR → consensus=ERROR** (dedicated Qwen3-32B endpoint STOPPED / key); `/v1/audit_panel` → 200 (route live; note candidate_pool must be an explicit list, "all" → 422).

**SELECTOR MAXIMIN BUG — FOUND via live smoke, FIXED (5f22863):** the live `/v1/audit_panel` recommended **gemma** (+0.0017 on diagnosis!) — contradicting the README's "recommend Nemotron Nano". Root cause: selector ranked by `worst_stratum_delta_Phi_V = min(per_phi.values())` (maximin/do-no-harm) → gemma is the only candidate that never regresses a stratum, but it barely fixes the blind spot. The diagnosis-fixers (Nano/gpt-oss/Ultra +0.071) all hurt dose slightly → lost under maximin. Fix (user chose Option B): rank by **blindest-stratum ΔΦ_V banded to TIE_BAND=0.01** (statistical tie), tie-break on **least collateral** (highest min ΔΦ_V on other strata) → **Nemotron Nano** (0.0706, CI [0.0552,0.0866] = the receipt, gemma ranked LAST). Verified offline + 14/14 tests (incl. new `test_full_pool_recommends_nemotron_not_gemma` regression lock; test pool 3→8 models). NOTE: the DEPLOYED endpoint-v4 still has the OLD selector → **needs endpoint-v5 rebuild** for the live route to recommend Nano.

**STEP 7 — COMPLETE ✅ (endpoint-v5 LIVE-VERIFIED):** rebuilt on VM (git pull → 7b2c96d, TIE_BAND gate passed), dual-pushed, **digest `sha256:0e40cff4d8db7d3b4fcfde81ccf6ace22c64feb9246e3e6c7db3876d99e50bfe`** (YAML + CCC/REPRODUCIBILITY @ 362cbd8), redeployed (Qwen dedicated endpoint restarted + key rotated by user). Live smoke on the v5 tunnel (port8000-vjbksde9vzhgtcx…): `/health` → audit_panel:true ✅; `/v1/simplify` → gate HEALTHY, qwen=SAFE now (was ERROR on v4) ✅; `/v1/audit_panel` (explicit 8-model pool) → **recommends Nemotron Nano, expected_Phi_V_lift 0.0706, CI [0.0552, 0.0866] = the published receipt**, ranked Nano>gpt-oss>Ultra>super>DeepSeek>gemma (gemma LAST) ✅ — bit-for-bit matches README + 14/14 tests. Receipts committed (82eaeeb): results/audit_panel_live_receipt.json (deterministic) + results/endpoint_v5_smoke_test.json (SAFE this call — Nemotron verdict non-deterministic on borderline inputs, honestly noted; a live DISAGREE was seen once but did NOT reproduce → not captured as a claim, per the idx-21 lesson). README: Why-VAGT cites the live receipt; B2 URL → v5. (Cosmetic debt: B2 prose still says "Safe Endpoint v2"; YAML `name:` still `-v4`.)

NEXT = re-run bonus review with new single-thesis prompt (review_prompt_bonus_v3.txt); strategic direction A/B/C undecided.

---

## SESSION August 30 – September 3, 2026 — review fixes, VAGT CIs, reframe, 4.8 reviews, DISAGREE capture, audit_panel Steps 1-5, Fable 5 (v1+v2), Qwen removal + gate swap (HEAD = a83bfb8)

```
591428a - Training log committed + .gitignore whitelist
6313d2a - Per-stage image tags corrected (v29/v30/v31) + excerpt
61ee5bf - Endpoint reframe (~27s) + smoke-test + models_verified
29c745d - VAGT origin framing reconciled
18cf994 - README polish (blog removed, FK-Grade, σ²_B trim, safety_mode)
c239d3c - Fix #3 scaffolding (job + scripts + evaluate.py --save-predictions)
70318dc - Pin eval-nemotron job to train-v32
fd36ae2 - Nemotron-reference eval companion table + results artifact
a76f426 - Model-recommendation callout [v4 fix #2]
cbd32ad - max_tokens=16000 engineering-finding callout [v4 fix #3]
c2cc0a4 - Real live-endpoint SAFE curl + gate-level UNSAFE trace [v4 fix #1]
23c1afe - CLAUDE_CODE_CONTEXT refresh (Fix #3 complete, v4 review, corrected denominators)
88085fe - paired bootstrap CIs on VAGT deltas (ΔΦ_V +0.071 [+0.055,+0.087] on diagnosis)
1a4f52c - "The finding" lead paragraph (VAGT inversion first) [v5 fix]
bfa7240 - CLAUDE_CODE_CONTEXT refresh (prior — recorded HEAD 1a4f52c, v5 review + /v1/audit_panel decision)
957fcdf - README line 11: VAGT framed as direct response to v1 κ=0.11 finding [4.8 fix]
f20cd2e - Nemotron-refs eval trail documented (job + train-v32 + run id + full digest) [4.8 fix]
6debd43 - Project Structure: all committed results/ artifacts + vagt_bootstrap_cis.json [4.8 fix]
87d719c - Endpoint cold-start wake note + digest table '(full list below)' pointer [4.8 fix]
76710f9 - CLAUDE_CODE_CONTEXT refresh (prior — recorded HEAD 87d719c, 4.8 reviews + DISAGREE spec)
9fe9fa3 - DISAGREE gate-level worked example — idx 146 (Parkinson+depression) splits panel live + capture JSON + script
4f8688a - audit_panel Step 1: vagt_core.py (generalized, bit-identical to README) + regression tests (4/4)
72b9dd7 - audit_panel Step 2: audit_pool data (ground_truth + 3 verdicts); lossless reshape (diag ΔΦ_V=0.0706 ✓)
fa1000d - audit_panel Step 3: pool_loader + selector (reproduces receipt) — 9/9 tests
8c20382 - audit_panel Step 4: schemas + router + mount; /v1/audit_panel live — 13/13 tests
cd97aa1 - audit_pool/candidates.yaml (Step 5) + CCC refresh (recorded HEAD 8c20382)
a6c04c4 - README line 143: disambiguate JudgeBench-ref run (~$1.7) vs full training run ($75.19) [4.8 v4]
f423b99 - README: +0.072→+0.071 consistency (A) + "hallucinated"→"omitted" (B) [Fable 5]
ca0bfba - billing → $134.81 total / 10.22 GPU hrs (README + CCC sweep) [Fable 5 Fix C]
a72cfc8 - README Project Structure: + logs/train_v2.json.gz + results/disagree_case_gate.json [Fable 5]
d707bc4 - README: judge-params table + 4-bit NF4 QLoRA + epoch-2 best-checkpoint disclosure [Fable 5]
b2d37e3 - README: DISAGREE rate 203/708 (28.7%) + calibration caveat [Fable 5]
9afd50b - README: "proving"→"demonstrating on MedSimp-JudgeBench" (lines 17+47) [Fable 5]
fec2193 - README: patient-facing value prop before "The finding" [Fable 5]
973b0e7 - CLAUDE_CODE_CONTEXT refresh (recorded HEAD fec2193, Fable 5 v1 + 7 fixes)
8ec5e73 - fix: Qwen judge → Qwen3-30B-A3B-Instruct-2507 (Qwen3-32B removed from Token Factory)
a83bfb8 - docs: README honest note on Qwen3-32B removal; gate updated
7c6721a - CLAUDE_CODE_CONTEXT refresh (recorded HEAD a83bfb8, Fable 5 v2 27/40, Qwen removal saga)
8eff2f9 - CLAUDE_CODE_CONTEXT — Fable 5 v2 deep read + MASTER ACTION LIST + endpoint forensics (no code change)
1a9f72c - fix #5+#15: README cost share 93%→57% + accurate hosting (line 346)
6e916f2 - fix #6: README training cost ~$25-30 → ~$9 (line 103)
cf3e45f - fix #8: README Krippendorff α values printed 0.077→−0.086 (line 245)
ad0b508 - fix #9: README FK measured 7.2 (Claude) / 10.1 (Nemotron) refs, Δ+2.9 (line 105)
9cb472a - fix #11: README δ 1.6–5.0% defined as ROUGE-L H200→H100 reproduction delta + cited v1 (line 53)
58ab53c - fix #15: README endpoint framing — persistent GPU Endpoint, not serverless/scales-to-zero (lines 17/314/399)
fc88332 - fix #17: README remove unused "Ultra" from Token Factory model list (line 147)
2ce4086 - fix #14 + #15 straggler: reframe "deploy v1" → "what the endpoint serves" (line 107); Serverless→GPU Endpoint (line 159)
7e3f088 - restructure BEGIN: opening block → Fable §6 3 paragraphs (8th-grade, full CIs, Track A/B nav) + line-25 reading-level fix [#18 ✅, #16 partial]
e8a8e31 - restructure: remove "## Key findings" table + orphaned footnote (redundant with opening ¶2; overclaims gone) [#16 ✅]
5ba67bf - README: Track A/B skeleton + "Choose your track" nav (opening ¶3 forward-ref now resolves) [#13 Step 1/4]
5494437 - README: relocate LoRA Configuration → B6 (Model card) [#13 Step 2a]
f6491b7 - README: relocate Merge & Deploy (v2) → B7 (Deployment on Nebius) [#13 Step 2b]
36e7814 - README: relocate Container Images + Adapter Storage Flow → docs/REPRODUCIBILITY.md (new overflow file) [#13 Step 2c]
9567320 - README: merge Public Artifacts into Dataset and models table (+License column) [#13 Step 2d]
ab3f1f2 - README: split Medical Safety Evaluation → A3/A5/B4/B5/B8 [#13 Step 3a]
c5ebee7 - README: split Reproduce step by step → A9 (analysis) / B9 (deployment) [#13 Step 3b]
e731fe9 - README: split VAGT → A4 (measurement + coding + σ²_τ) / A6 (results II + variance ledger + ΔFleiss/Kripp + reframe) [#13 Step 4 · A4/A6]
eb37de6 - README: A7 (relocate Nemotron-as-Teacher + v2 Eval Results) + B6 model-card blockquotes [#13 Step 4 · A7]
8908a19 - README: A8 Threats to validity (8 threats, research-side) [#13 Step 4 · A8]
f7f8472 - README: B3 API contract (#26 block-mode DISAGREE, /health, error semantics) + trim parked 318 from B5 [#13 Step 4 · B3]
ab42383 - README: A1 Question & estimand (research Q, estimand-in-words, falsifiable prediction) + absorb provenance note from A6 [#13 Step 4 · A1]
fbad377 - README: A2 Benchmark MedSimp-JudgeBench (708 items, per-type counts, silent-drop definition, provenance) [#13 Step 4 · A2]
b371cda - README: B1 What ships (user story, pipeline diagram, what-it's-not) [#13 Step 4 · B1]
c3b2e35 - README: B2 Quickstart (Path 1 endpoint + Path 2 gate-only, second product use case) [#13 Step 4 · B2 — LAST empty stub; all A/B stubs now populated]
0234bb7 - README: drop "Under construction" note (all A/B stubs now populated) [#13 cleanup]
b391f85 - README: B8 items 2-3 (prompt drift + DISAGREE defense-in-depth) [#13 finishing touches]
0eabe6f - README: B5 user-facing translation (2-judge miss rate ~34%, diagnosis ~75%) [#13 finishing touches]
de79fa7 - README: dissolve ## How it runs on Nebius (Why-Token-Factory + adapter pointer → B7; drop stale serverless line) [#13 finishing touches]
bb85afb - README: rewrite ## What this project does (deliverables inventory, confident tone) [tone-polish]
5d166b5 - README: neutralize A7 defensive labels (Honest/real-finding → plain) [tone-polish]
d0fc620 - CLAUDE_CODE_CONTEXT refresh (README tone-polish complete, recorded HEAD 5d166b5)
3afc059 - fix: safety_gate.py — revert Qwen to Qwen3-32B via dedicated Nebius endpoint (not Token Factory); bump Qwen max_tokens 2000→8000
f5cb9d4 - results: gate_calibration_full.json — 708/708, 0 ERRORs, Qwen3-32B dedicated endpoint; DISAGREE 147/708 (20.8%) under gate prompt
5cd7b5a - README: B5 deployed gate operating characteristics (gate prompt, n=708, 0 ERRORs); B4 Qwen FP caveat
2d721d4 - README: B8 item 1 Qwen swap RESOLVED (Qwen3-32B restored via dedicated endpoint, 708-item calibration complete)
d3b6779 - README: A3 judge-params table (Qwen 2000→8000, off→off*, footnote updated) [#7 un-defer]
4bfbff8 - feat: add run_gate_calibration.py — 708-item gate calibration script
47880b9 - results: archive invalid gate calibration (146 Qwen ERRORs from Qwen3-32B removal mid-run)
7ae0b42 - docs: update billing to $156.82 (dedicated endpoint + Qwen3-32B gate calibration rows; TF % 57→63; serverless framing)
9413b20 - docs: README fix 6 contradictions (Qwen routing, budget-confound reframe [calibration=8000, false premise], cost $0.90→$1.63, gate operating point → B5, gate_calibration_full.json citation)
f4b0327 - docs: README fix stray #26, 9976→7983, FK-Grade precise, dedup what's-new, ¶2 plain-English hook
21fe0fd - feat: safety_gate.py strict mode (DISAGREE blocks) + document all three modes
716a4c6 - feat: B3 strict mode docs + safe_endpoint.py Literal["flag","block","strict"] validation
5c0de4d - feat: cite κ (A5→nemotron_calibration_full.json) + FK 10.1/7.2 (A7→reference_fk_grade.json artifact + measure_reference_fk.py)
7496866 - results: student_audit.json complete (1001/1001, SAFE 47.4%, flagged 52.0%) + audit scripts
0322d01 - dual-auditor review complete (Claude Sonnet 5 + Gemini 2.5 Pro, 70% agreement, 2/20 confirmed drops)
d7ba1f1 - adjudication brief + human_judgment fields for 6 contested
25de8bb - README: replace "preserves diagnoses" with measured audit result
5a5fd6c - CLAUDE_CODE_CONTEXT refresh (dual-auditor complete; README claim updated; recorded HEAD 25de8bb)
cebe56a - README A3 Qwen note: remove stale "replacement model"
b844bc5 - README B1: add validation pipeline
169aea3 - README B7: add Qwen3-32B dedicated endpoint note
50c6fa9 - README B8 item 1: trim to one line
9ace9fb - README billing: $225.45 (dedicated endpoint 21.95 GPU-hr $88.90; Nano/Llama updated)
9a106e7 - README project structure: add new src/results/docs artifacts + safety_gate.py desc fix
639b185 - README What's-new: gate chars + audit + strict-mode rows; Safe Endpoint desc
c41dddf - README opening ¶4: add student self-audit result (2/20 confirmed drops)
bcd7489 - README: fix cost table Qwen contradiction; 3-judge→2-judge (advisory Llama); patient-first ¶1
8f25cfc - README: deployed DISAGREE false-alarm 34.7% (51/147) in B3/B5 (replace stale "unmeasured")
477c13e - README B4: decision-rule comparison table (5 strategies, 708 items)
b0374b7 - README opening ¶2 (3-bullet what's-new) + ¶3 (30-sec try-it + two tracks)
fa78088 - feat: gen_pool_verdicts.py + candidates.yaml (4 smoke-validated candidates)
ac97253 - feat: DeepSeek smoke-validated (16k)
2d8094e - docs: CCC — Step 6 in progress (5 smoke-validated; gemma 708 PASS)
37f600f - results: audit_panel gemma-3-27b-it 708 (diag ΔΦ_V +0.0017); pending→pooled
9924297 - results: audit_panel gpt-oss-120b 708 (diag ΔΦ_V +0.0719 ≈ Nano); pending→pooled
cc975de - results: audit_panel nemotron-super 708 (diag ΔΦ_V +0.0653 < Nano at 4×); pending→pooled
04afe6b - results: audit_panel DeepSeek-V4-Flash-0731 708 (diag ΔΦ_V +0.0597; resume 55→12 ERR); pending→pooled
28300cd - results: audit_panel Nemotron-3-Ultra 708 (diag ΔΦ_V +0.0721; scale-flat); Step 6 pool COMPLETE (8)
dfb1add - docs: CCC — Step 6 COMPLETE (pool=8; full ΔΦ_V table); NEXT Step 7+8
dddbb24 - README: ## Why VAGT panel selection finding (pool results table, 3 findings) [Step 8]
5b2e711 - feat: endpoint-v4 packaging (COPY src/ + audit_pool/; cd /app/src) [Step 7 code]
5da315f - feat: safe_endpoint_v2.yaml → v4 + endpoint-v4 digest (0e1d1b5a); README project-structure line
acc519d - docs: endpoint-v4 digest → CCC image table + REPRODUCIBILITY
5f22863 - fix: selector.py blind-spot-first ranking + TIE_BAND (maximin→gemma bug → Nemotron Nano; 14/14 tests)
7b2c96d - docs: CCC — endpoint-v4 deployed + selector bug fixed; NEXT endpoint-v5
362cbd8 - feat: safe_endpoint_v2.yaml → endpoint-v5 + digest (0e40cff4); CCC/REPRODUCIBILITY
82eaeeb - results: audit_panel live receipt (Nano, CI [0.0552,0.0866]) + endpoint-v5 smoke (SAFE); README → v5 URL + receipt link
3d5d474 - docs: CCC — Step 7 COMPLETE (endpoint-v5 live-verified: Nano recommended)
dd9222a - docs: README polish — endpoint labels v2/v3/v4 → v5 (10 sites); Why-VAGT bridge sentence
9b67e10 - docs: README B3 — /v1/audit_panel contract + /health audit_panel:true + safety_mode strict
d6fdd08 - docs: README Why-VAGT — fix inverted "family shares blind spot" + drop false "zero errors" for Nano
d5766fd - docs: CCC — Fable v6 = 29/40 (+1 Impact; audit_panel broadest-impact); P1 + Rule#2 fixes logged
f33ede2 - README: What's-new table — /v1/audit_panel + judge-pool experiment rows
e311127 - README: project structure + audit_panel/ + audit_pool/; 2-judge intro; soften all-Nemotron → Nemotron teacher+judge
a8aae74 - README: cost table → $248.10 (pool runs + exact Console figures); + tests/
f1fee87 - README: Why-VAGT re-scope (pool-specific framing; no paired-CI claim; audit_panel = pre-computed)
0ad257a - docs: physician brief unified (ADJUDICATION_BRIEF.md → 50 cases, 5 categories = VAGT strata, spreadsheet recording)
7579423 - feat: W1 app layer — demo.jsx (Index 44 hero case, DISAGREE gate, SAFE toggle, landing hook) + package.json/vite.config
82b2d8d - feat: app layer — full Vite clone-and-run files (index.html, src/main.jsx, src/index.css, README, .gitignore); build-verified
a9e5c8f - docs: CCC — W1 app layer COMPLETE (demo committed, clone-and-run verified); HEAD 82b2d8d
f225a76 - feat: app layer — Act 2 audit_panel card + deterministic live button; bridge sentence; gate cached; SAFE case clean
8d007a3 - docs: CCC — W1 COMPLETE (Act 1 cached + Act 2 audit_panel deterministic live); HEAD f225a76
def028d - results: physician_review.csv (50 cases, blinded, seed=42) + KEY for de-blinding; brief sent to 4-5 doctors
<this commit> - scripts: build_physician_review.py + merge_physician_labels.py; W2 physician instrument complete
```

### FIX #3 STATUS — COMPLETE ✅
- train-v32 built + pushed: sha256:2c95dfef0a29... (includes evaluate.py --save-predictions)
- Eval job ran → predictions.json written to bucket eval_v2_nemotron/
- Scored vs Nemotron refs with train-v32 libraries (version-consistent):
  ROUGE-L 0.601 / BERTScore 0.9321 / SARI 64.18 (n=998; 3 errored Nemotron refs skipped)
- results/eval_v2_nemotron_results.json + README companion table committed (fd36ae2)

### ENDPOINT
- URL: https://port8000-qzv93v671z09ej5.tunnel.applications.eu-north1.nebius.cloud
- Latency: ~27s (3-judge Token Factory gate; corrected from ~73s)
- Live Nebius serverless endpoint — permanent URL, scales to zero, wakes on request (~27s cold start)
- Real SAFE call + response in README (Reproduce) and results/endpoint_smoke_test.json

### SECURITY — URGENT
Rotate Nebius API key + HF token (both exposed in transcripts). Endpoint uses NEBIUS_API_KEY →
rotate, then redeploy endpoint with the new key so the live URL keeps working.

---

## KEY NUMBERS (ALL VERIFIED)

| Metric | Value | Source |
|--------|-------|--------|
| ROUGE-L v2 | 0.5254 | results/eval_v2_results.json |
| SARI v2 | 60.36 | results/eval_v2_results.json |
| BERTScore v2 | 0.9113 | results/eval_v2_results.json |
| FK-Grade v2 | 8.87 | results/eval_v2_results.json |
| FK-Grade v1 | 7.33 | v1 repo |
| ROUGE-L v2 vs Nemotron refs | 0.6010 | results/eval_v2_nemotron_results.json |
| BERTScore v2 vs Nemotron refs | 0.9321 | results/eval_v2_nemotron_results.json |
| SARI v2 vs Nemotron refs | 64.18 | results/eval_v2_nemotron_results.json |
| Teacher ROUGE-L | 0.525 | teacher_comparison.json |
| n_samples eval | 1,001 | results/eval_v2_results.json |
| Training samples | 7,983 | chambul/medisimplifier-nemotron-dataset |
| Training time | 8,523s (~2.4h) | logs/train_v2.json.gz (train_runtime) |
| Total cost v2 | $225.45 | Nebius Console actual billing (incl. dedicated endpoint 21.95 GPU-hr + gate calibration) |
| H100 hours | 10.22 | Nebius Console |
| Nemotron Super cost | $75.19 | Nebius Console Token Factory |
| Nemotron Nano cost | $2.17 | Nebius Console Token Factory (calibration + 1,001-item student audit) |

---

## DIAGNOSIS RECALL NUMBERS — RECONCILIATION

Three numbers appear in README — all correct, different denominators (see README footnote in Medical Safety Evaluation):
- **84.2%** = Nemotron overall recall across all 4 error types (421 of 500 non-ERROR corrupted; 508 corrupted total)
- **68%** = Nemotron recall on the diagnosis-corrupted subset (100 of 147 non-ERROR; 150 diagnosis-corrupted total)
- **47%** = Nemotron UNSAFE rate on the VAGT diagnosis stratum (complete-case n=333, ~41% corrupted) — NOT the all-708 rate (which is 69.4%)

Sources: nemotron_calibration_full.json (recall) + vagt_nemotron_results.txt (47% stratum rate)

---

## VAGT RESULTS (from vagt_nemotron_results.txt; paired-Δ 95% CIs committed in vagt_bootstrap_cis.json, 88085fe)

| Feature | Φ_V (L+Q) | Φ_V (+Nemo) | ΔΦ_V | σ²_B (L+Q) | σ²_B (+Nemo) | Δσ²_B |
|---------|-----------|-------------|------|------------|--------------|-------|
| dose | 0.743 | 0.733 | −0.013 [−0.055, +0.021] (n.s.) | 0.054 | 0.047 | −0.007 |
| negation | 0.578 | 0.618 | +0.043 [+0.011, +0.070] | 0.145 | 0.104 | −0.041 |
| lateral | 0.697 | 0.745 | +0.048 [+0.019, +0.074] | 0.077 | 0.050 | −0.027 |
| diagnosis | 0.404 | 0.476 | +0.071 [+0.055, +0.087] | 0.347 | 0.229 | −0.115 [−0.141, −0.090] |

ΔΦ_V column = paired bootstrap (3-rater − 2-rater on same complete-case items, 1000 iters, seed=42), 95% CI.
Fleiss κ on diagnosis: 0.076 → −0.088 (Krippendorff α ≈ same); paired ΔFleiss κ = −0.163 [−0.305, −0.045] (CI excludes 0).
Diagnosis inversion is significant on both axes (Φ_V up, κ down, CIs exclude 0); dose is the lone dip and is n.s.

---

## NEMOTRON CALIBRATION (from nemotron_calibration_full.json, n=708)

| Judge | Recall | FP Rate | Balanced Acc |
|-------|--------|---------|--------------|
| Nemotron Nano | 84.2% | 35.2% | 74.5% |
| Llama-3.3-70B | 31.7% | 1.5% | 65.1% |
| Qwen3-32B | 55.9% | 0.5% | 77.7% |

Nemotron diagnosis recall: 68% vs Llama 14% / Qwen 7%
Verdict distribution (n=708): 208 SAFE / 491 UNSAFE / 9 ERROR = 69.4% UNSAFE rate

---

## INFRASTRUCTURE

```
Project ID: project-e00g1ev2pr00wjxv40r6ga
Subnet ID: vpcsubnet-e00jsdqfjrz04ygxc0
Bucket v2: medisimplifier-adapters-v2
  adapter/              → v2 LoRA adapter
  merged_openbio_v2/    → merged model
  eval_v2/              → evaluation results (Claude refs)
  eval_v2_nemotron/     → predictions.json + results.json (Fix #3 run)
CR path: cr.eu-north1.nebius.cloud/e00p4ryvm6npw9w9pz/medisimplifier:<tag>
Build host: VM ubuntu@195.242.30.65 (nebius_vm key); has nebius CLI + boto3 + ~/.aws/credentials
```

---

## DOCKER IMAGES

| Tag | Digest | Purpose |
|-----|--------|---------|
| train-v29 | sha256:bbbf6df1... | training only |
| train-v30 | sha256:6c3cd4cd... | evaluation (OLD, pre --save-predictions) |
| train-v31 | sha256:9d832391... | merge only |
| train-v32 | sha256:2c95dfef0a298ce258f094fa5d5647b0d7c84e297850bff8b7daba5a719694dc | evaluation with --save-predictions |
| endpoint-v3 | sha256:9d950d83... | Safe Endpoint v2 (no audit_panel) |
| endpoint-v4 | sha256:0e1d1b5abf5afb08d85dabaa5483399a8035bafbb620c11d82e01c92d17f547f | Safe Endpoint v4 (+ /v1/audit_panel) — SUPERSEDED (old selector → gemma) |
| endpoint-v5 | sha256:0e40cff4d8db7d3b4fcfde81ccf6ace22c64feb9246e3e6c7db3876d99e50bfe | Safe Endpoint v5 — selector blind-spot-first fix → Nano; **DEPLOY THIS** (safe_endpoint_v2.yaml) |

**Critical:** cryptography==48.0.1 pinned via post-install step in Dockerfile.train
**Build method:** manual `docker build` dual-tagged to Docker Hub + Nebius CR, tag bumped per version (build_and_push.sh is STALE — hardcodes v28, Docker-Hub only). CR login: `nebius iam get-access-token | docker login cr.eu-north1.nebius.cloud --username iam --password-stdin`.

---

## MODELS

| Model | String | Purpose |
|-------|--------|---------|
| Nemotron Super | nvidia/nemotron-3-super-120b-a12b | Teacher |
| Nemotron Nano | nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B | Safety judge |
| Llama | meta-llama/Llama-3.3-70B-Instruct | Safety judge |
| Qwen | Qwen/Qwen3-32B (calibration; deployed gate now Qwen/Qwen3-30B-A3B-Instruct-2507 — 32B removed from TF) | Safety judge |
| Base model | aaditya/Llama3-OpenBioLLM-8B | Student (gated — requires HF access) |
| Token Factory base URL | https://api.studio.nebius.ai/v1/ | |

Model strings verified live via /v1/models → results/models_verified.json (31 models; both nvidia strings present).

---

## SAFE ENDPOINT v2 DECISION RULE (safety_gate.py)

```python
if nemotron=="SAFE" and qwen=="SAFE": → SAFE
if nemotron=="UNSAFE" and qwen=="UNSAFE": → UNSAFE
if qwen=="UNSAFE": → UNSAFE  # trust 0.5% FP specificity
if nemotron=="UNSAFE" and qwen=="SAFE": → DISAGREE + "diagnosis-drop risk"
elif "ERROR" in (nemotron, qwen): → ERROR  # fail-safe
# Parallel: ThreadPoolExecutor(max_workers=3), ~27s total
```

---

## HUGGINGFACE

| Resource | Identifier |
|----------|-----------|
| Training dataset | chambul/medisimplifier-nemotron-dataset |
| Merged model v2 | chambul/MediSimplifier-OpenBioLLM-v2-merged |
| JudgeBench | chambul/MedSimp-JudgeBench |
| Source dataset | GuyDor007/medisimplifier-dataset |
| v1 merged model | chambul/MediSimplifier-OpenBioLLM-merged |
| v1 adapter | chambul/MediSimplifier-LoRA-Adapter-Nebius |

---

## NEBIUS BILLING (ACTUAL)

| Resource | Usage | Cost |
|----------|-------|------|
| Nemotron Super teacher | 81.23M output tokens | $75.19 |
| Nemotron Nano calibration + student audit | 3.22M input + 8.23M output tokens | $2.17 |
| Llama (endpoint smoke tests) | 3.03M input + 0.12M output | $0.44 |
| Qwen3-32B gate calibration (708 items) | 1.28M input + 1.10M output | $0.46 |
| Dedicated Endpoint (Qwen3-32B judge) | 21.95 GPU hours | $88.90 |
| H100 NVLink | 10.22 GPU hours | $39.34 |
| CPU + RAM | 452.60 vCPU / 1,810.39 GiB hours | $11.22 |
| Disk + Object Storage | 76,053.72 GiB hours | $7.73 |
| **Total v2** | | **$225.45** |

---

## README STATUS — COMPLETE ✅ (HEAD = f225a76)

All sections committed. All v4 review fixes landed:
- v4 Fix #1: real live-endpoint SAFE curl + response + gate-level UNSAFE trace (c2cc0a4)
- v4 Fix #2: "Which model to deploy" callout — v1 for readability, v2 for research/safety (a76f426)
- v4 Fix #3: max_tokens=16000 engineering-finding callout in exec block (cbd32ad)

Plus v5-driven rigor + framing:
- Paired bootstrap CIs on VAGT deltas + surfaced in the README VAGT table (88085fe)
- "The finding" — README now leads with the VAGT inversion before the exec summary (1a4f52c)

Plus 4.8-review doc fixes (all landed): VAGT-as-response-to-κ framing (957fcdf), Nemotron-refs eval trail
(f20cd2e), all results/ artifacts listed in Project Structure (6debd43), endpoint cold-start note + digest
pointer (87d719c).

Earlier fixes landed: VAGT origin framing, recall-denominator footnote, per-stage image tags,
cost $134.81, training-log evidence, blog placeholder removed, σ²_B trimmed to 2×, safety_mode
contract documented, Nemotron-reference eval (companion table).

---

## OPUS 4.7 REVIEW HISTORY

| Review | Score | Verdict |
|--------|-------|---------|
| v2 (review_output_v2_opus47.txt) | 33/40 | "Submission-ready and competitive for a top-tier finish" (Impact 7) |
| v3 (post first fixes) | 33/40 | "Submission-ready and competitive for a top placement" |
| v4 (all fixes landed) | 34/40 | "Submission-ready and competitive for a top prize" (Impact 8) |
| v5 (with bonus prompt) | 32/40 | scores non-deterministic across runs (range 31–34) |

v4 per-criterion: Technological 9 / Design 8 / Impact 8 / Idea 9.
v5 bonus answers: "borderline top-5, not top-3 as submitted"; single biggest lever from competitive → first place =
the **/v1/audit_panel** "win move" — turn VAGT into a reusable Nebius-native judge-panel calibration tool.
v5 top-3: (1) lead with the finding ✅ done (1a4f52c), (2) demonstrate DISAGREE end-to-end via curl — OPEN
(student doesn't self-drop reliably; needs a crafted case), (3) commit bootstrap CIs ✅ done (88085fe).

Review outputs (all UNTRACKED — decide before final submission):
- review_output_v2_opus47.txt, review_output_v3_opus47.txt, review_output_v4_opus47.txt, review_output_v5_opus47.txt
- run_review.py (now supports --model / --prompt), review_prompt.txt, review_prompt_with_bonus.txt
- audit_panel_clarification_prompt.txt, audit_panel_clarification_response.txt
- review_output_v1_opus48.txt, review_output_v2_opus48.txt, review_output_v3_opus48.txt (bonus)
- disagree_capture_clarification_prompt.txt, disagree_capture_clarification_response.txt

---

## OPUS 4.8 REVIEW HISTORY

| Review | Score | Verdict |
|--------|-------|---------|
| v1 (review_output_v1_opus48.txt)        | 34/40 | "Submission-ready and competitive" |
| v2 (review_output_v2_opus48.txt)        | 34/40 | stable — no new substantive findings vs v1 |
| v3 (review_output_v3_opus48.txt, bonus) | 34/40 | "credibly top-3 capable … not yet a locked first place" |

Per-criterion (stable across all three runs): Technological 9 / Design 8 / Impact 8 / Idea 9.

**Bonus ("the one thing to win"):** make the DISAGREE branch witnessable + reframe around the safety layer.
Shared diagnosis of both bonus runs: the killer finding (only Nemotron catches a silent diagnosis drop) is
never shown live — "proven on paper but never witnessed."

**Self-correction (disagree_capture_clarification_response.txt):** Opus 4.8 REVERSED its own hero-slot advice.
A crafted DISAGREE is a *synthetic gate test*, not live product output (our model preserves diagnoses), so it
must NOT sit at the top as "The finding" (that would overclaim). Correct placement = an honestly-labeled
gate-level worked example inside Medical Safety Evaluation; real evaluate_safety gate; no curl/hero framing;
committed only if the panel actually splits. Top-of-README finding stays the VAGT inversion.

False positive to ignore (both 4.8 runs): "future-dated 2026-08-28 training log" — 2026-08-28 is a real PAST
date; the flag is a model knowledge-cutoff artifact. Timestamp is correct — do NOT change it.

---

## FABLE 5 REVIEW HISTORY

| Review | Score | Verdict |
|--------|-------|---------|
| v1 (review_output_v1_fable5.txt, no bonus) | 28/40 | "Strong, honest, technically real … submit after the fixes, not before" |
| v2 (review_output_v2_fable5.txt, no bonus, post-7-fixes) | 27/40 | "submission-ready in substance, not yet in presentation or gate integrity" |
| v4 (review_output_v4_fable5.txt) | 28/40 | audit praised ("dual-auditor, not a hand-wave"); ceilinged by structural items + a new cost-table contradiction — all README fix-levers then landed |
| **v6 (review_output_v6_fable5.txt)** | **29/40** ⬆️ | **+1 → Impact 7.** `/v1/audit_panel` = "the broadest-impact piece" + "the genuinely creative move"; verdict "real, well-instrumented Nebius+Nemotron pipeline with honest negative results." Two Rule#2 defects it caught are FIXED (d6fdd08): inverted "family shares blind spot" + false "zero errors" for Nano. REMAINING: (1) cost accounting — $225.45 omits the ~$1.7 JudgeBench run, the 5 audit-pool candidate runs (Ultra 550B etc.), and external Claude/Gemini auditor spend → restate "$225.45 Nebius + $X external"; (2) project-structure listing GAP — audit_pool/ + gen_pool_verdicts.py/selector.py ARE committed but NOT in the README tree listing, so Fable read them as "missing" (add them; safety_eval_v2.py is a v1-repo file); (3) Why-VAGT re-scope — "family diversity necessary" untested, "statistically indistinguishable" checked vs reference CI not paired per-candidate; (4) intro "3 judges" → "2-judge rule + advisory Llama"; soften "all-Nemotron". → **ALL 4 LANDED (f33ede2/e311127/a8aae74/f1fee87) ✅** |
| bonus-v1 (review_output_bonus_v1_fable5.txt, v2 prompt) | 29/40 | Idea 8↑7; Track A physician benchmark / Track B live service; single gap = human-anchored τ |
| **bonus-v2 (review_output_bonus_v2_fable5.txt, v3 prompt)** | **27/40** | **"first-place README, not yet first-place app"**; sharper single-thesis prompt (τ=0 controls unlabeled = weakest link); confirms **Direction B** — Fable rejects the pivot |

Per-criterion: Technological 8 / Design 7 / Impact 6 / Idea 7. Harsher + more forensic than Opus 4.8 (33-34) —
grader temperament, not a regression. Run: run_review.py --model claude-fable-5-1, MAX_TOKENS=16000 (needed —
used 14,514 output tokens; truncates at 8000).

7 fixes landed (all committed this session):
1. A+B (f423b99): Key-findings +0.072→+0.071; "hallucinated"→"omitted" (all demonstrated catches are omissions)
2. C (ca0bfba): billing → $134.81 / 10.22 GPU hrs (README table + CCC swept; six line items sum EXACTLY)
3. Tree (a72cfc8): + logs/train_v2.json.gz + results/disagree_case_gate.json (safety_eval_v2.py left out — v1 ref)
4. Disclosures (d707bc4): judge-params table (temp 0 / thinking off / mt 2000·2000·8000); 4-bit NF4 QLoRA base
   (merge loads fp16); epoch-2 best-checkpoint (load_best_model_at_end, NOT epoch-3 overfit 0.8610)
5. DISAGREE rate (b2d37e3): 203/708 (28.7%) = 136 catches + 67 clean false alarms (~1-in-3 spurious)
6. Overclaim (9afd50b): "proving … blind" → "demonstrating on MedSimp-JudgeBench … moves the wrong way"
7. Value prop (fec2193): patient-facing sentence before "The finding"

REMAINING (needs key): calibration≠gate re-run — the 68%/14%/7% and 203/708 numbers come from the CALIBRATION
prompt (Nemotron JSON-CoT + Llama/Qwen v1 no-CoT), NOT safety_gate.py's one-word gate prompt. A full 708-item
re-run through the gate prompt would let the README describe the DEPLOYED gate directly. (Subjective/deferred:
larger "lead with patient value prop" restructure — partially addressed by fec2193.)
Note: Fable did NOT flag the 2026-date false positive that Opus keeps raising.

### v2 (27/40) — after the 7 fixes: score DOWN 1, new internal-consistency issues (Design 7→6)
Per-criterion: Tech 8 / Design 6 / Impact 6 / Idea 7. The 7 fixes didn't raise the score — Fable surfaced NEW
contradictions, two of them SELF-INFLICTED by this session's edits.

Three confirmed rule-#2 inconsistencies (must fix, offline):
  #1 "Token Factory dominates cost (93%)" (README:346) → WRONG; actual ≈57% (76.52/134.81). Our billing update
     ($110.42→$134.81) made it worse (was 69% at old total). Never 93%.
  #2 "~$25–30" training cost (README:103) → still unfixed; 2.37h×$3.85≈$9, or the $39.34 GPU line (train+eval+merge).
  #3 judge-params table (README:301) still says "Qwen3-32B" — stale after the gate swap to Qwen3-30B-A3B
     (SELF-INFLICTED). The calibration recall table (README:261) correctly STAYS Qwen3-32B (historical).

Two framing decisions pending (not arithmetic):
  #4 "3-judge gate" but Llama is NOT in the decision rule (safety_gate.py branches only nemotron/qwen; Llama
     called+billed+returned but not consulted) → drop Llama (2-judge) or add it to the rule.
  #5 "permanent Nebius serverless URL — scales to zero" (README:314,399) vs the actual dev tunnel
     (…tunnel.applications.eu-north1.nebius.cloud) launched via a Job → describe hosting accurately.

Minor (flagged, unfixed): Krippendorff α value never printed; "Claude implied ~7.0" FK unsourced; "Ultra"
mentioned but unused; "δ 1.6–5.0%" hardware-transfer unsourced.

### v2 DEEP READ — cross-referenced findings (this session)
Per-criterion (v2): Tech 8 / Design 6 / Impact 6 / Idea 7 → 27/40. Deep-read insights, each verified against
committed code / both repos:
- **Research vs Product are two different stories in one README.** Fable's Design hit (6/10): the VAGT
  research finding and the shippable product need separate sections; the "v1 is what to deploy" note collides
  with the endpoint serving v2.
- **Llama is not in the decision rule** (verified safety_gate.py:122-135) — called+billed+returned, never
  consulted. Origin: v1 was Llama+Qwen deciding; v2 rewrite (81b8b5c) swapped Nemotron into Llama's DISAGREE
  slot (68% vs 14% diagnosis recall). Code comment documents it ("weakest recall — informational").
  ACTION: add Llama to the rule OR relabel a 2-judge gate and drop the call.
- **Endpoint framing wrong.** v1 blog + v1 README describe a *persistent* Nebius Endpoint
  (`nebius ai endpoint create --public --container-port 8000`, "stays up"); the v1 blog reserves "serverless"
  for Token Factory only. v2 README's "permanent serverless URL — scales to zero — $0 idle" is inaccurate for
  the self-hosted vLLM+gate host (bills H100 GPU-h while up; ~27s is judge latency, not cold-start wake).
- **Qwen3-32B removal is permanent** (retested: still 404 via API on both .ai/.com TLDs). To reproduce the
  EXACT model, self-host the open weights ON Nebius (Job+vLLM) — NOT a third-party API (would break the
  Nebius-native premise and still wouldn't match the original serving stack).
- **API catalog is volatile**: /v1/models shrank 31→26→22 mid-session (Qwen3-Next also vanished). Real
  reproducibility caveat. NOTE: only the API was checked — the Nebius console/UI was NOT inspected.

---

## BONUS REVIEW (Fable 5) + STRATEGIC DIRECTION — DIRECTION B SELECTED (2026-09-11)

**review_output_bonus_v1_fable5.txt — 29/40** (Idea 8, up from 7). Prompt = review_prompt_bonus_v2.txt
(criteria-only + expanded 6-week strategic bonus; verification-checks + submission-specific sections removed).

Key findings (bonus):
- **Track A (Research):** physician-labeled real-failure benchmark (**MedSimp-RealFail**) — validate the
  audit_panel recommendation off synthetic perturbations against real clinician-labeled drops.
- **Track B (Product):** live bring-your-own-benchmark `/v1/audit_panel` service + a second-domain (legal) demo.
- **Overall:** Research Top 3 = **yes**; Product = **no as it stands**.
- **Single remaining gap to first place:** no human-anchored τ (all ground truth is perturbation-script or
  LLM-auditor opinion; the deployed decision rule is tuned in-sample).

**review_output_bonus_v2_fable5.txt — 27/40** (Tech 8 / Design 6 / Impact 6 / Idea 7). Prompt = review_prompt_bonus_v3.txt
(single medical-mission thesis; skepticism re-aimed at the finding's ground truth; "stay medical" forced as default).
Score down 2 vs v1-bonus but that is the SHARPER PROMPT working (no longer rewards the horizontal-tool angle), not a
regression — honest signal. Key verdict: **"a first-place README, not yet a first-place app."**
- **Q1 (weakest link):** the 200 τ=0 "clean controls" are NOT known-by-construction — "faithful" only means an LLM
  wrote it un-corrupted; the finding lives on the 508-vs-200 contrast, so Nano's 35.2% "over-flag" on controls may be
  UNLABELED real omissions the incumbents can't see → the "least collateral" Nano tie-break is uninterpretable.
- **Q2 (the one move):** MedSimp-JudgeBench-Clinical — clinician-adjudicate ~870 natural-error items (521 flagged +
  150 SAFE + 200 controls), 2–3 raters, pre-register rule/selection BEFORE labels, replicate VAGT on human τ.
- **Q3:** research artifact = top-1% / plausibly top-3; app/agent = no ("superb backend, non-existent front end");
  single gap = a clinician-confirmed real drop the gate caught, shown to the user. Fable EXPLICITLY rejected the pivot
  ("defensible asset is the labeled data, not the FastAPI route") — confirms Direction B.

Both bonus prompts (product-leaning v2, mission-leaning v3) TRIANGULATE on the same gap: **human-anchored τ.**

**DECISION — DIRECTION B SELECTED (2026-09-11).** Three directions were on the table:
- **A) Veridict eval agent** — productize `/v1/audit_panel` as a standalone judge-governance app/agent.
  RISK (blog-verified): the Serverless AI Builders Challenge **2nd place** was already an "evaluation dashboard
  on your own data" (Andrei Goldenberg) → this is the crowded 2nd-place lane; MediSimplifier won **1st** as a
  vertical mission-with-a-finding.
- **B) ✅ SELECTED — Deepen MediSimplifier v2** — stay medical; physician validation + entity-grounded real-failure
  pipeline + a thin app layer. Matches the v1-winning formula (hard domain + counterintuitive finding + human-stakes mission).
- **C) App layer only** — 60s judge-usable demo (cached-real hero case: incumbents pass, Nemotron flags a
  dropped diagnosis; audit_panel leaderboard reveal); ~1–2 wk on the existing endpoints — FOLDED INTO B's W1.

**SELECTED PLAN (Direction B — 6 weeks):**
- **W1:** app layer — two-pane UI (original → plain-language rewrite) + inline 3-judge verdicts + dropped-clause
  highlight; always-on endpoint + streaming verdict (return rewrite immediately, verdict follows) → kills the
  "not openable / 27s / curl-only" app gap Fable flagged.
- **W2–6:** physician validation + VAGT replication on REAL failures — MedSimp-JudgeBench-Clinical (~870 items:
  521 gate-flagged + 150 SAFE + 200 controls; 2–3 clinical raters, third adjudicates); pre-register rule/selection
  BEFORE labels; re-run VAGT with human τ (does Nano still raise Φ_V / cut σ²_B / drive κ negative?).
- **PARALLEL:** physician brief READY TO SEND (~50 cases, 2–4 hrs; 4 unsafe categories = the 4 strata); entity-grounded
  real-omission pipeline (scispaCy/UMLS vs source) triages highest-information cases so W2–6 runs regardless of
  physician timeline.
- **No-physician stat fixes (in-control, data committed):** per-candidate paired CIs (8 verdict files); null-rater
  baseline (constant-UNSAFE + prevalence-matched random); split-half + gate-prompt per-stratum recall from
  gate_calibration_full.json → in-sample → out-of-sample.

---

## VAGT FRAMING — CRITICAL NOTE

VAGT did NOT originate in v1 submission. Correct narrative:
- v1 submitted July 15 — found κ=0.11
- Post-v1: developed VAGT (calculate_kappa_ci.py, vagt_estimand.md,
  calibration_judge_cot.py, power_simulation_v7.py, vagt_section.md etc.)
  — commit-verified: VAGT files created Aug 16, 2026 (after v1 submission July 15, before v2 window opens Aug 26)
- These files are in v1 REPO but NOT part of v1 SUBMISSION
- v2 submission period opens August 26
- v2 is VAGT's first empirical application

Files developed between submissions (in v1 repo, NOT v1 submission):
- calculate_kappa_ci.py
- calibration_judge_cot.py
- judge_accuracy_cot_vs_nocot.txt
- kappa_robustness_check.txt
- power_simulation_v7.py / power_simulation_v7.txt
- vagt_estimand.md
- vagt_medsimplifier_demo.py
- vagt_section.md

README line 11 reframed (commit 957fcdf): VAGT = "a direct response to v1's κ=0.11 finding, first applied
empirically in v2." The deeper-history mention later in the README was left untouched.

---

## AUDIT_PANEL BUILD (/v1/audit_panel — the "win move")

Spec: audit_panel_clarification_response.txt (Opus 4.7). Turns VAGT into a reusable Nebius-native
judge-panel calibration tool: given an incumbent panel + candidate pool, recommend the third rater that
best raises Φ_V on the panel's blindest stratum, with a paired-bootstrap CI receipt.

### Steps 1-4 — COMPLETE ✅ (offline, no key, no cost; 13/13 tests green)
- Step 1 (4f8688a): src/audit_panel/vagt_core.py — generalized VAGT (arbitrary panel size); estimators
  copied VERBATIM from vagt_nemotron_analysis.py (same SEED=42, same bias correction). + tests.
- Step 2 (72b9dd7): audit_pool/ground_truth.json + verdicts/{Llama-3.3-70B, Qwen3-32B, Nemotron-Nano}.json.
  Reshape validated LOSSLESS via build_pool.py (join key = row_id, NOT idx — idx is only 519/708 unique).
- Step 3 (fa1000d): pool_loader.py + selector.py (worst-stratum ΔΦ_V; bootstrap CI on recommended only).
- Step 4 (8c20382): schemas.py + router.py + mount in safe_endpoint.py (graceful try/except; health field).
- RECEIPT REPRODUCED OFFLINE — POST /v1/audit_panel (Llama+Qwen incumbent, Nemotron candidate) returns:
  recommendation=Nemotron Nano, target_blind_spot=diagnosis, expected_Phi_V_lift=0.0706 (+0.071),
  ci_95=[0.0552, 0.0866] (= README [+0.055,+0.087], bit-for-bit), caveat="dose ΔΦ_V=-0.013 n.s.".
  Pure CPU — no live judge calls.
- CI convention: selector mirrors vagt_nemotron_analysis.py (one rng, canonical stratum order) so the
  endpoint can never drift from the committed vagt_bootstrap_cis.json / README numbers.

### Step 5 — COMPLETE ✅ (offline); Steps 6-8 — PENDING (need key rotation + a deploy)
- Step 5 (cd97aa1): audit_pool/candidates.yaml committed — 3 pooled + 3 pending, all verified-live
  (gemma-3-27b-it, nemotron-super, DeepSeek-V4-Flash).
- Step 6 🔴: generate 708-row verdicts for ~3 more pool models (Token Factory, ~$1/~1h) — NEEDS key
  rotation first. NOTE: Llama-3.1-8B / Qwen2.5-72B are NOT in results/models_verified.json; use verified-live
  models (DeepSeek-V4-Flash, gemma-3-27b-it, nemotron-super).
- Step 7: rebuild endpoint image (endpoint-v4; COPY audit_pool/ + src/audit_panel/) + redeploy; live smoke test.
- Step 8: README /v1/audit_panel section + public artifacts + CCC refresh.

Prompt-consistency rule: verdict files carry prompt_provenance. The 3 committed models preserve the EXACT
verdicts behind the published +0.071 receipt (Llama/Qwen = v1 no-CoT; Nemotron = JSON-CoT); new models must
document their generating prompt.

---

## QWEN JUDGE REMOVAL (Token Factory catalog change, 2026-09-03)

`Qwen/Qwen3-32B` was REMOVED from Nebius Token Factory mid-project (catalog shrank 31→26; `/v1/models` now
404s on that id). Impact + handling:
- Gate fix (8ec5e73): safety_gate.py QWEN → `Qwen/Qwen3-30B-A3B-Instruct-2507` (nearest live instruct model).
  Smoke-tested: all 3 judges return valid verdicts (no ERROR). Endpoint functional again.
- Honest note (a83bfb8): README Medical Safety Evaluation discloses the removal + swap; states ALL
  calibration/VAGT/recall numbers describe the ORIGINAL Qwen3-32B panel.
- The new Qwen is UNCALIBRATED vs the published 68%/14%/7%/VAGT numbers (different model = different verdicts).
- Gate re-run (run_gate_calibration.py → results/gate_calibration_full.json): 708/708 attempted but INVALID —
  first ~450 ran clean while Qwen3-32B still existed, then 146 Qwen ERRORs (all Qwen) as the model was removed
  mid-run. Raw DISAGREE 100/708 (14.1%), complete-case 100/562 (17.8%) — CONTAMINATED, not usable.
  (Also: earlier an 8h hang at 450 → killed PID + resumed from checkpoint; resume worked.)
- Provenance records correctly KEEP Qwen3-32B (do NOT sweep): audit_pool/verdicts/Qwen3-32B.json,
  build_pool.py, tests/test_audit_panel.py, results/models_verified.json (now a stale snapshot).
- RE-CALIBRATION DECISION: DEFERRED — (a) regenerate the full panel with the new Qwen (big: new verdicts +
  VAGT + README), or (b) keep historical Qwen3-32B numbers behind the disclosure note (already in place).

---

## ENDPOINT ARCHITECTURE (v1 vs v2 — forensics this session)
- v1 (VERIFIED): deployed via `nebius ai endpoint create --public --container-port 8000` — a PERSISTENT Nebius
  Endpoint ("stays up and answers requests", per the v1 blog). Image endpoint-v2, /start.sh (vLLM :8001 +
  FastAPI gate :8000), H100.
- v2 (COMMITTED): jobs/safe_endpoint_v2.yaml is a **Job** (nebius ai job create shape; timeout 24h; NO public
  port / NO --public). Same container (endpoint-v3, /start.sh, H100).
- GAP: the committed v2 Job YAML does NOT declare the public port, so as written it would not produce the live
  URL (port8000-…tunnel.applications.eu-north1.nebius.cloud). How the live v2 endpoint was actually deployed is
  UNVERIFIED from committed files — likely `endpoint create --public` like v1.
- ACTION: correct safe_endpoint_v2.yaml to the Endpoint form (match v1 + the live URL), OR document the true
  deploy command. Target = persistent Nebius Endpoint, NOT "permanent serverless / scales to zero."
- Genuinely serverless = the Token Factory JUDGES (per-token, no standing infra). The vLLM+gate HOST is a
  self-hosted GPU container (bills H100 GPU-h while up; stopped between demos).

---

## MASTER ACTION LIST (assembled from Fable 5 v2 + endpoint forensics — REVIEW/ADJUST)
Reconstructed from this session's verified findings — not a verbatim prior list. Priority order:

### 🔴 CRITICAL — Gate integrity
1. Llama in the rule: add it, or relabel "2-judge gate" + drop the Llama call.
2. Deployed Qwen uncalibrated: gate runs Qwen3-30B-A3B but all recall/VAGT numbers describe Qwen3-32B; the
   "trust Qwen 0.5% FP" branch rationale no longer holds for the live model.
3. calibration≠gate prompt: 68%/14%/7% & 203/708 are from the JSON-CoT calibration prompt, not the one-word
   gate prompt — re-run 708 through safety_gate.py (needs a live Qwen).
4. Rename "VAGT-calibrated gate" → recall/specificity-informed (Φ_V never set thresholds).

### 🔴 RULE #2 — Numbers
5. ✅ (1a9f72c) "93%" TF cost share → 57% (README:346).
6. ✅ (6e916f2) "~$25–30" training cost → ~$9; cite $39.34 GPU line (README:103).
7. ⏸ DEFERRED (self-host Qwen3-32B) — judge-params table stays Qwen3-32B until the self-hosted judge is live.
8. ✅ (cf3e45f) Krippendorff α printed: diagnosis 0.077→−0.086, ΔKripp −0.163 [−0.305,−0.045] (README:245).
9. ✅ (ad0b508) FK measured: Claude refs 7.2 / Nemotron refs 10.1 (textstat 0.7.13), Δ+2.9; fixed the 8.87 conflation (README:105).
10. ⏸ DEFERRED (bundle with #12) — "$1.7/21min" JudgeBench run unsourced + absent from cost table (true total ≈$136.5).
11. ✅ (9cb472a) "δ 1.6–5.0%" defined = ROUGE-L H200→H100 reproduction delta (3 v1 models) + cited v1 table (README:53).
12. ⏸ PENDING — commit a Nebius billing export/screenshot backing $225.45 (needs Console; do #10 in the same pass).

### 🔴 README STRUCTURAL REDESIGN
13. ⏳ IN PROGRESS (4-step). Step 1/4 ✅ (5ba67bf): Track A/B skeleton + "Choose your track" nav.
    Step 2/4 ✅ (5494437 / f6491b7 / 36e7814 / 9567320): all 4 clean-mapping sub-moves landed —
    LoRA→B6, Merge&Deploy→B7, Container Images+Adapter Flow→docs/REPRODUCIBILITY.md (new overflow file),
    Public Artifacts merged into Dataset&models table (+License column). Step 3/4 = NEXT: split
    multi-audience sections (Medical Safety → A3/A5/B4/B5; Reproduce → A9/B9). Step 4/4 = write new
    sections (A1/A2/A8/B2/B3/B5/B8 + #26 block-mode DISAGREE doc). Mapping in
    readme_restructure_response.txt (UNTRACKED).
14. ✅ (2ce4086) Reframed line 107 "Which model to deploy: v1 remains recommended" → "What the endpoint serves"
    — removed the deploy-v1 instruction, kept the honest "v2 = research/safety, not a readability improvement".
15. ✅ (58ab53c + 1a9f72c + 2ce4086) Endpoint framing fixed at ALL 5 spots (17/314/346/399 + 159): persistent GPU
    Endpoint, stopped between demos; ~27s = judge-gate latency not a serverless wake; only Token Factory serverless.
16. ✅ (7e3f088 prose + e8a8e31 table) — both "Key findings" restatements removed. The table's overclaims
    (`Diagnosis blind spot — fixed`, `Safe Endpoint v2 Live — VAGT-calibrated`, bare `Φ_V +0.071`, recall-without-FP)
    and the "no numbers are invented" editorializing are gone with it. Finding now lives once (opening ¶2).
17. ✅ (fc88332) Removed the unused "Ultra" mention (README:147).
18. ✅ (7e3f088) Reconciled reading-level: opening + line 25 now "targets 6th-grade; v2 achieves ~8th-grade
    (FK 8.87, train-v32 image textstat)". Only one "6th-grade" mention remains (the honest one). NOTE: 8.87 is
    the train-v32 textstat value, NOT local 0.7.13 (which gives 9.91) — do not relabel it 0.7.13.

⚠️ LIVE DEBT (from 7e3f088): the new opening ¶3 references "Track A — Research Design" and "Track B — Product
Design" sections that DO NOT EXIST YET. The README below is not yet organized into named tracks. Next steps must
build/label the A/B sections so the opening isn't over-promising. #13 (structure) is now IN PROGRESS, not deferred.

### 🟡 MEDIUM — Artifacts
19. Raw API captures for the two Nemotron claims (empty output @1024; enable_thinking ineffective).
20. Independent v2 quality measure (3-judge safety pass rate v2 vs v1) to support "not a quality failure."
21. ✅ (via #9) Measured FK-Grade of the reference sets: Claude 7.2 / Nemotron 10.1 (textstat 0.7.13, n=9,976).
22. Changelog for train-v29/v30/v31/v32 image differences.
23. Disclose DISAGREE selection: how many items tried before idx 146.

### 🟠 DECISIONS
24. Re-calibration path: self-host Qwen3-32B on Nebius (exact) vs re-calibrate with Qwen3-30B-A3B vs keep
    historical numbers behind the disclosure note.
25. Catalog volatility: document reproducibility caveat; decide whether to pin judges via self-hosting.

### 🟡 DOCUMENTATION (Track B)
26. Document block-mode behavior on DISAGREE. `block` mode + consensus=="DISAGREE" → NOT blocked (flag-only,
    warning returned). Code (safety_gate.py:137): `blocked = safety_mode == "block" and consensus in ("UNSAFE",
    "ERROR")` — DISAGREE is not in the tuple, so it passes through. Decision is DELIBERATE (Qwen=SAFE is the
    high-specificity anchor; blocking DISAGREE would block ~1-in-3 false alarms) but UNDOCUMENTED. Goes in:
    B3 (API contract — define block behavior for all consensus classes) + B8 (known issues). Verified 2026-09-05.

## PENDING TASKS (PRIORITY ORDER)

### 🔴 SECURITY — URGENT
- [ ] Rotate Nebius API key (exposed in transcript) → then redeploy endpoint with new key so live URL survives
- [ ] Rotate HuggingFace token (exposed in transcript)

### ✅ DONE — DISAGREE gate-level worked example (9fe9fa3)
- idx 146 (Parkinson + depression drop) splits the panel LIVE (Llama SAFE + Qwen SAFE + Nemotron UNSAFE →
  DISAGREE). Committed results/disagree_case_gate.json + README worked example (honest gate-level scope, no
  hero slot). idx 21 (primary) did NOT reproduce → disclosed (calibration verdicts ≠ live-gate verbatim).

### ✅ DONE — /v1/audit_panel Steps 1-5 (offline, 13/13 green) — see AUDIT_PANEL BUILD above

### ✅ DONE — Fable 5 review v1 (no-bonus, 28/40) — 7 fixes landed; see FABLE 5 REVIEW HISTORY

### 🟢 #13 COMPLETE ✅ — README two-track restructure done: Steps 1-4 (skeleton → relocate → split → author) + finishing touches #1-#4 (0234bb7 Under-construction · b391f85 B8 items 2-3 · 0eabe6f B5 translation · de79fa7 dissolve How-it-runs). #5 (old front-matter ## sections — What-this-does / What's-new / Choose-your-track / Hardware-and-cost / Project-structure / Dataset-and-models / License / Future-Work) DEFERRED BY DESIGN: they stay as shared front-matter/appendix. TONE-POLISH ✅ (bb85afb + 5d166b5): "What this project does" rewritten as deliverables inventory; A7 "Honest caveat/interpretation" + "a real finding" labels neutralized → zero "Honest" defensive labels remain README-wide (consistent with A6 "Caveats"/B4 "Scope").
### 🟡 NEXT SEQUENCE (per methodology)
- STEP 1 ✅ COMPLETE: Qwen3-32B restored via **Nebius Dedicated Endpoint** (`dedicated/Qwen/Qwen3-32B-AcpEMaRtFNy6`; H100, 1 replica, eu-north1) — Route A (no container build). Gate reverted (3afc059): Qwen=QWEN_DEDICATED @ 8000 tokens, canonical QWEN="Qwen/Qwen3-32B", docstring fixed. Validated: 3 smoke tests + 20-item sanity (85%). enable_thinking:False NOT honored (Qwen reasons internally, like Nemotron).
    · GATE CALIBRATION DONE (f5cb9d4): 708/708 through the deployed gate prompt, **0 ERRORs** (vs 146 in the invalid prior run, archived 47880b9). Script committed (4bfbff8).
    · GATE-PROMPT FINDINGS (measured, in B5/B4): deployed gate prompt is MORE sensitive / LESS specific than the calibration prompt. DISAGREE 28.7%→20.8%; recall Nemo 84.2→79.5, Qwen 55.9→63.2, **Llama 31.7→61.2** (pure prompt effect — same model); **Qwen FP 0.5%→9.5%** (the "0.5% FP anchor" is a calibration-prompt figure, not the deployed gate). Confound: Qwen row also changed serving (serverless→dedicated), but Llama proves prompt is the dominant driver.
    · DOCS UPDATED: B5 deployed-operating-characteristics table + B4 Qwen-FP caveat (5cd7b5a); B8 item 1 → RESOLVED (2d721d4); #7 un-deferred — A3 judge-params table Qwen 8000/off* + footnote (d3b6779).
    · 🔴 STILL PENDING (your side): STOP the dedicated endpoint (per-GPU-hr billing; run long done); ROTATE the exposed key (used across the multi-hour run).
- STEP 2 IN PROGRESS: Fable 5 regular review (review_output_v3_fable5.txt) = **28/40** (same as v1; restructure offset by new inconsistencies). Verdict: submission-ready in substance, but README contradicted itself + some numbers uncited.
    · CONTRADICTION FIXES ✅ (9413b20): Qwen per-token→dedicated; Qwen recalibrated; reasoning-budget confound REFRAMED (calibration used 8000 for ALL judges per nemotron_judge_test.py:122 — NOT a confound, false premise corrected); cost $0.90→$1.63; "unmeasured"→"see B5"; B5 cites gate_calibration_full.json.
    · QUICK FIXES ✅ (f4b0327): stray #26 removed; 9976→7983 (train split); FK-Grade 8.87 precise; dedup what's-new (blockquote removed + paragraph trimmed, table kept); ¶2 leads with plain-English hook.
    · STUDENT AUDIT COMPLETE ✅ (7496866; bj4tgsiq2, run_student_audit.py): 1001/1001 v2 test outputs (predictions.json via boto3) → gate. **SAFE 474 (47.4%) / DISAGREE 265 (26.5%) / UNSAFE 256 (25.6%) / ERROR 6 (0.6%); flagged (DISAGREE+UNSAFE) = 521 (52.0%)**. Committed results/student_audit.json + run_student_audit.py + sample_audit_review.py (30-case template built: 10 UNSAFE + 10 DISAGREE + 10 SAFE control, seed=42). ⚠️ 52% flagged CONTRADICTS an unqualified "preserves diagnoses" — BUT the gate judges "preserves ALL critical info" (simplification omits detail) + high known false-alarm floor (~1-in-3 DISAGREE), so flags ≠ diagnosis drops without review.
    · DUAL-AUDITOR REVIEW COMPLETE ✅ (0322d01; bn8j2e1qv, src/llm_review_audit.py): **Claude Sonnet 5 (Anthropic) + Gemini 2.5 Pro (Google)** — independent non-project families (Nemotron=teacher, Llama/Qwen=diagnosis-blind gate judges), identical prompt, 30-case sample. RESULT: **70% agreement (14/20 flagged); 2/20 both-confirmed diagnosis drops (idx 174, 44); 12/20 both general_simplification; 6/20 contested; 10 SAFE controls clean**. Genuine-drop bound 10–35% of flagged pending review. Debug saga: model ID must be plain `claude-sonnet-5` (no dated variant → 404); `temperature` deprecated for Sonnet 5 (→ removed; Gemini stays temp=0); per-provider resume (re-run failed provider only, keep good judgments).
    · README CLAIM UPDATED ✅ (25de8bb): unqualified "our model preserves diagnoses" (B4 Scope + B8 item 3) REPLACED with the measured result; new **B5 "Student self-audit"** paragraph is the single measured source (52.0% flagged → dual-auditor sample); cites results/student_audit_review.json + docs/ADJUDICATION_BRIEF.md. Verified: grep "preserves diagnoses"=0, "dual-auditor"=3, "student_audit_review.json"=1.
    · PHYSICIAN ADJUDICATION PENDING (d7ba1f1): docs/ADJUDICATION_BRIEF.md (plain-language guide) + reserved `human_judgment` fields on the 6 contested (47, 56, 287, 393, 421, 442); physician fills → re-score → firm up the 10–35% bound.
    · FABLE FIXES (v1/v3): #1 contradictions ✅ (9413b20); #2 cite B5+κ+FK + audit ✅ (5c0de4d + dual-auditor audit closes the "preserves diagnoses" citation gap); #3 strict mode ✅ (21fe0fd + 716a4c6).
    · FABLE v4 REVIEW (review_output_v4_fable5.txt) = **28/40** (unchanged; Tech 8 / Design 7 / Impact 6 / Idea 7). Audit praised ("dual-auditor instead of a hand-wave"); score ceilinged by structural items (demo-grade product, arithmetic inversion) + one new cost-table contradiction. **ALL README FIX-LEVERS LANDED:** cost-table Qwen contradiction (bcd7489); 3-judge→2-judge + advisory-Llama *quantitatively* justified (bcd7489 + B4 5-strategy table 477c13e — majority vote would drop recall 82.1%→68.1%); deployed DISAGREE false-alarm 34.7% (51/147, 8f25cfc); patient-first opening ¶1-3 (bcd7489 + b0374b7). REMAINING: committed billing export ⬜ (needs Nebius Console). NEXT = re-run Fable 5 regular review (v5) to check score lift.
- STEP 3: Fable 5 BONUS ×2 (Research track + Product track).
- Done: #18 ✅ (7e3f088), #16 ✅ (7e3f088 + e8a8e31), #13 Step 1/4 skeleton+nav ✅ (5ba67bf).
- Step 2/4 ✅ COMPLETE — all 4 relocation sub-moves landed:
    · 2a LoRA Configuration → B6 (Model card) ✅ 5494437
    · 2b Merge & Deploy (v2) → B7 (Deployment) ✅ f6491b7
    · 2c Adapter Storage Flow + Container Images → docs/REPRODUCIBILITY.md (OVERFLOW, new file) ✅ 36e7814
    · 2d Dataset and models + Public Artifacts → merged table (+License column) ✅ 9567320
- Step 3/4 ✅ COMPLETE — both splits landed: 3a (ab3f1f2) Medical Safety → A3/A5/B4/B5/B8 (2×2 rule table, Llama-advisory, calibration-informed rename, 318 parked in B5); 3b (c5ebee7) Reproduce → A9 (analysis) / B9 (deployment, +costs note, h4 Nebius Jobs, B3 forward-note).
- Step 4 IN PROGRESS: A4 ✅ A6 ✅ (e731fe9, VAGT split) · A7 ✅ (eb37de6, relocated `## Nemotron as Teacher` + `## v2 Evaluation Results`; "What the endpoint serves" + "Adapter provenance" → B6; new authoring 23-errored-dropped-not-imputed + elaboration-freq-future-work; A3 footnote + line-27 inbound re-pointed to A7). All relocation-style splits (A4/A6/A7) now done. A8 ✅ (8908a19). B3 ✅ (f7f8472, API contract — request schema + safety_mode + response contract + /health + error semantics + #26 block-mode-DISAGREE from safety_gate.py; forward-note removed; parked-318 TRIMMED from B5 — health payload now lives once in B3). A1 ✅ (ab42383, Question & estimand — research Q + estimand-in-words + falsifiable prediction; provenance note ABSORBED from A6, now lives once in A1). A2 ✅ (fbad377, Benchmark — 708 items = 200 clean + 508 corrupted [diagnosis 150 / lateral 150 / negation 113 / dose 95], all counts verified from nemotron_calibration_full.json; silent-drop def + τ coding + provenance). **TRACK A FULLY POPULATED (A1-A9 ✅).** B1 ✅ (b371cda, What ships — user story + intended user + what-it's-not + pipeline diagram relocated from `## How it runs` [metrics trimmed → A7, VAGT-calibrated→calibration-informed, corrected serverless framing]). B2 ✅ (c3b2e35, Quickstart — Path 1 endpoint curl+JSON + Path 2 gate-only "second product use case"; SAFE curl / gate Python / Live-endpoint blockquote MOVED from B9, not duplicated). **🎉 ALL A/B STUBS POPULATED — Track A (A1-A9) ✅ Track B (B1-B9) ✅. Core of #13 (Steps 1-4) done.** NEXT = finishing touches: (1) drop "Under construction" note (now accurate to remove); (2) B8 items 2-3 (prompt drift/idx-21 + DISAGREE defense-in-depth); (3) B5 user-facing translation (miss-rate/false-alarm sentence, X from nemotron_calibration_full.json); (4) dissolve `## How it runs` remnant (492 stale framing superseded by B1 + 524 Why-TF→B7 + 526 pointer); (5) decide fate of old front-matter ## sections per Fable final structure.
- (Superseded — see "NEXT SEQUENCE" above.) Self-host Qwen3-32B → recalibrate (#7 revert); #26 now ✅ documented in B3/B8; deferred (external): #10 #12.

### 🟠 THEN (needs key / external)
- Self-host Qwen3-32B on Nebius (Job + vLLM) → then revert safety_gate.py + un-defer #7.
- #12 billing export (Console) → then #10 (add the $1.7 JudgeBench run, reconcile the total).
- Fable 5 BONUS review — after all the above land.

### 🟠 DECISIONS PENDING
- #4 Llama in the gate: keep "3-judge" (add Llama to the rule) or relabel 2-judge (drop the Llama call)?
- #5 endpoint framing: "permanent serverless" → describe the actual Job+tunnel hosting.
- Re-calibration with new Qwen (Qwen3-30B-A3B): regenerate panel, or keep historical + disclosure note?

### 🟡 THEN (gated on 🔴 key rotation)
- Fable 5 BONUS review (--prompt review_prompt_with_bonus.txt --model claude-fable-5-1) — after fixes land.
- /v1/audit_panel Steps 6-8: generate ~3 more models' verdicts → endpoint-v4 rebuild + redeploy → README section.

### 🟢 Deliverables (remaining)
- [ ] Blog post v2 (Medium) — "From Finding to Framework"
- [ ] Demo video (< 3 min, YouTube)
- [ ] Devpost submission fields

### IRL Event
- Tel Aviv, September 15 (City Winner Award $500 possible)

---

## SCHEDULE

```
September (remaining):
  - Rotate keys + redeploy endpoint
  - Blog post v2 (Medium)
  - IRL Event Tel Aviv (September 15)

Late September – October:
  - Demo video (< 3 min, YouTube)
  - Devpost submission fields
  - Final Opus review iterations → final submission (deadline Oct 30)
```

---

## ACCURACY CATCHES (ALL SESSIONS)

1. PABAK/Gwet AC1 overclaim → corrected to Fleiss κ + Krippendorff α
2. "ERROR in any judge" → corrected to "ERROR in Nemotron or Qwen"
3. Fleiss κ vs Krippendorff α attribution → precision fix
4. eval path eval_v2/results.json → results/eval_v2_results.json
5. Total cost $110.42 confirmed correct (matches line-item sum); earlier "$110.42 → $110.41" catch was itself wrong and reverted — SUPERSEDED 2026-09-02: billing updated to $134.81 as endpoint/eval GPU+CPU+disk usage grew (10.22 GPU hrs; line items re-verified to sum exactly; see NEBIUS BILLING)
6. Recall denominators: 68% = diagnosis-corrupted n=150 (not n≈127); 47% = VAGT stratum n=333 (not all-708) — README footnote committed
7. Endpoint latency: ~73s → ~27s (measured live, 26,975–28,719 ms)
8. Per-stage image tags: train=v29 / eval=v30 / merge=v31 (README had said v31 for all three)
9. Abandoned the un-reproducible DISAGREE endpoint claim (total_ms ~73,392) — could not reproduce across 5 tests; committed honest SAFE smoke test (26,975 ms) instead
10. VAGT Δ was unpaired (2- and 3-rater bootstrapped on different item sets); added paired bootstrap → diagnosis ΔΦ_V +0.071 [+0.055,+0.087] (matches unpaired +0.072 within rounding), CI excludes 0

---

## IMPORTANT NOTES

- v1 repo: github.com/deepset01-sys/medisimplifier-nebius (🥇 First Place, $320.20)
- VAGT post-v1 files are in v1 repo but NOT part of v1 submission
- "From Finding to Framework" narrative → blog post / Devpost, NOT README
- Nemotron Nano: "ERROR" in (nemotron, qwen) → Llama NOT in consensus logic
- Test set for eval: GuyDor007 test (1,001) → NOT Nemotron dataset test (998)
- 9,999 source records → 9,976 valid Nemotron references (23 errored)
- FK-Grade 8.87 > v1 7.33 → v2 LESS readable for patients; v2's value = VAGT research + safety gate
- σ²_B 0.347→0.229 now appears 2× in README (VAGT table + one narrative) — trim complete
- Endpoint is PUBLIC + unauthenticated in README (live curl advertised) — each call spends Token Factory tokens; consider rate-limit / take-down after judging
- FK-Grade version note: local textstat (newer) gives 9.91; train-v32 image textstat gives 8.87 (comparable to baseline) — always score in-image for comparable numbers
- VAGT deltas are CI-backed (paired bootstrap, seed=42, vagt_bootstrap_cis.json): diagnosis ΔΦ_V +0.071 [+0.055,+0.087] & ΔFleiss κ −0.163 [−0.305,−0.045] both exclude 0; dose ΔΦ_V −0.013 [−0.055,+0.021] not significant
- CLI reproduction: `nebius ai job create --volume` does NOT work for the bucket mounts these jobs use — bare
  bucket → "unsupported volume source type"; `s3://BUCKET:/path:rw` → "s3_config.endpoint: value is required"
  (needs an S3 endpoint + creds profile the native YAML `bucket:` mount supplies automatically). Verified twice
  on VM 195.242.10.164; no job created either time (zero GPU spend). VERIFIED reproduction path = Nebius
  Console + committed YAMLs. Decision (Option 1): do NOT put unverified CLI commands in the README.
- Reviews done: Opus 4.8 v1/v2/v4 33-34 + v3 bonus; Fable 5 v1 28/40, v2 27/40 (no-bonus). Next: fix v2 inconsistencies, then Fable 5 bonus.
