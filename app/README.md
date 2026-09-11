# MediSimplifier — Safety Gate Demo

A single-page demo of the MediSimplifier diagnosis-drop safety gate, built on two
**real, captured** cases from the 1,001-item student self-audit
(`../results/student_audit_review.json`) — nothing synthetic, nothing staged:

- **FLAGGED — Case #44:** the plain-language rewrite silently dropped the diagnosis
  *"liquoral hypotension"* (intracranial hypotension). Llama-3.3-70B and Qwen3-32B
  passed it; **Nemotron Nano flagged it**; the gate returned **DISAGREE**. Both LLM
  auditors (Claude Sonnet 5 + Gemini 2.5 Pro) independently confirmed the drop.
- **SAFE — Case #820:** a faithful COVID-19 rewrite. All three judges **SAFE**; the
  gate passes it — showing the gate is a real discriminator, not a flag-everything alarm.

Use the **"Show SAFE example" / "Show FLAGGED example"** button to toggle between them.

## Run it

```bash
npm install
npm run dev
```

Then open **http://localhost:5173**

## Files

| File | Purpose |
|------|---------|
| `demo.jsx` | The whole app — one self-contained React component with inline styles |
| `src/main.jsx` | React mount (imports `../demo.jsx`) |
| `src/index.css` | Minimal reset so browser defaults don't fight the clinical layout |
| `index.html` | Vite entry |
| `package.json`, `vite.config.js` | Pinned deps (React 19, Vite 8) + config |

Research prototype — **not for clinical use.**
