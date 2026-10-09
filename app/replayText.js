/**
 * Every text that Replay shows once the recording is in this page, and the small pure functions that read the
 * recording and pick a text by state. An endpoint's answer and the gate's verdicts are shown with Live's texts
 * (liveText.js); the texts Replay shows before the recording is in this page are there too.
 *
 * The recording is replay_recording.json, written by the replay session (docs/replay_set.md):
 *   session  {start_utc, end_utc, image ("sha256:…"), verify_all_passed: true}
 *   part_a   12 × {n, index, third ("short" | "middle" | "long"), input, cut_at_512,
 *                  attempts: 1 to 3 × {time_utc, error} or {time_utc, response (the /v1/simplify answer)},
 *                  added_content (the author's full read of the rewrite: {found: false} | {found: true, what},
 *                  what without a final period; null only for a case not recorded)}
 *   part_b   16 × {n, idx, condition ("corrupted" | "clean"), cell, original, rewrite,
 *                  committed {llama_verdict, qwen_verdict, nemotron_verdict, consensus},
 *                  recorded {time_utc, llama_verdict, qwen_verdict, nemotron_verdict, consensus}}
 */
import { CONSENSUS, judgeList, readSimplify } from "./liveText.js";

export const ASCLEPIUS_URL = "https://huggingface.co/datasets/starmpcc/Asclepius-Synthetic-Clinical-Notes";
export const THIRDS = ["short", "middle", "long"];
export const CELLS = ["drop caught", "drop missed", "control falsely flagged", "control correctly passed"];

export const RT = {
  // the view
  introBefore: "These 28 cases were chosen by ",
  introLink: "a rule fixed before the recording",
  introAfter: ", and each was recorded once, on the final endpoint image.",
  recorded: (s) =>
    `Recorded on ${s.date}, ${s.start}–${s.end} UTC, in one session on the endpoint image ${s.image}, after the ` +
    "endpoint passed scripts/verify_endpoint.py --all.",
  partsA:
    "Part A: 12 texts, each sent to the endpoint with Live's request (flag mode, max_tokens 1,024) and shown with " +
    "the endpoint's full answer, whatever the gate said. A call with no usable answer (a connection error, no " +
    "answer within 600 seconds, an answer that could not be read or an HTTP status other than 200) was repeated " +
    "up to twice; the case says when.",
  partsB:
    "Part B: 16 known-answer pairs, each scored once by the safety gate alone, with the recorded verdict beside the " +
    "committed one. The endpoint takes a text to rewrite, not a pair, so the gate was called directly, in a " +
    "container of the same image.",
  sourcesBefore: "The source notes are synthetic (",
  sourcesLink: "Asclepius",
  sourcesAfter: ", CC-BY-NC-SA-4.0); every text here derives from them.",
  unreadableAll: "The recording in this page could not be read.",
  unreadableCase: "This case's recording could not be read.",

  // Part A
  partA: "Part A — 12 texts, rewritten and checked end to end",
  partAWhy:
    "The gate checks for dropped content, not added content, so the author also read each rewrite in full against " +
    "its input for added content: a statement about the patient or their care that the input does not contain. " +
    "Explaining a term the input uses does not count.",
  thirdGroup: { short: "Short inputs", middle: "Middle-length inputs", long: "Long inputs" },
  thirdWord: { short: "short", middle: "middle-length", long: "long" },
  notRecordedShort: "Not recorded",
  caseLabel: (c) =>
    `A${c.n} · input #${c.index} · ${RT.thirdWord[c.third]} input` + (c.time ? ` · recorded ${c.time} UTC` : ""),
  inputLabel: "The input",
  secondAttempt: (e1) => `Recorded at the second attempt: the first gave no usable answer (${e1}).`,
  thirdAttempt: (e1, e2) => `Recorded at the third attempt: the first two gave no usable answer (${e1}; ${e2}).`,
  notRecorded: (last) =>
    `Not recorded: the endpoint gave no usable answer in three attempts (the last: ${last}). The case is not replaced.`,
  endpointTook: (ms) => `The endpoint took ${(ms / 1000).toFixed(1)} s.`,
  cut512:
    "The published evaluation's output for this input stopped at its 512-token cap; this recording allowed 1,024.",
  errorShown: "An ERROR verdict is shown as recorded; it was not repeated.",
  addedNone: "The author read the rewrite in full against the input and found no added content.",
  addedFound: (what) => `The author read the rewrite in full against the input and found added content: ${what}.`,

  // Part B
  partB: "Part B — 16 known-answer pairs, scored by the gate alone",
  referenceRewrite:
    "A reference rewrite is a note rewritten in plain language by Claude Opus 4.5 for Project v1's dataset.",
  rates: "In the committed run the gate flagged 110 of the 120 drops and falsely flagged 58 of the 120 controls.",
  runs:
    "Verdicts can differ between runs: Qwen judged the same 240 items a second time, and its verdict differed from " +
    "the committed run on 41 of them. That second run was made to check the gate's verdict parser, and both " +
    "parsers read every reply alike, so the differences are between runs, not between parsers. With the other " +
    "judges' verdicts as committed, the gate would have flagged 111 of the 120 drops and 59 of the 120 controls " +
    "instead of 110 and 58.",
  noExplanation: "Part B is scored by the gate alone, so it has no explanation.",
  cellGroup: {
    "drop caught": "Drops the gate caught",
    "drop missed": "Drops the gate missed",
    "control falsely flagged": "Controls the gate falsely flagged",
    "control correctly passed": "Controls the gate correctly passed",
  },
  pairLabel: (p) =>
    `B${p.n} · pair ${p.idx}, ${p.condition === "corrupted" ? "a drop" : "a control"} · drawn from: ${p.cell}`,
  kindDrop:
    "A drop: the reference rewrite with its primary diagnosis removed; the author verified the removal by hand.",
  kindControl: "A control: the reference rewrite, unedited.",
  originalLabel: "The original",
  recordedVerdict: (time) => `Recorded verdict · ${time} UTC`,
  committedVerdict: "Committed verdict · results/judgebench_v2_panel_gate.json",
  same: "The recorded verdict is the same as the committed one.",
  differs: (committed, recorded) =>
    `The recorded verdict differs from the committed one: ${committed} committed, ${recorded} recorded.`,
  staysInCell: "The pair stays in the cell it was drawn from, whatever its recorded verdict.",
};

const isText = (x) => typeof x === "string" && x.length > 0;
const UTC = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/;
const clock = (iso) => (isText(iso) && UTC.test(iso) ? iso.slice(11, 19) : null);

/** Which line, if any, says how a recorded answer was reached (the errors of the attempts before it). */
export function attemptLine(errors) {
  if (errors.length === 1) return RT.secondAttempt(errors[0]);
  if (errors.length === 2) return RT.thirdAttempt(errors[0], errors[1]);
  return null;
}

/** The line on the author's full read for added content, or null when the recording holds no read for the case. */
export function addedLine(a) {
  if (!a || typeof a !== "object") return null;
  if (a.found === false) return RT.addedNone;
  if (a.found === true && isText(a.what)) return RT.addedFound(a.what);
  return null;
}

/** The agreement line under a Part B pair's two verdicts. */
export function agreementLine(committed, recorded) {
  return committed === recorded ? RT.same : RT.differs(committed, recorded);
}

function readCase(c) {
  const base = { part: "A", n: c.n, index: c.index, third: c.third, input: c.input };
  const errors = [];
  for (const a of c.attempts) {
    if (a && a.response && typeof a.response === "object") {
      const result = readSimplify(a.response);
      const time = clock(a.time_utc);
      if (!result || !time) return { ...base, ok: false };
      return {
        ...base,
        ok: true,
        time,
        errors,
        result,
        cut512: c.cut_at_512 === true,
        added: addedLine(c.added_content),
      };
    }
    errors.push(a && isText(a.error) ? a.error : "?");
  }
  return errors.length === 3 ? { ...base, ok: true, notRecorded: true, last: errors[2] } : { ...base, ok: false };
}

function readVerdict(v, withTime) {
  if (!v || typeof v !== "object" || !CONSENSUS.includes(v.consensus)) return null;
  const time = withTime ? clock(v.time_utc) : null;
  if (withTime && !time) return null;
  return { consensus: v.consensus, judges: judgeList(v), time };
}

function readPair(p) {
  const base = { part: "B", n: p.n, idx: p.idx, condition: p.condition, cell: p.cell };
  const committed = readVerdict(p.committed, false);
  const recorded = readVerdict(p.recorded, true);
  if (!isText(p.original) || !isText(p.rewrite) || !committed || !recorded) return { ...base, ok: false };
  return { ...base, ok: true, original: p.original, rewrite: p.rewrite, committed, recorded };
}

const four = (items, key, values) => values.every((v) => items.filter((x) => x[key] === v).length === 4);

/**
 * The recording as Replay shows it, or null when it does not hold the rule's 28 cases (12 in Part A, four per third;
 * 16 in Part B, four per cell) or the session's details, or when a recorded Part A case has no line on the author's
 * full read (the Part A heading says the author read each rewrite in full). A case whose content cannot be read keeps
 * its place and says so.
 */
export function readRecording(raw) {
  if (!raw || typeof raw !== "object") return null;
  const s = raw.session;
  if (!s || !clock(s.start_utc) || !clock(s.end_utc) || !isText(s.image) || s.verify_all_passed !== true) return null;
  const a = raw.part_a;
  const b = raw.part_b;
  if (!Array.isArray(a) || !Array.isArray(b) || a.length !== 12 || b.length !== 16) return null;
  const caseOk = (c) =>
    c && Number.isInteger(c.n) && Number.isInteger(c.index) && THIRDS.includes(c.third) && isText(c.input) &&
    Array.isArray(c.attempts) && c.attempts.length >= 1 && c.attempts.length <= 3;
  const pairOk = (p) =>
    p && Number.isInteger(p.n) && isText(p.idx) && (p.condition === "corrupted" || p.condition === "clean") &&
    CELLS.includes(p.cell);
  if (!a.every(caseOk) || !b.every(pairOk) || !four(a, "third", THIRDS) || !four(b, "cell", CELLS)) return null;
  const byN = (x, y) => x.n - y.n;
  const partA = a.map(readCase).sort(byN);
  if (partA.some((c) => c.ok && !c.notRecorded && !c.added)) return null;
  return {
    session: {
      date: s.start_utc.slice(0, 10),
      start: s.start_utc.slice(11, 16),
      end: s.end_utc.slice(11, 16),
      image: s.image,
    },
    partA,
    partB: b.map(readPair).sort(byN),
  };
}

/** The verdict a case's button shows: the consensus, "Not recorded", or nothing for a case that cannot be read. */
export function chipVerdict(item) {
  if (!item.ok) return null;
  if (item.part === "A") return item.notRecorded ? RT.notRecordedShort : item.result.consensus;
  return item.recorded.consensus;
}
