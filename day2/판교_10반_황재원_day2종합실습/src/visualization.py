"""Seaborn 정적 차트 및 Plotly 인터랙티브 차트.

Step 7(Seaborn·Plotly 시각화)을 구현한다.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import seaborn as sns

from src.eda import TARGET_COL

TOP_N_COUNTRIES = 10


def create_seaborn_charts(df: pd.DataFrame, output_path: Path) -> Path:
    """급여 분포·그룹 비교·상관관계를 2x2 서브플롯 PNG로 저장한다.

    Args:
        df: 정제·피처 선택이 끝난 DataFrame.
        output_path: 저장할 PNG 파일 경로.

    Returns:
        저장된 PNG 파일 경로.
    """
    sns.set_style("whitegrid")
    # sns.set_style()이 font.family를 초기화하므로 그 이후에 한글 폰트를 다시 지정한다.
    plt.rcParams["font.family"] = "AppleGothic"
    plt.rcParams["axes.unicode_minus"] = False

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    sns.histplot(df[TARGET_COL], kde=True, ax=axes[0, 0], color="steelblue")
    axes[0, 0].set_title("급여 분포 (히스토그램 + KDE)")
    axes[0, 0].set_xlabel("연환산 급여 (USD)")
    axes[0, 0].set_ylabel("빈도")

    sns.boxplot(data=df, x="RemoteWork", y=TARGET_COL, ax=axes[0, 1])
    axes[0, 1].set_title("원격근무 형태별 급여 분포")
    axes[0, 1].set_xlabel("원격근무 형태")
    axes[0, 1].set_ylabel("연환산 급여 (USD)")
    axes[0, 1].tick_params(axis="x", rotation=15)

    sns.scatterplot(data=df, x="WorkExp", y=TARGET_COL, alpha=0.3, ax=axes[1, 0])
    axes[1, 0].set_title("경력연수(WorkExp) vs 급여")
    axes[1, 0].set_xlabel("경력 연수")
    axes[1, 0].set_ylabel("연환산 급여 (USD)")

    numeric_cols = ["WorkExp", "JobSat", TARGET_COL]
    corr = df[numeric_cols].corr(method="pearson")
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", ax=axes[1, 1])
    axes[1, 1].set_title("수치형 변수 상관관계 히트맵")

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=100)
    plt.close(fig)
    print(f"[visualization] Seaborn 2x2 차트 저장: {output_path}")
    return output_path


def create_plotly_chart(df: pd.DataFrame, output_path: Path) -> Path:
    """국가별(상위 N개) 급여 분포를 Plotly 인터랙티브 박스플롯 HTML로 저장한다.

    Args:
        df: 정제·피처 선택이 끝난 DataFrame.
        output_path: 저장할 HTML 파일 경로.

    Returns:
        저장된 HTML 파일 경로.
    """
    top_countries = df["Country"].value_counts().head(TOP_N_COUNTRIES).index
    plot_df = df[df["Country"].isin(top_countries)]

    fig = px.box(
        plot_df,
        x="Country",
        y=TARGET_COL,
        color="Country",
        title=f"국가별(응답 수 상위 {TOP_N_COUNTRIES}개) 급여 분포",
        labels={"Country": "국가", TARGET_COL: "연환산 급여 (USD)"},
    )
    fig.update_layout(showlegend=False)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    print(f"[visualization] Plotly 인터랙티브 차트 저장: {output_path}")
    return output_path
