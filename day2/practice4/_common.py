"""step2~5 파이프라인이 공유하는 공통 유틸리티.

파일 로딩 예외처리, practice3 정제 파이프라인 재사용, 산출물 디렉토리 준비를 담당한다.
"""

import sys
from pathlib import Path

import pandas as pd

CSV_PATH = Path(__file__).resolve().parents[2] / "sales_100k.csv"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
PRACTICE3_DIR = Path(__file__).resolve().parents[1] / "practice3"


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


def load_cleaned_sales(csv_path: Path = CSV_PATH, verbose: bool = False) -> pd.DataFrame:
    """practice3의 Pandas 파이프라인을 재사용해 결측·IQR 이상치가 정제된 DataFrame을 얻는다.

    day2/practice3/step3_pandas_pipeline.py의 run_pipeline()을 그대로 호출해
    "실습3 산출물(IQR 정제 DataFrame)을 실습4가 입력으로 사용"하는 연계 구조를 만족한다.
    두 실습 폴더 간 로직 중복을 피하기 위해 결측 제거/IQR 계산 코드를 이 파일에 다시
    작성하지 않고 practice3 모듈을 직접 import한다.

    Args:
        csv_path: 원본 CSV 파일 경로.
        verbose: True면 practice3 파이프라인의 단계별 통계를 출력한다.

    Returns:
        결측 제거 및 IQR 이상치 제거가 끝난 행 단위 DataFrame.

    Raises:
        FileNotFoundError: csv_path에 파일이 없을 경우 (practice3 파이프라인에서 발생).
        ValueError: CSV 내용을 읽을 수 없을 경우 (practice3 파이프라인에서 발생).
    """
    if str(PRACTICE3_DIR) not in sys.path:
        sys.path.insert(0, str(PRACTICE3_DIR))
    from step3_pandas_pipeline import load_and_clean, remove_outliers_iqr

    df, _clean_stats = load_and_clean(csv_path, verbose=verbose)
    df, _outlier_stats = remove_outliers_iqr(df, verbose=verbose)
    return df
