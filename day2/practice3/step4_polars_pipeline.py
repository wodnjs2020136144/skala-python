"""Polars Lazy API 기반 매출 데이터 전처리 및 집계 파이프라인.

scan_csv -> filter(결측 제거) -> filter(IQR 이상치 제거) -> group_by -> agg
-> sort -> collect() 체인으로 step3_pandas_pipeline.py와 동일한 집계 3종을 구현한다.
"""

from pathlib import Path

import polars as pl

CSV_PATH = Path(__file__).resolve().parents[2] / "sales_100k.csv"
REQUIRED_COLS = ["region", "category", "amount"]


def scan_clean(csv_path: Path, verbose: bool = False) -> tuple[pl.LazyFrame, dict]:
    lf = pl.scan_csv(csv_path)

    before = lf.select(pl.len()).collect().item()
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


def agg_region_category(lf: pl.LazyFrame) -> pl.DataFrame:
    return (
        lf.group_by(["region", "category"])
        .agg(
            pl.col("amount").sum().alias("total_amount"),
            pl.col("amount").mean().alias("avg_amount"),
            pl.col("amount").count().alias("item_count"),
        )
        .sort("total_amount", descending=True)
        .collect()
    )


def agg_payment_method(lf: pl.LazyFrame) -> pl.DataFrame:
    return (
        lf.group_by(["region", "category", "payment_method"])
        .agg(
            pl.col("amount").sum().alias("total_amount"),
            pl.col("amount").mean().alias("avg_amount"),
            pl.col("amount").count().alias("item_count"),
        )
        .sort("total_amount", descending=True)
        .collect()
    )


def agg_monthly_trend(lf: pl.LazyFrame) -> pl.DataFrame:
    return (
        lf.with_columns(pl.col("order_date").str.slice(0, 7).alias("order_month"))
        .group_by("order_month")
        .agg(
            pl.col("amount").sum().alias("total_amount"),
            pl.col("amount").mean().alias("avg_amount"),
            pl.col("amount").count().alias("item_count"),
        )
        .sort("order_month")
        .collect()
    )


def run_pipeline(csv_path: Path, verbose: bool = False) -> dict:
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
