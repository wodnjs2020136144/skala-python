# 트러블슈팅 & 의사결정 기록 (암묵지)

Day1 종합 실습 1(데이터 수집 미니 파이프라인)을 사용자와 함께 스텝별로 진행하며 겪은 의사결정·오류·해결 과정을 시간순으로 기록한다.
가이드: `docs/Day1_종합_실습_1_가이드.md`

## [Step 1] venv 활성화 및 의존성 확인

- 상황: 이전 세션(자율 실행)에서 `.venv`를 활성화하지 않고 실행했다가 우연히 문제가 드러나지 않았던 사례가 있어, 이번 재진행에서는 Step 1을 "venv 미활성화가 왜 위험한지" 짚고 넘어가는 것으로 시작함.
- 실행: `source .venv/bin/activate` → `which python3`, `python3 --version`, `echo $VIRTUAL_ENV`로 확인.
- 결과: `python3`가 `/Users/hwangjaewon/skala-workspace/skala-python/.venv/bin/python3`(3.11.15)를 정확히 가리켰고, `VIRTUAL_ENV`도 프로젝트 `.venv` 경로로 잡힘. 프롬프트에도 `(.venv)` 표시 확인.
- 검증: `python3 -c "import httpx, pydantic, pandas, pyarrow, pytest, ruff; print('OK')"` → `OK` 출력, 필요한 패키지 전부 정상 임포트됨.
- 결론: 문제 없이 통과. 앞으로 모든 스텝은 이 `.venv` 활성화 상태를 유지한 채 진행.
- 근거:
  ![Step1 venv 활성화](outputs/step1_venv_activate.png)
  ![Step1 의존성 확인](outputs/step1_dependency_check.png)

## [Step 2] asyncio + httpx 비동기 동시 수집

- 상황: `main_pipeline.py`에 Open-Meteo/Countries.dev/ip-api 3개 API를 `httpx.AsyncClient` + `asyncio.gather()`로 동시 수집하는 코드를 직접 작성.
- 가이드 원본 코드 대비 반영한 결정:
  - 반환 타입은 `typing.Tuple` import 없이 PEP585 내장 제네릭 `tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]`로 표기 — import 누락 문제 자체를 원천 차단.
  - import 순서를 코드 스타일 규칙(`.claude/rules/code-style.md`)에 맞게 표준 라이브러리(`asyncio`, `logging`, `time`, `typing`) → 서드파티(`httpx`) 순으로 정리하고 그룹 사이 빈 줄 삽입.
  - `fetch_weather`에서 `zip(times, temps, probs, strict=True)`를 사용해, 세 리스트 길이가 어긋나면 조용히 잘리지 않고 즉시 `ValueError`로 드러나도록 함.
  - `fetch_country`는 가이드처럼 `except Exception`으로 감싸 하드코딩된 대체값을 반환하지 않고, `raise_for_status()` 실패 시 예외가 그대로 전파되도록 둠 (제너릭 Exception 금지, 예외 무마 금지 규칙 준수). Countries.dev API가 실제로 정상 응답한다는 것은 이미 사전 curl로 확인되어 있어 fallback이 불필요하다고 판단.
  - `print()` 대신 `logging` 모듈(`logger.info`)로 통일.
  - 파일명은 가이드 6장 제출 구조에 맞춰 `mini_pipeline.py` → `main_pipeline.py`로 변경.
  - 모듈 docstring 추가(작성자/작성일/설명), `weather,country,ip` → `weather, country, ip` PEP8 콤마 스페이싱 수정.
- 검증: `python3 day1/comprehensive_practice1/main_pipeline.py` 실행 → 3개 API 로그가 섞여서 찍히고 "3개 API 비동기 동시 수집 완료 (소요시간: 1.034초)", Open-Meteo 72건, Country `{'name': 'Korea (Republic of)', 'alpha2_code': 'KR'}`, IP `{'ip': '8.8.8.8', 'country': 'United States', 'city': 'Ashburn', 'isp': 'Google LLC'}` 정상 출력 확인.
- 결론: Step 2 통과. 순차 호출이 아닌 동시 호출로 3개 API를 약 1초 만에 모두 수집했음을 실측으로 확인.
- 근거:
  ![Step2 실행 결과](outputs/step2_collect_run.png)
  로그 원문: `outputs/step2_collect_log.txt`

## [Step 3] Pydantic v2 스키마 검증

- 상황: `main_pipeline.py`에 `WeatherItem`/`CountryInfo`/`IPLocationInfo` 모델을 정의하고, `collect_all_data()`가 반환한 raw dict를 실제로 검증하는 로직을 `__main__` 블록에 추가.
- 모델 설계 결정:
  - `WeatherItem.time_str`은 원본 API 응답 키가 `time`이라 `Field(..., alias="time")`으로 별칭 처리 — 파이썬에서 `time`은 표준 라이브러리 모듈명과 겹치므로 필드명 자체는 `time_str`로 회피.
  - `precip_prob`에 `ge=0, le=100` 범위 제약을 걸어 강수확률이 논리적으로 유효한 범위인지 검증.
  - `CountryInfo.alpha2_code`에 `min_length=2, max_length=2` 제약을 걸어 국가 코드 형식(2자리)을 강제 — 가이드 원본에는 없던 제약이지만, "타입/범위 검증"이라는 실습 취지에 맞게 추가.
  - 날씨는 리스트이므로 항목별로 `try/except ValidationError`로 개별 검증해, 일부 레코드가 실패해도 나머지는 계속 처리되도록 함.
- 검증 1 (정상 케이스): `main_pipeline.py` 실행 → `Pydantic 검증 완료 - Weather: 72건, Country: Korea (Republic of), IP: 8.8.8.8` 정상 출력.
- 검증 2 (의도적 실패 케이스): `precip_prob=150`(범위 초과)인 더미 데이터를 `WeatherItem.model_validate()`에 직접 넣어 `ValidationError`가 실제로 발생하는지 확인 → `Input should be less than or equal to 100 [type=less_than_equal, input_value=150, input_type=int]` 정확히 포착됨. 검증 로직이 "그냥 통과시키는 게 아니라 실제로 걸러낸다"는 것을 실측으로 확인.
- 결론: Step 3 통과. 정상/실패 케이스 모두 의도대로 동작.
- 근거:
  ![Step3 정상 검증](outputs/step3_validation_run.png)
  ![Step3 검증 실패 케이스](outputs/step3_validation_error_case.png)
  로그 원문: `outputs/step3_validation_log.txt`

## [Step 4] CSV vs Parquet 저장 성능 비교

- 상황: 검증된 `valid_weather`를 `pandas.DataFrame`으로 변환하고, `time.perf_counter()`로 CSV/Parquet 각각의 쓰기·읽기 시간과 파일 용량을 측정하는 `run_pipeline()`을 작성. 이 과정에서 기존 `run_pipeline`이 없던 구조를 `validate_weather()` + `run_pipeline()` 함수로 리팩터링하며 전체 흐름을 하나로 통합.
- 실행: `python3 day1/comprehensive_practice1/main_pipeline.py` (`.venv` 활성화 상태, Terminal.app에서 실행 후 캡처).
- 결과(72건 기준):
  | 항목 | CSV | Parquet |
  |---|---|---|
  | 파일 용량 | 3,943 bytes | 4,264 bytes |
  | 쓰기 시간 | 2.818 ms | 45.629 ms |
  | 읽기 시간 | 3.231 ms | 42.529 ms |
- 해석: 일반적으로 "Parquet이 CSV보다 빠르다"고 알려져 있지만, 이번처럼 소량 데이터(72행)에서는 정반대로 CSV가 훨씬 빠르고 용량도 작았다. Parquet은 컬럼형 포맷 특성상 스키마/메타데이터 기록과 압축 코덱 초기화에 고정 오버헤드가 있어, 레코드 수가 적을 때는 이 오버헤드가 전체 처리 시간을 지배한다. 데이터가 수만~수백만 건 규모로 커지면 컬럼형 압축·I/O 이점이 이 오버헤드를 상쇄하고 역전될 것으로 예상되나, 이번 실습 데이터로는 확인되지 않음.
- 결론: Step 4 통과. "포맷 선택은 데이터 규모에 따라 달라진다"는 실무 감각을 실측으로 확인.
- 근거:
  ![Step4 벤치마크 실행 결과](outputs/step4_benchmark_run.png)
  로그 원문: `outputs/step4_benchmark_log.txt`

## [Step 5] pytest + ruff

- 상황: `tests/test_pipeline.py`에 네트워크 호출 없이 순수하게 Pydantic 모델과 `validate_weather()` 함수만 검증하는 테스트 5건 작성 (정상/경계값/실패 케이스 혼합).
  - `test_weather_item_accepts_valid_range` — 정상 범위 값 통과
  - `test_weather_item_rejects_precip_prob_over_100` — 범위 초과 시 `ValidationError`
  - `test_validate_weather_filters_out_invalid_records` — 정상/비정상 혼합 리스트에서 정상만 필터링되는지
  - `test_country_info_requires_two_letter_alpha2_code` — `alpha2_code="KOR"`(3자리)처럼 길이 제약 위반 시 거부
  - `test_ip_location_info_parses_required_fields` — 필수 필드 정상 파싱
  - 모듈을 패키징하지 않은 단일 폴더 구조라 `sys.path.insert(0, str(Path(__file__).resolve().parent.parent))`로 `main_pipeline` 모듈을 임포트.
- ruff 트러블슈팅(실제 겪은 오류 2건, 순차 해결):
  1. 1차 오류: `I001 Import block is un-sorted` — `main_pipeline.py`의 `import os`가 `import time` 뒤에 위치해 표준 라이브러리 그룹 내 정렬이 어긋남 → `logging, os, time` 순으로 재배치.
  2. 2차 오류: 같은 `I001`이 재발 — `import time`과 `from typing import Any` 사이에 불필요한 빈 줄이 있어 `typing`이 별도 그룹으로 분리되어 있었음(`typing`도 표준 라이브러리라 같은 그룹이어야 함) → 그 빈 줄 삭제로 해결. (중간에 동일 스크린샷을 다시 공유해서 수정이 반영 안 된 것처럼 보였던 순간이 있었으나, 파일을 직접 확인해 이미 정상 상태임을 확인하고 재실행으로 최종 검증함.)
- 검증: `pytest day1/comprehensive_practice1/tests/ -v` → 5 passed. `ruff check day1/comprehensive_practice1/` → All checks passed!
- 결론: Step 5 통과. import 순서 규칙은 "표준 라이브러리 vs 서드파티"뿐 아니라 "같은 그룹 내 알파벳 정렬"과 "그룹 내부에 불필요한 빈 줄 금지"까지 포함한다는 것을 실습으로 체득.
- 근거:
  ![Step5 pytest/ruff 실행 결과](outputs/step5_pytest_ruff_run.png)
  로그 원문: `outputs/step5_pytest_ruff_log.txt`
  실제 산출 파일: `outputs/pipeline_result.csv`, `outputs/pipeline_result.parquet`
