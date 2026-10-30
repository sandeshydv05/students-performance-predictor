"""Train, compare, and persist student examination mark prediction models."""

from pathlib import Path
import json

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.compose import ColumnTransformer
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "students.csv"
MODEL_PATH = ROOT / "student_model.pkl"
METRICS_PATH = ROOT / "model_metrics.json"

NUMERIC_FEATURES = [
    "study_hours",
    "attendance",
    "previous_marks",
    "assignment_marks",
    "sleep_hours",
]
CATEGORICAL_FEATURES = [
    "parental_education",
    "internet_access",
    "extracurricular",
]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET = "exam_marks"


def build_preprocessor():
    numeric = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric, NUMERIC_FEATURES),
            ("categorical", categorical, CATEGORICAL_FEATURES),
        ]
    )


def train_model():
    """Train candidate regressors, choose lowest-MAE model, and save artifacts."""
    data = pd.read_csv(DATA_PATH)
    required = FEATURES + [TARGET]
    missing_columns = sorted(set(required) - set(data.columns))
    if missing_columns:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing_columns)}")
    data = data[required].copy()
    data[TARGET] = pd.to_numeric(data[TARGET], errors="coerce")
    data = data.dropna(subset=[TARGET])
    if len(data) < 10:
        raise ValueError("At least 10 valid student rows are required to train the model.")

    x_train, x_test, y_train, y_test = train_test_split(
        data[FEATURES], data[TARGET], test_size=0.2, random_state=42
    )
    feature_count = build_preprocessor().fit_transform(x_train).shape[1]
    selected_feature_count = min(10, feature_count)
    candidates = {
        "Linear Regression": LinearRegression(),
        "Decision Tree": DecisionTreeRegressor(max_depth=5, random_state=42),
        "Random Forest": RandomForestRegressor(
            n_estimators=250, max_depth=8, min_samples_leaf=2, random_state=42
        ),
    }

    metrics = {}
    trained = {}
    for name, estimator in candidates.items():
        pipeline = Pipeline(
            steps=[
                ("preprocessor", build_preprocessor()),
                ("feature_selection", SelectKBest(score_func=f_regression, k=selected_feature_count)),
                ("regressor", estimator),
            ]
        )
        pipeline.fit(x_train, y_train)
        predictions = pipeline.predict(x_test)
        mse = mean_squared_error(y_test, predictions)
        metrics[name] = {
            "mae": round(float(mean_absolute_error(y_test, predictions)), 3),
            "mse": round(float(mse), 3),
            "rmse": round(float(np.sqrt(mse)), 3),
            "r2": round(float(r2_score(y_test, predictions)), 3),
        }
        trained[name] = pipeline

    best_name = min(metrics, key=lambda model_name: metrics[model_name]["mae"])
    bundle = {
        "model": trained[best_name],
        "model_name": best_name,
        "features": FEATURES,
        "metrics": metrics,
    }
    joblib.dump(bundle, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    image_dir = ROOT / "static" / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    comparison = pd.DataFrame(
        [
            {"Model": name, "Metric": metric.upper(), "Error (marks)": score[metric]}
            for name, score in metrics.items()
            for metric in ("mae", "rmse")
        ]
    )
    figure, axis = plt.subplots(figsize=(8, 4.2))
    sns.barplot(
        data=comparison,
        x="Model",
        y="Error (marks)",
        hue="Metric",
        palette=["#6573e8", "#49c9a5"],
        ax=axis,
    )
    axis.set_title("Held-out prediction error by model", loc="left", fontsize=12, pad=14)
    axis.set_xlabel("")
    axis.set_ylabel("Error (marks)")
    axis.spines[["top", "right"]].set_visible(False)
    figure.tight_layout()
    figure.savefig(image_dir / "model_comparison.png", dpi=150, bbox_inches="tight")
    plt.close(figure)
    print(f"Best model: {best_name}")
    print(json.dumps(metrics, indent=2))
    return bundle


if __name__ == "__main__":
    train_model()
