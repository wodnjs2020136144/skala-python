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
    lines = ["| 엔진 | 평균 소요시간(ms) | 반복 횟수 |", "|---|---|---|"]
    for r in sorted(results, key=lambda x: x["avg_ms"]):
        lines.append(f"| {r['engine']} | {r['avg_ms']:.2f} | {r['number']} |")
    return "\n".join(lines)


def main() -> None:
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
