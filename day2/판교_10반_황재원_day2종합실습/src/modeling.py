"""ColumnTransformer + Pipeline 기반 회귀·분류 모델 학습·평가·저장.

Step 9(Pipeline 모델 학습·평가·저장)를 구현한다. 회귀는 급여(ConvertedCompYearly)
자체를 예측하고, 분류는 급여가 정제 데이터 중앙값을 넘는지(고액 여부)를 예측한다.
"""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.eda import Tee
from src.preprocessing import FEATURE_CATEGORICAL, FEATURE_NUMERIC, TARGET_COL

RANDOM_STATE = 42
TEST_SIZE = 0.2


def _build_preprocessor() -> ColumnTransformer:
    """수치형(결측 대체+스케일링)·범주형(결측 대체+원핫인코딩) 전처리기를 구성한다.

    Returns:
        ColumnTransformer 인스턴스.
    """
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, FEATURE_NUMERIC),
            ("categorical", categorical_pipeline, FEATURE_CATEGORICAL),
        ]
    )


def run_regression_pipeline(
    df: pd.DataFrame, model_path: Path, out: Tee
) -> dict[str, float]:
    """급여(ConvertedCompYearly)를 예측하는 회귀 Pipeline을 학습·평가·저장한다.

    Args:
        df: 모델용 피처가 선택된 DataFrame.
        model_path: 학습된 Pipeline을 저장할 .joblib 경로.
        out: 실행 로그를 기록할 Tee 인스턴스.

    Returns:
        R², MAE 및 저장 경로를 담은 딕셔너리.
    """
    features = df[[*FEATURE_NUMERIC, *FEATURE_CATEGORICAL]]
    target = df[TARGET_COL]
    x_train, x_test, y_train, y_test = train_test_split(
        features, target, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", _build_preprocessor()),
            ("model", RandomForestRegressor(n_estimators=100, max_depth=15, random_state=RANDOM_STATE)),
        ]
    )
    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)

    r2 = r2_score(y_test, predictions)
    mae = mean_absolute_error(y_test, predictions)
    out(f"\n[회귀] R²={r2:.4f}, MAE={mae:,.0f}")

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_path)
    out(f"[회귀] 모델 저장: {model_path}")

    return {"r2": r2, "mae": mae, "model_path": str(model_path)}


def run_classification_pipeline(
    df: pd.DataFrame, model_path: Path, out: Tee
) -> dict[str, float]:
    """급여가 중앙값을 넘는지(고액 여부)를 예측하는 분류 Pipeline을 학습·평가·저장한다.

    Args:
        df: 모델용 피처가 선택된 DataFrame.
        model_path: 학습된 Pipeline을 저장할 .joblib 경로.
        out: 실행 로그를 기록할 Tee 인스턴스.

    Returns:
        Accuracy, F1-score, 임계값(중앙값) 및 저장 경로를 담은 딕셔너리.
    """
    median_salary = df[TARGET_COL].median()
    target = (df[TARGET_COL] > median_salary).astype(int)
    features = df[[*FEATURE_NUMERIC, *FEATURE_CATEGORICAL]]

    x_train, x_test, y_train, y_test = train_test_split(
        features, target, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=target
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", _build_preprocessor()),
            ("model", RandomForestClassifier(n_estimators=100, max_depth=15, random_state=RANDOM_STATE)),
        ]
    )
    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)

    accuracy = accuracy_score(y_test, predictions)
    f1 = f1_score(y_test, predictions)
    out(f"\n[분류] 고액 급여 기준(중앙값)={median_salary:,.0f}")
    out(f"[분류] Accuracy={accuracy:.4f}, F1-score={f1:.4f}")

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_path)
    out(f"[분류] 모델 저장: {model_path}")

    return {
        "accuracy": accuracy,
        "f1": f1,
        "median_threshold": median_salary,
        "model_path": str(model_path),
    }


def run_model_pipelines(
    df: pd.DataFrame, models_dir: Path, log_path: Path
) -> dict[str, dict[str, float]]:
    """회귀·분류 Pipeline을 순서대로 학습·평가·저장한다.

    Args:
        df: 모델용 피처가 선택된 DataFrame.
        models_dir: .joblib 모델 파일을 저장할 디렉토리.
        log_path: 실행 결과를 기록할 로그 파일 경로.

    Returns:
        {"regression": {...}, "classification": {...}} 형태의 결과 딕셔너리.
    """
    out = Tee(log_path)
    out("=== Step 9: Pipeline 모델 학습·평가·저장 ===")

    regression_result = run_regression_pipeline(
        df, models_dir / "salary_regression_pipeline.joblib", out
    )
    classification_result = run_classification_pipeline(
        df, models_dir / "salary_classification_pipeline.joblib", out
    )

    out.flush()
    print(f"\n[modeling] Step 9 로그 저장: {log_path}")

    return {"regression": regression_result, "classification": classification_result}
