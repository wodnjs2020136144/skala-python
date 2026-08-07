# Day2 Practice3 — 트러블슈팅 기록

## Step2 — 데이터 프로파일링

**이슈**: 실습 가이드 문서는 `sales_100k.csv`를 10만 건 규모의 결측치 없는 가상 데이터로 설명하지만, 실제 파일은 100만 건이며 `region`(1.0%), `category`(0.8%), `amount`(0.5%)에 결측치가 존재한다.

**해결**: 가이드 예시 코드는 참고하지 않고 실제 스키마를 `df.info()` / `df.isnull().sum()`으로 직접 확인한 뒤 파이프라인을 설계했다. 결측 행은 집계 전 명시적으로 제거하고 제거 건수를 로그로 남기는 방식을 채택했다(암묵적 `dropna` 대신 명시적 처리로 원인 추적 가능).

**부가 발견**: `amount`와 `quantity * unit_price`를 비교했을 때 약 2%(19,874건)가 허용 오차(±1) 밖에 있었다. 실제 데이터에 존재하는 노이즈로 판단하고, 이번 실습 범위(엔진 간 처리 성능 비교)와는 무관하므로 별도 정제 없이 현상만 기록했다.

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
