#!/usr/bin/env python3
"""Trend report. See RUBRIC_SOURCES.md for what each metric means / is grounded in.

Headlines, in order of what matters:
  1. PROACTIVITY (driver) + SIGNAL trends — are you driving / clearing the bar, improving?
  2. SELF-ATTACK — per-category blind spots (miss rate) + novel (off-list) trend.
  3. CALIBRATION — self_grade vs actual signal (self-awareness).
  4. CRAFT — solution quality, complexity-stated, code quality; gold-standard count.
  5. Coverage and the revisit queue.

Usage: python3 report.py [--date YYYY-MM-DD]
"""
import argparse
import datetime as dt
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CURRICULUM = os.path.join(HERE, "curriculum.json")
ENTRIES = os.path.join(HERE, "entries.jsonl")

DRIVER_GLYPH = {"candidate": "+", "mixed": "~", "interviewer": "-", "unknown": "?"}
SOLUTION_GLYPH = {"optimal": "*", "solid": "o", "suboptimal": ".",
                  "incorrect": "x", "unsolved": "_"}
DRIVER_SCORE = {"interviewer": 0, "mixed": 1, "candidate": 2}
SIGNAL_SCORE = {"no-hire": 0, "lean-no": 1, "lean-hire": 2, "hire": 3, "strong-hire": 4}
SIGNAL_ORDER = ["no-hire", "lean-no", "lean-hire", "hire", "strong-hire"]
ATTACK_CATEGORIES = {
    "coding": ["boundary", "numeric", "duplicates", "ordering",
               "size-perf", "structure", "concurrency"],
    "design": ["hot-key", "dependency-failure", "cascading", "consistency",
               "latency", "backpressure", "durability", "idempotency",
               "scale-10x", "cost"],
}
MIN_TREND_N = 6


def load_entries():
    out = []
    if os.path.exists(ENTRIES):
        with open(ENTRIES) as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    out.sort(key=lambda e: e["date"])
    return out


def load_curriculum():
    with open(CURRICULUM) as f:
        return json.load(f)


def trend(values):
    if len(values) < MIN_TREND_N:
        return (f"need {MIN_TREND_N}+ ({len(values)} so far)", None, None)
    mid = len(values) // 2
    a = sum(values[:mid]) / mid
    b = sum(values[mid:]) / (len(values) - mid)
    delta = b - a
    lab = "IMPROVING" if delta > 0.25 else "REGRESSING" if delta < -0.25 else "flat"
    return (lab, a, b)


def proactivity_section(entries):
    graded = [e for e in entries if e.get("driver") in DRIVER_SCORE]
    print("PROACTIVITY (driver)  + candidate | ~ mixed | - interviewer   [trained axis]")
    if not graded:
        print("  none recorded yet")
    else:
        print("  oldest -> newest:  " +
              "".join(DRIVER_GLYPH.get(e["driver"], "?") for e in graded))
        lab, a, b = trend([DRIVER_SCORE[e["driver"]] for e in graded])
        print(f"  trend: {lab}" + (f"  ({a:.2f} -> {b:.2f} on 0..2)" if a is not None else ""))

    sig = [e for e in entries if e.get("signal") in SIGNAL_SCORE]
    print("\nSIGNAL (hire-bar)")
    if not sig:
        print("  none recorded yet")
        return
    counts = {}
    for e in sig:
        counts[e["signal"]] = counts.get(e["signal"], 0) + 1
    print("  totals: " + ", ".join(f"{k}={counts[k]}" for k in SIGNAL_ORDER if k in counts))
    lab, a, b = trend([SIGNAL_SCORE[e["signal"]] for e in sig])
    print(f"  trend: {lab}" + (f"  ({a:.2f} -> {b:.2f} on 0=no-hire..4=strong-hire)"
                               if a is not None else ""))


def selfattack_section(entries):
    print("\nSELF-ATTACK BLIND SPOTS  (miss rate per category, where applicable)")
    any_data = False
    for dom in ("coding", "design"):
        rows = []
        for cat in ATTACK_CATEGORIES[dom]:
            applic = miss = 0
            for e in entries:
                if e.get("domain") != dom:
                    continue
                hits, misses = e.get("attack_hits") or [], e.get("attack_misses") or []
                if cat in hits or cat in misses:
                    applic += 1
                    miss += (cat in misses)
            if applic:
                rows.append((miss / applic, miss, applic, cat))
        if rows:
            any_data = True
            rows.sort(reverse=True)
            print(f"  {dom}:")
            for rate, miss, applic, cat in rows:
                print(f"    {cat:<18} {miss}/{applic} missed  {'#' * round(rate*10)} {rate*100:.0f}%")
    if not any_data:
        print("  none recorded yet")

    nov = [e.get("novel_attacks", 0) for e in entries if e.get("attack_hits") is not None]
    if nov:
        lab, a, b = trend([float(x) for x in nov])
        avg = sum(nov) / len(nov)
        print(f"  NOVEL (off-list cases found): avg {avg:.2f}/problem, trend {lab}"
              + (f" ({a:.2f} -> {b:.2f})" if a is not None else ""))
        print("    (the anti-rote metric: real antagonism = cases BEYOND the checklist)")


def calibration_section(entries):
    pairs = [(SIGNAL_SCORE[e["self_grade"]], SIGNAL_SCORE[e["signal"]])
             for e in entries
             if e.get("self_grade") in SIGNAL_SCORE and e.get("signal") in SIGNAL_SCORE]
    print("\nCALIBRATION  (your predicted signal vs actual)")
    if not pairs:
        print("  none recorded yet (set --self-grade to track self-awareness)")
        return
    gap = sum(s - a for s, a in pairs) / len(pairs)
    tendency = ("OVER-confident" if gap > 0.25 else
                "UNDER-confident" if gap < -0.25 else "well-calibrated")
    print(f"  avg gap (self - actual): {gap:+.2f} -> {tendency}  over {len(pairs)} graded")


def craft_section(entries):
    graded = [e for e in entries if e.get("solution")]
    print("\nCRAFT  (* optimal | o solid | . suboptimal | x incorrect | _ unsolved)")
    if not graded:
        print("  none recorded yet")
        return
    print("  solution:  " + "".join(SOLUTION_GLYPH.get(e["solution"], "?") for e in graded))

    def tally(field, skip=("na", None)):
        c = {}
        for e in graded:
            v = e.get(field)
            if v not in skip:
                c[v] = c.get(v, 0) + 1
        return c
    cx, cq = tally("complexity_stated"), tally("code_quality")
    if cx:
        print("  complexity stated: " + ", ".join(f"{k}={v}" for k, v in sorted(cx.items())))
    if cq:
        print("  code quality:      " + ", ".join(f"{k}={v}" for k, v in sorted(cq.items())))
    gold = [e for e in graded if e.get("solution") == "optimal"
            and e.get("aided") == "unaided" and e.get("driver") == "candidate"
            and e.get("scoping") == "strong"]
    print(f"  GOLD STANDARD (optimal + unaided + candidate-driven + scoped): "
          f"{len(gold)}/{len(graded)}")
    for e in graded[-5:]:
        print(f"    {e['date']}  {SOLUTION_GLYPH.get(e['solution'],'?')} {e['solution']:<10}"
              f" diff={e.get('difficulty','?'):<6} signal={e.get('signal','?'):<11}"
              f" pushback={e.get('pushback','?')}")


def coverage_section(curr, entries):
    covered = {e["topic_id"] for e in entries}
    print("\nCURRICULUM COVERAGE")
    for dom in ("coding", "design"):
        nodes = curr[dom]
        done = [n for n in nodes if n["id"] in covered]
        mined = [n for n in nodes if n.get("status") == "mined"]
        print(f"  {dom}: {len(done)}/{len(nodes)} covered"
              + (f"  ({len(mined)} mined)" if mined else ""))
        todo = [n["topic"] for n in nodes
                if n["id"] not in covered and n.get("status") != "mined"]
        if todo:
            print(f"    next up: {', '.join(todo[:5])}" + (" ..." if len(todo) > 5 else ""))


def revisit_section(entries, today):
    latest = {}
    for e in entries:
        tid = e["topic_id"]
        if tid not in latest or e["date"] >= latest[tid]["date"]:
            latest[tid] = e
    rows = sorted((e["revisit_after"], tid, e) for tid, e in latest.items()
                  if e.get("revisit_after"))
    print("\nREVISIT QUEUE")
    if not rows:
        print("  (empty)")
        return
    due = sum(1 for ra, _, _ in rows if ra <= today)
    print(f"  {due} due now / {len(rows)} tracked")
    for ra, tid, e in rows:
        flag = "DUE" if ra <= today else "   "
        print(f"  [{flag}] {ra}  {e.get('domain','?'):<6} {tid}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    args = ap.parse_args()
    today = args.date or dt.date.today().isoformat()
    entries = load_entries()
    curr = load_curriculum()
    print(f"=== PRACTICE REPORT  ({today}) ===  {len(entries)} problems logged\n")
    proactivity_section(entries)
    selfattack_section(entries)
    calibration_section(entries)
    craft_section(entries)
    coverage_section(curr, entries)
    revisit_section(entries, today)


if __name__ == "__main__":
    main()
