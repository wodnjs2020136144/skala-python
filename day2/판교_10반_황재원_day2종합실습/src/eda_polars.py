"""Polars Lazy API로 EDA 구간(Step 1, Step 5)을 이중 수행하고 Pandas 결과와 교차검증한다.

Step 0에서 실제로 로딩한 Polars DataFrame을 재사용해 결측률 집계(Step 1 대응)와
급여 이상치 제거 후 범주형 그룹 비교(Step 5 대응)를 Polars로도 수행한다. 시각화·통계
검정·모델링은 pandas 객체를 요구하므로 여전히 src/eda.py, src/preprocessing.py 등의
Pandas 구현을 사용하며, 이 모듈은 EDA 결과가 두 엔진에서 일치하는지 검증하는 용도다.
"""

import time
from pathlib import Path

import polars as pl

from src.eda import CATEGORICAL_CANDIDATES, TARGET_COL, Tee

MISSING_RATE_TOP_N = 15
MIN_GROUP_SIZE = 30


def run_raw_missing_rate_polars(pl_df: pl.DataFrame, log_path: Path) -> dict[str, float]:
    """Polars Lazy API로 원본 데이터의 컬럼별 결측률을 계산한다(Step 1 대응).

    Args:
        pl_df: Step 0에서 로딩한 원본 Polars DataFrame.
        log_path: 실행 결과를 기록할 로그 파일 경로.

    Returns:
        컬럼명을 키로, 결측률(%)을 값으로 하는 딕셔너리(결측률 내림차순).
    """
    out = Tee(log_path)
    out("=== Step 1 (Polars): 원본 데이터 결측률 집계 ===")

    start = time.perf_counter()
    null_counts = pl_df.lazy().select(pl.all().null_count()).collect()
    elapsed = time.perf_counter() - start

    n_rows = pl_df.height
    missing_rate = {col: null_counts[col][0] / n_rows * 100 for col in null_counts.columns}
    missing_rate = dict(sorted(missing_rate.items(), key=lambda item: item[1], reverse=True))

    out(f"\n[소요 시간] {elapsed:.3f}초 (Lazy API, {len(missing_rate)}개 컬럼)")
    out(f"\n[결측률 상위 {MISSING_RATE_TOP_N}개 컬럼]")
    for col, rate in list(missing_rate.items())[:MISSING_RATE_TOP_N]:
        out(f"  {col}: {rate:.1f}%")

    out.flush()
    print(f"\n[eda_polars] Step 1 (Polars) 로그 저장: {log_path}")
    return missing_rate


def run_salary_group_comparison_polars(
    pl_df: pl.DataFrame,
    lower_bound: float,
    upper_bound: float,
    pandas_remote_work_medians: dict[str, float],
    pandas_n_final: int,
    log_path: Path,
) -> dict[str, object]:
    """Polars Lazy API로 급여 정제·범주형 그룹 비교를 수행하고 Pandas 결과와 대조한다(Step 5 대응).

    Pandas 파이프라인(src/preprocessing.py의 run_preprocessing)과 동일한 정제 조건
    (급여 결측 제거 → 완전 중복 제거 → IQR 경계 필터)을 Polars Lazy 체인으로 재현한다.

    Args:
        pl_df: Step 0에서 로딩한 원본 Polars DataFrame.
        lower_bound: Pandas Step 2에서 계산된 IQR 하한.
        upper_bound: Pandas Step 2에서 계산된 IQR 상한.
        pandas_remote_work_medians: Pandas로 계산한 RemoteWork 그룹별 급여 중앙값.
        pandas_n_final: Pandas 정제 파이프라인의 최종 행 수.
        log_path: 실행 결과를 기록할 로그 파일 경로.

    Returns:
        Polars 정제 행 수, 그룹별 중앙값, 교차검증 결과를 담은 딕셔너리.
    """
    out = Tee(log_path)
    out("=== Step 5 (Polars): 급여 정제 및 범주형 그룹 비교 ===")

    start = time.perf_counter()
    # Polars는 CSV 스키마 추론 시 ConvertedCompYearly를 문자열로 읽는 경우가 있어
    # 비교 연산 전에 명시적으로 숫자형으로 캐스팅한다(파싱 불가 값은 null로 처리).
    cleaned = (
        pl_df.lazy()
        .with_columns(pl.col(TARGET_COL).cast(pl.Float64, strict=False))
        .filter(pl.col(TARGET_COL).is_not_null())
        .unique()
        .filter(pl.col(TARGET_COL).is_between(lower_bound, upper_bound))
    )
    cleaned_df = cleaned.collect()
    elapsed = time.perf_counter() - start
    n_final = cleaned_df.height
    out(f"\n[소요 시간] {elapsed:.3f}초, 정제 후 {n_final}행")

    group_medians: dict[str, dict[str, float]] = {}
    for col in CATEGORICAL_CANDIDATES:
        groups = (
            cleaned.group_by(col)
            .agg(
                [
                    pl.len().alias("count"),
                    pl.col(TARGET_COL).median().alias("median"),
                ]
            )
            .filter(pl.col("count") >= MIN_GROUP_SIZE)
            .sort("median", descending=True)
            .collect()
        )
        group_medians[col] = dict(zip(groups[col], groups["median"], strict=True))
        out(f"\n[{col}] 그룹 수={len(groups)} (최소 표본 {MIN_GROUP_SIZE}건, 급여 중앙값 내림차순 상위 5개)")
        for row in groups.head(5).iter_rows(named=True):
            out(f"  {row[col]}: count={row['count']}, median={row['median']:,.0f}")

    # Pandas 파이프라인 결과와 교차검증: 행 수, RemoteWork 그룹 중앙값 비교.
    out("\n[교차검증] Pandas 결과와 대조")
    rows_match = n_final == pandas_n_final
    out(f"  정제 후 행 수: Polars={n_final}, Pandas={pandas_n_final} → {'일치' if rows_match else '불일치'}")

    polars_remote_medians = group_medians.get("RemoteWork", {})
    medians_match = True
    for group, pandas_median in pandas_remote_work_medians.items():
        polars_median = polars_remote_medians.get(group)
        matched = polars_median is not None and abs(polars_median - pandas_median) < 1.0
        medians_match = medians_match and matched
        out(
            f"  RemoteWork='{group}' 중앙값: Polars={polars_median}, Pandas={pandas_median:,.0f} "
            f"→ {'일치' if matched else '불일치'}"
        )

    out.flush()
    print(f"\n[eda_polars] Step 5 (Polars) 로그 저장: {log_path}")

    return {
        "n_final": n_final,
        "elapsed_sec": elapsed,
        "group_medians": group_medians,
        "rows_match": rows_match,
        "medians_match": medians_match,
    }
