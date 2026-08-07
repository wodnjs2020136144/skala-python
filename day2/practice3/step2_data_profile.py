"""sales_100k.csv 스키마 및 결측치 현황을 점검한다.

df.info()와 isnull().sum()으로 기본 상태를 확인하고, amount 컬럼이
quantity * unit_price와 정합적인지 검증해 데이터 신뢰도를 파악한다.
"""

from pathlib import Path

import pandas as pd

CSV_PATH = Path(__file__).resolve().parents[2] / "sales_100k.csv"


def load_raw(csv_path: Path) -> pd.DataFrame:
    return pd.read_csv(csv_path)


def print_missing_report(df: pd.DataFrame) -> None:
    total = len(df)
    missing = df.isnull().sum()
    ratio = (missing / total * 100).round(3)
    report = pd.DataFrame({"missing_count": missing, "missing_ratio(%)": ratio})
    report = report[report["missing_count"] > 0].sort_values("missing_count", ascending=False)

    print("\n[결측치 현황] (전체 {}행 기준)".format(total))
    if report.empty:
        print("결측치 없음")
    else:
        print(report.to_string())


def check_amount_consistency(df: pd.DataFrame, tolerance: float = 1.0) -> None:
    valid = df.dropna(subset=["amount", "quantity", "unit_price"])
    expected = valid["quantity"] * valid["unit_price"]
    diff = (valid["amount"] - expected).abs()
    mismatch = valid[diff > tolerance]

    print(f"\n[정합성 점검] amount ≈ quantity * unit_price (허용 오차 ±{tolerance})")
    print(f"검증 대상: {len(valid)}행 / 불일치: {len(mismatch)}행 "
          f"({len(mismatch) / len(valid) * 100:.3f}%)")


def main() -> None:
    df = load_raw(CSV_PATH)

    print(f"[파일 경로] {CSV_PATH}")
    print(f"[전체 행/열] {df.shape[0]}행 x {df.shape[1]}열\n")

    print("[df.info()]")
    df.info()

    print_missing_report(df)
    check_amount_consistency(df)


if __name__ == "__main__":
    main()
