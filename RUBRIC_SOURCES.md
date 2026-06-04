# Rubric Sources — what's grounded vs. user-tuned

This system's metrics are built from published interview rubrics, not invented. This
file records the sources and labels each metric **[standard]** (a recognized rubric
dimension), **[calibration]** (a standard input, usually a note rather than a graded
axis), or **[bespoke]** (a construct of this build, oriented toward the training focus in
`profile.md`; this build is geared to **proactive rigor**). Audit and challenge freely.

## Coding interview — standard axes
Four axes recur across FAANG rubrics (Tech Interview Handbook; Google via Exponent/Quora;
interviewing.io):
1. **Communication** — clarifying questions; narrating approach and tradeoffs.
2. **Problem-solving** — understanding, sound approach, multiple approaches, tradeoff
   analysis, optimization (incl. **complexity analysis**, stated aloud).
3. **Technical competency / coding** — speed + accuracy; **code clarity/quality**.
4. **Testing / verification** — exercising common + corner cases; proving invariants;
   tracing boundaries.

## Coding edge-case taxonomy (grounded, broader than the seed's 5)
From Beyz "30 edge cases", AlgoCademy, LeetCopilot. Grouped:
- **boundary** — empty, single, two-element, off-by-one, index/limit bounds, incl/excl.
- **numeric** — negatives, zero, overflow / very large, INT_MIN/MAX sentinels.
- **duplicates** — all-identical, clustered, at start/end, key overwrite, missing-key.
- **ordering** — pre-sorted, reverse-sorted, nearly-sorted, adversarial/alternating.
- **size-perf** — max input (TLE), recursion depth, memory growth.
- **structure** — graph/tree/string shape: cycles, disconnected, null nodes, skew,
  whitespace/separators/unicode, empty tokens.
- **concurrency** — ONLY when the problem is explicitly concurrent (not universal).

## System design — standard axes
Alex Xu (Insider's Guide), DesignGurus, interviewing.io:
requirements clarification → high-level design (data/API/components) → deep-dive depth
(sharding, caching, LB) → tradeoffs & judgment under ambiguity → scalability & bottlenecks
(stress test, 10x) → operational maturity / graceful failure handling → **cost reasoning**
(2026 addition) → communication.

## System design failure-mode taxonomy (the design "self-attack")
"Stress test the design" = enumerate failure modes (Xu + DDIA + SRE patterns):
- **hot-key** — hot key/shard, skew.
- **dependency-failure** — each dependency fails; fail-open vs fail-closed; SPOF.
- **cascading** — retry storms, thundering herd, cascading failure.
- **consistency** — partition/CAP, split-brain, replication lag, stale reads.
- **latency** — tail latency on the hot path.
- **backpressure** — overload, rate limiting, unbounded queue growth.
- **durability** — data loss, replication, backups.
- **idempotency** — dedup, exactly-once, safe retries.
- **scale-10x** — 10x load/data growth.
- **cost** — cost blowup at scale.

## Hire signal — standard
Google uses a 7-point scale: Strong No-Hire, No-Hire, Lean No-Hire, On-the-fence, Lean
Hire, Hire, Strong Hire (Tech Interview Handbook; interviewing.io). We use a 5-point
collapse: `no-hire | lean-no | lean-hire | hire | strong-hire`. Senior target = `hire`+.

## How each of our metrics is grounded
- `scoping` **[standard]** — requirements clarification (both domains).
- `solution` **[standard]** — problem-solving + technical competency (optimality).
- `complexity_stated` **[standard]** — complexity analysis, valued when *unprompted*.
- `code_quality` **[standard]** — code clarity (coding domain).
- `attack_hits/misses` + `novel_attacks` **[standard core, bespoke extension]** —
  testing/verification (coding) and failure-mode stress-test (design). The reference
  taxonomy is the floor; `novel_attacks` rewards relevant cases NOT on the list, so we
  measure genuine antagonism rather than rote recital (anti-Goodhart).
- `aided` **[calibration]** — hints needed; a standard debrief input.
- `difficulty` **[calibration]** — leveling context for every other metric.
- `signal` **[standard]** — the hire-bar verdict; the actual debrief output.
- `self_grade` **[bespoke, principled]** — candidate predicts own signal first; the gap
  measures self-awareness — a numeric proxy for the reactive→proactive axis.
- `driver` **[bespoke]** — who surfaced the rigor. Not an off-the-shelf per-interview
  metric; maps to the *leveling* axis "operates independently." Kept because it targets
  this build's proactive-rigor focus.
- `pushback` **[bespoke]** — resilience when a correct answer is probed. Maps loosely to
  "receptiveness/conviction" in soft-skill rubrics; kept as a targeted signal.

## Deliberately omitted
- **Communication** — the most-weighted standard axis — is intentionally NOT a graded
  field: this practice is typed (typing < talking), which would distort it. It is
  partially absorbed by `signal`. Revisit if sessions move to voice.

## Sources
- [Tech Interview Handbook — coding rubrics](https://www.techinterviewhandbook.org/coding-interview-rubrics/)
- [Exponent — Google coding interview rubric](https://www.tryexponent.com/blog/google-coding-interview-rubric)
- [Beyz — coding edge cases to say out loud](https://beyz.ai/blog/coding-interview-edge-cases-30-to-say-out-loud)
- [AlgoCademy — thinking in edge cases](https://algocademy.com/blog/thinking-in-edge-cases-how-to-bulletproof-your-coding-solutions-in-interviews/)
- [DesignGurus — system design interview guide](https://www.designgurus.io/system-design-interview)
- [Alex Xu — System Design Interview (Insider's Guide)](https://www.amazon.com/System-Design-Interview-insiders-Second/dp/B08CMF2CQF)
- [interviewing.io — Google senior engineer guide](https://interviewing.io/guides/hiring-process/google)
