"""원본/정제 데이터 EDA, 기술통계, 상관분석, 그룹 비교.

Step 1(원본 데이터 EDA)을 우선 구현한다. Step 3~5(정제 데이터 EDA, 상관관계,
범주형 그룹 비교)는 정제 파이프라인(preprocessing.py) 확정 후 이어서 추가한다.
"""

from pathlib import Path

import pandas as pd

TARGET_COL = "ConvertedCompYearly"
NUMERIC_CANDIDATES = ["YearsCode", "YearsCodePro", "WorkExp", "JobSat"]
CATEGORICAL_CANDIDATES = [
    "Country",
    "EdLevel",
    "DevType",
    "RemoteWork",
    "OrgSize",
    "Employment",
    "Industry",
]
MULTISELECT_CANDIDATES = ["LanguageHaveWorkedWith", "DatabaseHaveWorkedWith", "PlatformHaveWorkedWith"]


class Tee:
    """print() 출력을 화면과 로그 파일에 동시에 기록하는 헬퍼."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.lines: list[str] = []

    def __call__(self, *args: object) -> None:
        text = " ".join(str(a) for a in args)
        print(text)
        self.lines.append(text)

    def flush(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


def run_raw_eda(df: pd.DataFrame, log_path: Path) -> None:
    """원본 데이터(정제 이전) 기준 EDA를 수행하고 결과를 출력·로그 저장한다.

    Args:
        df: Pandas로 로딩한 원본 DataFrame.
        log_path: 실행 결과를 기록할 로그 파일 경로.
    """
    out = Tee(log_path)
    out("=== Step 1: 원본 데이터 EDA ===")

    _summarize_shape_and_dtypes(df, out)
    _summarize_missing_rate(df, out)
    _summarize_target(df, out)
    _check_numeric_candidates(df, out)
    _check_categorical_candidates(df, out)
    _check_multiselect_candidates(df, out)

    out.flush()
    print(f"\n[eda] 원본 EDA 로그 저장: {log_path}")


def _summarize_shape_and_dtypes(df: pd.DataFrame, out: Tee) -> None:
    """행·열 수, dtype 분포, 전체 메모리 사용량을 요약한다."""
    memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
    out(f"\n[형태] shape={df.shape}, 메모리={memory_mb:.1f} MB")
    dtype_counts = df.dtypes.value_counts()
    out("[dtype 분포]")
    for dtype, count in dtype_counts.items():
        out(f"  {dtype}: {count}개 컬럼")


def _summarize_missing_rate(df: pd.DataFrame, out: Tee) -> None:
    """컬럼별 결측률을 계산해 결측이 가장 심한/적은 컬럼을 각각 상위 15개 출력한다."""
    missing_rate = (df.isnull().sum() / len(df) * 100).sort_values(ascending=False)
    out("\n[결측률 상위 15개 컬럼]")
    for col, rate in missing_rate.head(15).items():
        out(f"  {col}: {rate:.1f}%")
    out("\n[결측률 낮은(분석 활용 용이) 15개 컬럼]")
    for col, rate in missing_rate.tail(15).sort_values().items():
        out(f"  {col}: {rate:.1f}%")


def _summarize_target(df: pd.DataFrame, out: Tee) -> None:
    """급여 타깃 컬럼(ConvertedCompYearly)의 결측·기술통계·극단값을 요약한다."""
    out(f"\n[타깃: {TARGET_COL}]")
    if TARGET_COL not in df.columns:
        out(f"  경고: {TARGET_COL} 컬럼이 존재하지 않습니다.")
        return
    series = df[TARGET_COL]
    missing = series.isnull().sum()
    out(f"  결측 수: {missing} / {len(series)} ({missing / len(series) * 100:.1f}%)")
    desc = series.describe()
    out(f"  기술통계: {desc.to_dict()}")
    quantiles = series.quantile([0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
    out("  분위수:")
    for q, v in quantiles.items():
        out(f"    {q:.2f}: {v:,.0f}")


def _check_numeric_candidates(df: pd.DataFrame, out: Tee) -> None:
    """수치형 피처 후보의 실제 dtype과 샘플 값을 확인한다(문자열 혼입 여부 점검)."""
    out("\n[수치형 후보 컬럼 dtype/샘플]")
    for col in NUMERIC_CANDIDATES:
        if col not in df.columns:
            out(f"  {col}: 컬럼 없음")
            continue
        sample = df[col].dropna().unique()[:5]
        out(f"  {col}: dtype={df[col].dtype}, 샘플={list(sample)}")


def _check_categorical_candidates(df: pd.DataFrame, out: Tee) -> None:
    """범주형 피처 후보의 고유값 수와 상위 빈도를 확인한다."""
    out("\n[범주형 후보 컬럼 고유값/상위 빈도]")
    for col in CATEGORICAL_CANDIDATES:
        if col not in df.columns:
            out(f"  {col}: 컬럼 없음")
            continue
        nunique = df[col].nunique(dropna=True)
        top3 = df[col].value_counts().head(3).to_dict()
        out(f"  {col}: 고유값 {nunique}개, 상위3={top3}")


def _check_multiselect_candidates(df: pd.DataFrame, out: Tee) -> None:
    """멀티셀렉트(세미콜론 구분) 컬럼의 특성만 확인한다(파싱은 이후 단계로 보류)."""
    out("\n[멀티셀렉트 후보 컬럼 특성 (파싱은 보류)]")
    for col in MULTISELECT_CANDIDATES:
        if col not in df.columns:
            out(f"  {col}: 컬럼 없음")
            continue
        sample = df[col].dropna().iloc[0] if df[col].notna().any() else None
        out(f"  {col}: dtype={df[col].dtype}, 샘플='{sample}'")


def run_clean_eda(df: pd.DataFrame, log_path: Path) -> None:
    """정제된 데이터 기준 EDA(형태, 기술통계)를 수행하고 결과를 출력·로그 저장한다.

    Args:
        df: preprocessing.run_preprocessing()으로 정제된 DataFrame.
        log_path: 실행 결과를 기록할 로그 파일 경로.
    """
    out = Tee(log_path)
    out("=== Step 3: 정제 데이터 EDA 및 기술통계 ===")

    memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
    out(f"\n[형태] shape={df.shape}, 메모리={memory_mb:.1f} MB")

    numeric_cols = [TARGET_COL, *NUMERIC_CANDIDATES]
    out("\n[수치형 컬럼 기술통계]")
    out(df[numeric_cols].describe().to_string())

    out.flush()
    print(f"\n[eda] 정제 EDA 로그 저장: {log_path}")


def run_correlation_analysis(df: pd.DataFrame, log_path: Path) -> dict[str, float]:
    """급여 타깃과 수치형 변수 간 상관관계(Pearson)를 분석한다.

    Args:
        df: 정제된 DataFrame.
        log_path: 실행 결과를 기록할 로그 파일 경로.

    Returns:
        수치형 변수별 급여와의 상관계수(절댓값 내림차순)를 담은 딕셔너리.
    """
    out = Tee(log_path)
    out("=== Step 4: 급여와 수치형 변수의 상관관계 분석 ===")

    numeric_cols = [TARGET_COL, *NUMERIC_CANDIDATES]
    corr = df[numeric_cols].corr(method="pearson")
    out("\n[상관계수 행렬]")
    out(corr.to_string())

    target_corr = corr[TARGET_COL].drop(TARGET_COL).sort_values(key=lambda s: s.abs(), ascending=False)
    out(f"\n[{TARGET_COL}와의 상관계수 (절댓값 내림차순)]")
    for col, value in target_corr.items():
        out(f"  {col}: {value:.4f}")

    out.flush()
    print(f"\n[eda] 상관관계 분석 로그 저장: {log_path}")
    return target_corr.to_dict()


def run_categorical_group_comparison(df: pd.DataFrame, log_path: Path, min_group_size: int = 30) -> None:
    """범주형 변수별 급여 중앙값·분포를 비교한다(그룹 크기 min_group_size 미만은 제외).

    Args:
        df: 정제된 DataFrame.
        log_path: 실행 결과를 기록할 로그 파일 경로.
        min_group_size: 통계 노이즈를 줄이기 위한 최소 그룹 크기.
    """
    out = Tee(log_path)
    out("=== Step 5: 범주형 변수별 급여 중앙값·분포 비교 ===")

    for col in CATEGORICAL_CANDIDATES:
        if col not in df.columns:
            out(f"\n[{col}] 컬럼 없음")
            continue
        grouped = df.groupby(col)[TARGET_COL].agg(["count", "median", "mean", "std"])
        grouped = grouped[grouped["count"] >= min_group_size].sort_values("median", ascending=False)
        out(f"\n[{col}] 그룹 수={len(grouped)} (최소 표본 {min_group_size}건 기준, 급여 중앙값 내림차순 상위 10개)")
        out(grouped.head(10).to_string())

    out.flush()
    print(f"\n[eda] 범주형 그룹 비교 로그 저장: {log_path}")
