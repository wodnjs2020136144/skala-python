# Day2 Practice3 — 트러블슈팅 기록

## Step5 — DuckDB SQL 파이프라인

**이슈**: 월별 집계 쿼리에서 `SUBSTR(order_date, 1, 7)`을 실행하자 다음 오류가 발생했다.

```
_duckdb.BinderException: Binder Error: No function matches the given name and
argument types 'substr(DATE, INTEGER_LITERAL, INTEGER_LITERAL)'.
```

DuckDB는 CSV를 스캔할 때 `order_date` 컬럼을 문자열이 아닌 `DATE` 타입으로 자동 추론하는 반면, Pandas/Polars는 동일 컬럼을 문자열로 읽어들여 엔진 간 타입 추론 방식에 차이가 있었다.

**해결**: `SUBSTR(CAST(order_date AS VARCHAR), 1, 7)`로 명시적 형변환을 추가해 세 엔진의 월별 집계 결과를 동일하게 맞췄다. 수정 후 Pandas 결과와 `total_amount` 합계 차이가 0.0000으로 확인되었다.

## 엔진 간 결과 일치 검증

Pandas / Polars / DuckDB 세 엔진의 `region x category` 집계 `total_amount` 합계를 비교한 결과:

| 비교 | 차이 |
|---|---|
| Pandas vs Polars | 0.0005 (부동소수점 합산 순서 차이) |
| Pandas vs DuckDB | 0.0000 |

부동소수점 합산 순서에 따른 미세한 오차를 제외하면 세 엔진의 결과가 완전히 일치함을 확인했다.

## Checkpoint 대조 코드 리뷰 후속 개선

코드 리뷰에서 실습 Checkpoint 배점표의 "오류/예외 처리" 및 "코드 간결성" 기준으로 점검한 결과 두 가지
개선점이 확인되어 반영했다.

**이슈1 — 파일 로딩 예외 미반영**: `step2`~`step5` 모두 CSV 파일이 없거나 손상된 경우 각 라이브러리의
원본 traceback으로 그대로 실패했다. IQR 처리는 정확했지만 Checkpoint가 명시한 "파일 로딩 예외" 반영이
비어 있었다.

**해결**: `_common.py`에 `ensure_csv_exists()`를 두어 파일 부재 시 `FileNotFoundError`를 명확한 메시지로
발생시키도록 했고, step2~5가 이를 공통으로 사용한다. 파일 존재 확인 이후 실제 파싱 단계에서도 pandas
`EmptyDataError`/`ParserError`, polars `ComputeError`, duckdb `Error`를 잡아 `ValueError`로 다시 발생시켜
손상된 CSV도 명확한 원인 메시지로 실패하도록 했다. 존재하지 않는 경로로 각 함수를 호출해 예외가 실제로
발생하는지 검증했다.

**이슈2 — 집계 함수 중복**: `step3`/`step4`/`step5` 각 파일에서 `agg_region_category`와
`agg_payment_method`(및 월별 집계)가 group 컬럼만 다르고 구조가 거의 동일하게 반복되어 있었다.

**해결**: 각 파일에 group 컬럼 리스트를 인자로 받는 내부 헬퍼(`_named_aggregation` in pandas/polars,
`_named_agg_sql` in DuckDB)를 두어 중복된 집계 로직을 하나로 합쳤다. 월별 집계는 `order_month`가 파생
컬럼(DuckDB는 `SUBSTR` 표현식)이라 별도 함수로 유지했지만, DuckDB의 공통 FROM/WHERE 서브쿼리
(`build_filtered_query`)는 계속 재사용한다.

리팩터링 후 세 스크립트를 재실행해 기존 `outputs/stepN_*_log.txt`와 diff로 비교했고, 출력이 완전히
동일함을 확인했다(처리 로직 자체는 바뀌지 않았으므로).
