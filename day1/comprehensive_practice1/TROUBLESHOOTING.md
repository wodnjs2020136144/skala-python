# 트러블슈팅 & 의사결정 기록 (암묵지)

Day1 종합 실습 1(데이터 수집 미니 파이프라인)을 사용자와 함께 스텝별로 진행하며 겪은 의사결정·오류·해결 과정을 시간순으로 기록한다.
가이드: `docs/Day1_종합_실습_1_가이드.md`

## [Step 1] venv 활성화 및 의존성 확인

- 상황: 이전 세션(자율 실행)에서 `.venv`를 활성화하지 않고 실행했다가 우연히 문제가 드러나지 않았던 사례가 있어, 이번 재진행에서는 Step 1을 "venv 미활성화가 왜 위험한지" 짚고 넘어가는 것으로 시작함.
- 실행: `source .venv/bin/activate` → `which python3`, `python3 --version`, `echo $VIRTUAL_ENV`로 확인.
- 결과: `python3`가 `/Users/hwangjaewon/skala-workspace/skala-python/.venv/bin/python3`(3.11.15)를 정확히 가리켰고, `VIRTUAL_ENV`도 프로젝트 `.venv` 경로로 잡힘. 프롬프트에도 `(.venv)` 표시 확인.
- 검증: `python3 -c "import httpx, pydantic, pandas, pyarrow, pytest, ruff; print('OK')"` → `OK` 출력, 필요한 패키지 전부 정상 임포트됨.
- 결론: 문제 없이 통과. 앞으로 모든 스텝은 이 `.venv` 활성화 상태를 유지한 채 진행.
