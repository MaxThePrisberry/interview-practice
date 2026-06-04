#!/usr/bin/env bash
# Encrypted off-machine backup of the PERSONAL ledger (entries.jsonl + sessions/ + profile.md).
#
# Model: snapshot-on-sync. Plaintext data stays LOCAL and gitignored. Only the
# encrypted blob `ledger.age` is committed and pushed, so the remote (even a public
# repo) never sees your performance history in the clear.
#
#   ./sync.sh push      encrypt the ledger -> ledger.age, commit, push (refuses if stale)
#   ./sync.sh pull      fetch + fast-forward, then decrypt ledger.age onto this machine
#   ./sync.sh restore   decrypt the local ledger.age -> rebuild entries.jsonl + sessions/
#
# MULTI-MACHINE: ledger.age is one encrypted blob git CANNOT merge. Run `pull` before a
# session on a different machine, and `push` after. `push` refuses on a stale base so two
# machines can't silently diverge / lose entries.
#
# Key:   ~/.ssh/practice-age-key.txt  (override with $PRACTICE_AGE_KEY)
# Recipients: recipients.txt (one age public key per line; multi-recipient = sharing)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
KEY="${PRACTICE_AGE_KEY:-$HOME/.ssh/practice-age-key.txt}"
RECIP="$HERE/recipients.txt"
BLOB="$HERE/ledger.age"
DATA=(entries.jsonl sessions profile.md)

die() { echo "error: $*" >&2; exit 1; }
command -v age >/dev/null 2>&1 || die "age not found on PATH"

decrypt_blob() {
  [ -f "$BLOB" ] || die "no ledger.age to restore from"
  [ -f "$KEY" ]  || die "missing age key at $KEY (recover it from your password manager)"
  age -d -i "$KEY" "$BLOB" | tar xzf -
}

case "${1:-}" in
  push)
    # Staleness guard: never push on top of a base the remote has moved past.
    if git remote get-url origin >/dev/null 2>&1; then
      git fetch -q origin || true
      BR="$(git rev-parse --abbrev-ref HEAD)"
      if git rev-parse -q --verify "origin/$BR" >/dev/null 2>&1 \
         && ! git merge-base --is-ancestor "origin/$BR" HEAD; then
        die "remote/$BR has commits this machine doesn't — run './sync.sh pull' first (ledger.age can't be merged; pushing now would diverge)"
      fi
    fi
    [ -f "$RECIP" ] || die "missing $RECIP"
    args=(); rcount=0
    while IFS= read -r line; do
      line="${line%%#*}"; line="$(echo "$line" | tr -d '[:space:]')"
      [ -n "$line" ] && { args+=( -r "$line" ); rcount=$((rcount+1)); }
    done < "$RECIP"
    [ "$rcount" -gt 0 ] || die "no recipient keys in $RECIP"
    present=()
    for p in "${DATA[@]}"; do [ -e "$p" ] && present+=("$p"); done
    [ ${#present[@]} -gt 0 ] || die "nothing to back up (no ${DATA[*]})"
    tar czf - "${present[@]}" | age "${args[@]}" -o "$BLOB"
    echo "encrypted ${present[*]} -> ledger.age ($rcount recipient(s))"
    git add -A
    git commit -q -m "sync: encrypted ledger snapshot" || { echo "(nothing to commit)"; exit 0; }
    if git remote get-url origin >/dev/null 2>&1; then
      git push -q origin HEAD && echo "pushed to origin."
    else
      echo "committed locally (no 'origin' remote configured)."
    fi
    ;;
  pull)
    git remote get-url origin >/dev/null 2>&1 || die "no 'origin' remote configured"
    BR="$(git rev-parse --abbrev-ref HEAD)"
    git fetch -q origin
    git merge --ff-only "origin/$BR" 2>/dev/null \
      || die "local diverges from origin/$BR — you have unpushed local commits. Push from the machine that has the newest ledger first, or back up entries.jsonl and 'git reset --hard origin/$BR'."
    decrypt_blob
    echo "pulled origin/$BR and restored ${DATA[*]} from ledger.age"
    ;;
  restore)
    decrypt_blob
    echo "restored ${DATA[*]} from ledger.age"
    ;;
  *)
    echo "usage: $0 {push|pull|restore}" >&2; exit 1 ;;
esac
