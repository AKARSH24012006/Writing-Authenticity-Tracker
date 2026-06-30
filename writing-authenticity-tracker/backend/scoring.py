"""
Scoring Engine
==============
Transparent, explainable heuristic scoring (v1).

Design philosophy:
  - No black-box "AI says you cheated" verdict.
  - Every signal is shown to the user with its raw value AND
    what it contributes to the final suspicion score.
  - The final score is a *suspicion score* (0-100), explicitly
    framed as "worth a human looking at", not proof of anything.

Signals used (v1 heuristic):
  1. Paste ratio       — % of final text that arrived via paste events
  2. Typing rhythm      — variance in time between keystrokes
                          (very low variance = robotic/auto-typed;
                           humans have natural irregular rhythm)
  3. Correction rate    — backspace/delete events per 100 characters
                          (humans make typos and fix them; pasted or
                           AI-generated text often has near-zero corrections)
  4. Tab-switch events  — how many times the window lost focus
                          (could indicate checking another tab/app)
  5. Burst typing       — large chunks of text appearing in a very
                          short time window without matching keystroke
                          events (a stronger paste-like signal even if
                          the paste event itself was suppressed)

Each signal contributes a WEIGHTED, CAPPED score. Weights are stored
as named constants so they're easy to find and tune later — this is
the first thing worth improving/experimenting with.
"""

from typing import List
import statistics


# ---------- Tunable weights (out of 100 total) ----------
WEIGHT_PASTE_RATIO = 35
WEIGHT_RHYTHM = 20
WEIGHT_CORRECTION_RATE = 20
WEIGHT_TAB_SWITCH = 10
WEIGHT_BURST_TYPING = 15


def compute_report(log) -> dict:
    text_len = max(len(log.final_text), 1)

    # ---------- 1. Paste ratio ----------
    total_pasted_chars = sum(p.length for p in log.pastes)
    paste_ratio = min(total_pasted_chars / text_len, 1.0)
    paste_score = paste_ratio * WEIGHT_PASTE_RATIO

    # ---------- 2. Typing rhythm variance ----------
    char_events = [k for k in log.keystrokes if k.key_type == "char"]
    intervals = []
    for i in range(1, len(char_events)):
        intervals.append(char_events[i].t - char_events[i - 1].t)

    if len(intervals) >= 5:
        mean_interval = statistics.mean(intervals)
        stdev_interval = statistics.pstdev(intervals)
        # Coefficient of variation: humans are typically > 0.4-0.5
        # Very low CV (robotic/auto-typed) is suspicious
        cv = stdev_interval / mean_interval if mean_interval > 0 else 0
        if cv < 0.15:
            rhythm_score = WEIGHT_RHYTHM  # very robotic
        elif cv < 0.35:
            rhythm_score = WEIGHT_RHYTHM * 0.5
        else:
            rhythm_score = 0  # natural human variance
        rhythm_label = round(cv, 3)
    else:
        # Not enough typed characters to judge rhythm
        # (e.g. text arrived almost entirely via paste)
        rhythm_score = 0
        rhythm_label = None

    # ---------- 3. Correction rate ----------
    correction_events = [
        k for k in log.keystrokes if k.key_type in ("backspace", "delete")
    ]
    corrections_per_100 = (len(correction_events) / text_len) * 100

    if corrections_per_100 < 0.5:
        correction_score = WEIGHT_CORRECTION_RATE  # almost no corrections = suspicious
    elif corrections_per_100 < 2:
        correction_score = WEIGHT_CORRECTION_RATE * 0.4
    else:
        correction_score = 0  # normal human typo/fix behavior

    # ---------- 4. Tab-switch / blur events ----------
    blur_count = len(log.blurs)
    total_blur_time = sum(
        (b.focus_t - b.blur_t) for b in log.blurs if b.focus_t is not None
    )
    if blur_count == 0:
        tab_score = 0
    elif blur_count <= 2:
        tab_score = WEIGHT_TAB_SWITCH * 0.3
    else:
        tab_score = WEIGHT_TAB_SWITCH

    # ---------- 5. Burst typing detection ----------
    # Look for any single keystroke gap where a large amount of new
    # text appears to have shown up — a paste-like signature even if
    # no explicit paste event fired (e.g. some "type slowly" extensions
    # still insert text in chunks).
    burst_flag = False
    char_count_total = len(char_events)
    if char_count_total > 0 and text_len > 0:
        typed_ratio = char_count_total / text_len
        if typed_ratio < 0.5 and total_pasted_chars < text_len * 0.3:
            # Lots of text exists that's neither typed nor explicitly pasted
            burst_flag = True

    burst_score = WEIGHT_BURST_TYPING if burst_flag else 0

    # ---------- Final score ----------
    total_score = round(
        paste_score + rhythm_score + correction_score + tab_score + burst_score, 1
    )
    total_score = min(total_score, 100)

    if total_score < 25:
        verdict_label = "Low suspicion — signals consistent with natural typing"
    elif total_score < 55:
        verdict_label = "Moderate suspicion — some signals worth a manual look"
    else:
        verdict_label = "High suspicion — multiple signals suggest pasted/automated text"

    return {
        "suspicion_score": total_score,
        "verdict_label": verdict_label,
        "disclaimer": (
            "This is a behavioral suspicion score based on typing patterns, "
            "not proof of cheating. Many honest explanations exist for any "
            "single signal (pasting your own notes, accessibility tools, "
            "fast typing speed, etc). Use this as a prompt for a human "
            "conversation, not an automatic penalty."
        ),
        "signals": [
            {
                "name": "Paste ratio",
                "value": f"{round(paste_ratio * 100, 1)}% of text arrived via paste",
                "contribution": round(paste_score, 1),
                "max_contribution": WEIGHT_PASTE_RATIO,
            },
            {
                "name": "Typing rhythm variance",
                "value": (
                    f"Coefficient of variation: {rhythm_label}"
                    if rhythm_label is not None
                    else "Not enough typed keystrokes to measure"
                ),
                "contribution": round(rhythm_score, 1),
                "max_contribution": WEIGHT_RHYTHM,
            },
            {
                "name": "Correction rate",
                "value": f"{round(corrections_per_100, 2)} corrections per 100 characters",
                "contribution": round(correction_score, 1),
                "max_contribution": WEIGHT_CORRECTION_RATE,
            },
            {
                "name": "Tab-switch / focus loss",
                "value": f"{blur_count} tab switch(es), {round(total_blur_time / 1000, 1)}s away from window",
                "contribution": round(tab_score, 1),
                "max_contribution": WEIGHT_TAB_SWITCH,
            },
            {
                "name": "Burst / unaccounted text",
                "value": "Detected text not explained by typing or paste events" if burst_flag else "No unexplained bursts detected",
                "contribution": round(burst_score, 1),
                "max_contribution": WEIGHT_BURST_TYPING,
            },
        ],
        "raw_stats": {
            "final_text_length": text_len,
            "total_keystrokes": len(log.keystrokes),
            "total_pastes": len(log.pastes),
            "total_pasted_chars": total_pasted_chars,
            "session_duration_seconds": round(log.session_duration_ms / 1000, 1),
            "click_count": log.click_count,
        },
    }
