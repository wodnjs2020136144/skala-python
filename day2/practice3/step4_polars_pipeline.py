"""Polars Lazy API 기반 매출 데이터 전처리 및 집계 파이프라인.

scan_csv -> filter(결측 제거) -> filter(IQR 이상치 제거) -> group_by -> agg
-> sort -> collect() 체인으로 step3_pandas_pipeline.py와 동일한 집계 3종을 구현한다.
"""

from pathlib import Path

import polars as pl

from _common import ensure_csv_exists

CSV_PATH = Path(__file__).resolve().parents[2] / "sales_100k.csv"
REQUIRED_COLS = ["region", "category", "amount"]


def scan_clean(csv_path: Path, verbose: bool = False) -> tuple[pl.LazyFrame, dict]:
    """CSV를 Lazy로 스캔하고 region/category/amount 결측 행을 filter로 제외한다.

    scan_csv는 즉시 데이터를 읽지 않으므로, 결측 건수 집계와 필터링 모두
    collect() 호출 시점에 실제로 실행된다.

    Args:
        csv_path: 스캔할 CSV 파일 경로.
        verbose: True면 결측 제거 전후 행 수와 컬럼별 결측 건수를 출력한다.

    Returns:
        결측 행이 제외된 LazyFrame과 (전/후 행 수, 컬럼별 결측 건수) 통계 딕셔너리.

    Raises:
        FileNotFoundError: csv_path에 파일이 없을 경우.
        ValueError: CSV 내용을 스캔/파싱할 수 없을 경우.
    """
    ensure_csv_exists(csv_path)
    lf = pl.scan_csv(csv_path)

    try:
        before = lf.select(pl.len()).collect().item()
    except pl.exceptions.ComputeError as e:
        raise ValueError(f"CSV 파일을 읽을 수 없습니다: {csv_path}") from e
    missing_counts = (
        lf.select([pl.col(c).is_null().sum().alias(c) for c in REQUIRED_COLS])
        .collect()
        .row(0, named=True)
    )

    clean_lf = lf.filter(
        pl.col("region").is_not_null()
        & pl.col("category").is_not_null()
        & pl.col("amount").is_not_null()
    )
    after = clean_lf.select(pl.len()).collect().item()

    stats = {"before": before, "after": after, "dropped": before - after,
              "missing_by_col": missing_counts}
    if verbose:
        print(f"[결측 제거] {before}행 -> {after}행 (제거 {stats['dropped']}행)")
        for col, cnt in missing_counts.items():
            print(f"  - {col}: {cnt}건 결측")
    return clean_lf, stats


def filter_outliers_iqr(lf: pl.LazyFrame, verbose: bool = False) -> tuple[pl.LazyFrame, dict]:
    """amount 컬럼 기준 IQR 범위를 벗어나는 이상치 행을 filter로 제외한다.

    Q1/Q3는 interpolation="linear"로 계산해 pandas의 quantile() 기본 동작과
    수치가 일치하도록 맞춘다.

    Args:
        lf: 이상치를 제거할 LazyFrame.
        verbose: True면 IQR 범위와 제거 전후 행 수를 출력한다.

    Returns:
        이상치가 제외된 LazyFrame과 (Q1, Q3, IQR, 허용범위, 제거 건수) 통계 딕셔너리.
    """
    before = lf.select(pl.len()).collect().item()

    quantiles = lf.select(
        pl.col("amount").quantile(0.25, interpolation="linear").alias("q1"),
        pl.col("amount").quantile(0.75, interpolation="linear").alias("q3"),
    ).collect()
    q1 = quantiles["q1"].item()
    q3 = quantiles["q3"].item()
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    filtered_lf = lf.filter((pl.col("amount") >= lower) & (pl.col("amount") <= upper))
    after = filtered_lf.select(pl.len()).collect().item()

    stats = {"before": before, "after": after, "removed": before - after,
              "q1": q1, "q3": q3, "iqr": iqr, "lower": lower, "upper": upper}
    if verbose:
        print(f"[IQR 이상치 제거] Q1={q1:.1f}, Q3={q3:.1f}, IQR={iqr:.1f}, "
              f"허용범위=[{lower:.1f}, {upper:.1f}]")
        print(f"  {before}행 -> {after}행 (제거 {stats['removed']}행)")
    return filtered_lf, stats


def _named_aggregation(lf: pl.LazyFrame, group_cols: list[str]) -> pl.DataFrame:
    """group_cols 기준으로 total_amount/avg_amount/item_count를 집계하는 공통 로직.

    region x category, payment_method 확장 집계, 월별 추이 집계가 group_cols만
    다르고 나머지 집계식은 동일하므로 이 헬퍼로 중복을 제거한다.
    group_by -> agg -> sort -> collect() 체인으로 Lazy 쿼리를 실행 계획째
    최적화한 뒤 마지막에 한 번에 실행한다.

    Args:
        lf: 집계 대상 LazyFrame.
        group_cols: group_by 기준 컬럼 목록.

    Returns:
        total_amount(합계), avg_amount(평균), item_count(건수)를 담은
        DataFrame. total_amount 내림차순으로 정렬된다.
    """
    return (
        lf.group_by(group_cols)
        .agg(
            pl.col("amount").sum().alias("total_amount"),
            pl.col("amount").mean().alias("avg_amount"),
            pl.col("amount").count().alias("item_count"),
        )
        .sort("total_amount", descending=True)
        .collect()
    )


def agg_region_category(lf: pl.LazyFrame) -> pl.DataFrame:
    """region x category 기준으로 매출을 집계한다.

    Args:
        lf: 집계 대상 LazyFrame.

    Returns:
        _named_aggregation() 결과. total_amount 내림차순으로 정렬된다.
    """
    return _named_aggregation(lf, ["region", "category"])


def agg_payment_method(lf: pl.LazyFrame) -> pl.DataFrame:
    """region x category x payment_method 기준으로 매출을 집계한다.

    Args:
        lf: 집계 대상 LazyFrame.

    Returns:
        _named_aggregation() 결과. total_amount 내림차순으로 정렬된다.
    """
    return _named_aggregation(lf, ["region", "category", "payment_method"])


def agg_monthly_trend(lf: pl.LazyFrame) -> pl.DataFrame:
    """order_date에서 연-월을 추출해 월별 매출 추이를 집계한다.

    Args:
        lf: 집계 대상 LazyFrame. order_date 컬럼은 'YYYY-MM-DD' 형식 문자열이어야 한다.

    Returns:
        order_month(연-월) 기준 _named_aggregation() 결과를 order_month
        오름차순으로 다시 정렬한 DataFrame.
    """
    monthly_lf = lf.with_columns(pl.col("order_date").str.slice(0, 7).alias("order_month"))
    return _named_aggregation(monthly_lf, ["order_month"]).sort("order_month")


def run_pipeline(csv_path: Path, verbose: bool = False) -> dict:
    """결측 제거 -> IQR 이상치 제거 -> 집계 3종으로 이어지는 Lazy 파이프라인을 실행한다.

    Args:
        csv_path: 처리할 CSV 파일 경로.
        verbose: True면 각 처리 단계의 통계를 출력한다.

    Returns:
        region_category/payment_method/monthly_trend 집계 결과와
        clean_stats/outlier_stats 통계를 담은 딕셔너리.
    """
    lf, clean_stats = scan_clean(csv_path, verbose=verbose)
    lf, outlier_stats = filter_outliers_iqr(lf, verbose=verbose)

    return {
        "region_category": agg_region_category(lf),
        "payment_method": agg_payment_method(lf),
        "monthly_trend": agg_monthly_trend(lf),
        "clean_stats": clean_stats,
        "outlier_stats": outlier_stats,
    }


def main() -> None:
    """파이프라인을 실행하고 결과를 출력한 뒤 Pandas 결과와 교차 검증한다."""
    result = run_pipeline(CSV_PATH, verbose=True)

    print("\n[region x category 집계] (total_amount 내림차순, 상위 5행)")
    print(result["region_category"].head(5))

    print("\n[payment_method 확장 집계] (상위 5행)")
    print(result["payment_method"].head(5))

    print("\n[월별 매출 추이]")
    print(result["monthly_trend"])

    pandas_total = 0.0
    pandas_csv = Path(__file__).resolve().parent / "outputs" / "pandas_agg_result.csv"
    if pandas_csv.exists():
        import pandas as pd
        pandas_total = pd.read_csv(pandas_csv)["total_amount"].sum()
        polars_total = result["region_category"]["total_amount"].sum()
        print(f"\n[교차 검증] pandas total_amount 합계={pandas_total:.2f} / "
              f"polars total_amount 합계={polars_total:.2f} / "
              f"차이={abs(pandas_total - polars_total):.4f}")


if __name__ == "__main__":
    main()
