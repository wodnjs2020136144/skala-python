# Day1 Practice 1 [심화 실습]: 자료구조 집계 · 컴프리헨션 · 제너레이터.
# 작성자: P345 황재원
# 작업환경: Python 3.11.6, macOS, VSCode
# 작성일: 2026-08-06
# 설명: Python_Practice1_Data.json의 매출 데이터를 컴프리헨션, Counter, defaultdict, 제너레이터로 집계한다.
# 변경내역:
#   - 2026-08-06: 최초 작성

import json
import sys
from collections import Counter, defaultdict
from collections.abc import Generator
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[2] / "Python_Practice1_Data.json"
HIGH_AMOUNT_THRESHOLD = 1000

with open(DATA_PATH, "r", encoding="utf-8") as f:
    raw_text = f.read()

# 교수님이 주신 Python_Practice1_Data.json은 "sales = [...]" 형태(파이썬 변수 할당 문법)라 순수 JSON이 아니었다.
# 처음 "[" 앞부분을 잘라내고 배열 부분만 파싱한다.
json_start = raw_text.index("[")
data = json.loads(raw_text[json_start:])

# 데이터 구조 파악용
# print(len(data))
# print(data[0])

# ---------------------------------------------------------
# 1) 리스트/딕셔너리 컴프리헨션 amount >= 1000 필터링 후 지역별 총매출(region_total) 계산
# ---------------------------------------------------------
filtered_sales = [s for s in data if s["amount"] >= HIGH_AMOUNT_THRESHOLD]

regions = {s["region"] for s in filtered_sales}
region_total: dict[str, float] = {
    region: sum(s["amount"] for s in filtered_sales if s["region"] == region)
    for region in regions
}
print(f"[1] 지역별 총매출 (컴프리헨션): {region_total}")

# 위의 컴프리헨션 방식은 지역 수만큼 filtered_sales를 반복 스캔해 O(n * 지역 수)로 동작합니다.
# defaultdict + for 루프로 한 번만 순회하면 O(n)으로 더 빠르다...
#
#   region_total = defaultdict(float)
#   for s in filtered_sales:
#       region_total[s["region"]] += s["amount"]
#
# 다만 문제 요구사항에서 "지역별 총매출 dict를 컴프리헨션으로 계산"이 필터링에서 컴프리헨션을 썼더라도,
# 총매출 dict는 컴프리헨션으로 한게 아니라 감점요소에 포함될지 애매해서 순수 컴프리헨션만 사용한 버전을 적었습니다...

assert region_total["서울"] == sum(
    s["amount"] for s in data if s["region"] == "서울" and s["amount"] >= HIGH_AMOUNT_THRESHOLD
), "서울 총매출 계산이 정확해야 합니다."

# ---------------------------------------------------------
# 2) Counter + defaultdict
# ---------------------------------------------------------
region_counts = Counter(s["region"] for s in data)
print(f"[2-1] 지역별 거래 건수 (Counter): {region_counts.most_common()}")

category_amounts = defaultdict(list)
for s in data:
    category_amounts[s["category"]].append(s["amount"])
print(f"[2-2] 카테고리별 amount 목록: {dict(category_amounts)}")

# ---------------------------------------------------------
# 3) 제너레이터 — 메모리 비교
# ---------------------------------------------------------


def filter_high_sales(sales: list[dict]) -> Generator[dict, None, None]:
    """amount > 1000인 거래만 한 번에 하나씩 반환하는 제너레이터."""
    for s in sales:
        if s["amount"] > HIGH_AMOUNT_THRESHOLD:
            yield s


gen_obj = filter_high_sales(data)
list_obj = [s for s in data if s["amount"] > HIGH_AMOUNT_THRESHOLD]

gen_size = sys.getsizeof(gen_obj)
list_size = sys.getsizeof(list_obj)
print(
    f"[3] 메모리 용량 비교 - Generator: {gen_size} bytes vs List: {list_size} bytes")
assert gen_size < list_size, "Generator 메모리가 더 적어야 합니다."

# ---------------------------------------------------------
# 4) 종합 - 월별/카테고리별 매출 집계
# ---------------------------------------------------------
month_cat_sales = defaultdict(float)
for s in data:
    key = (s["month"], s["category"])
    month_cat_sales[key] += s["amount"]

print("[4] 월별/카테고리별 매출 집계:")
for (m, c), total in sorted(month_cat_sales.items()):
    print(f"  - {m} | {c}: {total:,.0f}원")

# top3 금액 내림차순 정렬
top3_month_cat = sorted(month_cat_sales.items(),
                        key=lambda item: item[1], reverse=True)[:3]
print(f"[4-1] 월별/카테고리별 매출 top3 (내림차순): {top3_month_cat}")
assert top3_month_cat == sorted(
    top3_month_cat, key=lambda item: item[1], reverse=True)
