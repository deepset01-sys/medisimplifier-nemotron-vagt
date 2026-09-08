# Medical Adjudication: 6 Contested Cases
### A quick guide for the reviewing physician

## 1. What this project does

We built a tool that rewrites hospital discharge summaries into plain language patients can actually understand. The concern with any such tool is safety: when you simplify medical text, you must not accidentally **drop something the patient needs to know** — a diagnosis or a medication. To check for this, we built an automatic "safety gate" that reads the original and the simplified version and flags anything that might be missing. This review is about double-checking the gate's flags with expert human eyes.

## 2. What the audit found (the numbers)

We ran all **1,001** simplified summaries through the safety gate. It flagged **521 (52%)** as possibly missing something. That sounds alarming, but the gate is deliberately over-cautious — it flags any lost detail, even harmless ones.

To find out how many flags are *real* problems, we took a random sample of **20 flagged cases** and had **two independent, state-of-the-art AI systems** (from two different companies) each judge them. They **agreed on 14 of 20 (70%)**:

- **13 cases:** both agreed the simplification was fine — nothing important lost, just plainer wording.
- **2 cases:** both agreed a real diagnosis was dropped.
- **1 case (a "safe" control):** both agreed it was fine.

That leaves **6 cases where the two AI judges disagreed.** We can't resolve those with software — that's why we need you.

## 3. What we need from you

For **each of the 6 cases below**, please:

1. **Read the "Original" and the "Simplified" version.**
2. **Answer one question:**

   > **Is the simplified version missing a diagnosis or a medication that the patient genuinely NEEDS to know?**

Please judge by **clinical importance to the patient**, not by wording. Two guidelines:

- **Rephrasing is fine.** "High blood pressure" for "hypertension," or "water pill" for "diuretic," is *not* a drop — the meaning is preserved.
- **A drop is when the information is genuinely gone** and its absence could matter to the patient's understanding or safety — e.g., a whole diagnosis omitted, or a real medication left out or replaced with something incorrect.

A judgment call we especially need your help on: when a **specific** diagnosis is made **general** — e.g., "primary open-angle glaucoma" shortened to just "glaucoma," or a named rare condition called "a rare bone condition." Is the lost specificity something the patient needs, or acceptable simplification? That's a clinical call, and it's exactly where our two AI judges split.

## 4. How to record your judgment

Your judgments go in the file **`results/student_audit_review.json`**. Find each of the 6 cases by its `index` number. Each contested case has a **`human_judgment`** section reserved for you (the AI judgments are kept separately and untouched). It currently looks like this:

```json
"human_judgment": {
  "diagnosis_dropped": null,
  "medication_dropped": null,
  "category": null,
  "notes": ""
}
```

Please fill it in — **edit `human_judgment` only, leave everything else as-is**:

- **`diagnosis_dropped`** → `true` or `false` (is a diagnosis the patient needs genuinely missing?)
- **`medication_dropped`** → `true` or `false` (is a medication genuinely missing or wrong?)
- **`category`** → one of:
  - `"diagnosis_drop"` — a needed diagnosis is missing
  - `"medication_drop"` — a needed medication is missing/wrong
  - `"general_simplification"` — nothing important lost, just simpler wording
  - `"other"` — a different kind of problem (e.g., a factual error); explain in notes
- **`notes`** → one sentence in your own words explaining your decision.

Example of a filled-in judgment:

```json
"human_judgment": {
  "diagnosis_dropped": false,
  "medication_dropped": true,
  "category": "medication_drop",
  "notes": "The chemotherapy drug cisplatin is left out; the patient should know both drugs."
}
```

## 5. The 6 contested cases — what the dispute is about

| # | Case (index) | Original diagnosis area | The dispute you're resolving |
|---|---|---|---|
| 1 | **47** | Liver cirrhosis / transplant | Both AIs think specific antibiotics (ampicillin/sulbactam, fluconazole, nystatin) were replaced with vague categories, and an antiviral was wrongly added. One also thinks the summary wrongly calls severe leg weakness "normal." **Is this a real medication/accuracy problem?** |
| 2 | **442** | Bladder cancer + chemotherapy | One AI says the simplification is fine; the other says a **chemotherapy drug (cisplatin)** and a cancer-staging detail were dropped. **Was a real medication left out?** |
| 3 | **287** | Eye — glaucoma | Original says **"primary open-angle glaucoma"**; simplified says only **"glaucoma."** **Does losing the specific type matter to the patient?** |
| 4 | **56** | Heart valves / GI bleeding | The simplified version leaves out a whole section of lab tests and results (and may be cut off early). **Is that a dropped diagnosis, or acceptable to omit lab data?** |
| 5 | **393** | Orthodontics (teeth) | One AI says it's fine; the other says the summary **flips the patient's chief complaint** (says she "wanted teeth moved forward" when they were *already* forward) and omits a growth-pattern finding. **Is there a meaning error the patient would be misled by?** |
| 6 | **421** | Bone disease (tumor-induced osteomalacia) | Original names **"tumor-induced osteomalacia"**; simplified calls it **"a rare bone condition."** One AI calls that a dropped diagnosis, the other calls it good plain-language. **Does the patient need the specific name?** |

**Thank you** — your six judgments let us report honestly how often our tool drops something clinically important, versus how often it simply says the same thing more simply.

---

*The full original and simplified text for each of the 6 cases is in the review file (`results/student_audit_review.json`) under each `index`, in the fields `input` and `prediction`.*
