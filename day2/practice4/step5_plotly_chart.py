"""region x category 매출 집계를 Plotly 인터랙티브 바 차트로 저장한다.

practice3의 region x category Named Aggregation 결과(_common.load_region_category_summary)를
그대로 재사용해, 실습3 산출물이 실습4 시각화 입력으로 이어지는 연계 구조를 만족한다.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px

from _common import ensure_output_dir, load_region_category_summary


def build_region_category_chart(agg_df: pd.DataFrame) -> px.bar:
    """region x category 매출 합계를 그룹 바 차트로 그린다.

    Args:
        agg_df: region/category/total_amount 컬럼을 포함한 집계 DataFrame.

    Returns:
        Plotly Figure 객체.
    """
    return px.bar(
        agg_df, x="region", y="total_amount", color="category", barmode="group",
        title="지역 및 카테고리별 매출액 (Plotly Interactive)",
        labels={"total_amount": "총 매출액", "region": "지역", "category": "카테고리"},
    )


def save_chart_html(fig: px.bar, output_path: Path) -> Path:
    """Plotly Figure를 인터랙티브 HTML 파일로 저장한다.

    Args:
        fig: 저장할 Plotly Figure.
        output_path: 저장할 HTML 파일 경로.

    Returns:
        저장된 파일 경로.

    Raises:
        OSError: 저장 디렉토리에 쓰기 권한이 없는 등 파일 저장에 실패할 경우.
    """
    try:
        fig.write_html(output_path)
    except OSError as e:
        raise OSError(f"HTML 파일을 저장할 수 없습니다: {output_path}") from e
    return output_path


def main() -> None:
    """region x category 집계를 로드해 Plotly 차트를 생성하고 HTML로 저장한다."""
    agg_df = load_region_category_summary(verbose=True)
    print(f"\n[집계 결과] {len(agg_df)}개 region x category 조합")
    print(agg_df.head(5).to_string(index=False))

    fig = build_region_category_chart(agg_df)

    output_dir = ensure_output_dir()
    output_path = output_dir / "sales_interactive.html"
    saved_path = save_chart_html(fig, output_path)
    print(f"\n[저장 완료] {saved_path}")


if __name__ == "__main__":
    main()
