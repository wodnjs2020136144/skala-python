# Day2 Practice4 — 트러블슈팅 기록

## Step2 — EDA 시각화 4종

**이슈**: `fig, axes = plt.subplots(2, 2)`로 4종 차트를 그렸을 때 제목/축 라벨의 한글이 전부
네모(tofu) 문자로 깨져 출력됐다.

![Step2 실행 결과](outputs/step2_eda_run.png)

**원인**: matplotlib 기본 폰트(DejaVu Sans)에는 한글 글리프가 없다. 1차로
`plt.rcParams["font.family"] = "AppleGothic"`를 모듈 상단에서 설정했지만 여전히 깨졌는데,
`sns.set_style("whitegrid")` 호출이 `font.family`를 `sans-serif`로 다시 초기화하기 때문이었다.

**해결**: `sns.set_style()` 호출 **이후** 시점에 `AppleGothic`(macOS 내장 한글 폰트)을 다시
지정하도록 순서를 바꿔 해결했다. 최종 결과물(`eda_2x2_subplots.png`)에서 4종 차트의 한글 제목이
정상 출력되는 것을 확인했다.

## Step4 — sklearn Pipeline 구축·저장

**이슈1 — 가이드 예시의 데이터 누수**: 참고했던 실습 가이드 예시는 `X = df[['region','category','amount']]`,
`y = (amount > mean(amount))`로 두어, 타깃을 만드는 데 사용한 `amount` 컬럼을 그대로 피처에도
포함시키는 데이터 누수 구조였다. 이 방식은 정확도가 사실상 자기 자신을 맞추는 것이라 의미가 없다.

**해결**: 타깃(`high_value_order = amount > 평균`)은 유지하되, 피처에서는 `amount`를 제외하고
`region`/`category`/`payment_method`(범주형)와 `quantity`/`unit_price`/`customer_age`(수치형)를
사용하도록 재설계했다. "주문 규모·가격·고객 속성으로 고액 주문을 예측"하는 현실적인 분류 문제가 됐다.

**이슈2 — 모델 파일 용량 폭증**: `RandomForestClassifier(n_estimators=100, random_state=42)`를
트리 깊이 제한 없이 약 78만 행으로 학습시키자 `joblib.dump()` 결과 파일이 **약 500MB**까지
커졌다(GitHub 저장소에 커밋하기엔 지나치게 큰 크기이며, 100MB를 넘으면 push 자체가 차단된다).
학습 시간도 약 7분으로 길었다.

![Step4 실행 결과 (개선 후)](outputs/step4_ml_run.png)

**해결**:
- `max_depth=15`, `min_samples_leaf=50`으로 트리 깊이를 제한해 파일 크기를 **37MB**로 줄였다.
  정확도는 0.9875 → 0.9831로 0.004%p만 낮아져 실질적인 손실은 거의 없었다.
- `n_jobs=-1`로 CPU 코어를 모두 활용하도록 해 학습 시간을 약 7분에서 약 1분대로 단축했다.

## 실습3 연계 설계 결정

이미지로 공유된 "연계 Point"에 따라 실습4는 실습3의 IQR 정제 결과를 입력으로 사용해야 했다.
실습3가 정제된 행 단위 DataFrame 자체를 파일로 저장해두지 않아(요약 집계만 저장), 아래와 같이
역할을 나눴다.

- **개별 step 스크립트(step2/3/5)**: `day2/practice3/step3_pandas_pipeline.py`의
  `load_and_clean()`/`remove_outliers_iqr()`/`agg_region_category()`를 그대로 import해서 재사용한다
  (`_common.py`의 `load_cleaned_sales()`, `load_region_category_summary()`). 결측 제거·IQR 로직이
  practice3 한 곳에만 존재해 중복이 없다.
- **최종 제출 스크립트(판교_10반_황재원.py)**: 다른 디렉토리에 대한 의존성 없이 독립적으로 실행돼야
  하므로, 결측 제거+IQR 로직을 자체적으로 다시 구현한다.

## sklearn Pipeline 학습 데이터 결정

이미지의 "연계 Point" 표는 `sales_100k.csv`(원본)를 Pipeline 학습 데이터 원본으로 명시하고 있어,
시각화·통계 검정과 달리 Pipeline은 IQR 이상치를 제거하지 않은 원본 데이터로 학습했다. 단, 피처로
사용하는 컬럼(`region`/`category`/`amount`)의 결측 행만 제거해 모델 학습이 가능한 상태로 만들었다.
