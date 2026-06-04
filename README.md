# Daily Interview Practice — System

A self-hosted daily interview-practice ritual for **Claude Code**: one coding + one
system-design problem a day, run through a "flipped" protocol that trains you to surface
the hard parts *unprompted*. It keeps a persistent, append-only ledger and schedules
spaced revisits. Built to be **ironclad**: the writer is an LLM, so the design's #1 job
is to make it impossible to silently lose or rewrite history.

Generic and forkable — your personal config (`profile.md`, `recipients.txt`) and data
(`entries.jsonl`, `sessions/`) are gitignored, so the repo itself carries no personal
information. **Prerequisites:** Claude Code; Python 3 (stdlib only); `git`; `age` (only
for the optional encrypted backup).

## Design invariants (don't break these)
1. **Append-only source of truth.** `entries.jsonl` is only ever appended to, via
   `log_entry.py`. Never hand-edit or rewrite it. A bad write can add one bad line;
   it can never destroy the past.
2. **Selection is deterministic, in code — not vibes.** `select_today.py` decides
   what to practice. The agent does not eyeball the ledger and "pick something."
3. **Zero runtime dependencies.** Pure Python stdlib + git. No DB daemon, no pip
   installs — the daily ritual can't break on a missing import.
4. **Versioned + encrypted backup.** Local git for history/audit. Off-machine backup is
   opt-in and manual via `./sync.sh push`: your personal data is `age`-encrypted into
   `ledger.age` before it ever leaves the machine, so the remote (even a PUBLIC repo)
   only ever sees ciphertext. Plaintext (`entries.jsonl`, `sessions/`) is gitignored.

## Quick start
1. `./install.sh` once — symlinks the `/practice` command into `~/.claude/commands/`, makes
   scripts executable, checks for `age`, and creates `profile.md` + `recipients.txt` from
   the committed templates.
2. Edit **`profile.md`** (your level / language / training focus) so the interviewer
   calibrates to you.
3. (Optional backup) generate an age key and put your public key in `recipients.txt` — see
   *Encrypted backup* below.
4. Type **`/practice`** in Claude Code.

## Files
- `PROTOCOL.md` — the judging contract (candidate profile, flipped protocol, what each
  grade means, sourcing rules). The behavioral half; this README is the mechanical half.
- `RUBRIC_SOURCES.md` — the published rubrics the metrics are grounded in, labeling each
  metric [standard] / [calibration] / [bespoke]. Audit trail for "is this professional?".
- `profile.md` (gitignored) / `profile.example.md` — your calibration: level, language,
  training focus. The interviewer reads `profile.md`; copy it from the example.
- `recipients.txt` (gitignored) / `recipients.example.txt` — age public key(s) for the
  encrypted backup. Yours stays local; only the template is committed.
- `commands/practice.md` — the `/practice` slash command (symlinked into `~/.claude/commands/`).
- `install.sh` — one-step setup for a fresh clone.
- `curriculum.json` — the syllabus as data. Stable `id`s (entries reference them).
  `status: "mined"` excludes a topic from auto-pick/revisit (revisit only on purpose).
  Coverage is otherwise **derived** from entries, not stored here. Hand-edit to add topics.
- `entries.jsonl` — append-only spine. One JSON object per problem. The queryable record.
- `sessions/YYYY-MM-DD.md` — rich narrative per session (the teardown, what you missed).
  Additive: one new file per day, never overwrites.
- `select_today.py` — deterministic picker. Variable cadence via `--coding N --design N`
  (default 1 each, 0 to skip); auto-escalated difficulty, last drill surfaced, catch-up
  overflow when many revisits are overdue, and the topic's PAST PROBLEMS surfaced so the
  agent generates something materially different (repeat-avoidance). See `--help`.
- `log_entry.py` — validated append + quality-aware spaced repetition. See `--help`.
- `report.py` — trend report: proactivity + signal trends, per-category blind spots.

## Entry schema (one JSON object per line in entries.jsonl)
| field | meaning |
|---|---|
| `date` | ISO date of the session |
| `domain` | `coding` \| `design` |
| `topic_id` | curriculum id (FK into curriculum.json) |
| `difficulty` | `easy` \| `medium` \| `hard` — context denominator; auto-escalates |
| `problem` | name or short description |
| `scoping` | `strong` \| `partial` \| `none` — did they clarify BEFORE solving? (the *how*, pre-solve) |
| `driver` | `candidate` \| `mixed` \| `interviewer` \| `unknown` — **who drove the rigor** (the *how*) |
| `attack_hits` / `attack_misses` | applicable reference taxonomy categories caught / missed |
| `novel_attacks` | count of relevant OFF-LIST cases found — the anti-rote antagonism signal |
| `self_attack_coverage` | derived `"caught/total"` from the two lists above (nullable) |
| `solution` | `optimal` \| `solid` \| `suboptimal` \| `incorrect` \| `unsolved` — **answer quality** (the *what*) |
| `aided` | `unaided` \| `nudged` \| `hinted` \| `given` — how much help to reach it |
| `complexity_stated` | `yes` \| `prompted` \| `wrong` \| `no` \| `na` — stated Big-O *unprompted*? |
| `code_quality` | `clean` \| `adequate` \| `messy` \| `na` — graded apart from correctness (coding) |
| `pushback` | `held` \| `folded_correctly` \| `caved` \| `doubled_down` \| `na` — resilience when probed |
| `signal` | `no-hire` \| `lean-no` \| `lean-hire` \| `hire` \| `strong-hire` — holistic hire-bar read |
| `self_grade` | candidate's predicted `signal` (before reveal) — calibration / self-awareness |
| `pass_class` | derived `strong` \| `weak` \| `fail` — drives scheduling (see below) |
| `verdict` | optional override; `revisit` forces a soon revisit |
| `drill` | the ONE thing to fix next; surfaced when the topic recurs |
| `interval_days` / `revisit_after` | computed spaced-repetition schedule |
| `notes` | short structured summary |

## The metrics that matter
Two orthogonal axes the senior bar grades:
- **HOW (proactivity)** — `scoping` (clarified up front?), `driver` (who surfaced the
  rigor?), the structured self-attack (`attack_hits`/`attack_misses`), and `pushback`
  (held ground when probed?). This is the one thing being trained: reactive → proactive.
- **WHAT (optimality)** — `solution` (reached the *optimal* answer?) + `aided` (help
  needed?). Driving well does not excuse a brute-force answer.

`signal` is the holistic bottom line (hire-bar); `self_grade` (your prediction first)
measures calibration. `difficulty` contextualizes all of it. **Gold standard** for a
problem: `optimal + unaided + candidate-driven + scoped`.

The self-attack taxonomy is a **floor, not a ceiling**: `attack_hits`/`attack_misses`
make blind spots measurable, while `novel_attacks` rewards finding cases the list doesn't
have — so we train genuine antagonism, not rote recital. `report.py` shows whether the
`driver`/`signal` trends are improving, your per-category **blind spots**, the novel-case
trend, and your calibration gap. Metrics are grounded in `RUBRIC_SOURCES.md`.

## Quality-aware spaced repetition (Moderate profile, in log_entry.py)
Scheduling is driven by `pass_class`, derived from how the pass actually went — a
reactive pass resurfaces sooner than a clean one:
- `strong` → `max(7, prior * 2)` — clean, proactive, ~gold: double the interval
- `weak` → `max(7, prior)` — interviewer-driven / no scoping / hinted / suboptimal: HOLD
- `fail` → 3d — incorrect/unsolved, bottom signal, or `--verdict revisit`: tight loop

**Difficulty auto-escalates**: a strong pass steps the next target up
(easy→medium→hard), a fail steps it down, a weak pass holds. New topics start at medium.

## Encrypted backup & sharing (age + sync.sh)
The repo cleanly splits into two layers:
- **Machinery** (`*.py`, `curriculum.json`, docs, `*.example` templates, `sync.sh`) —
  generic, plaintext, safe to share. Anyone can clone it and run the system with their
  own ledger. The repo can even be public.
- **Personal config & data** (`profile.md`, `recipients.txt`, `entries.jsonl`,
  `sessions/`) — gitignored; never committed in the clear. The ledger + profile are backed
  up only as the encrypted `ledger.age`.

Commands:
- `./sync.sh push` — encrypt the ledger to every key in `recipients.txt`, commit
  `ledger.age`, push. Run it after a session when you want an off-machine snapshot.
- `./sync.sh restore` — decrypt `ledger.age` back into `entries.jsonl` + `sessions/`
  (e.g. on a new machine). Needs your secret key.

Keys:
- Secret key: `~/.ssh/practice-age-key.txt` (`600`). **Also keep a copy off-machine
  (password manager).** Lose it and every encrypted backup is unrecoverable — there is
  no recovery path. SSH keys are regenerable; this one is not.
- Public key(s): `recipients.txt`. Add a collaborator's age public key there + `push`
  to grant them read access to your history; remove + `push` to revoke.
- Each `push` writes a fresh `ledger.age` (age uses a random ephemeral key), so expect
  one snapshot commit per push even if little changed. That's fine — it's manual.

## Daily flow (what /practice does)
1. `python3 select_today.py` → today's picks, target difficulty, last drill to prove fixed.
2. Work the problems **one at a time**, each in the **flipped protocol**: scope/clarify
   first → solve out loud → your OWN teardown → agent probes for resilience → agent grades
   **and teaches the optimal approach**, then logs it. Never lists the gaps before the
   self-attack.
3. After grading, the agent **stops and waits** — this is your time to ask about anything you
   didn't understand. The next problem starts only when you say you're ready.
4. After the last problem: `sessions/YYYY-MM-DD.md` narrative, `git commit`, optional
   `./sync.sh push`, and an optional `report.py` readout.

## License
No license — this is a personal project (all rights reserved). It's public so you can read
and fork it for your own use, but it's not formally licensed for redistribution.
