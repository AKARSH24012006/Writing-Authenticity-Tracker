"""
GenAI Layer (OpenAI version)
==============================
Two distinct uses of an LLM, kept clearly separate because they do
different jobs:

  1. analyze_text_patterns() — TEXT-SIDE signal. Asks the model to look at
     the final essay text itself (not behavior) and assess whether the
     writing style/patterns look more like typical AI-generated prose
     or human writing. This is a SEPARATE signal from the behavioral
     score — the two are combined into a hybrid report, not merged
     into one number, so the user can see when they agree or disagree.

  2. review_session() — AGENTIC layer. Takes the FULL report (behavioral
     + ML + text signals) and acts like a teaching-assistant reviewer:
     decides whether the session is worth flagging, and if so, drafts a
     non-accusatory message asking the student to explain. This is
     "agentic" in the real sense — it reasons over the evidence and
     produces an action (a drafted message), not just a description.

Both functions are OPTIONAL — they require OPENAI_API_KEY to be set.
If it's missing, both return None and the app falls back to the
heuristic + ML report only (layers 1-3 are unaffected).
"""

import os
import json
import re

try:
    from openai import OpenAI
    _client = OpenAI() if os.environ.get("OPENAI_API_KEY") else None
except ImportError:
    _client = None

# gpt-4o-mini is fast/cheap and plenty capable for this; swap to "gpt-4o"
# for higher quality reasoning if you want, at higher cost per call.
MODEL = "gpt-4o-mini"


def genai_available() -> bool:
    return _client is not None


def _extract_json(text: str):
    """Strip any stray markdown fences/prose around the JSON object."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    return json.loads(text)


def _chat_json(prompt: str, max_tokens: int = 500) -> str:
    """Calls the OpenAI chat completions API and returns raw text content.
    Uses response_format=json_object so the model is constrained to
    return valid JSON directly, instead of relying purely on prompting."""
    response = _client.chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        temperature=0.3,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def analyze_text_patterns(essay_text: str) -> dict:
    """Text-side AI-writing-pattern check. Returns None if no API key set."""
    if _client is None:
        return None
    if len(essay_text.strip()) < 50:
        return {
            "ai_likelihood_score": 0,
            "reasoning": "Text too short for meaningful pattern analysis.",
        }

    prompt = f"""You are assisting a teacher in evaluating whether a student essay shows writing patterns common in AI-generated text (overly uniform sentence structure, generic transitions, lack of a specific personal voice, etc) versus patterns typical of human student writing (some awkwardness, specific personal detail, varied sentence length, minor inconsistency).

Give your honest assessment as calibrated evidence, not a verdict — many honest student essays may still score moderately here, and that is expected and fine.

Essay text:
---
{essay_text[:4000]}
---

Respond with ONLY a JSON object, no other text:
{{"ai_likelihood_score": <integer 0-100>, "reasoning": "<2-3 sentence plain-language explanation citing specific patterns you noticed>"}}"""

    raw = _chat_json(prompt, max_tokens=400)
    try:
        return _extract_json(raw)
    except (json.JSONDecodeError, AttributeError, TypeError):
        return {"ai_likelihood_score": None, "reasoning": "Could not parse model response."}


def review_session(behavioral_report: dict, ml_result: dict, text_result: dict, baseline_comparison: dict) -> dict:
    """Agentic layer: reasons over the full combined evidence and decides
    whether to flag the session, producing a drafted message if so."""
    if _client is None:
        return None

    evidence_summary = {
        "heuristic_suspicion_score": behavioral_report.get("suspicion_score"),
        "heuristic_signals": [
            {"name": s["name"], "value": s["value"]} for s in behavioral_report.get("signals", [])
        ],
        "ml_prediction": ml_result,
        "text_pattern_analysis": text_result,
        "baseline_comparison": baseline_comparison,
    }

    prompt = f"""You are a fair, careful teaching-assistant reviewer helping a teacher decide whether a writing session is worth a follow-up conversation with the student. You have behavioral evidence (typing patterns), an ML model's prediction, a text-pattern analysis, and possibly a comparison to the student's own personal baseline.

Evidence:
{json.dumps(evidence_summary, indent=2)}

Your job:
1. Decide: should this be flagged for a human conversation? Be conservative — only recommend flagging when MULTIPLE signals agree, since any single signal alone has many honest explanations.
2. If flagged, draft a SHORT, warm, non-accusatory message a teacher could send the student, asking them to explain their writing process. Never assume guilt. Frame it as curiosity, not accusation.
3. If not flagged, briefly say why the evidence doesn't warrant it.

Respond with ONLY a JSON object, no other text:
{{"should_flag": <true/false>, "confidence": "<low/medium/high>", "reasoning": "<2-3 sentences synthesizing the evidence>", "drafted_message": "<message text if flagged, or empty string if not>"}}"""

    raw = _chat_json(prompt, max_tokens=500)
    try:
        return _extract_json(raw)
    except (json.JSONDecodeError, AttributeError, TypeError):
        return {
            "should_flag": False,
            "confidence": "low",
            "reasoning": "Could not parse agent response.",
            "drafted_message": "",
        }
