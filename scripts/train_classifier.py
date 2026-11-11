#!/usr/bin/env python3
"""Обучение классификатора категории заявки и оценка качества."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "processed" / "procurement_requests_clean.csv"
MODEL = ROOT / "agent" / "models" / "category_clf.joblib"
METRICS = ROOT / "reports" / "model_metrics.json"
FIG = ROOT / "reports" / "figures" / "fig_confusion.png"

MODEL.parent.mkdir(parents=True, exist_ok=True)

BLUE = "#0071e3"
TEXT = "#1d1d1f"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "text.color": TEXT})


def main() -> None:
    df = pd.read_csv(CLEAN, encoding="utf-8-sig")
    X = df["request_text"].fillna("")
    y = df["category"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=2,
            max_features=9000,
            sublinear_tf=True,
        )),
        ("clf", LogisticRegression(
            max_iter=2500,
            C=2.0,
            class_weight="balanced",
            random_state=42,
        )),
    ])
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average="macro")
    weighted_f1 = f1_score(y_test, y_pred, average="weighted")
    majority = y_test.value_counts(normalize=True).max()

    cv = cross_val_score(pipeline, X, y, cv=5, scoring="f1_macro")
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    labels = sorted(y.unique())
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)

    # Топ-признаки по классам — для объяснимости.
    vec = pipeline.named_steps["tfidf"]
    clf = pipeline.named_steps["clf"]
    terms = np.array(vec.get_feature_names_out())
    top_terms: dict[str, list[str]] = {}
    for i, label in enumerate(clf.classes_):
        order = np.argsort(clf.coef_[i])[-8:][::-1]
        top_terms[label] = [str(terms[j]) for j in order]

    metrics = {
        "n_samples": int(len(df)),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "n_classes": int(y.nunique()),
        "accuracy": round(float(accuracy), 4),
        "macro_f1": round(float(macro_f1), 4),
        "weighted_f1": round(float(weighted_f1), 4),
        "majority_baseline": round(float(majority), 4),
        "cv_macro_f1_mean": round(float(cv.mean()), 4),
        "cv_macro_f1_std": round(float(cv.std()), 4),
        "classification_report": report,
        "top_terms": top_terms,
        "labels": labels,
    }
    METRICS.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    joblib.dump(pipeline, MODEL)

    # Матрица ошибок
    fig, ax = plt.subplots(figsize=(8.6, 7.0))
    im = ax.imshow(cm_norm, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=42, ha="right", fontsize=8)
    ax.set_yticklabels(labels, fontsize=8)
    for i in range(len(labels)):
        for j in range(len(labels)):
            if cm[i, j] == 0:
                continue
            ax.text(j, i, f"{cm_norm[i, j]:.2f}", ha="center", va="center",
                    fontsize=7, color="white" if cm_norm[i, j] > 0.55 else TEXT)
    ax.set_xlabel("Предсказанная категория")
    ax.set_ylabel("Истинная категория")
    ax.set_title(f"Матрица ошибок (нормированная), accuracy = {accuracy:.2f}", loc="left", fontsize=12, pad=12)
    fig.colorbar(im, ax=ax, fraction=0.035, pad=0.03)
    fig.tight_layout()
    fig.savefig(FIG, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print(f"Accuracy: {accuracy:.4f}")
    print(f"Macro F1: {macro_f1:.4f}")
    print(f"Weighted F1: {weighted_f1:.4f}")
    print(f"CV macro F1: {cv.mean():.4f} ± {cv.std():.4f}")
    print(f"Модель: {MODEL}")
    print(f"Метрики: {METRICS}")


if __name__ == "__main__":
    main()
