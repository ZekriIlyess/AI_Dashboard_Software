"""
Nexus AI — LLM Benchmark Script
=================================
Benchmarks local LLM models for SQL generation accuracy and latency.
Tests both primary (main PC) and secondary (second PC) Ollama instances.

Usage:
    python scripts/benchmark-llm.py
    python scripts/benchmark-llm.py --host http://second-pc:11434
    python scripts/benchmark-llm.py --model nemotron-cascade-2:30b --runs 5
"""

import argparse
import json
import time
from dataclasses import dataclass

import httpx


# ---------------------------------------------------------------------------
# Test Cases: Natural Language → Expected SQL Patterns
# ---------------------------------------------------------------------------
BENCHMARK_CASES = [
    {
        "id": "simple_count",
        "question": "How many customers do we have?",
        "schema": "Table: customers (id, email, first_name, last_name, city, country, signup_date, is_churned)",
        "expected_keywords": ["SELECT", "COUNT", "customers"],
        "difficulty": "easy",
    },
    {
        "id": "simple_aggregation",
        "question": "What is the total revenue?",
        "schema": "Table: orders (id, customer_id, order_date, total_amount, status)",
        "expected_keywords": ["SELECT", "SUM", "total_amount", "orders"],
        "difficulty": "easy",
    },
    {
        "id": "filtered_query",
        "question": "How many orders were placed in 2024?",
        "schema": "Table: orders (id, customer_id, order_date, total_amount, status)",
        "expected_keywords": ["SELECT", "COUNT", "orders", "2024"],
        "difficulty": "easy",
    },
    {
        "id": "group_by",
        "question": "What is the total revenue by country?",
        "schema": "Tables: customers (id, country), orders (id, customer_id, total_amount)",
        "expected_keywords": ["SELECT", "SUM", "GROUP BY", "country", "JOIN"],
        "difficulty": "medium",
    },
    {
        "id": "top_n",
        "question": "What are the top 10 customers by lifetime value?",
        "schema": "Table: customers (id, first_name, last_name, email, lifetime_value)",
        "expected_keywords": ["SELECT", "ORDER BY", "lifetime_value", "DESC", "LIMIT", "10"],
        "difficulty": "medium",
    },
    {
        "id": "multi_join",
        "question": "What are the best selling products by category?",
        "schema": "Tables: categories (id, name), products (id, name, category_id, price), order_items (id, order_id, product_id, quantity)",
        "expected_keywords": ["SELECT", "JOIN", "categories", "products", "order_items", "SUM", "GROUP BY"],
        "difficulty": "hard",
    },
    {
        "id": "window_function",
        "question": "Show monthly revenue with month-over-month growth rate",
        "schema": "Table: orders (id, customer_id, order_date, total_amount, status)",
        "expected_keywords": ["SELECT", "DATE_TRUNC", "SUM", "LAG"],
        "difficulty": "hard",
    },
    {
        "id": "churn_analysis",
        "question": "What is the churn rate by signup month?",
        "schema": "Table: customers (id, signup_date, is_churned)",
        "expected_keywords": ["SELECT", "is_churned", "signup_date", "GROUP BY", "AVG"],
        "difficulty": "hard",
    },
]


@dataclass
class BenchmarkResult:
    case_id: str
    difficulty: str
    question: str
    generated_sql: str
    keywords_found: int
    keywords_total: int
    keyword_score: float
    latency_ms: float
    is_valid_sql: bool
    error: str | None = None


def call_ollama(host: str, model: str, prompt: str, timeout: int = 120) -> tuple[str, float]:
    """Call Ollama API and return (response_text, latency_ms)."""
    start = time.perf_counter()
    response = httpx.post(
        f"{host}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 500},
        },
        timeout=timeout,
    )
    latency_ms = (time.perf_counter() - start) * 1000
    response.raise_for_status()
    return response.json()["response"], latency_ms


def build_prompt(question: str, schema: str) -> str:
    """Build a text-to-SQL prompt."""
    return f"""You are a SQL expert. Given the following database schema and a natural language question, generate a PostgreSQL query.

Schema:
{schema}

Question: {question}

Return ONLY the SQL query, nothing else. Do not include explanations or markdown formatting."""


def check_keywords(sql: str, keywords: list[str]) -> tuple[int, int]:
    """Check how many expected keywords appear in the generated SQL."""
    sql_upper = sql.upper()
    found = sum(1 for kw in keywords if kw.upper() in sql_upper)
    return found, len(keywords)


def is_valid_sql(sql: str) -> bool:
    """Basic SQL validity check (not a full parser)."""
    sql_clean = sql.strip().upper()
    return sql_clean.startswith("SELECT") and "FROM" in sql_clean


def run_benchmark(host: str, model: str, runs: int = 3) -> list[BenchmarkResult]:
    """Run the full benchmark suite."""
    results = []

    print(f"\n{'='*70}")
    print(f" Nexus AI LLM Benchmark")
    print(f" Host:  {host}")
    print(f" Model: {model}")
    print(f" Runs:  {runs} (averaging latency)")
    print(f"{'='*70}\n")

    for case in BENCHMARK_CASES:
        prompt = build_prompt(case["question"], case["schema"])
        latencies = []
        best_sql = ""
        error = None

        for run in range(runs):
            try:
                sql, latency = call_ollama(host, model, prompt)
                latencies.append(latency)
                best_sql = sql.strip()
            except Exception as e:
                error = str(e)
                break

        if error:
            results.append(BenchmarkResult(
                case_id=case["id"],
                difficulty=case["difficulty"],
                question=case["question"],
                generated_sql="",
                keywords_found=0,
                keywords_total=len(case["expected_keywords"]),
                keyword_score=0.0,
                latency_ms=0,
                is_valid_sql=False,
                error=error,
            ))
            print(f"  ❌ {case['id']}: ERROR — {error}")
            continue

        found, total = check_keywords(best_sql, case["expected_keywords"])
        avg_latency = sum(latencies) / len(latencies)
        valid = is_valid_sql(best_sql)

        result = BenchmarkResult(
            case_id=case["id"],
            difficulty=case["difficulty"],
            question=case["question"],
            generated_sql=best_sql,
            keywords_found=found,
            keywords_total=total,
            keyword_score=found / total if total > 0 else 0,
            latency_ms=avg_latency,
            is_valid_sql=valid,
        )
        results.append(result)

        status = "✅" if valid and result.keyword_score >= 0.7 else "⚠️" if valid else "❌"
        print(f"  {status} {case['id']:25s} | {case['difficulty']:6s} | "
              f"keywords: {found}/{total} ({result.keyword_score:.0%}) | "
              f"latency: {avg_latency:,.0f}ms | valid: {valid}")

    return results


def print_summary(results: list[BenchmarkResult]):
    """Print benchmark summary."""
    valid = [r for r in results if r.is_valid_sql and not r.error]
    avg_score = sum(r.keyword_score for r in valid) / len(valid) if valid else 0
    avg_latency = sum(r.latency_ms for r in valid) / len(valid) if valid else 0

    print(f"\n{'='*70}")
    print(f" SUMMARY")
    print(f"{'='*70}")
    print(f"  Total cases:     {len(results)}")
    print(f"  Valid SQL:       {len(valid)}/{len(results)} ({len(valid)/len(results):.0%})")
    print(f"  Avg keyword hit: {avg_score:.0%}")
    print(f"  Avg latency:     {avg_latency:,.0f}ms ({avg_latency/1000:.1f}s)")
    print(f"{'='*70}")

    # Verdict
    if avg_score >= 0.8 and len(valid) / len(results) >= 0.8:
        print(f"\n  ✅ VERDICT: Model is READY for production use")
    elif avg_score >= 0.6:
        print(f"\n  ⚠️ VERDICT: Model is ACCEPTABLE but needs prompt tuning")
    else:
        print(f"\n  ❌ VERDICT: Model needs improvement or replacement")


def main():
    parser = argparse.ArgumentParser(description="Benchmark LLM for SQL generation")
    parser.add_argument("--host", default="http://localhost:11434", help="Ollama host URL")
    parser.add_argument("--model", default="nemotron-cascade-2:30b", help="Model name")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs per case (for latency averaging)")
    parser.add_argument("--output", default=None, help="Save results to JSON file")
    args = parser.parse_args()

    results = run_benchmark(args.host, args.model, args.runs)
    print_summary(results)

    if args.output:
        with open(args.output, "w") as f:
            json.dump([{
                "case_id": r.case_id,
                "difficulty": r.difficulty,
                "question": r.question,
                "generated_sql": r.generated_sql,
                "keyword_score": r.keyword_score,
                "latency_ms": r.latency_ms,
                "is_valid_sql": r.is_valid_sql,
                "error": r.error,
            } for r in results], f, indent=2)
        print(f"\n  📄 Results saved to {args.output}")


if __name__ == "__main__":
    main()
