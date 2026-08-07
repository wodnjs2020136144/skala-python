"""ColumnTransformer + Pipeline 기반 회귀·분류 모델 학습·평가·저장.

Step 9(Pipeline 모델 학습·평가·저장)를 구현한다. 회귀는 급여(ConvertedCompYearly)
자체를 예측하고, 분류는 급여가 정제 데이터 중앙값을 넘는지(고액 여부)를 예측한다.

모델은 RandomForest를 사용한다. 피처가 수치형 2개(WorkExp, JobSat) + 범주형 5개
(Country 등)로 구성돼 있어 원핫인코딩 시 열 수가 꽤 늘어나는데, RandomForest는
피처 스케일에 둔감하고 비선형 상호작용(예: 국가별 원격근무 형태에 따른 급여 차이)도
별도 피처 엔지니어링 없이 잡아낼 수 있어 선형모델보다 적합하다고 판단했다.
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

# 재현성을 위해 고정하는 난수 시드. 사이킷런 예제/튜토리얼에서 관용적으로 쓰는 값이라
# 별다른 의미는 없지만, train_test_split·RandomForest 양쪽에 동일하게 적용해 실행할
# 때마다 같은 분할·같은 트리 구조가 나오도록 한다.
RANDOM_STATE = 42
# 학습:평가 = 8:2. 정제 후 표본이 22,457행으로 충분히 커서 20%(약 4,500행)만 떼어내도
# 평가 지표(R², Accuracy 등)가 안정적으로 나온다.
TEST_SIZE = 0.2


def _build_preprocessor() -> ColumnTransformer:
    """수치형(결측 대체+스케일링)·범주형(결측 대체+원핫인코딩) 전처리기를 구성한다.

    Returns:
        ColumnTransformer 인스턴스.
    """
    numeric_pipeline = Pipeline(
        steps=[
            # WorkExp/JobSat 모두 결측이 있고(Step3 기술통계 참고) 급여처럼 오른쪽 꼬리가
            # 긴 분포는 아니지만, 평균보다 이상치에 덜 흔들리는 중앙값 대체를 기본으로 택했다.
            ("imputer", SimpleImputer(strategy="median")),
            # RandomForest 자체는 트리 기반이라 피처 스케일에 영향받지 않지만, 회귀·분류
            # Pipeline을 동일한 전처리기로 통일해두면 이후 다른 모델(예: 선형/거리 기반)로
            # 교체하더라도 전처리 코드를 그대로 재사용할 수 있어 표준화를 넣었다.
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            # 범주형은 중앙값 개념이 없으므로 최빈값(mode)으로 결측을 대체한다.
            ("imputer", SimpleImputer(strategy="most_frequent")),
            # handle_unknown="ignore": train에 없던 범주(예: Country 소수 국가)가 test에서
            # 나와도 에러 없이 전부 0벡터로 인코딩되게 해 학습/평가 분할마다 실패하지 않도록 한다.
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
            # n_estimators=100, max_depth=15는 처음엔 200/무제한으로 학습시켰다가
            # joblib 모델 파일이 회귀 313MB까지 커지는 문제가 있어 조정한 값이다
            # (Country 원핫인코딩으로 열이 많아진 상태에서 트리 깊이 제한이 없으면
            # 개별 트리가 지나치게 깊어짐). 조정 후 R²는 0.5938→0.5879로 소폭만
            # 낮아지고 파일은 29MB로 줄었다 — 자세한 비교 수치는 TROUBLESHOOTING.md
            # "Step 9 — ML Pipeline 모델 파일 용량 과다" 참고.
            ("model", RandomForestRegressor(n_estimators=100, max_depth=15, random_state=RANDOM_STATE)),
        ]
    )
    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)

    # R²(설명력)와 MAE(달러 단위 오차 크기)를 함께 본다. R²만으로는 "실제 급여와 몇
    # 달러나 차이 나는지" 감이 안 오고, MAE만으로는 모델이 얼마나 잘 설명하는지
    # (베이스라인 대비 개선 정도) 알 수 없어 두 지표를 상호 보완적으로 사용했다.
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
    # 중앙값을 기준으로 "고액 급여 여부" 이진 타깃을 만든다. 상위 25%처럼 더 극단적인
    # 기준도 검토했지만, 중앙값 분할은 두 클래스 비율이 거의 50:50이 되어 정확도 지표를
    # 그대로 해석하기 쉽고(클래스 불균형 보정이 따로 필요 없음) 해석도 직관적이다.
    median_salary = df[TARGET_COL].median()
    target = (df[TARGET_COL] > median_salary).astype(int)
    features = df[[*FEATURE_NUMERIC, *FEATURE_CATEGORICAL]]

    # stratify=target: 급여 중앙값 기준 클래스 비율이 train/test에 동일하게 유지되도록
    # 층화 분할한다. 안 하면 분할 운에 따라 한쪽에 고액/저액 비율이 쏠려 평가 지표가
    # 흔들릴 수 있다.
    x_train, x_test, y_train, y_test = train_test_split(
        features, target, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=target
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", _build_preprocessor()),
            # 회귀와 동일한 근거로 n_estimators=100, max_depth=15를 사용한다(모델 파일
            # 용량·학습 시간 절충, TROUBLESHOOTING.md "Step 9" 참고).
            ("model", RandomForestClassifier(n_estimators=100, max_depth=15, random_state=RANDOM_STATE)),
        ]
    )
    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)

    # 클래스 비율이 중앙값 분할로 거의 50:50이라 Accuracy가 왜곡되지 않지만, F1-score도
    # 함께 봐서 정밀도·재현율이 한쪽으로 치우치지 않았는지 교차 확인한다.
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
