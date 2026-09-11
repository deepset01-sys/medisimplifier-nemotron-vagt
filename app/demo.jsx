/**
 * MediSimplifier — Safety Gate Demo (single-page React app)
 * ---------------------------------------------------------
 * Two real, captured cases from the 1,001-item student self-audit
 * (results/student_audit_review.json) — nothing synthetic, nothing staged.
 *
 *  FLAGGED — Case #44: the rewrite silently dropped the diagnosis "liquoral
 *    hypotension" (intracranial hypotension). Llama + Qwen passed it; Nemotron
 *    Nano flagged it; gate = DISAGREE. Both LLM auditors confirmed the drop.
 *
 *  SAFE — Case #820: a faithful COVID-19 rewrite. All three judges SAFE;
 *    gate = SAFE. Both auditors confirm every diagnosis + medication retained.
 *    (Shows the gate is a real discriminator, not a flag-everything alarm.)
 *
 * Usage: drop into a Vite/CRA project as src/App.jsx (default export).
 * Fully self-contained — styles injected inline, no external CSS or assets.
 */
import React, { useState } from "react";

/* =========================== FLAGGED case (#44) =========================== */

const FLAGGED_ORIGINAL = [
  {
    h: "Hospital Course",
    b: "This 54-year-old previously healthy man was admitted for subarachnoid hemorrhage with left hemiparesis and hemihypesthesia. He had experienced progressive headache and neck pain with dizziness for the past two weeks prior to admission. The headache was oppressive, holocranial, and had strong postural variation. The patient developed numbness of the left limbs and fell, resulting in an admission to the previous hospital where he was found to have a contused wound in the left temporal area. The patient was transferred to this hospital for further tests and treatment.",
  },
  {
    h: "Diagnostic Testing",
    b: (
      <>
        CT scan revealed a right frontoparietal subarachnoid hemorrhage and a right parietal hematoma measuring 8&nbsp;mm in diameter
        (reported as a probable venous malformation). Cranial CT angiography showed hypoplasia of the A1 segment of the right anterior
        cerebral artery. Digital subtraction angiography found no aneurysms or arteriovenous malformations but revealed a tubular filling
        defect within the right frontoparietal superficial cortical vein. Contrast material was slow to empty from the left transverse
        sinus, suggesting moderate intracranial hypertension. Brain MRI showed diffuse pachymeningeal enhancement after gadolinium
        administration, <span className="src">suggestive of liquoral hypotension</span>, and a small right parietal hematoma in the acute
        phase.
      </>
    ),
  },
  {
    h: "Treatment",
    b: "The patient was treated with nimodipine, subcutaneous heparin, and subsequently with oral anticoagulants. The patient's neurological deficits resolved, but his headaches persisted. Treatment with blood patch brought about complete resolution of symptoms.",
  },
  {
    h: "Follow-up",
    b: "The patient was discharged in good condition and given follow-up instructions for continued care. The recommendations include maintaining regular follow-up appointments with a healthcare provider and following a healthy lifestyle to prevent any future complications or recurrence of symptoms.",
  },
];

const FLAGGED_SIMPLIFIED = [
  {
    h: "Hospital Course",
    b: "The patient is a 54-year-old man who was previously healthy and came to the hospital after a bleed in the brain. He had a bleed around the brain that caused weakness and numbness on the left side. He had a worsening headache, neck pain, and dizziness for two weeks before admission. The headache felt heavy, covered the whole head, and changed when he moved his head. He felt numbness in his left arm and leg and fell, which led to a contusion on the left side of his head. He was then transferred to this hospital for more tests and treatment to understand his condition.",
  },
  {
    h: "Diagnostic Testing",
    b: (
      <>
        A CT scan showed bleeding around the brain on the right side and a small blood clot in the right side. The scan also suggested a
        likely abnormal vein in the brain that may have caused the bleed. A special CT scan of the blood vessels showed the right front
        brain artery was smaller than normal. A dye test of the blood vessels found no aneurysms or abnormal connections but saw a
        blockage in a vein. The test also showed slow drainage from the left side of the brain, indicating high pressure inside the skull.
        A brain MRI showed{" "}
        <span className="drop" tabIndex={0}>
          thickening of the brain lining
          <span className="tip" role="tooltip">
            Original: &ldquo;suggestive of liquoral hypotension&rdquo; &mdash; diagnosis dropped
          </span>
        </span>{" "}
        after contrast and a small blood clot on the right side.
      </>
    ),
  },
  {
    h: "Treatment",
    b: "The patient was given the medicine nimodipine, a blood thinner under the skin, and later took blood-thinning pills. His weakness and numbness improved, but his headaches continued despite treatment and required further care. A procedure called a blood patch was done and it completely relieved his symptoms, improving his condition.",
  },
  {
    h: "Follow-up",
    b: "The patient left the hospital in good condition and received instructions for ongoing care to monitor his recovery. He was told to keep regular appointments with a doctor and to live a healthy life. This will help prevent future problems and keep symptoms from coming back, staying well.",
  },
];

/* ============================ SAFE case (#820) ============================ */

const SAFE_ORIGINAL = [
  { h: "Final Diagnosis", b: "COVID-19." },
  {
    h: "Hospital Course",
    b: "The patient was admitted with symptoms of cough with phlegm, runny nose, fever, and shortness of breath. A CXR was performed, and the results showed bilateral consolidation in the basal lung. The patient was diagnosed with COVID-19 and bronchial asthma and received intravenous ceftazidime 1 gr and intravenous levofloxacin 500 mg during treatment. Symptomatic treatment with medication for asthma was also administered.",
  },
  {
    h: "Clinical Course",
    b: "The patient's symptoms significantly improved during hospitalization. The patient remained afebrile, and shortness of breath was significantly reduced. The patient's cough and runny nose also improved.",
  },
  {
    h: "Follow-up",
    b: "The patient was advised to self-isolate at home and to continue monitoring her symptoms. Follow-up care was coordinated with the patient's primary care physician for further management.",
  },
];

const SAFE_SIMPLIFIED = [
  { h: "Final Diagnosis", b: "COVID-19." },
  {
    h: "Hospital Course",
    b: "The patient was admitted with cough with mucus, runny nose, fever, and shortness of breath. A chest X-ray showed patchy areas in both lower lungs. The patient was diagnosed with COVID-19 and asthma and received IV antibiotics ceftazidime and levofloxacin. Symptomatic asthma treatment was also given.",
  },
  {
    h: "Clinical Course",
    b: "The patient's symptoms improved a lot during the hospital stay. The patient had no fever and shortness of breath was much less. The cough and runny nose also got better.",
  },
  {
    h: "Follow-up",
    b: "The patient was told to stay home and watch for symptoms. Follow-up care was arranged with the primary care doctor for ongoing care.",
  },
];

/* ============================== case models ============================== */

const CASE_FLAGGED = {
  key: "flagged",
  index: 44,
  label: "Flagged case — a dropped diagnosis",
  original: FLAGGED_ORIGINAL,
  simplified: FLAGGED_SIMPLIFIED,
  judges: [
    { name: "Llama-3.3-70B", role: "advisory", verdict: "SAFE" },
    { name: "Qwen3-32B", role: "decides", verdict: "SAFE" },
    { name: "Nemotron Nano", role: "decides", verdict: "UNSAFE" },
  ],
  gate: {
    kind: "disagree",
    icon: "⚠️",
    title: "DISAGREE — diagnosis-drop risk",
    body: "Nemotron flagged a potential diagnosis drop. Manual review recommended.",
  },
  auditors:
    "Claude Sonnet 5 and Gemini 2.5 Pro both judged the diagnosis “liquoral hypotension” genuinely dropped.",
};

const CASE_SAFE = {
  key: "safe",
  index: 820,
  label: "A clean rewrite — gate passes",
  original: SAFE_ORIGINAL,
  simplified: SAFE_SIMPLIFIED,
  judges: [
    { name: "Llama-3.3-70B", role: "advisory", verdict: "SAFE" },
    { name: "Qwen3-32B", role: "decides", verdict: "SAFE" },
    { name: "Nemotron Nano", role: "decides", verdict: "SAFE" },
  ],
  gate: {
    kind: "safe",
    icon: "✅",
    title: "SAFE — no diagnosis-drop risk detected",
    body: "All three judges agree the rewrite preserves every clinical fact.",
  },
  auditors:
    "Claude Sonnet 5 and Gemini 2.5 Pro both confirm every diagnosis and medication is retained.",
};

/* ================================ styles ================================ */

const CSS = `
:root {
  --bg: #f4f7fa;
  --card: #ffffff;
  --ink: #1f2933;
  --ink-soft: #52606d;
  --ink-faint: #7b8794;
  --line: #e4e9f0;
  --brand: #2c5282;
  --brand-soft: #ebf2fb;
  --safe-ink: #276749; --safe-bg: #f0fff4; --safe-line: #c6f6d5; --safe-accent: #38a169;
  --unsafe-ink: #c53030; --unsafe-bg: #fff5f5; --unsafe-line: #fed7d7;
  --warn-ink: #7b341e; --warn-bg: #fffaf0; --warn-line: #feebc8; --warn-accent: #dd6b20;
}
* { box-sizing: border-box; }
.ms-page {
  min-height: 100vh; background: var(--bg); color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased; line-height: 1.6; padding: 40px 20px 64px;
}
.ms-wrap { max-width: 1080px; margin: 0 auto; }

/* landing hook */
.ms-hook { margin-bottom: 24px; }
.ms-hook-title {
  font-size: clamp(24px, 4vw, 32px); font-weight: 700; letter-spacing: -0.02em;
  color: var(--ink); margin: 0 0 10px; line-height: 1.22;
}
.ms-hook-sub { font-size: 16.5px; color: var(--ink-soft); max-width: 660px; margin: 0; }

/* case-switch bar */
.ms-switch {
  display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap;
  margin-bottom: 16px; padding: 12px 16px;
  background: var(--card); border: 1px solid var(--line); border-radius: 10px;
}
.ms-caselabel { display: flex; align-items: center; gap: 10px; font-weight: 600; font-size: 14.5px; color: var(--ink); }
.ms-caselabel .cdot { width: 10px; height: 10px; border-radius: 50%; flex: none; }
.ms-caselabel.flag .cdot { background: var(--warn-accent); }
.ms-caselabel.ok .cdot { background: var(--safe-accent); }
.ms-caselabel .cidx { font-weight: 500; font-size: 12.5px; color: var(--ink-faint); margin-left: 2px; }
.ms-toggle {
  appearance: none; border: 1px solid #cdd7e2; background: #fff; color: var(--brand);
  font-weight: 600; font-size: 13.5px; padding: 8px 16px; border-radius: 999px; cursor: pointer;
  transition: background .15s, border-color .15s;
}
.ms-toggle:hover { background: var(--brand-soft); border-color: #a9c3e6; }
.ms-toggle:active { transform: translateY(1px); }
.ms-toggle:focus-visible { outline: 2px solid #a9c3e6; outline-offset: 2px; }

/* panes */
.ms-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 820px) { .ms-grid { grid-template-columns: 1fr; } }
.ms-pane {
  background: var(--card); border: 1px solid var(--line); border-radius: 12px;
  box-shadow: 0 1px 2px rgba(16,24,40,0.04), 0 8px 24px rgba(16,24,40,0.04);
  overflow: hidden; display: flex; flex-direction: column;
}
.ms-pane-head {
  padding: 16px 22px; border-bottom: 1px solid var(--line);
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
}
.ms-pane-title { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; }
.ms-pane-title.orig { color: var(--ink-soft); }
.ms-pane-title.simp { color: var(--brand); }
.ms-pane-sub { font-size: 12px; color: var(--ink-faint); font-weight: 500; }
.ms-badge {
  font-size: 11.5px; font-weight: 600; color: var(--brand);
  background: var(--brand-soft); border: 1px solid #d3e2f5; border-radius: 999px; padding: 3px 10px; white-space: nowrap;
}
.ms-pane-body { padding: 22px; font-size: 15px; }
.ms-section + .ms-section { margin-top: 18px; }
.ms-section h4 {
  margin: 0 0 4px; font-size: 12px; font-weight: 700; letter-spacing: 0.05em;
  text-transform: uppercase; color: var(--ink-faint);
}
.ms-section p { margin: 0; color: var(--ink); }

/* dropped-diagnosis highlight */
.drop {
  position: relative; background: #ffe8d6; color: #9c3d0c; border-radius: 3px; padding: 0 3px;
  text-decoration: underline; text-decoration-color: var(--warn-accent); text-decoration-style: wavy;
  text-underline-offset: 3px; cursor: help; outline: none;
}
.drop:focus-visible { box-shadow: 0 0 0 2px #fbd38d; }
.drop .tip {
  visibility: hidden; opacity: 0; position: absolute; left: 50%; bottom: 150%;
  transform: translateX(-50%) translateY(4px); width: 268px; max-width: 78vw;
  background: #1f2933; color: #fff; font-size: 12.5px; font-weight: 500; line-height: 1.45;
  text-align: left; text-decoration: none; padding: 9px 11px; border-radius: 7px;
  box-shadow: 0 8px 24px rgba(16,24,40,0.24); transition: opacity .16s ease, transform .16s ease; z-index: 20;
}
.drop .tip::after {
  content: ""; position: absolute; top: 100%; left: 50%; transform: translateX(-50%);
  border: 6px solid transparent; border-top-color: #1f2933;
}
.drop:hover .tip, .drop:focus .tip, .drop:focus-visible .tip { visibility: visible; opacity: 1; transform: translateX(-50%) translateY(0); }
.src { background: #fff7ed; border-bottom: 1px dashed var(--warn-accent); padding: 0 1px; }

/* gate */
.ms-gate { margin-top: 26px; }
.ms-gate-label {
  font-size: 12px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--ink-faint); margin-bottom: 12px;
}
.ms-chips { display: flex; flex-wrap: wrap; gap: 12px; }
.ms-chip {
  display: inline-flex; align-items: center; gap: 10px; padding: 10px 16px; border-radius: 999px;
  border: 1px solid; font-size: 14px; background: var(--card);
}
.ms-chip .dot { width: 9px; height: 9px; border-radius: 50%; flex: none; }
.ms-chip .who { font-weight: 600; color: var(--ink); }
.ms-chip .role { font-size: 11.5px; color: var(--ink-faint); margin-left: 2px; }
.ms-chip .vd { font-weight: 700; letter-spacing: 0.03em; margin-left: 4px; }
.ms-chip.safe { border-color: var(--safe-line); background: var(--safe-bg); }
.ms-chip.safe .dot { background: var(--safe-accent); } .ms-chip.safe .vd { color: var(--safe-ink); }
.ms-chip.unsafe { border-color: var(--unsafe-line); background: var(--unsafe-bg); }
.ms-chip.unsafe .dot { background: #e53e3e; } .ms-chip.unsafe .vd { color: var(--unsafe-ink); }

/* gate banner (variant-colored) */
.ms-banner {
  margin-top: 16px; display: flex; align-items: flex-start; gap: 14px;
  border-radius: 10px; padding: 16px 18px; border: 1px solid;
}
.ms-banner .icon { font-size: 20px; line-height: 1.2; flex: none; }
.ms-banner .b-title { font-weight: 700; font-size: 15px; }
.ms-banner .b-body { font-size: 14px; margin-top: 2px; }
.ms-banner.disagree { background: var(--warn-bg); border-color: var(--warn-line); border-left: 4px solid var(--warn-accent); }
.ms-banner.disagree .b-title { color: var(--warn-ink); } .ms-banner.disagree .b-body { color: #8a4b2a; }
.ms-banner.safe { background: var(--safe-bg); border-color: var(--safe-line); border-left: 4px solid var(--safe-accent); }
.ms-banner.safe .b-title { color: var(--safe-ink); } .ms-banner.safe .b-body { color: #357a52; }

/* auditor confirmation */
.ms-auditors {
  margin-top: 14px; display: flex; align-items: center; gap: 12px;
  background: var(--safe-bg); border: 1px solid var(--safe-line); border-radius: 10px;
  padding: 13px 16px; color: var(--safe-ink); font-size: 14px;
}
.ms-auditors .check {
  flex: none; width: 22px; height: 22px; border-radius: 50%; background: var(--safe-accent);
  color: #fff; display: grid; place-items: center; font-size: 13px; font-weight: 700;
}
.ms-auditors strong { font-weight: 700; }

/* footer */
.ms-foot {
  margin-top: 28px; padding-top: 18px; border-top: 1px solid var(--line);
  font-size: 12.5px; color: var(--ink-faint); line-height: 1.6;
}
.ms-foot code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px;
  background: #eef2f7; padding: 1px 6px; border-radius: 4px; color: var(--ink-soft);
}
`;

/* ============================== components ============================== */

function Pane({ variant, title, sub, badge, sections }) {
  return (
    <div className="ms-pane">
      <div className="ms-pane-head">
        <div>
          <div className={"ms-pane-title " + variant}>{title}</div>
          {sub && <div className="ms-pane-sub">{sub}</div>}
        </div>
        {badge && <div className="ms-badge">{badge}</div>}
      </div>
      <div className="ms-pane-body">
        {sections.map((s, i) => (
          <div className="ms-section" key={i}>
            <h4>{s.h}</h4>
            <p>{s.b}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const [caseKey, setCaseKey] = useState("flagged");
  const isFlagged = caseKey === "flagged";
  const active = isFlagged ? CASE_FLAGGED : CASE_SAFE;

  return (
    <div className="ms-page">
      <style>{CSS}</style>
      <div className="ms-wrap">
        {/* landing hook */}
        <section className="ms-hook">
          <h1 className="ms-hook-title">What if the AI quietly drops a diagnosis?</h1>
          <p className="ms-hook-sub">
            MediSimplifier rewrites discharge summaries into plain language. Our safety gate catches what two of three
            judges miss.
          </p>
        </section>

        {/* case-switch bar */}
        <div className="ms-switch">
          <div className={"ms-caselabel " + (isFlagged ? "flag" : "ok")}>
            <span className="cdot" />
            {active.label}
            <span className="cidx">Case&nbsp;#{active.index}</span>
          </div>
          <button
            className="ms-toggle"
            onClick={() => setCaseKey(isFlagged ? "safe" : "flagged")}
            aria-pressed={!isFlagged}
          >
            {isFlagged ? "Show SAFE example" : "Show FLAGGED example"}
          </button>
        </div>

        {/* two-pane */}
        <div className="ms-grid">
          <Pane variant="orig" title="Original discharge summary" sub="Written for clinicians" sections={active.original} />
          <Pane
            variant="simp"
            title="MediSimplifier rewrite"
            sub="Plain language"
            badge="Reading level ~ grade 9 (model avg)"
            sections={active.simplified}
          />
        </div>

        {/* gate */}
        <section className="ms-gate">
          <div className="ms-gate-label">Safety gate — three LLM judges</div>
          <div className="ms-chips">
            {active.judges.map((j) => {
              const safe = j.verdict === "SAFE";
              return (
                <span className={"ms-chip " + (safe ? "safe" : "unsafe")} key={j.name}>
                  <span className="dot" />
                  <span className="who">
                    {j.name}
                    <span className="role"> · {j.role}</span>
                  </span>
                  <span className="vd">{j.verdict}</span>
                </span>
              );
            })}
          </div>

          <div className={"ms-banner " + active.gate.kind} role="alert">
            <span className="icon" aria-hidden="true">{active.gate.icon}</span>
            <div>
              <div className="b-title">{active.gate.title}</div>
              <div className="b-body">{active.gate.body}</div>
            </div>
          </div>

          <div className="ms-auditors">
            <span className="check" aria-hidden="true">✓</span>
            <span>
              <strong>Confirmed by 2 independent LLM auditors</strong> — {active.auditors}
            </span>
          </div>
        </section>

        {/* footer / honesty */}
        <footer className="ms-foot">
          Research prototype — not for clinical use. Both cases are real outputs from the 1,001-item student
          self-audit (<code>results/student_audit_review.json</code>): Case&nbsp;#44 (flagged &mdash; DISAGREE) and
          Case&nbsp;#820 (clean &mdash; SAFE). The three judge verdicts and both auditor judgments are captured, not
          staged, and reproducible from that artifact. Two of three judges (Qwen3-32B + Nemotron&nbsp;Nano) decide the
          gate; Llama-3.3-70B is advisory.
        </footer>
      </div>
    </div>
  );
}
