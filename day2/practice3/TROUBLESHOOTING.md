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
