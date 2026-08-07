# Day2 Practice3: Pandas / Polars Lazy / DuckDB SQL 성능 비교.
# 작성자: P345 황재원
# 작업환경: Python 3.11.6, macOS, VSCode
# 작성일: 2026-08-07
# 설명: sales_100k.csv 매출 데이터를 대상으로 결측 제거 -> IQR 이상치 제거 -> Named Aggregation을
#       Pandas, Polars Lazy API, DuckDB SQL 세 엔진으로 동일하게 구현하고, 세 엔진의 집계 결과가
#       일치하는지 교차 검증한 뒤 timeit(number=10)으로 처리 성능을 비교한다.

import timeit
from pathlib import Path

import duckdb
import pandas as pd
import polars as pl

CSV_PATH = Path(__file__).resolve().parents[2] / "sales_100k.csv"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
REQUIRED_COLS = ["region", "category", "amount"]
CLEAN_WHERE = "region IS NOT NULL AND category IS NOT NULL AND amount IS NOT NULL"
BENCHMARK_NUMBER = 10


# ---------------------------------------------------------------------------
# 공통 유틸리티
# ---------------------------------------------------------------------------
def ensure_csv_exists(csv_path: Path) -> None:
    """CSV 파일이 실제로 존재하는지 확인한다.

    각 라이브러리(pandas/polars/duckdb)가 파일 부재 시 서로 다른 형태의
    예외를 던지기 전에, 먼저 명확한 메시지로 실패시켜 원인을 바로 알 수 있게 한다.

    Args:
        csv_path: 확인할 CSV 파일 경로.

    Raises:
        FileNotFoundError: 경로에 파일이 존재하지 않을 경우.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {csv_path}")


# ---------------------------------------------------------------------------
# Step2: 데이터 스키마 / 결측치 프로파일링
# ---------------------------------------------------------------------------
def profile_load_raw(csv_path: Path) -> pd.DataFrame:
    """CSV 파일을 가공 없이 그대로 읽어들인다.

    Args:
        csv_path: 읽을 CSV 파일 경로.

    Returns:
        원본 컬럼 구조를 그대로 유지한 DataFrame.

    Raises:
        FileNotFoundError: csv_path에 파일이 없을 경우.
        ValueError: CSV 내용이 비어 있거나 파싱할 수 없는 형식일 경우.
    """
    ensure_csv_exists(csv_path)
    try:
        return pd.read_csv(csv_path)
    except (pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        raise ValueError(f"CSV 파일을 읽을 수 없습니다: {csv_path}") from e


def profile_print_missing_report(df: pd.DataFrame) -> None:
    """컬럼별 결측치 건수와 비율을 계산해 출력한다.

    Args:
        df: 결측치를 점검할 DataFrame.
    """
    total = len(df)
    missing = df.isnull().sum()
    ratio = (missing / total * 100).round(3)
    report = pd.DataFrame({"missing_count": missing, "missing_ratio(%)": ratio})
    report = report[report["missing_count"] > 0].sort_values("missing_count", ascending=False)

    print(f"\n[결측치 현황] (전체 {total}행 기준)")
    if report.empty:
        print("결측치 없음")
    else:
        print(report.to_string())


def profile_check_amount_consistency(df: pd.DataFrame, tolerance: float = 1.0) -> None:
    """amount가 quantity * unit_price와 일치하는지 정합성을 점검한다.

    Args:
        df: 정합성을 점검할 DataFrame.
        tolerance: 허용 오차. 이 값을 초과하는 차이만 불일치로 집계한다.
    """
    valid = df.dropna(subset=["amount", "quantity", "unit_price"])
    expected = valid["quantity"] * valid["unit_price"]
    diff = (valid["amount"] - expected).abs()
    mismatch = valid[diff > tolerance]

    print(f"\n[정합성 점검] amount ≈ quantity * unit_price (허용 오차 ±{tolerance})")
    print(f"검증 대상: {len(valid)}행 / 불일치: {len(mismatch)}행 "
          f"({len(mismatch) / len(valid) * 100:.3f}%)")


def run_data_profile(csv_path: Path) -> None:
    """CSV를 로드해 스키마/결측치/정합성 점검 결과를 순서대로 출력한다."""
    df = profile_load_raw(csv_path)

    print(f"[파일 경로] {csv_path}")
    print(f"[전체 행/열] {df.shape[0]}행 x {df.shape[1]}열\n")

    print("[df.info()]")
    df.info()

    profile_print_missing_report(df)
    profile_check_amount_consistency(df)


# ---------------------------------------------------------------------------
# Step3: Pandas 파이프라인
# ---------------------------------------------------------------------------
def pandas_load_and_clean(csv_path: Path, verbose: bool = False) -> tuple[pd.DataFrame, dict]:
    """CSV를 읽고 region/category/amount 중 하나라도 결측인 행을 제거한다.

    Args:
        csv_path: 읽을 CSV 파일 경로.
        verbose: True면 결측 제거 전후 행 수와 컬럼별 결측 건수를 출력한다.

    Returns:
        결측 행이 제거된 DataFrame과 (전/후 행 수, 컬럼별 결측 건수) 통계 딕셔너리.

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

    missing_counts = {col: int(df[col].isnull().sum()) for col in REQUIRED_COLS}
    df = df.dropna(subset=REQUIRED_COLS)
    after = len(df)

    stats = {"before": before, "after": after, "dropped": before - after,
              "missing_by_col": missing_counts}
    if verbose:
        print(f"[결측 제거] {before}행 -> {after}행 (제거 {stats['dropped']}행)")
        for col, cnt in missing_counts.items():
            print(f"  - {col}: {cnt}건 결측")
    return df, stats


def pandas_remove_outliers_iqr(df: pd.DataFrame, verbose: bool = False) -> tuple[pd.DataFrame, dict]:
    """amount 컬럼 기준 IQR 범위를 벗어나는 이상치 행을 제거한다.

    Q1 - 1.5*IQR ~ Q3 + 1.5*IQR 범위를 정상 범위로 간주한다.

    Args:
        df: 이상치를 제거할 DataFrame.
        verbose: True면 IQR 범위와 제거 전후 행 수를 출력한다.

    Returns:
        이상치가 제거된 DataFrame과 (Q1, Q3, IQR, 허용범위, 제거 건수) 통계 딕셔너리.
    """
    before = len(df)
    q1 = df["amount"].quantile(0.25)
    q3 = df["amount"].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    filtered = df[(df["amount"] >= lower) & (df["amount"] <= upper)]
    after = len(filtered)

    stats = {"before": before, "after": after, "removed": before - after,
              "q1": q1, "q3": q3, "iqr": iqr, "lower": lower, "upper": upper}
    if verbose:
        print(f"[IQR 이상치 제거] Q1={q1:.1f}, Q3={q3:.1f}, IQR={iqr:.1f}, "
              f"허용범위=[{lower:.1f}, {upper:.1f}]")
        print(f"  {before}행 -> {after}행 (제거 {stats['removed']}행)")
    return filtered, stats


def _pandas_named_aggregation(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """group_cols 기준으로 total_amount/avg_amount/item_count를 집계하는 공통 로직.

    region x category, payment_method 확장 집계, 월별 추이 집계가 group_cols만
    다르고 나머지 집계식은 동일하므로 이 헬퍼로 중복을 제거한다.

    Args:
        df: 집계 대상 DataFrame.
        group_cols: groupby 기준 컬럼 목록.

    Returns:
        total_amount(합계), avg_amount(평균), item_count(건수)를 담은
        DataFrame. total_amount 내림차순으로 정렬된다.
    """
    return (
        df.groupby(group_cols)
        .agg(
            total_amount=("amount", "sum"),
            avg_amount=("amount", "mean"),
            item_count=("amount", "count"),
        )
        .reset_index()
        .sort_values("total_amount", ascending=False)
    )


def pandas_agg_region_category(df: pd.DataFrame) -> pd.DataFrame:
    """region x category 기준으로 매출을 집계한다.

    Args:
        df: 집계 대상 DataFrame.

    Returns:
        _pandas_named_aggregation() 결과. total_amount 내림차순으로 정렬된다.
    """
    return _pandas_named_aggregation(df, ["region", "category"])


def pandas_agg_payment_method(df: pd.DataFrame) -> pd.DataFrame:
    """region x category x payment_method 기준으로 매출을 집계한다.

    실제 데이터에만 존재하는 payment_method 컬럼을 활용해 기본 집계보다
    한 단계 더 세분화된 결제수단별 매출 비교를 제공한다.

    Args:
        df: 집계 대상 DataFrame.

    Returns:
        _pandas_named_aggregation() 결과. total_amount 내림차순으로 정렬된다.
    """
    return _pandas_named_aggregation(df, ["region", "category", "payment_method"])


def pandas_agg_monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """order_date에서 연-월을 추출해 월별 매출 추이를 집계한다.

    Args:
        df: 집계 대상 DataFrame. order_date 컬럼은 'YYYY-MM-DD' 형식 문자열이어야 한다.

    Returns:
        order_month(연-월) 기준 _pandas_named_aggregation() 결과를 order_month
        오름차순으로 다시 정렬한 DataFrame.
    """
    month = df["order_date"].str.slice(0, 7)
    return _pandas_named_aggregation(df.assign(order_month=month), ["order_month"]).sort_values(
        "order_month"
    )


def run_pandas_pipeline(csv_path: Path, verbose: bool = False) -> dict:
    """결측 제거 -> IQR 이상치 제거 -> 집계 3종으로 이어지는 Pandas 파이프라인을 실행한다.

    Args:
        csv_path: 처리할 CSV 파일 경로.
        verbose: True면 각 처리 단계의 통계를 출력한다.

    Returns:
        region_category/payment_method/monthly_trend 집계 결과와
        clean_stats/outlier_stats 통계를 담은 딕셔너리.
    """
    df, clean_stats = pandas_load_and_clean(csv_path, verbose=verbose)
    df, outlier_stats = pandas_remove_outliers_iqr(df, verbose=verbose)

    return {
        "region_category": pandas_agg_region_category(df),
        "payment_method": pandas_agg_payment_method(df),
        "monthly_trend": pandas_agg_monthly_trend(df),
        "clean_stats": clean_stats,
        "outlier_stats": outlier_stats,
    }


# ---------------------------------------------------------------------------
# Step4: Polars Lazy 파이프라인
# ---------------------------------------------------------------------------
def polars_scan_clean(csv_path: Path, verbose: bool = False) -> tuple[pl.LazyFrame, dict]:
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


def polars_filter_outliers_iqr(lf: pl.LazyFrame, verbose: bool = False) -> tuple[pl.LazyFrame, dict]:
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


def _polars_named_aggregation(lf: pl.LazyFrame, group_cols: list[str]) -> pl.DataFrame:
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


def polars_agg_region_category(lf: pl.LazyFrame) -> pl.DataFrame:
    """region x category 기준으로 매출을 집계한다.

    Args:
        lf: 집계 대상 LazyFrame.

    Returns:
        _polars_named_aggregation() 결과. total_amount 내림차순으로 정렬된다.
    """
    return _polars_named_aggregation(lf, ["region", "category"])


def polars_agg_payment_method(lf: pl.LazyFrame) -> pl.DataFrame:
    """region x category x payment_method 기준으로 매출을 집계한다.

    Args:
        lf: 집계 대상 LazyFrame.

    Returns:
        _polars_named_aggregation() 결과. total_amount 내림차순으로 정렬된다.
    """
    return _polars_named_aggregation(lf, ["region", "category", "payment_method"])


def polars_agg_monthly_trend(lf: pl.LazyFrame) -> pl.DataFrame:
    """order_date에서 연-월을 추출해 월별 매출 추이를 집계한다.

    Args:
        lf: 집계 대상 LazyFrame. order_date 컬럼은 'YYYY-MM-DD' 형식 문자열이어야 한다.

    Returns:
        order_month(연-월) 기준 _polars_named_aggregation() 결과를 order_month
        오름차순으로 다시 정렬한 DataFrame.
    """
    monthly_lf = lf.with_columns(pl.col("order_date").str.slice(0, 7).alias("order_month"))
    return _polars_named_aggregation(monthly_lf, ["order_month"]).sort("order_month")


def run_polars_pipeline(csv_path: Path, verbose: bool = False) -> dict:
    """결측 제거 -> IQR 이상치 제거 -> 집계 3종으로 이어지는 Polars Lazy 파이프라인을 실행한다.

    Args:
        csv_path: 처리할 CSV 파일 경로.
        verbose: True면 각 처리 단계의 통계를 출력한다.

    Returns:
        region_category/payment_method/monthly_trend 집계 결과와
        clean_stats/outlier_stats 통계를 담은 딕셔너리.
    """
    lf, clean_stats = polars_scan_clean(csv_path, verbose=verbose)
    lf, outlier_stats = polars_filter_outliers_iqr(lf, verbose=verbose)

    return {
        "region_category": polars_agg_region_category(lf),
        "payment_method": polars_agg_payment_method(lf),
        "monthly_trend": polars_agg_monthly_trend(lf),
        "clean_stats": clean_stats,
        "outlier_stats": outlier_stats,
    }


# ---------------------------------------------------------------------------
# Step5: DuckDB SQL 파이프라인
# ---------------------------------------------------------------------------
def duckdb_profile_and_bounds(csv_path: Path, verbose: bool = False) -> dict:
    """결측 건수, 결측 제거 전후 행 수, IQR 이상치 허용범위를 SQL로 계산한다.

    quantile_cont로 계산한 Q1/Q3를 기준으로 IQR 이상치 하한/상한을 구해
    이후 집계 쿼리(duckdb_agg_*)에서 재사용할 수 있도록 반환한다.

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


def duckdb_build_filtered_query(csv_path: Path, bounds: dict) -> str:
    """결측 제거 + IQR 이상치 제거 조건이 적용된 SELECT 서브쿼리 문자열을 만든다.

    Args:
        csv_path: 대상 CSV 파일 경로.
        bounds: duckdb_profile_and_bounds()가 반환한 lower/upper 허용범위를 포함한 딕셔너리.

    Returns:
        집계 쿼리에서 FROM 절 서브쿼리로 사용할 SQL 문자열.
    """
    return f"""
        SELECT * FROM '{csv_path}'
        WHERE {CLEAN_WHERE} AND amount BETWEEN {bounds['lower']} AND {bounds['upper']}
    """


def _duckdb_named_agg_sql(csv_path: Path, bounds: dict, group_cols: list[str]) -> pd.DataFrame:
    """group_cols 기준으로 total_amount/avg_amount/item_count를 집계하는 공통 SQL 실행 로직.

    region x category, payment_method 확장 집계가 group_cols만 다르고
    나머지 SELECT/GROUP BY 구조는 동일하므로 이 헬퍼로 중복을 제거한다.

    Args:
        csv_path: 대상 CSV 파일 경로.
        bounds: duckdb_profile_and_bounds()가 반환한 이상치 허용범위 딕셔너리.
        group_cols: GROUP BY 기준 컬럼 목록.

    Returns:
        total_amount(합계), avg_amount(평균), item_count(건수)를 담은
        DataFrame. total_amount 내림차순으로 정렬된다.
    """
    filtered = duckdb_build_filtered_query(csv_path, bounds)
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


def duckdb_agg_region_category(csv_path: Path, bounds: dict) -> pd.DataFrame:
    """region x category 기준으로 매출을 집계한다.

    Args:
        csv_path: 대상 CSV 파일 경로.
        bounds: duckdb_profile_and_bounds()가 반환한 이상치 허용범위 딕셔너리.

    Returns:
        _duckdb_named_agg_sql() 결과. total_amount 내림차순으로 정렬된다.
    """
    return _duckdb_named_agg_sql(csv_path, bounds, ["region", "category"])


def duckdb_agg_payment_method(csv_path: Path, bounds: dict) -> pd.DataFrame:
    """region x category x payment_method 기준으로 매출을 집계한다.

    Args:
        csv_path: 대상 CSV 파일 경로.
        bounds: duckdb_profile_and_bounds()가 반환한 이상치 허용범위 딕셔너리.

    Returns:
        _duckdb_named_agg_sql() 결과. total_amount 내림차순으로 정렬된다.
    """
    return _duckdb_named_agg_sql(csv_path, bounds, ["region", "category", "payment_method"])


def duckdb_agg_monthly_trend(csv_path: Path, bounds: dict) -> pd.DataFrame:
    """order_date에서 연-월을 추출해 월별 매출 추이를 집계한다.

    order_date는 CSV 스캔 시 DuckDB가 DATE 타입으로 자동 추론하므로
    SUBSTR에 넘기기 전 VARCHAR로 명시적으로 캐스팅한다.

    Args:
        csv_path: 대상 CSV 파일 경로.
        bounds: duckdb_profile_and_bounds()가 반환한 이상치 허용범위 딕셔너리.

    Returns:
        order_month(연-월), total_amount, avg_amount, item_count를 담은
        DataFrame. order_month 오름차순으로 정렬된다.
    """
    filtered = duckdb_build_filtered_query(csv_path, bounds)
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


def run_duckdb_pipeline(csv_path: Path, verbose: bool = False) -> dict:
    """결측/이상치 범위 계산 -> SQL 집계 3종으로 이어지는 DuckDB 파이프라인을 실행한다.

    Args:
        csv_path: 처리할 CSV 파일 경로.
        verbose: True면 각 처리 단계의 통계를 출력한다.

    Returns:
        region_category/payment_method/monthly_trend 집계 결과와
        bounds(결측/이상치 통계) 딕셔너리.
    """
    bounds = duckdb_profile_and_bounds(csv_path, verbose=verbose)

    return {
        "region_category": duckdb_agg_region_category(csv_path, bounds),
        "payment_method": duckdb_agg_payment_method(csv_path, bounds),
        "monthly_trend": duckdb_agg_monthly_trend(csv_path, bounds),
        "bounds": bounds,
    }


# ---------------------------------------------------------------------------
# Step6: 성능 벤치마크
# ---------------------------------------------------------------------------
def run_benchmark(csv_path: Path) -> list[dict]:
    """Pandas/Polars/DuckDB run_*_pipeline()을 동일 반복 횟수로 timeit 측정한다.

    verbose=False로 호출해 파이프라인 내부 print를 억제하고 순수 처리
    시간만 측정한다.

    Args:
        csv_path: 처리할 CSV 파일 경로.

    Returns:
        엔진별 {engine, avg_ms(평균 소요시간), number(반복 횟수)} 딕셔너리 리스트.
    """
    engines = [
        ("Pandas", lambda: run_pandas_pipeline(csv_path, verbose=False)),
        ("Polars Lazy", lambda: run_polars_pipeline(csv_path, verbose=False)),
        ("DuckDB SQL", lambda: run_duckdb_pipeline(csv_path, verbose=False)),
    ]

    results = []
    for name, func in engines:
        total_sec = timeit.timeit(func, number=BENCHMARK_NUMBER)
        avg_ms = total_sec / BENCHMARK_NUMBER * 1000
        results.append({"engine": name, "avg_ms": avg_ms, "number": BENCHMARK_NUMBER})
    return results


def format_benchmark_table(results: list[dict]) -> str:
    """벤치마크 결과를 평균 소요시간 오름차순 markdown 표 문자열로 변환한다.

    Args:
        results: run_benchmark()가 반환한 엔진별 결과 리스트.

    Returns:
        markdown 표 형식 문자열.
    """
    lines = ["| 엔진 | 평균 소요시간(ms) | 반복 횟수 |", "|---|---|---|"]
    for r in sorted(results, key=lambda x: x["avg_ms"]):
        lines.append(f"| {r['engine']} | {r['avg_ms']:.2f} | {r['number']} |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 전체 실행
# ---------------------------------------------------------------------------
def main() -> None:
    """Step2(프로파일링) -> Step3~5(3엔진 파이프라인+교차검증) -> Step6(벤치마크) 순으로 실행한다."""
    print("=" * 60)
    print("[Step2] 데이터 스키마 / 결측치 프로파일링")
    print("=" * 60)
    run_data_profile(CSV_PATH)

    print("\n" + "=" * 60)
    print("[Step3] Pandas 파이프라인")
    print("=" * 60)
    pandas_result = run_pandas_pipeline(CSV_PATH, verbose=True)
    print("\n[region x category 집계] (total_amount 내림차순, 상위 5행)")
    print(pandas_result["region_category"].head(5).to_string(index=False))
    print("\n[payment_method 확장 집계] (상위 5행)")
    print(pandas_result["payment_method"].head(5).to_string(index=False))
    print("\n[월별 매출 추이]")
    print(pandas_result["monthly_trend"].to_string(index=False))

    OUTPUT_DIR.mkdir(exist_ok=True)
    pandas_csv_path = OUTPUT_DIR / "pandas_agg_result.csv"
    pandas_result["region_category"].to_csv(pandas_csv_path, index=False)
    print(f"\n[저장 완료] {pandas_csv_path}")
    pandas_total = pandas_result["region_category"]["total_amount"].sum()

    print("\n" + "=" * 60)
    print("[Step4] Polars Lazy 파이프라인")
    print("=" * 60)
    polars_result = run_polars_pipeline(CSV_PATH, verbose=True)
    print("\n[region x category 집계] (total_amount 내림차순, 상위 5행)")
    print(polars_result["region_category"].head(5))
    polars_total = polars_result["region_category"]["total_amount"].sum()
    print(f"\n[교차 검증] pandas total_amount 합계={pandas_total:.2f} / "
          f"polars total_amount 합계={polars_total:.2f} / "
          f"차이={abs(pandas_total - polars_total):.4f}")

    print("\n" + "=" * 60)
    print("[Step5] DuckDB SQL 파이프라인")
    print("=" * 60)
    duckdb_result = run_duckdb_pipeline(CSV_PATH, verbose=True)
    print("\n[region x category 집계] (total_amount 내림차순, 상위 5행)")
    print(duckdb_result["region_category"].head(5).to_string(index=False))
    duckdb_total = duckdb_result["region_category"]["total_amount"].sum()
    print(f"\n[교차 검증] pandas total_amount 합계={pandas_total:.2f} / "
          f"duckdb total_amount 합계={duckdb_total:.2f} / "
          f"차이={abs(pandas_total - duckdb_total):.4f}")

    print("\n" + "=" * 60)
    print("[Step6] 성능 벤치마크")
    print("=" * 60)
    print(f"[벤치마크 조건] number={BENCHMARK_NUMBER} (세 엔진 동일 반복 횟수)")
    print("측정 중...")
    results = run_benchmark(CSV_PATH)

    print("\n=======================================================")
    print("[Practice3 엔진 성능 비교 벤치마크]")
    print("=======================================================")
    for r in results:
        print(f"  - {r['engine']:<12}: {r['avg_ms']:.2f} ms")
    print("=======================================================")

    fastest = min(results, key=lambda x: x["avg_ms"])
    print(f"\n가장 빠른 엔진: {fastest['engine']} ({fastest['avg_ms']:.2f} ms)")

    table_md = format_benchmark_table(results)
    benchmark_path = OUTPUT_DIR / "benchmark_result.md"
    benchmark_path.write_text(
        f"# Practice3 엔진 성능 벤치마크\n\n반복 횟수(number)={BENCHMARK_NUMBER}\n\n{table_md}\n",
        encoding="utf-8",
    )
    print(f"\n[저장 완료] {benchmark_path}")


if __name__ == "__main__":
    main()
