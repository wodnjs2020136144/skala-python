"""IQR 정제 매출 데이터를 4종 EDA 차트(2x2 서브플롯)로 시각화한다.

practice3의 결측 제거 + IQR 이상치 제거 결과(DataFrame)를 입력으로 받아, 매출액 분포,
지역별 분포, 월별 추이, 수치형 변수 상관관계를 한 figure 안에 배치한다.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes

from _common import ensure_output_dir, load_cleaned_sales

NUMERIC_CORR_COLS = ["amount", "quantity", "unit_price", "customer_age"]


def build_amount_histogram(ax: Axes, df: pd.DataFrame) -> None:
    """매출액(amount) 분포를 히스토그램 + KDE로 그린다.

    Args:
        ax: 그릴 대상 Axes.
        df: amount 컬럼을 포함한 DataFrame.
    """
    sns.histplot(df["amount"], kde=True, ax=ax, color="skyblue")
    ax.set_title("1) 매출액 분포 (Histogram + KDE)")
    ax.set_xlabel("amount")


def build_region_boxplot(ax: Axes, df: pd.DataFrame) -> None:
    """지역(region)별 매출액 분포를 박스플롯으로 그린다.

    Args:
        ax: 그릴 대상 Axes.
        df: region/amount 컬럼을 포함한 DataFrame.
    """
    sns.boxplot(x="region", y="amount", data=df, ax=ax, hue="region",
                palette="Set2", legend=False)
    ax.set_title("2) 지역별 매출 분포 (Boxplot)")
    ax.tick_params(axis="x", rotation=30)


def build_monthly_trend_line(ax: Axes, df: pd.DataFrame) -> None:
    """order_date에서 연-월을 추출해 월별 매출 추이를 라인차트로 그린다.

    실제 데이터에만 존재하는 order_date 컬럼을 활용해, practice3의 월별 집계와
    같은 관점(연-월 단위 총매출 추이)을 시각화로 보여준다.

    Args:
        ax: 그릴 대상 Axes.
        df: order_date/amount 컬럼을 포함한 DataFrame.
    """
    monthly = (
        df.assign(order_month=df["order_date"].str.slice(0, 7))
        .groupby("order_month")["amount"]
        .sum()
        .reset_index()
        .sort_values("order_month")
    )
    ax.plot(monthly["order_month"], monthly["amount"], marker="o", color="darkorange")
    ax.set_title("3) 월별 총 매출액 추이 (Line)")
    ax.tick_params(axis="x", rotation=60)


def build_correlation_heatmap(ax: Axes, df: pd.DataFrame) -> None:
    """수치형 변수(amount/quantity/unit_price/customer_age) 간 상관관계를 히트맵으로 그린다.

    Args:
        ax: 그릴 대상 Axes.
        df: NUMERIC_CORR_COLS에 해당하는 컬럼을 포함한 DataFrame.
    """
    corr = df[NUMERIC_CORR_COLS].corr()
    sns.heatmap(corr, annot=True, cmap="coolwarm", ax=ax, fmt=".2f")
    ax.set_title("4) 수치형 변수 상관관계 (Heatmap)")


def draw_eda_subplots(df: pd.DataFrame, output_path: Path) -> Path:
    """4종 차트를 2x2 서브플롯 단일 figure로 그려 png로 저장한다.

    Args:
        df: 시각화 대상 정제 DataFrame.
        output_path: 저장할 png 파일 경로.

    Returns:
        저장된 png 파일 경로.

    Raises:
        OSError: 저장 디렉토리에 쓰기 권한이 없는 등 파일 저장에 실패할 경우.
    """
    sns.set_style("whitegrid")
    # sns.set_style()가 font.family를 sans-serif로 재설정하므로, 한글 라벨이
    # 깨지지 않도록 스타일 적용 이후에 macOS 내장 한글 폰트를 다시 지정한다.
    plt.rcParams["font.family"] = "AppleGothic"
    plt.rcParams["axes.unicode_minus"] = False
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    build_amount_histogram(axes[0, 0], df)
    build_region_boxplot(axes[0, 1], df)
    build_monthly_trend_line(axes[1, 0], df)
    build_correlation_heatmap(axes[1, 1], df)

    fig.tight_layout()
    try:
        fig.savefig(output_path)
    except OSError as e:
        raise OSError(f"차트 이미지를 저장할 수 없습니다: {output_path}") from e
    finally:
        plt.close(fig)
    return output_path


def main() -> None:
    """정제 데이터를 로드해 2x2 서브플롯 차트를 그리고 결과를 출력한다."""
    df = load_cleaned_sales(verbose=True)
    print(f"\n[시각화 대상] {len(df)}행 (결측 제거 + IQR 이상치 제거 완료)")

    output_dir = ensure_output_dir()
    output_path = output_dir / "eda_2x2_subplots.png"
    saved_path = draw_eda_subplots(df, output_path)
    print(f"[저장 완료] {saved_path}")


if __name__ == "__main__":
    main()
