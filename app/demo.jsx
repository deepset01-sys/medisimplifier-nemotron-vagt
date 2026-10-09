/**
 * MediSimplifier — demo page (single-page React app)
 * ---------------------------------------------------
 * Two modes, then the panel section below them:
 *  Replay (the page opens here; replay.jsx) — the 28 cases of docs/replay_set.md, recorded once on the final endpoint
 *    image, read from replay_recording.json. Until that file is in this page, Replay says so. Pasted text is never
 *    processed in Replay: pasting switches to Live, with the pasted text in place.
 *  Live (live.jsx) — sends the visitor's text to the endpoint URL they enter, straight from the browser, in flag
 *    mode, and shows the gate's verdict and the endpoint's explanation in its own words.
 *  Panel section — the ΔΦ_V leaderboard, the live audit_panel call and "Try a different panel" (CPU service).
 *
 * Usage: rendered by src/main.jsx (Vite). Styles are injected inline; the wording is in liveText.js (Live, the mode
 * switch) and replayText.js (Replay).
 */
import React, { useEffect, useState } from "react";
import Live from "./live.jsx";
import { T } from "./liveText.js";
import Replay from "./replay.jsx";

/* ===================== audit_panel — Act 2 (live) ====================== */

const AUDIT_ENDPOINT = "https://port8000-vnvvxqt68q703dy.tunnel.applications.eu-north1.nebius.cloud/v1/audit_panel"; // CPU audit_panel service (audit-cpu-v2.1, open to any origin), started for judging windows; deterministic — same answer every call
// Only a response from the v2 clean-stratum pool is shown live; anything else (e.g. a stale v1
// service) is treated as unavailable, so the page never displays numbers the chart contradicts.
const AUDIT_BENCHMARK = "MedSimp-JudgeBench-v2";
const REPO_URL = "https://github.com/deepset01-sys/medisimplifier-nemotron-vagt";
const AUDIT_REQUEST = {
  incumbent_panel: ["meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen3-32B"],
  candidate_pool: [
    "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
    "google/gemma-3-27b-it",
    "openai/gpt-oss-120b",
    "nvidia/nemotron-3-super-120b-a12b",
    "deepseek-ai/DeepSeek-V4-Flash-0731",
    "nvidia/Nemotron-3-Ultra-550b-a55b",
  ],
};

// Static ΔΦ_V chart — v2 hand-verified diagnosis stratum (240 items), incumbent Llama+Qwen.
// Source: results/audit_panel_receipt_v2_diagnosis.json + results/judgebench_v2_pool_table.json.
const PANEL_CANDIDATES = [
  { name: "gpt-oss-120b", delta: 0.122, ci: [0.1, 0.1416], recommended: true },
  { name: "DeepSeek Flash", delta: 0.1238, ci: [0.1024, 0.144], note: "tied · 7 errors" },
  { name: "Ultra 550B", delta: 0.0781 },
  { name: "Nemotron Nano", delta: 0.0765 },
  { name: "Super 120B", delta: 0.048 },
  { name: "gemma-27B", delta: 0.0066, note: "CI includes 0" },
];
const PANEL_MAX = 0.1238; // longest bar (DeepSeek) → normalizes bar widths

/* ---- interactive panel explorer: the full 8-model pool ---- */
const EXPLORER_MODELS = [
  { id: "meta-llama/Llama-3.3-70B-Instruct", label: "Llama 3.3 70B" },
  { id: "Qwen/Qwen3-32B", label: "Qwen3-32B" },
  { id: "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B", label: "Nemotron Nano 30B" },
  { id: "nvidia/nemotron-3-super-120b-a12b", label: "Nemotron Super 120B" },
  { id: "nvidia/Nemotron-3-Ultra-550b-a55b", label: "Nemotron Ultra 550B" },
  { id: "openai/gpt-oss-120b", label: "GPT-OSS 120B" },
  { id: "deepseek-ai/DeepSeek-V4-Flash-0731", label: "DeepSeek Flash" },
  { id: "google/gemma-3-27b-it", label: "Gemma 27B" },
];
const EXPLORER_LABEL = Object.fromEntries(EXPLORER_MODELS.map((m) => [m.id, m.label]));

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
.ms-chip.error { border-color: var(--line); background: #f7fafc; }
.ms-chip.error .dot { background: #a0aec0; } .ms-chip.error .vd { color: var(--ink-faint); }

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
.ms-banner.unsafe { background: var(--unsafe-bg); border-color: var(--unsafe-line); border-left: 4px solid #e53e3e; }
.ms-banner.unsafe .b-title { color: var(--unsafe-ink); } .ms-banner.unsafe .b-body { color: #9b2c2c; }
.ms-banner.error { background: #f7fafc; border-color: var(--line); border-left: 4px solid #a0aec0; }
.ms-banner.error .b-title { color: var(--ink-soft); } .ms-banner.error .b-body { color: var(--ink-faint); }

/* footer */
.ms-foot {
  margin-top: 28px; padding-top: 18px; border-top: 1px solid var(--line);
  font-size: 12.5px; color: var(--ink-faint); line-height: 1.6;
}
.ms-foot code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px;
  background: #eef2f7; padding: 1px 6px; border-radius: 4px; color: var(--ink-soft);
}

/* run-it-live */
.ms-live { margin-top: 18px; }
.ms-runbtn {
  appearance: none; border: 1px solid var(--brand); background: var(--brand); color: #fff;
  font-weight: 600; font-size: 14px; padding: 10px 18px; border-radius: 8px; cursor: pointer;
  transition: background .15s, transform .05s;
}
.ms-runbtn:hover { background: #24466e; }
.ms-runbtn:active { transform: translateY(1px); }
.ms-runbtn:focus-visible { outline: 2px solid #a9c3e6; outline-offset: 2px; }
.ms-live-note { margin-left: 12px; font-size: 12.5px; color: var(--ink-faint); }
.ms-live-loading { display: inline-flex; align-items: center; font-size: 14px; color: var(--ink-soft); font-weight: 500; }
.ms-live-loading .dots span { animation: msblink 1.2s infinite both; }
.ms-live-loading .dots span:nth-child(2) { animation-delay: .2s; }
.ms-live-loading .dots span:nth-child(3) { animation-delay: .4s; }
@keyframes msblink { 0%, 80%, 100% { opacity: .2; } 40% { opacity: 1; } }
.ms-live-result {
  border: 1px solid #cbd6e6; border-left: 4px solid var(--brand); background: #f7fafd;
  border-radius: 10px; padding: 14px 16px;
}
.ms-live-badge {
  display: inline-flex; align-items: center; gap: 7px; font-size: 12px; font-weight: 700;
  letter-spacing: .04em; text-transform: uppercase; color: var(--brand); margin-bottom: 10px;
}
.ms-live-badge .live-dot { width: 8px; height: 8px; border-radius: 50%; background: #e53e3e; animation: mspulse 1.4s infinite; }
@keyframes mspulse { 0%, 100% { opacity: 1; } 50% { opacity: .35; } }
.ms-live-row { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.ms-live-consensus { font-weight: 700; font-size: 14px; }
.v-SAFE { color: var(--safe-ink); } .v-UNSAFE { color: var(--unsafe-ink); }
.v-DISAGREE { color: var(--warn-accent); } .v-ERROR { color: var(--ink-faint); }
.ms-live-meta { font-size: 12.5px; color: var(--ink-faint); }
.ms-live-error {
  border: 1px solid var(--warn-line); background: var(--warn-bg); border-radius: 10px;
  padding: 12px 16px; font-size: 14px; color: var(--warn-ink);
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
}
.ms-retry {
  appearance: none; border: 1px solid #cdd7e2; background: #fff; color: var(--brand);
  font-weight: 600; font-size: 13px; padding: 6px 12px; border-radius: 999px; cursor: pointer;
}

/* Act 2 — bridge + audit_panel card */
.ms-bridge {
  margin: 18px 0 0; font-size: 14.5px; line-height: 1.6; color: var(--ink-soft);
  border-left: 3px solid var(--line); padding-left: 14px;
}
.ms-act2 {
  margin-top: 20px; background: var(--card); border: 1px solid var(--line); border-radius: 12px;
  box-shadow: 0 1px 2px rgba(16,24,40,0.04), 0 8px 24px rgba(16,24,40,0.04); padding: 20px 22px;
}
.ms-act2-title { font-size: 16px; font-weight: 700; color: var(--ink); margin-bottom: 2px; }
.ms-act2-sub { font-size: 12.5px; color: var(--ink-faint); margin-bottom: 16px; }
.ms-bars { display: flex; flex-direction: column; gap: 9px; }
.ms-bar-row { display: grid; grid-template-columns: 104px 1fr 64px; align-items: center; gap: 12px; row-gap: 2px; font-size: 13px; }
.ms-bar-extra { grid-column: 2 / 4; font-size: 11.5px; color: var(--ink-faint); }
.ms-bar-name { color: var(--ink-soft); font-weight: 500; text-align: right; }
.ms-bar-row.rec .ms-bar-name { color: var(--brand); font-weight: 700; }
.ms-bar-track { height: 16px; background: #eef2f7; border-radius: 4px; overflow: hidden; }
.ms-bar-fill { display: block; height: 100%; background: #cbd6e6; border-radius: 4px; }
.ms-bar-row.rec .ms-bar-fill { background: var(--brand); }
.ms-bar-val { font-variant-numeric: tabular-nums; color: var(--ink-soft); white-space: nowrap; font-size: 12.5px; }
.ms-bar-row.rec .ms-bar-val { color: var(--ink); font-weight: 600; }
.ms-bar-ci { color: var(--ink-faint); font-weight: 400; }
.ms-bar-tag { color: var(--brand); font-weight: 700; margin-left: 6px; font-size: 11.5px; }
.ms-bar-note { color: var(--ink-faint); font-weight: 500; margin-left: 6px; font-size: 11.5px; }
.ms-act2-caption { margin: 16px 0 0; font-size: 13.5px; line-height: 1.55; color: var(--ink-soft); }
.ms-changed { margin-top: 12px; font-size: 13px; line-height: 1.55; color: var(--ink-soft); }
.ms-changed summary { cursor: pointer; color: var(--brand); font-weight: 600; }
.ms-changed ol { margin: 8px 0 6px; padding-left: 20px; }
.ms-changed li { margin-bottom: 4px; }
.ms-changed a { color: var(--brand); font-weight: 600; }
.ms-audit-live { margin-top: 16px; }

/* interactive panel explorer */
.ms-explorer {
  margin-top: 26px; background: var(--card); border: 1px solid var(--line); border-radius: 12px;
  box-shadow: 0 1px 2px rgba(16,24,40,0.04), 0 8px 24px rgba(16,24,40,0.04); padding: 22px;
}
.ms-exp-title { font-size: 18px; font-weight: 700; letter-spacing: -0.01em; color: var(--ink); margin-bottom: 4px; }
.ms-exp-sub { font-size: 13.5px; color: var(--ink-soft); margin: 0 0 18px; max-width: 720px; }
.ms-exp-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
@media (max-width: 820px) { .ms-exp-grid { grid-template-columns: repeat(2, 1fr); } }
.ms-exp-card {
  appearance: none; text-align: left; cursor: pointer; background: #fff; border: 1px solid var(--line);
  border-radius: 10px; padding: 12px 13px; display: flex; flex-direction: column; gap: 3px;
  transition: border-color .15s, background .15s, box-shadow .15s;
}
.ms-exp-card:hover { border-color: #a9c3e6; }
.ms-exp-card:focus-visible { outline: 2px solid #a9c3e6; outline-offset: 2px; }
.ms-exp-card.on { border-color: var(--brand); background: var(--brand-soft); box-shadow: inset 0 0 0 1px var(--brand); }
.ms-exp-check {
  width: 20px; height: 20px; border-radius: 50%; display: grid; place-items: center;
  font-size: 12px; font-weight: 700; background: #eef2f7; color: var(--ink-faint); margin-bottom: 2px;
}
.ms-exp-card.on .ms-exp-check { background: var(--brand); color: #fff; }
.ms-exp-name { font-size: 13.5px; font-weight: 600; color: var(--ink); }
.ms-exp-role { font-size: 11px; color: var(--ink-faint); text-transform: uppercase; letter-spacing: .04em; }
.ms-exp-card.on .ms-exp-role { color: var(--brand); }
.ms-exp-actions { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; margin-top: 16px; }
.ms-exp-count { font-size: 12.5px; color: var(--ink-faint); font-weight: 500; }
.ms-runbtn:disabled { background: #cbd6e6; border-color: #cbd6e6; cursor: not-allowed; }
.ms-exp-result {
  margin-top: 16px; border: 1px solid #cbd6e6; border-left: 4px solid var(--brand);
  background: #f7fafd; border-radius: 10px; padding: 14px 16px;
}
.ms-exp-blind { font-size: 13.5px; color: var(--ink-soft); margin-bottom: 10px; }
.ms-exp-blind strong { color: var(--warn-accent); font-weight: 700; text-transform: capitalize; }
.ms-exp-rec { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 12px; }
.ms-exp-rec-label { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: var(--ink-faint); }
.ms-exp-rec-model { font-size: 17px; font-weight: 700; color: var(--brand); }
.ms-exp-rec-meta { font-size: 12.5px; color: var(--ink-faint); font-variant-numeric: tabular-nums; }
.ms-exp-why { margin: 10px 0 0; font-size: 13.5px; line-height: 1.55; color: var(--ink); }
.ms-exp-scope { margin: 14px 0 0; font-size: 11.5px; color: var(--ink-faint); }

/* mode switch */
.ms-modes {
  display: inline-flex; gap: 4px; padding: 4px; margin-bottom: 16px;
  background: var(--card); border: 1px solid var(--line); border-radius: 999px;
}
.ms-mode {
  appearance: none; border: 0; background: transparent; color: var(--ink-soft);
  font-weight: 600; font-size: 14px; padding: 8px 20px; border-radius: 999px; cursor: pointer;
}
.ms-mode.on { background: var(--brand); color: #fff; }
.ms-mode:focus-visible { outline: 2px solid #a9c3e6; outline-offset: 2px; }

/* Replay and Live */
.ms-replay, .ms-lv {
  background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 20px 22px;
  box-shadow: 0 1px 2px rgba(16,24,40,0.04), 0 8px 24px rgba(16,24,40,0.04);
}
.ms-replay-text { margin: 0 0 10px; font-size: 15px; color: var(--ink); max-width: 760px; }
.ms-lv-intro { margin: 0 0 4px; font-size: 15px; color: var(--ink); }
.ms-lv-hint { margin: 6px 0 0; font-size: 12.5px; color: var(--ink-faint); }
.ms-lv-hint a { color: var(--brand); font-weight: 600; }
.ms-lv-label {
  display: block; margin: 18px 0 6px; font-size: 12px; font-weight: 700; letter-spacing: 0.06em;
  text-transform: uppercase; color: var(--ink-faint);
}
.ms-lv-input, .ms-lv-text {
  width: 100%; font: inherit; font-size: 14.5px; color: var(--ink); background: #fff;
  border: 1px solid #cdd7e2; border-radius: 8px; padding: 10px 12px;
}
.ms-lv-text { min-height: 180px; resize: vertical; }
.ms-lv-input:focus, .ms-lv-text:focus { outline: 2px solid #a9c3e6; outline-offset: 1px; }
.ms-lv-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-top: 10px; }
.ms-lv-row .ms-lv-hint { margin: 0; }
.ms-retry:disabled { color: var(--ink-faint); cursor: not-allowed; }
.ms-lv-notice { margin: 14px 0 0; font-size: 13px; font-weight: 600; color: var(--ink-soft); }
.ms-lv-status { margin-top: 10px; font-size: 14px; color: var(--ink-soft); }
.ms-lv-status.ok { color: var(--safe-ink); }
.ms-lv-status.bad { color: var(--warn-ink); }
.ms-lv-wait {
  margin-top: 16px; display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  border: 1px solid #cbd6e6; background: #f7fafd; border-radius: 10px; padding: 12px 16px;
  font-size: 14px; color: var(--ink-soft);
}
.ms-lv-timer { font-variant-numeric: tabular-nums; font-weight: 700; color: var(--brand); }
.ms-lv .ms-live-error { margin-top: 16px; }
.ms-lv-result { margin-top: 6px; }
.ms-lv-sub {
  margin: 20px 0 6px; font-size: 12px; font-weight: 700; letter-spacing: 0.06em;
  text-transform: uppercase; color: var(--ink-faint);
}
.ms-lv-rewrite { margin: 0; white-space: pre-wrap; font-size: 15px; color: var(--ink); }
.ms-lv-explain {
  margin-top: 18px; border: 1px solid var(--line); border-left: 4px solid #a0aec0; border-radius: 10px;
  background: #fbfcfe; padding: 12px 16px; font-size: 14px; color: var(--ink-soft);
}
.ms-lv-explain h5 {
  margin: 0 0 6px; font-size: 12px; font-weight: 700; letter-spacing: 0.06em;
  text-transform: uppercase; color: var(--ink-faint);
}
.ms-lv-explain p { margin: 0; }
.ms-lv-explain ul { margin: 8px 0 0; padding-left: 20px; }
.ms-lv-times { margin: 14px 0 0; font-size: 12.5px; color: var(--ink-faint); }

/* Replay: the recorded cases */
.ms-replay a { color: var(--brand); font-weight: 600; }
.ms-rp-meta { margin: 0 0 10px; font-size: 13px; color: var(--ink-soft); overflow-wrap: anywhere; }
.ms-rp-part { margin-top: 26px; padding-top: 20px; border-top: 1px solid var(--line); }
.ms-rp-part h3 { margin: 0 0 8px; font-size: 17px; font-weight: 700; color: var(--ink); }
.ms-rp-about { margin: 0 0 8px; font-size: 13.5px; color: var(--ink-soft); max-width: 820px; }
.ms-rp-group { margin-top: 14px; }
.ms-rp-group h4 {
  margin: 0 0 6px; font-size: 12px; font-weight: 700; letter-spacing: 0.06em;
  text-transform: uppercase; color: var(--ink-faint);
}
.ms-rp-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.ms-rp-chip {
  appearance: none; cursor: pointer; display: inline-flex; align-items: baseline; gap: 8px;
  border: 1px solid var(--line); background: #fff; border-radius: 999px; padding: 6px 12px;
  font-size: 13px; font-weight: 700; color: var(--ink);
}
.ms-rp-chip.on { border-color: var(--brand); background: var(--brand-soft); box-shadow: inset 0 0 0 1px var(--brand); }
.ms-rp-chip:focus-visible { outline: 2px solid #a9c3e6; outline-offset: 2px; }
.ms-rp-v { font-size: 12px; font-weight: 600; }
.ms-rp-v.v-none { color: var(--ink-faint); }
.ms-rp-case {
  margin-top: 18px; border: 1px solid var(--line); border-radius: 10px; padding: 16px 18px; background: #fbfcfe;
}
.ms-rp-label { font-size: 14px; font-weight: 700; color: var(--ink); }
.ms-rp-note { margin: 8px 0 0; font-size: 14px; color: var(--ink-soft); }
.ms-rp-text {
  margin: 0; white-space: pre-wrap; font-size: 14.5px; color: var(--ink); max-height: 360px; overflow: auto;
  background: #fff; border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px;
}
.ms-rp-verdicts { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.ms-rp-vlabel { margin: 0 0 8px; font-size: 13px; font-weight: 700; color: var(--ink-soft); overflow-wrap: anywhere; }
@media (max-width: 820px) { .ms-rp-verdicts { grid-template-columns: 1fr; } }
.ms-rp-end { margin-top: 24px; }

/* panel section, below both modes */
.ms-panelsec { margin-top: 28px; }
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
  const [mode, setMode] = useState("replay"); // the page opens on Replay
  const [liveText, setLiveText] = useState("");
  const [audit, setAudit] = useState({ status: "idle", data: null });

  // Replay never processes pasted text: pasting switches to Live, with the pasted text in place.
  useEffect(() => {
    if (mode !== "replay") return undefined;
    function onPaste(e) {
      const pasted = e.clipboardData ? e.clipboardData.getData("text") : "";
      if (pasted.trim()) {
        e.preventDefault();
        setLiveText(pasted);
        setMode("live");
      }
    }
    document.addEventListener("paste", onPaste);
    return () => document.removeEventListener("paste", onPaste);
  }, [mode]);

  async function runAudit() {
    setAudit({ status: "loading", data: null });
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 30000); // CPU service — milliseconds; generous ceiling
      const res = await fetch(AUDIT_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(AUDIT_REQUEST),
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      if (data.benchmark !== AUDIT_BENCHMARK) throw new Error("unexpected pool: " + data.benchmark);
      setAudit({ status: "success", data });
    } catch (e) {
      setAudit({ status: "error", data: null });
    }
  }

  // interactive panel explorer state (default = the gate's own panel: Llama + Qwen)
  const [panelSel, setPanelSel] = useState(["meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen3-32B"]);
  const [explore, setExplore] = useState({ status: "idle", data: null });

  function togglePanel(id) {
    setPanelSel((cur) => (cur.includes(id) ? cur.filter((m) => m !== id) : [...cur, id]));
    setExplore({ status: "idle", data: null }); // any panel change invalidates the last result
  }

  async function runExplorer() {
    if (panelSel.length < 2) return; // endpoint requires >= 2 incumbents
    setExplore({ status: "loading", data: null });
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 30000);
      const candidate_pool = EXPLORER_MODELS.map((m) => m.id).filter((id) => !panelSel.includes(id));
      const res = await fetch(AUDIT_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ incumbent_panel: panelSel, candidate_pool }),
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      if (data.benchmark !== AUDIT_BENCHMARK) throw new Error("unexpected pool: " + data.benchmark);
      setExplore({ status: "success", data });
    } catch (e) {
      setExplore({ status: "error", data: null });
    }
  }

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

        {/* mode switch: Replay (the page opens here) and Live */}
        <div className="ms-modes" role="tablist" aria-label={T.modesLabel}>
          <button
            role="tab"
            aria-selected={mode === "replay"}
            className={"ms-mode" + (mode === "replay" ? " on" : "")}
            onClick={() => setMode("replay")}
          >
            {T.replayTab}
          </button>
          <button
            role="tab"
            aria-selected={mode === "live"}
            className={"ms-mode" + (mode === "live" ? " on" : "")}
            onClick={() => setMode("live")}
          >
            {T.liveTab}
          </button>
        </div>

        {mode === "replay" ? (
          <Replay ruleUrl={REPO_URL + "/blob/main/docs/replay_set.md"} onTryLive={() => setMode("live")} />
        ) : (
          <Live text={liveText} setText={setLiveText} reproUrl={REPO_URL + "/blob/main/docs/REPRODUCIBILITY.md"} />
        )}

        {/* panel section — below both modes */}
        <section className="ms-panelsec">
          {/* bridge */}
          <p className="ms-bridge">
            A single judge call on a hard case is noisy — even Nemotron doesn't always agree with itself. So how do we
            know it belongs in the panel? We don't trust one call. We measured it.
          </p>

          {/* why you can trust the panel (audit_panel) */}
          <div className="ms-act2">
            <div className="ms-act2-title">Which judge best fixes the panel's blind spot?</div>
            <div className="ms-act2-sub">
              ΔΦ_V on the hand-verified diagnosis stratum — 120 real dropped diagnoses + 120 paired controls (a 50% drop rate; ΔΦ_V depends on it)
            </div>

            <div className="ms-bars">
              {PANEL_CANDIDATES.map((c) => (
                <div className={"ms-bar-row" + (c.recommended ? " rec" : "")} key={c.name}>
                  <span className="ms-bar-name">{c.name}</span>
                  <span className="ms-bar-track">
                    <span className="ms-bar-fill" style={{ width: (c.delta / PANEL_MAX) * 100 + "%" }} />
                  </span>
                  <span className="ms-bar-val">+{c.delta.toFixed(4)}</span>
                  {(c.ci || c.recommended || c.note) && (
                    <span className="ms-bar-extra">
                      {c.ci && <span className="ms-bar-ci">95% CI [{c.ci[0].toFixed(4)}, {c.ci[1].toFixed(4)}]</span>}
                      {c.recommended && <span className="ms-bar-tag">← recommended</span>}
                      {c.note && <span className="ms-bar-note">{c.note}</span>}
                    </span>
                  )}
                </div>
              ))}
            </div>

            <p className="ms-act2-caption">
              VAGT ranked six candidate judges by truth-anchored dependability on 240 hand-verified items. gpt-oss-120b
              and DeepSeek Flash are statistically tied; the tool picks gpt-oss because it returned no errors (DeepSeek: 7)
              — a tie-break we added after seeing this result. DeepSeek's errors were truncations from a smaller token budget; at a
              matched budget gpt-oss still wins, on specificity. An earlier, automated pass recommended Nemotron Nano — that result did not survive
              hand-verified labels.
            </p>

            <details className="ms-changed">
              <summary>What changed and why</summary>
              <ol>
                <li>
                  <strong>Automated pass.</strong> Diagnosis-drop labels were generated by script. On those labels,
                  Nemotron Nano was recommended: ΔΦ_V +0.0706.
                </li>
                <li>
                  <strong>Our own audit.</strong> We read all 150 “dropped diagnosis” items by hand: 128 (85%) still
                  contained the diagnosis, and only 9 were genuine drops, too few to show
                  whether Nano helps. At step 1’s 41% drop share, with all three judges on the deployed prompt, the
                  corrected labels give Nano a ΔΦ_V of +0.0323 [−0.0384, +0.0848], not detectable; the automated labels give
                  +0.0426. An earlier version of this page said Nano’s ΔΦ_V “reversed to −0.144”: that figure was at 2.7%
                  drops, not 41%, and like step 1’s it mixed two judge prompts.
                </li>
                <li>
                  <strong>Rebuild.</strong> A new benchmark of 120 hand-verified real drops + 120 paired controls: Nano
                  +0.0765, gpt-oss +0.1220 (recommended). These use the deployed gate prompt; with all three judges
                  under the calibration prompt, Nano scores +0.0591. All three figures are at 50% drops, step 1’s at 41%,
                  and ΔΦ_V depends on that share.
                </li>
              </ol>
              <a href={REPO_URL + "#why-vagt--the-panel-selection-finding"} target="_blank" rel="noopener noreferrer">
                Full account in the README →
              </a>
            </details>

            {/* live, deterministic audit_panel call (proxied by Vite) */}
            <div className="ms-audit-live">
              {audit.status === "idle" && (
                <button className="ms-runbtn" onClick={runAudit}>Run audit_panel live →</button>
              )}

              {audit.status === "loading" && (
                <div className="ms-live-loading">
                  Calling audit_panel
                  <span className="dots">
                    <span>.</span>
                    <span>.</span>
                    <span>.</span>
                  </span>
                </div>
              )}

              {audit.status === "success" && audit.data && (() => {
                const rec = audit.data.recommendation || {};
                const ci = rec.ci_95 || [];
                const others = (rec.tied_top_candidates || []).filter((m) => m !== rec.model);
                return (
                  <div className="ms-live-result">
                    <div className="ms-live-badge">
                      <span className="live-dot" aria-hidden="true" />Live result — deterministic (same answer every call)
                    </div>
                    <div className="ms-live-row">
                      <span className="ms-live-consensus v-SAFE">Recommended: {rec.model}</span>
                      {rec.expected_Phi_V_lift != null && (
                        <span className="ms-live-meta">
                          ΔΦ_V +{rec.expected_Phi_V_lift}
                          {ci.length === 2 && ` · CI [${ci[0]}, ${ci[1]}]`}
                        </span>
                      )}
                    </div>
                    {others.length > 0 && (
                      <div className="ms-live-meta">
                        Tied with {others.map((m) => EXPLORER_LABEL[m] || m).join(", ")} — chosen by{" "}
                        {rec.selected_among_ties_by}.
                      </div>
                    )}
                  </div>
                );
              })()}

              {audit.status === "error" && (
                <div className="ms-live-error">
                  <span>⚠️ Live service unavailable — the chart above is the committed v2 receipt.</span>
                  <button className="ms-retry" onClick={runAudit}>Try again</button>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* interactive panel explorer — Try a different panel */}
        <section className="ms-explorer">
          <div className="ms-exp-title">Try a different panel</div>
          <p className="ms-exp-sub">
            Pick the judges you'd run (at least 2). VAGT measures how dependably your panel catches dropped diagnoses
            and recommends which judge to add — live, deterministic, over the 8-model pool on the 240-item hand-verified
            diagnosis stratum. Change the panel and the recommendation changes.
          </p>

          <div className="ms-exp-grid">
            {EXPLORER_MODELS.map((m) => {
              const on = panelSel.includes(m.id);
              return (
                <button
                  key={m.id}
                  className={"ms-exp-card" + (on ? " on" : "")}
                  onClick={() => togglePanel(m.id)}
                  aria-pressed={on}
                >
                  <span className="ms-exp-check" aria-hidden="true">{on ? "✓" : "+"}</span>
                  <span className="ms-exp-name">{m.label}</span>
                  <span className="ms-exp-role">{on ? "in your panel" : "candidate"}</span>
                </button>
              );
            })}
          </div>

          <div className="ms-exp-actions">
            <span className="ms-exp-count">
              {panelSel.length} in panel
              {panelSel.length < 2
                ? " — pick at least 2"
                : ` · ${EXPLORER_MODELS.length - panelSel.length} candidates`}
            </span>
            <button
              className="ms-runbtn"
              onClick={runExplorer}
              disabled={panelSel.length < 2 || explore.status === "loading"}
            >
              {explore.status === "loading" ? "Analyzing…" : "Analyze my panel →"}
            </button>
          </div>

          {explore.status === "success" && explore.data && (() => {
            const d = explore.data;
            const rec = d.recommendation || {};
            const ci = rec.ci_95 || [];
            const blind = d.incumbent && d.incumbent.blindest_stratum;
            const phi = d.incumbent && d.incumbent.Phi_V_by_stratum && d.incumbent.Phi_V_by_stratum[blind];
            const label = EXPLORER_LABEL[rec.model] || rec.model;
            const straddles = ci.length === 2 && ci[0] <= 0;
            const others = (rec.tied_top_candidates || []).filter((m) => m !== rec.model);
            const tieNote = others.length
              ? ` Statistically tied with ${others.map((m) => EXPLORER_LABEL[m] || m).join(", ")}; chosen by ${rec.selected_among_ties_by}.`
              : "";
            return (
              <div className="ms-exp-result">
                <div className="ms-live-badge"><span className="live-dot" aria-hidden="true" />Live · deterministic</div>
                {blind && phi != null && (
                  <div className="ms-exp-blind">
                    Your panel on <strong>{blind}</strong> drops: Φ_V {phi}
                  </div>
                )}
                {rec.model ? (
                  <>
                    <div className="ms-exp-rec">
                      <span className="ms-exp-rec-label">Add</span>
                      <span className="ms-exp-rec-model">{label}</span>
                      {rec.expected_Phi_V_lift != null && (
                        <span className="ms-exp-rec-meta">
                          ΔΦ_V +{rec.expected_Phi_V_lift}
                          {ci.length === 2 ? ` · 95% CI [${ci[0]}, ${ci[1]}]` : ""}
                        </span>
                      )}
                    </div>
                    <p className="ms-exp-why">
                      {straddles
                        ? `${label} is the best available add, but its 95% CI straddles zero — no candidate in the pool clearly improves this panel on ${blind} drops. Sometimes the honest answer is "none of these clearly helps."`
                        : `Of the remaining models, ${label} most improves this panel on ${blind} drops.${tieNote}${rec.caveat ? " Caveat: " + rec.caveat : ""}`}
                    </p>
                  </>
                ) : (
                  <p className="ms-exp-why">No candidate in the pool improves this panel on {blind} drops.</p>
                )}
              </div>
            );
          })()}

          {explore.status === "error" && (
            <div className="ms-live-error">
              <span>⚠️ Couldn't reach audit_panel — the CPU service may be stopped between judging windows; otherwise check the selection (need ≥ 2) and try again.</span>
              <button className="ms-retry" onClick={runExplorer}>Try again</button>
            </div>
          )}

          <p className="ms-exp-scope">
            8-model pool · JudgeBench v2 diagnosis stratum (240 hand-verified items, 50% drops; Φ_V and ΔΦ_V depend on that share) · pre-computed verdicts, no live
            model calls · same panel → same answer.
          </p>
        </section>

        {/* footer / honesty */}
        <footer className="ms-foot">
          Research prototype — not for clinical use. Two of three judges (Qwen3-32B + Nemotron&nbsp;Nano) decide the
          gate; Llama-3.3-70B is advisory.
        </footer>
      </div>
    </div>
  );
}
