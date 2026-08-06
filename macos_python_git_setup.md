# macOS Python 실습 환경 및 Git 설정

## 1. VS Code 터미널 설정

VS Code에서 터미널을 연다.

- `Terminal → New Terminal`
- 기본 셸은 일반적으로 `zsh`
- 터미널 오른쪽 `∨`에서 `zsh` 선택

기본 터미널 설정:

1. `Cmd + Shift + P`
2. `Terminal: Select Default Profile`
3. `zsh` 선택

---

## 2. Homebrew 설치 확인

터미널에서 확인한다.

```bash
brew --version
```

버전이 출력되면 설치된 상태이다.

Homebrew가 없다면 공식 설치 명령을 이용해 설치한다.

설치 후 터미널을 다시 열고 확인한다.

```bash
brew --version
```

---

## 3. Python 3.11 설치

```bash
brew install python@3.11
```

설치 확인:

```bash
python3.11 --version
which python3.11
```

확인 기준:

```text
Python 3.11.x
```

Apple Silicon Mac에서는 일반적으로 다음 경로가 표시된다.

```text
/opt/homebrew/bin/python3.11
```

Intel Mac에서는 다음 경로가 표시될 수 있다.

```text
/usr/local/bin/python3.11
```

---

## 4. 프로젝트 폴더 생성

영문 경로를 권장한다.

```bash
mkdir -p ~/dev/skala-python
cd ~/dev/skala-python
```

현재 위치 확인:

```bash
pwd
```

예상 경로:

```text
/Users/사용자명/dev/skala-python
```

---

## 5. Python 3.11 가상환경 생성

```bash
python3.11 -m venv .venv
```

생성 확인:

```bash
ls -a
```

다음 폴더가 보여야 한다.

```text
.venv
```

---

## 6. 가상환경 활성화

```bash
source .venv/bin/activate
```

정상적으로 활성화되면 터미널 앞에 `(.venv)`가 표시된다.

```text
(.venv) 사용자명@MacBook skala-python %
```

---

## 7. 가상환경 확인

```bash
python --version
which python
python -c "import sys; print(sys.executable)"
```

확인 기준:

```text
Python 3.11.x
/Users/사용자명/dev/skala-python/.venv/bin/python
```

`which python` 결과가 `.venv/bin/python`으로 끝나야 한다.

---

## 8. pip 업데이트

```bash
python -m pip install --upgrade pip
python -m pip --version
```

pip 경로에도 `.venv`가 포함되어 있어야 한다.

---

## 9. VS Code에서 프로젝트 열기

```bash
code .
```

처음 열 때 다음을 선택한다.

```text
Yes, I trust the authors
```

### `code` 명령이 인식되지 않는 경우

VS Code에서 다음을 실행한다.

1. `Cmd + Shift + P`
2. `Shell Command: Install 'code' command in PATH`
3. 터미널을 닫았다가 다시 연다
4. 다시 실행한다.

```bash
code .
```

---

## 10. VS Code Python 확장 확인

VS Code 왼쪽 Extensions에서 다음 확장을 확인한다.

```text
Python
```

Microsoft에서 제공하는 Python 확장이 없다면 설치한다.

주피터 노트북을 사용할 경우 다음 확장도 확인한다.

```text
Jupyter
```

---

## 11. VS Code Python 인터프리터 선택

1. `Cmd + Shift + P`
2. `Python: Select Interpreter`
3. 프로젝트의 가상환경 선택

```text
.venv (3.11.x)  ./.venv/bin/python
```

목록에 나타나지 않으면 다음 경로를 직접 선택한다.

```text
~/dev/skala-python/.venv/bin/python
```

VS Code 오른쪽 아래에도 `.venv`가 표시되는지 확인한다.

---

## 12. Python 실행 테스트

`hello.py` 파일을 생성한다.

```python
import sys

print("SKALA Python 환경 준비 완료")
print("Python 버전:", sys.version)
print("실행 경로:", sys.executable)
```

터미널에서 실행한다.

```bash
python hello.py
```

실행 경로에 다음 내용이 포함되어야 한다.

```text
skala-python/.venv/bin/python
```

---

## 13. Git 제외 파일 설정

프로젝트 최상위 폴더에 `.gitignore` 파일을 만든다.

```gitignore
.venv/
__pycache__/
*.pyc
.env
.DS_Store
```

각 항목의 의미:

- `.venv/`: 가상환경 폴더 제외
- `__pycache__/`: Python 캐시 폴더 제외
- `*.pyc`: 컴파일된 Python 파일 제외
- `.env`: API 키 등 환경변수 파일 제외
- `.DS_Store`: macOS가 자동 생성하는 파일 제외

---

## 14. 빈 requirements.txt 생성

```bash
touch requirements.txt
```

파일 확인:

```bash
ls -a
```

패키지를 아직 설치하지 않았다면 빈 파일이어도 된다.

---

## 15. Git 설치 확인

```bash
git --version
```

macOS에서 Git이 설치되지 않은 경우 설치 안내 창이 나타날 수 있다.

안내에 따라 Command Line Tools를 설치한 뒤 다시 확인한다.

```bash
git --version
```

---

## 16. Git 저장소 초기화

```bash
git init
git status
```

`.gitignore` 설정이 정상이라면 `.venv`는 `git status`에 나타나지 않는다.

---

## 17. 첫 번째 Git 커밋

```bash
git add .
git commit -m "Initial Python environment setup"
```

Git 사용자 정보 오류가 발생하면 설정한다.

```bash
git config --global user.name "GitHub 사용자명"
git config --global user.email "GitHub 가입 이메일"
```

설정 확인:

```bash
git config --global user.name
git config --global user.email
```

다시 커밋:

```bash
git commit -m "Initial Python environment setup"
```

---

## 18. 기본 브랜치를 main으로 변경

```bash
git branch -M main
git status
```

정상 확인:

```text
On branch main
nothing to commit, working tree clean
```

---

## 19. GitHub 원격 저장소 생성

GitHub에서 빈 저장소를 만든다.

```text
저장소 이름: skala-python
```

다음 항목은 선택하지 않는다.

- README 생성
- `.gitignore` 추가
- License 추가

---

## 20. GitHub 원격 저장소 연결

```bash
git remote add origin https://github.com/사용자명/skala-python.git
```

연결 확인:

```bash
git remote -v
```

예상 결과:

```text
origin  https://github.com/사용자명/skala-python.git (fetch)
origin  https://github.com/사용자명/skala-python.git (push)
```

`origin`은 GitHub 원격 저장소 주소에 붙인 별명이다.

```text
origin = https://github.com/사용자명/skala-python.git
```

---

## 21. GitHub 최초 push

```bash
git push -u origin main
```

처음 실행하면 GitHub 인증이 필요할 수 있다.

정상 완료 메시지 예시:

```text
main -> main
branch 'main' set up to track 'origin/main'
```

GitHub 저장소에서 다음 파일을 확인한다.

```text
.gitignore
hello.py
requirements.txt
```

`.venv` 폴더는 GitHub에 나타나지 않아야 한다.

---

## 22. 1일차 실습용 패키지 설치

가상환경이 활성화되어 있는지 먼저 확인한다.

```bash
which python
```

결과가 다음과 비슷해야 한다.

```text
.../skala-python/.venv/bin/python
```

패키지 설치:

```bash
python -m pip install httpx pydantic pandas pyarrow pytest ruff
```

주요 용도:

- `httpx`: API 요청 및 비동기 통신
- `pydantic`: 데이터 구조와 타입 검증
- `pandas`: 데이터 처리
- `pyarrow`: Parquet 파일 저장 및 읽기
- `pytest`: 테스트 코드 실행
- `ruff`: 코드 검사 및 포매팅

---

## 23. 2일차 실습용 패키지 설치

```bash
python -m pip install polars duckdb matplotlib seaborn plotly scipy scikit-learn joblib jinja2 jupyter ipykernel
```

주요 용도:

- `polars`: 대용량 데이터 처리
- `duckdb`: 파일 기반 SQL 분석
- `matplotlib`, `seaborn`, `plotly`: 데이터 시각화
- `scipy`: 통계 분석
- `scikit-learn`: 머신러닝
- `joblib`: 모델 저장 및 불러오기
- `jinja2`: 보고서 템플릿
- `jupyter`, `ipykernel`: 주피터 노트북 실행

---

## 24. 패키지 설치 확인

```bash
python -c "import httpx, pydantic, pandas, pyarrow, pytest, polars, duckdb, matplotlib, seaborn, plotly, scipy, sklearn, joblib, jinja2, jupyter, ipykernel; print('설치 완료')"
```

정상 결과:

```text
설치 완료
```

---

## 25. requirements.txt 생성

모든 패키지 설치와 확인이 끝난 뒤 실행한다.

```bash
python -m pip freeze > requirements.txt
```

이 명령은 현재 가상환경에 설치된 패키지와 버전을 `requirements.txt`에 저장한다.

예:

```text
httpx==0.28.1
pandas==3.0.5
pydantic==2.13.4
pytest==9.1.1
```

새로운 패키지를 설치해도 `requirements.txt`가 자동으로 바뀌지는 않는다.

패키지 설치가 끝난 뒤 다음 명령을 다시 실행해야 한다.

```bash
python -m pip freeze > requirements.txt
```

다른 PC에서는 다음 명령으로 필요한 패키지를 설치할 수 있다.

```bash
python -m pip install -r requirements.txt
```

---

## 26. 패키지 설치 결과 Git 반영

```bash
git status
git add .
git commit -m "Add Python course dependencies"
git push
```

---

## 27. 이후 파일 추가·수정·삭제 반영

파일 추가, 수정, 삭제 후 다음 순서로 반영한다.

```bash
git status
git add .
git commit -m "작업 내용"
git push
```

삭제한 파일도 같은 명령으로 GitHub에 반영된다.

예:

```bash
git add .
git commit -m "Remove hello.py"
git push
```

---

## 28. 가상환경 종료

```bash
deactivate
```

터미널 앞의 `(.venv)` 표시가 사라진다.

---

## 29. 다음에 프로젝트 다시 시작하기

```bash
cd ~/dev/skala-python
source .venv/bin/activate
code .
```

확인:

```bash
python --version
which python
python -c "import sys; print(sys.executable)"
```

---

## 30. Jupyter 커널 확인

주피터 노트북을 사용하는 경우 가상환경을 커널로 등록할 수 있다.

```bash
python -m ipykernel install --user --name skala-python --display-name "Python 3.11 (skala-python)"
```

VS Code 또는 Jupyter Notebook에서 다음 커널을 선택한다.

```text
Python 3.11 (skala-python)
```

일반 `.py` 파일만 사용하는 경우 이 단계는 생략할 수 있다.

---

## 최종 프로젝트 구조

```text
skala-python/
├─ .git/
├─ .venv/
├─ .gitignore
├─ hello.py
└─ requirements.txt
```

GitHub에 포함되는 파일:

```text
.gitignore
hello.py
requirements.txt
```

GitHub에서 제외되는 항목:

```text
.venv/
__pycache__/
*.pyc
.env
.DS_Store
```

---

## Windows와 macOS 주요 차이

| 구분 | Windows | macOS |
|---|---|---|
| 기본 터미널 | Command Prompt | zsh |
| Python 설치 | winget | Homebrew |
| 가상환경 생성 | `python.exe -m venv .venv` | `python3.11 -m venv .venv` |
| 가상환경 활성화 | `.venv\Scripts\activate.bat` | `source .venv/bin/activate` |
| Python 경로 확인 | `where python` | `which python` |
| 프로젝트 경로 | `C:\dev\skala-python` | `~/dev/skala-python` |
| 빈 파일 생성 | `type nul > 파일명` | `touch 파일명` |
| macOS 자동 파일 | 없음 | `.DS_Store` 제외 필요 |

---

## 전체 작업 흐름 요약

```text
Homebrew 확인
→ Python 3.11 설치
→ 프로젝트 폴더 생성
→ 가상환경 생성·활성화
→ VS Code 인터프리터 선택
→ Python 실행 확인
→ .gitignore 작성
→ Git 초기화 및 첫 커밋
→ GitHub 연결 및 push
→ 필요한 패키지 설치
→ 패키지 import 확인
→ pip freeze로 requirements.txt 생성
→ Git commit 및 push
```