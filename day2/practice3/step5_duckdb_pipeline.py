"""DuckDB SQL 기반 매출 데이터 전처리 및 집계 파이프라인.

ANSI SQL로 결측 제거 -> IQR 이상치 제거 -> region x category 집계 ->
payment_method 확장 집계 -> 월별 매출 추이 집계를 수행한다.
Pandas/Polars 파이프라인과 동일한 로직을 SQL로 표현해 3엔진을 공정하게 비교한다.
"""

from pathlib import Path

import duckdb

from _common import ensure_csv_exists

CSV_PATH = Path(__file__).resolve().parents[2] / "sales_100k.csv"
CLEAN_WHERE = "region IS NOT NULL AND category IS NOT NULL AND amount IS NOT NULL"


def profile_and_bounds(csv_path: Path, verbose: bool = False) -> dict:
    """결측 건수, 결측 제거 전후 행 수, IQR 이상치 허용범위를 SQL로 계산한다.

    quantile_cont로 계산한 Q1/Q3를 기준으로 IQR 이상치 하한/상한을 구해
    이후 집계 쿼리(agg_*)에서 재사용할 수 있도록 반환한다.

    Args:
        csv_path: 대상 CSV 파일 경로.
        verbose: True면 결측/이상치 제거 통계를 출력한다.

    Returns:
        결측 건수, 행 수 변화, Q1/Q3/IQR, 이상치 허용범위(lower/upper)를 담은 딕셔너리.

    Raises:
        FileNotFoundError: csv_path에 파일이 없을 경우.
        ValueError: CSV 내용을 읽을 수 없을 경우.
    """
    ensure_csv_exists(csv_path)
    csv = str(csv_path)

    try:
        before = duckdb.sql(f"SELECT COUNT(*) AS n FROM '{csv}'").df()["n"].item()
    except duckdb.Error as e:
        raise ValueError(f"CSV 파일을 읽을 수 없습니다: {csv_path}") from e
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
    """결측 제거 + IQR 이상치 제거 조건이 적용된 SELECT 서브쿼리 문자열을 만든다.

    Args:
        csv_path: 대상 CSV 파일 경로.
        bounds: profile_and_bounds()가 반환한 lower/upper 허용범위를 포함한 딕셔너리.

    Returns:
        집계 쿼리에서 FROM 절 서브쿼리로 사용할 SQL 문자열.
    """
    return f"""
        SELECT * FROM '{csv_path}'
        WHERE {CLEAN_WHERE} AND amount BETWEEN {bounds['lower']} AND {bounds['upper']}
    """


def _named_agg_sql(csv_path: Path, bounds: dict, group_cols: list[str]):
    """group_cols 기준으로 total_amount/avg_amount/item_count를 집계하는 공통 SQL 실행 로직.

    region x category, payment_method 확장 집계가 group_cols만 다르고
    나머지 SELECT/GROUP BY 구조는 동일하므로 이 헬퍼로 중복을 제거한다.

    Args:
        csv_path: 대상 CSV 파일 경로.
        bounds: profile_and_bounds()가 반환한 이상치 허용범위 딕셔너리.
        group_cols: GROUP BY 기준 컬럼 목록.

    Returns:
        total_amount(합계), avg_amount(평균), item_count(건수)를 담은
        DataFrame. total_amount 내림차순으로 정렬된다.
    """
    filtered = build_filtered_query(csv_path, bounds)
    group_by = ", ".join(group_cols)
    query = f"""
        SELECT {group_by},
               SUM(amount) AS total_amount,
               AVG(amount) AS avg_amount,
               COUNT(amount) AS item_count
        FROM ({filtered}) t
        GROUP BY {group_by}
        ORDER BY total_amount DESC
    """
    return duckdb.sql(query).df()


def agg_region_category(csv_path: Path, bounds: dict):
    """region x category 기준으로 매출을 집계한다.

    Args:
        csv_path: 대상 CSV 파일 경로.
        bounds: profile_and_bounds()가 반환한 이상치 허용범위 딕셔너리.

    Returns:
        _named_agg_sql() 결과. total_amount 내림차순으로 정렬된다.
    """
    return _named_agg_sql(csv_path, bounds, ["region", "category"])


def agg_payment_method(csv_path: Path, bounds: dict):
    """region x category x payment_method 기준으로 매출을 집계한다.

    Args:
        csv_path: 대상 CSV 파일 경로.
        bounds: profile_and_bounds()가 반환한 이상치 허용범위 딕셔너리.

    Returns:
        _named_agg_sql() 결과. total_amount 내림차순으로 정렬된다.
    """
    return _named_agg_sql(csv_path, bounds, ["region", "category", "payment_method"])


def agg_monthly_trend(csv_path: Path, bounds: dict):
    """order_date에서 연-월을 추출해 월별 매출 추이를 집계한다.

    order_date는 CSV 스캔 시 DuckDB가 DATE 타입으로 자동 추론하므로
    SUBSTR에 넘기기 전 VARCHAR로 명시적으로 캐스팅한다.

    Args:
        csv_path: 대상 CSV 파일 경로.
        bounds: profile_and_bounds()가 반환한 이상치 허용범위 딕셔너리.

    Returns:
        order_month(연-월), total_amount, avg_amount, item_count를 담은
        DataFrame. order_month 오름차순으로 정렬된다.
    """
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
    """결측/이상치 범위 계산 -> SQL 집계 3종으로 이어지는 전체 파이프라인을 실행한다.

    Args:
        csv_path: 처리할 CSV 파일 경로.
        verbose: True면 각 처리 단계의 통계를 출력한다.

    Returns:
        region_category/payment_method/monthly_trend 집계 결과와
        bounds(결측/이상치 통계) 딕셔너리.
    """
    bounds = profile_and_bounds(csv_path, verbose=verbose)

    return {
        "region_category": agg_region_category(csv_path, bounds),
        "payment_method": agg_payment_method(csv_path, bounds),
        "monthly_trend": agg_monthly_trend(csv_path, bounds),
        "bounds": bounds,
    }


def main() -> None:
    """파이프라인을 실행하고 결과를 출력한 뒤 Pandas 결과와 교차 검증한다."""
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
