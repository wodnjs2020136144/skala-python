"""결측·중복·급여 이상치 처리 및 모델용 피처 선택.

Step 2(결측치·중복·급여 이상치 처리)와 Step 6(모델용 컬럼 선택)을 구현한다.
"""

from pathlib import Path

import pandas as pd

from src.eda import TARGET_COL, Tee

YEARS_COLUMNS = ["YearsCode", "YearsCodePro"]
LESS_THAN_ONE_YEAR = 0.0
MORE_THAN_FIFTY_YEARS = 51.0
IQR_MULTIPLIER = 1.5

# Step 4 상관분석에서 급여와 유의미한 상관을 보인 수치형 컬럼 중 다중공선성을 제거한 결과.
# YearsCode·YearsCodePro·WorkExp는 서로 상관계수 0.87~0.92, VIF 6.2~10.6으로 다중공선성이
# 심각해 셋 다 남기면 피처 중요도가 인위적으로 분산된다. 셋 중 급여와의 상관이 가장 높고
# (r=0.408) VIF가 가장 낮은(6.97) WorkExp만 남기고 YearsCode/YearsCodePro는 제외했다.
FEATURE_NUMERIC = ["WorkExp", "JobSat"]
# Step 5 그룹 비교에서 급여 중앙값 차이를 크게 만든 범주형 컬럼.
# DevType(34개)/Employment(110개)는 고유값이 지나치게 많고 상위 카테고리 집중도가
# 낮아 제외했다. CompTotal/Currency는 급여에서 직접 파생되는 값이라 타깃 누수를
# 피하기 위해 애초에 후보에서 제외한다 (practice4 트러블슈팅 참고).
FEATURE_CATEGORICAL = ["Country", "RemoteWork", "EdLevel", "OrgSize", "Industry"]


def _years_text_to_numeric(value: object) -> float:
    """YearsCode/YearsCodePro의 텍스트 응답을 숫자로 변환한다.

    "Less than 1 year"는 0, "More than 50 years"는 51로 매핑하고, 그 외에는
    정수 문자열을 float로 변환한다. 변환할 수 없는 값은 NaN으로 처리한다.

    Args:
        value: 원본 셀 값(문자열 또는 결측).

    Returns:
        변환된 숫자 값. 변환 불가 시 NaN.
    """
    if pd.isna(value):
        return float("nan")
    if value == "Less than 1 year":
        return LESS_THAN_ONE_YEAR
    if value == "More than 50 years":
        return MORE_THAN_FIFTY_YEARS
    try:
        return float(value)
    except ValueError:
        return float("nan")


def convert_years_columns(df: pd.DataFrame, columns: list[str] = YEARS_COLUMNS) -> pd.DataFrame:
    """YearsCode/YearsCodePro 컬럼을 텍스트에서 숫자(float)로 변환한다.

    Args:
        df: 변환 대상 DataFrame.
        columns: 변환할 컬럼 목록.

    Returns:
        해당 컬럼이 숫자형으로 변환된 새 DataFrame.
    """
    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[col] = df[col].map(_years_text_to_numeric)
    return df


def remove_salary_outliers_iqr(
    df: pd.DataFrame, target_col: str = TARGET_COL
) -> tuple[pd.DataFrame, dict[str, float]]:
    """IQR 규칙으로 급여 이상치를 제거한다.

    하한 = Q1 - 1.5*IQR, 상한 = Q3 + 1.5*IQR 범위를 벗어나는 행을 제거한다.

    Args:
        df: 이상치 제거 대상 DataFrame.
        target_col: 급여 컬럼명.

    Returns:
        (이상치가 제거된 DataFrame, 통계 정보 딕셔너리) 튜플.
    """
    q1, q3 = df[target_col].quantile([0.25, 0.75])
    iqr = q3 - q1
    lower = q1 - IQR_MULTIPLIER * iqr
    upper = q3 + IQR_MULTIPLIER * iqr

    mask = df[target_col].between(lower, upper)
    stats = {
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "lower_bound": lower,
        "upper_bound": upper,
        "n_before": len(df),
        "n_removed": int((~mask).sum()),
    }
    return df[mask].copy(), stats


def run_preprocessing(df: pd.DataFrame, log_path: Path) -> tuple[pd.DataFrame, dict[str, float]]:
    """결측(급여)·중복·급여 이상치 처리를 순서대로 수행한다.

    처리 순서: ① 급여 결측 행 제거 → ② 완전 중복 행 제거 →
    ③ YearsCode/YearsCodePro 텍스트→숫자 변환 → ④ 급여 IQR 이상치 제거.

    Args:
        df: 원본 Pandas DataFrame.
        log_path: 실행 결과를 기록할 로그 파일 경로.

    Returns:
        (정제가 끝난 DataFrame, 단계별 행 수·이상치 경계를 담은 통계 딕셔너리) 튜플.
    """
    out = Tee(log_path)
    out("=== Step 2: 결측치·중복·급여 이상치 처리 ===")
    n_start = len(df)
    out(f"\n[시작] {n_start}행")

    df = df.dropna(subset=[TARGET_COL]).copy()
    n_after_dropna = len(df)
    out(f"[1] 급여({TARGET_COL}) 결측 행 제거 → {n_after_dropna}행 (제거 {n_start - n_after_dropna}행)")

    df = df.drop_duplicates()
    n_after_dedup = len(df)
    out(f"[2] 완전 중복 행 제거 → {n_after_dedup}행 (제거 {n_after_dropna - n_after_dedup}행)")

    df = convert_years_columns(df)
    n_years_missing = {col: int(df[col].isna().sum()) for col in YEARS_COLUMNS if col in df.columns}
    out(f"[3] YearsCode/YearsCodePro 텍스트→숫자 변환 완료 (변환 후 결측: {n_years_missing})")

    df, outlier_stats = remove_salary_outliers_iqr(df)
    out(
        f"[4] 급여 IQR 이상치 제거 → {len(df)}행 (제거 {outlier_stats['n_removed']}행, "
        f"경계=[{outlier_stats['lower_bound']:,.0f}, {outlier_stats['upper_bound']:,.0f}])"
    )

    out(f"\n[완료] 최종 {len(df)}행 (원본 대비 {len(df) / n_start * 100:.1f}%)")
    out.flush()
    print(f"\n[preprocessing] Step 2 로그 저장: {log_path}")

    stats = {
        "n_start": n_start,
        "n_after_dropna_target": n_after_dropna,
        "n_after_dedup": n_after_dedup,
        "n_final": len(df),
        **outlier_stats,
    }
    return df, stats


def select_model_columns(df: pd.DataFrame, log_path: Path) -> pd.DataFrame:
    """Step 4/5 EDA 근거로 확정한 피처 컬럼과 타깃만 남긴다.

    Args:
        df: 정제된 DataFrame.
        log_path: 실행 결과를 기록할 로그 파일 경로.

    Returns:
        FEATURE_NUMERIC + FEATURE_CATEGORICAL + TARGET_COL만 남은 DataFrame.
    """
    out = Tee(log_path)
    out("=== Step 6: 모델용 컬럼 선택 ===")
    out(f"\n[수치형 피처] {FEATURE_NUMERIC} (Step4 상관계수 기준 채택)")
    out(f"[범주형 피처] {FEATURE_CATEGORICAL} (Step5 급여 중앙값 격차 기준 채택)")
    out("[제외] DevType/Employment: 고유값 과다·상위 카테고리 집중도 낮음")
    out("[제외] CompTotal/Currency: 급여에서 직접 파생되는 값 → 타깃 누수 방지")
    out(
        "[제외] YearsCode/YearsCodePro: WorkExp와 상관계수 0.87~0.92, VIF 6.2~10.6으로 "
        "다중공선성 심각 → 급여 상관·VIF가 가장 우수한 WorkExp만 유지"
    )

    columns = [*FEATURE_NUMERIC, *FEATURE_CATEGORICAL, TARGET_COL]
    model_df = df[columns].copy()
    out(f"\n[결과] shape={model_df.shape}")

    out.flush()
    print(f"\n[preprocessing] Step 6 로그 저장: {log_path}")
    return model_df
