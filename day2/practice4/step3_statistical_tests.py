"""IQR 정제 매출 데이터로 t-test와 카이제곱 독립성 검정을 수행한다.

서울-부산 두 지역의 매출 평균 차이(t-test)와, region x category 두 범주형
변수의 연관성(카이제곱 검정)을 확인하고 p-value 기준으로 유의성을 해석한다.
"""

import pandas as pd
from scipy import stats

from _common import load_cleaned_sales

SIGNIFICANCE_LEVEL = 0.05


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

    practice3의 region x category 집계 구조를 그대로 살려, 정제 데이터의
    빈도(건수) 기준 분할표(crosstab)를 구성해 검정에 사용한다.

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


def main() -> None:
    """정제 데이터를 로드해 t-test와 카이제곱 검정을 순서대로 수행하고 결과를 출력한다."""
    df = load_cleaned_sales(verbose=True)
    print(f"\n[검정 대상] {len(df)}행 (결측 제거 + IQR 이상치 제거 완료)")

    print("\n[t-test] 서울 vs 부산 매출액 평균 차이")
    ttest_result = run_region_ttest(df, "서울", "부산")
    print(f"  서울: n={ttest_result['n_a']}, 평균={ttest_result['mean_a']:.1f}")
    print(f"  부산: n={ttest_result['n_b']}, 평균={ttest_result['mean_b']:.1f}")
    print(f"  t-statistic={ttest_result['t_stat']:.4f}, p-value={ttest_result['p_value']:.4e}")
    print("  해석:", interpret_p_value(
        ttest_result["p_value"],
        "서울과 부산의 매출 평균 차이는 통계적으로 유의미합니다.",
        "서울과 부산의 매출 평균 차이는 통계적으로 유의미하지 않습니다.",
    ))

    print("\n[카이제곱 검정] region x category 독립성 검정")
    chi2_result = run_region_category_chi2(df)
    print(f"  분할표 크기: {chi2_result['contingency_table'].shape}")
    print(f"  chi2={chi2_result['chi2']:.4f}, dof={chi2_result['dof']}, "
          f"p-value={chi2_result['p_value']:.4e}")
    print("  해석:", interpret_p_value(
        chi2_result["p_value"],
        "지역과 카테고리는 서로 유의미한 연관성이 있습니다.",
        "지역과 카테고리는 통계적으로 독립적입니다.",
    ))


if __name__ == "__main__":
    main()
