"""Replay tests.json against POST /chat and print a pass-rate table.
Usage:  python benchmark/run_benchmark.py http://localhost:7860 [--only T01,T04] [--no-fresh]
Fresh mode (default) appends a run suffix to user_id/thread_id so reruns start clean.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def check(expect: dict, reply: str, tools: list) -> list[str]:
    fails = []
    names = [t["name"] for t in tools]
    low = reply.lower()
    for t in expect.get("tools_called", []):
        if t not in names:
            fails.append(f"tool not called: {t}")
    any_of = expect.get("tools_called_any")
    if any_of and not any(t in names for t in any_of):
        fails.append(f"none of tools called: {any_of}")
    for t in expect.get("tools_not_called", []):
        if t in names:
            fails.append(f"tool should NOT be called: {t}")
    must = expect.get("reply_contains_any")
    if must and not any(c.lower() in low for c in must):
        fails.append(f"reply lacks any of {must}")
    for c in expect.get("reply_not_contains", []):
        if c.lower() in low:
            fails.append(f"reply contains forbidden '{c}'")
    return fails


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("base_url")
    ap.add_argument("--only", default="")
    ap.add_argument("--no-fresh", action="store_true")
    args = ap.parse_args()
    base = args.base_url.rstrip("/")
    suffix = "" if args.no_fresh else f"_{int(time.time()) % 100000}"
    only = {x.strip() for x in args.only.split(",") if x.strip()}

    spec = json.loads((ROOT / "tests.json").read_text(encoding="utf-8"))
    client = httpx.Client(timeout=90)
    try:
        h = client.get(f"{base}/health")
        print(f"health: {h.status_code} {h.text.strip()}")
    except Exception as e:
        sys.exit(f"cannot reach {base}: {e}")

    rows, passed, total_in, total_out = [], 0, 0, 0
    tests = [t for t in spec["tests"] if not only or t["id"] in only]
    for t in tests:
        fails, lat, tin, tout, last = [], 0, 0, 0, None
        for i, turn in enumerate(t["turns"], start=1):
            body = {
                "user_id": turn["user_id"] + suffix,
                "thread_id": turn["thread_id"] + suffix,
                "message": turn["message"],
            }
            t0 = time.time()
            try:
                r = client.post(f"{base}/chat", json=body)
                data = r.json()
            except Exception as e:
                fails.append(f"turn {i}: request failed {e}")
                break
            lat += int((time.time() - t0) * 1000)
            tin += data.get("tokens", {}).get("in", 0)
            tout += data.get("tokens", {}).get("out", 0)
            last = data
            for te in t["expect"].get("turn_expectations", []):
                if te["turn"] == i:
                    fails += [f"turn {i}: {f}" for f in check(te, data["reply"], data["tool_calls"])]
        if last is not None:
            top = {k: v for k, v in t["expect"].items() if k not in ("turn_expectations", "behaviour")}
            fails += check(top, last["reply"], last["tool_calls"])
        ok = not fails
        passed += ok
        total_in += tin
        total_out += tout
        rows.append((t["id"], t["name"], t["category"], "PASS" if ok else "FAIL", lat, tin, tout, "; ".join(fails), (last or {}).get("reply", "")))
        print(f"{t['id']} {'PASS' if ok else 'FAIL'}  {lat} ms  {tin}/{tout} tok  {'; '.join(fails)}")

    lines = [
        "| Test | Category | Result | Latency (ms) | Tokens in/out |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r[0]} {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]}/{r[6]} |")
    lines.append("")
    lines.append(f"Pass rate: {passed}/{len(rows)}  |  total tokens in/out: {total_in}/{total_out}")
    table = "\n".join(lines)
    print("\n" + table)
    out = Path(__file__).resolve().parent
    (out / "results.md").write_text(table + "\n", encoding="utf-8")
    (out / "results.json").write_text(json.dumps([dict(zip(["id", "name", "category", "result", "latency_ms", "tokens_in", "tokens_out", "fails", "last_reply"], r)) for r in rows], indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
