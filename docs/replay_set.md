# Replay set — selection rule

Fixed and committed before the replay recording. Replay mode in the demo shows only the 28 cases this rule selects,
each recorded once, in one session on the final endpoint image. The source notes are synthetic (Asclepius); the
recorded cases contain text derived from them, so the replay data file joins the CC-BY-NC-SA-4.0 list in the README.

## Part A — pipeline cases (12)

- **Pool:** the 1,001 evaluation inputs (`input` in `results/student_predictions.json`, keyed by `index`).
- **Strata:** the 1,001 sorted by input length in characters, ties by `index`; the first 334 are short, the next
  333 middle, the last 334 long.
- **Draw:** one generator, `random.Random(42)`, calls `sample(stratum, 4)` on the short, middle and long stratum in
  that order, each stratum given as its `index` values in ascending order. The 12 are drawn before the recording and
  committed with the Python version used.
- **Run:** each input is sent once to the endpoint's `POST /v1/simplify` with
  `{"text": <input>, "max_tokens": 1024, "safety_mode": "flag"}`; the full response is recorded with the image
  digest and the time.
- **Shown:** every case, whatever the gate says, with its `truncated` flag. If the input's saved evaluation output is
  one of the 146 that stopped at the 512-token cap (`results/eval_v2_output_truncation.json`), the case says that
  the published evaluation's output for it was cut there. Each case reads "not reviewed" unless the author has
  reviewed it. Each rewrite is read in full for content that is not in the input (the gate checks for dropped
  content, not added content; README B8 item 6), and what is found is recorded with the case.

## Part B — known-answer gate cases (16)

- **Pool:** the 240 JudgeBench v2 items of the hand-verified stratum (120 primary-diagnosis drops, 120 paired
  controls), keyed by (`idx`, `condition`), since a drop and its paired control share an `idx`.
- **Cells,** from the committed consensus of the deployed gate in `results/judgebench_v2_panel_gate.json` (flagged =
  `UNSAFE` or `DISAGREE`): drop caught (110), drop missed (10), control falsely flagged (58), control correctly
  passed (62).
- **Draw:** after Part A, a second generator, `random.Random(42)`, calls `sample(cell, 4)` on the four cells in the
  order above, each cell given as its remaining (`idx`, `condition`) keys (see "Overlaps" below) sorted as strings.
  Drawn before the recording and committed with Part A.
- **Run:** in the same session the gate (`src/safety_gate.py` at the commit of the final image, with the same three
  judges) scores each pair once; the live verdicts are recorded with the time.
- **Shown:** each pair with its live verdict beside its committed one, and the stratum's committed rates: 110 of 120
  drops flagged, 58 of 120 controls falsely flagged. A pair stays in the cell it was drawn from whatever its live
  verdict; nothing is re-drawn or replaced. Verdicts can differ between runs: in the gate-parser check, Qwen's
  verdict differed from the committed run on 41 of the 240 items (`results/judgebench_v2_qwen_parser_check.json`).

## Both parts

- **Overlaps:** all 240 Part B items were built from evaluation inputs (`idx` `hf<N>` and a numeric `idx` `N` both
  name the input with `index` N), and every `idx` names one drop and its paired control. Before Part B is sampled,
  every item built from one of Part A's 12 inputs is removed from the four cells; before each control cell is
  sampled, every `idx` already drawn in the two drop cells is removed from it. No Part A input reappears in Part B,
  and no note appears there as both a drop and a control.
- **Before the session:** the recording starts only after `scripts/verify_endpoint.py --all` passes against the
  endpoint.
- **Failed calls:** a Part A call that gets no usable response (a connection error, a time-out or an HTTP 5xx) is
  repeated up to twice; if all three attempts fail, the case is shown as not recorded, with the error, and is not
  replaced.
- **ERROR verdicts:** a response or gate result with an `ERROR` verdict, from one judge or in the consensus, is
  recorded and shown as it is, not repeated. Each judge call already makes up to three attempts inside the gate.

## New text in Replay mode

Pasted text is never processed in Replay mode. Pasting switches to Live mode, which needs the user's own endpoint
URL; without one, the app says that new text needs a running endpoint and links the reproduction guide.

## Corrections

- 2026-10-03, after the draw was run and before it was committed: "Overlaps" first said 184 of the 240 Part B items
  were built from evaluation inputs, counting only `idx` `hf<N>`. The other 56, a drop and its control for each of
  28 numeric `idx` values, were built from evaluation inputs too: each numeric `idx` N names the input with `index` N.
  Checked by exact text: the 28 notes in Project v1's `results/nebius_evidence/calibration_verdicts.json` (public
  repository [github.com/deepset01-sys/medisimplifier-nebius](https://github.com/deepset01-sys/medisimplifier-nebius/tree/dd6681bed29199f7ed2f1eb10af3ad2c99b734d3)
  at commit `dd6681b`) equal those inputs in `results/student_predictions.json`. So all 240 are, and the exclusion
  covers both forms. No numeric `idx` is among Part A's 12 inputs, so the drawn identifiers are unchanged.
