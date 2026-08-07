"""Pandas / Polars Lazy / DuckDB SQL 세 파이프라인의 처리 성능을 비교한다.

동일한 반복 횟수(number=10)로 timeit 측정을 수행해 평균 소요시간을 표로 정리한다.
"""

import timeit
from pathlib import Path

import step3_pandas_pipeline as pandas_pipeline
import step4_polars_pipeline as polars_pipeline
import step5_duckdb_pipeline as duckdb_pipeline

CSV_PATH = Path(__file__).resolve().parents[2] / "sales_100k.csv"
NUMBER = 10


def run_benchmark() -> list[dict]:
    """세 엔진의 run_pipeline()을 동일 반복 횟수(NUMBER)로 timeit 측정한다.

    verbose=False로 호출해 파이프라인 내부 print를 억제하고 순수 처리
    시간만 측정한다.

    Returns:
        엔진별 {engine, avg_ms(평균 소요시간), number(반복 횟수)} 딕셔너리 리스트.
    """
    engines = [
        ("Pandas", lambda: pandas_pipeline.run_pipeline(CSV_PATH, verbose=False)),
        ("Polars Lazy", lambda: polars_pipeline.run_pipeline(CSV_PATH, verbose=False)),
        ("DuckDB SQL", lambda: duckdb_pipeline.run_pipeline(CSV_PATH, verbose=False)),
    ]

    results = []
    for name, func in engines:
        total_sec = timeit.timeit(func, number=NUMBER)
        avg_ms = total_sec / NUMBER * 1000
        results.append({"engine": name, "avg_ms": avg_ms, "number": NUMBER})
    return results


def format_table(results: list[dict]) -> str:
    """벤치마크 결과를 평균 소요시간 오름차순 markdown 표 문자열로 변환한다.

    Args:
        results: run_benchmark()가 반환한 엔진별 결과 리스트.

    Returns:
        markdown 표 형식 문자열.
    """
    lines = ["| 엔진 | 평균 소요시간(ms) | 반복 횟수 |", "|---|---|---|"]
    for r in sorted(results, key=lambda x: x["avg_ms"]):
        lines.append(f"| {r['engine']} | {r['avg_ms']:.2f} | {r['number']} |")
    return "\n".join(lines)


def main() -> None:
    """벤치마크를 실행하고 결과를 출력한 뒤 markdown 표로 저장한다."""
    print(f"[벤치마크 조건] number={NUMBER} (세 엔진 동일 반복 횟수)")
    print("측정 중...")
    results = run_benchmark()

    print("\n=======================================================")
    print("[Practice3 엔진 성능 비교 벤치마크]")
    print("=======================================================")
    for r in results:
        print(f"  - {r['engine']:<12}: {r['avg_ms']:.2f} ms")
    print("=======================================================")

    fastest = min(results, key=lambda x: x["avg_ms"])
    print(f"\n가장 빠른 엔진: {fastest['engine']} ({fastest['avg_ms']:.2f} ms)")

    table_md = format_table(results)
    output_path = Path(__file__).resolve().parent / "outputs" / "benchmark_result.md"
    output_path.write_text(
        f"# Practice3 엔진 성능 벤치마크\n\n반복 횟수(number)={NUMBER}\n\n{table_md}\n",
        encoding="utf-8",
    )
    print(f"\n[저장 완료] {output_path}")


if __name__ == "__main__":
    main()
