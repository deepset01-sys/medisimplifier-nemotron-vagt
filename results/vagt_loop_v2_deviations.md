# Scoped-gate experiment on JudgeBench v2 — deviations log

This log covers the run of `scripts/run_vagt_loop_v2.py` pre-registered in
`docs/vagt_loop_v2_preregistration.md` (commit `d69f506`; recorded blob ids: pre-registration
`03ba68ba…`, runner `49167946…`). The run ended 2026-09-27 02:05:19 UTC; this log was written
afterwards, from an independent recomputation of the committed call records.

None of the four gaps changes a pre-registered verdict. Primary fails, guardrail passes, driver
fails, and the noise check passes, under every reading below.

## 1. Production view: two readings of "counting only"

Pre-registration §6: "the same contrast, counting only verdicts reached at 8,000 tokens within 60 s."
The runner scored the calls that needed a second budget step as non-answers, and applied the
primary rule to them (against A1). "Counting only" can also be read as dropping those calls. The
two readings give opposite signs:

| Reading | d_J (A1 − A0) [95% CI] | Thresholds |
|--|--|--|
| As run: escalated calls scored against A1 | −0.0063 [−0.1146, +0.1021] | fail / pass / fail |
| Escalated calls dropped (complete-case) | +0.0444 [−0.0618, +0.1535] | fail / pass / fail |
| Escalated calls scored for A1 | +0.0750 [−0.0293, +0.1812] | fail / pass / fail |

- Escalated calls: A1 13 on drops and 20 on controls; A0 4 and 2.
- The 60 s limit never applied. The slowest first-step verdict took 59.1 s, and every 8,000-token
  cut-off took 63.6–86.6 s. So the production view is simply "first-step verdicts only".
- Both readings agree that at the deployed budget A1 shows no reliable edge over A0.

## 2. Where deviations are logged

Pre-registration §10.5 says deviations are logged in the summary file. The summary as written by
the run has no deviations field. This file is the log instead. `vagt_loop_v2_summary.json` is left
exactly as the run wrote it, so it still equals the runner's own analysis of the calls file.

## 3. What the git guard covered

The runner checks, and records blob ids for, only the pre-registration note and the runner. It did
not hash the code it imports or the files it reads. The blob ids of those files at `d69f506` are
recorded here after the fact. All of them match the working tree, so none changed between the
commit and the run.

| File | Blob at d69f506 |
|--|--|
| `src/safety_gate.py` (A0 prompt) | `2d06d2355e03700b829a2d8f45af981fb35e35b9` |
| `scripts/run_vagt_loop_experiment.py` (A1 prompt) | `de98e3ed023f42790ab760b69c17fa13915c37fc` |
| `src/audit_panel/vagt_core.py` | `76f29a7eae33bc349e804916d1e90db996cb1021` |
| `scripts/run_pool_judgebench_v2.py` | `e13d139517de3371748143cb2168ad8906c78bb2` |
| `scripts/run_panel_judgebench_v2.py` | `4aa5ce5b5d5945346fce8a035fbd2518eb717074` |
| `results/judgebench_v2_tau1_final.json` | `5ebab6f6cb8187a7d4b7519caadccfbed5569635` |
| `results/judgebench_v2_clean_controls.json` | `de23b167f2dc4510c411c4e104c9f9c4a5adabb6` |
| `results/judgebench_v2_panel_gate.json` | `add8e02194a7ecf6c36664028ae99bcf60dc8285` |

- **The original notes** were read from files outside this repository:
  - `results/student_predictions.json` is untracked; sha256 `8c94bb7c3914cbbe796142331a15ac7ed59658cc42f5c88ae5d5281b69b72557`.
  - The v1 repository's `results/nebius_evidence/calibration_verdicts.json` has sha256
    `88ef8dfa17625e35f5dc454e06dbbb8b5315f9f399e22e04e6eb925778360ea8`, and is committed in the
    v1 repository as blob `399489b482b1883d2af8589f65712214b33cc734`.
- **The pilot** (`--pilot`) returns before the guard and records no git metadata. It started 24 s
  after the commit, on 10 supplementary controls that are not analysed.
- **`--analyze-only`** copies the recorded ids from the calls file. They identify the code that
  collected the data, not the code that later analyses it. The committed summary was written by
  the full run itself, not by `--analyze-only`.

## 4. Placebo non-answers in the A1 arm

The runner scores a non-answer in a placebo half by the arm it came from. Read "as if they were two
arms" (§5) literally, a non-answer in the reference half (calls 1–2) is scored for that half. This
affects one A1 call (hf634, drop, call 2):

| A1 placebo | d_R [95% CI] | d_J [95% CI] |
|--|--|--|
| As run (scored by arm) | +0.0292 [−0.0126, +0.0708] | +0.0167 [−0.0542, +0.0875] |
| Scored by half | +0.0250 [−0.0167, +0.0667] | +0.0125 [−0.0583, +0.0833] |

The A0 placebo has no non-answers and is unaffected. The noise check passes under both readings.

## Not a deviation, but material

The power calculation in §9 covered only the recall difference. For the primary threshold, the
standard error of d_J is about 0.051, so a true +0.10 improvement would have passed only about
half the time. The primary result therefore cannot rule out an improvement of that size.
