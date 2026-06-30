# Writing Authenticity Tracker (v2)

A full-stack demo that logs typing behavior while someone writes — keystrokes,
paste events, tab switches, correction rate — and produces a **transparent,
multi-layer suspicion report**, not a binary "cheated / didn't cheat" verdict.

This is a prototype/demo project, not a production cheating-detection system.
Every real tool in this space (Turnitin, GPTZero, Grammarly Authorship) shares
the same fundamental limitation: behavioral signals are *evidence worth a
human look*, never proof. Every layer below says this explicitly.

---

## What's new in v2

v1 had one hand-tuned heuristic. v2 adds three more independent layers on
top, each addressing a specific weakness of the original:

| Layer | Fixes | How |
|---|---|---|
| **1. Heuristic** (v1, unchanged) | — | Hand-tuned weighted rules, fully transparent |
| **2. ML classifier** | "Weights were just guessed" | Logistic regression trained on synthetic labeled sessions |
| **3. Personalized baseline** | "Same threshold for every student is unfair" | Compares a session against *that student's own* recorded norm |
| **4. GenAI + agentic review** | "No text-level signal, no synthesis" | Claude analyzes the essay text itself, then an agent reasons over ALL the evidence and decides whether to flag + drafts a message |

Layers 2–4 are visible side-by-side in the report — they're not merged into
one fake "final number." You can see when they agree and when they don't,
which is itself useful information.

---

## Architecture

```
┌─────────────────┐        POST /analyze        ┌────────────────────────────┐
│  React frontend   │  ───────────────────────►   │  FastAPI backend             │
│  - calibration     │                              │                              │
│  - event capture   │   { keystrokes, pastes,      │  features.py (shared)        │
│  - report display  │     blurs, click_count,      │    ↓              ↓          │
│                    │     student_id, use_genai }   │  scoring.py    ml_model.py    │
└─────────────────┘  ◄───────────────────────    │  (heuristic)   (classifier)   │
                         combined report            │       ↓              ↓        │
                                                     │  baseline.py   genai_layer.py │
                                                     │  (personal norm) (Claude API)  │
                                                     └────────────────────────────┘
```

### Layer 1 — Heuristic (`scoring.py`)
Same as v1: five named, weighted signals (paste ratio, rhythm variance,
correction rate, tab switches, burst typing). Fully hand-readable.

### Layer 2 — ML classifier (`synthetic_data.py`, `features.py`, `train_model.py`, `ml_model.py`)
- `synthetic_data.py` simulates three realistic keystroke-level behavior
  patterns: `honest`, `paste_heavy`, `auto_typed` (a "humanizer" script that
  types with suspiciously uniform timing).
- `features.py` is the **single source of truth** for turning a raw session
  into an 8-number feature vector — both the heuristic and the ML model
  read from here, so they're always looking at the same underlying signals.
- `train_model.py` trains a logistic regression on 1,200 synthetic sessions
  and saves `model.pkl`. Logistic regression was chosen deliberately over
  something fancier: it's fully interpretable (every feature gets a
  readable learned weight), which matters for a tool that can make
  accusations.
- `ml_model.py` loads the model at inference time and returns class
  probabilities **plus the top 3 features that drove the prediction** —
  never a black-box label alone.

To retrain (e.g. after changing features or synthetic data):
```bash
cd backend
python train_model.py
```

### Layer 3 — Personalized baseline (`baseline.py`)
The fairness fix. A student records a short "calibration" writing sample
first (the frontend prompts for this on first use). Future sessions are
scored by how much they **deviate from that student's own normal typing**,
not from a one-size-fits-all global threshold. This catches things the
heuristic alone misses — e.g. in testing, a session that the heuristic
scored only 40/100 (moderate) was clearly flagged by the baseline
comparison as 92% more uniform and 100% fewer corrections than that
student's own established norm.

Storage is in-memory (resets when the server restarts) — a real deployment
would swap this for a database.

### Layer 4 — GenAI hybrid + agentic review (`genai_layer.py`)
**Optional** — requires `OPENAI_API_KEY` to be set as an environment
variable on the backend. Uses `gpt-4o-mini` by default (fast and cheap;
swap to `gpt-4o` in `genai_layer.py` for higher-quality reasoning at
higher cost per call). Two distinct uses of an LLM, kept separate
on purpose:

1. **Text-pattern analysis** — Claude reads the final essay text (not
   behavior) and assesses whether the writing style looks more like
   typical AI-generated prose or human writing. This is a genuinely
   different signal from the behavioral layers — it can agree or disagree
   with them, and the report shows both.
2. **Agentic review** — a second Claude call takes the *entire* combined
   report (heuristic + ML + baseline + text analysis) and acts like a
   careful teaching-assistant reviewer: decides whether the evidence is
   strong enough to flag (deliberately conservative — only flags when
   multiple signals agree), and if so, drafts a short, non-accusatory
   message asking the student to explain their process. Nothing is ever
   auto-sent — it's just drafted for a human to review.

If no API key is set, this layer cleanly reports itself as unavailable
and the rest of the app works exactly as before.

---

## Running it

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
python train_model.py        # trains model.pkl (only needed once, or after changing features)
uvicorn main:app --reload --port 8000
```

**Optional — enable the GenAI layer:**

PowerShell:
```powershell
$env:OPENAI_API_KEY="your-key-here"
uvicorn main:app --reload --port 8000
```

macOS/Linux:
```bash
export OPENAI_API_KEY="your-key-here"
uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000/` — the response shows `ml_model_available`
and `genai_available` so you can confirm what's active.

### 2. Frontend

In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`.

### 3. Try it

1. **First run**: you'll be asked to calibrate — type ~200+ characters
   naturally. This becomes your personal baseline.
2. **Honest session**: type a paragraph normally → submit → low heuristic
   score, ML predicts "honest," baseline shows no deviation.
3. **Paste test**: write something elsewhere, copy it, paste into the box
   → submit → heuristic spikes, ML predicts "paste_heavy" with high
   confidence.
4. **Auto-typer simulation**: hard to simulate by hand, but the baseline
   layer is specifically built to catch this — see `backend` test output
   in the project history for a worked example.
5. **GenAI toggle**: if you've set `OPENAI_API_KEY`, check "Run GenAI
   text analysis + agentic review" before submitting to see the text-level
   signal and the agent's drafted message (only appears if it decides to flag).

---

## Project structure

```
writing-authenticity-tracker/
├── backend/
│   ├── main.py             # FastAPI app, wires all 4 layers together
│   ├── scoring.py            # Layer 1: heuristic scorer
│   ├── features.py            # Shared feature extraction (used by all layers)
│   ├── synthetic_data.py      # Generates labeled training sessions
│   ├── train_model.py          # Trains the ML classifier → model.pkl
│   ├── ml_model.py              # Layer 2: ML inference
│   ├── baseline.py               # Layer 3: personalized baseline comparison
│   ├── genai_layer.py             # Layer 4: GenAI text analysis + agentic review
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx                  # Orchestrates calibration → writing → report
│   │   ├── CalibrationView.jsx       # Baseline recording flow
│   │   ├── ReportView.jsx             # Displays all 4 layers
│   │   ├── useSessionTracker.js        # Shared event-capture hook
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md
```

---

## Known limitations (honest, not just caveats)

- **Synthetic training data, not real student data.** The ML classifier has
  never seen a real human or a real cheater — it learned from simulated
  keystroke patterns. It will be much more confident than it should be on
  edge cases real students actually produce (disabilities, ESL typists,
  assistive tools, etc.).
- **In-memory baseline storage.** Restarting the server wipes all
  calibrated baselines. Fine for a demo, not for real use.
- **The agentic layer can still be wrong.** It's deliberately prompted to
  be conservative (require multiple agreeing signals before flagging), but
  it's still an LLM call and can misjudge nuance, especially on edge cases
  not represented in its prompt.
- **No real proctoring.** This only sees what happens inside the textarea.
  A student could write the essay on paper first, or use a second device,
  and none of these signals would catch it.
- **This should never be the sole basis for an academic integrity decision.**
  Every layer's output is explicitly framed as a prompt for a human
  conversation, not a verdict — and that framing should be preserved if
  you extend this further.
