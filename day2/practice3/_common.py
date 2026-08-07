"""step2~5 파이프라인이 공유하는 파일 로딩 예외처리 유틸리티."""

from pathlib import Path


def ensure_csv_exists(csv_path: Path) -> None:
    """CSV 파일이 실제로 존재하는지 확인한다.

    각 라이브러리(pandas/polars/duckdb)가 파일 부재 시 서로 다른 형태의
    예외를 던지기 전에, 먼저 명확한 메시지로 실패시켜 원인을 바로 알 수 있게 한다.

    Args:
        csv_path: 확인할 CSV 파일 경로.

    Raises:
        FileNotFoundError: 경로에 파일이 존재하지 않을 경우.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {csv_path}")
