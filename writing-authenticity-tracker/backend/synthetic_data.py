"""
Synthetic Session Generator
============================
Generates labeled fake writing sessions to train the ML classifier.

Why synthetic? We have no real student data (and shouldn't — privacy).
Instead we SIMULATE three realistic behavior patterns based on what
each one would actually look like at the keystroke level:

  1. "honest"       — natural human typing: irregular rhythm, regular
                       typo/backspace corrections, occasional short pastes
                       (e.g. pasting their own earlier notes), few tab switches
  2. "paste_heavy"   — most of the text arrives via one or two large paste
                       events, almost no typing, zero corrections
  3. "auto_typed"    — text arrives via simulated keystrokes but with
                       suspiciously UNIFORM timing (a humanizer / auto-typer
                       script) and near-zero corrections — harder to catch
                       than paste_heavy, which is exactly why it's a useful
                       training example

Each session is reduced to the same feature vector used at inference
time (see features.py) so the classifier trains on exactly what it
will see in production.
"""

import random
import numpy as np


def _simulate_honest_session(text_len=600):
    """Natural typing: irregular intervals, regular corrections, light pasting."""
    keystrokes = []
    t = 0
    chars_typed = 0
    corrections = 0

    while chars_typed < text_len:
        # Human inter-keystroke interval: log-normal-ish, irregular
        interval = max(30, random.gauss(180, 90))
        t += interval
        keystrokes.append((t, "char"))
        chars_typed += 1

        # Occasional typo + backspace (humans correct themselves)
        if random.random() < 0.045:
            t += random.gauss(150, 60)
            keystrokes.append((t, "backspace"))
            corrections += 1

    # Maybe one small legitimate paste (e.g. pasting own earlier note)
    pastes = []
    if random.random() < 0.3:
        paste_len = random.randint(10, 60)
        pastes.append((t * random.uniform(0.3, 0.7), paste_len))

    # Light, occasional tab switching
    blurs = []
    if random.random() < 0.4:
        blur_t = t * random.uniform(0.2, 0.8)
        blurs.append((blur_t, blur_t + random.uniform(2000, 15000)))

    return {
        "final_text_length": text_len,
        "keystrokes": keystrokes,
        "pastes": pastes,
        "blurs": blurs,
        "session_duration_ms": t,
        "click_count": random.randint(5, 25),
        "label": "honest",
    }


def _simulate_paste_heavy_session(text_len=600):
    """Most text arrives via one large paste, minimal typing/corrections."""
    keystrokes = []
    t = 0

    # A little bit of typing (e.g. title or intro line) before the big paste
    small_typed = random.randint(0, 40)
    for _ in range(small_typed):
        t += max(30, random.gauss(170, 80))
        keystrokes.append((t, "char"))

    # The big paste
    paste_len = text_len - small_typed
    t += random.uniform(500, 4000)
    pastes = [(t, paste_len)]

    blurs = []
    if random.random() < 0.2:
        blur_t = t * 0.5
        blurs.append((blur_t, blur_t + random.uniform(1000, 5000)))

    return {
        "final_text_length": text_len,
        "keystrokes": keystrokes,
        "pastes": pastes,
        "blurs": blurs,
        "session_duration_ms": t + random.uniform(500, 3000),
        "click_count": random.randint(1, 4),
        "label": "paste_heavy",
    }


def _simulate_auto_typed_session(text_len=600):
    """Text arrives via keystrokes but with suspiciously uniform timing
    and almost zero corrections — simulates a 'humanizer' auto-typer."""
    keystrokes = []
    t = 0
    base_interval = random.uniform(40, 90)

    for _ in range(text_len):
        # Very low variance — small jitter only, NOT human-like irregularity
        interval = base_interval + random.uniform(-5, 5)
        t += interval
        keystrokes.append((t, "char"))

    # Auto-typers almost never simulate typos
    corrections = 0
    if random.random() < 0.1:
        idx = random.randint(0, len(keystrokes) - 1)
        keystrokes.insert(idx, (keystrokes[idx][0], "backspace"))

    pastes = []
    blurs = []
    if random.random() < 0.15:
        blur_t = t * 0.5
        blurs.append((blur_t, blur_t + random.uniform(1000, 4000)))

    return {
        "final_text_length": text_len,
        "keystrokes": keystrokes,
        "pastes": pastes,
        "blurs": blurs,
        "session_duration_ms": t,
        "click_count": random.randint(1, 6),
        "label": "auto_typed",
    }


def generate_dataset(n_per_class=400, seed=42):
    random.seed(seed)
    np.random.seed(seed)

    sessions = []
    for _ in range(n_per_class):
        text_len = random.randint(250, 1200)
        sessions.append(_simulate_honest_session(text_len))
    for _ in range(n_per_class):
        text_len = random.randint(250, 1200)
        sessions.append(_simulate_paste_heavy_session(text_len))
    for _ in range(n_per_class):
        text_len = random.randint(250, 1200)
        sessions.append(_simulate_auto_typed_session(text_len))

    random.shuffle(sessions)
    return sessions


if __name__ == "__main__":
    data = generate_dataset(5)
    for s in data[:3]:
        print(s["label"], "| keystrokes:", len(s["keystrokes"]), "| pastes:", s["pastes"])
