#!/usr/bin/env python3
"""Run an eval set against two Claude models and emit a before/after diff.

Anthropic-native: uses the Messages API (and Message Batches for large sets). Scores
each case with its declared grader and reports per-case pass/fail for both models
plus aggregate pass rate, tokens, latency, and estimated cost.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python run_eval_comparison.py evals.json \
        --old claude-sonnet-4-5 --new claude-opus-4-8 \
        --system system_prompt.txt \
        --out diff.json

Eval file: a JSON list of cases (see references/running-experiments.md):
    [{"id": "...", "input": "...", "expected": "...", "grader": "contains",
      "metadata": {"slice": "...", "severity": "high"}}]
  `input` may be a string (becomes a single user turn) or a messages array.

Graders: exact | contains | json_match | tool_call | rubric
  rubric grading uses an LLM judge (--judge-model, default = claude-opus-4-8, the
  strongest judge) and expects `expected` to hold the rubric text.

This is a starting point, intentionally hackable — adjust graders, batching, and the
price table to fit the actual setup.
"""

import argparse
import json
import os
import sys
import time
from statistics import mean

try:
    from anthropic import Anthropic
except ImportError:
    sys.exit("Missing dependency: pip install anthropic")

# Per-million-token prices (USD). Verify against the live pricing page during phase 2
# and override with --prices price_table.json if these are stale.
DEFAULT_PRICES = {
    "claude-opus-4-8": {"in": 5.0, "out": 25.0},
    "claude-sonnet-4-6": {"in": 3.0, "out": 15.0},
    "claude-sonnet-4-5": {"in": 3.0, "out": 15.0},
    "claude-haiku-4-5-20251001": {"in": 1.0, "out": 5.0},
}


def load_json(path):
    with open(path) as f:
        return json.load(f)


def as_messages(case_input):
    if isinstance(case_input, list):
        return case_input
    return [{"role": "user", "content": str(case_input)}]


def run_case(client, model, system, case, max_tokens):
    """Run one case; return (text, tool_uses, usage, latency_s)."""
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": as_messages(case["input"]),
    }
    if system:
        kwargs["system"] = system
    start = time.time()
    resp = client.messages.create(**kwargs)
    latency = time.time() - start
    text = "".join(b.text for b in resp.content if b.type == "text")
    tool_uses = [
        {"name": b.name, "input": b.input} for b in resp.content if b.type == "tool_use"
    ]
    usage = {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens}
    return text, tool_uses, usage, latency


def grade(case, text, tool_uses, client, judge_model):
    """Return (passed: bool, note: str)."""
    grader = case.get("grader", "contains")
    expected = case.get("expected", "")

    if grader == "exact":
        return text.strip() == str(expected).strip(), "exact match"
    if grader == "contains":
        ok = str(expected).lower() in text.lower()
        return ok, f"contains '{expected}'"
    if grader == "json_match":
        try:
            got = json.loads(text)
        except json.JSONDecodeError:
            return False, "output was not valid JSON"
        want = expected if isinstance(expected, dict) else json.loads(expected)
        missing = {k: v for k, v in want.items() if got.get(k) != v}
        return (not missing), ("all fields match" if not missing else f"mismatch: {missing}")
    if grader == "tool_call":
        # expected: {"name": "...", "input": {optional subset of args}}
        want = expected if isinstance(expected, dict) else json.loads(expected)
        for tu in tool_uses:
            if tu["name"] == want.get("name"):
                want_args = want.get("input", {})
                if all(tu["input"].get(k) == v for k, v in want_args.items()):
                    return True, f"called {tu['name']} correctly"
        return False, f"expected tool call {want.get('name')} not found"
    if grader == "rubric":
        return rubric_grade(client, judge_model, case, text)
    return False, f"unknown grader '{grader}'"


def rubric_grade(client, judge_model, case, text):
    prompt = (
        "You are grading a model output against a rubric. Respond with a JSON object "
        '{"pass": true|false, "reason": "..."}.\n\n'
        f"RUBRIC:\n{case.get('expected', '')}\n\n"
        f"INPUT:\n{json.dumps(case['input'])[:2000]}\n\n"
        f"OUTPUT:\n{text[:4000]}"
    )
    resp = client.messages.create(
        model=judge_model,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = "".join(b.text for b in resp.content if b.type == "text")
    try:
        start, end = raw.find("{"), raw.rfind("}") + 1
        verdict = json.loads(raw[start:end])
        return bool(verdict.get("pass")), verdict.get("reason", "")
    except (json.JSONDecodeError, ValueError):
        return False, f"judge returned unparseable verdict: {raw[:200]}"


def cost(usage, model, prices):
    p = prices.get(model)
    if not p:
        return None
    return usage["in"] / 1e6 * p["in"] + usage["out"] / 1e6 * p["out"]


def run_model(client, model, system, cases, max_tokens, judge_model, prices):
    results = []
    for case in cases:
        try:
            text, tool_uses, usage, latency = run_case(
                client, model, system, case, max_tokens
            )
            passed, note = grade(case, text, tool_uses, client, judge_model)
            results.append(
                {
                    "id": case.get("id"),
                    "slice": case.get("metadata", {}).get("slice"),
                    "passed": passed,
                    "note": note,
                    "tokens": usage,
                    "latency_s": round(latency, 2),
                    "cost_usd": cost(usage, model, prices),
                }
            )
        except Exception as e:  # keep the run going; record the failure
            results.append({"id": case.get("id"), "passed": False, "note": f"ERROR: {e}"})
        print(f"  [{model}] {case.get('id')}: {'PASS' if results[-1].get('passed') else 'FAIL'}")
    return results


def summarize(results):
    graded = [r for r in results if "passed" in r]
    costs = [r["cost_usd"] for r in results if r.get("cost_usd") is not None]
    lats = [r["latency_s"] for r in results if r.get("latency_s") is not None]
    return {
        "n": len(graded),
        "pass_rate": round(sum(r["passed"] for r in graded) / max(len(graded), 1), 4),
        "avg_cost_usd": round(mean(costs), 6) if costs else None,
        "total_cost_usd": round(sum(costs), 6) if costs else None,
        "avg_latency_s": round(mean(lats), 2) if lats else None,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("evals", help="path to eval JSON file")
    ap.add_argument("--old", required=True, help="current model ID")
    ap.add_argument("--new", required=True, help="target model ID")
    ap.add_argument("--system", help="path to system prompt file (optional)")
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--judge-model", default="claude-opus-4-8",
                    help="model for rubric grading (default: claude-opus-4-8, the strongest judge)")
    ap.add_argument("--prices", help="optional JSON price table override")
    ap.add_argument("--out", default="diff.json", help="output diff path")
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY in the environment.")

    cases = load_json(args.evals)
    system = open(args.system).read() if args.system else None
    prices = {**DEFAULT_PRICES, **(load_json(args.prices) if args.prices else {})}
    judge_model = args.judge_model
    client = Anthropic()

    print(f"Running {len(cases)} cases against OLD={args.old}")
    old = run_model(client, args.old, system, cases, args.max_tokens, judge_model, prices)
    print(f"Running {len(cases)} cases against NEW={args.new}")
    new = run_model(client, args.new, system, cases, args.max_tokens, judge_model, prices)

    old_by_id = {r["id"]: r for r in old}
    regressions, improvements = [], []
    for r in new:
        o = old_by_id.get(r["id"], {})
        if o.get("passed") and not r.get("passed"):
            regressions.append(r["id"])
        elif not o.get("passed") and r.get("passed"):
            improvements.append(r["id"])

    diff = {
        "old_model": args.old,
        "new_model": args.new,
        "summary": {"old": summarize(old), "new": summarize(new)},
        "regressions": regressions,
        "improvements": improvements,
        "per_case": {"old": old, "new": new},
    }
    with open(args.out, "w") as f:
        json.dump(diff, f, indent=2)

    so, sn = diff["summary"]["old"], diff["summary"]["new"]
    print("\n" + "=" * 60)
    print(f"OLD {args.old}: pass {so['pass_rate']:.1%}  "
          f"${so['total_cost_usd']}  {so['avg_latency_s']}s avg")
    print(f"NEW {args.new}: pass {sn['pass_rate']:.1%}  "
          f"${sn['total_cost_usd']}  {sn['avg_latency_s']}s avg")
    print(f"Regressions (passed→failed): {regressions or 'none'}")
    print(f"Improvements (failed→passed): {improvements or 'none'}")
    print(f"\nFull diff written to {args.out}")


if __name__ == "__main__":
    main()
