"""
Personalized Baseline
========================
The fairness fix: instead of judging every student against the same
fixed global thresholds (which unfairly flags naturally fast typists,
non-native typists, or anyone whose honest rhythm doesn't match the
"average" assumption baked into the heuristic), this module lets a
student record a short calibration sample first. Future sessions are
then scored by how much they DEVIATE from that student's own baseline,
not from a generic population assumption.

Storage: simple in-memory dict keyed by student_id, swappable for a
real DB later (this is a demo — no persistence across server restarts).
"""

from features import SessionFeatures

# student_id -> baseline stats (mean/spread of their own honest typing)
_baselines: dict[str, dict] = {}


def save_baseline(student_id: str, features: SessionFeatures):
    """Store a student's calibration session as their personal baseline."""
    _baselines[student_id] = {
        "rhythm_cv": features.rhythm_cv,
        "corrections_per_100": features.corrections_per_100,
        "chars_per_second": features.chars_per_second,
        "typed_ratio": features.typed_ratio,
    }


def has_baseline(student_id: str) -> bool:
    return student_id in _baselines


def get_baseline(student_id: str):
    return _baselines.get(student_id)


def compare_to_baseline(student_id: str, features: SessionFeatures) -> dict:
    """Returns deviation info: how far this session is from the student's
    own established norm, expressed as plain-language deltas rather than
    a single opaque number."""
    baseline = _baselines.get(student_id)
    if baseline is None:
        return None

    def pct_change(current, base):
        if base == 0:
            return None
        return round(((current - base) / abs(base)) * 100, 1)

    rhythm_delta = pct_change(features.rhythm_cv, baseline["rhythm_cv"])
    correction_delta = pct_change(
        features.corrections_per_100, baseline["corrections_per_100"]
    )
    speed_delta = pct_change(features.chars_per_second, baseline["chars_per_second"])

    # Flag if this session looks meaningfully MORE "robotic" than the
    # student's own established norm — i.e. less rhythm variance and
    # fewer corrections than how they normally write.
    deviation_flags = []
    if rhythm_delta is not None and rhythm_delta < -40:
        deviation_flags.append(
            f"Typing rhythm is {abs(rhythm_delta)}% more uniform than this student's own baseline"
        )
    if correction_delta is not None and correction_delta < -50:
        deviation_flags.append(
            f"Correction rate is {abs(correction_delta)}% lower than this student's own baseline"
        )
    if speed_delta is not None and speed_delta > 150:
        deviation_flags.append(
            f"Typing speed is {round(speed_delta)}% faster than this student's own baseline"
        )

    return {
        "baseline_exists": True,
        "rhythm_delta_pct": rhythm_delta,
        "correction_delta_pct": correction_delta,
        "speed_delta_pct": speed_delta,
        "deviation_flags": deviation_flags,
        "baseline_stats": baseline,
    }
