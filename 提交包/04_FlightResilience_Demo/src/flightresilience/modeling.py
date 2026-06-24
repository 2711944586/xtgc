from __future__ import annotations

import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .config import DEMO_DIR, FIGURES_DIR, MODELS_DIR, PROCESSED_DIR, TABLES_DIR, ensure_dirs
from .utils import write_json


TARGET = "ArrDel15"

NUMERIC_FEATURES = [
    "Month",
    "DayOfWeek",
    "is_weekend",
    "crs_dep_hour",
    "Distance",
    "CRSElapsedTime",
    "origin_hist_delay_rate",
    "dest_hist_delay_rate",
    "route_hist_delay_rate",
    "airline_hist_delay_rate",
    "origin_hour_hist_delay_rate",
    "origin_rolling_3h_delay_rate",
    "origin_rolling_3h_volume",
    "hour_sin",
    "hour_cos",
    "month_sin",
    "month_cos",
]

CATEGORICAL_FEATURES = [
    "Origin",
    "Dest",
    "Reporting_Airline",
    "dep_time_block",
]

FORBIDDEN_FEATURES = [
    "DepTime",
    "DepDelay",
    "DepDelayMinutes",
    "DepDel15",
    "ArrTime",
    "ArrDelay",
    "ArrDelayMinutes",
    "CarrierDelay",
    "WeatherDelay",
    "NASDelay",
    "SecurityDelay",
    "LateAircraftDelay",
    "ActualElapsedTime",
    "AirTime",
]


def completed_model_frame(df: pd.DataFrame) -> pd.DataFrame:
    cols = [TARGET, "split", "FlightDate"] + NUMERIC_FEATURES + CATEGORICAL_FEATURES
    return df[df["is_completed"] == 1][cols].copy()


def make_preprocessor() -> ColumnTransformer:
    try:
        encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=True, min_frequency=20)
    except TypeError:
        encoder = OneHotEncoder(handle_unknown="ignore")
    numeric = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())])
    categorical = Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", encoder)])
    return ColumnTransformer(
        [
            ("num", numeric, NUMERIC_FEATURES),
            ("cat", categorical, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )


def make_models(seed: int = 42) -> dict[str, Pipeline]:
    return {
        "logistic": Pipeline(
            [
                ("preprocess", make_preprocessor()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=500,
                        class_weight="balanced",
                        solver="saga",
                        n_jobs=-1,
                        random_state=seed,
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("preprocess", make_preprocessor()),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=120,
                        min_samples_leaf=30,
                        max_depth=14,
                        class_weight="balanced_subsample",
                        n_jobs=-1,
                        random_state=seed,
                    ),
                ),
            ]
        ),
        "lightgbm": Pipeline(
            [
                ("preprocess", make_preprocessor()),
                (
                    "model",
                    LGBMClassifier(
                        n_estimators=240,
                        learning_rate=0.045,
                        max_depth=-1,
                        num_leaves=31,
                        min_child_samples=60,
                        subsample=0.85,
                        colsample_bytree=0.85,
                        class_weight="balanced",
                        random_state=seed,
                        verbose=-1,
                    ),
                ),
            ]
        ),
    }


def evaluate_predictions(y_true: pd.Series, proba: np.ndarray, threshold: float = 0.5) -> dict[str, float]:
    pred = (proba >= threshold).astype(int)
    metrics: dict[str, float] = {
        "accuracy": float(accuracy_score(y_true, pred)),
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, proba)),
        "pr_auc": float(average_precision_score(y_true, proba)),
        "brier": float(brier_score_loss(y_true, proba)),
        "log_loss": float(log_loss(y_true, np.clip(proba, 1e-5, 1 - 1e-5))),
    }
    cm = confusion_matrix(y_true, pred).ravel()
    if len(cm) == 4:
        metrics.update({"tn": int(cm[0]), "fp": int(cm[1]), "fn": int(cm[2]), "tp": int(cm[3])})
    return metrics


def find_threshold(y_true: pd.Series, proba: np.ndarray) -> tuple[float, dict[str, float]]:
    best_threshold = 0.5
    best = {"f1": -1.0}
    for threshold in np.linspace(0.20, 0.80, 61):
        metrics = evaluate_predictions(y_true, proba, float(threshold))
        if metrics["f1"] > best["f1"]:
            best_threshold = float(threshold)
            best = metrics
    return best_threshold, best


def permutation_importance_fast(
    model: Pipeline, X: pd.DataFrame, y: pd.Series, base_score: float, sample_size: int = 5000
) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    sample_idx = rng.choice(X.index.to_numpy(), size=min(sample_size, len(X)), replace=False)
    Xs = X.loc[sample_idx].copy()
    ys = y.loc[sample_idx]
    rows = []
    for col in NUMERIC_FEATURES + CATEGORICAL_FEATURES:
        Xp = Xs.copy()
        Xp[col] = rng.permutation(Xp[col].to_numpy())
        try:
            score = average_precision_score(ys, model.predict_proba(Xp)[:, 1])
        except Exception:
            score = np.nan
        rows.append({"feature": col, "importance": float(base_score - score)})
    return pd.DataFrame(rows).sort_values("importance", ascending=False)


def shap_summary_for_tree(model: Pipeline, X: pd.DataFrame, sample_size: int = 1500) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    sample_idx = rng.choice(X.index.to_numpy(), size=min(sample_size, len(X)), replace=False)
    Xs = X.loc[sample_idx]
    preprocessor = model.named_steps["preprocess"]
    estimator = model.named_steps["model"]
    Xt = preprocessor.transform(Xs)
    feature_names = preprocessor.get_feature_names_out()
    if hasattr(Xt, "toarray"):
        Xt_for_shap = Xt.toarray()
    else:
        Xt_for_shap = Xt
    explainer = shap.TreeExplainer(estimator)
    values = explainer.shap_values(Xt_for_shap)
    if isinstance(values, list):
        values = values[1]
    values = np.asarray(values)
    if values.ndim == 3:
        values = values[:, :, 1]
    mean_abs = np.abs(values).mean(axis=0)
    rows = pd.DataFrame({"feature": feature_names, "mean_abs_shap": mean_abs})
    rows["source_feature"] = rows["feature"].str.replace(r"^(num|cat)__", "", regex=True)
    for base in CATEGORICAL_FEATURES:
        rows.loc[rows["source_feature"].str.startswith(f"{base}_"), "source_feature"] = base
    grouped = rows.groupby("source_feature", as_index=False)["mean_abs_shap"].sum()
    return grouped.sort_values("mean_abs_shap", ascending=False)


def train_models() -> dict:
    ensure_dirs()
    df = pd.read_parquet(PROCESSED_DIR / "flights_features.parquet")
    mf = completed_model_frame(df)
    train = mf[mf["split"] == "train"]
    valid = mf[mf["split"] == "valid"]
    test = mf[mf["split"] == "test"]

    feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    X_train, y_train = train[feature_cols], train[TARGET].astype(int)
    X_valid, y_valid = valid[feature_cols], valid[TARGET].astype(int)
    X_test, y_test = test[feature_cols], test[TARGET].astype(int)

    models = make_models()
    results = []
    fitted = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        valid_proba = model.predict_proba(X_valid)[:, 1]
        threshold, valid_metrics = find_threshold(y_valid, valid_proba)
        test_proba = model.predict_proba(X_test)[:, 1]
        test_metrics = evaluate_predictions(y_test, test_proba, threshold)
        results.append(
            {
                "model": name,
                "threshold": threshold,
                "split": "valid",
                **{f"valid_{k}": v for k, v in valid_metrics.items()},
                **{f"test_{k}": v for k, v in test_metrics.items()},
            }
        )
        fitted[name] = model

    metrics_df = pd.DataFrame(results).sort_values(["test_pr_auc", "test_roc_auc"], ascending=False)
    best_name = str(metrics_df.iloc[0]["model"])
    best_threshold = float(metrics_df.iloc[0]["threshold"])
    best_model = fitted[best_name]

    # Fit a lightweight calibration layer on validation data only. If the local
    # sklearn version rejects prefit syntax, keep the uncalibrated model and
    # record the reason.
    calibrated = None
    calibration_note = "not attempted"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            calibrated = CalibratedClassifierCV(best_model, cv="prefit", method="isotonic")
            calibrated.fit(X_valid, y_valid)
        calibration_note = "isotonic calibration fitted on validation split"
    except Exception as exc:
        calibrated = best_model
        calibration_note = f"using raw probabilities because calibration failed: {exc}"

    best_test_proba = calibrated.predict_proba(X_test)[:, 1]
    best_test_metrics = evaluate_predictions(y_test, best_test_proba, best_threshold)
    frac_pos, mean_pred = calibration_curve(y_test, best_test_proba, n_bins=10, strategy="quantile")
    calibration_df = pd.DataFrame({"mean_predicted": mean_pred, "fraction_positive": frac_pos})

    base_pr_auc = average_precision_score(y_test, best_test_proba)
    importance_df = permutation_importance_fast(calibrated, X_test, y_test, base_pr_auc)
    try:
        shap_df = shap_summary_for_tree(best_model, X_test)
        shap_note = "Tree SHAP computed on a representative test sample"
    except Exception as exc:
        shap_df = importance_df.rename(columns={"importance": "mean_abs_shap"})[["feature", "mean_abs_shap"]]
        shap_df = shap_df.rename(columns={"feature": "source_feature"})
        shap_note = f"SHAP fallback used permutation importance because SHAP failed: {exc}"

    # Representative local explanation compatible with the Streamlit page.
    sample = X_test.iloc[[0]].copy()
    baseline = float(y_train.mean())
    sample_proba = float(calibrated.predict_proba(sample)[:, 1][0])
    local_contrib = []
    for feature in importance_df.head(8)["feature"]:
        value = sample.iloc[0][feature]
        local_contrib.append(
            {
                "feature": feature,
                "value": str(value),
                "contribution": float(importance_df.loc[importance_df["feature"] == feature, "importance"].iloc[0]),
            }
        )

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(calibrated, MODELS_DIR / "delay_model.joblib")
    joblib.dump({"features": feature_cols, "threshold": best_threshold}, MODELS_DIR / "feature_spec.joblib")
    metrics_df.to_csv(TABLES_DIR / "model_metrics.csv", index=False, encoding="utf-8-sig")
    calibration_df.to_csv(TABLES_DIR / "calibration_curve.csv", index=False, encoding="utf-8-sig")
    importance_df.to_csv(TABLES_DIR / "feature_importance.csv", index=False, encoding="utf-8-sig")
    shap_df.to_csv(TABLES_DIR / "shap_summary.csv", index=False, encoding="utf-8-sig")

    scored = df[df["is_completed"] == 1].copy()
    scored["delay_risk"] = calibrated.predict_proba(scored[feature_cols])[:, 1]
    scored.to_parquet(PROCESSED_DIR / "flights_scored.parquet", index=False)

    model_summary = {
        "best_model": best_name,
        "threshold": best_threshold,
        "feature_columns": feature_cols,
        "forbidden_features_excluded": FORBIDDEN_FEATURES,
        "calibration_note": calibration_note,
        "shap_note": shap_note,
        "best_test_metrics": best_test_metrics,
        "sample_prediction": {
            "baseline_train_rate": baseline,
            "probability": sample_proba,
            "contributions": local_contrib,
        },
    }
    write_json(MODELS_DIR / "model_summary.json", model_summary)
    write_json(DEMO_DIR / "model_metrics.json", model_summary)
    return model_summary
