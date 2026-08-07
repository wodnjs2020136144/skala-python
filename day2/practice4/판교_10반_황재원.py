# Day2 Practice4: 시각화 4종 / 통계 검정 / sklearn Pipeline / Plotly 인터랙티브 차트.
# 작성자: P345 황재원
# 작업환경: Python 3.11.6, macOS, VSCode
# 작성일: 2026-08-07
# 설명: sales_100k.csv 매출 데이터를 결측 제거 + IQR 이상치 제거로 정제한 뒤, 2x2 서브플롯
#       EDA 시각화(히스토그램/박스플롯/월별추이/상관관계 히트맵), t-test·카이제곱 통계 검정,
#       ColumnTransformer+RandomForestClassifier Pipeline 학습/저장, Plotly 인터랙티브 차트
#       생성까지 수행한다. Day2 Practice3의 결측 제거+IQR 로직과 동일한 기준을 이 파일 안에
#       독립적으로 구현해, 다른 디렉토리에 의존하지 않고 단독 실행 가능하도록 했다.
# 변경내역:
#   - 2026-08-07: 최초 작성 (Step2~5 통합 — EDA 시각화, 통계 검정, sklearn Pipeline, Plotly 차트)
#   - 2026-08-07: 함수 타입힌트 정리 (matplotlib.axes.Axes, plotly.graph_objects.Figure)
#   - 2026-08-07: sns.histplot 인자 형식 수정 (data=df, x="amount")

from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
from matplotlib.axes import Axes
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

CSV_PATH = Path(__file__).resolve().parents[2] / "sales_100k.csv"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
REQUIRED_COLS = ["region", "category", "amount"]
NUMERIC_CORR_COLS = ["amount", "quantity", "unit_price", "customer_age"]
NUMERIC_FEATURES = ["quantity", "unit_price", "customer_age"]
CATEGORICAL_FEATURES = ["region", "category", "payment_method"]
SIGNIFICANCE_LEVEL = 0.05


# ---------------------------------------------------------------------------
# 공통 유틸리티
# ---------------------------------------------------------------------------
def ensure_csv_exists(csv_path: Path) -> None:
    """CSV 파일이 실제로 존재하는지 확인한다.

    Args:
        csv_path: 확인할 CSV 파일 경로.

    Raises:
        FileNotFoundError: 경로에 파일이 존재하지 않을 경우.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {csv_path}")


def ensure_output_dir() -> Path:
    """산출물 저장 디렉토리(outputs/)가 없으면 생성한다.

    Returns:
        생성 또는 기존에 존재하는 outputs 디렉토리 경로.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def load_raw_sales(csv_path: Path) -> pd.DataFrame:
    """원본 CSV를 가공 없이 그대로 읽어들인다.

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


def get_cleaned_sales(csv_path: Path, verbose: bool = False) -> pd.DataFrame:
    """결측 제거 + IQR 이상치 제거를 거친 정제 DataFrame을 만든다.

    Day2 Practice3의 결측 제거(region/category/amount 결측 행 제거) + IQR
    이상치 제거(Q1-1.5*IQR ~ Q3+1.5*IQR) 로직과 동일한 기준을 적용한다.
    이 실습(Practice4)의 시각화·통계 검정 입력 데이터로 사용한다.

    Args:
        csv_path: 원본 CSV 파일 경로.
        verbose: True면 결측/이상치 제거 통계를 출력한다.

    Returns:
        결측 제거 및 IQR 이상치 제거가 끝난 행 단위 DataFrame.
    """
    df = load_raw_sales(csv_path)
    before = len(df)
    missing_counts = {col: int(df[col].isnull().sum()) for col in REQUIRED_COLS}
    df = df.dropna(subset=REQUIRED_COLS)
    after_clean = len(df)

    q1 = df["amount"].quantile(0.25)
    q3 = df["amount"].quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    df = df[(df["amount"] >= lower) & (df["amount"] <= upper)]
    after_outlier = len(df)

    if verbose:
        print(f"[결측 제거] {before}행 -> {after_clean}행 (제거 {before - after_clean}행)")
        for col, cnt in missing_counts.items():
            print(f"  - {col}: {cnt}건 결측")
        print(f"[IQR 이상치 제거] Q1={q1:.1f}, Q3={q3:.1f}, IQR={iqr:.1f}, "
              f"허용범위=[{lower:.1f}, {upper:.1f}]")
        print(f"  {after_clean}행 -> {after_outlier}행 (제거 {after_clean - after_outlier}행)")
    return df


# ---------------------------------------------------------------------------
# Step2: EDA 시각화 4종 (2x2 서브플롯)
# ---------------------------------------------------------------------------
def build_amount_histogram(ax: Axes, df: pd.DataFrame) -> None:
    """매출액(amount) 분포를 히스토그램 + KDE로 그린다.

    Args:
        ax: 그릴 대상 Axes.
        df: amount 컬럼을 포함한 DataFrame.
    """
    sns.histplot(data=df, x="amount", kde=True, ax=ax, color="skyblue")
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


# ---------------------------------------------------------------------------
# Step3: 통계 검정 (t-test + 카이제곱)
# ---------------------------------------------------------------------------
def run_region_ttest(df: pd.DataFrame, region_a: str, region_b: str) -> dict:
    """두 지역 간 매출액(amount) 평균 차이를 독립표본 t-test로 검정한다.

    Args:
        df: region/amount 컬럼을 포함한 정제 DataFrame.
        region_a: 비교할 첫 번째 지역명.
        region_b: 비교할 두 번째 지역명.

    Returns:
        t_stat, p_value, region_a/b의 표본 수와 평균을 담은 딕셔너리.

    Raises:
        ValueError: 두 지역 중 하나라도 표본이 없을 경우.
    """
    sample_a = df.loc[df["region"] == region_a, "amount"]
    sample_b = df.loc[df["region"] == region_b, "amount"]

    if sample_a.empty or sample_b.empty:
        raise ValueError(
            f"t-test를 수행할 표본이 없습니다: {region_a}={len(sample_a)}건, "
            f"{region_b}={len(sample_b)}건"
        )

    t_stat, p_value = stats.ttest_ind(sample_a, sample_b)
    return {
        "region_a": region_a, "region_b": region_b,
        "n_a": len(sample_a), "n_b": len(sample_b),
        "mean_a": sample_a.mean(), "mean_b": sample_b.mean(),
        "t_stat": t_stat, "p_value": p_value,
    }


def run_region_category_chi2(df: pd.DataFrame) -> dict:
    """region x category 분할표로 두 범주형 변수의 독립성을 카이제곱 검정한다.

    Args:
        df: region/category 컬럼을 포함한 정제 DataFrame.

    Returns:
        chi2, p_value, 자유도(dof), 분할표(contingency_table)를 담은 딕셔너리.
    """
    contingency_table = pd.crosstab(df["region"], df["category"])
    chi2, p_value, dof, _expected = stats.chi2_contingency(contingency_table)
    return {"chi2": chi2, "p_value": p_value, "dof": dof, "contingency_table": contingency_table}


def interpret_p_value(p_value: float, alternative_desc: str, null_desc: str) -> str:
    """p-value를 유의수준과 비교해 사람이 읽을 수 있는 해석 문장을 만든다.

    Args:
        p_value: 검정에서 산출된 p-value.
        alternative_desc: p < 유의수준일 때(귀무가설 기각) 보여줄 해석 문구.
        null_desc: p >= 유의수준일 때(귀무가설 채택) 보여줄 해석 문구.

    Returns:
        해석 문장 (유의수준 값 포함).
    """
    if p_value < SIGNIFICANCE_LEVEL:
        return f"p < {SIGNIFICANCE_LEVEL}이므로 {alternative_desc}"
    return f"p >= {SIGNIFICANCE_LEVEL}이므로 {null_desc}"


# ---------------------------------------------------------------------------
# Step4: sklearn Pipeline 구축·저장
# ---------------------------------------------------------------------------
def prepare_ml_data(csv_path: Path, verbose: bool = False) -> tuple[pd.DataFrame, pd.Series, dict]:
    """원본 CSV에서 결측 필수 컬럼 행만 제거하고 피처/타깃을 분리한다.

    IQR 이상치는 제거하지 않는다(Pipeline 학습 데이터는 sales_100k.csv 원본을
    그대로 사용). amount 평균을 기준으로 고액 주문 여부(high_value_order)를
    타깃으로 만들고, amount 자체는 데이터 누수를 피하기 위해 피처에서 제외한다.

    Args:
        csv_path: 원본 CSV 파일 경로.
        verbose: True면 결측 제거 통계와 타깃 분포를 출력한다.

    Returns:
        (피처 DataFrame, 타깃 Series, 통계 딕셔너리) 튜플.
    """
    df = load_raw_sales(csv_path)
    before = len(df)
    df = df.dropna(subset=REQUIRED_COLS)
    after = len(df)

    threshold = df["amount"].mean()
    y = (df["amount"] > threshold).astype(int).rename("high_value_order")
    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]

    stats_dict = {
        "before": before, "after": after, "dropped": before - after,
        "threshold": threshold, "positive_ratio": y.mean(),
    }
    if verbose:
        print(f"[결측 제거] {before}행 -> {after}행 (제거 {stats_dict['dropped']}행)")
        print(f"[타깃 정의] amount > {threshold:.1f} (평균) -> high_value_order")
        print(f"[타깃 분포] 양성(1) 비율={stats_dict['positive_ratio']:.3f}")
    return X, y, stats_dict


def build_ml_pipeline() -> Pipeline:
    """수치 스케일링 + 범주 원핫인코딩 전처리와 분류 모델을 하나의 Pipeline으로 구성한다.

    max_depth/min_samples_leaf를 제한하지 않으면 약 78만 건 학습 데이터에서
    트리가 과도하게 깊어져 저장 파일이 수백 MB로 커진다(실측 약 500MB, 정확도
    개선은 거의 없음). 트리 깊이를 제한해 모델 크기를 실용적인 수준으로 낮췄다.

    Returns:
        preprocessor와 classifier 두 단계로 이뤄진 학습 전 Pipeline 객체.
    """
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )
    return Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", RandomForestClassifier(
            n_estimators=100, max_depth=15, min_samples_leaf=50,
            random_state=42, n_jobs=-1,
        )),
    ])


def train_and_evaluate_ml_pipeline(
    X: pd.DataFrame, y: pd.Series, verbose: bool = False
) -> tuple[Pipeline, dict]:
    """train/test로 분할해 Pipeline을 학습시키고 테스트 세트로 평가한다.

    Args:
        X: 피처 DataFrame.
        y: 타깃 Series.
        verbose: True면 정확도와 분류 리포트를 출력한다.

    Returns:
        학습이 끝난 Pipeline과 (accuracy, classification_report 문자열) 통계 딕셔너리.
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = build_ml_pipeline()
    pipeline.fit(X_train, y_train)

    accuracy = pipeline.score(X_test, y_test)
    y_pred = pipeline.predict(X_test)
    report = classification_report(y_test, y_pred)

    stats_dict = {"accuracy": accuracy, "report": report, "n_train": len(X_train), "n_test": len(X_test)}
    if verbose:
        print(f"\n[학습/평가] train={stats_dict['n_train']}건, test={stats_dict['n_test']}건")
        print(f"[정확도] {accuracy:.4f}")
        print("[분류 리포트]")
        print(report)
    return pipeline, stats_dict


def save_ml_model(pipeline: Pipeline, output_path: Path) -> Path:
    """학습된 Pipeline을 joblib 파일로 저장한다.

    Args:
        pipeline: 저장할 학습된 Pipeline.
        output_path: 저장할 .joblib 파일 경로.

    Returns:
        저장된 파일 경로.

    Raises:
        OSError: 저장 디렉토리에 쓰기 권한이 없는 등 파일 저장에 실패할 경우.
    """
    try:
        joblib.dump(pipeline, output_path)
    except OSError as e:
        raise OSError(f"모델 파일을 저장할 수 없습니다: {output_path}") from e
    return output_path


# ---------------------------------------------------------------------------
# Step5: Plotly 인터랙티브 차트
# ---------------------------------------------------------------------------
def agg_region_category(df: pd.DataFrame) -> pd.DataFrame:
    """region x category 기준으로 매출을 집계한다.

    Args:
        df: 집계 대상 DataFrame.

    Returns:
        total_amount(합계), avg_amount(평균), item_count(건수)를 담은
        DataFrame. total_amount 내림차순으로 정렬된다.
    """
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


def build_region_category_chart(agg_df: pd.DataFrame) -> go.Figure:
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


def save_chart_html(fig: go.Figure, output_path: Path) -> Path:
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


# ---------------------------------------------------------------------------
# 전체 실행
# ---------------------------------------------------------------------------
def main() -> None:
    """Step2(시각화) -> Step3(통계 검정) -> Step4(Pipeline) -> Step5(Plotly) 순으로 실행한다."""
    output_dir = ensure_output_dir()

    print("=" * 60)
    print("[Step2] EDA 시각화 4종 (2x2 서브플롯)")
    print("=" * 60)
    cleaned_df = get_cleaned_sales(CSV_PATH, verbose=True)
    print(f"\n[시각화 대상] {len(cleaned_df)}행 (결측 제거 + IQR 이상치 제거 완료)")
    eda_path = draw_eda_subplots(cleaned_df, output_dir / "eda_2x2_subplots.png")
    print(f"[저장 완료] {eda_path}")

    print("\n" + "=" * 60)
    print("[Step3] 통계 검정 (t-test + 카이제곱)")
    print("=" * 60)
    ttest_result = run_region_ttest(cleaned_df, "서울", "부산")
    print(f"  서울: n={ttest_result['n_a']}, 평균={ttest_result['mean_a']:.1f}")
    print(f"  부산: n={ttest_result['n_b']}, 평균={ttest_result['mean_b']:.1f}")
    print(f"  t-statistic={ttest_result['t_stat']:.4f}, p-value={ttest_result['p_value']:.4e}")
    print("  해석:", interpret_p_value(
        ttest_result["p_value"],
        "서울과 부산의 매출 평균 차이는 통계적으로 유의미합니다.",
        "서울과 부산의 매출 평균 차이는 통계적으로 유의미하지 않습니다.",
    ))

    chi2_result = run_region_category_chi2(cleaned_df)
    print(f"\n  분할표 크기: {chi2_result['contingency_table'].shape}")
    print(f"  chi2={chi2_result['chi2']:.4f}, dof={chi2_result['dof']}, "
          f"p-value={chi2_result['p_value']:.4e}")
    print("  해석:", interpret_p_value(
        chi2_result["p_value"],
        "지역과 카테고리는 서로 유의미한 연관성이 있습니다.",
        "지역과 카테고리는 통계적으로 독립적입니다.",
    ))

    print("\n" + "=" * 60)
    print("[Step4] sklearn Pipeline 구축·저장")
    print("=" * 60)
    X, y, _prep_stats = prepare_ml_data(CSV_PATH, verbose=True)
    pipeline, _eval_stats = train_and_evaluate_ml_pipeline(X, y, verbose=True)
    model_path = save_ml_model(pipeline, output_dir / "sales_pipeline_model.joblib")
    print(f"\n[저장 완료] {model_path}")

    print("\n" + "=" * 60)
    print("[Step5] Plotly 인터랙티브 차트")
    print("=" * 60)
    agg_df = agg_region_category(cleaned_df)
    print(f"[집계 결과] {len(agg_df)}개 region x category 조합")
    fig = build_region_category_chart(agg_df)
    chart_path = save_chart_html(fig, output_dir / "sales_interactive.html")
    print(f"[저장 완료] {chart_path}")


if __name__ == "__main__":
    main()
