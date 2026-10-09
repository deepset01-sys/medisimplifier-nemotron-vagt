/**
 * Live mode: sends the visitor's text to the Safe Endpoint URL they enter, straight from the browser, with the replay
 * rule's request (the text, max_tokens 1,024, flag mode), and shows the safety gate's verdict, the rewrite and, for a
 * flagged rewrite, the endpoint's explanation in its own words. The URL stays in this component's state only (not
 * saved, not in the address bar). A request gives up after CEILING_S, and the visitor can cancel it while waiting.
 * Every text it shows is in liveText.js. Replay (replay.jsx) shows a recorded answer with Result, and verdicts with
 * Judges and Banner.
 */
import React, { useEffect, useRef, useState } from "react";
import {
  CEILING_S,
  HEALTH_TIMEOUT_S,
  MAX_TOKENS,
  T,
  describeHttp,
  explanationView,
  healthView,
  normalizeEndpoint,
  readSimplify,
  waitLine,
} from "./liveText.js";

const oneDecimal = (ms) => (ms / 1000).toFixed(1);

async function readJson(res) {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

/** The three judges' verdicts as chips (Replay shows its verdicts with these too). */
export function Judges({ judges }) {
  return (
    <div className="ms-chips">
      {judges.map((j) => {
        const kind = j.verdict === "SAFE" ? "safe" : j.verdict === "UNSAFE" ? "unsafe" : "error";
        return (
          <span className={"ms-chip " + kind} key={j.name}>
            <span className="dot" />
            <span className="who">
              {j.name}
              <span className="role"> · {j.role}</span>
            </span>
            <span className="vd">{j.verdict || "—"}</span>
          </span>
        );
      })}
    </div>
  );
}

/** The gate's consensus and its line, with the endpoint's warning when there is one. */
export function Banner({ consensus, warning }) {
  const verdict = T.verdict[consensus];
  return (
    <div className={"ms-banner " + consensus.toLowerCase()}>
      <div>
        <div className="b-title">{verdict.title}</div>
        <div className="b-body">{verdict.body}</div>
        {warning && <div className="b-body">{T.warning(warning)}</div>}
      </div>
    </div>
  );
}

/** An endpoint's answer: the gate's verdict, the rewrite, the explanation of a flag, and a line on the times. */
export function Result({ result, timesLine }) {
  const explanation = explanationView(result.consensus, result.explanation);
  return (
    <div className="ms-lv-result">
      <section className="ms-gate">
        <div className="ms-gate-label">{T.gateLabel}</div>
        <Judges judges={result.judges} />
        <Banner consensus={result.consensus} warning={result.warning} />
        <p className="ms-lv-hint">{T.gateNotes}</p>
      </section>

      <div className="ms-lv-sub">{T.rewriteLabel}</div>
      <p className="ms-lv-rewrite">
        {result.blocked ? T.withheld : result.rewrite != null ? result.rewrite : T.noRewrite}
      </p>
      {result.truncated && (
        <p className="ms-lv-hint">
          {T.truncated}
          {result.consensus === "SAFE" && " " + T.truncatedSafe}
        </p>
      )}

      {explanation && (
        <div className="ms-lv-explain">
          <h5>{T.explainLabel}</h5>
          {explanation.none ? (
            <p>{explanation.none}</p>
          ) : (
            <>
              <p>{explanation.note}</p>
              {explanation.quotes.length > 0 && (
                <ul>
                  {explanation.quotes.map((q, i) => (
                    <li key={i}>“{q}”</li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
      )}

      {timesLine && <p className="ms-lv-times">{timesLine}</p>}
    </div>
  );
}

export default function Live({ text, setText, reproUrl }) {
  const [url, setUrl] = useState("");
  const [health, setHealth] = useState({ status: "idle" });
  const [run, setRun] = useState({ status: "idle" });
  const [elapsed, setElapsed] = useState(0);
  const pending = useRef(null);
  const started = useRef(0);

  const waiting = run.status === "waiting";
  useEffect(() => {
    if (!waiting) return undefined;
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - started.current) / 1000)), 1000);
    return () => clearInterval(id);
  }, [waiting]);
  // Leaving Live (switching to Replay) stops a pending wait in this page.
  useEffect(() => () => pending.current && pending.current.abort("cancel"), []);

  const endpoint = normalizeEndpoint(url);
  const missing = !url.trim() ? T.needUrl : !endpoint.ok ? endpoint.error : !text.trim() ? T.needText : null;

  async function check() {
    if (!endpoint.ok) return;
    setHealth({ status: "checking" });
    const c = new AbortController();
    const timer = setTimeout(() => c.abort("timeout"), HEALTH_TIMEOUT_S * 1000);
    try {
      const res = await fetch(endpoint.base + "/health", { signal: c.signal });
      const body = await readJson(res);
      setHealth(
        res.ok
          ? { status: "done", ...healthView(body) }
          : { status: "done", ok: false, lines: [describeHttp(res.status, body)] },
      );
    } catch {
      const line = c.signal.reason === "timeout" ? T.healthTimeout : T.unreachable;
      setHealth({ status: "done", ok: false, lines: [line] });
    } finally {
      clearTimeout(timer);
    }
  }

  async function simplify() {
    if (missing || waiting) return;
    const c = new AbortController();
    pending.current = c;
    started.current = Date.now();
    setElapsed(0);
    setRun({ status: "waiting" });
    const timer = setTimeout(() => c.abort("ceiling"), CEILING_S * 1000);
    try {
      const res = await fetch(endpoint.base + "/v1/simplify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, max_tokens: MAX_TOKENS, safety_mode: "flag" }),
        signal: c.signal,
      });
      const body = await readJson(res);
      const pageMs = Date.now() - started.current;
      if (!res.ok) {
        setRun({ status: "failed", message: describeHttp(res.status, body) });
        return;
      }
      const result = readSimplify(body);
      setRun(result ? { status: "done", result, pageMs } : { status: "failed", message: T.unreadable });
    } catch {
      const why = c.signal.reason;
      if (why === "cancel") setRun({ status: "cancelled" });
      else setRun({ status: "failed", message: why === "ceiling" ? T.ceiling : T.unreachable });
    } finally {
      clearTimeout(timer);
      if (pending.current === c) pending.current = null;
    }
  }

  return (
    <section className="ms-lv" role="tabpanel">
      <p className="ms-lv-intro">{T.liveIntro}</p>
      <p className="ms-lv-hint">
        {T.needEndpointBefore}
        <a href={reproUrl} target="_blank" rel="noopener noreferrer">
          {T.needEndpointLink}
        </a>
        {T.needEndpointAfter}
      </p>

      <label className="ms-lv-label" htmlFor="ms-lv-url">
        {T.urlLabel}
      </label>
      <input
        id="ms-lv-url"
        className="ms-lv-input"
        type="url"
        inputMode="url"
        autoComplete="off"
        spellCheck={false}
        placeholder={T.urlPlaceholder}
        value={url}
        onChange={(e) => {
          setUrl(e.target.value);
          setHealth({ status: "idle" });
        }}
      />
      <p className="ms-lv-hint">{T.urlHint}</p>
      <div className="ms-lv-row">
        <button className="ms-retry" onClick={check} disabled={!endpoint.ok || health.status === "checking"}>
          {T.checkButton}
        </button>
        {health.status === "checking" && <span className="ms-lv-status">{T.checking}</span>}
      </div>
      {health.status === "done" && (
        <div className={"ms-lv-status " + (health.ok ? "ok" : "bad")} role="status">
          {health.lines.map((line, i) => (
            <div key={i}>{line}</div>
          ))}
        </div>
      )}

      <label className="ms-lv-label" htmlFor="ms-lv-text">
        {T.textLabel}
      </label>
      <textarea
        id="ms-lv-text"
        className="ms-lv-text"
        placeholder={T.textPlaceholder}
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div className="ms-lv-row">
        <button className="ms-runbtn" onClick={simplify} disabled={Boolean(missing) || waiting}>
          {T.simplifyButton}
        </button>
        {missing && !waiting && <span className="ms-lv-hint">{missing}</span>}
      </div>
      <p className="ms-lv-hint">{T.flagMode}</p>
      <p className="ms-lv-notice">{T.sentNotAdvice}</p>

      <div aria-live="polite">
        {waiting && (
          <div className="ms-lv-wait">
            <span className="ms-lv-timer">{T.seconds(elapsed)}</span>
            <span>{waitLine(elapsed)}</span>
            <button className="ms-retry" onClick={() => pending.current && pending.current.abort("cancel")}>
              {T.cancelButton}
            </button>
          </div>
        )}
        {run.status === "failed" && (
          <div className="ms-live-error">
            <span>{run.message}</span>
          </div>
        )}
        {run.status === "cancelled" && <div className="ms-lv-status">{T.cancelled}</div>}
        {run.status === "done" && (
          <Result
            result={run.result}
            timesLine={T.times(
              run.result.endpointMs != null ? oneDecimal(run.result.endpointMs) : null,
              oneDecimal(run.pageMs),
            )}
          />
        )}
      </div>
    </section>
  );
}
