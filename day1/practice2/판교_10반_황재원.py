# Day1 Practice 2: 파일 I/O · 예외 처리 · Pydantic 검증 파이프라인.
# 작성자: P345 황재원
# 작업환경: Python 3.11.6, macOS, VSCode
# 작성일: 2026-08-06
# Python_Practice2_Data.json의 매출 데이터를 안전하게 로딩하고, Pydantic v2 스키마로 검증한 뒤
# 정상 데이터와 결함 데이터를 분류하여 각각 CSV/JSON으로 저장한다.

import csv
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("Practice2_Pipeline")

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = Path(__file__).resolve().parents[2] / "Python_Practice2_Data.json"
VALID_CSV_PATH = BASE_DIR / "valid_sales_output.csv"
ERRORS_JSON_PATH = BASE_DIR / "error_sales_output.json"
DEMO_ERRORS_JSON_PATH = BASE_DIR / "error_demo_output.json"


class SalesRecord(BaseModel):
    """매출 레코드 한 건을 검증하기 위한 스키마."""

    month: str = Field(..., min_length=1, description="월 정보 (필수)")
    region: str = Field(..., min_length=1, description="지역 정보 (필수)")
    amount: float = Field(..., gt=0, description="매출액 (0 초과 필수)")
    category: str | None = Field(default=None, description="카테고리 (선택)")


def safe_load_csv(filepath: Path) -> list[dict[str, Any]] | None:
    """파일을 읽어 dict 리스트로 반환하는 안전한 로더.

    확장자가 .json이면 JSON으로, 그 외(.csv)에는 CSV로 파싱한다.
    파일이 없으면 None을 반환하고, finally 블록에서 항상 종료 로그를 남긴다.
    """
    data: list[dict[str, Any]] = []
    try:
        with open(filepath, mode="r", encoding="utf-8") as f:
            if filepath.suffix == ".json":
                data = json.load(f)
            else:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("amount"):
                        row["amount"] = float(row["amount"])
                    data.append(row)
        logger.info(f"성공적으로 파일 데이터를 로드했습니다: {filepath} ({len(data)}건)")
        return data
    except FileNotFoundError:
        logger.error(f"지정된 파일을 찾을 수 없습니다: {filepath}")
        return None
    except Exception as e:  # noqa: BLE001 — 알 수 없는 오류 안전하게 처리
        logger.error(f"파일 로딩 중 알 수 없는 오류 발생: {e}")
        return None
    finally:
        logger.info("자원 정리: 파일 로딩 프로세스 종료")


def run_validation_pipeline(
    raw_data: list[dict[str, Any]],
) -> tuple[list[SalesRecord], list[dict[str, Any]]]:
    """raw_data를 검증해 정상(valid)/결함(errors) 레코드로 분리한다."""
    valid_records: list[SalesRecord] = []
    error_records: list[dict[str, Any]] = []

    for row in raw_data:
        try:
            record = SalesRecord.model_validate(row)
            valid_records.append(record)
        except ValidationError as ve:
            logger.warning(
                f"데이터 검증 실패: {row.get('month')} | 사유: {ve.errors()[0]['msg']}")
            error_records.append({"row": row, "error": ve.errors()})

    return valid_records, error_records


# 원본 데이터에서 이 인덱스들만 규칙 위반으로 바꿔서 errors 분기 동작을 증명한다.
CORRUPTIONS = {
    0: {"month": ""},
    1: {"region": ""},
    2: {"amount": -950},
    3: {"amount": 0},
}


def demonstrate_error_handling(raw_data: list[dict[str, Any]]) -> None:
    """원본 데이터 일부를 규칙 위반으로 오염시켜 errors 분기가 실제로 동작하는지 보여준다.

    Python_Practice2_Data.json은 100건 전부 정상이라 ValidationError를 잡는 except
    분기가 한 번도 실행되지 않는다. 원본을 그대로 두고 복사본만 오염시켜 검증한다.
    """
    corrupted = [dict(row) for row in raw_data]
    for index, overrides in CORRUPTIONS.items():
        corrupted[index].update(overrides)

    valid, errors = run_validation_pipeline(corrupted)
    print(f"\n[오류 처리 데모] Valid: {len(valid)}건 | Errors: {len(errors)}건")
    expected_valid = len(raw_data) - len(CORRUPTIONS)
    assert len(valid) == expected_valid, (
        f"Valid 건수는 {expected_valid}건이어야 합니다. (현재: {len(valid)})"
    )
    assert len(errors) == len(CORRUPTIONS), (
        f"Errors 건수는 {len(CORRUPTIONS)}건이어야 합니다. (현재: {len(errors)})"
    )
    for err in errors:
        print(f"  - 위반 데이터: {err['row']} | 사유: {err['error'][0]['msg']}")

    with open(DEMO_ERRORS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(errors, f, ensure_ascii=False, indent=2)
    print(f"  → 데모 오류 {len(errors)}건을 {DEMO_ERRORS_JSON_PATH.name}에 저장했습니다.")


def main() -> None:
    # 1) 존재하지 않는 파일 테스트
    assert safe_load_csv(BASE_DIR / "non_existent_file.json") is None, (
        "파일 미존재 시 None이 반환되어야 합니다."
    )

    # 2) 실제 데이터 로드 (Python_Practice2_Data.json)
    raw_data = safe_load_csv(DATA_PATH)
    assert raw_data is not None and len(raw_data) == 100

    # 3) 검증 파이프라인 실행
    valid, errors = run_validation_pipeline(raw_data)
    print(f"\n[검증 결과] Valid: {len(valid)}건 | Errors: {len(errors)}건")
    assert len(valid) == 100, f"Valid 건수는 100건이어야 합니다. (현재: {len(valid)})"
    assert len(errors) == 0, f"Errors 건수는 0건이어야 합니다. (현재: {len(errors)})"

    # 3-1) 오류 처리 데모 (원본 raw_data는 그대로, 복사본만 오염시켜 검증)
    demonstrate_error_handling(raw_data)

    # 4) 저장 (Valid -> CSV, Errors -> JSON)
    with open(VALID_CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["month", "region", "amount", "category"])
        writer.writeheader()
        for rec in valid:
            writer.writerow(rec.model_dump())

    with open(ERRORS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(errors, f, ensure_ascii=False, indent=2)

    # 5) 재로딩 검증
    reloaded_valid = safe_load_csv(VALID_CSV_PATH)
    assert reloaded_valid is not None and len(reloaded_valid) == len(valid), (
        f"재로딩된 건수가 {len(valid)}건이어야 합니다."
    )
    print("검증 완료")


if __name__ == "__main__":
    main()
