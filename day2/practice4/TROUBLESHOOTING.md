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

**설계 결정 — 피처에서 amount 제외**: 실습 가이드는 `ColumnTransformer`+`Pipeline` 코드 형태를
보여주는 예시로 `X = df[['region','category','amount']]`, `y = (amount > mean(amount))`라는
컬럼 구성을 들고 있었다. 가이드 코드는 API 사용법을 보여주는 참고 자료일 뿐 이 컬럼 구성을 그대로
따르라는 의미는 아니지만, 이 구성을 그대로 가져다 쓰면 타깃을 만드는 데 쓴 `amount` 컬럼이 피처에도
그대로 들어가 모델이 사실상 자기 자신을 맞히는 데이터 누수가 생긴다는 점은 실제 데이터로 구현하면서
직접 고려해야 했다.

**결정**: 타깃(`high_value_order = amount > 평균`)은 유지하되, 피처에서는 `amount`를 제외하고
`region`/`category`/`payment_method`(범주형)와 `quantity`/`unit_price`/`customer_age`(수치형)를
사용하도록 설계했다. "주문 규모·가격·고객 속성으로 고액 주문을 예측"하는 현실적인 분류 문제가 됐다.

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

"연계 Point"에 따라 실습4는 실습3의 IQR 정제 결과를 입력으로 사용해야 했다.
실습3가 정제된 행 단위 DataFrame 자체를 파일로 저장해두지 않아(요약 집계만 저장), 아래와 같이
역할을 나눴다.

- **개별 step 스크립트(step2/3/5)**: `day2/practice3/step3_pandas_pipeline.py`의
  `load_and_clean()`/`remove_outliers_iqr()`/`agg_region_category()`를 그대로 import해서 재사용한다
  (`_common.py`의 `load_cleaned_sales()`, `load_region_category_summary()`). 결측 제거·IQR 로직이
  practice3 한 곳에만 존재해 중복이 없다.
- **최종 제출 스크립트(판교_10반_황재원.py)**: 다른 디렉토리에 대한 의존성 없이 독립적으로 실행돼야
  하므로, 결측 제거+IQR 로직을 자체적으로 다시 구현한다.

## VSCode Pylance 정적 타입 검사 이슈

코드 작성 시점에는 터미널 실행으로만 검증했는데, VSCode에서 직접 열어보니 Pylance가 아래 3건을
에러로 표시했다. 셋 다 런타임 크래시는 아니고(실제 실행 결과는 수정 전후 동일), 정적 타입 분석
단계에서만 걸리는 문제였다.

**1) `"Axes" is not exported from module "matplotlib.pyplot"` (reportPrivateImportUsage)**

`ax: plt.Axes` 타입힌트에서 `Axes`가 `matplotlib.pyplot`의 공식 공개 심볼이 아니어서 발생.
`from matplotlib.axes import Axes`로 가져와 `ax: Axes`로 교체해 해결했다. 같은 이유로
`step5_plotly_chart.py`의 `-> px.bar`(함수를 타입으로 잘못 사용)도 `-> go.Figure`
(`plotly.graph_objects.Figure`)로 함께 교정했다.

**2) `Argument of type "Series[Any]" ...` (reportArgumentType, `sns.histplot`)**

`sns.histplot(df["amount"], kde=True, ...)`처럼 Series를 첫 위치 인자로 넘기면 seaborn 타입
스텁이 이를 DataFrame을 기대하는 `data` 파라미터로 해석해 타입 불일치가 났다.
`sns.histplot(data=df, x="amount", kde=True, ...)` 형태로 바꿔, 이미 사용 중이던
`sns.boxplot(data=df, x=..., y=...)` 패턴과 통일해 해결했다.

**3) `Import "step3_pandas_pipeline" could not be resolved` (reportMissingImports)**

`_common.py`는 `sys.path.insert(0, str(PRACTICE3_DIR))`로 실행 시점에 practice3 경로를
추가한 뒤 `from step3_pandas_pipeline import ...`를 한다. Pylance는 코드를 실행하지 않고
정적으로만 분석하므로 이 동적 경로 추가를 알 수 없어 import를 해석하지 못했다.

1차로 `day2/practice4/pyrightconfig.json`에 `extraPaths`를 추가했지만 경고가 그대로 남았다.
VSCode가 저장소 루트(`skala-python`)를 워크스페이스로 열고 있어, Pyright/Pylance는 워크스페이스
루트의 설정 파일만 읽고 하위 폴더의 `pyrightconfig.json`은 인식하지 않기 때문이었다(config는
"열려 있는 워크스페이스 폴더" 기준으로 탐색되며, 파일 위치를 기준으로 상위 탐색을 하지 않는다).

**해결**: 설정 파일을 저장소 루트(`/pyrightconfig.json`)로 옮기고, `executionEnvironments`로
`day2/practice4` 아래 파일에만 `day2/practice3`를 추가 경로로 적용하도록 범위를 좁혔다.

```json
{
  "executionEnvironments": [
    { "root": "day2/practice4", "extraPaths": ["day2/practice3"] }
  ]
}
```

코드 변경 없이 설정만으로 해결했으며(억제 주석 대신 실제 경로를 알려주는 방식이라 해당 함수들의
자동완성·타입 검사도 함께 살아난다), 다른 실습 폴더에는 영향을 주지 않는다.

## sklearn Pipeline 학습 데이터 결정

"연계 Point"는 `sales_100k.csv`(원본)를 Pipeline 학습 데이터 원본으로 명시하고 있어,
시각화·통계 검정과 달리 Pipeline은 IQR 이상치를 제거하지 않은 원본 데이터로 학습했다. 단, 피처로
사용하는 컬럼(`region`/`category`/`amount`)의 결측 행만 제거해 모델 학습이 가능한 상태로 만들었다.
