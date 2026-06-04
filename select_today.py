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

HERE = os.path.dirname(os.path.abspath(__file__))
CURRICULUM = os.path.join(HERE, "curriculum.json")
ENTRIES = os.path.join(HERE, "entries.jsonl")

LEVELS = ["easy", "medium", "hard"]
CHECKLISTS = {
    "coding": "boundary / numeric / duplicates / ordering / size-perf / structure / [concurrency]",
    "design": ("hot-key / dependency-failure / cascading / consistency / latency / "
               "backpressure / durability / idempotency / scale-10x / cost"),
}


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
            if line:
                entries.append(json.loads(line))
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
    """Return (ordered list of picks, overdue_revisit_count) for one domain."""
    covered = set(latest.keys())
    picks = []

    overdue = sorted(
        (latest[n["id"]]["revisit_after"], n["id"]) for n in nodes
        if n.get("status") != "mined" and n["id"] in covered
        and latest[n["id"]].get("revisit_after")
        and latest[n["id"]]["revisit_after"] <= today
    )
    for _, tid in overdue:
        node = next(n for n in nodes if n["id"] == tid)
        picks.append({"kind": "revisit", "node": node, "prior": latest[tid]})

    for n in nodes:  # new topics, curriculum order
        if n.get("status") != "mined" and n["id"] not in covered:
            picks.append({"kind": "new", "node": n, "prior": None})

    seen = {p["node"]["id"] for p in picks}
    fallback = sorted((latest[n["id"]]["date"], n["id"]) for n in nodes
                      if n.get("status") != "mined" and n["id"] in covered
                      and n["id"] not in seen)
    for _, tid in fallback:
        node = next(n for n in nodes if n["id"] == tid)
        picks.append({"kind": "revisit", "node": node, "prior": latest[tid]})

    return picks, len(overdue)


def render(domain, pick, history):
    node = pick["node"]
    tag = "REVISIT" if pick["kind"] == "revisit" else "NEW"
    diff = target_difficulty(pick["prior"])
    lines = [f"  {domain.upper()}  [{tag}]  {node['topic']}  (id: {node['id']})",
             f"    target difficulty: {diff.upper()}"]
    if pick["kind"] == "revisit":
        p = pick["prior"]
        lines.append(f"    last seen {p['date']} | {entry_class(p)} pass | "
                     f"driver {p.get('driver','?')} | signal {p.get('signal','?')} | "
                     f"was {p.get('difficulty','?')}")
        if p.get("drill"):
            lines.append(f"    >> LAST DRILL (prove you fixed it): {p['drill']}")
        if p.get("notes"):
            lines.append(f"    prior notes: {p['notes']}")
    past = history.get(node["id"], [])
    if past:
        lines.append(f"    PAST PROBLEMS ({len(past)}) — do NOT repeat; make the new one materially different:")
        for q in past[-6:]:
            lines.append(f"      - [{q['date']}] {q['problem']}")
        if len(past) > 6:
            lines.append(f"      ... and {len(past) - 6} earlier")
    lines.append(f"    self-attack checklist (floor, not ceiling): {CHECKLISTS[domain]}")
    return "\n".join(lines)


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
    chosen, overdue = {}, {}
    for dom in ("coding", "design"):
        picks, n_over = ranked_picks(curr[dom], latest, today)
        chosen[dom] = picks[:counts[dom]]
        overdue[dom] = n_over

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

    print(f"=== TODAY'S PICKS  ({today}) ===")
    for dom in ("coding", "design"):
        if counts[dom] == 0:
            continue
        extra = ""
        if overdue[dom] > len(chosen[dom]):
            extra = f"   (catch-up: {overdue[dom]} {dom} revisits overdue; showing {len(chosen[dom])})"
        if extra:
            print(extra.strip())
        for p in chosen[dom]:
            print(render(dom, p, history))
    print("\nFlipped protocol: candidate scopes/clarifies FIRST -> solves out loud -> "
          "candidate's OWN teardown (find cases BEYOND the checklist) -> agent grades. "
          "Do NOT list the gaps before the self-attack.")


if __name__ == "__main__":
    main()
