# skala-python

**작성자**: 황재원 (P345) · 판교캠퍼스 10반

SKALA "서비스화 데이터분석 및 AIOps — 데이터 분석을 위한 Python 이해" 강의(Day1~Day2) 실습 저장소.
각 실습 디렉토리에는 제출용 스크립트(`캠퍼스명_반_이름.py`)와 함께 실행 과정·트러블슈팅·결과를 정리한
`README.md`/`TROUBLESHOOTING.md`, 실행 캡처와 산출 파일을 모은 `outputs/`가 포함되어 있다.

## 진행 현황

| Day | 실습 | 내용 | 상태 | 위치 |
|---|---|---|---|---|
| Day1 | Practice1 | 컴프리헨션·`Counter`·`defaultdict`·제너레이터로 매출 데이터 집계 | 완료 | `day1/practice1/` |
| Day1 | Practice2 | 파일 I/O·예외 처리·Pydantic v2 스키마 검증 파이프라인 | 완료 | `day1/practice2/` |
| Day1 | 종합실습1 | `asyncio`+`httpx` 비동기 수집 → Pydantic 검증 → CSV/Parquet 저장 성능 비교 → pytest/ruff | 완료 | [`day1/comprehensive_practice1/`](day1/comprehensive_practice1/README.md) |
| Day2 | Practice3 | Pandas EDA·IQR 이상치 제거 vs Polars Lazy API vs DuckDB SQL 성능 비교 | 완료 | [`day2/practice3/`](day2/practice3/README.md) |
| Day2 | Practice4 | 2×2 서브플롯 시각화·t-test/카이제곱 검정·sklearn Pipeline·Plotly 인터랙티브 차트 | 완료 | [`day2/practice4/`](day2/practice4/README.md) |
| Day2 | 종합실습2 | End-to-End 데이터 분석 파이프라인 (예정) | 진행 예정 | - |

Day2 종합실습2는 아직 진행 전이며, 완료되는 대로 이 표와 아래 요약에 추가한다.

## 디렉토리 구조

```
skala-python/
├── day1/
│   ├── practice1/                   # 컴프리헨션·집계 실습
│   ├── practice2/                   # 파일 I/O·Pydantic 검증 실습
│   └── comprehensive_practice1/     # Day1 종합 실습
├── day2/
│   ├── practice3/                   # Pandas/Polars/DuckDB 성능 비교
│   └── practice4/                   # 시각화·통계 검정·ML Pipeline
├── docs/                            # 강의 학습 가이드 md (참고용, 실습 근거로 쓰지 않음)
├── requirements.txt
└── sales_100k.csv                   # Day2 실습 공통 데이터셋 (gitignore 대상)
```

## 실행 환경

모든 실습은 저장소 루트의 `.venv` 가상환경을 기준으로 한다.

```bash
source .venv/bin/activate
pip install -r requirements.txt   # 이미 설치되어 있다면 생략 가능
```

각 실습의 정확한 실행 명령은 해당 디렉토리의 `README.md`를 따른다.

## 실습 요약

### Day1 Practice1 — 자료구조 집계
`Python_Practice1_Data.json` 매출 데이터를 리스트/딕셔너리 컴프리헨션, `Counter`, `defaultdict`,
제너레이터로 다각도로 집계한다.

### Day1 Practice2 — 파일 I/O·예외 처리·Pydantic 검증
`Python_Practice2_Data.json`을 안전하게 로딩하고 Pydantic v2 스키마로 검증한 뒤, 정상/결함 데이터를
분류해 CSV·JSON으로 저장한다.

### Day1 종합실습1 — 데이터 수집 미니 파이프라인
Open-Meteo/Countries.dev/ip-api 등 외부 API를 `asyncio`+`httpx`로 동시 수집하고 Pydantic v2로
검증한 뒤, CSV와 Parquet 저장 성능을 비교한다. pytest 테스트와 ruff 린트를 포함한다.

### Day2 Practice3 — Pandas / Polars / DuckDB 성능 비교
`sales_100k.csv`(100만 행)를 결측 제거·IQR 이상치 제거 후 Pandas, Polars Lazy API, DuckDB SQL
세 엔진으로 동일하게 집계하고 `timeit`으로 처리 성능을 비교한다. 세 엔진의 결과가 일치함을
교차 검증했다.

### Day2 Practice4 — 시각화 · 통계 검정 · sklearn Pipeline · Plotly
Practice3의 정제 데이터를 입력으로 2×2 서브플롯 EDA 시각화, t-test/카이제곱 통계 검정을 수행하고,
`ColumnTransformer`+`RandomForestClassifier` Pipeline을 학습·저장한 뒤 Plotly 인터랙티브 차트를
생성한다. Pipeline 피처에 `quantity`/`unit_price`를 남겨두면 `amount ≈ quantity × unit_price`
관계 때문에 사실상 산술 연산을 재현하는 데이터 누수가 생긴다는 점을 검증으로 확인해 제외했고,
그 결과 정확도는 베이스라인 수준(0.65)으로 낮아지지만 이는 결함이 아니라 "인구통계·범주형
정보만으로는 고액 주문을 예측하기 어렵다"는 정직한 결과다. 최종 스크립트는 단독 파일로
분리해 실행해도(경로 하드코딩 없이) 동일하게 동작함을 검증했다.
