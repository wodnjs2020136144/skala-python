"""sales_100k.csv 원본으로 고액 주문 여부를 예측하는 sklearn Pipeline을 구축한다.

수치형(quantity/unit_price/customer_age) 스케일링 + 범주형(region/category/
payment_method) 원핫인코딩을 ColumnTransformer로 묶고, RandomForestClassifier와
함께 단일 Pipeline으로 구성해 학습·평가한 뒤 joblib으로 저장한다.

타깃(high_value_order)은 amount 평균 초과 여부로 정의하되, 타깃을 만든 컬럼인
amount 자체는 피처에서 제외해 "타깃과 동일한 정보가 피처에 그대로 들어가는"
데이터 누수를 피한다.
"""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from _common import CSV_PATH, ensure_csv_exists, ensure_output_dir

NUMERIC_FEATURES = ["quantity", "unit_price", "customer_age"]
CATEGORICAL_FEATURES = ["region", "category", "payment_method"]
REQUIRED_COLS = ["region", "category", "amount"]


def load_and_prepare_data(csv_path: Path, verbose: bool = False) -> tuple[pd.DataFrame, pd.Series, dict]:
    """원본 CSV에서 결측 필수 컬럼 행만 제거하고 피처/타깃을 분리한다.

    IQR 이상치는 제거하지 않는다("Pipeline의 학습 데이터 원본"은 sales_100k.csv
    원본을 그대로 사용한다는 실습 요구사항에 따름). amount 평균을 기준으로
    고액 주문 여부(high_value_order)를 타깃으로 만들고, amount 자체는
    데이터 누수를 피하기 위해 피처에서 제외한다.

    Args:
        csv_path: 원본 CSV 파일 경로.
        verbose: True면 결측 제거 통계와 타깃 분포를 출력한다.

    Returns:
        (피처 DataFrame, 타깃 Series, 통계 딕셔너리) 튜플.

    Raises:
        FileNotFoundError: csv_path에 파일이 없을 경우.
        ValueError: CSV 내용이 비어 있거나 파싱할 수 없는 형식일 경우.
    """
    ensure_csv_exists(csv_path)
    try:
        df = pd.read_csv(csv_path)
    except (pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        raise ValueError(f"CSV 파일을 읽을 수 없습니다: {csv_path}") from e

    before = len(df)
    df = df.dropna(subset=REQUIRED_COLS)
    after = len(df)

    threshold = df["amount"].mean()
    y = (df["amount"] > threshold).astype(int).rename("high_value_order")
    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]

    stats = {
        "before": before, "after": after, "dropped": before - after,
        "threshold": threshold, "positive_ratio": y.mean(),
    }
    if verbose:
        print(f"[결측 제거] {before}행 -> {after}행 (제거 {stats['dropped']}행)")
        print(f"[타깃 정의] amount > {threshold:.1f} (평균) -> high_value_order")
        print(f"[타깃 분포] 양성(1) 비율={stats['positive_ratio']:.3f}")
    return X, y, stats


def build_pipeline() -> Pipeline:
    """수치 스케일링 + 범주 원핫인코딩 전처리와 분류 모델을 하나의 Pipeline으로 구성한다.

    max_depth/min_samples_leaf를 제한하지 않으면 약 78만 건 학습 데이터에서
    트리가 과도하게 깊어져 저장 파일이 수백 MB로 커진다(실측 약 500MB, 정확도
    개선은 거의 없음). 트리 깊이를 제한해 모델 크기를 실용적인 수준으로 낮췄다.

    Returns:
        preprocessor와 classifier 두 단계로 이뤄진 학습 전 Pipeline 객체.
    """
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )
    return Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", RandomForestClassifier(
            n_estimators=100, max_depth=15, min_samples_leaf=50,
            random_state=42, n_jobs=-1,
        )),
    ])


def train_and_evaluate(X: pd.DataFrame, y: pd.Series, verbose: bool = False) -> tuple[Pipeline, dict]:
    """train/test로 분할해 Pipeline을 학습시키고 테스트 세트로 평가한다.

    Args:
        X: 피처 DataFrame.
        y: 타깃 Series.
        verbose: True면 정확도와 분류 리포트를 출력한다.

    Returns:
        학습이 끝난 Pipeline과 (accuracy, classification_report 문자열) 통계 딕셔너리.
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    accuracy = pipeline.score(X_test, y_test)
    y_pred = pipeline.predict(X_test)
    report = classification_report(y_test, y_pred)

    stats = {"accuracy": accuracy, "report": report, "n_train": len(X_train), "n_test": len(X_test)}
    if verbose:
        print(f"\n[학습/평가] train={stats['n_train']}건, test={stats['n_test']}건")
        print(f"[정확도] {accuracy:.4f}")
        print("[분류 리포트]")
        print(report)
    return pipeline, stats


def save_model(pipeline: Pipeline, output_path: Path) -> Path:
    """학습된 Pipeline을 joblib 파일로 저장한다.

    Args:
        pipeline: 저장할 학습된 Pipeline.
        output_path: 저장할 .joblib 파일 경로.

    Returns:
        저장된 파일 경로.

    Raises:
        OSError: 저장 디렉토리에 쓰기 권한이 없는 등 파일 저장에 실패할 경우.
    """
    try:
        joblib.dump(pipeline, output_path)
    except OSError as e:
        raise OSError(f"모델 파일을 저장할 수 없습니다: {output_path}") from e
    return output_path


def main() -> None:
    """데이터 준비 -> Pipeline 학습/평가 -> joblib 저장을 순서대로 수행한다."""
    X, y, prep_stats = load_and_prepare_data(CSV_PATH, verbose=True)
    pipeline, eval_stats = train_and_evaluate(X, y, verbose=True)

    output_dir = ensure_output_dir()
    model_path = output_dir / "sales_pipeline_model.joblib"
    saved_path = save_model(pipeline, model_path)
    print(f"\n[저장 완료] {saved_path}")


if __name__ == "__main__":
    main()
