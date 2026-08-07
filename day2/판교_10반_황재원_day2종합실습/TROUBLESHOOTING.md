# Day2 종합 실습 2 — 트러블슈팅 기록

진행 중 발생한 이슈를 이슈 → 원인 → 해결 순서로 기록한다.

## Step 9 — ML Pipeline 모델 파일 용량 과다

**이슈**: `RandomForestRegressor`/`RandomForestClassifier`를 트리 깊이 제한 없이
`n_estimators=200`으로 학습시키자 `joblib.dump()` 결과 파일이 회귀 313MB, 분류 156MB까지
커졌다.

**원인**: 범주형 피처 중 `Country`가 원핫인코딩되면서 열 수가 크게 늘어난 상태에서, 트리
깊이 제한 없이 22,457행을 학습시키다 보니 개별 트리가 매우 깊어졌다(`day2/practice4`에서도
동일한 원인으로 모델이 500MB까지 커졌던 전례가 있음).

**해결**: `n_estimators=200→100`, `max_depth=15`로 조정했다. 회귀 R²는 0.5938→0.5879,
분류 Accuracy는 0.8059→0.7861로 소폭 낮아졌지만, 모델 파일은 회귀 29MB·분류 11MB로 대폭
줄었고 학습 시간도 크게 단축됐다(약 55초 → 약 11초). 성능 손실 대비 용량·속도 이득이 커
이 설정으로 확정했다.

## Step 0/5 — Polars가 로딩 벤치마크에만 쓰이고 EDA에는 반영되지 않음

**이슈**: `main.py`가 Step 0에서 `compare_engines()`로 Polars DataFrame을 받아놓고
`_polars_df`라는 언더스코어 변수로 즉시 버려서, Step 1~10이 전부 Pandas로만 실행되고
있었다. 채점 기준(Pandas·Polars 모두 사용해 EDA 수행)을 충족하지 못하는 상태였다.

**해결**: `src/eda_polars.py`를 신규 작성해 Step 0에서 로딩한 Polars DataFrame을 재사용하는
`run_raw_missing_rate_polars`(Step 1 결측률 집계)와 `run_salary_group_comparison_polars`
(Step 5 급여 정제·범주형 그룹 비교)를 Polars Lazy API로 구현했다. 후자는 Pandas Step 2와
동일한 IQR 경계를 넘겨받아 같은 조건으로 정제하고, 정제 후 행 수·`RemoteWork` 그룹 중앙값을
Pandas 결과와 대조해 로그에 남긴다.

## Step 5 (Polars) — 문자열/숫자 비교 ComputeError

**이슈**: `run_salary_group_comparison_polars`에서 `ConvertedCompYearly`에 IQR 경계로
`is_between()`을 적용하자 `polars.exceptions.ComputeError: cannot compare string with
numeric type (f64)`가 발생했다.

**원인**: Polars가 CSV 스키마를 추론할 때(`infer_schema_length=None`, `ignore_errors=True`)
`ConvertedCompYearly`를 문자열(`str`)로 읽었다. Pandas는 동일 컬럼을 `float64`로 읽으므로
같은 이름의 컬럼이라도 두 엔진의 dtype 추론 결과가 다를 수 있음을 보여주는 사례다.

**해결**: 비교 연산 전에 `pl.col(TARGET_COL).cast(pl.Float64, strict=False)`로 명시적
캐스팅을 추가했다(파싱 불가 값은 null 처리). 캐스팅 후 재실행한 결과 정제 후 행 수(22,457행)와
`RemoteWork` 그룹 급여 중앙값(Remote 70,000 / Hybrid 64,444 / In-person 42,962) 모두
Pandas 결과와 정확히 일치함을 확인했다.

## Step 1 (Polars) — 결측률이 Pandas와 크게 다름 ("NA" 문자열 미인식)

**이슈**: Pandas와 Polars 결과를 비교해 달라는 요청을 받고 대조해보니, Step 5(정제·그룹비교)는
완전히 일치했지만 Step 1 결측률 집계는 컬럼마다 크게 달랐다. 예를 들어 `AINextMuch less
integrated`의 결측률이 Pandas 98.2% vs Polars 50.5%로 거의 2배 차이 났다.

**원인**: 직접 `value_counts()`로 대조한 결과, 원본 CSV에는 결측을 나타내는 리터럴 문자열
`"NA"`가 실제로 들어있었다(예: `AINextMuch less integrated`의 Pandas 결측 64,289건 중
33,020건만 Polars 기준 진짜 null이고 나머지 31,269건은 `"NA"`라는 문자열 값). **Pandas
`read_csv`는 기본 `na_values`에 `"NA"`가 포함돼 있어 자동으로 NaN 처리하지만, Polars
`read_csv`는 기본적으로 `"NA"`를 결측으로 인식하지 않고 문자열 그대로 남긴다.** 이 토큰은
`ConvertedCompYearly`, `RemoteWork`, `Country` 등 파이프라인 핵심 컬럼에도 존재했다.
Step 5 교차검증이 그럼에도 일치했던 것은, `ConvertedCompYearly`를 숫자로 캐스팅하는 과정에서
`"NA"`가 어차피 파싱 실패로 null이 되고, `RemoteWork`의 `"NA"` 그룹은 최소 표본 크기(30건)
미만이라 상위 목록에 드러나지 않았을 뿐이었다 — 근본 원인은 남아있는 채 결과 표시상 우연히
맞아떨어진 상태였다.

**해결**: `src/data_loader.py`의 `load_with_polars()`에서 `pl.read_csv(...,
null_values=["NA"])`를 추가해 Pandas와 동일한 기준으로 `"NA"`를 결측 처리하도록 맞췄다.
재실행 결과 Step 1 Polars 결측률 상위 15개 컬럼이 Pandas와 완전히 일치했다.

## Step 6 — 수치형 피처 간 다중공선성 미검토

**이슈**: Step 4 상관행렬에 이미 `YearsCode`·`YearsCodePro`·`WorkExp` 사이 상관계수가
0.87~0.92로 매우 높게 나와 있었는데, Step 6 피처 선택 시 급여와의 상관(모두 0.40 안팎)만
보고 셋 다 모델 피처로 채택했다. 사용자가 다중공선성 여부를 지적해 VIF(분산팽창지수)를
계산해보니 `YearsCode` 6.19, `YearsCodePro` 10.57, `WorkExp` 6.97로(통상 VIF>5 주의,
VIF>10 심각 기준) 명백한 다중공선성이 확인됐다.

**원인**: `YearsCode`(전체 코딩 경력), `YearsCodePro`(전문 코딩 경력), `WorkExp`(직장 경력)는
사실상 같은 "경력 연차"라는 개념을 서로 다른 방식으로 중복 측정한 값이라 상관이 극단적으로
높을 수밖에 없다. RandomForest는 다중공선성에 선형회귀만큼 취약하지 않지만, 피처 중요도가
세 변수에 인위적으로 분산돼 해석을 왜곡한다.

**해결**: 급여와의 상관이 가장 높고(r=0.408) VIF가 가장 낮은(6.97) `WorkExp`만 남기고
`YearsCode`/`YearsCodePro`를 `FEATURE_NUMERIC`에서 제외했다(`src/preprocessing.py`).
재학습 결과 회귀 R²는 0.5879→0.5370, 분류 F1은 0.7914→0.7781로 낮아졌지만(중복 신호가
줄어든 자연스러운 트레이드오프), 분류 Accuracy는 0.7861로 변화 없었고 피처 해석의 엄밀성을
얻었다. Step 7 시각화(산점도·상관 히트맵)도 `WorkExp` 기준으로 함께 수정했다.

## Step 6 후속 — 나머지 피처 조합 다중공선성 재검증

**확인 배경**: `YearsCode`/`YearsCodePro` 제거로 수치형 다중공선성은 해결됐지만, 남은 피처
조합(수치형 `WorkExp`/`JobSat`, 범주형 `Country`/`RemoteWork`/`EdLevel`/`OrgSize`/`Industry`)
전체에 대해서도 다중공선성이 없는지 추가로 검증했다.

**검증 방법**: 수치형-수치형은 VIF, 범주형-범주형은 Cramér's V(0~1, 범주형 변수 간 연관성
강도 지표 — VIF는 연속형·더미 인코딩 전제라 범주형 원본 변수 간 연관성 확인에는 부적절)로
각각 계산했다.

**결과**:

| 구분 | 대상 | 수치 |
|---|---|---|
| 수치형 VIF | WorkExp | 1.01 |
| 수치형 VIF | JobSat | 1.01 |
| Cramér's V | Country ↔ RemoteWork | 0.303 (약~중간) |
| Cramér's V | Country ↔ EdLevel | 0.176 (약함) |
| Cramér's V | RemoteWork ↔ OrgSize | 0.135 (약함) |
| Cramér's V | 그 외 조합 | 모두 0.13 미만 |

`WorkExp`/`JobSat`는 VIF≈1로 사실상 완전히 독립적이다. 범주형 조합 중 가장 높은 `Country`-`RemoteWork`
0.303도 "중간" 문턱값(0.3)에 걸쳐 있을 뿐 강한 연관은 아니며(국가별 원격근무 문화 차이 정도로
해석 가능), 나머지는 전부 약한 연관(< 0.2)이다.

**결론**: 추가 조치는 필요 없다고 판단해 현재 7개 피처 구성(`WorkExp`, `JobSat`, `Country`,
`RemoteWork`, `EdLevel`, `OrgSize`, `Industry`)을 그대로 유지했다.
