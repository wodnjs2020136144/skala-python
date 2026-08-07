# Stack Overflow Developer Survey 2024 개발자 급여 분석 리포트

생성 일시: 2026-08-07 18:28:34

## Step 0. Pandas vs Polars 로딩 비교

| 엔진 | 행 수 | 열 수 | 로딩 시간(초) | 메모리(MB) |
|---|---|---|---|---|
| pandas | 65437 | 114 | 1.109 | 195.7 |
| polars | 65437 | 114 | 0.342 | 145.1 |

## Polars 활용 범위

로딩 성능 비교뿐 아니라, Step 1(원본 결측률 집계)과 Step 5(급여 정제·범주형 그룹 비교)를 Polars Lazy API로 이중 수행하고 Pandas 결과와 대조했다.
- Step 1 결측률 집계: Polars 0.012초
- Step 5 정제+그룹비교: Polars 0.063초, 정제 후 22457행 (Pandas와 행 수 일치, RemoteWork 그룹 중앙값 일치)

## Step 2. 정제 결과

- 원본 65437행 → 급여 결측 제거 23435행 → 중복 제거 23435행 → IQR 이상치 제거 후 최종 **22457행**
- IQR 경계: [-80,177, 220,861]

## Step 4. 급여와 수치형 변수 상관관계

| 변수 | 상관계수 |
|---|---|
| WorkExp | 0.4084 |
| YearsCodePro | 0.4002 |
| YearsCode | 0.3983 |
| JobSat | 0.0752 |

급여와 가장 강한 상관을 보인 변수는 **WorkExp**(r=0.4084)이다.

## Step 6. 모델용 피처 선택 (다중공선성 제거)

`YearsCode`·`YearsCodePro`·`WorkExp`는 서로 상관계수 0.87–0.92, VIF(분산팽창지수) 6.2–10.6으로 다중공선성이 심각했다. 급여와의 상관이 가장 높고 (r=0.408) VIF가 가장 낮은(6.97) `WorkExp`만 남기고 `YearsCode`/`YearsCodePro`는 모델 피처에서 제외했다.

## Step 8. t-test (Remote vs In-person 급여 비교)

- Remote 평균: 78,720 (n=9039)
- In-person 평균: 52,638 (n=3833)
- t-통계량: 27.8965, p-value: 3.22365e-164
- 해석: p-value(3.22365e-164) < 0.05 → 귀무가설(두 그룹의 급여 평균이 같다) 기각. Remote 근무자와 In-person 근무자의 평균 급여 차이는 통계적으로 유의하다.

## Step 9. ML Pipeline 결과

- 회귀(급여 예측): R²=0.5370, MAE=25,635
- 분류(고액 급여 여부, 임계값=63,694): Accuracy=0.7861, F1-score=0.7781
- 모델 저장 경로: `outputs/models/salary_regression_pipeline.joblib`, `outputs/models/salary_classification_pipeline.joblib`
