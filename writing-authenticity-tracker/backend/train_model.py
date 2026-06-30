"""
Train ML Classifier
=====================
Trains a logistic regression on synthetic labeled sessions to predict
P(honest / paste_heavy / auto_typed) from the 8-feature vector defined
in features.py.

Why logistic regression and not something fancier?
  - Fully interpretable: each feature gets a learned weight you can
    inspect and explain (important for a tool making accusations).
    "The model weighs paste_ratio 3.2x more heavily than blur_count" is
    a sentence you can actually say to someone.
  - Small dataset (1200 synthetic sessions) — a deep model would overfit.
  - Easy to retrain fast as features evolve.

Run with:
    python train_model.py

Produces model.pkl, loaded by ml_model.py at inference time.
"""

import pickle
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix

from synthetic_data import generate_dataset
from features import extract_features, features_to_vector, FEATURE_NAMES


def build_training_matrix(sessions):
    X, y = [], []
    for s in sessions:
        f = extract_features(
            text_len=s["final_text_length"],
            keystrokes=s["keystrokes"],
            pastes=s["pastes"],
            blurs=s["blurs"],
            session_duration_ms=s["session_duration_ms"],
            click_count=s["click_count"],
        )
        X.append(features_to_vector(f))
        y.append(s["label"])
    return np.array(X), np.array(y)


def main():
    print("Generating synthetic dataset...")
    sessions = generate_dataset(n_per_class=400)
    X, y = build_training_matrix(sessions)
    print(f"Dataset shape: {X.shape}, classes: {sorted(set(y))}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    clf = LogisticRegression(max_iter=1000)
    clf.fit(X_train_scaled, y_train)

    y_pred = clf.predict(X_test_scaled)
    print("\n=== Classification report (held-out test set) ===")
    print(classification_report(y_test, y_pred))
    print("=== Confusion matrix ===")
    print("Classes:", clf.classes_)
    print(confusion_matrix(y_test, y_pred))

    print("\n=== Learned feature weights per class ===")
    for i, cls in enumerate(clf.classes_):
        print(f"\n{cls}:")
        for name, weight in zip(FEATURE_NAMES, clf.coef_[i]):
            print(f"  {name:25s} {weight:+.3f}")

    with open("model.pkl", "wb") as f:
        pickle.dump({"model": clf, "scaler": scaler, "feature_names": FEATURE_NAMES}, f)
    print("\nSaved model.pkl")


if __name__ == "__main__":
    main()
