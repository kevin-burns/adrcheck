#!/usr/bin/env bash
# commit-msg hook: enforce Conventional Commits and reject AI attribution trailers.
# Subjects use `type(scope): summary`.
set -euo pipefail

message_file="${1:?usage: check-commit-msg.sh <commit-msg-file>}"
subject="$(grep -v '^#' "$message_file" | sed -n '1p')"

case "$subject" in
  Merge\ * | Revert\ * | fixup!\ * | squash!\ *) ;;
  *)
    pattern='^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9._-]+\))?!?: .+'
    if ! grep -Eq "$pattern" <<<"$subject"; then
      printf 'commit-msg: subject is not a Conventional Commit: %s\n' "$subject" >&2
      printf 'expected: type(scope): summary\n' >&2
      exit 1
    fi
    ;;
esac

if grep -v '^#' "$message_file" | grep -Eiq 'co-authored-by:.*(claude|anthropic|codex|openai|copilot)|generated with \[?claude|claude-session:|claude\.ai/code'; then
  printf 'commit-msg: AI attribution or session link found; remove it before committing\n' >&2
  exit 1
fi
