"""
train_model.py - Generische sklearn-Pipeline fuer Regression (z.B. TKM) und Klassifikation (z.B. Qualitaetsklasse).

Aufruf:
  python train_model.py --csv ../outputs/seg/image_features.csv --target tkm_g --drop image
  python train_model.py --csv daten.xlsx --target klasse --group feld_id

Prinzip: Baseline (Mittelwert/Mehrheit) vs. Ridge/LogReg vs. RandomForest vs. HistGradientBoosting,
         Kreuzvalidierung (bei kleinen n: Leave-One-Out), Out-of-fold-Vorhersagen, Bestes Modell speichern.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import (HistGradientBoostingClassifier, HistGradientBoostingRegressor,
                              RandomForestClassifier, RandomForestRegressor)
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, mean_absolute_error,
                             mean_squared_error, r2_score)
from sklearn.model_selection import GroupKFold, KFold, LeaveOneOut, StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from eda_tabular import load_table

RANDOM_STATE = 42


def infer_task(y: pd.Series) -> str:
    """Text/Kategorie/Bool -> Klassifikation; Ganzzahl mit <= 10 Werten -> Klassifikation; sonst Regression."""
    if not pd.api.types.is_numeric_dtype(y) or pd.api.types.is_bool_dtype(y):
        return "clf"
    if pd.api.types.is_integer_dtype(y) and y.nunique() <= 10:
        return "clf"
    return "reg"


def build_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    num = X.select_dtypes(include="number").columns.tolist()
    cat = [c for c in X.columns if c not in num]
    return ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), num),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                          ("oh", OneHotEncoder(handle_unknown="ignore"))]), cat),
    ])


def clean_features(X: pd.DataFrame) -> pd.DataFrame:
    """Entfernt konstante, fast leere und ID-artige Spalten (z.B. Dateinamen)."""
    drop = [c for c in X.columns
            if X[c].isna().mean() > 0.5 or X[c].nunique(dropna=True) <= 1
            or (not pd.api.types.is_numeric_dtype(X[c]) and X[c].nunique() == len(X))]
    if drop:
        print("Entfernte Spalten:", drop)
    return X.drop(columns=drop)


def candidate_models(task: str) -> dict:
    if task == "reg":
        return {
            "baseline_mean": DummyRegressor(strategy="mean"),
            "ridge": Ridge(alpha=1.0),
            "random_forest": RandomForestRegressor(n_estimators=400, min_samples_leaf=2,
                                                   random_state=RANDOM_STATE, n_jobs=-1),
            "hist_gb": HistGradientBoostingRegressor(max_depth=4, learning_rate=0.06,
                                                     min_samples_leaf=5, random_state=RANDOM_STATE),
        }
    return {
        "baseline_majority": DummyClassifier(strategy="most_frequent"),
        "logreg": LogisticRegression(max_iter=2000, class_weight="balanced"),
        "random_forest": RandomForestClassifier(n_estimators=400, class_weight="balanced",
                                                random_state=RANDOM_STATE, n_jobs=-1),
        "hist_gb": HistGradientBoostingClassifier(max_depth=4, learning_rate=0.06,
                                                  random_state=RANDOM_STATE),
    }


def make_cv(task, n, y, groups, n_splits):
    if groups is not None:
        return GroupKFold(n_splits=min(n_splits, groups.nunique()))
    if task == "reg":
        return LeaveOneOut() if n < 40 else KFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)
    min_class = y.value_counts().min()
    return StratifiedKFold(n_splits=max(2, min(n_splits, int(min_class))), shuffle=True,
                           random_state=RANDOM_STATE)


def score(task, y_true, y_pred) -> dict:
    if task == "reg":
        return {"r2": r2_score(y_true, y_pred), "mae": mean_absolute_error(y_true, y_pred),
                "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
                "mape_pct": float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100)}
    return {"accuracy": accuracy_score(y_true, y_pred), "f1_macro": f1_score(y_true, y_pred, average="macro")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--target", required=True)
    ap.add_argument("--task", default="auto", choices=["auto", "reg", "clf"])
    ap.add_argument("--drop", nargs="*", default=[], help="Spalten ohne Vorhersagewert (IDs, Leckage!)")
    ap.add_argument("--group", default=None, help="Gruppenspalte (z.B. Feld/Partie) gegen Leckage")
    ap.add_argument("--cv", type=int, default=5)
    ap.add_argument("--out", default="../outputs/model")
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    df = load_table(a.csv, a.sheet)
    if a.target not in df.columns:
        raise SystemExit(f"Zielspalte '{a.target}' nicht gefunden. Vorhanden: {list(df.columns)[:30]}")
    df = df.dropna(subset=[a.target]).reset_index(drop=True)
    unknown = [c for c in a.drop if c not in df.columns]
    if unknown:
        print("Hinweis: --drop-Spalten nicht vorhanden (ignoriert):", unknown)
    a.drop = [c for c in a.drop if c in df.columns]
    y = df[a.target]
    task = infer_task(y) if a.task == "auto" else a.task
    groups = df[a.group] if a.group else None
    X = clean_features(df.drop(columns=[a.target] + a.drop + ([a.group] if a.group else [])))
    print(f"Aufgabe: {'Regression' if task == 'reg' else 'Klassifikation'} | n={len(X)} | Features={X.shape[1]}")

    cv = make_cv(task, len(X), y, groups, a.cv)
    results, oof = {}, {}
    for name, model in candidate_models(task).items():
        pipe = Pipeline([("prep", build_preprocessor(X)), ("model", model)])
        pred = cross_val_predict(pipe, X, y, cv=cv, groups=groups)
        results[name] = score(task, y, pred)
        oof[name] = pred
        print(f"{name:18s}", {k: round(float(v), 4) for k, v in results[name].items()})

    key = "rmse" if task == "reg" else "f1_macro"
    non_base = {k: v for k, v in results.items() if not k.startswith("baseline")}
    best = (min if task == "reg" else max)(non_base, key=lambda k: non_base[k][key])
    print("Bestes Modell:", best)

    best_pipe = Pipeline([("prep", build_preprocessor(X)), ("model", candidate_models(task)[best])]).fit(X, y)
    joblib.dump({"pipeline": best_pipe, "features": list(X.columns), "target": a.target, "task": task},
                out / "best_model.joblib")
    pd.DataFrame({"y_true": y, **{f"oof_{k}": v for k, v in oof.items()}}).to_csv(out / "oof_predictions.csv",
                                                                                   index=False)
    json.dump({"best": best, "task": task, "n": len(X),
               "results": {k: {m: float(v) for m, v in r.items()} for k, r in results.items()}},
              open(out / "metrics.json", "w"), indent=2)

    # Permutation Importance (in-sample, nur zur Orientierung!)
    imp = permutation_importance(best_pipe, X, y, n_repeats=10, random_state=RANDOM_STATE,
                                 scoring="r2" if task == "reg" else "f1_macro")
    imp_df = pd.DataFrame({"feature": X.columns, "importance": imp.importances_mean}).sort_values(
        "importance", ascending=False)
    imp_df.to_csv(out / "feature_importance.csv", index=False)
    print(imp_df.head(10).round(4).to_string(index=False))

    fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
    if task == "reg":
        ax[0].scatter(y, oof[best], s=22)
        lim = [min(y.min(), oof[best].min()), max(y.max(), oof[best].max())]
        ax[0].plot(lim, lim, "k--", lw=1)
        ax[0].set_xlabel(f"{a.target} (gemessen)")
        ax[0].set_ylabel("Vorhersage (out-of-fold)")
        ax[0].set_title(f"{best}: R2={results[best]['r2']:.3f}, MAE={results[best]['mae']:.2f}")
    else:
        cm = confusion_matrix(y, oof[best])
        ax[0].imshow(cm, cmap="Blues")
        ax[0].set_title(f"{best}: Confusion Matrix")
    top = imp_df.head(10)[::-1]
    ax[1].barh(top["feature"], top["importance"])
    ax[1].set_title("Permutation Importance (in-sample)")
    fig.tight_layout()
    fig.savefig(out / "model_overview.png", dpi=120)
    print("->", out.resolve())


if __name__ == "__main__":
    main()
