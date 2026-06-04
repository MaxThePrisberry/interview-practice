#!/usr/bin/env python3
"""Append ONE validated entry to entries.jsonl (append-only; never clobbers history).

Metrics are grounded in published rubrics — see RUBRIC_SOURCES.md for what is
[standard] vs [bespoke]. Axes the senior bar grades, kept orthogonal:
  WHAT:  solution (optimality) + aided (help) + complexity_stated + code_quality
  HOW:   scoping (clarified up front) + driver (who surfaced rigor) +
         structured self-attack (hit/missed vs the reference taxonomy) +
         novel_attacks (off-list cases found -> genuine antagonism, anti-Goodhart) +
         pushback (held ground when probed)
  META:  signal (hire-bar) + self_grade (your predicted signal -> calibration) +
         difficulty (context).

Quality-aware spaced repetition (Moderate profile):
  fail   -> 3d       (incorrect/unsolved, bottom signal, or --verdict revisit)
  weak   -> hold     max(7, prior)  (reactive: interviewer-driven, no scoping, hinted/
                     given, suboptimal, no/wrong complexity, or messy code)
  strong -> double   max(7, prior*2)
"""
import argparse
import datetime as dt
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CURRICULUM = os.path.join(HERE, "curriculum.json")
ENTRIES = os.path.join(HERE, "entries.jsonl")

VALID_DOMAINS = {"coding", "design"}
VALID_DIFFICULTY = {"easy", "medium", "hard"}
VALID_SCOPING = {"strong", "partial", "none"}
VALID_DRIVERS = {"candidate", "mixed", "interviewer", "unknown"}
VALID_SOLUTIONS = {"optimal", "solid", "suboptimal", "incorrect", "unsolved"}
VALID_AIDED = {"unaided", "nudged", "hinted", "given", "unknown"}
VALID_COMPLEXITY = {"yes", "prompted", "wrong", "no", "na"}  # stated Big-O unprompted?
VALID_CODE_QUALITY = {"clean", "adequate", "messy", "na"}
VALID_PUSHBACK = {"held", "folded_correctly", "caved", "doubled_down", "na"}
VALID_SIGNAL = {"no-hire", "lean-no", "lean-hire", "hire", "strong-hire"}
VALID_SELF_GRADE = VALID_SIGNAL | {"unknown"}
VALID_VERDICT = {"pass", "revisit"}

# Grounded reference taxonomy (RUBRIC_SOURCES.md). The FLOOR, not the ceiling:
# off-list cases are counted via --novel. Items not in --hit/--missed are N/A.
ATTACK_CATEGORIES = {
    "coding": {"boundary", "numeric", "duplicates", "ordering",
               "size-perf", "structure", "concurrency"},
    "design": {"hot-key", "dependency-failure", "cascading", "consistency",
               "latency", "backpressure", "durability", "idempotency",
               "scale-10x", "cost"},
}

FAIL_SIGNALS = {"no-hire", "lean-no"}


def valid_topic_ids():
    with open(CURRICULUM) as f:
        data = json.load(f)
    return {n["id"] for dom in ("coding", "design") for n in data[dom]}


def prior_interval(topic_id):
    if not os.path.exists(ENTRIES):
        return 0
    latest_date, interval = None, 0
    with open(ENTRIES) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            if e["topic_id"] == topic_id and (latest_date is None or e["date"] >= latest_date):
                latest_date = e["date"]
                interval = e.get("interval_days", 0) or 0
    return interval


def classify(solution, signal, driver, scoping, aided, complexity, code_quality, verdict):
    if verdict == "revisit":
        return "fail"
    if solution in {"incorrect", "unsolved"} or signal in FAIL_SIGNALS:
        return "fail"
    weak = (driver == "interviewer" or scoping == "none"
            or aided in {"hinted", "given"} or solution == "suboptimal"
            or complexity in {"no", "wrong"} or code_quality == "messy")
    return "weak" if weak else "strong"


def schedule(cls, prior):
    if cls == "fail":
        return 3
    if cls == "weak":
        return max(7, prior)
    return max(7, prior * 2)


def parse_categories(raw, domain, label):
    if not raw:
        return []
    items = [x.strip() for x in raw.split(",") if x.strip()]
    allowed = ATTACK_CATEGORIES[domain]
    bad = [x for x in items if x not in allowed]
    if bad:
        raise SystemExit(f"--{label} has unknown {domain} categories {bad}; "
                         f"allowed: {sorted(allowed)}")
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True)
    ap.add_argument("--topic", required=True, help="curriculum topic id")
    ap.add_argument("--difficulty", required=True, help="easy|medium|hard")
    ap.add_argument("--problem", required=True,
                    help="1-2 sentence statement of the problem AS POSED (drives repeat-avoidance)")
    ap.add_argument("--scoping", required=True, help="clarified up front? strong|partial|none")
    ap.add_argument("--driver", default="unknown")
    ap.add_argument("--hit", default="", help="reference self-attack categories CAUGHT (comma list)")
    ap.add_argument("--missed", default="", help="reference categories MISSED (comma list)")
    ap.add_argument("--novel", type=int, default=0, help="count of relevant OFF-LIST cases found")
    ap.add_argument("--solution", required=True,
                    help="optimal|solid|suboptimal|incorrect|unsolved")
    ap.add_argument("--aided", default="unknown", help="unaided|nudged|hinted|given")
    ap.add_argument("--complexity", default="na",
                    help="stated Big-O unprompted? yes|prompted|wrong|no|na")
    ap.add_argument("--code-quality", dest="code_quality", default="na",
                    help="clean|adequate|messy|na")
    ap.add_argument("--pushback", default="na",
                    help="held|folded_correctly|caved|doubled_down|na")
    ap.add_argument("--signal", required=True,
                    help="no-hire|lean-no|lean-hire|hire|strong-hire")
    ap.add_argument("--self-grade", dest="self_grade", default="unknown",
                    help="candidate's OWN predicted signal (before reveal) -> calibration")
    ap.add_argument("--drill", default="", help="the ONE thing to drill next time")
    ap.add_argument("--verdict", default=None, help="optional override: 'revisit' forces a soon revisit")
    ap.add_argument("--notes", default="")
    ap.add_argument("--date", default=None)
    args = ap.parse_args()

    checks = [
        ("--domain", args.domain, VALID_DOMAINS),
        ("--difficulty", args.difficulty, VALID_DIFFICULTY),
        ("--scoping", args.scoping, VALID_SCOPING),
        ("--driver", args.driver, VALID_DRIVERS),
        ("--solution", args.solution, VALID_SOLUTIONS),
        ("--aided", args.aided, VALID_AIDED),
        ("--complexity", args.complexity, VALID_COMPLEXITY),
        ("--code-quality", args.code_quality, VALID_CODE_QUALITY),
        ("--pushback", args.pushback, VALID_PUSHBACK),
        ("--signal", args.signal, VALID_SIGNAL),
        ("--self-grade", args.self_grade, VALID_SELF_GRADE),
    ]
    for flag, val, allowed in checks:
        if val not in allowed:
            raise SystemExit(f"{flag} must be one of {sorted(allowed)}")
    if args.verdict is not None and args.verdict not in VALID_VERDICT:
        raise SystemExit(f"--verdict must be one of {sorted(VALID_VERDICT)}")
    if args.novel < 0:
        raise SystemExit("--novel must be >= 0")
    if args.topic not in valid_topic_ids():
        raise SystemExit(f"unknown topic id {args.topic!r}; add it to curriculum.json first")

    hits = parse_categories(args.hit, args.domain, "hit")
    missed = parse_categories(args.missed, args.domain, "missed")
    overlap = set(hits) & set(missed)
    if overlap:
        raise SystemExit(f"categories in both --hit and --missed: {sorted(overlap)}")
    coverage = f"{len(hits)}/{len(hits) + len(missed)}" if (hits or missed) else None

    date = args.date or dt.date.today().isoformat()
    dt.date.fromisoformat(date)

    cls = classify(args.solution, args.signal, args.driver, args.scoping,
                   args.aided, args.complexity, args.code_quality, args.verdict)
    interval = schedule(cls, prior_interval(args.topic))
    revisit_after = (dt.date.fromisoformat(date) + dt.timedelta(days=interval)).isoformat()

    entry = {
        "date": date,
        "domain": args.domain,
        "topic_id": args.topic,
        "difficulty": args.difficulty,
        "problem": args.problem,
        "scoping": args.scoping,
        "driver": args.driver,
        "attack_hits": hits,
        "attack_misses": missed,
        "novel_attacks": args.novel,
        "self_attack_coverage": coverage,
        "solution": args.solution,
        "aided": args.aided,
        "complexity_stated": args.complexity,
        "code_quality": args.code_quality,
        "pushback": args.pushback,
        "signal": args.signal,
        "self_grade": args.self_grade,
        "pass_class": cls,
        "verdict": args.verdict,
        "drill": args.drill,
        "interval_days": interval,
        "revisit_after": revisit_after,
        "notes": args.notes,
    }
    with open(ENTRIES, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"logged: {date} {args.domain}/{args.topic} [{args.difficulty}] -> {cls} pass, "
          f"signal={args.signal}, novel={args.novel}; next revisit {revisit_after} (in {interval}d)")


if __name__ == "__main__":
    main()
