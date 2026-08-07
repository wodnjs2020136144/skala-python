"""Pandas 기반 매출 데이터 전처리 및 집계 파이프라인.

결측 행 제거 -> IQR 이상치 제거 -> region x category Named Aggregation
-> payment_method 확장 집계 -> 월별 매출 추이 집계 순으로 처리한다.
"""

from pathlib import Path

import pandas as pd

CSV_PATH = Path(__file__).resolve().parents[2] / "sales_100k.csv"
REQUIRED_COLS = ["region", "category", "amount"]


def load_and_clean(csv_path: Path, verbose: bool = False) -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(csv_path)
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


def remove_outliers_iqr(df: pd.DataFrame, verbose: bool = False) -> tuple[pd.DataFrame, dict]:
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


def agg_region_category(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["region", "category"])
        .agg(
            total_amount=("amount", "sum"),
            avg_amount=("amount", "mean"),
            item_count=("amount", "count"),
        )
        .reset_index()
        .sort_values("total_amount", ascending=False)
    )


def agg_payment_method(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["region", "category", "payment_method"])
        .agg(
            total_amount=("amount", "sum"),
            avg_amount=("amount", "mean"),
            item_count=("amount", "count"),
        )
        .reset_index()
        .sort_values("total_amount", ascending=False)
    )


def agg_monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    month = df["order_date"].str.slice(0, 7)
    return (
        df.assign(order_month=month)
        .groupby("order_month")
        .agg(
            total_amount=("amount", "sum"),
            avg_amount=("amount", "mean"),
            item_count=("amount", "count"),
        )
        .reset_index()
        .sort_values("order_month")
    )


def run_pipeline(csv_path: Path, verbose: bool = False) -> dict:
    df, clean_stats = load_and_clean(csv_path, verbose=verbose)
    df, outlier_stats = remove_outliers_iqr(df, verbose=verbose)

    return {
        "region_category": agg_region_category(df),
        "payment_method": agg_payment_method(df),
        "monthly_trend": agg_monthly_trend(df),
        "clean_stats": clean_stats,
        "outlier_stats": outlier_stats,
    }


def main() -> None:
    result = run_pipeline(CSV_PATH, verbose=True)

    print("\n[region x category 집계] (total_amount 내림차순, 상위 5행)")
    print(result["region_category"].head(5).to_string(index=False))

    print("\n[payment_method 확장 집계] (상위 5행)")
    print(result["payment_method"].head(5).to_string(index=False))

    print("\n[월별 매출 추이]")
    print(result["monthly_trend"].to_string(index=False))

    output_path = Path(__file__).resolve().parent / "outputs" / "pandas_agg_result.csv"
    result["region_category"].to_csv(output_path, index=False)
    print(f"\n[저장 완료] {output_path}")


if __name__ == "__main__":
    main()
