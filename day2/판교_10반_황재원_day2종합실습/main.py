"""Stack Overflow Developer Survey 2024 개발자 급여 분석 — 전체 실행 엔트리포인트.

Step 0(Pandas/Polars 로딩 비교) ~ Step 10(report.md 자동 생성)을 순서대로 실행한다.
"""

import time
from datetime import datetime, timezone
from pathlib import Path

from src.data_loader import RAW_CSV_PATH, compare_engines, ensure_dataset
from src.eda import (
    TARGET_COL,
    run_categorical_group_comparison,
    run_clean_eda,
    run_correlation_analysis,
    run_raw_eda,
)
from src.eda_polars import (
    run_raw_missing_rate_polars,
    run_salary_group_comparison_polars,
)
from src.modeling import run_model_pipelines
from src.preprocessing import run_preprocessing, select_model_columns
from src.statistics import run_remote_work_ttest
from src.visualization import create_plotly_chart, create_seaborn_charts

PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "outputs" / "logs"
CHARTS_DIR = PROJECT_ROOT / "outputs" / "charts"
HTML_DIR = PROJECT_ROOT / "outputs" / "html"
MODELS_DIR = PROJECT_ROOT / "outputs" / "models"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_PATH = PROJECT_ROOT / "report.md"


def generate_report(context: dict, report_path: Path) -> None:
    """각 단계 실행 결과를 종합해 report.md를 자동 생성한다.

    Args:
        context: Step 0~9 실행 결과를 모은 딕셔너리.
        report_path: 저장할 report.md 경로.
    """
    engine_stats = context["engine_stats"]
    prep_stats = context["prep_stats"]
    correlations = context["correlations"]
    ttest = context["ttest"]
    regression = context["regression"]
    classification = context["classification"]
    polars_eda = context["polars_eda"]

    top_corr_col, top_corr_val = next(iter(correlations.items()))

    lines = [
        "# Stack Overflow Developer Survey 2024 개발자 급여 분석 리포트",
        "",
        f"생성 일시: {datetime.now(tz=timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Step 0. Pandas vs Polars 로딩 비교",
        "",
        "| 엔진 | 행 수 | 열 수 | 로딩 시간(초) | 메모리(MB) |",
        "|---|---|---|---|---|",
        (
            f"| pandas | {engine_stats['pandas'].n_rows} | {engine_stats['pandas'].n_cols} | "
            f"{engine_stats['pandas'].elapsed_sec:.3f} | {engine_stats['pandas'].memory_mb:.1f} |"
        ),
        (
            f"| polars | {engine_stats['polars'].n_rows} | {engine_stats['polars'].n_cols} | "
            f"{engine_stats['polars'].elapsed_sec:.3f} | {engine_stats['polars'].memory_mb:.1f} |"
        ),
        "",
        "## Polars 활용 범위",
        "",
        (
            "로딩 성능 비교뿐 아니라, Step 1(원본 결측률 집계)과 Step 5(급여 정제·범주형 그룹 비교)를 "
            "Polars Lazy API로 이중 수행하고 Pandas 결과와 대조했다."
        ),
        (
            f"- Step 1 결측률 집계: Polars {polars_eda['step1_elapsed_sec']:.3f}초"
        ),
        (
            f"- Step 5 정제+그룹비교: Polars {polars_eda['step5_elapsed_sec']:.3f}초, "
            f"정제 후 {polars_eda['n_final']}행 "
            f"(Pandas와 행 수 {'일치' if polars_eda['rows_match'] else '불일치'}, "
            f"RemoteWork 그룹 중앙값 {'일치' if polars_eda['medians_match'] else '불일치'})"
        ),
        "",
        "## Step 2. 정제 결과",
        "",
        (
            f"- 원본 {prep_stats['n_start']}행 → 급여 결측 제거 {prep_stats['n_after_dropna_target']}행 "
            f"→ 중복 제거 {prep_stats['n_after_dedup']}행 → IQR 이상치 제거 후 최종 **{prep_stats['n_final']}행**"
        ),
        f"- IQR 경계: [{prep_stats['lower_bound']:,.0f}, {prep_stats['upper_bound']:,.0f}]",
        "",
        "## Step 4. 급여와 수치형 변수 상관관계",
        "",
        "| 변수 | 상관계수 |",
        "|---|---|",
        *[f"| {col} | {value:.4f} |" for col, value in correlations.items()],
        "",
        f"급여와 가장 강한 상관을 보인 변수는 **{top_corr_col}**(r={top_corr_val:.4f})이다.",
        "",
        "## Step 6. 모델용 피처 선택 (다중공선성 제거)",
        "",
        (
            "`YearsCode`·`YearsCodePro`·`WorkExp`는 서로 상관계수 0.87~0.92, "
            "VIF(분산팽창지수) 6.2~10.6으로 다중공선성이 심각했다. 급여와의 상관이 가장 높고 "
            "(r=0.408) VIF가 가장 낮은(6.97) `WorkExp`만 남기고 `YearsCode`/`YearsCodePro`는 "
            "모델 피처에서 제외했다."
        ),
        "",
        "## Step 8. t-test (Remote vs In-person 급여 비교)",
        "",
        f"- {ttest['group_a']} 평균: {ttest['mean_a']:,.0f} (n={ttest['n_a']})",
        f"- {ttest['group_b']} 평균: {ttest['mean_b']:,.0f} (n={ttest['n_b']})",
        f"- t-통계량: {ttest['t_stat']:.4f}, p-value: {ttest['p_value']:.6g}",
        f"- 해석: {ttest['interpretation']}",
        "",
        "## Step 9. ML Pipeline 결과",
        "",
        f"- 회귀(급여 예측): R²={regression['r2']:.4f}, MAE={regression['mae']:,.0f}",
        (
            f"- 분류(고액 급여 여부, 임계값={classification['median_threshold']:,.0f}): "
            f"Accuracy={classification['accuracy']:.4f}, F1-score={classification['f1']:.4f}"
        ),
        f"- 모델 저장 경로: `{regression['model_path']}`, `{classification['model_path']}`",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[main] report.md 생성 완료: {report_path}")


def main() -> None:
    """Step 0~10을 순서대로 실행한다."""
    csv_path = ensure_dataset(RAW_CSV_PATH)

    # Step 0: Pandas vs Polars 로딩 성능 비교
    pandas_df, polars_df, engine_stats = compare_engines(csv_path)

    # Step 1: 원본 데이터 EDA (Pandas 상세 EDA + Polars 결측률 이중 집계)
    run_raw_eda(pandas_df, LOG_DIR / "step1_raw_eda.txt")
    polars_missing_start = time.perf_counter()
    run_raw_missing_rate_polars(polars_df, LOG_DIR / "step1_raw_eda_polars.txt")
    step1_polars_elapsed = time.perf_counter() - polars_missing_start

    # Step 2: 결측치·중복·급여 이상치 처리
    clean_df, prep_stats = run_preprocessing(pandas_df, LOG_DIR / "step2_preprocessing.txt")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    clean_df.to_parquet(PROCESSED_DIR / "cleaned_survey.parquet", index=False)

    # Step 3: 정제 데이터 EDA 및 기술통계
    run_clean_eda(clean_df, LOG_DIR / "step3_clean_eda.txt")

    # Step 4: 급여와 수치형 변수의 상관관계 분석
    correlations = run_correlation_analysis(clean_df, LOG_DIR / "step4_correlation.txt")

    # Step 5: 범주형 변수별 급여 중앙값·분포 비교 (Pandas + Polars 이중 수행 및 교차검증)
    run_categorical_group_comparison(clean_df, LOG_DIR / "step5_categorical_groups.txt")
    pandas_remote_medians = clean_df.groupby("RemoteWork")[TARGET_COL].median().to_dict()
    polars_group_result = run_salary_group_comparison_polars(
        polars_df,
        prep_stats["lower_bound"],
        prep_stats["upper_bound"],
        pandas_remote_medians,
        prep_stats["n_final"],
        LOG_DIR / "step5_categorical_groups_polars.txt",
    )

    # Step 6: 모델용 컬럼 선택
    model_df = select_model_columns(clean_df, LOG_DIR / "step6_feature_selection.txt")

    # Step 7: Seaborn·Plotly 시각화
    create_seaborn_charts(model_df, CHARTS_DIR / "eda_2x2_subplots.png")
    create_plotly_chart(model_df, HTML_DIR / "salary_by_country.html")

    # Step 8: t-test 및 p-value 해석
    ttest = run_remote_work_ttest(model_df, LOG_DIR / "step8_ttest.txt")

    # Step 9: Pipeline 모델 학습·평가·저장
    model_results = run_model_pipelines(model_df, MODELS_DIR, LOG_DIR / "step9_ml_pipeline.txt")
    for result in model_results.values():
        result["model_path"] = str(Path(result["model_path"]).relative_to(PROJECT_ROOT))

    # Step 10: report.md 자동 생성
    generate_report(
        {
            "engine_stats": engine_stats,
            "prep_stats": prep_stats,
            "correlations": correlations,
            "ttest": ttest,
            "regression": model_results["regression"],
            "classification": model_results["classification"],
            "polars_eda": {
                "step1_elapsed_sec": step1_polars_elapsed,
                "step5_elapsed_sec": polars_group_result["elapsed_sec"],
                "n_final": polars_group_result["n_final"],
                "rows_match": polars_group_result["rows_match"],
                "medians_match": polars_group_result["medians_match"],
            },
        },
        REPORT_PATH,
    )


if __name__ == "__main__":
    main()
