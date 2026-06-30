"""
Feature Extraction
====================
Single source of truth for turning a raw session log into a numeric
feature vector. Used by BOTH:
  - the heuristic scorer (scoring.py)
  - the ML classifier (ml_model.py)

Keeping this in one place means the two scorers are always looking
at the same underlying signals, just combining them differently
(hand-tuned weights vs learned weights).
"""

import statistics
from dataclasses import dataclass


@dataclass
class SessionFeatures:
    paste_ratio: float          # 0-1, fraction of final text from pastes
    rhythm_cv: float             # coefficient of variation of keystroke intervals
    corrections_per_100: float   # backspace/delete events per 100 chars
    blur_count: int              # number of tab-switch events
    blur_seconds: float          # total time spent away from window
    typed_ratio: float           # fraction of final text explained by typed keystrokes
    chars_per_second: float      # overall typing throughput
    click_count: int


def extract_features(text_len, keystrokes, pastes, blurs, session_duration_ms, click_count) -> SessionFeatures:
    """
    keystrokes: list of (t_ms, key_type) tuples or objects with .t/.key_type
    pastes: list of (t_ms, length) tuples or objects with .t/.length
    blurs: list of (blur_t, focus_t) tuples or objects with .blur_t/.focus_t
    """
    text_len = max(text_len, 1)

    def _get(item, attr, idx):
        return getattr(item, attr) if hasattr(item, attr) else item[idx]

    # --- paste ratio ---
    total_pasted = sum(_get(p, "length", 1) for p in pastes)
    paste_ratio = min(total_pasted / text_len, 1.0)

    # --- typing rhythm ---
    char_times = [
        _get(k, "t", 0) for k in keystrokes
        if _get(k, "key_type", 1) == "char"
    ]
    intervals = [char_times[i] - char_times[i - 1] for i in range(1, len(char_times))]

    if len(intervals) >= 5:
        mean_iv = statistics.mean(intervals)
        std_iv = statistics.pstdev(intervals)
        rhythm_cv = std_iv / mean_iv if mean_iv > 0 else 0.0
    else:
        rhythm_cv = -1.0  # sentinel: not enough data to judge

    # --- corrections ---
    correction_count = sum(
        1 for k in keystrokes if _get(k, "key_type", 1) in ("backspace", "delete")
    )
    corrections_per_100 = (correction_count / text_len) * 100

    # --- tab switches ---
    blur_count = len(blurs)
    blur_seconds = sum(
        (_get(b, "focus_t", 1) - _get(b, "blur_t", 0)) / 1000
        for b in blurs
        if _get(b, "focus_t", 1) is not None
    )

    # --- typed ratio / throughput ---
    typed_ratio = min(len(char_times) / text_len, 1.0)
    duration_s = max(session_duration_ms / 1000, 0.001)
    chars_per_second = text_len / duration_s

    return SessionFeatures(
        paste_ratio=paste_ratio,
        rhythm_cv=rhythm_cv,
        corrections_per_100=corrections_per_100,
        blur_count=blur_count,
        blur_seconds=blur_seconds,
        typed_ratio=typed_ratio,
        chars_per_second=chars_per_second,
        click_count=click_count,
    )


def features_to_vector(f: SessionFeatures):
    """Convert to a fixed-order numeric vector for the ML model.
    rhythm_cv sentinel (-1) is passed through as-is — the model learns
    its meaning from training data rather than us hardcoding a rule."""
    return [
        f.paste_ratio,
        f.rhythm_cv,
        f.corrections_per_100,
        f.blur_count,
        f.blur_seconds,
        f.typed_ratio,
        f.chars_per_second,
        f.click_count,
    ]


FEATURE_NAMES = [
    "paste_ratio",
    "rhythm_cv",
    "corrections_per_100",
    "blur_count",
    "blur_seconds",
    "typed_ratio",
    "chars_per_second",
    "click_count",
]
