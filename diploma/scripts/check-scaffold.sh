#!/usr/bin/env bash
# Sanity check that pipeline is ready for scheduled run.
# Run manually before relying on autonomous nightly invocations.

set -e
cd "$(dirname "$0")/../.."

echo "=== 1. Branch check ==="
BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "master" ]; then
  echo "  FAIL: expected master, got $BRANCH"
  exit 1
fi
echo "  OK: on master"

echo ""
echo "=== 2. Required files ==="
REQUIRED=(
  "diploma/CLAUDE.md"
  "diploma/README.md"
  "diploma/docs/style-guide.md"
  "diploma/docs/sources.md"
  "diploma/docs/glossary.md"
  "diploma/docs/narrative.md"
  "diploma/scripts/wake-up-prompt.txt"
  "diploma/text/01-intro.md"
  "diploma/text/02-review.md"
  "diploma/text/03-requirements.md"
  "diploma/text/04-architecture.md"
  "diploma/text/05-implementation.md"
  "diploma/text/06-ml-finetuning.md"
  "diploma/text/07-experiments.md"
  "diploma/text/08-conclusion.md"
)
for FILE in "${REQUIRED[@]}"; do
  if [ ! -f "$FILE" ]; then
    echo "  FAIL: missing $FILE"
    exit 1
  fi
done
echo "  OK: all ${#REQUIRED[@]} required files present"

echo ""
echo "=== 3. Tools available ==="
for TOOL in bd git python claude; do
  if command -v "$TOOL" >/dev/null 2>&1; then
    echo "  OK: $TOOL → $(command -v $TOOL)"
  else
    echo "  FAIL: $TOOL not found in PATH"
    [ "$TOOL" != "claude" ] && exit 1  # claude not strictly required for check
  fi
done

echo ""
echo "=== 4. Beads state ==="
TOTAL=$(bd list --label vkr --json | python -c "import json,sys; print(len(json.loads(sys.stdin.read())))")
OPEN=$(bd list --label vkr --status open --json | python -c "import json,sys; print(len(json.loads(sys.stdin.read())))")
READY=$(bd ready --label vkr --limit 100 --json | python -c "import json,sys; d=[x for x in json.loads(sys.stdin.read()) if x['issue_type']=='task']; print(len(d))")
echo "  Total vkr issues:           $TOTAL"
echo "  Open vkr issues:            $OPEN"
echo "  Ready tasks (excl. epic):   $READY"
if [ "$READY" -lt 1 ]; then
  echo "  WARNING: no ready tasks — agent will exit without writing"
fi

echo ""
echo "=== 5. Next task agent will pick ==="
bd ready --label vkr --limit 100 --json | python -c "
import json, sys
d = [x for x in json.loads(sys.stdin.read()) if x['issue_type']=='task']
d.sort(key=lambda x: (x['priority'], x['created_at']))
if d:
    t = d[0]
    print(f'  {t[\"id\"]} (P{t[\"priority\"]})')
    print(f'  Title: {t[\"title\"]}')
    print(f'  Description: {t.get(\"description\", \"\")[:120]}')
else:
    print('  (none)')
"

echo ""
echo "=== 6. Git remote ==="
git remote -v | head -1
UPSTREAM=$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>&1 || echo "(not set)")
echo "  Upstream tracking: $UPSTREAM"

echo ""
echo "=== ALL CHECKS PASSED — pipeline ready ==="
