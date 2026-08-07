"""t-test 및 p-value 해석.

Step 8(t-test 및 p-value 해석)을 구현한다.
"""

from pathlib import Path

import pandas as pd
from scipy import stats

from src.eda import TARGET_COL, Tee

ALPHA = 0.05
GROUP_A = "Remote"
GROUP_B = "In-person"


def run_remote_work_ttest(df: pd.DataFrame, log_path: Path) -> dict[str, float]:
    """원격근무(Remote) vs 사무실 근무(In-person) 간 급여 평균 차이를 t-검정한다.

    Args:
        df: 정제·피처 선택이 끝난 DataFrame(RemoteWork, ConvertedCompYearly 포함).
        log_path: 실행 결과를 기록할 로그 파일 경로.

    Returns:
        t-통계량, p-value, 두 그룹 평균·표본 수를 담은 딕셔너리.
    """
    out = Tee(log_path)
    out("=== Step 8: t-test (Remote vs In-person 급여 비교) ===")

    group_a = df.loc[df["RemoteWork"] == GROUP_A, TARGET_COL].dropna()
    group_b = df.loc[df["RemoteWork"] == GROUP_B, TARGET_COL].dropna()

    t_stat, p_value = stats.ttest_ind(group_a, group_b, equal_var=False)

    out(f"\n[{GROUP_A}] n={len(group_a)}, 평균={group_a.mean():,.0f}")
    out(f"[{GROUP_B}] n={len(group_b)}, 평균={group_b.mean():,.0f}")
    out(f"\nt-통계량={t_stat:.4f}, p-value={p_value:.6g}")

    is_significant = p_value < ALPHA
    if is_significant:
        interpretation = (
            f"p-value({p_value:.6g}) < {ALPHA} → 귀무가설(두 그룹의 급여 평균이 같다) 기각. "
            f"{GROUP_A} 근무자와 {GROUP_B} 근무자의 평균 급여 차이는 통계적으로 유의하다."
        )
    else:
        interpretation = (
            f"p-value({p_value:.6g}) >= {ALPHA} → 귀무가설을 기각할 수 없다. "
            f"두 그룹의 평균 급여 차이가 통계적으로 유의하다고 보기 어렵다."
        )
    out(f"\n[해석] {interpretation}")

    out.flush()
    print(f"\n[statistics] Step 8 로그 저장: {log_path}")

    return {
        "group_a": GROUP_A,
        "group_b": GROUP_B,
        "n_a": len(group_a),
        "n_b": len(group_b),
        "mean_a": float(group_a.mean()),
        "mean_b": float(group_b.mean()),
        "t_stat": float(t_stat),
        "p_value": float(p_value),
        "is_significant": is_significant,
        "interpretation": interpretation,
    }
