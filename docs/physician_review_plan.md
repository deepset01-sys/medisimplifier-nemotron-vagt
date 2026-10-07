# Physician review — analysis plan

**Status:** fixed before any answer is seen, from the commit that adds it. Every later change is listed in
the results as a deviation. No returned sheet is opened before that commit is on GitHub.

## The request

- **Sent** by email on 2026-10-06 to a physician: a sheet of 16 pairs, each an original discharge summary and a
  plain-language rewrite of it, with a two-page brief. For each pair the physician marks Safe or Unsafe; if Unsafe,
  one category (A diagnosis dropped or softened, B medication or dose dropped or changed, C left/right or "no/not"
  flipped, D other clinical problem); an optional one-sentence note; and a confidence (Sure, Fairly sure, Unsure).
  The pairs come in four blocks of four (cases 1–4, 5–8, 9–12, 13–16), and the physician may stop after any block.
  For each pair the sheet showed only the two texts, a case number and empty answer cells: no gate verdict, label,
  cell, primary diagnosis or pair identifier.
- **The pairs** are the 16 Part B known-answer pairs of the replay set (`results/replay_set_draw.json`, commit
  `be46161`; rule in `docs/replay_set.md`): four from each cell of the gate's committed result on the hand-verified
  stratum — drop caught, drop missed, control falsely flagged, control correctly passed. A drop is a reference
  rewrite whose primary diagnosis was removed, verified by hand by the author
  (`results/judgebench_v2_tau1_final.json`); a control is an unedited reference rewrite
  (`results/judgebench_v2_clean_controls.json`). The source notes are synthetic (Asclepius), as
  `docs/replay_set.md` says, and the order on the sheet comes from a private random seed.
- This plan covers this request only. The 50-case sheet of 2026-09-12 (`docs/ADJUDICATION_BRIEF.md`) is a
  separate request.

## Order of steps

1. **Signature.** The author signs off on this file, and only then is it committed. Pushing the commit to
   GitHub is a separate step.
2. **Receipt.** A returned sheet — the filled file, or the email itself if the answers are written in it — is
   saved unopened, and its sha256 and time of receipt (UTC) are recorded. A sheet that arrives before the commit
   is on GitHub stays unopened until then.
3. **Consent request,** sent when a sheet is received, before it is opened and whatever it holds (see "What is
   published about the physician").
4. **Opening and merging,** only once the commit that adds this plan is on GitHub. The answers are copied as
   written into one file, one row per case number: Safe or Unsafe, category, confidence, and whether a note was
   written. Nothing is corrected, completed or recoded. Where the return carries the texts, each row's texts are
   checked against the sent sheet; a row whose texts do not match its case number is outside the tables and
   listed as "texts do not match". The merged file's sha256 is recorded.
5. **The key,** a private file that maps each case number to its pair, is opened only after step 4, checked
   against the sha256 recorded before the sheet was sent, and joined on the case number.
6. **Analysis,** as below. Nothing is re-run: the gate's verdicts, the labels and the stored explanations are
   the ones named here.
7. **Results:** a separate README section and a Devpost line, for the author's sign-off, before the 2026-10-26
   submission freeze. They leave the headline results unchanged, and they cite this plan's commit, when it was on
   GitHub, each sheet's time of receipt and when it was opened.

## What the answers are compared with

- **The gate:** its committed consensus for each pair in `results/judgebench_v2_panel_gate.json` (commit
  `2f70ad3`): flagged = `UNSAFE` or `DISAGREE`, passed = `SAFE`, as in the replay-set rule; none of the 240 is
  `ERROR`. The live verdicts the replay recording adds later are not used.
- **The hand-verified label:** drop (τ=1) or control (τ=0), from the same file. The two auditors' labels (the
  dual-auditor review in `results/student_audit_review.json`, Claude Sonnet 5 and Gemini 2.5 Pro) exist for none
  of the 16 pairs: they judged the student model's rewrites, and none of the 16 rewrites is one of those. Two of
  the 16 share an input with a reviewed case (171 and 762), with a different rewrite.
- **The explanation of a gate flag** (`src/explain.py`, commit `97b620f`): the explanations stored from two
  development runs of the method that went into that commit, on all 240 pairs of the stratum, 2026-10-07, not in
  this repository.
- **The committed labels and results** do not change because of the answers: disagreements are reported, not
  corrected.

## Results: counts only

The 16 pairs were drawn by design, four per cell, not at random from any population. The results are counts of
these cases, with no confidence intervals and no accuracy percentages. In both tables the gate's or the label's
side is fixed by the draw (8 and 8 when all 16 are answered).

- **Table 1:** the physician's Safe or Unsafe against the gate's flagged or passed.
- **Table 2:** the physician's Safe or Unsafe against the hand-verified drop or control. The label concerns the
  removed primary diagnosis only; a pair can be Unsafe for another reason, which its category shows.
- **In both tables** only cases with a Safe or Unsafe answer count, and each cell gives how many of its answers
  were marked Unsure. Confidence is not used to weight or drop answers.
- **Case list:** every case returned, with its pair (`idx`, `condition`), its cell, the gate's consensus and the
  answer as written (Safe or Unsafe, category, confidence; no note). Every disagreement is marked, in both
  directions: Unsafe where the gate passed or on a control, Safe where the gate flagged or on a drop.
- **Answers as they are:** "Unsure", partial and missing answers are reported as they are. A case without Safe or
  Unsafe is outside the tables and listed as "no answer". An Unsafe without a category, a category with Safe, a
  missing confidence, or anything outside the sheet's choices is reported as written.
- **A partial return** is analyzed by the blocks returned; a block not returned is reported as such. Answers
  received after the cutoff are not used, and the results say so.

## The explanation and category A (counts only)

For each stored run, the physician's category A (Unsafe with A) or not A (Safe, or Unsafe with B, C or D) against
the run's outcome for the pair: possible omissions (stored status `explained`); none found (`none` with reason
`no_dropped_diagnosis`, `found_in_rewrite` or `no_grounded_quote`); or the explainer's own reply cut (`none`,
`truncated`) — in the endpoint's terms, `possible_omissions`, `none_found` (reason `no_omission_found`,
`all_found_in_rewrite` or `no_quote_held_up`) and `unavailable` (reason `explainer_reply_cut`). Counted separately
for the gate-flagged pairs, the only ones the endpoint adds an explanation to, and for the passed ones. Also
counted: the cases where the two runs differ, and the stored calls over 30 seconds. Only answers that are Safe
without a category, or Unsafe with one, enter these counts; the case list shows the others.

These counts describe; they do not validate. The explanation was developed on these 240 pairs, the 16 among them.
The stored runs predate the endpoint's 30-second limit and the explanation's final wording. Category A is the
most serious problem only, so a diagnosis problem named only in a note is not counted: notes are not coded.

## If two physicians answer

Each is analyzed separately as above, with their own sheet, sha256 and consent. Their agreement is given as counts
over the cases both answered (same Safe or Unsafe; same category), with the cases where they differ listed; it is
published only with both consents to the use of the answers. Sixteen cases chosen by design are too few for an
agreement coefficient: these counts describe these cases only.

## When results are published

- **A sheet returned by the cutoff:** the results section appears whatever the result, within the consent given.
- **No sheet by the cutoff:** no results section is published, and no text claims a physician review.
- **The cutoff** is 2026-10-22, end of day UTC; the time of receipt recorded in step 2 decides.

## What is published about the physician

Nothing about the physician's name or area of expertise is public as of this plan's commit. The invitation, the
author's email of 2026-10-06, says that the physician's name and area of expertise will be published as a
consulting expert only with the physician's consent, and that any phrasing and publication need the physician's
approval in advance.

- **The consent request.** Only if a sheet is returned does the author ask the physician in writing for permission
  (1) to publish the physician's name and area of expertise, as a consulting expert on the filled pairs, and (2)
  to use the physician's answers in the published results: counts and case-level categories, no notes quoted.
  The request shows the exact wording that would name or describe the physician. Silence is not consent, and
  consent counts only in writing received before the 2026-10-26 submission freeze.
- **With written consent to (2),** the results section is published; with written consent to (1) as well, it gives
  the physician's name and area of expertise, as a consulting expert, in the wording the physician approved.
- **Without written consent to (1),** every text says only "an independent physician", and no draft names the
  physician or the area of expertise.
- **Without written consent to (2),** no results section is published, no text claims a physician review, and
  the physician is not named.
- **Notes** are not quoted word for word without a later written consent; the request above does not ask for
  that. Otherwise only categories and counts are reported.
- **In the results** the physician's answers are called "reference labels", not "ground truth".

## Deviations

Any change after the author's signature is listed in the results as a deviation: what changed, when, and why.
With none, the results say so.
