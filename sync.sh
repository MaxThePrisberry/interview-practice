#!/usr/bin/env bash
# Encrypted off-machine backup of the PERSONAL ledger (entries.jsonl + sessions/).
#
# Model: snapshot-on-sync. Plaintext data stays LOCAL and gitignored. Only the
# encrypted blob `ledger.age` is committed and pushed, so the remote (even a public
# repo) never sees your performance history in the clear.
#
#   ./sync.sh push      encrypt the ledger -> ledger.age, commit, push
#   ./sync.sh restore   decrypt ledger.age -> rebuild entries.jsonl + sessions/
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

case "${1:-}" in
  push)
    [ -f "$RECIP" ] || die "missing $RECIP"
    args=(); rcount=0
    while IFS= read -r line; do
      line="${line%%#*}"; line="$(echo "$line" | tr -d '[:space:]')"
      [ -n "$line" ] && { args+=( -r "$line" ); rcount=$((rcount+1)); }
    done < "$RECIP"
    [ "$rcount" -gt 0 ] || die "no recipient keys in $RECIP"
    # tar only what exists, then encrypt to all recipients
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
  restore)
    [ -f "$BLOB" ] || die "no ledger.age to restore from"
    [ -f "$KEY" ]  || die "missing age key at $KEY (recover it from your password manager)"
    age -d -i "$KEY" "$BLOB" | tar xzf -
    echo "restored ${DATA[*]} from ledger.age"
    ;;
  *)
    echo "usage: $0 {push|restore}" >&2; exit 1 ;;
esac
