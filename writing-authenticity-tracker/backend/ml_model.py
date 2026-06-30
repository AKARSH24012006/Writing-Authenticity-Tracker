"""
ML Model Inference
====================
Loads the trained classifier (model.pkl) and exposes a clean
predict() function used by main.py. Falls back gracefully if the
model file hasn't been trained yet.
"""

import pickle
import os
import numpy as np

from features import SessionFeatures, features_to_vector, FEATURE_NAMES

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")
_model_bundle = None


def _load():
    global _model_bundle
    if _model_bundle is None:
        if not os.path.exists(_MODEL_PATH):
            return None
        with open(_MODEL_PATH, "rb") as f:
            _model_bundle = pickle.load(f)
    return _model_bundle


def is_model_available() -> bool:
    return _load() is not None


def predict(features: SessionFeatures) -> dict:
    """Returns class probabilities + the top contributing features for
    the predicted class, so the result stays explainable rather than
    being a black-box label."""
    bundle = _load()
    if bundle is None:
        return None

    model = bundle["model"]
    scaler = bundle["scaler"]

    vec = np.array([features_to_vector(features)])
    vec_scaled = scaler.transform(vec)

    probs = model.predict_proba(vec_scaled)[0]
    classes = model.classes_
    prob_map = {cls: round(float(p) * 100, 1) for cls, p in zip(classes, probs)}

    predicted_class = classes[np.argmax(probs)]

    # Explainability: for the predicted class, show which features pushed
    # the prediction most (weight * standardized feature value)
    class_idx = list(classes).index(predicted_class)
    coefs = model.coef_[class_idx]
    contributions = vec_scaled[0] * coefs
    ranked = sorted(
        zip(FEATURE_NAMES, contributions), key=lambda x: abs(x[1]), reverse=True
    )
    top_factors = [
        {"feature": name, "influence": round(float(val), 3)}
        for name, val in ranked[:3]
    ]

    return {
        "predicted_class": predicted_class,
        "class_probabilities": prob_map,
        "top_factors": top_factors,
    }
