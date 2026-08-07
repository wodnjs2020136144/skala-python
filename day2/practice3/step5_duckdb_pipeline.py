"""DuckDB SQL 기반 매출 데이터 전처리 및 집계 파이프라인.

ANSI SQL로 결측 제거 -> IQR 이상치 제거 -> region x category 집계 ->
payment_method 확장 집계 -> 월별 매출 추이 집계를 수행한다.
Pandas/Polars 파이프라인과 동일한 로직을 SQL로 표현해 3엔진을 공정하게 비교한다.
"""

from pathlib import Path

import duckdb

CSV_PATH = Path(__file__).resolve().parents[2] / "sales_100k.csv"
CLEAN_WHERE = "region IS NOT NULL AND category IS NOT NULL AND amount IS NOT NULL"


def profile_and_bounds(csv_path: Path, verbose: bool = False) -> dict:
    csv = str(csv_path)

    before = duckdb.sql(f"SELECT COUNT(*) AS n FROM '{csv}'").df()["n"].item()
    missing = duckdb.sql(f"""
        SELECT
            SUM(CASE WHEN region IS NULL THEN 1 ELSE 0 END) AS region,
            SUM(CASE WHEN category IS NULL THEN 1 ELSE 0 END) AS category,
            SUM(CASE WHEN amount IS NULL THEN 1 ELSE 0 END) AS amount
        FROM '{csv}'
    """).df().iloc[0].to_dict()
    after_clean = duckdb.sql(f"SELECT COUNT(*) AS n FROM '{csv}' WHERE {CLEAN_WHERE}").df()["n"].item()

    quantiles = duckdb.sql(f"""
        SELECT
            quantile_cont(amount, 0.25) AS q1,
            quantile_cont(amount, 0.75) AS q3
        FROM '{csv}'
        WHERE {CLEAN_WHERE}
    """).df().iloc[0]
    q1, q3 = float(quantiles["q1"]), float(quantiles["q3"])
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr

    after_outlier = duckdb.sql(f"""
        SELECT COUNT(*) AS n FROM '{csv}'
        WHERE {CLEAN_WHERE} AND amount BETWEEN {lower} AND {upper}
    """).df()["n"].item()

    stats = {
        "before": before, "after_clean": after_clean, "after_outlier": after_outlier,
        "dropped_missing": before - after_clean, "removed_outlier": after_clean - after_outlier,
        "missing_by_col": missing, "q1": q1, "q3": q3, "iqr": iqr, "lower": lower, "upper": upper,
    }
    if verbose:
        print(f"[결측 제거] {before}행 -> {after_clean}행 (제거 {stats['dropped_missing']}행)")
        for col, cnt in missing.items():
            print(f"  - {col}: {int(cnt)}건 결측")
        print(f"[IQR 이상치 제거] Q1={q1:.1f}, Q3={q3:.1f}, IQR={iqr:.1f}, "
              f"허용범위=[{lower:.1f}, {upper:.1f}]")
        print(f"  {after_clean}행 -> {after_outlier}행 (제거 {stats['removed_outlier']}행)")
    return stats


def build_filtered_query(csv_path: Path, bounds: dict) -> str:
    return f"""
        SELECT * FROM '{csv_path}'
        WHERE {CLEAN_WHERE} AND amount BETWEEN {bounds['lower']} AND {bounds['upper']}
    """


def agg_region_category(csv_path: Path, bounds: dict):
    filtered = build_filtered_query(csv_path, bounds)
    query = f"""
        SELECT region, category,
               SUM(amount) AS total_amount,
               AVG(amount) AS avg_amount,
               COUNT(amount) AS item_count
        FROM ({filtered}) t
        GROUP BY region, category
        ORDER BY total_amount DESC
    """
    return duckdb.sql(query).df()


def agg_payment_method(csv_path: Path, bounds: dict):
    filtered = build_filtered_query(csv_path, bounds)
    query = f"""
        SELECT region, category, payment_method,
               SUM(amount) AS total_amount,
               AVG(amount) AS avg_amount,
               COUNT(amount) AS item_count
        FROM ({filtered}) t
        GROUP BY region, category, payment_method
        ORDER BY total_amount DESC
    """
    return duckdb.sql(query).df()


def agg_monthly_trend(csv_path: Path, bounds: dict):
    filtered = build_filtered_query(csv_path, bounds)
    query = f"""
        SELECT SUBSTR(CAST(order_date AS VARCHAR), 1, 7) AS order_month,
               SUM(amount) AS total_amount,
               AVG(amount) AS avg_amount,
               COUNT(amount) AS item_count
        FROM ({filtered}) t
        GROUP BY order_month
        ORDER BY order_month
    """
    return duckdb.sql(query).df()


def run_pipeline(csv_path: Path, verbose: bool = False) -> dict:
    bounds = profile_and_bounds(csv_path, verbose=verbose)

    return {
        "region_category": agg_region_category(csv_path, bounds),
        "payment_method": agg_payment_method(csv_path, bounds),
        "monthly_trend": agg_monthly_trend(csv_path, bounds),
        "bounds": bounds,
    }


def main() -> None:
    result = run_pipeline(CSV_PATH, verbose=True)

    print("\n[region x category 집계] (total_amount 내림차순, 상위 5행)")
    print(result["region_category"].head(5).to_string(index=False))

    print("\n[payment_method 확장 집계] (상위 5행)")
    print(result["payment_method"].head(5).to_string(index=False))

    print("\n[월별 매출 추이]")
    print(result["monthly_trend"].to_string(index=False))

    pandas_csv = Path(__file__).resolve().parent / "outputs" / "pandas_agg_result.csv"
    if pandas_csv.exists():
        import pandas as pd
        pandas_total = pd.read_csv(pandas_csv)["total_amount"].sum()
        duckdb_total = result["region_category"]["total_amount"].sum()
        print(f"\n[교차 검증] pandas total_amount 합계={pandas_total:.2f} / "
              f"duckdb total_amount 합계={duckdb_total:.2f} / "
              f"차이={abs(pandas_total - duckdb_total):.4f}")


if __name__ == "__main__":
    main()
