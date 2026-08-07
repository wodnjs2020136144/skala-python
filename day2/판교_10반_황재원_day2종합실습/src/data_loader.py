"""데이터 다운로드/캐시 및 Pandas·Polars 로딩 성능 비교.

Stack Overflow Developer Survey 2024 원본 CSV(약 152MB, 114개 컬럼)를 대상으로
Step 0(데이터 준비 및 엔진 성능 비교)을 수행한다.
"""

import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import polars as pl
import requests

# GitHub는 원 URL(.../raw/refs/heads/main/...) 접근 시 302로 Git LFS 미디어 서버로
# 리다이렉트한다. requests는 기본적으로 리다이렉트를 따라가므로 원 URL을 그대로 사용한다.
RESULTS_URL = (
    "https://github.com/StackExchange/Survey/raw/refs/heads/main/"
    "packages/archive/2024/results.csv"
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_CSV_PATH = PROJECT_ROOT / "data" / "raw" / "results.csv"


@dataclass
class EngineLoadResult:
    """단일 엔진(Pandas 또는 Polars)의 로딩 성능 측정 결과.

    Attributes:
        engine: 엔진 이름 ("pandas" 또는 "polars").
        n_rows: 로딩된 행 수.
        n_cols: 로딩된 열 수.
        elapsed_sec: 로딩에 걸린 시간(초).
        memory_mb: 로딩된 데이터가 차지하는 메모리(MB).
    """

    engine: str
    n_rows: int
    n_cols: int
    elapsed_sec: float
    memory_mb: float


def ensure_dataset(csv_path: Path = RAW_CSV_PATH, url: str = RESULTS_URL) -> Path:
    """원본 CSV가 로컬에 없으면 다운로드하고, 있으면 캐시를 재사용한다.

    Args:
        csv_path: 원본 CSV를 저장할 경로.
        url: 다운로드할 원본 데이터 URL.

    Returns:
        원본 CSV 파일 경로.

    Raises:
        requests.HTTPError: 다운로드 요청이 실패할 경우.
    """
    if csv_path.exists():
        print(f"[data_loader] 캐시된 원본 CSV 사용: {csv_path}")
        return csv_path

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[data_loader] 원본 CSV 다운로드 중: {url}")
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        tmp_path = csv_path.with_suffix(".csv.part")
        with open(tmp_path, "wb") as f:
            f.writelines(response.iter_content(chunk_size=1024 * 1024))
        tmp_path.rename(csv_path)
    size_mb = csv_path.stat().st_size / (1024 * 1024)
    print(f"[data_loader] 다운로드 완료: {csv_path} ({size_mb:.1f} MB)")
    return csv_path


def load_with_pandas(csv_path: Path) -> tuple[pd.DataFrame, EngineLoadResult]:
    """Pandas 2.x로 CSV를 로딩하고 시간·메모리를 측정한다.

    Args:
        csv_path: 로딩할 CSV 파일 경로.

    Returns:
        (로딩된 DataFrame, 측정 결과) 튜플.
    """
    start = time.perf_counter()
    df = pd.read_csv(csv_path, low_memory=False)
    elapsed = time.perf_counter() - start
    memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
    result = EngineLoadResult(
        engine="pandas",
        n_rows=len(df),
        n_cols=df.shape[1],
        elapsed_sec=elapsed,
        memory_mb=memory_mb,
    )
    return df, result


def load_with_polars(csv_path: Path) -> tuple[pl.DataFrame, EngineLoadResult]:
    """Polars로 CSV를 로딩하고 시간·메모리를 측정한다.

    Args:
        csv_path: 로딩할 CSV 파일 경로.

    Returns:
        (로딩된 DataFrame, 측정 결과) 튜플.
    """
    start = time.perf_counter()
    # 원본 CSV에 결측을 나타내는 리터럴 문자열 "NA"가 포함돼 있다. Pandas read_csv는
    # 기본 na_values에 "NA"가 포함돼 있어 자동으로 NaN 처리하지만, Polars read_csv는
    # 기본적으로 이를 결측으로 인식하지 않으므로 null_values로 명시해 두 엔진의
    # 결측 판정 기준을 일치시킨다.
    df = pl.read_csv(csv_path, infer_schema_length=None, ignore_errors=True, null_values=["NA"])
    elapsed = time.perf_counter() - start
    memory_mb = df.estimated_size() / (1024 * 1024)
    result = EngineLoadResult(
        engine="polars",
        n_rows=df.height,
        n_cols=df.width,
        elapsed_sec=elapsed,
        memory_mb=memory_mb,
    )
    return df, result


def compare_engines(
    csv_path: Path = RAW_CSV_PATH,
) -> tuple[pd.DataFrame, pl.DataFrame, dict[str, EngineLoadResult]]:
    """Pandas·Polars 양쪽으로 로딩 후 행·열 수와 성능을 비교 출력한다.

    Args:
        csv_path: 로딩할 CSV 파일 경로.

    Returns:
        (Pandas DataFrame, Polars DataFrame, 엔진별 측정 결과 딕셔너리) 튜플.
        DataFrame들은 이후 EDA 단계에서 재사용한다.

    Raises:
        AssertionError: 두 엔진의 행·열 수가 일치하지 않을 경우.
    """
    pandas_df, pandas_result = load_with_pandas(csv_path)
    polars_df, polars_result = load_with_polars(csv_path)

    print("\n=== Step 0: Pandas vs Polars 로딩 비교 ===")
    print(f"{'엔진':<10}{'행 수':>10}{'열 수':>8}{'로딩 시간(초)':>16}{'메모리(MB)':>14}")
    for result in (pandas_result, polars_result):
        print(
            f"{result.engine:<10}{result.n_rows:>10}{result.n_cols:>8}"
            f"{result.elapsed_sec:>16.3f}{result.memory_mb:>14.1f}"
        )

    assert pandas_result.n_rows == polars_result.n_rows, "두 엔진의 행 수가 다릅니다."
    assert pandas_result.n_cols == polars_result.n_cols, "두 엔진의 열 수가 다릅니다."
    print("[data_loader] 행·열 수 일치 확인 완료.")

    return pandas_df, polars_df, {"pandas": pandas_result, "polars": polars_result}
