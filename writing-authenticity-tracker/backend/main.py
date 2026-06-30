"""
Writing Authenticity Tracker - Backend (v2)
=============================================
Now combines FOUR layers of analysis:

  1. Heuristic scorer   — transparent hand-tuned rules (v1, unchanged)
  2. ML classifier       — logistic regression trained on synthetic data
  3. Personalized baseline — compares this session to the student's own
                              recorded normal typing pattern (if calibrated)
  4. GenAI hybrid + agentic review — optional, requires OPENAI_API_KEY:
       - text-pattern analysis of the essay itself
       - an agentic reviewer that decides whether to flag + drafts a
         non-accusatory message

Layers 3 and 4 degrade gracefully: the app works fully without them
(no baseline calibrated yet / no API key set), and clearly reports
their own availability so the frontend can show what's active.

Run with:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from scoring import compute_report
from features import extract_features
from ml_model import predict as ml_predict, is_model_available
from baseline import save_baseline, has_baseline, compare_to_baseline
from genai_layer import analyze_text_patterns, review_session, genai_available

app = FastAPI(title="Writing Authenticity Tracker API v2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Request schemas ----------

class KeystrokeEvent(BaseModel):
    t: float
    key_type: str


class PasteEvent(BaseModel):
    t: float
    length: int


class BlurEvent(BaseModel):
    blur_t: float
    focus_t: Optional[float] = None


class SessionLog(BaseModel):
    final_text: str
    session_duration_ms: float
    keystrokes: List[KeystrokeEvent]
    pastes: List[PasteEvent]
    blurs: List[BlurEvent]
    click_count: int
    student_id: Optional[str] = "demo_student"
    is_calibration: Optional[bool] = False
    use_genai: Optional[bool] = False


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Writing Authenticity Tracker API v2 is running",
        "ml_model_available": is_model_available(),
        "genai_available": genai_available(),
    }


@app.post("/analyze")
def analyze_session(log: SessionLog):
    features = extract_features(
        text_len=len(log.final_text),
        keystrokes=log.keystrokes,
        pastes=log.pastes,
        blurs=log.blurs,
        session_duration_ms=log.session_duration_ms,
        click_count=log.click_count,
    )

    if log.is_calibration:
        save_baseline(log.student_id, features)
        return {
            "calibration_saved": True,
            "message": f"Baseline recorded for '{log.student_id}'. Future sessions will be compared against this norm.",
        }

    heuristic_report = compute_report(log)
    ml_result = ml_predict(features)

    baseline_result = None
    if has_baseline(log.student_id):
        baseline_result = compare_to_baseline(log.student_id, features)

    text_pattern_result = None
    agent_review = None
    if log.use_genai and genai_available():
        text_pattern_result = analyze_text_patterns(log.final_text)
        agent_review = review_session(
            heuristic_report, ml_result, text_pattern_result, baseline_result
        )

    return {
        "heuristic": heuristic_report,
        "ml": ml_result,
        "baseline_comparison": baseline_result,
        "text_pattern_analysis": text_pattern_result,
        "agent_review": agent_review,
        "layers_active": {
            "heuristic": True,
            "ml": ml_result is not None,
            "baseline": baseline_result is not None,
            "genai": text_pattern_result is not None,
        },
    }


@app.get("/baseline_status/{student_id}")
def baseline_status(student_id: str):
    return {"student_id": student_id, "has_baseline": has_baseline(student_id)}
