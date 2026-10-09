/**
 * Replay mode: the 28 cases of docs/replay_set.md as recorded once on the final endpoint image — Part A, 12 texts
 * rewritten and checked end to end; Part B, 16 known-answer pairs scored by the safety gate alone — read from
 * replay_recording.json when that file is in this page. Replay sends nothing: it shows what the recording holds, an
 * endpoint's answer and the gate's verdicts as Live shows them. Every text it shows is in replayText.js or, where it
 * is Live's, in liveText.js.
 */
import React, { useMemo, useState } from "react";
import { Banner, Judges, Result } from "./live.jsx";
import { CONSENSUS, T } from "./liveText.js";
import {
  ASCLEPIUS_URL,
  CELLS,
  RT,
  THIRDS,
  agreementLine,
  attemptLine,
  chipVerdict,
  readRecording,
} from "./replayText.js";

// The recording, once it is committed next to this file; until then the glob finds nothing and Replay says so.
const FOUND = import.meta.glob("./replay_recording.json", { eager: true, import: "default" });
const RECORDING = FOUND["./replay_recording.json"] || null;

function Chip({ item, on, onSelect }) {
  const v = chipVerdict(item);
  return (
    <button className={"ms-rp-chip" + (on ? " on" : "")} aria-pressed={on} onClick={onSelect}>
      {item.part + item.n}
      {v && <span className={"ms-rp-v " + (CONSENSUS.includes(v) ? "v-" + v : "v-none")}>{v}</span>}
    </button>
  );
}

function Groups({ items, field, order, labels, selected, onSelect }) {
  return order.map((key) => (
    <div className="ms-rp-group" key={key}>
      <h4>{labels[key]}</h4>
      <div className="ms-rp-chips">
        {items
          .filter((x) => x[field] === key)
          .map((x) => (
            <Chip key={x.n} item={x} on={x.n === selected} onSelect={() => onSelect(x.n)} />
          ))}
      </div>
    </div>
  ));
}

function CaseA({ c }) {
  const attempts = c.ok && !c.notRecorded ? attemptLine(c.errors) : null;
  return (
    <div className="ms-rp-case">
      <div className="ms-rp-label">{RT.caseLabel(c)}</div>
      {!c.ok ? (
        <p className="ms-rp-note">{RT.unreadableCase}</p>
      ) : (
        <>
          {attempts && <p className="ms-rp-note">{attempts}</p>}
          <div className="ms-lv-sub">{RT.inputLabel}</div>
          <p className="ms-rp-text">{c.input}</p>
          {c.notRecorded ? (
            <p className="ms-rp-note">{RT.notRecorded(c.last)}</p>
          ) : (
            <>
              <Result
                result={c.result}
                timesLine={c.result.endpointMs != null ? RT.endpointTook(c.result.endpointMs) : null}
              />
              {c.result.consensus === "ERROR" && <p className="ms-rp-note">{RT.errorShown}</p>}
              {c.cut512 && <p className="ms-lv-hint">{RT.cut512}</p>}
              <p className="ms-lv-hint">{c.added}</p>
            </>
          )}
        </>
      )}
    </div>
  );
}

function Verdict({ label, v }) {
  return (
    <div>
      <div className="ms-rp-vlabel">{label}</div>
      <Judges judges={v.judges} />
      <Banner consensus={v.consensus} />
    </div>
  );
}

function PairB({ p }) {
  if (!p.ok) {
    return (
      <div className="ms-rp-case">
        <div className="ms-rp-label">{RT.pairLabel(p)}</div>
        <p className="ms-rp-note">{RT.unreadableCase}</p>
      </div>
    );
  }
  return (
    <div className="ms-rp-case">
      <div className="ms-rp-label">{RT.pairLabel(p)}</div>
      <p className="ms-rp-note">{p.condition === "corrupted" ? RT.kindDrop : RT.kindControl}</p>
      <div className="ms-lv-sub">{RT.originalLabel}</div>
      <p className="ms-rp-text">{p.original}</p>
      <div className="ms-lv-sub">{T.rewriteLabel}</div>
      <p className="ms-rp-text">{p.rewrite}</p>
      <section className="ms-gate">
        <div className="ms-gate-label">{T.gateLabel}</div>
        <div className="ms-rp-verdicts">
          <Verdict label={RT.recordedVerdict(p.recorded.time)} v={p.recorded} />
          <Verdict label={RT.committedVerdict} v={p.committed} />
        </div>
        <p className="ms-rp-note">{agreementLine(p.committed.consensus, p.recorded.consensus)}</p>
        {p.recorded.consensus === "ERROR" && <p className="ms-rp-note">{RT.errorShown}</p>}
        <p className="ms-lv-hint">{RT.staysInCell}</p>
        <p className="ms-lv-hint">{T.gateNotes}</p>
      </section>
    </div>
  );
}

export default function Replay({ ruleUrl, onTryLive, recording = RECORDING }) {
  const view = useMemo(() => (recording ? readRecording(recording) : null), [recording]);
  const [selA, setSelA] = useState(1);
  const [selB, setSelB] = useState(1);
  const tryLive = (
    <button className="ms-runbtn" onClick={onTryLive}>
      {T.tryLive}
    </button>
  );

  if (!view) {
    return (
      <section className="ms-replay" role="tabpanel">
        <p className="ms-replay-text">{recording ? RT.unreadableAll : T.replayNotYet}</p>
        <p className="ms-replay-text">{T.replayPaste}</p>
        <p className="ms-lv-notice">{T.notAdvice}</p>
        {tryLive}
      </section>
    );
  }

  const caseA = view.partA.find((c) => c.n === selA) || view.partA[0];
  const pairB = view.partB.find((p) => p.n === selB) || view.partB[0];
  return (
    <section className="ms-replay" role="tabpanel">
      <p className="ms-replay-text">
        {RT.introBefore}
        <a href={ruleUrl} target="_blank" rel="noopener noreferrer">
          {RT.introLink}
        </a>
        {RT.introAfter}
      </p>
      <p className="ms-rp-meta">{RT.recorded(view.session)}</p>
      <p className="ms-replay-text">{RT.partsA}</p>
      <p className="ms-replay-text">{RT.partsB}</p>
      <p className="ms-rp-meta">
        {RT.sourcesBefore}
        <a href={ASCLEPIUS_URL} target="_blank" rel="noopener noreferrer">
          {RT.sourcesLink}
        </a>
        {RT.sourcesAfter}
      </p>
      <p className="ms-replay-text">{T.replayPaste}</p>
      <p className="ms-lv-notice">{T.notAdvice}</p>

      <div className="ms-rp-part">
        <h3>{RT.partA}</h3>
        <p className="ms-rp-about">{RT.partAWhy}</p>
        <Groups
          items={view.partA}
          field="third"
          order={THIRDS}
          labels={RT.thirdGroup}
          selected={caseA.n}
          onSelect={setSelA}
        />
        <CaseA c={caseA} />
      </div>

      <div className="ms-rp-part">
        <h3>{RT.partB}</h3>
        <p className="ms-rp-about">{RT.referenceRewrite}</p>
        <p className="ms-rp-about">{RT.rates}</p>
        <p className="ms-rp-about">{RT.runs}</p>
        <p className="ms-rp-about">{RT.noExplanation}</p>
        <Groups
          items={view.partB}
          field="cell"
          order={CELLS}
          labels={RT.cellGroup}
          selected={pairB.n}
          onSelect={setSelB}
        />
        <PairB p={pairB} />
      </div>

      <div className="ms-rp-end">{tryLive}</div>
    </section>
  );
}
