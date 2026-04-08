"""
Benchmark script — measures latency and throughput for architecture analysis.

Runs a set of test queries against the system and reports P50, P95, P99
latency, plus throughput metrics.  Results are used in the architecture
analysis document (Task 4).
"""

import sys
import time
import statistics
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from aamsir.main import app  # noqa: E402 — triggers full initialization
from aamsir.api.routes import get_orchestrator  # noqa: E402

TEST_QUERIES = [
    "What is the leave policy for employees?",
    "How many days of sick leave do employees get?",
    "What is the travel reimbursement process?",
    "What are the graduation requirements for CS?",
    "How many credits are needed to graduate?",
    "What is the password policy?",
    "How do I report a security incident?",
    "What are the research funding options?",
    "How much is the per diem for international travel?",
    "What is the GPA requirement for magna cum laude?",
    "Who approves grant applications?",
    "What is the maximum seed grant amount?",
    "How do I apply for parental leave?",
    "What are the data classification levels?",
    "When is the graduation application deadline?",
    "What expenses are not reimbursable?",
    "What is the indirect cost rate for grants?",
    "How do I connect personal devices to the network?",
    "What is the annual leave accrual rate?",
    "What are the capstone project requirements?",
]

STRATEGY_CONFIGS = [
    ("syntactic", ["syntactic"]),
    ("semantic", ["semantic"]),
    ("syntactic+semantic", ["syntactic", "semantic"]),
]


def percentile(data: list[float], p: int) -> float:
    """Compute the p-th percentile of a sorted list."""
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100)
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    d = k - f
    return sorted_data[f] + d * (sorted_data[c] - sorted_data[f])


def run_benchmark():
    """Execute benchmark queries and print results."""
    orch = get_orchestrator()

    print("=" * 70)
    print("AAMSIR Benchmark — Latency & Throughput Analysis")
    print("=" * 70)
    print(f"Test queries: {len(TEST_QUERIES)}")
    print(f"Available strategies: {orch.get_available()}")
    print()

    for config_name, strategies in STRATEGY_CONFIGS:
        print(f"--- Configuration: {config_name} ---")
        latencies: list[float] = []

        for query in TEST_QUERIES:
            start = time.perf_counter()
            merged, _, elapsed = orch.query(query, strategies, top_k=5)
            end = time.perf_counter()
            wall_ms = (end - start) * 1000
            latencies.append(wall_ms)

        mean = statistics.mean(latencies)
        p50 = percentile(latencies, 50)
        p95 = percentile(latencies, 95)
        p99 = percentile(latencies, 99)
        total_time = sum(latencies) / 1000
        throughput = len(TEST_QUERIES) / total_time

        print(f"  Mean:       {mean:.1f} ms")
        print(f"  P50:        {p50:.1f} ms")
        print(f"  P95:        {p95:.1f} ms")
        print(f"  P99:        {p99:.1f} ms")
        print(f"  Min:        {min(latencies):.1f} ms")
        print(f"  Max:        {max(latencies):.1f} ms")
        print(f"  Total time: {total_time:.2f} s")
        print(f"  Throughput: {throughput:.1f} queries/sec")
        print(f"  NFR-01 (P95 ≤ 15s): {'PASS' if p95 <= 15000 else 'FAIL'}")
        print()

    print("=" * 70)
    print("Benchmark complete.")


if __name__ == "__main__":
    run_benchmark()
