#!/usr/bin/env bash
# One-step setup for a fresh clone: link the /practice command into Claude Code,
# make scripts executable, and check prerequisites.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.claude/commands"

mkdir -p "$DEST"
ln -sf "$REPO/commands/practice.md" "$DEST/practice.md"
echo "linked  $DEST/practice.md -> $REPO/commands/practice.md   (use /practice)"

chmod +x "$REPO"/*.py "$REPO/sync.sh" "$REPO/install.sh" 2>/dev/null || true
echo "made scripts executable"

# Bootstrap per-user config from templates (gitignored; never clobbers an existing one)
if [ ! -f "$REPO/profile.md" ]; then
  cp "$REPO/profile.example.md" "$REPO/profile.md"
  echo "created profile.md from template — EDIT it to set your level / language / focus"
fi
if [ ! -f "$REPO/recipients.txt" ]; then
  cp "$REPO/recipients.example.txt" "$REPO/recipients.txt"
  echo "created recipients.txt from template — replace the placeholder with YOUR age public key"
fi

if command -v age >/dev/null 2>&1; then
  echo "age: $(age --version)"
else
  echo "WARNING: 'age' not installed — needed for ./sync.sh backup/restore."
  echo "  install (no root): grab a release binary from github.com/FiloSottile/age into ~/.local/bin"
fi

if [ ! -f "$HOME/.ssh/practice-age-key.txt" ]; then
  echo "NOTE: no age key at ~/.ssh/practice-age-key.txt."
  echo "  - new setup:     age-keygen -o ~/.ssh/practice-age-key.txt && chmod 600 ~/.ssh/practice-age-key.txt"
  echo "                   (then add its public key to recipients.txt)"
  echo "  - restoring:     put your saved secret key there, then run ./sync.sh restore"
fi
echo "done."
