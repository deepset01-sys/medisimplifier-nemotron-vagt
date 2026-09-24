#!/usr/bin/env python3
"""
build_judgebench_v2.py — STEP 0 ONLY: diagnosis-drop generator validation batch.

Per docs/judgebench_v2_protocol.md. tau=1 = PATIENT-INVISIBLE primary-diagnosis drop
(name+abbrev+lay-paraphrase absent AND not lay-recoverable, DELETION-ONLY diff). Pipeline per
item: select a PRIMARY diagnosis from a clean control (F1 split compound -> primary component;
F2 reject lay-mechanism/injury targets); elicit its forms/synonyms (F4); editor removes every
form across the WHOLE document, deletion-only, no placeholder, coherence-repaired (F3/F5/F6);
then GATES:
  V1  name/synonym surface absent (F9 synonym-aware),
  V1b deletion-only diff (no med/lab/imaging/histology removed),
  V2  dose preservation,
  V3  oracle: Q_name NO (named/paraphrased?) AND Q_lay NO (lay-recoverable? F7 GATE) AND
      Q_added NO (fabrication? F8 GATE).
COVARIATES recorded, never gating: expert_recoverable (expert can infer from fingerprint) and
category_retained (broad parent category kept; Decision 1). Q_removed_other -> human-adjudicated
(F8; avoids the idx-203 false alarm where removed text WAS the diagnosis restatement).
Writes one record per item with a BLANK human_verdict for the V4 human pass. It does NOT scale,
does NOT accept any item on automated gates, and does NOT touch the benchmark/README/tests.

Roles (frozen): EDITOR=DeepSeek-V4-Pro, ORACLE=gpt-oss-120b, EMBED=Qwen3-Embedding-8B,
HUMAN=arbiter (fills human_verdict later). None is a panel judge / teacher / each other.

Run (after review):
    export NEBIUS_API_KEY='...'
    python scripts/build_judgebench_v2.py --n 22 --seed 99
Output: results/judgebench_v2_step0_seed<SEED>.json  (human_verdict / human_note blank)
"""
import os, re, sys, json, time, argparse, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8")

# ---------- config ----------
CAL = r"D:/Owner/Desktop/assignment_01/medisimplifier-nebius/results/nebius_evidence/calibration_verdicts.json"
OUT_TMPL = r"C:/Users/User/Desktop/medisimplifier-nemotron-vagt/results/judgebench_v2_step0_seed{seed}.json"
CHAT_URL  = "https://api.studio.nebius.ai/v1/chat/completions"
EMBED_URL = "https://api.studio.nebius.ai/v1/embeddings"
EDITOR = "deepseek-ai/DeepSeek-V4-Pro"
ORACLE = "openai/gpt-oss-120b"
EMBED  = "Qwen/Qwen3-Embedding-8B"
SEED = 42
# max_sim is INFORMATIONAL ONLY and does not gate: under the patient-invisible tau definition a
# remaining clinical fingerprint is legitimately similar to "the patient has X" and must not fail
# the item (that is expert_recoverable, set by the oracle's Q_name — not by cosine). The raw value
# is still recorded per item to help V4 calibration.
SENT_SPLIT = r'(?<=[.!?])\s+'
DOSE = re.compile(r'\b(\d+)\s*(mg|mcg|ml|mL|g|units?|IU)\b', re.IGNORECASE)
LAB  = re.compile(r'\b\d+(?:\.\d+)?\s*(?:%|mg/dL|g/dL|mmol/L|mEq/L|ng/mL|U/L|IU/L|/[uµ]L|mm\s?Hg|mmHg)\b', re.IGNORECASE)
# markers of a removed finding / procedure / imaging / histology (collateral-removal screen, V1b)
CLINICAL_KW = ["biopsy","histolog","patholog","immunohistochem","cytolog","staining",
               "mri","ct scan"," ct ","pet scan","ultrasound","x-ray","radiograph","echocardiogram",
               "endoscopy","colonoscopy","bronchoscopy","culture","serolog","electrophysiolog",
               "excision","resection","angiogram","laparoscopy"]

# diagnosis header lines, most-specific first
DX_HEADERS = [
    r'(?im)^\s*(?:final|discharge)\s+diagnosis\s*:\s*(.+)$',
    r'(?im)^\s*(?:principal|main)\s+diagnosis\s*:\s*(.+)$',
    r'(?im)^\s*(?:admitting|admission)\s+diagnosis\s*:\s*(.+)$',
    r'(?im)^\s*diagnosis\s*:\s*(.+)$',
]

# ---------- api helpers (stdlib urllib; empty/None guarded) ----------
def _key():
    k = os.environ.get("NEBIUS_API_KEY")
    if not k: sys.exit("ERROR: NEBIUS_API_KEY not set.")
    return k

def call_chat(model, system, user, max_tokens=4000, retries=4):
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": max_tokens,
                       "messages": [{"role":"system","content":system},
                                    {"role":"user","content":user}]}).encode()
    req = urllib.request.Request(CHAT_URL, data=body, method="POST",
        headers={"Authorization":"Bearer "+_key(), "Content-Type":"application/json"})
    for a in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read().decode())
            txt = (d["choices"][0]["message"].get("content") or "").strip()
            if txt: return txt
        except (OSError, KeyError):  # OSError superclass of TimeoutError/URLError/HTTPError/ConnectionError
            pass                     # read-timeout in getresponse() propagates as bare TimeoutError -> now retried
        time.sleep(2**a)
    return ""   # caller treats empty as a failure, never a silent pass

def call_embed(inputs, retries=3):
    body = json.dumps({"model": EMBED, "input": inputs}).encode()
    req = urllib.request.Request(EMBED_URL, data=body, method="POST",
        headers={"Authorization":"Bearer "+_key(), "Content-Type":"application/json"})
    for a in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read().decode())
            return [row["embedding"] for row in d["data"]]
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError):
            time.sleep(2**a)
    return None

def cosine(a, b):
    import math
    dot = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(y*y for y in b))
    return dot/(na*nb) if na and nb else 0.0

def sentences(t): return [s for s in re.split(SENT_SPLIT, t.strip()) if s.strip()]

# ---------- item selection ----------
LEADINS = ["the patient was diagnosed with","patient was diagnosed with",
           "the patient was found to have","patient was found to have",
           "a diagnosis of","final diagnosis of","diagnosis of","diagnosed with"]
POST_MARKERS = [" consistent with "," suggestive of "," compatible with "," suspicious for "]
REJECT_SUBSTR = ["no formal diagnosis","no diagnosis","not mentioned","not provided",
                 "n/a","none","unknown","unremarkable"]
SENTENCEY = [" were "," was "," are "," is "," manifesting"," leading to",
             "however"," presented "," during "]
# F1: joiners that separate two independent diagnoses -> keep only the PRIMARY (earliest) part.
COMPOUND_JOINERS = [" secondary to ", " due to ", " co-existing ", " coexisting ",
                    " along with ", " with ", " and ", " plus "]
# F2: lay-mechanism / injury targets whose plain-language description IS the diagnosis -> reject
# (they cannot be made patient-invisible without removing findings). Conservative: may also drop a
# few "X injury" disease names (e.g. acute kidney injury) — a yield tradeoff, backstopped by Q_lay.
MECHANISM_RE = re.compile(r'\b(injur\w*|trauma\w*|particle|foreign body|burns?|fracture\w*|'
                          r'wound\w*|laceration|bite|sting|poisoning|overdose)\b', re.IGNORECASE)

def clean_diagnosis(raw):
    """Reduce a diagnosis-header capture to a bare PRIMARY noun-phrase, or None if not cleanly
    extractable. F1: split compounds to the primary component. F2: reject mechanism/injury dx."""
    dx = raw.strip().strip("-*•‑ ").strip()
    low = dx.lower()
    if " or " in low or " versus " in low or " vs " in low: return None   # differential -> ambiguous
    if any(s in low for s in REJECT_SUBSTR): return None                  # non-diagnosis line
    if MECHANISM_RE.search(low): return None                             # F2: lay-mechanism / injury dx
    for mk in POST_MARKERS:                                               # "...consistent with X" -> X
        if mk in low: dx = dx[low.index(mk)+len(mk):].strip(); low = dx.lower(); break
    changed = True
    while changed:                                                        # strip lead-in phrases
        changed = False
        for p in LEADINS:
            if low.startswith(p):
                dx = dx[len(p):].strip().strip(":,-").strip(); low = dx.lower(); changed = True
    for cut in [", which"," which "," that "]:                            # drop relative clause
        i = low.find(cut)
        if i > 0: dx = dx[:i].strip(); low = dx.lower()
    if "," in dx: dx = dx.split(",")[0].strip(); low = dx.lower()         # drop appositive tail
    cut_at = min([low.find(j) for j in COMPOUND_JOINERS if low.find(j) > 0] or [-1])  # F1 -> primary
    if cut_at > 0: dx = dx[:cut_at].strip(); low = dx.lower()
    if any(s in (" "+low+" ") for s in SENTENCEY): return None            # still a sentence
    dx = dx.rstrip(". ").strip()
    return dx if 3 <= len(dx) <= 80 else None

# ---------- 3-tier primary-diagnosis extraction ----------
# Tier 1/2 header keyword (broader than DX_HEADERS: also primary/clinical/working). DX_HEADERS is
# kept as-is for v2_scope's other-diagnosis listing.
_HDR_KW = r'(?:final|discharge|admission|admitting|principal|main|primary|clinical|working)?\s*diagnos[ie]s'
# Tier 3 narrative fallback patterns (used ONLY when no header yields a diagnosis).
NARR_PATTERNS = [
    r'(?i)diagnosed with (?:a |an )?([^.,;\n]{3,80})',
    r'(?i)(?:found to have|noted to have) (?:a |an )?([^.,;\n]{3,80})',
    r'(?i)consistent with (?:a |an )?([^.,;\n]{3,80})',
    r'(?i)(?:a|the) diagnosis of ([^.,;\n]{3,80})',
    r'(?i)(?:confirmed|revealed|demonstrated) (?:a |an |the )?([^.,;\n]{3,80})',
]
_NARR_MEASURE = re.compile(r'\d|×|\bmeasuring\b|\bcm\b|\bmm\b', re.IGNORECASE)   # measurement fragments
_NARR_VERBY   = re.compile(r'\b(underwent|presented|unresponsive|based|sloughed|impacted|showed|found|revealed)\b', re.IGNORECASE)
_NARR_BADEND  = {"for","but","and","of","with","based","to","on","in","at","the","a","an","that","which","was","were"}
def _narr_clean(cap):
    """Tightened cleaner for narrative captures (noisier than headers): reject measurements, verby
    fragments, over-long spans, and trailing prepositions/conjunctions."""
    dx = clean_diagnosis(cap)                          # base cleaner (differential/symptom/mechanism rejects)
    if not dx: return None
    if _NARR_MEASURE.search(dx): return None
    if _NARR_VERBY.search(dx): return None
    w = dx.split()
    if len(w) > 6: return None
    if w[-1].lower() in _NARR_BADEND: return None
    return dx

def extract_primary_diagnosis(source):
    """3-tier: (1) diagnosis header, value on the SAME line; (2) header, value on the NEXT non-empty
    line (section-style); (3) narrative fallback (diagnosed with / found to have / consistent with /
    a-the diagnosis of / confirmed-revealed-demonstrated), only if no header produced a diagnosis.
    Header tiers are preferred (cleaner); is_named_diagnosis (Fix 10) filters residual findings later."""
    lines = source.split("\n")
    for i, ln in enumerate(lines):                     # Tier 1 (same-line) + Tier 2 (next line)
        m = re.match(r'(?i)^\s*'+_HDR_KW+r'\s*:\s*(.*)$', ln)
        if not m: continue
        val = m.group(1).strip()
        if not val:                                    # Tier 2: value on the next non-empty line
            j = i + 1
            while j < len(lines) and not lines[j].strip(): j += 1
            val = lines[j].strip() if j < len(lines) else ""
        dx = clean_diagnosis(val) if val else None
        if dx: return dx
    for pat in NARR_PATTERNS:                          # Tier 3: narrative fallback
        for m in re.finditer(pat, source):
            dx = _narr_clean(m.group(1))
            if dx: return dx
    return None

# Fix 10: reject targets that are not bona-fide NAMED diagnoses — symptoms/complaints and purely
# descriptive findings. Cheap lexical stoplist first, then a one-question oracle classifier.
SYMPTOM_STOP = {"chest pain","belly pain","abdominal pain","stomach pain","back pain","flank pain",
                "headache","fever","nausea","vomiting","cough","dizziness","weakness","fatigue",
                "pain","swelling","bleeding","shortness of breath","draining wounds","rash",
                "diarrhea","constipation","painful urination"}
CLASSIFY_SYS = "You are a clinical terminology classifier. Answer only what is asked."
def is_named_diagnosis(target):
    """True iff `target` is a specific named disease/diagnosis (not a symptom/complaint/finding)."""
    low = target.lower().strip()
    if low in SYMPTOM_STOP or any(low.endswith(" "+s) for s in SYMPTOM_STOP):
        return False, "symptom/complaint (stoplist)"
    q = (f'Is "{target}" a SPECIFIC NAMED disease or diagnosis (e.g. tuberculosis, glioblastoma, '
         f'follicular lymphoma), as opposed to (a) a symptom or chief complaint (e.g. chest pain, '
         f'fever, draining wounds) or (b) a purely descriptive finding (e.g. "a large mass", '
         f'"damaged tissue spreading through the bowel")? Answer YES if it is a named diagnosis, '
         f'NO otherwise, then a short reason.')
    ans = call_chat(ORACLE, CLASSIFY_SYS, q, max_tokens=200)
    return (_yn(ans) == "YES"), (ans[:180] or "no answer")

def load_clean_controls(include_hf=False):
    """Unified clean-control (τ=0) loader. Always the 200 calibration controls; with include_hf,
    also the ADDABLE rows of the GuyDor007/medisimplifier-dataset test split (HF input->input,
    HF output->clean_ref), skipping any row whose input already matches a calibration control."""
    recs = json.load(open(CAL, encoding="utf-8"))
    controls = [{"idx": str(r["idx"]), "input": r["input"], "clean_ref": r["clean_ref"], "origin": "calib200"}
                for r in recs if r.get("condition")=="clean" and r.get("error_type")=="none"]
    if include_hf:
        os.environ.setdefault("HF_HUB_OFFLINE","1"); os.environ.setdefault("HF_DATASETS_OFFLINE","1")
        from datasets import load_dataset
        ds = load_dataset("GuyDor007/medisimplifier-dataset", split="test")
        norm = lambda s: re.sub(r'\s+', ' ', (s or '')).strip()
        used = {norm(c["input"]) for c in controls}
        added = 0
        for i, x in enumerate(ds):
            if norm(x["input"]) in used: continue
            controls.append({"idx": f"hf{i}", "input": x["input"], "clean_ref": x["output"], "origin": "hf_test"})
            added += 1
        print(f"  [pool] +{added} addable HF test-split rows (skipped {len(ds)-added} already-used/dup)")
    return controls

def select_items(controls, n, seed):
    import random
    controls = sorted(controls, key=lambda r: str(r["idx"]))   # canonical order before seeded shuffle
    random.Random(seed).shuffle(controls)
    picked, rejected = [], []
    for r in controls:
        dx = extract_primary_diagnosis(r["input"])
        if not dx: continue
        ok, reason = is_named_diagnosis(dx)                 # Fix 10 classifier gate
        if not ok:
            rejected.append({"idx": r["idx"], "target": dx, "reason": reason})
            print(f"  [select] REJECT idx={r['idx']} {dx!r} -> {reason}")
            continue
        picked.append((r, dx))
        print(f"  [select] keep   idx={r['idx']} {dx!r} [{r.get('origin','')}]")
        if len(picked) >= n: break
    return picked, rejected

# ---------- editor (DeepSeek) ----------
FORMS_SYS = "You are a clinical terminology expert. Output only what is asked, no commentary."
# Fix 12: F4 must return ONLY the diagnosis's NAMING forms. Cue-words that mark an elicited line as a
# symptom / finding / manifestation / anatomical location (NOT a diagnosis name) -> drop it in the post-filter.
FORM_EXCLUDE_RE = re.compile(
    r'\b(pain|swelling|spasm\w*|weakness|fever|bleeding|delay\w*|lesion|mass|growth|fluid|nodule|'
    r'edema|oedema|rash|cough|nausea|vomit\w*|seizure|ulcer|discharge|tissue|duct|lobe|region|'
    r'area|upper|lower|scan|biopsy|x-ray|mri|\bct\b|caused by|spread)\b', re.IGNORECASE)
def elicit_forms(target, clean_ref):
    """F4 pass 1 (Fix 12): list ONLY the NAMING forms of the target present in this summary — the
    technical name, abbreviations, true clinical SYNONYMS / named subtypes, and a plain-language
    paraphrase OF THE NAME. NEVER symptoms, findings, lab/imaging results, manifestations, locations,
    severity/timing qualifiers, or the cause."""
    p = (f'DIAGNOSIS: "{target}"\n\nSUMMARY:\n[BEGIN SUMMARY]\n{clean_ref}\n[END SUMMARY]\n\n'
         f'List ONLY the ways this diagnosis is NAMED in the summary, one phrase per line: the '
         f'technical name, any abbreviation, any true CLINICAL SYNONYM or named subtype that denotes '
         f'the same disease (e.g. "Parsonage-Turner syndrome" for brachial plexopathy), and a '
         f'plain-language paraphrase OF THE NAME (e.g. "fast-growing blood cancer" for leukemia).\n'
         f'Do NOT list symptoms, signs, physical/lab/imaging findings, manifestations, disease '
         f'locations, severity or timing qualifiers, or the cause. (For "West syndrome" do NOT list '
         f'"bending spasms" or "developmental delays"; for a bile-duct tumor do NOT list "leftover '
         f'tumor tissue in the bile duct".) If unsure whether a phrase is a NAME or a FINDING, EXCLUDE it. '
         f'Output only the naming phrases, one per line - no numbering, no commentary.')
    txt = call_chat(EDITOR, FORMS_SYS, p, max_tokens=400)
    out = []
    for ln in txt.splitlines():
        f = ln.strip(" -*\t•").strip()
        if not (2 <= len(f) <= 80): continue
        if FORM_EXCLUDE_RE.search(f): continue        # Fix 12 post-filter: drop finding/location-like lines
        if f.lower() in (x.lower() for x in out): continue
        out.append(f)
    return out[:12]

EDITOR_SYS = ("You are a careful medical-text editor. You remove one specified diagnosis "
              "from a patient summary and leave everything else exactly as written.")
EDITOR_USER = '''Remove the diagnosis "__TARGET__" from the patient summary below, in EVERY section it appears (hospital course, summary, impressions, admission/discharge diagnosis lines).

Remove EVERY form that conveys it, including these forms found in this summary:
__FORMS__
- plus the technical name, any abbreviation, any clinical SYNONYM or named subtype, and any plain-language paraphrase (e.g. "leukemia" -> "fast-growing blood cancer").

DELETION-ONLY - the following are forbidden:
- Do NOT add, invent, rename, or rephrase any other content.
- Do NOT write a placeholder in place of the removed diagnosis. If removing it empties a labelled line OR a section header (an inline "Diagnosis: ..." line, OR a header on its own line such as "Discharge Diagnosis:" whose only content was the diagnosis), DELETE THE WHOLE HEADER/LABEL too - never leave an empty "Diagnosis:" / "Discharge Diagnosis:" header, and never write "No diagnosis", "None", or similar.
- Keep every OTHER diagnosis, medication, dose, lab value, finding, procedure, and instruction exactly as written - same words, same numbers.
- If the diagnosis is embedded in a sentence that ALSO states an INDEPENDENT clinical fact - its cause/etiology, prognosis, that a disease has SPREAD or progressed, or a separate co-finding - remove ONLY the words that name or describe "__TARGET__" and KEEP the independent fact, rephrasing minimally so the sentence still reads. Do NOT delete the whole sentence. Example: "The nerve damage was caused by the spread of her blood cancer." -> keep that her blood cancer had spread; drop only the nerve-damage (diagnosis) part.

Then fix ONLY grammar so the text reads cleanly, adding NO new information. In particular, repair any reference the removal left dangling: if a sentence now begins with a pronoun or connective ("This", "These", "That", "It", "Also", "Then") whose subject you removed, either restore a neutral noun subject (e.g. "This was caused by the spread of her blood cancer." -> "The arm problem was caused by the spread of her blood cancer." WITHOUT re-naming the diagnosis) or drop the orphaned clause. Also fix stubs like a sentence that now ends mid-thought (e.g. "doctors found the tissue holding the intestines and") or a header left with no content.

After editing, NEITHER a lay reader NOR the text itself may state or plainly imply "__TARGET__", while every other fact remains. Output ONLY the edited summary - no commentary, no markers.

SUMMARY (between the markers):
[BEGIN SUMMARY]
__SUMMARY__
[END SUMMARY]'''

_HDR_EMPTY = re.compile(r'^\s*(final |discharge |admission |admitting |principal |main )?diagnosis\s*:\s*$', re.I)
_HDR_NEXT  = re.compile(r'^\s*[A-Z][A-Za-z /]{1,40}:?\s*$')
def clean_editor_output(txt):
    """Strip prompt markers; Fix 13: also drop any diagnosis header left orphaned (label alone on its
    line, body removed, followed by a blank line / another header / end-of-text)."""
    if not txt: return txt
    for m in ("[BEGIN SUMMARY]", "[END SUMMARY]", "<<<", ">>>"): txt = txt.replace(m, "")
    txt = re.sub(r'^\s*(edited summary|summary)\s*:?\s*', '', txt, flags=re.I)
    lines = txt.split("\n"); keep = []; i = 0
    while i < len(lines):
        if _HDR_EMPTY.match(lines[i]):                     # a diagnosis header with an empty value
            j = i + 1
            while j < len(lines) and lines[j].strip() == "": j += 1
            if j >= len(lines) or _HDR_NEXT.match(lines[j]) or _HDR_EMPTY.match(lines[j]):
                i += 1; continue                           # orphaned -> skip the header line
        keep.append(lines[i]); i += 1
    txt = re.sub(r'\n{3,}', '\n\n', "\n".join(keep))       # collapse blank run left by the removed header
    return txt.strip()

# Fix 14 detection (informational, surfaced for V4): a section/paragraph opening with a demonstrative
# or connective whose antecedent may have been removed. Not a gate.
_DANGLE = re.compile(r'(?:\n\s*\n|\n[A-Z][A-Za-z /]{1,40}\n)\s*(This|These|That|It|Also|Then)\b'
                     r'[^\n.]*\b(was|were|had|is|are|caused|showed|pointed)\b', re.IGNORECASE)
def dangling_pronoun_flag(edited):
    return bool(edited) and bool(_DANGLE.search(edited))

def editor_edit(clean_ref, target, forms):
    forms_block = "\n".join(f"- {f}" for f in forms) if forms else "- (none additional)"
    user = (EDITOR_USER.replace("__TARGET__", target)
                       .replace("__FORMS__", forms_block)
                       .replace("__SUMMARY__", clean_ref))
    return clean_editor_output(call_chat(EDITOR, EDITOR_SYS, user, max_tokens=4000))

# ---------- V1 surface (mechanical name-form absence) ----------
COMMON = {"multiple","chronic","acute","bilateral","benign","malignant","primary","secondary",
          "severe","disease","disorder","syndrome","injury","injuries","infection","tumor",
          "tumour","cancer","failure","progressive","congenital","associated","mutation",
          "particle","involvement","process","inflammatory","recurrent"}
def target_forms(target):
    forms = {target.lower()}
    m = re.search(r'\(([^)]{1,20})\)', target)          # parenthetical abbrev
    if m: forms.add(m.group(1).strip().lower())
    # longest SPECIFIC (non-generic) medical word as a coarse head-term; skip category words
    # like "multiple"/"chronic"/"infection" that are common English and cause false name-hits.
    words = [w for w in re.findall(r'[A-Za-z]{5,}', target)
             if w.lower() not in COMMON and w.lower() not in {"with","without","right","left"}]
    if words: forms.add(max(words, key=len).lower())
    return sorted(forms)

# Fix 15: content-word overlap matcher for SHORT name-phrases. Grammatical stopwords only (medical
# content words like "tumor"/"hole"/"muscle" are KEPT so a rephrase is still caught).
STOP15 = {"the","a","an","in","of","on","to","and","or","with","that","this","these","those","was",
          "were","is","are","by","for","from","into","onto","at","as","its","his","her","below",
          "above","near","over","under","around","some","other","two","one","type","types","caused",
          "causing","made","known"}
def _content_words(phrase):
    return [w for w in re.findall(r'[a-z]{3,}', phrase.lower()) if w not in STOP15]

def v1_surface(edited, target, forms):
    """F9 + Fix 15: absence of name/abbrev/head-term and elicited synonyms/paraphrase, by exact
    word-boundary match AND a fuzzy content-word overlap for SHORT name-phrases (catches trivial
    rephrases). max_sim is RECORDED (>=0.70 triage flag) but does NOT gate."""
    extra = {f.lower() for f in forms if f and f.lower() not in COMMON and len(f.strip()) >= 4}
    check_forms = sorted(set(target_forms(target)) | extra)
    el = edited.lower()
    name_hits = [f for f in check_forms if re.search(r'\b'+re.escape(f)+r'\b', el)]
    # Fix 15: fuzzy content-word overlap for SHORT name-phrases (2-4 content words) — catches trivial
    # rephrases ("Returning jaw tumor" -> "jaw tumor that kept coming back"; "hole in the muscle below
    # the lungs" -> "hole in the muscle"). Long definitional glosses (>4 content words) are SKIPPED so
    # retained FINDINGS that merely share words with a gloss are not falsely flagged (e.g. idx 928).
    el_tokens = set(re.findall(r'[a-z]{3,}', el))
    fuzzy_hits = []
    for f in check_forms:
        if re.search(r'\b'+re.escape(f)+r'\b', el): continue          # already an exact hit
        cw = _content_words(f)
        if not (2 <= len(cw) <= 4): continue                          # only short name-phrases
        present = sum(1 for w in cw if w in el_tokens)
        if present >= max(2, -(-len(cw)*6//10)):                      # >= ceil(0.6*n), min 2
            fuzzy_hits.append({"form": f, "present": present, "n": len(cw)})
    sents = sentences(edited)
    embs = call_embed([f"the patient has {target}"] + sents) if sents else None
    max_sim, flagged = None, None
    if embs:
        tgt, sent_e = embs[0], embs[1:]
        sims = [cosine(tgt, e) for e in sent_e]
        if sims:
            max_sim = max(sims); flagged = sents[sims.index(max_sim)]
    passed = (len(name_hits)==0 and len(fuzzy_hits)==0)   # Fix 15: fuzzy leak also fails V1
    return {"forms_checked": check_forms, "name_hits": name_hits, "fuzzy_hits": fuzzy_hits,
            "max_sentence_similarity": None if max_sim is None else round(max_sim,4),
            "high_similarity_flag": bool(max_sim is not None and max_sim >= 0.70),
            "flagged_sentence": flagged, "embed_ok": embs is not None,
            "note": "pass = exact name/synonym forms absent AND no short-form content-word overlap (Fix 15)",
            "pass_provisional": bool(passed)}

# ---------- V1b deletion-only diff (no collateral clinical removal) ----------
def v1b_deletion_only(clean_ref, edited, target):
    """The edit must be DELETION-ONLY of diagnosis-name spans: no medication dose, lab value,
    imaging, histology, or procedure content removed. Machine screen; collateral removal = reject.
    (Medication NAMES without a dose are cross-checked by the oracle Q_other_changed + V4.)"""
    import difflib
    a, b = clean_ref.split(), edited.split()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    removed = [" ".join(a[i1:i2]) for tag,i1,i2,j1,j2 in sm.get_opcodes()
               if tag in ("delete","replace")]
    removed_text = " ".join(removed)
    rl = " " + removed_text.lower() + " "
    form_words = {w for f in target_forms(target) for w in f.split()}
    removed_doses = [f"{v}{u}" for v,u in DOSE.findall(removed_text)]
    removed_labs  = [m.group(0).strip() for m in LAB.finditer(removed_text)]
    kw_hits = [k.strip() for k in CLINICAL_KW if k in rl and k.strip() not in form_words]
    collateral = bool(removed_doses or removed_labs or kw_hits)
    return {"removed_doses": removed_doses, "removed_labs": removed_labs,
            "removed_clinical_keywords": kw_hits, "removed_spans": removed[:12],
            "pass_provisional": (not collateral)}

# ---------- V2 scope + diff ----------
def v2_scope(clean_ref, edited, source):
    import difflib
    def dset(t): return {(v,u.lower()) for v,u in DOSE.findall(t)}
    doses_clean, doses_edit = dset(clean_ref), dset(edited)
    doses_missing = sorted(doses_clean - doses_edit)   # doses present in clean, gone from edited
    a, b = clean_ref.split(), edited.split()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    removed, added = [], []
    for tag,i1,i2,j1,j2 in sm.get_opcodes():
        if tag in ("delete","replace"): removed.append(" ".join(a[i1:i2]))
        if tag in ("insert","replace"): added.append(" ".join(b[j1:j2]))
    # other diagnosis header lines in source (besides the target) should still be conveyed
    other_dx = []
    for pat in DX_HEADERS:
        for m in re.finditer(pat, source):
            other_dx.append(m.group(1).strip().rstrip(". "))
    # dose preservation is the ONLY automated pass criterion; removed/added spans are surfaced for
    # human diff review, never auto-failed (difflib marks legitimate rephrase as add+delete).
    passed = (len(doses_missing)==0)
    return {"doses_clean": [f"{v}{u}" for v,u in sorted(doses_clean)],
            "doses_missing_in_edited": [f"{v}{u}" for v,u in doses_missing],
            "removed_spans": removed[:12], "added_spans": added[:12],
            "n_words_removed": sum(len(s.split()) for s in removed),
            "other_diagnosis_lines_in_source": other_dx,
            "pass_provisional": bool(passed)}

# ---------- V3 oracle (gpt-oss) ----------
ORACLE_SYS = "You are a meticulous clinical reviewer. Answer only what is asked, briefly."
def _yn(txt):
    m = re.search(r'\b(YES|NO)\b', txt, re.I)
    return m.group(1).upper() if m else None
def v3_oracle(source, clean_ref, edited, target):
    E  = f'EDITED SUMMARY:\n[BEGIN SUMMARY]\n{edited}\n[END SUMMARY]'
    OE = (f'ORIGINAL SUMMARY:\n[BEGIN SUMMARY]\n{clean_ref}\n[END SUMMARY]\n\n'
          f'EDITED SUMMARY:\n[BEGIN SUMMARY]\n{edited}\n[END SUMMARY]')
    # Q_name (GATE, must be NO) — named or lay-paraphrased?
    qn_p = (f'{E}\n\nDoes the text state the diagnosis "{target}" BY NAME, by an abbreviation, or by '
            f'a plain-language paraphrase a lay reader would recognize as that exact condition '
            f'(e.g. "fast-growing blood cancer" for leukemia)? Do NOT count indirect clues such as '
            f'medications, labs, or findings. Answer YES or NO, then one sentence why.')
    # Q_lay (F7 GATE, must be NO) — patient-recoverable from plain-language content?
    ql_p = (f'{E}\n\nForget technical medical knowledge. Could an ORDINARY PATIENT with no medical '
            f'training tell from the plain-language wording alone (everyday descriptions of what '
            f'happened, e.g. "pencil lead bits in the eye", "a germ was causing the infection in the '
            f'breastbone") that the patient has "{target}"? Answer YES or NO, then one sentence why.')
    # Q_expert (COVARIATE) — expert inference from the residual fingerprint
    qe_p = (f'{E}\n\nThe diagnosis "{target}" is not named. Could a medical EXPERT still infer the '
            f'patient has it from the remaining clinical details (medications, labs, imaging, '
            f'findings)? Answer YES or NO, then name the clue.')
    # Q_category (COVARIATE, Decision 1) — broad parent category kept without the specific diagnosis?
    qc_p = (f'{E}\n\nThe specific diagnosis "{target}" has been removed. Does the text still state the '
            f'BROAD disease CATEGORY it belongs to (e.g. "cancer", "an infection", "a nerve problem") '
            f'WITHOUT naming the specific diagnosis? Answer YES or NO, then the category if YES.')
    # Q_added (F8 GATE, must be NO) — fabrication / inserted claim
    qa_p = (f'{OE}\n\nDid the edit ADD, invent, or assert any NEW statement not supported by the '
            f'original (for example writing "No diagnosis" or a placeholder)? Answer YES or NO; if '
            f'YES, quote the added text.')
    # Q_removed_other (INFORMATIONAL -> human, F8) — other clinical fact removed?
    qr_p = (f'{OE}\n\nOther than the diagnosis "{target}" and its restatements, was any OTHER '
            f'medication, dose, lab, imaging, finding, or instruction REMOVED? Answer YES or NO; '
            f'if YES, name it.')
    qn = call_chat(ORACLE, ORACLE_SYS, qn_p, max_tokens=400)
    ql = call_chat(ORACLE, ORACLE_SYS, ql_p, max_tokens=400)
    qe = call_chat(ORACLE, ORACLE_SYS, qe_p, max_tokens=400)
    qc = call_chat(ORACLE, ORACLE_SYS, qc_p, max_tokens=400)
    qa = call_chat(ORACLE, ORACLE_SYS, qa_p, max_tokens=400)
    qr = call_chat(ORACLE, ORACLE_SYS, qr_p, max_tokens=400)
    qn_v, ql_v, qe_v, qc_v, qa_v, qr_v = _yn(qn), _yn(ql), _yn(qe), _yn(qc), _yn(qa), _yn(qr)
    return {"q_name_present_answer": qn_v, "q_name_present_reason": qn[:300],        # GATE: want NO
            "q_lay_recoverable_answer": ql_v, "q_lay_recoverable_reason": ql[:300],  # GATE: want NO (F7)
            "q_expert_infer_answer": qe_v, "q_expert_infer_reason": qe[:300],        # covariate
            "q_category_retained_answer": qc_v, "q_category_retained_reason": qc[:300], # covariate (Dec1)
            "q_added_answer": qa_v, "q_added_reason": qa[:300],                      # GATE: want NO (F8)
            "q_removed_other_answer": qr_v, "q_removed_other_reason": qr[:300],      # informational -> human
            "tau_pass": (qn_v == "NO" and ql_v == "NO" and qa_v == "NO"),
            "patient_recoverable": 1 if ql_v == "YES" else 0,   # F7 / Decision 2 (gate driver)
            "expert_recoverable": 1 if qe_v == "YES" else 0,    # covariate
            "category_retained": 1 if qc_v == "YES" else 0,     # covariate (Decision 1)
            "needs_human_collateral_check": (qr_v == "YES")}    # F8 human adjudication

# ---------- Q_finding PRE-FILTER (finding-survival triage; NON-GATING) ----------
# Held-out validation (v1-v5 on the full 95-item labeled census) plateaued at ~75% leak-recall /
# ~93% retention; gpt-oss temp-0 is non-deterministic and 5x-majority does NOT stabilize it
# (fingerprint variance dominates: a clean item flipped YES*5 <-> NO*5 across independent runs).
# So Q_finding is a PRE-FILTER, never a gate: it does NOT touch tau_pass or auto_gates_all_pass.
# q_finding_prefilter=YES flags an item as a LIKELY finding-survival leak (needs_full_v4=True,
# high priority). Per the NO-QUICK-ACCEPTS policy, V4 reviews EVERY item regardless.
QF_FP_SYS = "You are a clinical educator. Return ONLY valid JSON."
def _qf_fp_prompt(t):
    return (f'For the diagnosis "{t}", produce its "diagnostic fingerprint": specific things a SIMPLIFIED '
    "PATIENT SUMMARY might contain that would let someone recognize this exact diagnosis EVEN IF its name "
    "were deleted. Three lists: 1. pathognomonic_findings 2. anatomy_mechanism 3. characteristic_treatments "
    "(only treatments a LAYPERSON would recognize as implying it). EXCLUDE items fitting many diagnoses and "
    'treatments only a specialist would link. Return JSON {"pathognomonic_findings":[],"anatomy_mechanism":[],'
    '"characteristic_treatments":[]}.')
QF_SYS = ("You judge whether a specific diagnosis remains RECOVERABLE BY A LAYPERSON in an edited discharge "
    "summary after its name was removed. Answer strictly in the requested three-line format.")
def _qf_prompt(t, fp, edited):
    return (f'The diagnosis "{t}" and its NAME have been removed from the edited summary below. A diagnostic '
    "fingerprint (things to watch for) is provided; judge holistically. Read EVERY sentence - reason-for-admission, "
    "hospital course, exam/lab/imaging FINDINGS, PROCEDURES, TREATMENTS/medications, and all diagnosis/discharge lines.\n\n"
    "QUESTION: Ignoring the removed name, does the edited summary still let a layperson UNDERSTAND WHAT THE CONDITION "
    "SPECIFICALLY IS - its defining finding, bodily defect, mechanism, or a revealing treatment - well enough that "
    "deleting the technical name did NOT truly conceal the diagnosis? (They need NOT produce the medical term.)\n\n"
    "DECISIVE TEST - SPECIFIC vs BROAD FAMILY: is the retained phrase the ACTUAL CONDITION ITSELF (recovers the "
    "complete patient-level diagnosis, nothing meaningful hidden), or only the BROAD FAMILY it belongs to with a "
    "specific member/subtype still hidden?\n"
    "  SPECIFIC (YES): 'depression'; 'appendicitis'/'a worn-out knee'/'blocked heart arteries'. If the retained "
    "phrase IS the diagnosis even without its technical modifier, it is SPECIFIC.\n"
    "  BROAD (NO + category_retained=1): 'cancer near the kidney'/'kidney cancer' (kind unknown); 'lung cancer that "
    "has spread'; 'skin cancer that spread deeper into the skin' (squamous vs basal vs melanoma unknown); 'a type of "
    "brain tumor'; 'a mental-health condition'; 'an infection'.\n\n"
    "FIX-1 TREATMENTS/PROCEDURES THAT REVEAL THE DIAGNOSIS (YES): a treatment/procedure that REMOVES or REPLACES a "
    "specific body part, or CORRECTS a specific defect, reveals the condition -> YES (appendectomy->appendicitis; "
    "knee replacement->worn-out knee; valve replacement->diseased valve; bypass->blocked arteries; copper->copper "
    "deficiency; insulin pump->type-1 diabetes). CARVE-OUT (NOT recovery -> NO): a procedure revealing only a broad "
    "organ-cancer whose subtype is still hidden (kidney removed -> kidney cancer, kind unknown); OR an UNRELATED "
    "coincident lesion/procedure (e.g. brain surgery for a cyst is NOT evidence of a pituitary cause of a hormone "
    "disorder) - the treatment must plausibly be FOR this diagnosis, not a coincidence.\n\n"
    "Answer NO if what remains is ONLY: bare SYMPTOMS; a BROAD family (subtype hidden); a NONSPECIFIC finding shared "
    "by many diseases (a mass, inflammation, white-matter changes) - NO even when paired with a specialist-only "
    "marker; or a SPECIALIST-ONLY marker a layperson cannot decode (gene name like NOTCH3, drug/regimen like "
    "afatinib/R-CHOP, cornstarch dosing, raw lab value).\n\n"
    f"DIAGNOSTIC FINGERPRINT:\n{fp}\n\nEDITED SUMMARY:\n{edited}\n\n"
    "Output EXACTLY three lines:\nq_finding_answer: YES or NO\ncategory_retained: 0 or 1 or NA\nq_finding_reason: one line.")
def q_finding_prefilter(target, edited):
    """1x Q_finding v5, NON-GATING pre-filter. Returns (answer 'YES'|'NO'|'ABSTAIN', category_retained, reason)."""
    if not edited:
        return ("ABSTAIN", None, "no edit produced")
    fp = call_chat(ORACLE, QF_FP_SYS, _qf_fp_prompt(target), max_tokens=800)
    a  = call_chat(ORACLE, QF_SYS, _qf_prompt(target, fp, edited), max_tokens=3000)
    m  = re.search(r"q_finding_answer\s*:?\s*(YES|NO)", a, re.I)
    mc = re.search(r"category_retained\s*:?\s*(0|1|NA)", a, re.I)
    mr = re.search(r"q_finding_reason\s*:?\s*(.+)", a)
    return ((m.group(1).upper() if m else "ABSTAIN"),
            (mc.group(1).upper() if mc else None),
            (mr.group(1).strip()[:300] if mr else a[:200]))

# ---------- main (Step 0) ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=22, help="validation batch size (~20-25)")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--pool", choices=["calib","expanded"], default="calib",
                    help="calib = 200 calibration controls only; expanded = + addable HF test-split rows")
    args = ap.parse_args()
    _key()
    controls = load_clean_controls(include_hf=(args.pool=="expanded"))
    if args.pool == "expanded":
        # draw NET-NEW items from the ADDABLE rows only (the 200 calib controls were already mined
        # in the calib run; the final stratum unions all batches' accepts). Honors "from addable rows".
        controls = [c for c in controls if c.get("origin") == "hf_test"]
        # top-up: exclude idx already generated in prior expanded batches so this run is net-new
        import glob
        used = set()
        for f in glob.glob(OUT_TMPL.format(seed="*").replace(".json", "_expanded.json")):
            try:
                for it in json.load(open(f, encoding="utf-8")).get("items", []): used.add(str(it["idx"]))
            except Exception: pass
        before = len(controls)
        controls = [c for c in controls if str(c["idx"]) not in used]
        print(f"  [pool] excluded {before-len(controls)} idx already in prior expanded batches (net-new top-up)")
    print(f"loaded {len(controls)} clean controls (pool={args.pool})")
    items, sel_rejected = select_items(controls, args.n, args.seed)
    print(f"selected {len(items)} named-diagnosis clean controls "
          f"({len(sel_rejected)} rejected by target-type filter, Fix 10)")

    out = []
    out_path = OUT_TMPL.format(seed=args.seed)
    if args.pool == "expanded":                       # clobber-safe: don't overwrite calib runs
        out_path = out_path.replace(".json", "_expanded.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    def _save():                                      # crash-safe: rewrite full payload after every item
        json.dump({"step": 0,
                   "tau_definition": "patient-invisible primary-diagnosis drop: name+abbrev+lay-paraphrase "
                                     "absent (Q_name NO) AND not lay-recoverable (Q_lay NO, F7/§6 gate) AND "
                                     "no fabrication (Q_added NO); deletion-only. Covariates (never gate): "
                                     "expert_recoverable, category_retained.",
                   "fixes": "F1-F16 + Q_finding pre-filter (NON-GATING triage; tau_pass unchanged)",
                   "editor": EDITOR, "oracle": ORACLE, "embed": EMBED, "seed": args.seed, "pool": args.pool,
                   "selection_rejected_by_target_type": sel_rejected,   # Fix 10 audit trail
                   "note": "Automated gates are SCREENS only. human_verdict is authoritative; V4 reviews "
                           "ALL items (no quick-accepts). INCREMENTAL SAVE: rewritten after every item.",
                   "items": out}, open(out_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    for i, (r, target) in enumerate(items, 1):
        idx = str(r["idx"]); clean_ref = r["clean_ref"]; source = r["input"]
        print(f"[{i}/{len(items)}] idx={idx}  target={target!r}")
        forms  = elicit_forms(target, clean_ref)          # F4 pass 1
        edited = editor_edit(clean_ref, target, forms)    # F4 pass 2 (+F3/F5/F6)
        # Fix 16b (INFORMATIONAL only — NOT a gate): does the diagnosis appear in the SUMMARY in some
        # elicited form? Retro-simulation showed gating on this over-rejects genuine lay-paraphrase
        # drops (elicited form strings do not word-boundary-exact-match the clean_ref phrasing) while
        # missing the real defects, so it is surfaced for V4, never enforced. Fix 16a (no_op) is the gate.
        forms_in_ref = [f for f in forms if re.search(r'\b'+re.escape(f.lower())+r'\b', clean_ref.lower())]
        rec = {
            "idx": idx, "target": target, "target_type": "primary",
            "origin": r.get("origin"),
            "target_in_clean_ref": bool(forms_in_ref),     # Fix 16b (informational flag, non-gating)
            "editor_ok": bool(edited),
            "no_op_edit": None,                            # Fix 16a (filled below)
            "target_forms_elicited": forms,
            "clean_ref": clean_ref, "edited_summary": edited,
            "V1_surface":   v1_surface(edited, target, forms) if edited else None,
            "V1b_deletion": v1b_deletion_only(clean_ref, edited, target) if edited else None,
            "V2_scope":     v2_scope(clean_ref, edited, source) if edited else None,
            "V3_oracle":    v3_oracle(source, clean_ref, edited, target) if edited else None,
            "patient_recoverable": None,           # GATE driver (F7/§6); mirrors V3
            "expert_recoverable": None,            # covariate
            "category_retained": None,             # covariate (Decision 1)
            "needs_human_collateral_check": None,  # F8: Q_removed_other -> human adjudication
            "coherence_dangling_flag": (dangling_pronoun_flag(edited) if edited else None),  # Fix 14 detection
            "q_finding_prefilter": None,           # NON-GATING pre-filter: YES=likely finding-survival leak
            "q_finding_category": None,            # category_retained per Q_finding (covariate cross-check)
            "q_finding_reason": None,
            "needs_full_v4": True,                 # V4 reviews ALL items; True=pre-filter flagged (priority)
            "auto_gates_all_pass": None,           # filled below (screen only, NOT acceptance)
            "human_verdict": "",                   # V4 fills: ACCEPT | REJECT | RETRY
            "human_note": "",
        }
        if edited:
            v3 = rec["V3_oracle"]
            rec["patient_recoverable"] = v3["patient_recoverable"]
            rec["expert_recoverable"]  = v3["expert_recoverable"]
            rec["category_retained"]   = v3["category_retained"]
            rec["needs_human_collateral_check"] = v3["needs_human_collateral_check"]
            rec["no_op_edit"] = (rec["V2_scope"]["n_words_removed"]==0) or (edited.strip()==clean_ref.strip())  # Fix 16a
            rec["auto_gates_all_pass"] = bool(
                rec["V1_surface"]["pass_provisional"] and
                rec["V1b_deletion"]["pass_provisional"] and
                rec["V2_scope"]["pass_provisional"] and
                v3["tau_pass"] and                 # tau_pass = Q_name NO AND Q_lay NO AND Q_added NO
                not rec["no_op_edit"])             # Fix 16a: empty/identical diff cannot be tau=1
            # Q_finding PRE-FILTER (NON-GATING: does NOT change tau_pass / auto_gates_all_pass above)
            qf_ans, qf_cat, qf_reason = q_finding_prefilter(target, edited)
            rec["q_finding_prefilter"] = qf_ans
            rec["q_finding_category"]  = qf_cat
            rec["q_finding_reason"]    = qf_reason
            rec["needs_full_v4"]       = (qf_ans != "NO")   # YES/ABSTAIN -> flag priority; V4 reviews all
        else:
            rec["no_op_edit"] = True               # target not in clean_ref -> no perturbation
            rec["auto_gates_all_pass"] = False
            rec["needs_full_v4"] = True            # no edit -> can't pre-filter -> full V4
        out.append(rec)
        _save()                                       # crash-safe incremental checkpoint
        time.sleep(0.3)

    _save()                                           # final write (identical payload)
    n_auto = sum(1 for o in out if o["auto_gates_all_pass"])
    n_pr0  = sum(1 for o in out if o["patient_recoverable"] == 0)
    n_cat  = sum(1 for o in out if o["category_retained"] == 1)
    n_hum  = sum(1 for o in out if o["needs_human_collateral_check"])
    print(f"\nwrote {out_path}")
    print(f"editor produced text: {sum(1 for o in out if o['editor_ok'])}/{len(out)}")
    print(f"auto-gates all-pass (SCREEN, not acceptance): {n_auto}/{len(out)}")
    print(f"patient_recoverable=0 (required for tau=1): {n_pr0}/{len(out)}")
    n_dang = sum(1 for o in out if o.get("coherence_dangling_flag"))
    print(f"category_retained=1 (covariate): {n_cat}/{len(out)} | needs_human_collateral_check: {n_hum}/{len(out)}")
    print(f"coherence_dangling_flag (Fix 14 detection): {n_dang}/{len(out)}")
    n_noop = sum(1 for o in out if o.get("no_op_edit"))
    n_notin = sum(1 for o in out if o.get("target_in_clean_ref") is False)
    print(f"Fix 16: no_op_edit (auto-failed): {n_noop}/{len(out)} | target_not_in_clean_ref: {n_notin}/{len(out)}")
    n_qf_yes = sum(1 for o in out if o.get("q_finding_prefilter") == "YES")
    n_v4 = sum(1 for o in out if o.get("needs_full_v4"))
    print(f"Q_finding PRE-FILTER (non-gating): YES(likely leak)={n_qf_yes}/{len(out)} | needs_full_v4 flagged={n_v4}/{len(out)}")
    print("NEXT: V4 human review — fill human_verdict per item (ALL items, no quick-accepts); then compute confirmed-genuine rate.")

if __name__ == "__main__":
    main()
