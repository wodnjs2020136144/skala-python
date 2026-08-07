"""sales_100k.csv 스키마 및 결측치 현황을 점검한다.

df.info()와 isnull().sum()으로 기본 상태를 확인하고, amount 컬럼이
quantity * unit_price와 정합적인지 검증해 데이터 신뢰도를 파악한다.
"""

from pathlib import Path

import pandas as pd

CSV_PATH = Path(__file__).resolve().parents[2] / "sales_100k.csv"


def load_raw(csv_path: Path) -> pd.DataFrame:
    """CSV 파일을 가공 없이 그대로 읽어들인다.

    Args:
        csv_path: 읽을 CSV 파일 경로.

    Returns:
        원본 컬럼 구조를 그대로 유지한 DataFrame.
    """
    return pd.read_csv(csv_path)


def print_missing_report(df: pd.DataFrame) -> None:
    """컬럼별 결측치 건수와 비율을 계산해 출력한다.

    Args:
        df: 결측치를 점검할 DataFrame.
    """
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


def main() -> None:
    """CSV를 로드해 스키마/결측치/정합성 점검 결과를 순서대로 출력한다."""
    df = load_raw(CSV_PATH)

    print(f"[파일 경로] {CSV_PATH}")
    print(f"[전체 행/열] {df.shape[0]}행 x {df.shape[1]}열\n")

    print("[df.info()]")
    df.info()

    print_missing_report(df)
    check_amount_consistency(df)


if __name__ == "__main__":
    main()
