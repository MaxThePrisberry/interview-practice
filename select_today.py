#!/usr/bin/env python3
"""Deterministically pick today's practice problems.

Selection is computed here, NOT by the agent eyeballing the ledger, so coverage,
spaced-repetition, and difficulty escalation stay auditable and tamper-proof.

Volume is a parameter (variable cadence):
  --coding N --design N   how many of each to surface (default 1 each; 0 to skip a domain)

Priority per domain: most-overdue REVISITS first, then NEW topics (curriculum order),
then least-recently-seen fallback; deduped within the batch. When many revisits are
overdue, the count is surfaced instead of flooding (catch-up).

Difficulty AUTO-ESCALATES: strong pass steps the next target up (easy->medium->hard),
a fail steps it down, a weak pass holds. New topics start at medium. The last 'drill'
for a revisited topic is surfaced so feedback gets acted on.

Usage:
  python3 select_today.py [--coding N] [--design N] [--date YYYY-MM-DD] [--json]
"""
import argparse
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CURRICULUM = os.path.join(HERE, "curriculum.json")
ENTRIES = os.path.join(HERE, "entries.jsonl")

LEVELS = ["easy", "medium", "hard"]


def load_curriculum():
    with open(CURRICULUM) as f:
        data = json.load(f)
    return {"coding": data["coding"], "design": data["design"]}


def load_entries():
    entries = []
    if not os.path.exists(ENTRIES):
        return entries
    with open(ENTRIES) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"warning: skipping malformed entries.jsonl line: {line[:60]!r}",
                      file=sys.stderr)
    return entries


def latest_by_topic(entries):
    latest = {}
    for e in entries:
        tid = e["topic_id"]
        if tid not in latest or e["date"] >= latest[tid]["date"]:
            latest[tid] = e
    return latest


def problems_by_topic(entries):
    """topic_id -> chronological list of {date, problem} so the agent can avoid repeats."""
    hist = {}
    for e in sorted(entries, key=lambda x: x["date"]):
        hist.setdefault(e["topic_id"], []).append(
            {"date": e["date"], "problem": e.get("problem", "")})
    return hist


def entry_class(e):
    cls = e.get("pass_class")
    if cls:
        return cls
    if e.get("verdict") == "revisit":
        return "fail"
    return "strong"


def target_difficulty(prior):
    if not prior:
        return "medium"
    last = prior.get("difficulty") or "medium"
    i = LEVELS.index(last) if last in LEVELS else 1
    cls = entry_class(prior)
    if cls == "strong":
        i = min(i + 1, len(LEVELS) - 1)
    elif cls == "fail":
        i = max(i - 1, 0)
    return LEVELS[i]


def ranked_picks(nodes, latest, today):
    """Return per-domain pools: overdue revisits, new topics, and fallback revisits."""
    covered = set(latest.keys())
    by_id = {n["id"]: n for n in nodes}

    overdue = sorted(
        (latest[n["id"]]["revisit_after"], n["id"]) for n in nodes
        if n.get("status") != "mined" and n["id"] in covered
        and latest[n["id"]].get("revisit_after")
        and latest[n["id"]]["revisit_after"] <= today
    )
    revisits = [{"kind": "revisit", "node": by_id[tid], "prior": latest[tid]}
                for _, tid in overdue]

    new = [{"kind": "new", "node": n, "prior": None} for n in nodes
           if n.get("status") != "mined" and n["id"] not in covered]

    seen = {p["node"]["id"] for p in revisits} | {p["node"]["id"] for p in new}
    fallback = [{"kind": "revisit", "node": by_id[tid], "prior": latest[tid]}
                for _, tid in sorted((latest[n["id"]]["date"], n["id"]) for n in nodes
                                     if n.get("status") != "mined" and n["id"] in covered
                                     and n["id"] not in seen)]

    return {"revisits": revisits, "new": new, "fallback": fallback,
            "overdue": len(overdue)}


def compose(pools, n, new_first):
    """Interleave revisits and new topics so new coverage never starves behind a
    revisit backlog. `new_first` (date parity) alternates who leads, so the single-
    problem-per-day case splits over time instead of always serving a revisit."""
    rev, new, fb = list(pools["revisits"]), list(pools["new"]), list(pools["fallback"])
    out, take_new = [], new_first
    while len(out) < n and (rev or new):
        if take_new and new:
            out.append(new.pop(0))
        elif not take_new and rev:
            out.append(rev.pop(0))
        elif new:
            out.append(new.pop(0))
        elif rev:
            out.append(rev.pop(0))
        take_new = not take_new
    while len(out) < n and fb:   # only if revisits+new are exhausted
        out.append(fb.pop(0))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coding", type=int, default=1, help="how many coding problems (0 to skip)")
    ap.add_argument("--design", type=int, default=1, help="how many design problems (0 to skip)")
    ap.add_argument("--date", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    today = args.date or dt.date.today().isoformat()
    curr = load_curriculum()
    entries = load_entries()
    latest = latest_by_topic(entries)
    history = problems_by_topic(entries)

    counts = {"coding": max(0, args.coding), "design": max(0, args.design)}
    new_first = dt.date.fromisoformat(today).toordinal() % 2 == 0
    chosen, overdue = {}, {}
    for dom in ("coding", "design"):
        pools = ranked_picks(curr[dom], latest, today)
        chosen[dom] = compose(pools, counts[dom], new_first)
        overdue[dom] = pools["overdue"]

    if args.json:
        def slim(p):
            return {"kind": p["kind"], "id": p["node"]["id"], "topic": p["node"]["topic"],
                    "target_difficulty": target_difficulty(p["prior"]),
                    "last_drill": (p["prior"] or {}).get("drill"), "prior": p["prior"],
                    "past_problems": [q["problem"] for q in history.get(p["node"]["id"], [])]}
        print(json.dumps({"date": today,
                          "coding": [slim(p) for p in chosen["coding"]],
                          "design": [slim(p) for p in chosen["design"]],
                          "overdue": overdue}, indent=2))
        return

    # CANDIDATE-SAFE output: difficulty only. The topic/technique, checklist, past
    # problems, and prior performance are deliberately withheld — recognizing the pattern
    # and generating the edge cases is part of what's being tested. Interviewer uses --json.
    print(f"=== TODAY ({today}) ===")
    for dom in ("coding", "design"):
        if counts[dom] == 0:
            continue
        picks = chosen[dom]
        if not picks:
            print(f"  {dom}: (no eligible topic — check curriculum.json)")
            continue
        diffs = ", ".join(target_difficulty(p["prior"]).upper() for p in picks)
        print(f"  {dom.upper()}: {len(picks)} problem(s) — difficulty: {diffs}")
        if overdue[dom] > len(picks):
            print(f"    (catch-up: {overdue[dom]} {dom} revisits overdue)")
    print("\nInterviewer: run with --json for topic/past-problems and run the flipped protocol.")
    print("Do NOT reveal the topic, technique, self-attack checklist, or past problems to the")
    print("candidate — recognizing the pattern is part of the test. Pose ONLY the problem.")


if __name__ == "__main__":
    main()
