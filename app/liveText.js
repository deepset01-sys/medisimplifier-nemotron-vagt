/**
 * Every text that Live mode and the mode switch display, and the small pure functions that pick one by state. They
 * are kept apart from the components so that all of this wording sits in one place and can be checked without a
 * browser. The times in the wait lines come from a running endpoint (October 2026): discharge summaries of about 1,000
 * characters took 16 to 29 seconds, flagged ones included, and the lines allow a margin. Replay shows an endpoint's
 * answer and the gate's verdicts with these same texts (replayText.js holds the rest of Replay's).
 */

export const CEILING_S = 300; // a simplify request gives up after 5 minutes
export const HEALTH_TIMEOUT_S = 20;
export const MAX_TOKENS = 1024; // the replay rule's request: the text, max_tokens 1,024 and flag mode

const num = (n) => Number(n).toLocaleString("en-US"); // 4096 → "4,096", as the README writes it

export const T = {
  // mode switch and Replay (until the recording is in this page)
  modesLabel: "Mode",
  replayTab: "Replay",
  liveTab: "Live",
  replayNotYet:
    "Replay shows 28 cases recorded once on the final endpoint image: 12 texts rewritten and checked end to end, " +
    "and 16 known-answer pairs scored by the safety gate. They are not in this version of the page yet.",
  replayPaste: "Pasted text is never processed here: pasting switches to Live.",
  notAdvice: "This is not medical advice.",
  tryLive: "Try Live →",

  // Live: the form
  liveIntro: "Live sends a text to a running Safe Endpoint, straight from your browser, and shows what it returns.",
  needEndpointBefore: "New text needs a running endpoint. Enter its URL below, or deploy your own with the ",
  needEndpointLink: "reproduction guide",
  needEndpointAfter: ".",
  onRequestBefore:
    "This project's Safe Endpoint and its two judge endpoints are not kept running between demos: together they " +
    "cost about $14 an hour. To try Live on them at no cost to you, write to ",
  onRequestAddress: "deepset01@gmail.com",
  onRequestAfter:
    " with the time you plan to look. They are started for your session and take about 8 to 10 minutes to load; " +
    "you then get an endpoint address to paste below. That endpoint has no authentication, so use synthetic " +
    "text only.",
  onRequestSubject: "MediSimplifier Live session",
  onRequestBody: "The time I plan to look (with my time zone): ",
  urlLabel: "Endpoint URL",
  urlPlaceholder: "https://…",
  urlHint: "Kept in this page only: not saved, and not added to the address bar.",
  textLabel: "Text to simplify",
  textPlaceholder: "Paste a discharge summary or another medical text…",
  checkButton: "Check endpoint",
  simplifyButton: "Simplify and check →",
  cancelButton: "Cancel",
  flagMode: "Live uses flag mode: the rewrite is never withheld, and the gate's verdict is shown beside it.",
  sentNotAdvice: "Your text is sent to the endpoint URL you entered. This is not medical advice.",
  needUrl: "Enter the endpoint's URL first.",
  badUrl: "The URL must start with https:// (or http:// for an endpoint on this computer).",
  needText: "Paste a text first.",

  // Live: Check endpoint (GET /health)
  checking: "Checking the endpoint…",
  healthReady: "Ready: the model is loaded and the judges' API key is set. This check does not call the judges.",
  healthNoModel: "Not ready: the model is not loaded yet. A starting endpoint needs several minutes.",
  healthNoKey: "Not ready: the endpoint has no NEBIUS_API_KEY, so the judges cannot be called.",
  healthNotReady: "Not ready, by the endpoint's own report.",
  healthKeyUnset: (name) =>
    `${name} is not set on this endpoint, so the gate uses this project's own routing key, which belongs to this ` +
    "project's account.",
  healthTimeout: `The endpoint did not answer within ${HEALTH_TIMEOUT_S} seconds.`,

  // Live: waiting, giving up, failures
  wait0:
    "Rewriting and checking with three judges. This usually takes under 30 seconds, or under 45 when the rewrite " +
    "is flagged and the endpoint adds its explanation.",
  wait45: "Still working. A longer text takes longer to rewrite and check.",
  wait90: "Still working. A cold start, or a judge endpoint that is still starting, can take several minutes.",
  seconds: (n) => `${n} s`,
  ceiling: "No answer after 5 minutes. The endpoint may be stopped, still starting or busy. Check it and try again.",
  cancelled: "Cancelled. The endpoint may still finish this request on its side.",
  unreachable:
    "This page could not reach the endpoint. Check the URL. The endpoint must be running, and it must allow this " +
    "page (it does by default).",
  unreadable: "The endpoint's answer could not be read.",
  http413: (d) =>
    `The text is too long for the endpoint: ${num(d.prompt_tokens)} prompt tokens plus ${num(d.max_tokens)} for the ` +
    `rewrite exceed its ${num(d.context_window)}-token window.`,
  http413Plain: "The text is too long for the endpoint.",
  http422: "The endpoint rejected the request as invalid.",
  http503: (detail) => `The endpoint's model server failed: ${detail}`,
  http503Plain: "The endpoint's model server failed.",
  httpOther: (status, detail) => `The endpoint answered HTTP ${status}` + (detail ? `: ${detail}` : "."),

  // Live: the result
  gateLabel: "Safety gate — three LLM judges",
  roleAdvisory: "advisory",
  roleDecides: "decides",
  verdict: {
    SAFE: { title: "SAFE", body: "Qwen and Nemotron both judged the rewrite safe." },
    UNSAFE: { title: "UNSAFE", body: "Qwen judged the rewrite unsafe, which flags it whatever Nemotron says." },
    DISAGREE: {
      title: "DISAGREE",
      body: "Nemotron judged the rewrite unsafe and Qwen judged it safe, so the gate flags it.",
    },
    ERROR: {
      title: "ERROR",
      body: "A Qwen or Nemotron call failed, or its reply could not be read, so the gate gives no verdict.",
    },
  },
  warning: (w) => `Warning from the endpoint: ${w}`,
  gateNotes:
    "Llama's verdict is shown but does not enter the gate's rule. The gate checks the rewrite for dropped content, " +
    "not for added content.",
  rewriteLabel: "The rewrite",
  truncated: `The rewrite stopped at its ${num(MAX_TOKENS)}-token limit, so it is incomplete.`,
  truncatedSafe: "The gate judged the rewrite as returned.",
  withheld: "The endpoint withheld the rewrite.",
  noRewrite: "The endpoint returned no rewrite.",
  explainLabel: "Explanation from the endpoint (advisory)",
  noExplanation: "The endpoint gave no explanation for this flag.",
  times: (endpointS, pageS) =>
    endpointS != null
      ? `The endpoint took ${endpointS} s; the whole wait in this page was ${pageS} s.`
      : `The whole wait in this page was ${pageS} s.`,
};

export const CONSENSUS = ["SAFE", "UNSAFE", "DISAGREE", "ERROR"];

/** The three judges in display order, from an object with llama_verdict, qwen_verdict and nemotron_verdict. */
export function judgeList(s) {
  const v = (x) => (typeof x === "string" ? x : "");
  return [
    { name: "Llama-3.3-70B", role: T.roleAdvisory, verdict: v(s.llama_verdict) },
    { name: "Qwen3-32B", role: T.roleDecides, verdict: v(s.qwen_verdict) },
    { name: "Nemotron Nano", role: T.roleDecides, verdict: v(s.nemotron_verdict) },
  ];
}

/** The line shown while waiting, by elapsed seconds. */
export function waitLine(seconds) {
  return seconds >= 90 ? T.wait90 : seconds >= 45 ? T.wait45 : T.wait0;
}

/** The mailto link that asks for the project's endpoints to be started for a session. */
export function requestMailto() {
  const q = "subject=" + encodeURIComponent(T.onRequestSubject) + "&body=" + encodeURIComponent(T.onRequestBody);
  return "mailto:" + T.onRequestAddress + "?" + q;
}

/** The endpoint's base URL from what the visitor typed: http(s) only; a pasted /v1/simplify or /health is dropped. */
export function normalizeEndpoint(raw) {
  const s = (raw || "").trim();
  if (!s) return { ok: false, error: T.needUrl };
  let u;
  try {
    u = new URL(s);
  } catch {
    return { ok: false, error: T.badUrl };
  }
  if (u.protocol !== "https:" && u.protocol !== "http:") return { ok: false, error: T.badUrl };
  const path = u.pathname.replace(/\/+$/, "").replace(/\/(v1\/simplify|health)$/, "");
  return { ok: true, base: u.origin + path };
}

/** The message for an HTTP error from the endpoint, from its status and its JSON body (if any). */
export function describeHttp(status, body) {
  const d = body && typeof body === "object" ? body.detail : undefined;
  if (status === 413) return d && typeof d === "object" && d.prompt_tokens != null ? T.http413(d) : T.http413Plain;
  if (status === 422) return T.http422;
  if (status === 503) return typeof d === "string" && d ? T.http503(d) : T.http503Plain;
  return T.httpOther(status, typeof d === "string" ? d : "");
}

/** What /v1/simplify returned, in the shape the page shows; null when it cannot be read. */
export function readSimplify(b) {
  if (!b || typeof b !== "object" || !b.safety || typeof b.safety !== "object") return null;
  const s = b.safety;
  if (!CONSENSUS.includes(s.consensus)) return null;
  return {
    consensus: s.consensus,
    judges: judgeList(s),
    warning: typeof s.warning === "string" && s.warning ? s.warning : null,
    blocked: b.blocked === true || s.blocked === true,
    rewrite: typeof b.simplified_text === "string" ? b.simplified_text : null,
    truncated: b.truncated === true,
    explanation: b.explanation && typeof b.explanation === "object" ? b.explanation : null,
    endpointMs: b.latency_ms && typeof b.latency_ms.total_ms === "number" ? b.latency_ms.total_ms : null,
  };
}

/**
 * The explanation block: none for SAFE or ERROR; for a flagged verdict (UNSAFE or DISAGREE) the endpoint's note in
 * its own words, with its quotes when it lists possible omissions, or one line when the endpoint gave none.
 */
export function explanationView(consensus, ex) {
  if (consensus !== "UNSAFE" && consensus !== "DISAGREE") return null;
  if (!ex || typeof ex.note !== "string" || !ex.note) return { none: T.noExplanation };
  const quotes =
    ex.status === "possible_omissions" && Array.isArray(ex.possible_omissions)
      ? ex.possible_omissions.map((q) => q && q.source_quote).filter((q) => typeof q === "string" && q)
      : [];
  return { note: ex.note, quotes };
}

/** What Check endpoint shows, from the /health body. */
export function healthView(h) {
  if (!h || typeof h !== "object" || typeof h.ready !== "boolean") return { ok: false, lines: [T.unreadable] };
  const set = h.judge_models_set && typeof h.judge_models_set === "object" ? h.judge_models_set : {};
  const unset = [
    ["qwen", "QWEN_JUDGE_MODEL"],
    ["llama", "LLAMA_JUDGE_MODEL"],
  ]
    .filter(([k]) => set[k] === false)
    .map(([, name]) => T.healthKeyUnset(name));
  if (h.ready) return { ok: unset.length === 0, lines: [T.healthReady, ...unset] }; // a key not set: amber
  if (h.vllm === false) return { ok: false, lines: [T.healthNoModel, ...unset] };
  if (h.token_factory === false) return { ok: false, lines: [T.healthNoKey, ...unset] };
  return { ok: false, lines: [T.healthNotReady, ...unset] };
}
